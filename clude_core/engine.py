"""Headless rules engine: setup, movement, suggestion/refutation,
accusation, and the turn loop. No inference, no LLM.

Every seat is asked its four decisions through `PlayerProtocol`, each
call receiving that seat's `ClueObservation` first (Phase 5a). The
observation is built by an injectable `observer`, defaulting to
`ClueObservation.for_player`, so this package still never imports the
deduction floor -- callers who want a masked view pass
`clude_constraints.observe` (see docs/architecture.md).

A seat that also implements `SpeakingPlayer` (Phase 6) has its buffered
table talk appended to the event log as `RemarkEvent`s right after each
decision; every other seat's game is untouched by that hook.

The turn loop is written once, as the generator `game_steps` (Phase
8.1). A seat listed in its `external` set has no player object to call:
the generator yields a `DecisionRequest` and waits for the driver to
send the answer back in, which is what lets a web request hold a seat
open across requests without threads. `run_game` is `game_steps` driven
with no external seats, so it never pauses and plays exactly the game it
always did; `resolve_suggestion` stands in the same relation to
`resolve_suggestion_steps`, so the refuter's off-turn choice can be
external too.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Optional, Protocol, runtime_checkable

from . import board
from .board import Node
from .domain import ALL_CARDS, Accusation, ROOMS, Suggestion, SUSPECTS, WEAPONS, players_after
from .events import (
    AccusationEvent,
    GameEvent,
    GameOverEvent,
    MoveEvent,
    RemarkEvent,
    SuggestionEvent,
)
from .state import ClueObservation, GameState

MIN_PLAYERS = 3
MAX_PLAYERS = 6

Observer = Callable[[GameState, int], ClueObservation]
"""Builds one seat's view of the game: ``observer(state, player)``."""


@dataclass(frozen=True)
class MoveChoice:
    """One legal movement option for a turn.

    `kind` is one of ``"stay"`` (offered while in a room, or when a
    hallway token is boxed in with no legal move at all; `destination`
    is the current node, so a player can tell where staying keeps them),
    ``"secret_passage"`` (only offered in a room that has one;
    `destination` is the connected room), or ``"move"`` (`destination`
    is a reachable node).
    """

    kind: str
    destination: Optional[Node] = None


@dataclass(frozen=True)
class DecisionRequest:
    """One decision the engine needs from a seat it cannot call itself.

    `game_steps` yields this whenever the seat to ask is in its
    `external` set, and waits for the driver to send the answer back in
    with `steps.send(answer)`. `kind` names which of `PlayerProtocol`'s
    four decisions is wanted, which fields carry its context, and what
    the answer must be:

    ===============  ======================  ===========================
    kind             carried in              answer to send back
    ===============  ======================  ===========================
    "movement"       `choices`               a `MoveChoice` from `choices`
    "suggestion"     `room`                  `(suspect, weapon)`, or None
    "accusation"     --                      `(suspect, weapon, room)`,
                                             or None
    "card_to_show"   `candidates`,           one card from `candidates`
                     `shown_to`
    ===============  ======================  ===========================

    `obs` is that seat's own `ClueObservation`, built by the same
    `observer` a player object would have been handed, so an external
    seat sees exactly what a seated character would and no more.
    """

    seat: int
    kind: str
    obs: ClueObservation
    choices: Optional[list[MoveChoice]] = None
    room: Optional[str] = None
    candidates: Optional[list[str]] = None
    shown_to: Optional[int] = None


@dataclass(frozen=True)
class LiveGame:
    """The game a `game_steps` generator is playing, yielded once before
    its first turn.

    `state` and `events` are the generator's own objects, not copies, so
    a driver that keeps this handle can read the game as it stands at
    every later pause -- the board, the tokens, the log so far. A
    `DecisionRequest` deliberately carries only one seat's masked view
    instead, so that what the referee can see and what a player is told
    stay separate things (docs/architecture.md, "Reveal integrity").
    """

    state: GameState
    events: list[GameEvent]


