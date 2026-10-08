"""JSON codecs and omniscient GameRecord/SeatRecord documents.

Records hold deal, events, seats/profiles, outcome and optional model audit/
costs. Never expose them directly to a live player. Version 3 is the Classic
grid; versions 1/2 retain ring-node decoding. Optional added fields default
when missing, preserving old records. Logbook documents reference games
rather than changing their schema. See docs/architecture.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from clude_core.board import HallwayCell, Square
from clude_core.domain import Accusation, Suggestion
from clude_core.events import (
    AccusationEvent,
    GameEvent,
    GameOverEvent,
    MoveEvent,
    RemarkEvent,
    SuggestionEvent,
)
from clude_core.state import GameState

RECORD_VERSION = 3
#: The first version written on the Classic grid; older records are ring-era.
GRID_RECORD_VERSION = 3

DEVELOPMENT_PHASE = 2
"""The ``phase`` a development run summary is stamped with when stored:
2 since the new Plum (Phase 12, 2026-10-07). A summary without one is
phase 1; the lobby files runs by it."""


def node_to_json(node):
    """A room name as-is; a `Square` as ``{row, col}``; a legacy
    `HallwayCell` (only ever read back from a version-1 or -2 record)
    as ``{room_a, room_b, k}``."""
    if isinstance(node, str):
        return node
    if isinstance(node, Square):
        return {"row": node.row, "col": node.col}
    return {"room_a": node.room_a, "room_b": node.room_b, "k": node.k}


def node_from_json(data):
    """Inverse of `node_to_json`. A ring-era cell loads as the legacy
    `HallwayCell`, so a stored ring game still replays with its
    positions (`clude_training.replay`)."""
    if isinstance(data, str):
        return data
    if "row" in data:
        return Square(int(data["row"]), int(data["col"]))
    return HallwayCell(data["room_a"], data["room_b"], int(data["k"]))


def _suggestion_to_json(s: Suggestion) -> dict:
    return {
        "suggester": s.suggester,
        "suspect": s.suspect,
        "weapon": s.weapon,
        "room": s.room,
        "refuter": s.refuter,
        "shown_to": s.shown_to,
        "card_shown": s.card_shown,
    }


def _suggestion_from_json(data: dict) -> Suggestion:
    return Suggestion(
        suggester=int(data["suggester"]),
        suspect=data["suspect"],
        weapon=data["weapon"],
        room=data["room"],
        refuter=None if data.get("refuter") is None else int(data["refuter"]),
        shown_to=int(data["shown_to"]),
        card_shown=data.get("card_shown"),
    )


def _accusation_to_json(a: Accusation) -> dict:
    return {
        "accuser": a.accuser,
        "suspect": a.suspect,
        "weapon": a.weapon,
        "room": a.room,
        "correct": a.correct,
    }


def _accusation_from_json(data: dict) -> Accusation:
    return Accusation(
        accuser=int(data["accuser"]),
        suspect=data["suspect"],
        weapon=data["weapon"],
        room=data["room"],
        correct=bool(data["correct"]),
    )


def event_to_json(event: GameEvent) -> dict:
    """One event as a JSON object with a ``type`` tag: ``move``,
    ``suggestion``, ``accusation``, ``game_over`` or ``remark``.

    Raises
    ------
    TypeError
        For an object that is not one of the five event types.
    """
    if isinstance(event, MoveEvent):
        return {
            "type": "move",
            "turn": event.turn,
            "player": event.player,
            "destination": node_to_json(event.destination),
            "used_secret_passage": event.used_secret_passage,
        }
    if isinstance(event, SuggestionEvent):
        return {"type": "suggestion", "turn": event.turn, **_suggestion_to_json(event.suggestion)}
    if isinstance(event, AccusationEvent):
        return {"type": "accusation", "turn": event.turn, **_accusation_to_json(event.accusation)}
    if isinstance(event, GameOverEvent):
        return {
            "type": "game_over",
            "turn": event.turn,
            "winner": event.winner,
            "solution": list(event.solution),
        }
    if isinstance(event, RemarkEvent):
        return {
            "type": "remark",
            "turn": event.turn,
            "seat": event.seat,
            "text": event.text,
            "about": event.about,
        }
    raise TypeError(f"not a game event: {event!r}")


def event_from_json(data: dict) -> GameEvent:
    """Inverse of `event_to_json`.

    Raises
    ------
    ValueError
        On an unknown ``type`` tag.
    """
    kind = data.get("type")
    turn = int(data["turn"])
    if kind == "move":
        return MoveEvent(
            turn, int(data["player"]), node_from_json(data["destination"]),
            bool(data.get("used_secret_passage", False)),
        )
    if kind == "suggestion":
        return SuggestionEvent(turn, _suggestion_from_json(data))
    if kind == "accusation":
        return AccusationEvent(turn, _accusation_from_json(data))
    if kind == "game_over":
        winner = data.get("winner")
        return GameOverEvent(turn, None if winner is None else int(winner), tuple(data["solution"]))
    if kind == "remark":
        return RemarkEvent(turn, int(data["seat"]), str(data["text"]), str(data["about"]))
    raise ValueError(f"unknown event type {kind!r}")


@dataclass(frozen=True)
class SeatRecord:
    """Who occupied one seat for one game.

    Parameters
    ----------
    seat : int
        Seat index (turn order; seat 0 moves first).
    suspect : str
        The suspect token in that seat (`GameState.suspects_in_play`).
    label : str
        Roster label: a character name or a bot kind (``"floor"``).
    kind : str
        ``"character"``, ``"llm"`` (an LLM piloting a character, Phase 6),
        ``"floor"``, ``"random"`` or ``"human"`` (a person, labelled by
        their account key, Phase 8.2).
    profile : dict or None
        The character's `Profile.to_dict()` at play time; None for bots.
    model : str or None
        The model id behind an ``"llm"`` seat; None otherwise.
    cost : float or None
        Dollars this seat's model spent on the game, its logbook entry
        included; None for a seat with no model, and for a
        game recorded before costs were.
    """

    seat: int
    suspect: str
    label: str
    kind: str
    profile: Optional[dict] = None
    model: Optional[str] = None
    cost: Optional[float] = None

    def to_dict(self) -> dict:
        out = {
            "seat": self.seat,
            "suspect": self.suspect,
            "label": self.label,
            "kind": self.kind,
            "profile": self.profile,
            "model": self.model,
        }
        if self.cost is not None:
            out["cost"] = self.cost
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "SeatRecord":
        return cls(
            seat=int(data["seat"]),
            suspect=data["suspect"],
            label=data["label"],
            kind=data["kind"],
            profile=data.get("profile"),
            model=data.get("model"),
            cost=None if data.get("cost") is None else float(data["cost"]),
        )


@dataclass
class GameRecord:
    """One finished game, omniscient (see module docstring).

    Parameters
    ----------
    run_id : str
        The arena run this game belongs to.
    game_index : int
        0-based index within the run.
    seed : int
        The engine seed that produced the deal and dice.
    n_players : int
    seats : list[SeatRecord]
    envelope : tuple[str, str, str]
    hands : dict[int, list[str]]
        Seat -> sorted cards.
    events : list[GameEvent]
        The full event log, in order, ending with `GameOverEvent`.
    winner : int or None
    turns : int
    n_suggestions, n_accusations : int
    llm_log : dict or None
        Seat -> that seat's LLM decision audit, a list of
        `clude_llm.Decision.to_dict()` objects; None when no
        seat was LLM-piloted.
    created_at : str
        ISO-8601 UTC timestamp of when the record was built.
    version : int
        `RECORD_VERSION`, for future schema changes.
    cost : float or None
        Dollars the game's model seats spent, at list prices, their
        logbook entries included; None for a game with no
        model seat, and for one recorded before costs were.
    """

    run_id: str
    game_index: int
    seed: int
    n_players: int
    seats: list
    envelope: tuple
    hands: dict
    events: list
    winner: Optional[int]
    turns: int
    n_suggestions: int
    n_accusations: int
    llm_log: Optional[dict] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: int = RECORD_VERSION
    cost: Optional[float] = None

    @classmethod
    def from_game(
        cls, run_id: str, game_index: int, seed: int, state: GameState, events: list, seats: list,
        llm_log: Optional[dict] = None,
    ) -> "GameRecord":
        """Build a record from a finished `engine.run_game` result."""
        final = events[-1] if events else None
        winner = final.winner if isinstance(final, GameOverEvent) else None
        return cls(
            run_id=run_id,
            game_index=game_index,
            seed=seed,
            n_players=state.n_players,
            seats=list(seats),
            envelope=tuple(state.envelope),
            hands={p: sorted(h) for p, h in state.hands.items()},
            events=list(events),
            winner=winner,
            turns=state.turn,
            n_suggestions=len(state.suggestion_log),
            n_accusations=len(state.accusation_log),
            llm_log=llm_log,
        )

    def to_dict(self) -> dict:
        """JSON-ready copy (hand keys become strings, events are tagged
        objects). ``cost`` is written last, and only when it is set."""
        out = {
            "version": self.version,
            "run_id": self.run_id,
            "game_index": self.game_index,
            "seed": self.seed,
            "n_players": self.n_players,
            "seats": [s.to_dict() for s in self.seats],
            "envelope": list(self.envelope),
            "hands": {str(p): list(cards) for p, cards in self.hands.items()},
            "events": [event_to_json(e) for e in self.events],
            "winner": self.winner,
            "turns": self.turns,
            "n_suggestions": self.n_suggestions,
            "n_accusations": self.n_accusations,
            "llm_log": (
                None if self.llm_log is None
                else {str(seat): log for seat, log in self.llm_log.items()}
            ),
            "created_at": self.created_at,
        }
        if self.cost is not None:
            out["cost"] = self.cost
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "GameRecord":
        """Inverse of `to_dict`. Accepts every `RECORD_VERSION` so far."""
        return cls(
            run_id=data["run_id"],
            game_index=int(data["game_index"]),
            seed=int(data["seed"]),
            n_players=int(data["n_players"]),
            seats=[SeatRecord.from_dict(s) for s in data.get("seats", [])],
            envelope=tuple(data["envelope"]),
            hands={int(p): list(cards) for p, cards in data.get("hands", {}).items()},
            events=[event_from_json(e) for e in data.get("events", [])],
            winner=None if data.get("winner") is None else int(data["winner"]),
            turns=int(data["turns"]),
            n_suggestions=int(data["n_suggestions"]),
            n_accusations=int(data["n_accusations"]),
            llm_log=(
                None if data.get("llm_log") is None
                else {int(seat): log for seat, log in data["llm_log"].items()}
            ),
            created_at=data.get("created_at", ""),
            version=int(data.get("version", RECORD_VERSION)),
            cost=None if data.get("cost") is None else float(data["cost"]),
        )
