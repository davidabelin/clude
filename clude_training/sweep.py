"""Compare one Profile dial across paired arena seed sequences.

Optional logbooks are read-only at every value; keep memory inputs fixed.
Report per-value results/variation rather than claiming significance from
small runs. Real LLM choices can spend money and are not deterministic.
See docs/cli.md and docs/strategy-glossary.md.
"""
from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field
from typing import Callable, Optional

from clude_agents import AGENT_SPECS
from clude_agents.personality import DIALS, preset
from clude_training.arena import (
    DEFAULT_MAX_TURNS,
    DEFAULT_N_GAMES,
    DEFAULT_ROSTER,
    DEFAULT_SEED,
    PlayerStats,
    parse_roster,
    run_arena,
)
from clude_training.self_play import DEFAULT_PLAYER_COUNTS

SWEEP_METRICS: tuple = (
    "win_rate",
    "wrong_accusation_rate",
    "mean_first_accusation_turn",
    "never_accused_rate",
    "mean_cards_leaked",
    "mean_own_cards_named",
    "reshow_rate",
    "fallback_rate",
    "deviation_rate",
    "remarks_per_game",
)

PHASE14_HEADLESS_GRIDS: dict = {
    "accuse_threshold": (0.2, 0.4, 0.6, 0.8, 1.0),
    "bluff_rate": (0.0, 0.25, 0.5, 1.0),
    "curiosity": (0.0, 0.5, 1.0),
    "secrecy": (0.0, 0.5, 1.0),
    "temperature": (0.0, 0.05, 0.1, 0.2, 0.5, 2.0),
}
PHASE14_PAID_GRIDS: dict = {
    "chattiness": (0.0, 0.25, 0.5, 0.75, 1.0),
    "memory": (0.0, 0.25, 0.5, 0.75, 1.0),
}
PAIRED_METRICS: tuple = (
    "win_rate", "wrong_accusation_rate", "mean_cards_leaked",
    "mean_own_cards_named", "mean_suggestions", "mean_turns",
)
DIRECT_FOOTPRINTS: dict = {
    "accuse_threshold": ("wrong_accusation_rate", "never_accused_rate", "mean_first_accusation_turn"),
    "bluff_rate": ("mean_own_cards_named",),
    "curiosity": ("mean_suggestions",),
    "secrecy": ("mean_cards_leaked", "reshow_rate"),
    "temperature": ("mean_turns",),
    "leash": ("deviation_rate",),
    "chattiness": ("remarks_per_game",),
    "memory": ("llm_lookups", "llm_entries"),
}


def phase14_isolated_values(dial: str, current: float) -> tuple:
    """Phase 14's three-value isolated screen around a preset."""
    current = float(current)
    if dial == "temperature":
        return tuple(dict.fromkeys((0.0, current, round(2.0 * current, 12))))
    if dial not in DIALS:
        raise ValueError(f"unknown dial {dial!r}; dials are {DIALS}")
    return tuple(dict.fromkeys((
        round(max(0.0, current - 0.2), 12), current, round(min(1.0, current + 0.2), 12),
    )))


def pooled_stats(stats_by_label: dict, labels) -> PlayerStats:
    """One `PlayerStats` with every listed label's counts pooled."""
    pooled = PlayerStats(label="+".join(labels), kind="character")
    for label in labels:
        if label in stats_by_label:
            pooled.merge(stats_by_label[label])
    return pooled


@dataclass(frozen=True)
class SweepRow:
    """The swept characters' pooled metrics at one dial value."""

    value: float
    stats: PlayerStats
    mean_turns: float

    def metric(self, name: str) -> float:
        if name == "mean_turns":
            return self.mean_turns
        return getattr(self.stats, name)


