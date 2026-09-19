"""The table driver (Phase 8.2a, docs/phase8-plan.md 3.1).

What is pinned: that a table with no humans plays exactly the game
`headless_table` and `play` play; that a seat answered from outside
reproduces the game a player object in that seat would have played,
the off-turn refutation included; that a game rebuilt from its entry
log lands on the same pause as the live one; that every answer round
trips as data; and that a bad answer is refused with a message and
leaves the game exactly as it was, rather than finishing the generator
for everyone.
"""
from __future__ import annotations

import dataclasses
import random

import pytest

from clude_core import board, engine
from clude_core.domain import ROOMS, SUSPECTS, WEAPONS
from clude_core.engine import DecisionRequest, MoveChoice
from clude_core.events import GameOverEvent
from clude_training.arena import headless_table, lineup_for_game, parse_roster, seat_lineup
from clude_training.table import (
    SeatSpec,
    TableError,
    TableGame,
    TableSetup,
    build_table,
    decode_answer,
    describe_request,
    encode_answer,
    seat_specs,
)
from tests.test_engine_steps import Fixed, Recorder

ROSTER = ("Scarlett", "Mustard", "White")
"""The fast three, as `tests/test_web_watch.py` uses them."""
SEED = 7


def _events(game) -> list:
    return [repr(e) for e in game.events]


def reference_game(setup: TableSetup, human_seats, inner=None):
    """The game `run_game` plays with `Fixed` players in the human seats,
    recording what they were asked, so a `TableGame` answered from that
    log must reproduce it."""
    table, external = build_table(setup)
    assert external == frozenset(human_seats)
    log: list = []
    players = dict(table.players)
    for seat in human_seats:
        players[seat] = Recorder(seat, (inner or Fixed)(), log)
    state, events = engine.run_game(
        setup.n_players, players, seed=setup.seed, max_turns=setup.max_turns,
        observer=table.observer, suspects=table.suspects,
    )
    return state, events, log


def play_from_log(game: TableGame, log, check=None):
    """Answer every request of `game` from a recorded log, in order.
    `check(game)` is called after each answer."""
    supply = iter(log)
    while not game.finished:
        if game.pending is None:
            game.run(1)
            continue
        seat, kind, answer = next(supply)
        assert (game.pending.seat, game.pending.kind) == (seat, kind)
        game.answer(seat, game.seq, encode_answer(kind, answer))
        if check is not None:
            check(game)
    with pytest.raises(StopIteration):
        next(supply)


def human_setup(roster=ROSTER, n_players=4, seed=SEED, humans=None, max_turns=300):
    humans = humans if humans is not None else {"Green": "david"}
    return TableSetup.from_roster(roster, n_players, seed, humans=humans, max_turns=max_turns)


# --- 1. seating ---------------------------------------------------------------


@pytest.mark.parametrize(
    "roster,n_players",
    [(("Scarlett", "Mustard", "White"), 4), (("Mustard", "White"), 3), (("Peacock",), 5),
     (("Plum", "floor", "random"), 6), (("Scarlett", "Mustard", "White", "Green", "Peacock", "Plum"), 6)],
)
def test_from_roster_seats_exactly_as_seat_lineup_does(roster, n_players):
    setup = TableSetup.from_roster(roster, n_players, SEED)
    labels, suspects = seat_lineup(lineup_for_game(parse_roster(roster), 0, n_players))
    assert setup.labels == labels
    assert setup.suspects == suspects
    assert setup.external == frozenset()
    assert all(kind in ("character", "floor", "random") for kind in setup.kinds)


def test_headless_table_and_a_no_human_table_play_the_same_game():
    table = headless_table(ROSTER, 4, SEED)
    reference = engine.run_game(4, table.players, seed=SEED, observer=table.observer, suspects=table.suspects)
    game = TableGame(TableSetup.from_roster(ROSTER, 4, SEED))
    assert game.external == frozenset()
    assert game.kinds == ["character", "character", "character", "floor"]
    played = game.play_to_end()
    assert game.finished and played == game.turns
    assert [repr(e) for e in reference[1]] == _events(game)
    assert game.entries == []


