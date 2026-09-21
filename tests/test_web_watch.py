"""The lobby and the Watch screen (Phase 8.1a, step 5).

Three things are pinned here that matter more than any layout:

1. **Without stored memory, Watch plays the same game as `clude_cli.py play`.**
   `headless_table` was lifted out of the CLI's private `_play_game`, and
   a watched game is that table driven a turn at a time through the
   engine seam. Both halves are checked against the originals.
2. **A watched game survives losing its process.** The setup, memory
   snapshot and turn count rebuild the live game exactly.
3. **A watched game gives nothing away.** Hands and the envelope stay
   hidden until the end (`docs/phase8.1-plan.md` 3.2), and a refutation
   names who disproved a suggestion, never the card they showed.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pytest
from werkzeug.datastructures import MultiDict

from clude_core import engine
from clude_core.domain import ALL_CARDS
from clude_core.events import GameOverEvent, SuggestionEvent
from clude_storage import GameRecord, open_store
from clude_training.arena import headless_table
from clude_web import create_app, users, watch

NAME = "watcher"
PASSWORD = "watcher-password"

ROSTER = ("Scarlett", "Mustard", "White")
"""Fast on purpose: a whole game at four seats takes under a second.
Plum takes about 7 s a game and Green 12 s, so they get one capped case
of their own below rather than riding along in every test."""
SEED = 7


def cli_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "clude_cli.py"
    spec = importlib.util.spec_from_file_location("clude_cli_for_watch", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def play_via_cli(roster, n_players, seed, max_turns=watch.MAX_TURNS):
    """The game ``clude_cli.py play --roster ... --players ... --seed ...``
    plays, through the CLI's own code, not a copy of it."""
    cli = cli_module()
    args = argparse.Namespace(
        players=n_players,
        roster=",".join(roster),
        seed=seed,
        max_turns=max_turns,
        llm=False,
        logbook=None,
        store="",
    )
    state, events, labels = cli._play_game(args)
    return state, events, labels


@pytest.fixture
def store(tmp_path):
    return open_store(str(tmp_path))


@pytest.fixture
def app(tmp_path, store):
    users.add_user(store, NAME, PASSWORD)
    users.mark_password_prompted(store, NAME)
    return create_app({"TESTING": True, "STORE_URI": str(tmp_path)})


@pytest.fixture
def client(app):
    client = app.test_client()
    page = client.get("/login").get_data(as_text=True)
    token = page.split('name="csrf" value="')[1].split('"')[0]
    client.post("/login", data={"name": NAME, "password": PASSWORD, "csrf": token})
    return client


def csrf(client) -> str:
    page = client.get("/").get_data(as_text=True)
    return page.split('name="csrf" value="')[1].split('"')[0]


def deal(client, characters=ROSTER, n_players=4, seed=SEED):
    """POST the lobby's form; returns the watch id it redirected to."""
    response = client.post(
        "/watch",
        data=MultiDict(
            [("csrf", csrf(client)), ("n_players", str(n_players)), ("seed", str(seed))]
            + [("characters", name) for name in characters]
        ),
    )
    assert response.status_code == 302, response.get_data(as_text=True)[:300]
    return response.headers["Location"].rstrip("/").split("/")[-1]


# --- 1. the same game as `play` -------------------------------------------


@pytest.mark.parametrize(
    "roster,n_players,seed,max_turns",
    [
        (("Scarlett", "Mustard", "White"), 4, 7, watch.MAX_TURNS),
        (("Mustard", "White"), 3, 2, watch.MAX_TURNS),
        (("Peacock",), 5, 19, watch.MAX_TURNS),
        # Every character at one table, capped. Plum's and Green's early
        # turns are their slowest (a 12-turn cap still cost 19 s), and the
        # table is built the same way for all six, so six turns is enough
        # to prove each is seated, reset and told its company as `play`
        # does it -- in about 2 s.
        (("Scarlett", "Mustard", "White", "Green", "Peacock", "Plum"), 6, 7, 6),
    ],
)
def test_the_headless_table_plays_what_play_plays(roster, n_players, seed, max_turns):
    state, events, labels = play_via_cli(roster, n_players, seed, max_turns)
    table = headless_table(roster, n_players, seed)
    mine_state, mine_events = engine.run_game(
        n_players, table.players, seed=seed, max_turns=max_turns,
        observer=table.observer, suspects=table.suspects,
    )

    assert table.labels == labels
    assert mine_events == events
    assert mine_state.envelope == state.envelope


