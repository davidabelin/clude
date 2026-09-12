"""Green -- Thompson-sampling bandit ensemble over the other five.

Ports the structure of `rps_agents/heuristic/multi_armed_bandit.py`
almost directly: a Beta(alpha, beta) posterior per arm, decayed each
`observe` call so old evidence fades, with the arm sampled highest this
turn chosen outright (not blended). Here the five arms are literal
instances of the other five methods rather than move-predictor
heuristics, so "the arm sampled highest" means "whichever method's
belief Green trusts most right now" -- opportunistic, hedges, only as
good as his arms.

The arm reward is a *rank* (Phase 5b, docs/phase5-plan.md 4.4): on
each revealed envelope the arm with the lowest log-loss scores 1, the
highest 0, linear in between, ties sharing their mean position. The
Phase 4 reward -- mean probability on the three true cards -- was
dominated by the shared deduction floor, so all five arms scored within
a percent of each other and Thompson sampling picked among them at
random. Ranking compares the arms against each other on the same
snapshot, which is the only thing Green needs to learn.

`random.betavariate` (stdlib) stands in for `numpy.random.beta` so this
package doesn't need to add numpy as a dependency the rest of the repo
doesn't otherwise require.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from clude_agents.base import ClueBelief, SeededAgentMixin
from clude_agents.decision_tree import DecisionTreeAgent
from clude_agents.dempster_shafer import DempsterShaferAgent
from clude_agents.exact_enum import ExactEnumAgent
from clude_agents.markov import MarkovAgent
from clude_agents.naive_bayes import NaiveBayesAgent
from clude_core.state import ClueObservation

EPS = 1e-9


@dataclass
class RevealedOutcome:
    """Minimal ground-truth signal for scoring bandit arms: the solved
    envelope. A placeholder for a fuller `ClueTransition` (see
    docs/architecture.md) -- Green only needs the solution to score arms
    against, not the full transition contract."""

    envelope: tuple


@dataclass
class _Candidate:
    """Beta posterior parameters for one arm."""

    alpha: float = 1.0
    beta: float = 1.0

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)


def _build_arms() -> dict:
    return {
        "Scarlett": NaiveBayesAgent(),
        "Plum": ExactEnumAgent(),
        "Peacock": DempsterShaferAgent(),
        "Mustard": DecisionTreeAgent(),
        "White": MarkovAgent(),
    }


def log_loss(belief: ClueBelief, envelope: tuple) -> float:
    """Summed ``-log P(true card)`` over the three envelope cards, with
    a hard 0 clamped at `EPS` (about 20.7 per category)."""
    return sum(-math.log(max(belief.probabilities.get(card, 0.0), EPS)) for card in envelope)


def rank_rewards(losses: dict) -> dict:
    """Rank reward per arm: 1 for the lowest loss, 0 for the highest,
    linear in rank position; exact ties share the mean of the positions
    they span. A single arm scores 1.

    Parameters
    ----------
    losses : dict[str, float]
        Arm name -> log-loss on this snapshot (lower is better).

    Returns
    -------
    dict[str, float]
    """
    names = sorted(losses, key=lambda n: losses[n])
    n = len(names)
    if n <= 1:
        return {name: 1.0 for name in names}
    rewards: dict = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(losses[names[j + 1]] - losses[names[i]]) < 1e-12:
            j += 1
        mean_position = (i + j) / 2.0
        for k in range(i, j + 1):
            rewards[names[k]] = 1.0 - mean_position / (n - 1)
        i = j + 1
    return rewards


class BanditAgent(SeededAgentMixin):
    """Samples a Beta posterior per arm, plays the highest-sampled arm's
    belief outright, and updates all posteriors once given a solution."""

    name = "Green"

    def __init__(self, step_size: float = 2.0, decay_rate: float = 1.05) -> None:
        super().__init__()
        self.step_size = step_size
        self.decay_rate = decay_rate
        self.arms: dict = {}
        self.candidates: dict = {}
        self._last_predictions: dict = {}
        self._selected: "str | None" = None
        self.reset(None)

    def reset(self, seed) -> None:
        """Reset RNG, rebuild all five arms, and reset every posterior
        to its Beta(1, 1) prior."""
        super().reset(seed)
        self.arms = _build_arms()
        for arm in self.arms.values():
            arm.reset(seed)
        self.candidates = {name: _Candidate() for name in self.arms}
        self._last_predictions = {}
        self._selected = next(iter(self.arms))

    def select_action(self, obs: ClueObservation) -> ClueBelief:
        """Query every arm, sample each arm's Beta posterior, and return
        the belief of whichever arm sampled highest."""
        assert obs.mask is not None, (
            "select_action requires a masked observation (see clude_constraints.observe)"
        )
        best_name, best_value = None, -1.0
        self._last_predictions = {}
        for name, arm in self.arms.items():
            belief = arm.select_action(obs)
            self._last_predictions[name] = belief
            c = self.candidates[name]
            sampled = self.rng.betavariate(c.alpha, c.beta)
            if sampled > best_value:
                best_value, best_name = sampled, name
        self._selected = best_name
        chosen = self._last_predictions[self._selected]
        return ClueBelief(
            probabilities=dict(chosen.probabilities), extra={"selected_arm": self._selected}
        )

    def observe(self, transition: RevealedOutcome) -> None:
        """Rank every arm's most recent prediction by log-loss against
        the revealed envelope and update its Beta posterior with the
        rank reward, after the same decay-toward-prior `rps`'s bandit
        uses so stale evidence fades. Nothing happens if no prediction
        has been made since the last reset."""
        if not self._last_predictions:
            return
        losses = {
            name: log_loss(belief, transition.envelope)
            for name, belief in self._last_predictions.items()
        }
        rewards = rank_rewards(losses)
        for name, reward in rewards.items():
            c = self.candidates[name]
            c.alpha = (c.alpha - 1.0) / self.decay_rate + 1.0
            c.beta = (c.beta - 1.0) / self.decay_rate + 1.0
            c.alpha += self.step_size * reward
            c.beta += self.step_size * (1.0 - reward)