def test_a_human_takes_a_token_and_the_fills_take_the_lowest_free_ones():
    setup = TableSetup.from_roster(("Plum", "Mustard"), 4, SEED, humans={"Scarlett": "david"})
    assert [(s.token, s.kind, s.label) for s in setup.seats] == [
        ("Scarlett", "human", "david"), ("Mustard", "character", "Mustard"),
        ("White", "floor", "floor"), ("Plum", "character", "Plum"),
    ]
    assert setup.external == frozenset({0})
    assert setup.labels == ["david", "Mustard", "floor", "Plum"]
    table, external = build_table(setup)
    assert external == frozenset({0})
    assert 0 not in table.players and sorted(table.players) == [1, 2, 3]
    assert table.kinds == ["human", "character", "floor", "character"]


def test_a_human_cannot_take_a_seated_characters_token():
    with pytest.raises(ValueError, match="Plum"):
        TableSetup.from_roster(("Plum", "Mustard"), 4, SEED, humans={"Plum": "david"})
    with pytest.raises(ValueError, match="own character|never"):
        SeatSpec("Plum", "character", "david")
    with pytest.raises(ValueError, match="needs a name"):
        SeatSpec("Plum", "human", "")
    with pytest.raises(ValueError, match="open seat"):
        SeatSpec("Plum", "open", "someone")


def test_an_all_human_table_needs_no_roster_at_all():
    setup = TableSetup.from_roster((), 3, SEED, humans={"Scarlett": "a", "Plum": "b", "White": "c"})
    assert setup.labels == ["a", "c", "b"]
    assert setup.external == frozenset({0, 1, 2})
    with pytest.raises(ValueError, match="will not fit"):
        TableSetup.from_roster((), 2, SEED, humans={"Scarlett": "a", "Plum": "b", "White": "c"})


def test_setup_validation_and_round_trip():
    seats = (SeatSpec("Plum", "character", "Plum"), SeatSpec("Scarlett", "human", "david"), SeatSpec("White", "open"))
    setup = TableSetup(seats, SEED, remember=True)
    assert setup.suspects == ["Scarlett", "White", "Plum"], "seats run in the board's order"
    assert setup.open_seats == [1] and setup.labels[1] == "floor"
    with pytest.raises(ValueError, match="open seat"):
        build_table(setup)
    dealt = setup.dealt()
    assert dealt.kinds == ["human", "floor", "character"] and dealt.remember
    again = TableSetup.from_dict(setup.to_dict())
    assert again == setup
    sat = setup.with_seat(1, SeatSpec("White", "human", "ann"))
    assert sat.external == frozenset({0, 1})
    with pytest.raises(ValueError, match="keeps its token"):
        setup.with_seat(1, SeatSpec("Green", "human", "ann"))
    with pytest.raises(ValueError, match="3 to 6"):
        TableSetup(seats[:2], SEED)
    with pytest.raises(ValueError, match="share a token"):
        TableSetup(seats + (SeatSpec("Plum", "floor"),), SEED)
    with pytest.raises(ValueError, match="two seats"):
        TableSetup((SeatSpec("Plum", "human", "d"), SeatSpec("Scarlett", "human", "d"), SeatSpec("White", "floor")), SEED)
    assert seat_specs(["floor", "Peacock"]) == (
        SeatSpec("Scarlett", "floor"), SeatSpec("Peacock", "character", "Peacock"),
    )


# --- 2. answers as data -------------------------------------------------------


def _request(kind, **fields):
    return DecisionRequest(seat=0, kind=kind, obs=None, **fields)


