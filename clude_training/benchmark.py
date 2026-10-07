"""Measure belief quality on shared self-play snapshots, not win rate.

FloorBot is the default regime; RandomBot is a historical baseline. Report
Brier error over 21 cards, per-category log-loss/top-1, call time and optional
method diagnostics at fractions of suggestions, and a calibration table of
the accusation test's P against how often that triple was the envelope.
Uniform over the floor's allowed candidates is the control.

Agent instances persist across games; Green learns from RevealedOutcome
at every snapshot, unlike the arena's once-per-game feedback. Timings do
not reproduce from a seed. See docs/strategy-glossary.md for dated results.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Optional

from clude_agents import AGENT_SPECS, list_agent_specs
from clude_agents.bandit import RevealedOutcome
from clude_agents.base import mask_and_normalize
from clude_agents.character import best_triple, probabilities_confidence
from clude_core.domain import ROOMS, SUSPECTS, WEAPONS
from clude_training.self_play import (
    DEFAULT_BOT,
    DEFAULT_CHECKPOINTS,
    DEFAULT_MAX_TURNS,
    DEFAULT_PLAYER_COUNTS,
    generate_snapshots,
)

CATEGORIES = (SUSPECTS, WEAPONS, ROOMS)
EPS = 1e-9
DEFAULT_N_GAMES = 60
DEFAULT_SEED = 4004
UNIFORM = "uniform"


@dataclass
class _Accumulator:
    """Running totals for one (agent, checkpoint) pair. Brier is
    accumulated per card (21 per snapshot); log-loss and top-1 are
    accumulated per category (3 per snapshot) -- kept as separate
    counters since they're different units of "one observation." Call
    cost and sampling fallbacks are accumulated per `select_action`
    call (1 per snapshot).
    """

    brier_sum: float = 0.0
    n_cards: int = 0
    logloss_sum: float = 0.0
    top1_correct: int = 0
    n_categories: int = 0
    n_calls: int = 0
    seconds: float = 0.0
    sampled_calls: int = 0

    def update(self, probabilities: dict, envelope: tuple) -> None:
        """Score one belief against one ground-truth envelope."""
        for category, truth in zip(CATEGORIES, envelope):
            for c in category:
                target = 1.0 if c == truth else 0.0
                self.brier_sum += (probabilities[c] - target) ** 2
                self.n_cards += 1
            top = max(category, key=lambda c: probabilities[c])
            self.top1_correct += int(top == truth)
            self.logloss_sum += -math.log(max(probabilities[truth], EPS))
            self.n_categories += 1

    def record_call(self, seconds: float, extra: dict) -> None:
        """Record one `select_action` call's cost and, if the agent
        reported it (`extra["method"] == "sampled"`, Plum), whether it
        fell back to sampling."""
        self.n_calls += 1
        self.seconds += seconds
        if extra.get("method") == "sampled":
            self.sampled_calls += 1

    @property
    def brier(self) -> float:
        return self.brier_sum / self.n_cards if self.n_cards else float("nan")

    @property
    def log_loss(self) -> float:
        return self.logloss_sum / self.n_categories if self.n_categories else float("nan")

    @property
    def top1_accuracy(self) -> float:
        return self.top1_correct / self.n_categories if self.n_categories else float("nan")

    @property
    def ms_per_call(self) -> float:
        return 1000.0 * self.seconds / self.n_calls if self.n_calls else float("nan")

    def to_dict(self) -> dict:
        """JSON-ready metrics for this cell."""
        return {
            "brier": self.brier,
            "log_loss": self.log_loss,
            "top1_accuracy": self.top1_accuracy,
            "n_calls": self.n_calls,
            "ms_per_call": self.ms_per_call,
            "sampled_calls": self.sampled_calls,
        }


CALIBRATION_EDGES = (0.0, 0.1, 0.3, 0.5, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0)
"""Bin edges for the accusation test's P; the top bins are narrow because
the thresholds that matter (0.8-0.95) live there."""


@dataclass
class _Calibration:
    """How often the triple a character would accuse is the envelope,
    binned by the P its accusation test compares with `accuse_threshold`
    (`best_triple` over the spec's confidence), all checkpoints pooled.
    Bin i holds ``edges[i] < P <= edges[i + 1]``, the first from 0."""

    edges: tuple = CALIBRATION_EDGES
    counts: list = field(default_factory=lambda: [0] * (len(CALIBRATION_EDGES) - 1))
    p_sums: list = field(default_factory=lambda: [0.0] * (len(CALIBRATION_EDGES) - 1))
    correct: list = field(default_factory=lambda: [0] * (len(CALIBRATION_EDGES) - 1))

    def update(self, confidence: dict, envelope: tuple) -> None:
        triple, p = best_triple(confidence)
        i = next((i for i, hi in enumerate(self.edges[1:]) if p <= hi + EPS), len(self.counts) - 1)
        self.counts[i] += 1
        self.p_sums[i] += p
        self.correct[i] += int(tuple(triple) == tuple(envelope))

    def at_or_above(self, threshold: float) -> tuple:
        """(snapshots, accuracy) over every P >= `threshold`: how often an
        accusation at that threshold would have been right."""
        lows = [i for i, lo in enumerate(self.edges[:-1]) if lo >= threshold - EPS]
        n = sum(self.counts[i] for i in lows)
        hits = sum(self.correct[i] for i in lows)
        return n, (hits / n if n else float("nan"))

    def to_dict(self) -> dict:
        return {
            "edges": list(self.edges),
            "bins": [
                {
                    "n": n,
                    "mean_p": s / n if n else None,
                    "accuracy": c / n if n else None,
                }
                for n, s, c in zip(self.counts, self.p_sums, self.correct)
            ],
        }


@dataclass
class BenchmarkResult:
    """Per-agent, per-checkpoint accumulators from one `run_benchmark`
    call, plus a `"uniform"` baseline (the deduction floor's own
    mask-uniform belief, no method-specific evidence at all) that every
    real agent should beat -- a sanity floor, not a seventh suspect.

    `agents` holds the actual agent instances as they ended the run
    (Green's learned posteriors included) -- useful for inspecting
    final state, e.g. which arm Green ended up favoring.
    """

    checkpoints: tuple
    n_games: int = 0
    seed: int = 0
    player_counts: tuple = DEFAULT_PLAYER_COUNTS
    bot: str = DEFAULT_BOT
    n_snapshots: int = 0
    per_agent: dict = field(default_factory=dict)  # name -> {checkpoint: _Accumulator}
    agents: dict = field(default_factory=dict)  # name -> agent instance
    calibration: dict = field(default_factory=dict)  # name -> _Calibration

    def calibration_table(self) -> str:
        """Per agent, each P bin's count, mean P and share of triples
        correct, then the accuracy at or above 0.8, 0.9 and 0.95."""
        header = f"{'agent':<12}{'P bin':>13}{'n':>6}{'mean P':>9}{'correct':>9}"
        lines = [header, "-" * len(header)]
        for name in sorted(self.calibration):
            cal = self.calibration[name]
            for i, n in enumerate(cal.counts):
                if not n:
                    continue
                span = f"{cal.edges[i]:.2f}-{cal.edges[i + 1]:.2f}"
                lines.append(
                    f"{name:<12}{span:>13}{n:>6}{cal.p_sums[i] / n:>9.3f}{cal.correct[i] / n:>9.3f}"
                )
            above = []
            for t in (0.8, 0.9, 0.95):
                n, acc = cal.at_or_above(t)
                above.append(f">={t:.2f}: {acc:.3f} of {n}" if n else f">={t:.2f}: -")
            lines.append(f"{name:<12}  " + "; ".join(above))
        return "\n".join(lines)

    def summary_table(self) -> str:
        """One row per (agent, checkpoint), agents in name order. The
        uniform baseline has no `select_action` call, so its ``ms/call``
        prints as ``-``."""
        header = (
            f"{'agent':<12}{'checkpoint':>11}{'brier':>10}{'log_loss':>10}"
            f"{'top1_acc':>10}{'ms/call':>9}"
        )
        lines = [header, "-" * len(header)]
        for name in sorted(self.per_agent):
            for cp in self.checkpoints:
                acc = self.per_agent[name][cp]
                ms = f"{acc.ms_per_call:>9.1f}" if acc.n_calls else f"{'-':>9}"
                lines.append(
                    f"{name:<12}{cp:>11.2f}{acc.brier:>10.4f}{acc.log_loss:>10.4f}"
                    f"{acc.top1_accuracy:>10.3f}{ms}"
                )
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """JSON-ready copy of the run's settings and every cell's metrics
        (checkpoints become string keys, since JSON objects can't have
        float keys)."""
        return {
            "n_games": self.n_games,
            "seed": self.seed,
            "checkpoints": list(self.checkpoints),
            "player_counts": list(self.player_counts),
            "bot": self.bot,
            "n_snapshots": self.n_snapshots,
            "per_agent": {
                name: {str(cp): acc.to_dict() for cp, acc in cells.items()}
                for name, cells in self.per_agent.items()
            },
            "calibration": {name: cal.to_dict() for name, cal in self.calibration.items()},
        }


def _uniform_probabilities(obs) -> dict:
    """The deduction floor's own belief with zero method-specific
    evidence -- what every real agent is implicitly competing against.
    """
    return mask_and_normalize({}, obs.mask)


def run_benchmark(
    n_games: int = DEFAULT_N_GAMES,
    seed: int = DEFAULT_SEED,
    checkpoints: tuple = DEFAULT_CHECKPOINTS,
    agents: Optional[dict] = None,
    player_counts: tuple = DEFAULT_PLAYER_COUNTS,
    max_turns: int = DEFAULT_MAX_TURNS,
    bot: str = DEFAULT_BOT,
) -> BenchmarkResult:
    """Run agents (plus the uniform baseline) over shared self-play
    snapshots and score each one's belief against the eventual ground
    truth.

    Parameters
    ----------
    n_games, seed, checkpoints, player_counts, max_turns, bot
        Passed to `generate_snapshots`; `player_counts` fixes or cycles
        the table size, `bot` picks the self-play regime (``"floor"``
        by default since Phase 5, ``"random"`` for the Phase 4 one).
    agents : dict[str, AgentProtocol] or None
        Agents to score, keyed by display name. Default: all six from
        the registry. Pass a subset to benchmark one method, or a
        hand-built instance (``{"Mustard": DecisionTreeAgent(...)}``) to
        evaluate non-default hyperparameters.

    Returns
    -------
    BenchmarkResult

    Notes
    -----
    Each agent is reset with `seed` once, then reused for every snapshot
    in chronological (game, then checkpoint) order -- see the module
    docstring for why that matters specifically for Green.
    """
    if agents is None:
        agents = {spec.name: spec.factory() for spec in list_agent_specs()}
    for agent in agents.values():
        agent.reset(seed)

    names = list(agents) + [UNIFORM]
    result = BenchmarkResult(
        checkpoints=checkpoints,
        n_games=n_games,
        seed=seed,
        player_counts=tuple(player_counts),
        bot=bot,
        per_agent={name: {cp: _Accumulator() for cp in checkpoints} for name in names},
        agents=agents,
        calibration={name: _Calibration() for name in names},
    )

    for snap in generate_snapshots(
        n_games, seed, checkpoints=checkpoints, max_turns=max_turns,
        player_counts=player_counts, bot=bot,
    ):
        result.n_snapshots += 1
        uniform = _uniform_probabilities(snap.obs)
        result.per_agent[UNIFORM][snap.checkpoint].update(uniform, snap.envelope)
        result.calibration[UNIFORM].update(uniform, snap.envelope)
        for name, agent in agents.items():
            cell = result.per_agent[name][snap.checkpoint]
            started = time.perf_counter()
            belief = agent.select_action(snap.obs)
            cell.record_call(time.perf_counter() - started, belief.extra)
            cell.update(belief.probabilities, snap.envelope)
            spec = AGENT_SPECS.get(name)
            confidence = spec.confidence_fn if spec is not None else probabilities_confidence
            result.calibration[name].update(confidence(belief), snap.envelope)
            agent.observe(RevealedOutcome(envelope=snap.envelope))

    return result
