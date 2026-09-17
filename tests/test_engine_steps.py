"""The resumable turn loop (Phase 8.1, `docs/phase8.1-plan.md` 3.3).

`run_game` is `engine.game_steps` driven with no external seats; every
golden in `tests/test_character.py` proves that driver plays the game it
always did. What is left to prove here is the other half: that a seat the
engine cannot call is asked for exactly the same decisions, in the same
order, and that answering them reproduces the same game -- including the
one decision that falls on someone else's turn, the refutation.
"""
import random
from typing import NamedTuple

import pytest

from clude_core import board, engine
from clude_core.domain import SUSPECTS, WEAPONS
from clude_core.events import GameOverEvent


class Fixed:
    """A deterministic seat that never draws from the engine's RNG.

    `RandomBot` cannot stand in here: it draws its choices from the
    engine RNG, so a table of external seats -- which never calls a
    player object at all -- would roll different dice from the recorded
    game and diverge for a reason that has nothing to do with the seam.
    A real `Character` has its own RNG and leaves the engine's untouched
    (`PlayerProtocol`), which is the property this stands in for.

    It heads for a room whenever one is offered, so that a sample game
    actually produces suggestions and refutations, and its suggestions
    walk the card lists by how many have been made, so the refutations
    land on different seats over a game rather than always the same one.
    """

    def choose_movement(self, obs, choices, rng):
        into_room = [
            c
            for c in choices
            if c.kind != "stay" and board.room_of(c.destination) is not None
        ]
        return into_room[0] if into_room else choices[-1]

    def choose_suggestion(self, obs, room, rng):
        k = len(obs.suggestion_log)
        return SUSPECTS[k % len(SUSPECTS)], WEAPONS[k % len(WEAPONS)]

    def choose_accusation(self, obs, rng):
        return None

    def choose_card_to_show(self, obs, candidates, shown_to, rng):
        return candidates[0]


class Accuser(Fixed):
    """`Fixed`, but accuses `envelope` on its `at`-th turn, to end a game
    on a correct accusation rather than the turn cap."""

    def __init__(self, envelope, at=2):
        self.envelope = envelope
        self.at = at
        self.turns = 0

    def choose_accusation(self, obs, rng):
        self.turns += 1
        return self.envelope if self.turns >= self.at else None


class Recorder:
    """Plays like `inner` and writes every decision into `log`, in the
    order the engine asked for it."""

    def __init__(self, seat, inner, log):
        self.seat = seat
        self.inner = inner
        self.log = log

    def _note(self, kind, answer):
        self.log.append((self.seat, kind, answer))
        return answer

    def choose_movement(self, obs, choices, rng):
        return self._note("movement", self.inner.choose_movement(obs, choices, rng))

    def choose_suggestion(self, obs, room, rng):
        return self._note("suggestion", self.inner.choose_suggestion(obs, room, rng))

    def choose_accusation(self, obs, rng):
        return self._note("accusation", self.inner.choose_accusation(obs, rng))

    def choose_card_to_show(self, obs, candidates, shown_to, rng):
        return self._note(
            "card_to_show",
            self.inner.choose_card_to_show(obs, candidates, shown_to, rng),
        )


def envelope_for(n_players, seed):
    """The envelope a game will deal, worked out before it is played.

    `setup` is the first thing `game_steps` draws from the RNG, so
    dealing from a fresh `Random(seed)` here deals exactly the game the
    generator is about to.
    """
    return engine.setup(n_players, random.Random(seed)).envelope


def record(n_players=4, seed=7, max_turns=40, inner=None):
    """Play a game through `run_game` and return its result with the
    decisions it asked for."""
    log = []
    make = inner or (lambda: Fixed())
    bots = {p: Recorder(p, make(), log) for p in range(n_players)}
    state, events = engine.run_game(n_players, bots, seed=seed, max_turns=max_turns)
    return state, events, log


class Replayed(NamedTuple):
    """What `replay` saw: the live game, and how it got there."""

    state: object
    events: list
    requests: list
    markers: list
    finished: bool


def replay(answers, n_players=4, seed=7, max_turns=40, external=None, bots=None):
    """Drive `game_steps` with `external` seats, answering each request
    from `answers` in order.

    Every answer is checked against the request it answers, so a seam
    that asked the wrong seat, or asked in the wrong order, fails here
    rather than silently playing a different game.

    If `answers` runs out mid-game the drive stops there and comes back
    with `finished` False, which is how these tests model a session
    pausing between two web requests. The state and events come from the
    `LiveGame` handle, so they read correctly at a pause as well as at
    the end.
    """
    if external is None:
        external = frozenset(range(n_players))
    steps = engine.game_steps(
        n_players,
        bots if bots is not None else {},
        seed=seed,
        max_turns=max_turns,
        external=external,
    )
    live = next(steps)
    assert isinstance(live, engine.LiveGame), "the handle comes before the first turn"
    requests, markers = [], []
    supply = iter(answers)
    answer = None
    ready = False  # an answer may legitimately be None, so track it apart
    finished = False
    try:
        while True:
            item = steps.send(answer) if ready else next(steps)
            ready = False
            if isinstance(item, engine.DecisionRequest):
                requests.append(item)
                try:
                    seat, kind, recorded = next(supply)
                except StopIteration:
                    break  # paused: nothing left to answer with
                assert (item.seat, item.kind) == (seat, kind), (
                    f"expected {seat} to be asked for {kind}, "
                    f"got {item.seat} asked for {item.kind}"
                )
                answer, ready = recorded, True
            else:
                markers.append(item)
    except StopIteration:
        finished = True
    return Replayed(live.state, live.events, requests, markers, finished)