def test_every_answer_round_trips_including_a_stay_on_a_square():
    boxed = MoveChoice("stay", board.Square(7, 4))
    choices = [boxed, MoveChoice("move", "Kitchen"), MoveChoice("secret_passage", "Study"),
               MoveChoice("move", board.Square(8, 4)), MoveChoice("stay", "Lounge")]
    request = _request("movement", choices=choices)
    for choice in choices:
        data = encode_answer("movement", choice)
        assert decode_answer(request, data) == choice
    described = describe_request(request)
    assert described["kind"] == "movement" and len(described["options"]) == len(choices)
    assert described["options"][1]["room"] == "Kitchen" and described["options"][3]["room"] is None
    for option, choice in zip(described["options"], choices):
        assert decode_answer(request, option) == choice, "an option goes straight back as an answer"

    suggest = _request("suggestion", room="Hall")
    assert decode_answer(suggest, encode_answer("suggestion", None)) is None
    assert decode_answer(suggest, encode_answer("suggestion", ("Plum", "Rope"))) == ("Plum", "Rope")
    accuse = _request("accusation")
    assert decode_answer(accuse, None) is None
    assert decode_answer(accuse, encode_answer("accusation", ("Plum", "Rope", "Hall"))) == ("Plum", "Rope", "Hall")
    show = _request("card_to_show", candidates=["Hall", "Rope"], shown_to=2)
    assert decode_answer(show, encode_answer("card_to_show", "Rope")) == "Rope"
    assert describe_request(show) == {"seat": 0, "kind": "card_to_show", "candidates": ["Hall", "Rope"], "shown_to": 2}


def test_bad_answers_are_refused_with_a_message():
    request = _request("movement", choices=[MoveChoice("move", "Kitchen")])
    with pytest.raises(TableError, match="not one of the moves"):
        decode_answer(request, {"move": "move", "to": "Lounge"})
    with pytest.raises(TableError, match="shape"):
        decode_answer(request, {"nonsense": 1})
    with pytest.raises(TableError, match="shape"):
        decode_answer(request, "Kitchen")
    with pytest.raises(TableError, match="suspect and a weapon"):
        decode_answer(_request("suggestion", room="Hall"), {"suspect": "Nobody", "weapon": "Rope"})
    with pytest.raises(TableError, match="suspect, a weapon and a room"):
        decode_answer(_request("accusation"), {"suspect": "Plum", "weapon": "Rope", "room": "Attic"})
    with pytest.raises(TableError, match="must show one of: Hall, Rope"):
        decode_answer(_request("card_to_show", candidates=["Hall", "Rope"], shown_to=1), {"card": "Plum"})


# --- 3. a seat answered from outside ------------------------------------------


def test_a_human_seat_answered_from_a_recorded_game_reproduces_it():
    setup = human_setup()
    state, events, log = reference_game(setup, [3])
    assert isinstance(events[-1], GameOverEvent)
    kinds = {kind for _seat, kind, _answer in log}
    assert "card_to_show" in kinds, "the sample game must ask the human to refute off-turn"

    game = TableGame(setup)
    assert game.pending is None and game.snapshot.seq == 0
    play_from_log(game, log)
    assert _events(game) == [repr(e) for e in events]
    assert game.state.envelope == state.envelope
    assert len(game.entries) == len(log)
    assert all(entry["by"] == "human" for entry in game.entries)
    assert [entry["decision"] for entry in game.entries] == [kind for _s, kind, _a in log]
    assert game.snapshot.finished and game.snapshot.n_events == len(events)


def test_two_humans_refute_each_other_off_turn():
    setup = human_setup(roster=("Mustard",), n_players=3, humans={"Scarlett": "ann", "Plum": "bob"})
    assert setup.external == frozenset({0, 2})
    _state, events, log = reference_game(setup, [0, 2])
    shows = [(seat, kind) for seat, kind, _a in log if kind == "card_to_show"]
    assert {seat for seat, _k in shows} == {0, 2}, "each person is asked to show a card on another's turn"
    game = TableGame(setup)
    play_from_log(game, log)
    assert _events(game) == [repr(e) for e in events]