@dataclass(frozen=True)
class TurnComplete:
    """Yielded at the end of every turn, after that seat's accusation and
    its last remarks -- including the turn that ends the game, whose
    marker comes after the `GameOverEvent`.

    `events` is the length of the event log at that moment, so a driver
    holding the previous marker can slice out exactly the turn just
    played. This is what "play one more turn" resumes to.
    """

    turn: int
    seat: int
    events: int


class PlayerProtocol(Protocol):
    """The four decisions the engine asks of every seat.

    Each takes the seat's own `ClueObservation` first, built by
    `run_game`'s `observer` from that seat's perspective. With the
    default observer `obs.mask` is None; pass `clude_constraints.observe`
    to `run_game` for a masked view (every Phase 3+ agent needs one).

    `rng` is the engine's seeded RNG. Phase 1's `RandomBot` draws from
    it, so seeded random games are reproducible; a player with its own
    RNG (Phase 5's `Character`) should leave it untouched, so that the
    dice sequence depends only on the seed and games played under
    different personality settings share the same deal *and* rolls.
    """

    def choose_movement(
        self, obs: ClueObservation, choices: list[MoveChoice], rng: random.Random
    ) -> MoveChoice: ...

    def choose_suggestion(
        self, obs: ClueObservation, room: str, rng: random.Random
    ) -> Optional[tuple[str, str]]:
        """Return (suspect, weapon) to suggest in `room`, the seat's
        current room, or None to make no suggestion this turn."""
        ...

    def choose_accusation(
        self, obs: ClueObservation, rng: random.Random
    ) -> Optional[tuple[str, str, str]]:
        """Return (suspect, weapon, room) to accuse, or None. `obs` is
        rebuilt after this turn's suggestion resolves, so its refutation
        is already visible."""
        ...

    def choose_card_to_show(
        self, obs: ClueObservation, candidates: list[str], shown_to: int, rng: random.Random
    ) -> str:
        """Return which of `candidates` (the named cards this seat holds,
        sorted) to show to `shown_to`. The suggestion being refuted is
        not yet in `obs.suggestion_log`."""
        ...


@runtime_checkable
class SpeakingPlayer(Protocol):
    """Optional extension of `PlayerProtocol` for seats that talk
    (Phase 6's LLM characters).

    After each decision the engine asks the deciding seat -- and, once a
    suggestion has resolved, its refuter -- for the lines it buffered,
    and appends them to the event log as `RemarkEvent`s in order, right
    after the decision's own event; every other speaking seat is told each
    line through `hear`. A player without these methods is never asked,
    so nothing about its games changes.
    """

    def take_remarks(self) -> list[str]:
        """Return, and clear, the lines buffered since the last call."""
        ...

    def hear(self, remark: RemarkEvent) -> None:
        """Be told a remark another seat just made (never this seat's own)."""
        ...


def setup(n_players: int, rng: random.Random, suspects=None) -> GameState:
    """Deal a new game: pick the envelope, deal the rest round-robin, and
    place each in-play suspect's token at its starting hallway cell.

    `suspects` names the token in each seat, in seat order (the board's
    turn order); default the first `n_players` suspects. The deal draws
    from `rng` the same way whatever the seating, so one seed is one
    deal at every table.

    Raises
    ------
    ValueError
        On a table size outside 3-6, or `suspects` that are not
        `n_players` distinct suspect names.
    """
    if not (MIN_PLAYERS <= n_players <= MAX_PLAYERS):
        raise ValueError(f"Clue supports {MIN_PLAYERS}-{MAX_PLAYERS} players")
    if suspects is None:
        suspects_in_play = list(SUSPECTS[:n_players])
    else:
        suspects_in_play = list(suspects)
        if (
            len(suspects_in_play) != n_players
            or len(set(suspects_in_play)) != n_players
            or any(s not in SUSPECTS for s in suspects_in_play)
        ):
            raise ValueError(
                f"suspects must be {n_players} distinct names from {SUSPECTS}, got {suspects_in_play}"
            )
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
        summoned=[False] * n_players,
    )