def test_a_watched_game_turn_by_turn_is_the_whole_game():
    setup = watch.WatchSetup(roster=ROSTER, n_players=4, seed=SEED)
    game = watch.WatchGame(setup)
    while not game.finished:
        assert game.advance(1) in (0, 1)
    _state, events, _labels = play_via_cli(ROSTER, 4, SEED)

    assert game.events == events
    assert isinstance(game.events[-1], GameOverEvent)


def test_the_last_turn_says_the_game_is_over():
    """No click that plays nothing: the turn that ends the game is the
    one that reports it."""
    setup = watch.WatchSetup(roster=ROSTER, n_players=4, seed=SEED)
    game = watch.WatchGame(setup)
    while not game.finished:
        before = game.turns
        game.advance(1)
        if game.finished:
            assert game.turns == before + 1, "a click finished the game without playing a turn"


def test_a_turn_cap_ends_the_game_too():
    setup = watch.WatchSetup(roster=ROSTER, n_players=4, seed=SEED, max_turns=5)
    game = watch.WatchGame(setup)

    game.play_to_end()

    assert game.finished
    assert game.turns <= 5
    assert isinstance(game.events[-1], GameOverEvent)


# --- 2. surviving a cold start -------------------------------------------


def test_a_rebuilt_game_matches_the_live_one(store):
    registry = watch.WatchRegistry(store)
    setup = watch.WatchSetup(roster=ROSTER, n_players=4, seed=SEED)
    watch_id = registry.create(setup, "someone")
    live = registry.game(watch_id)
    live.advance(12)
    registry.save(watch_id, live)

    cold = watch.WatchRegistry(store).game(watch_id)  # a fresh process

    assert cold is not live
    assert cold.turns == live.turns == 12
    assert cold.events == live.events
    assert cold.state.positions == live.state.positions
    assert cold.readings() == live.readings(), "a reading must be a pure function of the game"


def test_an_unknown_game_is_none_not_a_crash(store):
    registry = watch.WatchRegistry(store)

    assert registry.game("0000000000") is None
    assert registry.game("../escape") is None


# --- 3. giving nothing away ------------------------------------------------


def test_a_reading_names_no_card():
    """The compact bar is counts and confidences only. (A seat's own
    suspect name is also a card name, so this checks the shape rather
    than scanning for names.)"""
    game = watch.WatchGame(watch.WatchSetup(roster=ROSTER, n_players=4, seed=SEED))
    game.advance(15)

    for reading in game.readings():
        assert set(reading) == {
            "seat", "suspect", "label", "method", "active", "placed", "total", "groups",
        }
        for group in reading["groups"]:
            assert set(group) == {"name", "size", "placed", "solved", "confidence"}
            assert group["name"] in ("suspects", "weapons", "rooms")


def test_a_reading_counts_the_seat_s_own_hand_as_placed():
    game = watch.WatchGame(watch.WatchSetup(roster=ROSTER, n_players=4, seed=SEED))
    for reading in game.readings():
        hand = game.state.hands[reading["seat"]]
        assert reading["placed"] >= len(hand)
        assert reading["total"] == len(ALL_CARDS)


def test_the_watch_page_never_names_a_shown_card(client, app):
    watch_id = deal(client)
    game = app.extensions["watch"].game(watch_id)

    shown_so_far = []
    for _ in range(25):
        client.post(f"/watch/{watch_id}/next", data={"csrf": csrf(client)})
        if game.finished:
            break
        page = client.get(f"/watch/{watch_id}").get_data(as_text=True)
        shown_so_far = [
            e.suggestion for e in game.events
            if isinstance(e, SuggestionEvent) and e.suggestion.card_shown
        ]
        assert " showed " not in page, "a refutation named the card shown"
        assert "Holds:" not in page, "a hand was listed"
        assert "data-card=" not in page, "a per-card bar leaked in"
        assert "It was " not in page, "the envelope was announced"
    assert shown_so_far, "the sample never produced a refutation to hide"


def test_watch_remembers_by_default_and_preserves_an_opt_out(client, app):
    fields = [("csrf", csrf(client)), ("characters", "White"), ("n_players", "3"), ("seed", "7")]
    for value in (None, "0"):
        form = MultiDict(fields + ([] if value is None else [("remember", value)]))
        response = client.post("/watch", data=form)
        assert response.status_code == 302
        table_id = response.headers["Location"].rstrip("/").split("/")[-1]
        assert app.extensions["tables"].document(table_id)["setup"]["remember"] == (value is None)
    form["seed"] = "bad"
    response = client.post("/watch", data=form)
    assert response.status_code == 400
    checkbox = response.get_data(as_text=True).split('id="watch-remember"')[1].split(">", 1)[0]
    assert "checked" not in checkbox


