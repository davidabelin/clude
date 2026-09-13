"""Event log types.

Every engine action appends one of these. The log is the single source of
truth for building each player's `ClueObservation` (state.py) and, later,
for post-game replay of all six belief traces (see docs/architecture.md).
Some fields are private to specific players; `ClueObservation` is
responsible for redacting them, not this module. `RemarkEvent` (Phase 6)
is the one kind with no game effect: a line of table talk, public to
every seat, kept in order with the actions it accompanied.
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


@dataclass(frozen=True)
class RemarkEvent:
    """One line of table talk from `seat`, appended by the engine right
    after the decision it accompanied (Phase 6). `about` names that
    decision: ``"move"``, ``"suggest"``, ``"accuse"`` (also when the
    seat chose not to accuse) or ``"show"`` (said while refuting). Phase
    8's off-turn chat is meant to reuse this type with new `about`
    values. Nothing in the engine reads or acts on `text`."""

    turn: int
    seat: int
    text: str
    about: str


GameEvent = Union[MoveEvent, SuggestionEvent, AccusationEvent, GameOverEvent, RemarkEvent]