@dataclass
class SweepResult:
    """One `sweep_dial` call: one `SweepRow` per value, plus every
    underlying `ArenaResult` for anyone who wants the per-label detail."""

    dial: str
    values: tuple
    characters: tuple
    roster: tuple
    rows: list = field(default_factory=list)
    results: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    not_applicable: tuple = ()

    def monotone(self, metric: str, tolerance: float = 1e-9) -> Optional[str]:
        """``"increasing"``, ``"decreasing"``, ``"flat"`` or None.

        Non-strict in either direction, but at least one step must
        actually move (else ``"flat"``); None means the metric went both
        ways. NaN values (no data at that point) make the answer None.
        """
        series = [row.metric(metric) for row in self.rows]
        if len(series) < 2 or any(v != v for v in series):
            return None
        diffs = [b - a for a, b in zip(series, series[1:])]
        if all(abs(d) <= tolerance for d in diffs):
            return "flat"
        if all(d >= -tolerance for d in diffs):
            return "increasing"
        if all(d <= tolerance for d in diffs):
            return "decreasing"
        return None

    def summary_table(self) -> str:
        """One row per dial value, pooled over the swept characters."""
        header = (
            f"{self.dial:<18}{'games':>6}{'win%':>7}{'+-':>5}{'wrong%':>8}{'+-':>5}"
            f"{'1st_acc':>9}{'never%':>8}{'leaked':>8}{'named':>7}{'reshow%':>9}{'turns':>7}"
            f"{'deviate%':>10}{'talk/g':>8}"
        )
        lines = [header, "-" * len(header)]
        for row in self.rows:
            s = row.stats
            first = f"{s.mean_first_accusation_turn:>9.1f}" if s.first_accusation_turns else f"{'-':>9}"
            reshow = f"{100 * s.reshow_rate:>9.1f}" if s.reshow_choices else f"{'-':>9}"
            deviate = f"{100 * s.deviation_rate:>10.1f}" if s.llm_played else f"{'-':>10}"
            talk = f"{s.remarks_per_game:>8.2f}" if s.llm_decisions else f"{'-':>8}"
            lines.append(
                f"{row.value:<18.3f}{s.games:>6}{100 * s.win_rate:>7.1f}{100 * s.win_rate_std:>5.1f}"
                f"{100 * s.wrong_accusation_rate:>8.1f}{100 * s.wrong_accusation_std:>5.1f}"
                f"{first}{100 * s.never_accused_rate:>8.1f}{s.mean_cards_leaked:>8.2f}"
                f"{s.mean_own_cards_named:>7.2f}{reshow}{row.mean_turns:>7.1f}{deviate}{talk}"
            )
        verdicts = []
        for metric in SWEEP_METRICS:
            verdict = self.monotone(metric)
            if verdict in ("increasing", "decreasing"):
                verdicts.append(f"{metric} {verdict}")
        lines.append("")
        lines.append(
            "monotone: " + (", ".join(verdicts) if verdicts else "no metric moved monotonically")
        )
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """JSON-ready Phase 14 evidence, including paired uncertainty."""
        return {
            "dial": self.dial,
            "values": list(self.values),
            "characters": list(self.characters),
            "roster": list(self.roster),
            "not_applicable": list(self.not_applicable),
            "metadata": dict(self.metadata),
            "completed_values": [row.value for row in self.rows],
            "complete": len(self.rows) == len(self.values),
            "rows": [
                {"value": row.value, "mean_turns": row.mean_turns, **row.stats.to_dict()}
                for row in self.rows
            ],
            "per_character": self.per_character_rows(),
            "direct_footprint": self.direct_footprint(),
            "paired_deltas": self.paired_deltas(),
            "usage": self.usage(),
            "monotone": {metric: self.monotone(metric) for metric in SWEEP_METRICS},
            "runs": [r.to_dict() for r in self.results],
        }

    def per_character_rows(self) -> list:
        """One row per value and swept character, without pooling."""
        rows = []
        for value, result in zip(self.values, self.results):
            for character in self.characters:
                stats = result.per_player.get(character)
                if stats is not None:
                    rows.append({"value": value, **stats.to_dict()})
        return rows

    def direct_footprint(self) -> dict:
        """The metrics closest to the dial's direct decision surface."""
        metrics = DIRECT_FOOTPRINTS[self.dial]
        return {
            "metrics": list(metrics),
            "rows": [
                {"value": row.value, **{metric: row.metric(metric) for metric in metrics}}
                for row in self.rows
            ],
        }

    def usage(self) -> dict:
        """Tokens and recorded list-price cost by value and in total."""
        rows = []
        totals = {
            "llm_calls": 0, "input_tokens": 0, "output_tokens": 0,
            "cached_tokens": 0, "list_price_cost": 0.0,
        }
        for value, result in zip(self.values, self.results):
            stats = list(result.per_player.values())
            row = {
                "value": value,
                "llm_calls": sum(s.llm_calls for s in stats),
                "input_tokens": sum(s.llm_input_tokens for s in stats),
                "output_tokens": sum(s.llm_output_tokens for s in stats),
                "cached_tokens": sum(s.llm_cached_tokens for s in stats),
                "list_price_cost": round(sum(g.cost or 0.0 for g in result.games), 6),
            }
            rows.append(row)
            for key in totals:
                totals[key] += row[key]
        totals["list_price_cost"] = round(totals["list_price_cost"], 6)
        return {"values": rows, "total": totals}

    def paired_deltas(self, bootstrap_samples: int = 2000) -> list:
        """Pointwise game-bootstrap intervals versus the first completed value.

        Average swept characters within each paired game before taking the
        difference, so games have equal weight. Pooled table rates instead
        weight seat-games equally and can give a different mixed-roster delta.
        Resample games, not individual seats; no multiple-comparison correction
        is applied. ``bootstrap_samples`` controls the resample count.
        """
        if not self.results:
            return []
        baseline = self.results[0]
        rows = []
        for value, result in zip(self.values, self.results):
            metrics = {}
            for metric in PAIRED_METRICS:
                differences = _paired_game_differences(baseline, result, self.characters, metric)
                metrics[metric] = _bootstrap_interval(
                    differences, f"{self.dial}|{value}|{metric}", bootstrap_samples
                )
            rows.append({"value": value, "baseline_value": self.values[0], "metrics": metrics})
        return rows


