"""The shared deduction floor. See propagator.py, and floor_bot.py for
the dumb player that acts on the floor alone."""
from __future__ import annotations

from dataclasses import replace

from clude_core.state import ClueObservation, GameState

from .floor_bot import FloorBot
from .propagator import ENVELOPE, ConstraintError, ConstraintResult, Holder, propagate

__all__ = [
    "ENVELOPE",
    "ConstraintError",
    "ConstraintResult",
    "FloorBot",
    "Holder",
    "propagate",
    "observe",
]


def observe(state: GameState, viewer: int) -> ClueObservation:
    """Build viewer's redacted observation and attach freshly propagated mask.

    Pass this as the engine observer for FloorBot and numerical characters.
    The core factory itself supplies no mask, avoiding an import cycle.
    """
    obs = ClueObservation.for_player(state, viewer)
    return replace(obs, mask=propagate(obs))
