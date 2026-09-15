"""Phase 5d: dial sweeps -- the arena run once per value of one dial,
on the same deals and dice each time.

The rule for keeping a dial (docs/phase5-plan.md, section 2): it must
move at least one arena metric monotonically across a sweep, or it is
cut. `SweepResult.monotone` is that test, applied to the pooled metrics
of the swept characters. Games are paired across values -- same
`seed`, so the same deals and rolls (see `clude_training.arena`) --
which is what lets a sweep of a few dozen games say anything at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

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
        """JSON-ready: the rows' pooled metrics and every run's summary."""
        return {
            "dial": self.dial,
            "values": list(self.values),
            "characters": list(self.characters),
            "roster": list(self.roster),
            "rows": [
                {"value": row.value, "mean_turns": row.mean_turns, **row.stats.to_dict()}
                for row in self.rows
            ],
            "monotone": {metric: self.monotone(metric) for metric in SWEEP_METRICS},
            "runs": [r.to_dict() for r in self.results],
        }


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
    llm_backend, llm_settings, llm_characters
        Passed to `run_arena` (Phase 6): sweep a dial with the characters
        LLM-piloted, the `leash` sweep being the point.
    run_id : str or None
        Prefix for each value's run id (``<run_id>-<dial>-<value>``);
        default ``sweep-<seed>-<n_games>``.
    logbook_store : RecordStore or None
        Passed to `run_arena` read-only (Phase 7): every value's run
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
    swept = tuple(characters) if characters else tuple(l for l in roster if l in AGENT_SPECS)
    for name in swept:
        if name not in AGENT_SPECS or name not in roster:
            raise ValueError(f"{name!r} is not a character in the roster {roster}")
    if not swept:
        raise ValueError("nothing to sweep: the roster has no characters")
    run_id = run_id or f"sweep-{seed}-{n_games}"

    sweep = SweepResult(dial=dial, values=values, characters=swept, roster=roster)
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
            logbook_store=logbook_store,
            logbooks_readonly=True,
            logbook_characters=logbook_characters,
        )
        sweep.results.append(result)
        sweep.rows.append(
            SweepRow(value=value, stats=pooled_stats(result.per_player, swept), mean_turns=result.mean_turns)
        )
    return sweep
