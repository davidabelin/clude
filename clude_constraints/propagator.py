"""The shared deduction floor: hard logical constraint propagation.

Masks what is still *possible* for every card from one player's point of
view, so that every Phase 3 agent's probabilities can be renormalized over
that surviving set. No agent may ever assign nonzero probability to a card
this has already resolved, or to a holder this has already ruled out --
see docs/architecture.md.

Replaces `legacy/constraints.py`, fixing the five issues its own README
listed: elimination is actually tracked (no more "simplified; track
eliminations in production" stub), the category rule is implemented, hand
sizes are enforced, contradictions raise instead of being silently
dropped, and the envelope holder is the single string `'envelope'`
everywhere.

`possible_holders` is exposed per card rather than collapsed to
known/unknown, since Peacock's Dempster-Shafer method (Phase 3) wants
exactly that mass-assignment-shaped structure. `or_constraints` is exposed
too, separately from `possible_holders`, because per-card marginals lose
the joint "holds at least one of these three" structure that Plum's exact
enumeration (Phase 3) needs to search the true joint posterior correctly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from clude_core.domain import ALL_CARDS, ROOMS, SUSPECTS, WEAPONS, skipped_players
from clude_core.state import ClueObservation

ENVELOPE = "envelope"
Holder = Union[int, str]  # str is always ENVELOPE

CATEGORIES = (SUSPECTS, WEAPONS, ROOMS)


class ConstraintError(ValueError):
    """Raised when observed evidence is logically inconsistent -- a bug in
    the caller (e.g. mismatched turn order) rather than a normal game
    outcome, since real suggestion/refutation evidence is never
    contradictory."""


@dataclass(frozen=True)
class ConstraintResult:
    """The output of `propagate`: what's still logically possible."""

    possible_holders: dict[str, frozenset[Holder]]
    or_constraints: tuple[tuple[frozenset[str], int], ...]
    hand_sizes: dict[int, int]

    def holder_of(self, card: str) -> Holder | None:
        """The card's holder, if fully resolved; otherwise None."""
        holders = self.possible_holders[card]
        return next(iter(holders)) if len(holders) == 1 else None

    def is_possible(self, card: str, holder: Holder) -> bool:
        return holder in self.possible_holders[card]

    def solution(self) -> tuple[str, str, str] | None:
        """(suspect, weapon, room) if all three are proven; else None."""
        s = next((c for c in SUSPECTS if self.holder_of(c) == ENVELOPE), None)
        w = next((c for c in WEAPONS if self.holder_of(c) == ENVELOPE), None)
        r = next((c for c in ROOMS if self.holder_of(c) == ENVELOPE), None)
        return (s, w, r) if s and w and r else None


class _Working:
    """Mutable fixpoint-propagation state. Internal to this module --
    callers only ever see the frozen `ConstraintResult`."""

    def __init__(self, n_players: int, hand_sizes: dict[int, int]):
        self.n_players = n_players
        self.hand_sizes = hand_sizes
        holders: set[Holder] = set(range(n_players)) | {ENVELOPE}
        self.holders: dict[str, set[Holder]] = {c: set(holders) for c in ALL_CARDS}
        self.or_constraints: list[tuple[frozenset[str], int]] = []

    def assign(self, card: str, holder: Holder) -> bool:
        if holder not in self.holders[card]:
            raise ConstraintError(f"{card} cannot belong to {holder}: already ruled out")
        if self.holders[card] == {holder}:
            return False
        self.holders[card] = {holder}
        return True

    def eliminate(self, card: str, holder: Holder) -> bool:
        if holder not in self.holders[card]:
            return False
        self.holders[card] = self.holders[card] - {holder}
        if not self.holders[card]:
            raise ConstraintError(f"no possible holder remains for {card}")
        return True

    def propagate(self) -> None:
        changed = True
        while changed:
            changed = False
            changed |= self._propagate_or_constraints()
            changed |= self._propagate_category_rule()
            changed |= self._propagate_hand_sizes()

    def _propagate_or_constraints(self) -> bool:
        changed = False
        still_open = []
        for cards, holder in self.or_constraints:
            remaining = frozenset(c for c in cards if holder in self.holders[c])
            if not remaining:
                raise ConstraintError(
                    f"player {holder} must hold one of {sorted(cards)}, but none remain possible"
                )
            if remaining != cards:
                changed = True
            if len(remaining) == 1:
                if self.assign(next(iter(remaining)), holder):
                    changed = True
            else:
                still_open.append((remaining, holder))
        self.or_constraints = still_open
        return changed

    def _propagate_category_rule(self) -> bool:
        """Exactly one card per category is the envelope's."""
        changed = False
        for category in CATEGORIES:
            envelope_card = next((c for c in category if self.holders[c] == {ENVELOPE}), None)
            if envelope_card is not None:
                for c in category:
                    if c != envelope_card and self.eliminate(c, ENVELOPE):
                        changed = True
            else:
                candidates = [c for c in category if ENVELOPE in self.holders[c]]
                if len(candidates) == 1 and self.assign(candidates[0], ENVELOPE):
                    changed = True
        return changed

    def _propagate_hand_sizes(self) -> bool:
        """A player who has hit their hand size can't hold anything else."""
        changed = False
        for p in range(self.n_players):
            assigned = [c for c in ALL_CARDS if self.holders[c] == {p}]
            if len(assigned) > self.hand_sizes[p]:
                raise ConstraintError(f"player {p} assigned more cards than their hand size")
            if len(assigned) == self.hand_sizes[p]:
                for c in ALL_CARDS:
                    if self.holders[c] != {p} and self.eliminate(c, p):
                        changed = True
        return changed


def propagate(obs: ClueObservation) -> ConstraintResult:
    """Run the deduction floor over one player's observation.

    Recomputed from scratch every call -- cheap (21 cards, a handful of
    suggestions) and it means no agent can ever act on a stale mask.
    """
    working = _Working(obs.n_players, obs.hand_sizes)

    for card in obs.own_hand:
        working.assign(card, obs.my_index)

    for suggestion in obs.suggestion_log:
        cards = frozenset(suggestion.cards())
        for p in skipped_players(obs.n_players, suggestion.suggester, suggestion.refuter):
            for card in cards:
                working.eliminate(card, p)

        if suggestion.refuter is not None:
            if suggestion.card_shown is not None:
                working.assign(suggestion.card_shown, suggestion.refuter)
            else:
                remaining = frozenset(c for c in cards if suggestion.refuter in working.holders[c])
                if remaining:
                    working.or_constraints.append((remaining, suggestion.refuter))

    working.propagate()

    return ConstraintResult(
        possible_holders={c: frozenset(h) for c, h in working.holders.items()},
        or_constraints=tuple(working.or_constraints),
        hand_sizes=dict(obs.hand_sizes),
    )
