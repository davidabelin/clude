"""The shared deduction floor. See propagator.py."""
from __future__ import annotations

from dataclasses import replace

from clude_core.state import ClueObservation, GameState

from .propagator import ENVELOPE, ConstraintError, ConstraintResult, Holder, propagate

__all__ = [
    "ENVELOPE",
    "ConstraintError",
    "ConstraintResult",
    "Holder",
    "propagate",
    "observe",
]


def observe(state: GameState, viewer: int) -> ClueObservation:
    """Build `viewer`'s `ClueObservation` with a freshly computed `mask`.

    `ClueObservation.for_player` (in `clude_core`, which knows nothing
    about this package -- see its docstring) builds every field except
    `mask`. This is the one place that attaches it, so every Phase 3+
    agent that receives an observation through here can trust `mask` is
    present and fresh.
    """
    obs = ClueObservation.for_player(state, viewer)
    return replace(obs, mask=propagate(obs))