def _outcome_metric(outcome, metric: str) -> float:
    if metric == "win_rate":
        return float(outcome.won)
    if metric == "wrong_accusation_rate":
        return float(outcome.wrong_accusation)
    if metric == "mean_cards_leaked":
        return float(outcome.cards_leaked)
    if metric == "mean_own_cards_named":
        return float(outcome.own_cards_named)
    if metric == "mean_suggestions":
        return float(outcome.suggestions)
    raise ValueError(metric)


def _paired_game_differences(baseline, candidate, characters: tuple, metric: str) -> list:
    if len(baseline.games) != len(candidate.games):
        raise ValueError("paired sweep runs have different game counts")
    differences = []
    for left, right in zip(baseline.games, candidate.games):
        if left.seed != right.seed:
            raise ValueError("paired sweep runs have different seed sequences")
        if metric == "mean_turns":
            differences.append(float(right.turns - left.turns))
            continue
        left_by_label = {outcome.label: outcome for outcome in left.seat_outcomes}
        right_by_label = {outcome.label: outcome for outcome in right.seat_outcomes}
        labels = [label for label in characters if label in left_by_label and label in right_by_label]
        if not labels:
            continue
        before = sum(_outcome_metric(left_by_label[label], metric) for label in labels) / len(labels)
        after = sum(_outcome_metric(right_by_label[label], metric) for label in labels) / len(labels)
        differences.append(after - before)
    return differences


def _bootstrap_interval(differences: list, key: str, samples: int) -> dict:
    if not differences:
        return {"delta": float("nan"), "low": float("nan"), "high": float("nan"), "n_pairs": 0}
    delta = sum(differences) / len(differences)
    if len(differences) == 1 or not any(abs(value - differences[0]) > 1e-15 for value in differences):
        low = high = delta
    else:
        seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16)
        rng = random.Random(seed)
        means = sorted(
            sum(differences[rng.randrange(len(differences))] for _ in differences) / len(differences)
            for _ in range(samples)
        )
        low = means[max(0, math.floor(0.025 * (samples - 1)))]
        high = means[min(samples - 1, math.ceil(0.975 * (samples - 1)))]
    return {"delta": delta, "low": low, "high": high, "n_pairs": len(differences)}