def legal_moves(state: GameState, player: int, roll: int) -> list[MoveChoice]:
    """Every legal movement option for `player` given this turn's roll.

    In a room: "stay" only if a suggestion moved the token there since
    its last turn (`GameState.summoned`), the secret passage if the room
    has one, and every destination `board.reachable` allows under the
    Classic rules (the whole roll, no re-entering the room just left).
    In the corridor: every such destination. A token with no legal step
    (boxed in, or a room whose door squares are all occupied and no
    passage) gets a single "stay" where it is.
    """
    pos = state.positions[player]
    room = board.room_of(pos)
    choices: list[MoveChoice] = []

    if room is not None:
        if state.summoned and state.summoned[player]:
            choices.append(MoveChoice("stay", room))
        passage_target = board.SECRET_PASSAGES.get(room)
        if passage_target is not None:
            choices.append(MoveChoice("secret_passage", passage_target))

    occupied = frozenset(
        p for p in state.positions.values() if isinstance(p, board.Square)
    )
    # Sorted for a process-independent order before any caller indexes
    # into this list with a seeded RNG -- see `board.node_sort_key`.
    for dest in sorted(board.reachable(pos, roll, occupied), key=board.node_sort_key):
        choices.append(MoveChoice("move", dest))
    if not choices:
        # Boxed in on a hallway cell by other tokens: a blocked player
        # simply doesn't move this turn.
        choices.append(MoveChoice("stay", pos))
    return choices


def apply_move(state: GameState, player: int, choice: MoveChoice) -> None:
    if choice.kind == "stay":
        return
    state.positions[player] = choice.destination


def _checked(request: DecisionRequest, answer):
    """Check an external seat's answer before it is allowed to touch the
    game, and return it.

    A movement must be one of the choices actually offered, and a
    refutation one of the cards that seat actually holds: the
    reveal-integrity rule in docs/architecture.md, which the engine keeps
    impossible to break by accident, and which a seat answering over a
    network would otherwise be the first thing able to break. A
    suggestion or an accusation only has to name real cards -- naming the
    wrong ones is the game.
    """
    if request.kind == "movement":
        if answer not in request.choices:
            raise ValueError(
                f"seat {request.seat} chose an illegal move: {answer!r}"
            )
    elif request.kind == "card_to_show":
        if answer not in request.candidates:
            raise ValueError(
                f"seat {request.seat} must show one of {request.candidates}, "
                f"not {answer!r}"
            )
    elif request.kind == "suggestion" and answer is not None:
        suspect, weapon = answer
        if suspect not in SUSPECTS or weapon not in WEAPONS:
            raise ValueError(
                f"seat {request.seat} suggested unknown cards: {answer!r}"
            )
    elif request.kind == "accusation" and answer is not None:
        suspect, weapon, room = answer
        if suspect not in SUSPECTS or weapon not in WEAPONS or room not in ROOMS:
            raise ValueError(
                f"seat {request.seat} accused unknown cards: {answer!r}"
            )
    return answer


def _ask(
    bots: dict[int, PlayerProtocol],
    external: frozenset,
    request: DecisionRequest,
    rng: random.Random,
):
    """Get one decision from a seat: call its player object, as the engine
    always has, or, for a seat in `external`, yield `request` out to the
    driver and take the checked answer it sends back.

    This is a generator, so its callers reach it with `yield from`. For a
    seat with a player object it yields nothing at all, which is what
    lets `run_game` drive a table of headless seats to the end without
    ever pausing.
    """
    if request.seat in external:
        return _checked(request, (yield request))
    player = bots[request.seat]
    if request.kind == "movement":
        return player.choose_movement(request.obs, request.choices, rng)
    if request.kind == "suggestion":
        return player.choose_suggestion(request.obs, request.room, rng)
    if request.kind == "accusation":
        return player.choose_accusation(request.obs, rng)
    if request.kind == "card_to_show":
        return player.choose_card_to_show(
            request.obs, request.candidates, request.shown_to, rng
        )
    raise ValueError(f"unknown decision kind {request.kind!r}")


def _drive(steps):
    """Run a step generator that has no external seats to the end and
    return what it returns.

    `TurnComplete` markers are passed over; a `DecisionRequest` is a bug,
    since with `external` empty there is no seat to pause for.
    """
    try:
        while True:
            paused = next(steps)
            if isinstance(paused, DecisionRequest):
                raise RuntimeError(
                    f"seat {paused.seat} asked for {paused.kind!r} in a call "
                    "that has no external seats"
                )
    except StopIteration as stop:
        return stop.value


