"""Phase 4: measure the six methods' relative belief quality across
shared self-play snapshots.

Actions are still `RandomBot`-driven -- turning belief into a chosen
move is Phase 5's personality layer, which doesn't exist yet -- so this
can only compare *belief quality*, not win rate. Three metrics per
agent, per checkpoint (fraction of the game's suggestions played so
far):

- **Brier score** -- mean squared error between each of the 21 cards'
  predicted probability and its true 0/1 envelope membership. A proper
  scoring rule (lower is better); 0 is perfect.
- **Log loss** -- mean ``-log(P(true card))`` per category (lower is
  better). Punishes confident wrong answers harder than Brier does,
  which is exactly the number that should make Scarlett's overconfidence
  and Mustard's confident-but-wrong failure mode visible.
- **Top-1 accuracy** -- fraction of categories where the agent's
  highest-probability card is the true one. The most intuitive number,
  and a rough proxy for "would this method have won if it could act on
  its own top guess."

Alongside those, each (agent, checkpoint) cell records wall-clock cost
per `select_action` call and, for methods that report it in
`ClueBelief.extra` (Plum), how often the call fell back to sampling --
the raw material for the speed question Phase 5's arena has to answer.

Green's bandit posteriors are deliberately *not* reset between games in
this module (each agent instance is built once and reused for the whole
run) -- David's call: the benchmark should show Green actually learning
which method to trust over many games, not just his one-shot cold-start
quality. Every agent's `observe` is called with the revealed envelope
after every snapshot; only Green's does anything today, since every
other agent is either stateless (`select_action` is a pure function of
`obs`) or trained once at construction (Mustard).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Optional

from clude_agents import list_agent_specs
from clude_agents.bandit import RevealedOutcome
from clude_agents.base import mask_and_normalize
from clude_core.domain import ROOMS, SUSPECTS, WEAPONS
from clude_training.self_play import (
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
    n_snapshots: int = 0
    per_agent: dict = field(default_factory=dict)  # name -> {checkpoint: _Accumulator}
    agents: dict = field(default_factory=dict)  # name -> agent instance

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
            "n_snapshots": self.n_snapshots,
            "per_agent": {
                name: {str(cp): acc.to_dict() for cp, acc in cells.items()}
                for name, cells in self.per_agent.items()
            },
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
) -> BenchmarkResult:
    """Run agents (plus the uniform baseline) over shared self-play
    snapshots and score each one's belief against the eventual ground
    truth.

    Parameters
    ----------
    n_games, seed, checkpoints, player_counts, max_turns
        Passed to `generate_snapshots`; `player_counts` fixes or cycles
        the table size.
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
        per_agent={name: {cp: _Accumulator() for cp in checkpoints} for name in names},
        agents=agents,
    )

    for snap in generate_snapshots(
        n_games, seed, checkpoints=checkpoints, max_turns=max_turns, player_counts=player_counts
    ):
        result.n_snapshots += 1
        result.per_agent[UNIFORM][snap.checkpoint].update(
            _uniform_probabilities(snap.obs), snap.envelope
        )
        for name, agent in agents.items():
            cell = result.per_agent[name][snap.checkpoint]
            started = time.perf_counter()
            belief = agent.select_action(snap.obs)
            cell.record_call(time.perf_counter() - started, belief.extra)
            cell.update(belief.probabilities, snap.envelope)
            agent.observe(RevealedOutcome(envelope=snap.envelope))

    return result
