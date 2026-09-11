"""Event log types.

Every engine action appends one of these. The log is the single source of
truth for building each player's `ClueObservation` (state.py) and, later,
for post-game replay of all six belief traces (see docs/architecture.md).
Some fields are private to specific players; `ClueObservation` is
responsible for redacting them, not this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from .board import Node
from .domain import Accusation, Suggestion


@dataclass(frozen=True)
class MoveEvent:
    turn: int
    player: int
    destination: Node
    used_secret_passage: bool = False


@dataclass(frozen=True)
class SuggestionEvent:
    turn: int
    suggestion: Suggestion


@dataclass(frozen=True)
class AccusationEvent:
    turn: int
    accusation: Accusation


@dataclass(frozen=True)
class GameOverEvent:
    turn: int
    winner: Optional[int]  # None if every player accused incorrectly
    solution: tuple[str, str, str]


GameEvent = Union[MoveEvent, SuggestionEvent, AccusationEvent, GameOverEvent]
