"""Headless rules engine: setup, movement, suggestion/refutation,
accusation, and the turn loop. No inference, no LLM -- Phase 1 scope only
(see docs/phase-plan.md).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional, Protocol

from . import board
from .board import Node
from .domain import ALL_CARDS, Accusation, ROOMS, Suggestion, SUSPECTS, WEAPONS, players_after
from .events import AccusationEvent, GameEvent, GameOverEvent, MoveEvent, SuggestionEvent
from .state import GameState

MIN_PLAYERS = 3
MAX_PLAYERS = 6


@dataclass(frozen=True)
class MoveChoice:
    """One legal movement option for a turn.

    `kind` is one of ``"stay"`` (only offered while in a room), ``"secret_
    passage"`` (only offered in a room that has one; `destination` is the
    connected room), or ``"move"`` (`destination` is a reachable node).
    """

    kind: str
    destination: Optional[Node] = None


class RandomBotProtocol(Protocol):
    """The decision interface Phase 1's dumb bots implement. Not
    `AgentProtocol` -- that's introduced in Phase 3 once agents have
    beliefs to act on (see docs/architecture.md)."""

    def choose_movement(self, choices: list[MoveChoice], rng: random.Random) -> MoveChoice: ...

    def choose_suggestion(
        self, room: str, own_hand: frozenset[str], rng: random.Random
    ) -> Optional[tuple[str, str]]: ...

    def choose_accusation(
        self, rng: random.Random
    ) -> Optional[tuple[str, str, str]]: ...

    def choose_card_to_show(self, candidates: list[str], rng: random.Random) -> str: ...


def setup(n_players: int, rng: random.Random) -> GameState:
    """Deal a new game: pick the envelope, deal the rest round-robin, and
    place each in-play suspect's token at its starting hallway cell."""
    if not (MIN_PLAYERS <= n_players <= MAX_PLAYERS):
        raise ValueError(f"Clue supports {MIN_PLAYERS}-{MAX_PLAYERS} players")

    suspects_in_play = SUSPECTS[:n_players]
    envelope = (rng.choice(SUSPECTS), rng.choice(WEAPONS), rng.choice(ROOMS))
    remaining = [c for c in ALL_CARDS if c not in envelope]
    rng.shuffle(remaining)

    hands: dict[int, set[str]] = {p: set() for p in range(n_players)}
    for i, card in enumerate(remaining):
        hands[i % n_players].add(card)

    positions = {p: board.start_position(suspects_in_play[p]) for p in range(n_players)}

    return GameState(
        suspects_in_play=suspects_in_play,
        hands={p: frozenset(h) for p, h in hands.items()},
        envelope=envelope,
        positions=positions,
        active=[True] * n_players,
    )


def legal_moves(state: GameState, player: int, roll: int) -> list[MoveChoice]:
    """Every legal movement option for `player` given this turn's roll."""
    pos = state.positions[player]
    room = board.room_of(pos)
    choices: list[MoveChoice] = []

    if room is not None:
        choices.append(MoveChoice("stay"))
        passage_target = board.SECRET_PASSAGES.get(room)
        if passage_target is not None:
            choices.append(MoveChoice("secret_passage", passage_target))

    occupied = frozenset(
        p for p in state.positions.values() if isinstance(p, board.HallwayCell)
    )
    for dest in board.reachable(pos, roll, occupied):
        choices.append(MoveChoice("move", dest))
    return choices


def apply_move(state: GameState, player: int, choice: MoveChoice) -> None:
    if choice.kind == "stay":
        return
    state.positions[player] = choice.destination


def resolve_suggestion(
    state: GameState,
    suggester: int,
    suspect: str,
    weapon: str,
    bots: dict[int, RandomBotProtocol],
    rng: random.Random,
) -> Suggestion:
    """Move the named suspect's token into the room, then ask each other
    player in turn order (eliminated players included -- they still hold
    cards and must disprove) whether they can refute."""
    room = board.room_of(state.positions[suggester])
    assert room is not None, "suggestion made outside a room"

    for p, name in enumerate(state.suspects_in_play):
        if name == suspect:
            state.positions[p] = room
            break

    named = {suspect, weapon, room}
    refuter: Optional[int] = None
    shown: Optional[str] = None
    order = players_after(state.n_players, suggester)
    for p in order:
        matching = sorted(named & state.hands[p])
        if matching:
            refuter = p
            shown = bots[p].choose_card_to_show(matching, rng)
            break

    suggestion = Suggestion(
        suggester=suggester,
        suspect=suspect,
        weapon=weapon,
        room=room,
        refuter=refuter,
        shown_to=suggester,
        card_shown=shown,
    )
    state.suggestion_log.append(suggestion)
    return suggestion


def resolve_accusation(
    state: GameState, accuser: int, suspect: str, weapon: str, room: str
) -> Accusation:
    """Compare to the envelope. A wrong accusation eliminates the accuser
    from moving/suggesting/accusing but not from being asked to refute."""
    correct = (suspect, weapon, room) == state.envelope
    accusation = Accusation(accuser, suspect, weapon, room, correct)
    state.accusation_log.append(accusation)
    if not correct:
        state.active[accuser] = False
    return accusation


def run_game(
    n_players: int,
    bots: dict[int, RandomBotProtocol],
    seed: Optional[int] = None,
    max_turns: int = 300,
) -> tuple[GameState, list[GameEvent]]:
    """Play one full headless game and return the final state and event log."""
    rng = random.Random(seed)
    state = setup(n_players, rng)
    events: list[GameEvent] = []
    turns_taken = 0
    idx = 0

    while turns_taken < max_turns:
        if not any(state.active):
            break
        player = idx % n_players
        idx += 1
        if not state.active[player]:
            continue

        state.turn += 1
        turns_taken += 1
        roll = rng.randint(1, 6)
        choices = legal_moves(state, player, roll)
        choice = bots[player].choose_movement(choices, rng)
        apply_move(state, player, choice)
        events.append(
            MoveEvent(state.turn, player, state.positions[player], choice.kind == "secret_passage")
        )

        room = board.room_of(state.positions[player])
        if room is not None:
            suggested = bots[player].choose_suggestion(room, state.hands[player], rng)
            if suggested is not None:
                suspect, weapon = suggested
                suggestion = resolve_suggestion(state, player, suspect, weapon, bots, rng)
                events.append(SuggestionEvent(state.turn, suggestion))

        accused = bots[player].choose_accusation(rng)
        if accused is not None:
            suspect, weapon, room2 = accused
            accusation = resolve_accusation(state, player, suspect, weapon, room2)
            events.append(AccusationEvent(state.turn, accusation))
            if accusation.correct:
                events.append(GameOverEvent(state.turn, player, state.envelope))
                return state, events

    events.append(GameOverEvent(state.turn, None, state.envelope))
    return state, events
