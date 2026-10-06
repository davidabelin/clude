"""Omniscient event types used by the engine, records and replay.

ClueObservation redacts private shown cards for each viewer. RemarkEvent is
public table talk with no game effect, including off-turn chat.
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
    """Public table talk with no rules effect.

    about identifies the accompanying move/suggest/accuse/show decision or
    off-turn chat/reaction. Nothing in the engine interprets text as evidence.
    """

    turn: int
    seat: int
    text: str
    about: str


GameEvent = Union[MoveEvent, SuggestionEvent, AccusationEvent, GameOverEvent, RemarkEvent]
