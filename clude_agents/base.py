"""Shared agent contract: `ClueBelief`, the masking/renormalization
helper every method funnels its raw evidence through, and a seeded-RNG
mixin. Mirrors `rps_agents/base.py` and
`rps_agents/heuristic/common.RNGMixin`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Any, Protocol

from clude_constraints import ENVELOPE, ConstraintResult
from clude_core.domain import ROOMS, SUSPECTS, WEAPONS
from clude_core.engine import MoveChoice
from clude_core.state import ClueObservation

from .features import pick_destination
from .personality import Profile

CATEGORIES: tuple[list[str], ...] = (SUSPECTS, WEAPONS, ROOMS)


@dataclass(frozen=True)
class ClueBelief:
    """One agent's masked, renormalized belief over the envelope.

    Parameters
    ----------
    probabilities : dict[str, float]
        P(card is the envelope's) for all 21 cards. Sums to 1.0 within
        each of the three categories (suspects/weapons/rooms) separately
        -- never across categories, since "the envelope's suspect card"
        and "the envelope's weapon card" are independent questions.
    extra : dict[str, Any]
        Agent-specific auxiliary output that doesn't fit the common
        probabilities shape (Peacock's raw belief/plausibility bounds,
        Green's selected arm, ...). Empty for agents with nothing extra
        to report.
    """

    probabilities: dict[str, float]
    extra: dict[str, Any] = field(default_factory=dict)


class AgentProtocol(Protocol):
    """Same shape as `rps_agents/base.py`, phase-scoped per
    docs/architecture.md: `select_action` returns a belief only, never
    a chosen game action -- `clude_agents.character.Character` turns
    that belief plus a `Profile` into the engine's four decisions.
    `choose_destination` is the one decision the protocol itself owns,
    so a method can reason about rooms its own way; the shared default
    lives on `SeededAgentMixin`.
    """

    name: str

    def reset(self, seed: "int | None") -> None: ...

    def select_action(self, obs: ClueObservation) -> ClueBelief:
        """Return this agent's belief over the 21 cards, already masked
        and renormalized against `obs.mask` (see `mask_and_normalize`)."""
        ...

    def choose_destination(
        self, obs: ClueObservation, legal_moves: list, room_features: list, profile: Profile
    ) -> MoveChoice:
        """Pick where to move this turn. `room_features` is
        `clude_agents.features.room_features(obs, belief, legal_moves)`
        -- shared arithmetic; the pick is this agent's own. `profile`
        supplies the character's `curiosity` and `temperature`."""
        ...

    def observe(self, transition: Any) -> None: ...


class SeededAgentMixin:
    """Deterministic RNG plumbing for methods that need one (sampling
    fallbacks, Thompson sampling, tie-breaking), plus the default room
    choice. Mirrors `rps_agents.heuristic.common.RNGMixin`.
    """

    def __init__(self) -> None:
        self.rng = Random()

    def reset(self, seed: "int | None") -> None:
        self.rng.seed(seed)

    def choose_destination(
        self, obs: ClueObservation, legal_moves: list, room_features: list, profile: Profile
    ) -> MoveChoice:
        """Default: softmax over the profile's curiosity-weighted blend of
        each choice's information and proximity (`features.pick_destination`),
        drawn from this agent's own RNG. Override per method for a
        different room policy."""
        del obs, legal_moves  # the features already cover every legal move
        return pick_destination(room_features, profile, self.rng)


def mask_and_normalize(
    raw_scores: dict[str, float], mask: ConstraintResult
) -> dict[str, float]:
    """Turn arbitrary non-negative per-card scores into the shared
    `ClueBelief.probabilities` contract.

    A card the deduction floor has already ruled out as the envelope's
    gets probability exactly 0; a card it has already proven gets
    exactly 1. Everything else is renormalized to sum to 1 within its
    category over what's still logically possible -- no agent may ever
    assign nonzero probability to a card the floor has eliminated (see
    `clude_constraints.propagator`'s module docstring).

    Parameters
    ----------
    raw_scores : dict[str, float]
        Unnormalized, non-negative evidence per card from the calling
        agent's own method. A missing key is treated as 0. Negative
        values are clamped to 0 -- evidence *against* a card is
        expressed by giving it a low score, not a negative one.
    mask : ConstraintResult
        The shared deduction floor's output for this observation.

    Returns
    -------
    dict[str, float]
        Probabilities for all 21 cards, summing to 1.0 within each
        category.

    Notes
    -----
    If every surviving candidate in a category has zero raw score (the
    agent's method had no opinion), probability is spread uniformly over
    the surviving candidates rather than left undefined.
    """
    result: dict[str, float] = {}
    for category in CATEGORIES:
        resolved = next((c for c in category if mask.holder_of(c) == ENVELOPE), None)
        if resolved is not None:
            for c in category:
                result[c] = 1.0 if c == resolved else 0.0
            continue
        possible = [c for c in category if mask.is_possible(c, ENVELOPE)]
        scores = {c: max(raw_scores.get(c, 0.0), 0.0) for c in possible}
        total = sum(scores.values())
        for c in category:
            if c not in possible:
                result[c] = 0.0
            elif total > 0:
                result[c] = scores[c] / total
            else:
                result[c] = 1.0 / len(possible)
    return result