def test_a_fully_external_table_reproduces_the_same_game():
    state, events, log = record()
    done = replay(log)

    assert done.finished
    assert done.events == events
    assert done.state.envelope == state.envelope
    assert done.state.positions == state.positions
    assert done.state.suggestion_log == state.suggestion_log
    assert len(done.requests) == len(log)


def test_the_refuter_is_asked_on_someone_elses_turn():
    """The decision that makes the seam necessary: `choose_card_to_show`
    falls on a seat whose turn it is not, so pausing only the turn loop
    would never reach a human refuter."""
    _state, _events, log = record()
    done = replay(log)

    shows = [r for r in done.requests if r.kind == "card_to_show"]
    assert shows, "no refutation happened in the sample game"
    off_turn = [r for r in shows if r.seat != r.shown_to]
    assert len(off_turn) == len(shows), "a seat refuted its own suggestion"
    for request in shows:
        assert request.candidates, "a refuter was asked with no candidates"


def test_a_mixed_table_asks_only_its_external_seats():
    """Seats 0 and 2 external, 1 and 3 played by their own objects."""
    _state, events, log = record()
    external = frozenset({0, 2})
    answers = [entry for entry in log if entry[0] in external]
    bots = {p: Fixed() for p in range(4) if p not in external}

    mixed = replay(answers, external=external, bots=bots)

    assert mixed.events == events
    assert {r.seat for r in mixed.requests} == external
    assert len(mixed.requests) == len(answers)


def test_a_paused_session_is_readable_where_it_stopped():
    """A driver holding the `LiveGame` handle can render a game that is
    waiting on an external seat, which is what the Watch and human-seat
    screens do between requests."""
    _state, events, log = record()
    half = len(log) // 2

    paused = replay(log[:half])

    assert not paused.finished
    assert 0 < len(paused.events) < len(events)
    assert paused.events == events[: len(paused.events)]
    assert paused.state.positions, "the board is readable at the pause"


def test_a_rebuilt_session_matches_the_live_one():
    """The cold-instance story (plan 3.3): a paused game is its setup
    plus the answers sent so far, so a fresh generator fed that list
    catches up exactly and can carry the game on to the same end."""
    _state, events, log = record()
    half = len(log) // 2

    paused = replay(log[:half])
    rebuilt = replay(log[:half])  # a cold instance, replaying the answers
    carried_on = replay(log)  # and the same list plus the rest

    assert rebuilt.events == paused.events
    assert rebuilt.state.positions == paused.state.positions
    assert [m.turn for m in rebuilt.markers] == [m.turn for m in paused.markers]
    assert carried_on.finished
    assert carried_on.events == events
    assert carried_on.events[: len(paused.events)] == paused.events


def test_turn_markers_cover_every_event_including_the_last():
    envelope = envelope_for(4, seed=11)
    _state, events, log = record(
        seed=11, max_turns=40, inner=lambda: Accuser(envelope)
    )
    done = replay(log, seed=11, max_turns=40)
    markers = done.markers

    assert done.events == events
    assert isinstance(events[-1], GameOverEvent)
    assert [m.turn for m in markers] == sorted(m.turn for m in markers)
    assert [m.events for m in markers] == sorted(m.events for m in markers)
    # The marker for the winning turn comes after its GameOverEvent, so
    # a driver slicing turns by marker never drops the end of the game.
    assert markers[-1].events == len(events)
    assert markers[-1].seat == events[-1].winner


def test_turn_markers_land_once_per_turn():
    _state, events, log = record()
    done = replay(log)

    moves = [e for e in events if type(e).__name__ == "MoveEvent"]
    assert len(done.markers) == len(moves), "one marker per turn played"
    assert all(m.turn == move.turn for m, move in zip(done.markers, moves))


def test_an_illegal_move_from_an_external_seat_is_refused():
    steps = engine.game_steps(4, {}, seed=7, external=frozenset(range(4)))
    assert isinstance(next(steps), engine.LiveGame)
    request = next(steps)
    assert request.kind == "movement"
    bogus = engine.MoveChoice("move", "Kitchen")
    assert bogus not in request.choices
    with pytest.raises(ValueError, match="illegal move"):
        steps.send(bogus)


def test_an_external_seat_cannot_show_a_card_it_does_not_hold():
    """Reveal integrity (docs/architecture.md): the engine keeps this
    impossible to break by accident, and a seat answering from outside is
    the first thing that could."""
    _state, _events, log = record()
    answers = list(log)
    at = next(i for i, (_s, kind, _a) in enumerate(answers) if kind == "card_to_show")
    seat, kind, held = answers[at]
    not_held = next(c for c in SUSPECTS if c != held)
    answers[at] = (seat, kind, not_held)

    with pytest.raises(ValueError, match="must show one of"):
        replay(answers)


@pytest.mark.parametrize(
    "kind,bad",
    [("suggestion", ("Nobody", "Rope")), ("accusation", ("Scarlett", "Rope", "Attic"))],
)
def test_an_external_seat_cannot_name_a_card_that_does_not_exist(kind, bad):
    _state, _events, log = record()
    answers = list(log)
    at = next(i for i, (_s, k, _a) in enumerate(answers) if k == kind)
    seat, _k, _a = answers[at]
    answers[at] = (seat, kind, bad)

    with pytest.raises(ValueError, match="unknown cards"):
        replay(answers)


def test_run_game_refuses_a_generator_that_would_pause():
    """`run_game` has no way to answer a request, so a table with an
    external seat is a programming error, not a silent stall."""
    steps = engine.game_steps(4, {}, seed=7, external=frozenset({0}))
    with pytest.raises(RuntimeError, match="no external seats"):
        engine._drive(steps)
