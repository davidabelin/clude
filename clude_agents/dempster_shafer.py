"""Peacock -- Dempster-Shafer belief/plausibility.

Built fresh (no legacy basis). Per category (suspects/weapons/rooms),
maintains a mass function over subsets of still-possible envelope
candidates, combines evidence via Dempster's rule, and reports both
Belief (mass on that card alone) and Plausibility (mass on any subset
containing it) in `ClueBelief.extra` -- the two-tone belief/plausibility
bar from the visual design notes (`CLAUDE.md`) is literally this pair.
`ClueBelief.probabilities` itself is the pignistic transform (BetP),
which always lies within [Belief, Plausibility] for every card and is
what the rest of the system treats as "the" probability.

Notes
-----
Evidence source: `mask.or_constraints` (a holder holds at least one of a
set of cards spanning up to all three categories -- exactly a
Dempster-Shafer-shaped fact, and exactly why the deduction floor exposes
it separately from per-card marginals; see docs/architecture.md). Each
constraint's "holder holds >= 1 of these" burden is apportioned across
the categories it touches in proportion to how many of its cards fall in
that category -- a stated modeling choice, not a theorem, since the true
per-category split would require knowing which specific card the holder
actually has. This is Peacock's honest-but-approximate DS, matching her
cautious-until-forced character rather than a from-the-literature-exact
implementation.

Recomputes from scratch every call; `reset`/`observe` are no-ops.
"""
from __future__ import annotations

from typing import Any

from clude_agents.base import CATEGORIES, ClueBelief, SeededAgentMixin, mask_and_normalize
from clude_constraints import ENVELOPE, ConstraintResult
from clude_core.state import ClueObservation

Focal = frozenset
MassFunction = dict  # dict[Focal, float]


def _combine(m1: MassFunction, m2: MassFunction) -> MassFunction:
    """Dempster's combination rule: renormalize the product measure over
    conflicting (empty-intersection) focal-set pairs."""
    combined: dict = {}
    conflict = 0.0
    for a, ma in m1.items():
        for b, mb in m2.items():
            inter = a & b
            if not inter:
                conflict += ma * mb
            else:
                combined[inter] = combined.get(inter, 0.0) + ma * mb
    normalizer = 1.0 - conflict
    if normalizer <= 1e-12:
        # Total contradiction between two mass functions shouldn't arise
        # from evidence the sound deduction floor already accepted; fall
        # back to the second function rather than divide by zero.
        return dict(m2)
    return {focal: mass / normalizer for focal, mass in combined.items()}


def _category_mass(category: list, mask: ConstraintResult) -> "tuple[MassFunction, frozenset]":
    possible = frozenset(c for c in category if mask.is_possible(c, ENVELOPE))
    m: MassFunction = {possible: 1.0}
    for cards, _holder in mask.or_constraints:
        cat_cards = frozenset(cards) & possible
        if not cat_cards:
            continue
        complement = possible - cat_cards
        if not complement:
            continue
        share = len(cat_cards) / len(cards)
        m = _combine(m, {complement: share, possible: 1.0 - share})
    return m, possible


def _belief(m: MassFunction, card: str) -> float:
    return sum(mass for focal, mass in m.items() if focal == frozenset({card}))


def _plausibility(m: MassFunction, card: str) -> float:
    return sum(mass for focal, mass in m.items() if card in focal)


def _pignistic(m: MassFunction, possible: frozenset) -> dict:
    """BetP: each focal set's mass split evenly among its members."""
    bet = {c: 0.0 for c in possible}
    for focal, mass in m.items():
        if not focal:
            continue
        share = mass / len(focal)
        for c in focal:
            bet[c] += share
    return bet


class DempsterShaferAgent(SeededAgentMixin):
    """Won't commit until plausibility collapses toward belief."""

    name = "Peacock"

    def select_action(self, obs: ClueObservation) -> ClueBelief:
        """Combine or-constraint evidence into a per-category mass
        function and report BetP as the probability, Belief/Plausibility
        bounds alongside it."""
        assert obs.mask is not None, (
            "select_action requires a masked observation (see clude_constraints.observe)"
        )
        mask = obs.mask
        raw: dict = {}
        belief_bounds: dict = {}
        plausibility_bounds: dict = {}
        for category in CATEGORIES:
            m, possible = _category_mass(category, mask)
            bet = _pignistic(m, possible)
            for c in possible:
                raw[c] = bet[c]
                belief_bounds[c] = _belief(m, c)
                plausibility_bounds[c] = _plausibility(m, c)
        probabilities = mask_and_normalize(raw, mask)
        return ClueBelief(
            probabilities=probabilities,
            extra={"belief": belief_bounds, "plausibility": plausibility_bounds},
        )

    def observe(self, transition: Any) -> None:
        """No-op -- see module Notes: nothing incremental to update."""
        return None
