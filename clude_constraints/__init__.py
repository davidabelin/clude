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
    """Build `viewer`'s `ClueObservation` with a freshly computed `mask`.

    `ClueObservation.for_player` (in `clude_core`, which knows nothing
    about this package -- see its docstring) builds every field except
    `mask`. This is the one place that attaches it, so every Phase 3+
    agent that receives an observation through here can trust `mask` is
    present and fresh. Pass this as `run_game`'s `observer` to drive a
    live game with players that need the floor (`FloorBot`, Phase 5's
    characters).
    """
    obs = ClueObservation.for_player(state, viewer)
    return replace(obs, mask=propagate(obs))
