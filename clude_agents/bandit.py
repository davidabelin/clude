"""Green -- Thompson-sampling bandit ensemble over the other five.

Ports the structure of `rps_agents/heuristic/multi_armed_bandit.py`
almost directly: a Beta(alpha, beta) posterior per arm, decayed each
`observe` call so old evidence fades, with the arm sampled highest this
turn chosen outright (not blended). Here the five arms are literal
instances of the other five methods rather than move-predictor
heuristics, so "the arm sampled highest" means "whichever method's
belief Green trusts most right now" -- opportunistic, hedges, only as
good as his arms.

`random.betavariate` (stdlib) stands in for `numpy.random.beta` so this
package doesn't need to add numpy as a dependency the rest of the repo
doesn't otherwise require.
"""
from __future__ import annotations

from dataclasses import dataclass

from clude_agents.base import ClueBelief, SeededAgentMixin
from clude_agents.decision_tree import DecisionTreeAgent
from clude_agents.dempster_shafer import DempsterShaferAgent
from clude_agents.exact_enum import ExactEnumAgent
from clude_agents.markov import MarkovAgent
from clude_agents.naive_bayes import NaiveBayesAgent
from clude_core.state import ClueObservation


@dataclass
class RevealedOutcome:
    """Minimal ground-truth signal for scoring bandit arms: the solved
    envelope. A placeholder for Phase 4's real `ClueTransition` (see
    docs/architecture.md) -- Green only needs the solution to score arms
    against, not the full transition contract."""

    envelope: tuple


@dataclass
class _Candidate:
    """Beta posterior parameters for one arm."""

    alpha: float = 1.0
    beta: float = 1.0


def _build_arms() -> dict:
    return {
        "Scarlett": NaiveBayesAgent(),
        "Plum": ExactEnumAgent(),
        "Peacock": DempsterShaferAgent(),
        "Mustard": DecisionTreeAgent(),
        "White": MarkovAgent(),
    }


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
        """Score every arm's most recent prediction against the revealed
        envelope and update its Beta posterior, with the same
        decay-toward-prior `rps`'s bandit uses so stale evidence fades.
        """
        for name, belief in self._last_predictions.items():
            c = self.candidates[name]
            c.alpha = (c.alpha - 1.0) / self.decay_rate + 1.0
            c.beta = (c.beta - 1.0) / self.decay_rate + 1.0
            score = sum(belief.probabilities.get(card, 0.0) for card in transition.envelope) / 3.0
            c.alpha += self.step_size * score
            c.beta += self.step_size * (1.0 - score)