def test_the_lobby_form_rejects_what_it_should(client):
    cases = [
        ([], 4, "7", "Pick at least one character"),
        (["Scarlett", "Plum", "Green", "White"], 3, "7", "will not fit"),
        (["Scarlett"], 9, "7", "from 3 to 6"),
        (["Scarlett"], 4, "seven", "whole number"),
    ]
    for characters, n_players, seed, message in cases:
        response = client.post(
            "/watch",
            data=MultiDict(
                [("csrf", csrf(client)), ("n_players", str(n_players)), ("seed", seed)]
                + [("characters", c) for c in characters]
            ),
        )
        assert response.status_code == 400
        assert message in response.get_data(as_text=True)


def test_a_blank_seed_deals_a_random_one():
    form = MultiDict([("characters", "Scarlett"), ("n_players", "3"), ("seed", "")])

    assert isinstance(watch.parse_setup(form).seed, int)


def test_characters_are_seat_locked_in_a_watched_game():
    game = watch.WatchGame(watch.WatchSetup(roster=("Plum", "Scarlett"), n_players=4, seed=1))

    for label, suspect in zip(game.table.labels, game.table.suspects):
        if label != "floor":
            assert label == suspect, f"{label} was seated at {suspect}'s token"


# --- the screens ----------------------------------------------------------


def test_dealing_opens_a_game_at_turn_zero(client):
    watch_id = deal(client)
    page = client.get(f"/watch/{watch_id}").get_data(as_text=True)

    assert "Turn 0" in page
    assert page.count('class="seat compact') == 4
    assert page.count('class="board-token') == 4


def test_next_turn_plays_exactly_one_turn(client, app, store):
    watch_id = deal(client)
    registry = app.extensions["watch"]

    for expected in (1, 2, 3):
        client.post(f"/watch/{watch_id}/next", data={"csrf": csrf(client)})
        assert registry.game(watch_id).turns == expected
        assert registry.document(watch_id)["turns"] == expected, "the turn count was not saved"


def test_playing_to_the_end_opens_the_replay(client, store):
    watch_id = deal(client)

    response = client.post(f"/watch/{watch_id}/end", data={"csrf": csrf(client)})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/replay/web/0")
    record = GameRecord.from_dict(store.get_game("web", 0))
    assert isinstance(record.events[-1], GameOverEvent)
    assert [s.label for s in record.seats][:1]  # seats recorded
    assert client.get("/replay/web/0").status_code == 200


def test_a_finished_game_is_saved_once(client, store):
    watch_id = deal(client)
    client.post(f"/watch/{watch_id}/end", data={"csrf": csrf(client)})

    again = client.get(f"/watch/{watch_id}")
    client.post(f"/watch/{watch_id}/end", data={"csrf": csrf(client)})

    assert again.headers["Location"].endswith("/replay/web/0")
    assert store.list_games("web") == [0], "the same game was saved twice"


def test_a_second_game_gets_the_next_index(client, store):
    for _ in range(2):
        watch_id = deal(client, seed=SEED)
        client.post(f"/watch/{watch_id}/end", data={"csrf": csrf(client)})

    assert store.list_games("web") == [0, 1]
    assert store.get_run("web")["n_games"] == 2


def test_the_lobby_lists_games_in_progress_and_played(client, store):
    watch_id = deal(client)
    page = client.get("/").get_data(as_text=True)
    assert f"/watch/{watch_id}" in page, "an unfinished game is not listed"

    client.post(f"/watch/{watch_id}/end", data={"csrf": csrf(client)})
    page = client.get("/").get_data(as_text=True)
    assert f"/watch/{watch_id}" not in page, "a finished game is still listed as in progress"
    assert "/runs/web" in page

    run_page = client.get("/runs/web").get_data(as_text=True)
    assert "/replay/web/0" in run_page


def test_an_unknown_game_or_run_is_a_404(client):
    assert client.get("/watch/0000000000").status_code == 404
    assert client.post("/watch/0000000000/next", data={"csrf": csrf(client)}).status_code == 404
    assert client.get("/runs/no-such-run").status_code == 404


def test_the_watch_screens_need_a_session(app):
    anonymous = app.test_client()

    for path in ("/watch/0000000000", "/runs/web"):
        response = anonymous.get(path)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]