def resolve_suggestion(
    state: GameState,
    suggester: int,
    suspect: str,
    weapon: str,
    bots: dict[int, PlayerProtocol],
    rng: random.Random,
    observer: Observer = ClueObservation.for_player,
) -> Suggestion:
    """Move the named suspect's token into the room, then ask each other
    player in turn order (eliminated players included -- they still hold
    cards and must disprove) whether they can refute.

    Who must show a card is computed from `state.hands` -- ground truth,
    never a player's own claim (the reveal-integrity rule in
    docs/architecture.md). The refuter only chooses *which* matching
    card to show, given their own observation from `observer`.

    This is `resolve_suggestion_steps` driven with no external seats, so
    it never pauses; its signature and its result are what they have
    always been.
    """
    return _drive(
        resolve_suggestion_steps(
            state, suggester, suspect, weapon, bots, rng, observer
        )
    )


def resolve_suggestion_steps(
    state: GameState,
    suggester: int,
    suspect: str,
    weapon: str,
    bots: dict[int, PlayerProtocol],
    rng: random.Random,
    observer: Observer = ClueObservation.for_player,
    external: frozenset = frozenset(),
):
    """`resolve_suggestion` as a generator, pausing on a
    `DecisionRequest` when the seat that must refute is in `external`.

    Returns the `Suggestion`, so a caller inside another generator writes
    ``suggestion = yield from resolve_suggestion_steps(...)``. This is
    the only decision the engine asks of a seat on someone else's turn,
    and it is why a human seat cannot be served by pausing the turn loop
    alone.
    """
    room = board.room_of(state.positions[suggester])
    assert room is not None, "suggestion made outside a room"

    for p, name in enumerate(state.suspects_in_play):
        if name == suspect:
            if state.positions[p] != room:
                state.positions[p] = room
                if state.summoned:
                    state.summoned[p] = True  # may stay and suggest here on its next turn
            break

    named = {suspect, weapon, room}
    refuter: Optional[int] = None
    shown: Optional[str] = None
    order = players_after(state.n_players, suggester)
    for p in order:
        matching = sorted(named & state.hands[p])
        if matching:
            refuter = p
            shown = yield from _ask(
                bots,
                external,
                DecisionRequest(
                    seat=p,
                    kind="card_to_show",
                    obs=observer(state, p),
                    candidates=matching,
                    shown_to=suggester,
                ),
                rng,
            )
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


def _append_remarks(
    events: list[GameEvent], bots: dict[int, PlayerProtocol], seat: int, turn: int, about: str
) -> None:
    """Drain `seat`'s buffered table talk into `events`, if it speaks, and
    let every other speaking seat hear each line.

    An external seat has no player object at all, so it is simply never
    asked; its own talk reaches the log another way (Phase 8.3).
    """
    player = bots.get(seat)
    if not isinstance(player, SpeakingPlayer):
        return
    for text in player.take_remarks():
        remark = RemarkEvent(turn, seat, text, about)
        events.append(remark)
        for other, listener in bots.items():
            if other != seat and isinstance(listener, SpeakingPlayer):
                listener.hear(remark)


def run_game(
    n_players: int,
    bots: dict[int, PlayerProtocol],
    seed: Optional[int] = None,
    max_turns: int = 300,
    observer: Observer = ClueObservation.for_player,
    suspects=None,
) -> tuple[GameState, list[GameEvent]]:
    """Play one full headless game and return the final state and event log.

    Parameters
    ----------
    n_players : int
        Table size, 3-6.
    bots : dict[int, PlayerProtocol]
        One player per seat index. A seat that also implements
        `SpeakingPlayer` has its remarks appended after each decision.
    seed : int or None
        Seeds the deal, the dice, and any player that draws from the
        engine RNG.
    max_turns : int
        Turn cap if nobody accuses correctly.
    observer : Observer
        Builds each seat's `ClueObservation` before every decision.
        Default `ClueObservation.for_player` (no `mask`); pass
        `clude_constraints.observe` for players that need the deduction
        floor. One observation serves both the movement and the
        suggestion decision of a turn -- nothing a `ClueObservation`
        carries changes between them -- and a fresh one is built for the
        accusation once this turn's suggestion has resolved.
    suspects : sequence of str or None
        The token in each seat, in seat order (`setup`); default the
        first `n_players` suspects. A character plays its own suspect's
        token (`clude_training.arena.seat_lineup` seats a table that
        way), so seat `i` is `suspects[i]`'s.

    Notes
    -----
    This is `game_steps` driven with no external seats, so it never
    pauses. Its signature and its result are what they have always been,
    and the goldens in `tests/test_character.py` are what prove it.
    """
    return _drive(game_steps(n_players, bots, seed, max_turns, observer, suspects))