def test_a_rebuilt_table_matches_the_live_one_at_every_pause():
    setup = human_setup()
    _state, _ev, log = reference_game(setup, [3])
    game = TableGame(setup)
    pauses = 0

    def check(live: TableGame):
        nonlocal pauses
        pauses += 1
        if pauses % 4:
            return
        again = TableGame.rebuild(setup, list(live.entries), live.turns)
        assert again.turns == live.turns
        assert again.entries == live.entries
        assert _events(again) == _events(live)
        assert (again.pending is None) == (live.pending is None)
        if live.pending is not None:
            assert (again.pending.seat, again.pending.kind) == (live.pending.seat, live.pending.kind)
            assert again.pending.choices == live.pending.choices
            assert again.pending.candidates == live.pending.candidates
        assert again.snapshot == live.snapshot

    play_from_log(game, log, check)
    assert pauses >= 4
    final = TableGame.rebuild(setup, list(game.entries), game.turns)
    assert final.finished and _events(final) == _events(game)


def test_a_rebuild_stops_where_the_stored_turn_count_says():
    setup = human_setup()
    game = TableGame(setup)
    game.run(3)
    assert game.turns <= 3
    # The human (seat 3) has not been asked yet in three turns from seat 0.
    assert game.pending is None or game.pending.seat == 3
    again = TableGame.rebuild(setup, list(game.entries), game.turns)
    assert again.turns == game.turns and _events(again) == _events(game)


def test_a_corrupt_log_is_reported_not_replayed():
    setup = human_setup()
    _state, _ev, log = reference_game(setup, [3])
    game = TableGame(setup)
    play_from_log(game, log)
    entries = list(game.entries)
    entries[0] = dict(entries[0], decision="accusation")
    with pytest.raises(TableError, match="entry 0"):
        TableGame.rebuild(setup, entries, game.turns)


# --- 4. refusals leave the game alive ----------------------------------------


def test_a_bad_answer_is_refused_and_the_game_goes_on():
    setup = human_setup()
    game = TableGame(setup)
    while game.pending is None:
        game.run(1)
    request = game.pending
    before = (list(game.entries), _events(game), game.turns, game.snapshot)

    with pytest.raises(TableError, match="out of date"):
        game.answer(request.seat, game.seq + 1, {"move": "move", "to": "Kitchen"})
    with pytest.raises(TableError, match="not this seat"):
        game.answer((request.seat + 1) % 4, game.seq, {"move": "move", "to": "Kitchen"})
    if request.kind == "movement":
        with pytest.raises(TableError, match="not one of the moves"):
            game.answer(request.seat, game.seq, {"move": "move", "to": "Attic"})
    assert game.pending is request
    assert (list(game.entries), _events(game), game.turns, game.snapshot) == before
    assert not game.broken

    game.autopilot()
    assert game.pending is not request
    assert game.entries[-1]["by"] == "autopilot"


def test_a_card_the_seat_does_not_hold_is_refused():
    setup = human_setup()
    game = TableGame(setup)
    while not (game.pending is not None and game.pending.kind == "card_to_show"):
        if game.pending is not None:
            game.autopilot()
        else:
            game.run(1)
        assert not game.finished, "the sample game never asked the human to refute"
    request = game.pending
    held = set(request.obs.own_hand)
    not_held = next(c for c in SUSPECTS + WEAPONS + ROOMS if c not in held)
    with pytest.raises(TableError, match="must show one of"):
        game.answer(request.seat, game.seq, {"card": not_held})
    assert game.pending is request and not game.broken
    game.answer(request.seat, game.seq, {"card": request.candidates[0]})
    assert game.pending is not request


def test_check_answer_is_public_and_the_generator_is_never_asked_to_refuse():
    request = _request("card_to_show", candidates=["Hall"], shown_to=1)
    assert engine.check_answer(request, "Hall") == "Hall"
    with pytest.raises(ValueError, match="must show one of"):
        engine.check_answer(request, "Rope")
    assert engine._checked is engine.check_answer


# --- 5. autopilot -------------------------------------------------------------


def test_autopilot_answers_are_stored_and_a_rebuild_needs_no_stand_in():
    setup = human_setup()
    game = TableGame(setup)
    while not game.finished:
        if game.pending is None:
            game.run(1)
        else:
            game.autopilot()
    assert game.entries and all(entry["by"] == "autopilot" for entry in game.entries)
    again = TableGame.rebuild(setup, list(game.entries), game.turns)
    assert again.finished and _events(again) == _events(game)
    assert again._stand_ins == {}, "the rebuild replayed the stored answers, it did not ask the stand-in"


