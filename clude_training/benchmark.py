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

Green's bandit posteriors are deliberately *not* reset between games in
this module (each agent instance is built once and reused for the whole
run) -- David's call: the benchmark should show Green actually learning
which method to trust over many games, not just his one-shot cold-start
quality. Every other agent is either stateless (`select_action` is a
pure function of `obs`) or trained once at construction (Mustard), so
this only changes Green's behavior, not theirs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from clude_agents import list_agent_specs
from clude_agents.bandit import BanditAgent, RevealedOutcome
from clude_agents.base import mask_and_normalize
from clude_core.domain import ROOMS, SUSPECTS, WEAPONS
from clude_training.self_play import DEFAULT_CHECKPOINTS, generate_snapshots

CATEGORIES = (SUSPECTS, WEAPONS, ROOMS)
EPS = 1e-9
DEFAULT_N_GAMES = 60
DEFAULT_SEED = 4004


@dataclass
class _Accumulator:
    """Running totals for one (agent, checkpoint) pair. Brier is
    accumulated per card (21 per snapshot); log-loss and top-1 are
    accumulated per category (3 per snapshot) -- kept as separate
    counters since they're different units of "one observation."
    """

    brier_sum: float = 0.0
    n_cards: int = 0
    logloss_sum: float = 0.0
    top1_correct: int = 0
    n_categories: int = 0

    def update(self, probabilities: dict, envelope: tuple) -> None:
        for category, truth in zip(CATEGORIES, envelope):
            for c in category:
                target = 1.0 if c == truth else 0.0
                self.brier_sum += (probabilities[c] - target) ** 2
                self.n_cards += 1
            top = max(category, key=lambda c: probabilities[c])
            self.top1_correct += int(top == truth)
            self.logloss_sum += -math.log(max(probabilities[truth], EPS))
            self.n_categories += 1

    @property
    def brier(self) -> float:
        return self.brier_sum / self.n_cards if self.n_cards else float("nan")

    @property
    def log_loss(self) -> float:
        return self.logloss_sum / self.n_categories if self.n_categories else float("nan")

    @property
    def top1_accuracy(self) -> float:
        return self.top1_correct / self.n_categories if self.n_categories else float("nan")


@dataclass
class BenchmarkResult:
    """Per-agent, per-checkpoint accumulators from one `run_benchmark`
    call, plus a `"uniform"` baseline (the deduction floor's own
    mask-uniform belief, no method-specific evidence at all) that every
    real agent should beat -- a sanity floor, not a seventh suspect.

    `agents` holds the actual six agent instances as they ended the run
    (Green's learned posteriors included) -- useful for inspecting
    final state, e.g. which arm Green ended up favoring.
    """

    checkpoints: tuple
    per_agent: dict = field(default_factory=dict)  # name -> {checkpoint: _Accumulator}
    agents: dict = field(default_factory=dict)  # name -> agent instance

    def summary_table(self) -> str:
        header = f"{'agent':<12}{'checkpoint':>11}{'brier':>10}{'log_loss':>10}{'top1_acc':>10}"
        lines = [header, "-" * len(header)]
        for name in sorted(self.per_agent):
            for cp in self.checkpoints:
                acc = self.per_agent[name][cp]
                lines.append(
                    f"{name:<12}{cp:>11.2f}{acc.brier:>10.4f}{acc.log_loss:>10.4f}{acc.top1_accuracy:>10.3f}"
                )
        return "\n".join(lines)


def _uniform_probabilities(obs) -> dict:
    """The deduction floor's own belief with zero method-specific
    evidence -- what every real agent is implicitly competing against.
    """
    return mask_and_normalize({}, obs.mask)


def run_benchmark(
    n_games: int = DEFAULT_N_GAMES,
    seed: int = DEFAULT_SEED,
    checkpoints: tuple = DEFAULT_CHECKPOINTS,
) -> BenchmarkResult:
    """Run all six agents (plus the uniform baseline) over shared
    self-play snapshots and score each one's belief against the
    eventual ground truth.

    Each agent is built once and reused for every snapshot in
    chronological (game, then checkpoint) order -- see module docstring
    for why that matters specifically for Green.
    """
    agents = {spec.name: spec.factory() for spec in list_agent_specs()}
    for agent in agents.values():
        agent.reset(seed)
    green: BanditAgent = agents["Green"]

    names = list(agents) + ["uniform"]
    result = BenchmarkResult(
        checkpoints=checkpoints,
        per_agent={name: {cp: _Accumulator() for cp in checkpoints} for name in names},
        agents=agents,
    )

    for snap in generate_snapshots(n_games, seed, checkpoints=checkpoints):
        result.per_agent["uniform"][snap.checkpoint].update(
            _uniform_probabilities(snap.obs), snap.envelope
        )
        for name, agent in agents.items():
            belief = agent.select_action(snap.obs)
            result.per_agent[name][snap.checkpoint].update(belief.probabilities, snap.envelope)
            if agent is green:
                green.observe(RevealedOutcome(envelope=snap.envelope))

    return result