def game_steps(
    n_players: int,
    bots: dict[int, PlayerProtocol],
    seed: Optional[int] = None,
    max_turns: int = 300,
    observer: Observer = ClueObservation.for_player,
    suspects=None,
    external: frozenset = frozenset(),
):
    """The turn loop as a resumable generator; `run_game` drives it.

    Takes `run_game`'s parameters and one more:

    Parameters
    ----------
    external : frozenset[int]
        Seats with no player object in `bots`. Each of their four
        decisions pauses the generator on a `DecisionRequest`, which the
        driver answers with ``steps.send(answer)``; the answer is checked
        before it touches the game (`_checked`). Default empty, which is
        `run_game`.

    Yields
    ------
    LiveGame
        Once, before the first turn: the handle onto the state and event
        log this generator is building, for a driver that has to render
        the game while it is paused.
    DecisionRequest
        An external seat's decision is needed. Send the answer back in.
    TurnComplete
        One turn has finished, including the turn that ends the game.

    Returns
    -------
    tuple[GameState, list[GameEvent]]
        The same pair `run_game` returns, delivered on `StopIteration`.

    Because a game is deterministic per seed, a paused game is fully
    described by its setup plus the answers sent in so far: feeding a
    fresh generator that list rebuilds it exactly, which is how a web
    session survives a cold instance (docs/phase8.1-plan.md 3.3).
    """
    rng = random.Random(seed)
    state = setup(n_players, rng, suspects)
    events: list[GameEvent] = []
    yield LiveGame(state, events)
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
        if state.summoned:
            state.summoned[player] = False  # the right to stay lasts one turn, used or not
        obs = observer(state, player)
        choice = yield from _ask(
            bots,
            external,
            DecisionRequest(seat=player, kind="movement", obs=obs, choices=choices),
            rng,
        )
        apply_move(state, player, choice)
        events.append(
            MoveEvent(state.turn, player, state.positions[player], choice.kind == "secret_passage")
        )
        _append_remarks(events, bots, player, state.turn, "move")

        room = board.room_of(state.positions[player])
        if room is not None:
            suggested = yield from _ask(
                bots,
                external,
                DecisionRequest(seat=player, kind="suggestion", obs=obs, room=room),
                rng,
            )
            if suggested is not None:
                suspect, weapon = suggested
                suggestion = yield from resolve_suggestion_steps(
                    state, player, suspect, weapon, bots, rng, observer, external
                )
                events.append(SuggestionEvent(state.turn, suggestion))
                _append_remarks(events, bots, player, state.turn, "suggest")
                if suggestion.refuter is not None:
                    _append_remarks(events, bots, suggestion.refuter, state.turn, "show")
                obs = observer(state, player)

        accused = yield from _ask(
            bots,
            external,
            DecisionRequest(seat=player, kind="accusation", obs=obs),
            rng,
        )
        accusation: Optional[Accusation] = None
        if accused is not None:
            suspect, weapon, room2 = accused
            accusation = resolve_accusation(state, player, suspect, weapon, room2)
            events.append(AccusationEvent(state.turn, accusation))
        _append_remarks(events, bots, player, state.turn, "accuse")
        won = accusation is not None and accusation.correct
        if won:
            events.append(GameOverEvent(state.turn, player, state.envelope))
        # After the GameOverEvent, so the last marker covers the whole
        # turn and a driver slicing by marker never drops the ending.
        yield TurnComplete(state.turn, player, len(events))
        if won:
            return state, events

    events.append(GameOverEvent(state.turn, None, state.envelope))
    return state, events