def test_the_stand_in_is_deterministic_per_game_and_seat():
    setup = human_setup()
    first, second = TableGame(setup), TableGame(setup)
    for game in (first, second):
        while game.pending is None:
            game.run(1)
    assert first.stand_in_answer() == second.stand_in_answer()


# --- 6. the turn slice --------------------------------------------------------


def test_turn_events_cover_the_last_completed_turn_only():
    setup = human_setup()
    game = TableGame(setup)
    seen: list = []
    while not game.finished:
        if game.pending is None:
            before = game.turns
            game.run(1)
            if game.turns == before + 1:
                seen.append(game.turn_events())
        else:
            game.autopilot()
            if game.turns and game.pending is None and (not seen or seen[-1] is not game.turn_events()):
                pass
    marks = [len(t) for t in seen]
    assert all(m >= 1 for m in marks), "every completed turn has at least its move event"
    assert sum(marks) <= len(game.events)


def test_remarks_are_logged_as_entries_and_replayed_in_place():
    setup = human_setup()
    game = TableGame(setup)
    game.run(2)
    game.remark(3, "I have nothing to hide.", about="chat")
    at = game.entries[-1]["at"]
    assert game.events[at].text == "I have nothing to hide." and game.events[at].about == "chat"
    while not game.finished:
        if game.pending is None:
            game.run(1)
        else:
            game.autopilot()
    again = TableGame.rebuild(setup, list(game.entries), game.turns)
    assert _events(again) == _events(game)
    assert again.events[at].text == "I have nothing to hide."


def test_a_reference_game_with_a_different_inner_player_still_replays():
    """The driver does not care how the answers were chosen."""

    class Suggester(Fixed):
        def choose_suggestion(self, obs, room, rng):
            return random.Random(len(obs.suggestion_log)).choice(SUSPECTS), WEAPONS[0]

    setup = human_setup(max_turns=60)
    _state, events, log = reference_game(setup, [3], inner=Suggester)
    game = TableGame(setup)
    play_from_log(game, log)
    assert _events(game) == [repr(e) for e in events]
    assert isinstance(dataclasses.replace(game.events[-1]), type(events[-1]))


# --- 7. the terminal seat -----------------------------------------------------


def test_play_human_from_the_terminal(monkeypatch, capsys):
    """``play --human`` drives a `TableGame` from the keyboard: every
    prompt is answered by a script here, the person is asked to refute
    on another seat's turn, and the game reaches its end."""
    import argparse

    from tests.test_web_watch import cli_module

    cli = cli_module()
    answers = {"move> ": "A", "suggest> ": "pass", "accuse> ": "pass", "show> ": "A"}
    asked: list = []

    def scripted_input(prompt=""):
        asked.append(prompt)
        for key, value in answers.items():
            if prompt.startswith(key):
                return value
        raise AssertionError(f"unexpected prompt {prompt!r}")

    monkeypatch.setattr("builtins.input", scripted_input)
    args = argparse.Namespace(
        players=3, roster="Mustard,White", seed=7, max_turns=40, human="Scarlett", name="david",
        llm=False, store="", logbook=None, verbose=False, hands=False,
    )
    assert cli.cmd_play(args) == 0
    out = capsys.readouterr().out
    assert "you=david" in out and "Envelope:" in out and "Turns played:" in out
    assert any(p.startswith("move> ") for p in asked)
    assert any(p.startswith("show> ") for p in asked), "the person was asked to refute off-turn"
    assert "showed a card (hidden)" in out or "showed" in out


def test_play_human_refuses_the_llm_and_store_flags():
    import argparse

    from tests.test_web_watch import cli_module

    cli = cli_module()
    args = argparse.Namespace(
        players=3, roster="Mustard,White", seed=7, max_turns=40, human="Scarlett", name="david",
        llm=True, store="", logbook=None, verbose=False, hands=False,
    )
    with pytest.raises(SystemExit, match="plain table"):
        cli.cmd_play(args)