def sweep_dial(
    dial: str,
    values,
    n_games: int = DEFAULT_N_GAMES,
    seed: int = DEFAULT_SEED,
    roster=DEFAULT_ROSTER,
    characters=None,
    player_counts: tuple = DEFAULT_PLAYER_COUNTS,
    max_turns: int = DEFAULT_MAX_TURNS,
    store=None,
    run_id: Optional[str] = None,
    llm_backend=None,
    llm_settings=None,
    llm_characters=None,
    logbook_store=None,
    logbook_characters=None,
    llm_canon=None,
    metadata: Optional[dict] = None,
    on_update: Optional[Callable[[SweepResult], None]] = None,
    agent_overrides: Optional[dict] = None,
    agent_states: Optional[dict] = None,
) -> SweepResult:
    """Run the arena once per value of `dial`, setting it on every swept
    character (their other dials stay at preset), and pool the swept
    characters' metrics per value.

    Parameters
    ----------
    dial : str
        One of `clude_agents.personality.DIALS`.
    values : iterable of float
        In the order to report them.
    characters : iterable of str or None
        Which characters get the dial set; default every character in
        `roster`. Characters not swept keep their presets.
    n_games, seed, roster, player_counts, max_turns, store
        Passed to `run_arena`; the same `seed` for every value.
    llm_backend, llm_settings, llm_characters, llm_canon
        Passed to `run_arena`: sweep a dial with the characters
        LLM-piloted, the `leash` sweep being the point.
    run_id : str or None
        Prefix for each value's run id (``<run_id>-<dial>-<value>``);
        default ``sweep-<seed>-<n_games>``.
    logbook_store : RecordStore or None
        Passed to `run_arena` read-only: every value's run
        reads the same logbooks and none writes, so the comparison stays
        paired. The `memory` dial is swept this way.
    logbook_characters : iterable of str or None
        Passed to `run_arena`: which characters get a logbook (default
        all of them).

    Raises
    ------
    ValueError
        On an unknown dial, an empty value list, or a swept name that is
        not a character in the roster.
    """
    if dial not in DIALS:
        raise ValueError(f"unknown dial {dial!r}; dials are {DIALS}")
    values = tuple(float(v) for v in values)
    if not values:
        raise ValueError("sweep needs at least one value")
    roster = parse_roster(roster)
    requested = tuple(characters) if characters else tuple(l for l in roster if l in AGENT_SPECS)
    if dial == "curiosity" and characters is not None and "Plum" in requested:
        raise ValueError("curiosity is N/A for current Plum")
    not_applicable = ("Plum",) if dial == "curiosity" and "Plum" in requested else ()
    swept = tuple(name for name in requested if name not in not_applicable)
    for name in swept:
        if name not in AGENT_SPECS or name not in roster:
            raise ValueError(f"{name!r} is not a character in the roster {roster}")
    if not swept:
        raise ValueError("nothing to sweep: the roster has no characters")
    run_id = run_id or f"sweep-{seed}-{n_games}"

    context = {
        "n_games_per_value": n_games,
        "seed": seed,
        "player_counts": list(player_counts),
        "max_turns": max_turns,
        **dict(metadata or {}),
    }
    sweep = SweepResult(
        dial=dial, values=values, characters=swept, roster=roster,
        metadata=context, not_applicable=not_applicable,
    )
    for value in values:
        profiles = {name: preset(name).with_dials(**{dial: value}) for name in swept}
        result = run_arena(
            n_games=n_games,
            seed=seed,
            roster=roster,
            player_counts=player_counts,
            max_turns=max_turns,
            profiles=profiles,
            store=store,
            run_id=f"{run_id}-{dial}-{value:g}",
            llm_backend=llm_backend,
            llm_settings=llm_settings,
            llm_characters=llm_characters,
            llm_canon=llm_canon,
            logbook_store=logbook_store,
            logbooks_readonly=True,
            logbook_characters=logbook_characters,
            agent_overrides=agent_overrides,
            agent_states=agent_states,
        )
        sweep.results.append(result)
        sweep.rows.append(
            SweepRow(value=value, stats=pooled_stats(result.per_player, swept), mean_turns=result.mean_turns)
        )
        if on_update is not None:
            on_update(sweep)
    return sweep
