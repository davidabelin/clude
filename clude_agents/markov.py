"""White -- Markov model over opponents' suggestion patterns.

Starting point: `legacy/opponent_model.py`'s heuristic ("a player who
repeats a card probably doesn't hold it"), reworked into an actual
first-order Markov chain and its documented-inversion bug fixed (the
legacy README flags `estimated_knowledge` as ambiguous between "knows
where it is" and "probably doesn't hold it" -- this module commits to
one direction, stated below).

For each opponent, encodes their suggestion history as a sequence of
repeat(1)/new(0) symbols -- did this suggestion re-name at least one
card they'd already named before, or was it all new cards -- and fits a
two-state first-order Markov chain to it. A player currently in a
high-P(repeat) regime is read as still fishing for information about
those cards (hasn't been shown them, doesn't hold them), which raises
suspicion toward the *envelope* for cards they keep re-naming without
resolution. This is White's character: he reads suggestion behavior, not
card content -- strong on who's close to solving, weak on the envelope
itself if a player's pattern is atypical (a chatty human, say).

Notes
-----
Recomputes from scratch every call from `obs.suggestion_log`; `reset`/
`observe` are no-ops. Direction of the heuristic (repeats raise, not
lower, suspicion for envelope) is a stated modeling choice, not a
derived fact -- see module docstring above.
"""
from __future__ import annotations

from typing import Any

from clude_agents.base import ClueBelief, SeededAgentMixin, mask_and_normalize
from clude_core.state import ClueObservation

# Laplace-smoothed transition-count prior so a short/empty sequence
# returns the neutral P(repeat) = 0.5 rather than an undefined ratio.
_PRIOR = 1.0


def _stationary_repeat_probability(symbols: list) -> float:
    """First-order Markov chain over a repeat(1)/new(0) symbol sequence;
    returns P(state=1) under the chain's stationary distribution.

    For a 2-state chain with transition probabilities p01 (0->1) and
    p10 (1->0), the stationary probability of state 1 is
    ``p01 / (p01 + p10)`` -- standard detailed-balance result for a
    2-state Markov chain.
    """
    counts = {(0, 0): _PRIOR, (0, 1): _PRIOR, (1, 0): _PRIOR, (1, 1): _PRIOR}
    for a, b in zip(symbols, symbols[1:]):
        counts[(a, b)] += 1
    p01 = counts[(0, 1)] / (counts[(0, 0)] + counts[(0, 1)])
    p10 = counts[(1, 0)] / (counts[(1, 0)] + counts[(1, 1)])
    denom = p01 + p10
    return p01 / denom if denom > 0 else 0.5


class MarkovAgent(SeededAgentMixin):
    """Reads suggestion-repetition patterns per opponent, not card
    content -- strong on people, weak on unusual play."""

    name = "White"

    def select_action(self, obs: ClueObservation) -> ClueBelief:
        """Fit each opponent's repeat/new Markov chain, then weight
        still-unresolved cards they've re-named by that opponent's
        current P(repeat)."""
        assert obs.mask is not None, (
            "select_action requires a masked observation (see clude_constraints.observe)"
        )
        mask = obs.mask
        opponents = [p for p in range(obs.n_players) if p != obs.my_index]
        named_counts: dict = {p: {} for p in opponents}
        symbols: dict = {p: [] for p in opponents}

        for s in obs.suggestion_log:
            p = s.suggester
            if p not in named_counts:
                continue
            cards = s.cards()
            is_repeat = any(named_counts[p].get(c, 0) > 0 for c in cards)
            symbols[p].append(1 if is_repeat else 0)
            for c in cards:
                named_counts[p][c] = named_counts[p].get(c, 0) + 1

        raw: dict = {}
        for p in opponents:
            repeat_prob = _stationary_repeat_probability(symbols[p])
            for c, n in named_counts[p].items():
                if mask.holder_of(c) is not None:
                    continue  # already resolved; nothing left for White to add
                raw[c] = raw.get(c, 0.0) + n * repeat_prob

        return ClueBelief(
            probabilities=mask_and_normalize(raw, mask),
            extra={"named_counts": named_counts},
        )

    def observe(self, transition: Any) -> None:
        """No-op -- see module Notes: nothing incremental to update."""
        return None
