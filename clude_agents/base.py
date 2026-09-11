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
from clude_core.state import ClueObservation

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
    docs/architecture.md: through Phase 4 `select_action` returns a
    belief only, never a chosen game action. `choose_destination` is a
    Phase 5 slot, reserved now so this protocol doesn't need a breaking
    change later -- see `SeededAgentMixin.choose_destination`.
    """

    name: str

    def reset(self, seed: "int | None") -> None: ...

    def select_action(self, obs: ClueObservation) -> ClueBelief:
        """Return this agent's belief over the 21 cards, already masked
        and renormalized against `obs.mask` (see `mask_and_normalize`)."""
        ...

    def observe(self, transition: Any) -> None: ...


class SeededAgentMixin:
    """Deterministic RNG plumbing for methods that need one (sampling
    fallbacks, Thompson sampling, tie-breaking). Mirrors
    `rps_agents.heuristic.common.RNGMixin`.
    """

    def __init__(self) -> None:
        self.rng = Random()

    def reset(self, seed: "int | None") -> None:
        self.rng.seed(seed)

    def choose_destination(self, obs, legal_moves, room_features):
        """Phase 5 slot (see docs/architecture.md's room/suggestion
        target-selection note) -- not implemented until the personality
        layer exists to drive it."""
        raise NotImplementedError("room/destination choice is Phase 5")


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
