"""Tables people play at (Phase 8.2b-c, docs/phase8-plan.md 3.2-3.5).

Pinned here: that a person can sit at a table beside the characters and
play a whole game through the app's JSON routes (poll, work, answer);
that each viewer sees only what their seat may -- the card shown at a
refutation named to the two seats involved and to nobody else, a hand
and a notepad only for the seat's owner; that a bad answer is a 400 and
the game goes on; that a cold registry rebuilds a table exactly, its
pending decision included; that open seats, sitting, dealing and
autopilot work; that a finished game is recorded with ``kind="human"``
under the account key; that reserved names are refused; and that
"characters remember" writes White's counts under the human's label and
keeps Green's learning when two tables finish.
"""
from __future__ import annotations

import json

import pytest
from werkzeug.datastructures import MultiDict

from clude_core.events import GameOverEvent, SuggestionEvent
from clude_storage import GameRecord, Logbook, open_store
from clude_training import memory as method_memory
from clude_core.domain import ROOMS, SUSPECTS, WEAPONS
from clude_training.table import SeatSpec, TableSetup
from clude_web import create_app, tables, users

ANN, BOB, CAT = "ann", "bob", "cat"
PASSWORD = "pw"
SEED = 7


@pytest.fixture
def store(tmp_path):
    return open_store(str(tmp_path))


@pytest.fixture
def app(tmp_path, store):
    for name in (ANN, BOB, CAT):
        users.add_user(store, name, PASSWORD)
        users.mark_password_prompted(store, name)
    return create_app({"TESTING": True, "STORE_URI": str(tmp_path)})


def login(app, name):
    client = app.test_client()
    page = client.get("/login").get_data(as_text=True)
    token = page.split('name="csrf" value="')[1].split('"')[0]
    client.post("/login", data={"name": name, "password": PASSWORD, "csrf": token})
    return client


@pytest.fixture
def ann(app):
    return login(app, ANN)


@pytest.fixture
def bob(app):
    return login(app, BOB)


@pytest.fixture
def cat(app):
    return login(app, CAT)


def csrf(client) -> str:
    page = client.get("/").get_data(as_text=True)
    return page.split('name="csrf" value="')[1].split('"')[0]


def new_table(client, seats: dict, seed=SEED, remember=False, expect=302):
    """POST the lobby's table form; returns the table id, or the response
    when `expect` is not a redirect. Tests opt out of persistent memory
    unless requested; ``remember=None`` exercises the app's default."""
    fields = [("csrf", csrf(client)), ("seed", str(seed))]
    if remember is not None:
        fields.append(("remember", "1" if remember else "0"))
    for token, value in seats.items():
        fields.append((f"seat-{token}", value))
    response = client.post("/tables", data=MultiDict(fields))
    assert response.status_code == expect, response.get_data(as_text=True)[:400]
    if expect != 302:
        return response
    return response.headers["Location"].rstrip("/").split("/")[-1]


def poll(client, table_id, since=0):
    response = client.get(f"/tables/{table_id}/poll?since={since}")
    assert response.status_code == 200, response.get_data(as_text=True)[:300]
    return response.get_json()


def work(client, table_id):
    response = client.post(f"/tables/{table_id}/work", data={"csrf": csrf(client)})
    assert response.status_code == 200, response.get_data(as_text=True)[:300]
    return response.get_json()


def answer(client, table_id, seq, data, expect=200):
    response = client.post(
        f"/tables/{table_id}/answer",
        data={"csrf": csrf(client), "seq": str(seq), "data": json.dumps(data)},
    )
    assert response.status_code == expect, response.get_data(as_text=True)[:300]
    return response.get_json()


def simple_answer(pending: dict):
    """A legal answer to any decision: the first move, a fixed
    suggestion, no accusation, the first card."""
    kind = pending["kind"]
    if kind == "movement":
        option = pending["options"][0]
        return {"move": option["move"], "to": option["to"]}
    if kind == "suggestion":
        return {"suspect": "Plum", "weapon": "Rope"}
    if kind == "accusation":
        return None
    return {"card": pending["candidates"][0]}


def play_out(app, table_id, clients: dict, max_steps=4000, on_payload=None):
    """Drive a table to its end through the JSON routes: whoever the game
    waits on answers, and anyone fires the bot work. `clients` maps an
    account key to its client."""
    tables.WORK_INTERVAL, saved = 0.0, tables.WORK_INTERVAL
    try:
        first = next(iter(clients.values()))
        payload = poll(first, table_id)
        for _ in range(max_steps):
            if on_payload is not None:
                on_payload(payload)
            if payload["finished"]:
                return payload
            if payload["work"]:
                payload = work(first, table_id)
            elif payload["waiting"] is not None:
                who = payload["waiting"]["seat"]
                seat = next(s for s in payload["seats"] if s["seat"] == who)
                owner = clients[seat["label"]]
                mine = poll(owner, table_id)
                assert mine["pending"] is not None, "the owner was not shown the decision"
                payload = answer(owner, table_id, mine["pending"]["seq"], simple_answer(mine["pending"]))
            else:
                payload = poll(first, table_id)
        raise AssertionError("the game did not end")
    finally:
        tables.WORK_INTERVAL = saved


# --- the form -------------------------------------------------------------


def test_remembering_defaults_on_and_an_unchecked_form_stays_off(ann, app):
    page = ann.get("/").get_data(as_text=True)
    assert 'value="1" checked' in page.split('id="remember"')[1].split(">", 1)[0]
    seats = {"Scarlett": "me", "White": "character", "Plum": "open"}
    table_id = new_table(ann, seats, remember=None)
    assert app.extensions["tables"].document(table_id)["setup"]["remember"] is True
    table_id = new_table(ann, seats, remember=False)
    assert app.extensions["tables"].document(table_id)["setup"]["remember"] is False
    for value in ("0", "1"):
        invalid = ann.post("/tables", data={"csrf": csrf(ann), "remember": value})
        assert invalid.status_code == 400
        checkbox = invalid.get_data(as_text=True).split('id="remember"')[1].split(">", 1)[0]
        assert ("checked" in checkbox) == (value == "1")
    assert tables.remember_from_form(MultiDict([("remember", "1"), ("remember", "0")]))
    assert not tables.remember_from_form(MultiDict([("remember", "0")]))


def test_the_table_form_rejects_what_it_should(ann):
    cases = [
        ({"Scarlett": "me", "Mustard": "me", "White": "character"}, "only sit in one seat"),
        ({"Scarlett": "me", "Mustard": "character"}, "seats 3 to 6"),
        ({}, "Pick who sits"),
        ({"Scarlett": "me", "Mustard": "character", "White": "wizard"}, "unknown occupant"),
    ]
    for seats, message in cases:
        response = new_table(ann, seats, expect=400)
        assert message in response.get_data(as_text=True), message
    response = ann.post(
        "/tables",
        data=MultiDict([("csrf", csrf(ann)), ("seed", "seven"), ("seat-Scarlett", "me"),
                        ("seat-Mustard", "character"), ("seat-White", "character")]),
    )
    assert response.status_code == 400 and "whole number" in response.get_data(as_text=True)


def test_a_dealt_table_opens_on_the_play_view(ann, app):
    table_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "character", "Green": "floor"})
    page = ann.get(f"/tables/{table_id}").get_data(as_text=True)
    assert 'id="decision"' in page and 'id="table-data"' in page and 'id="notepad"' in page
    payload = json.loads(page.split('id="table-data" type="application/json">')[1].split("</script>")[0])
    assert payload["me"]["seat"] == 0 and payload["me"]["token"] == "Scarlett"
    assert len(payload["me"]["hand"]) == 5 or len(payload["me"]["hand"]) == 4
    assert payload["seats"][0] == {
        "seat": 0, "token": "Scarlett", "label": ANN, "name": "Scarlett (ann)", "kind": "human",
        "active": True, "autopilot": False, "me": True,
    }
    assert [s["kind"] for s in payload["seats"]] == ["human", "character", "character", "floor"]
    assert len(payload["notepad"]) == 21 and all(r["holder"] in (0, None, "envelope", 1, 2, 3) for r in payload["notepad"])
    mine = {r["card"] for r in payload["notepad"] if r["holder"] == 0}
    assert mine == set(payload["me"]["hand"]), "my own cards are proven mine on the notepad"
    assert payload["work"] is True and payload["pending"] is None or payload["pending"]["seat"] == 0


def test_a_spectator_sees_no_hand_and_no_notepad(ann, cat):
    table_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "character"})
    page = cat.get(f"/tables/{table_id}").get_data(as_text=True)
    assert 'id="decision"' not in page and 'id="notepad"' not in page and 'id="hand"' not in page
    payload = poll(cat, table_id)
    assert payload["me"] is None and payload["notepad"] is None and payload["pending"] is None
    assert "spectating" in page


def test_a_seated_player_gets_no_deduction_bars_and_a_spectator_does(ann, cat):
    """Phase 9d (David, 2026-09-22). At a real table nobody can see how
    close another player is to solving it, so a seated viewer gets no
    readings -- only who is at the table. Someone watching still does:
    the bars are what Watch is for. Skipping them also spares a fresh
    belief per poll.
    """
    table_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "character"})
    assert poll(ann, table_id)["readings"] is None
    watching = poll(cat, table_id)
    assert watching["readings"] is not None
    assert [r["seat"] for r in watching["readings"]] == [0, 1, 2]
    assert all("groups" in r for r in watching["readings"])

    page = ann.get(f"/tables/{table_id}").get_data(as_text=True)
    assert "how many of the 21 cards it has placed" not in page
    assert "how many of the 21 cards it has placed" in cat.get(f"/tables/{table_id}").get_data(as_text=True)


def test_events_say_whether_a_line_was_talk_and_moves_carry_room_distances(app, ann):
    """Phase 9d. `about` tells chat from narration, so the screen can put
    table talk in its own panel; `distances` says, for each move on
    offer, how far every room would then be -- what the chat seat asked
    for and what a tooltip gives a person.
    """
    table_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "character"})
    game = app.extensions["tables"].game(table_id)
    game.remark(0, "Anyone been in the Study?", "chat")

    payload = poll(ann, table_id)
    talk = [e for e in payload["events"] if e["kind"] == "remark"]
    assert talk and talk[-1]["about"] == "chat"
    assert all("about" in e for e in payload["events"])
    assert all(e["about"] is None for e in payload["events"] if e["kind"] == "move")

    while payload["pending"] is None and not payload["finished"]:
        payload = work(ann, table_id)
    pending = payload["pending"]
    assert pending["kind"] == "movement"
    for option in pending["options"]:
        assert option["distances"], option
        if option["room"]:
            assert option["distances"].startswith("in the " + option["room"])
        else:
            # A corridor square: every room, nearest first.
            steps = [int(part.rsplit(" ", 1)[1]) for part in option["distances"].split(", ")]
            assert steps == sorted(steps) and len(steps) == 9
    assert payload["me"]["at"] is not None


# --- playing ----------------------------------------------------------------


def test_two_people_play_a_table_to_the_end(app, store, ann, bob, cat):
    table_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "character", "Green": "open"})
    assert ann.get(f"/tables/{table_id}").status_code == 200
    page = ann.get("/").get_data(as_text=True)
    assert "waiting for 1 more" in page and "you are seated" in page

    response = bob.post(f"/tables/{table_id}/sit", data={"csrf": csrf(bob), "token": "Green"})
    assert response.status_code == 302
    assert bob.post(f"/tables/{table_id}/sit", data={"csrf": csrf(bob), "token": "Green"}).status_code == 400
    assert cat.post(f"/tables/{table_id}/deal", data={"csrf": csrf(cat)}).status_code == 403
    assert ann.post(f"/tables/{table_id}/deal", data={"csrf": csrf(ann)}).status_code == 302

    game = app.extensions["tables"].game(table_id)
    assert game.kinds == ["human", "character", "character", "human"]
    seen_by = {ANN: {}, BOB: {}, CAT: {}}

    def watch_lines(_payload):
        for key, client in ((ANN, ann), (BOB, bob), (CAT, cat)):
            for line in poll(client, table_id)["events"]:
                seen_by[key][line["i"]] = line["text"]

    final = play_out(app, table_id, {ANN: ann, BOB: bob}, on_payload=watch_lines)
    assert final["finished"] and final["over"] is not None
    assert final["over"]["replay"].endswith("/replay/web/0")
    watch_lines(final)

    shows = [
        (index, e.suggestion) for index, e in enumerate(game.events)
        if isinstance(e, SuggestionEvent) and e.suggestion.card_shown
    ]
    assert shows, "the sample game never showed a card"
    assert not any(" showed " in text for text in seen_by[CAT].values()), "a spectator saw a card shown"
    for index, s in shows:
        line = f"showed {s.card_shown}"
        involved = {game.labels[s.suggester], game.labels[s.refuter]}
        for key in (ANN, BOB):
            text = seen_by[key][index]
            if key in involved:
                assert line in text, f"{key} was involved and never saw {line}: {text}"
            else:
                assert line not in text and "disproved it" in text, f"{key} was not involved and saw {text}"

    record = GameRecord.from_dict(store.get_game("web", 0))
    assert isinstance(record.events[-1], GameOverEvent)
    assert [(s.kind, s.label) for s in sorted(record.seats, key=lambda s: s.seat)] == [
        ("human", ANN), ("character", "Mustard"), ("character", "White"), ("human", BOB),
    ]
    assert record.seats[0].profile is None
    assert ann.get("/replay/web/0").status_code == 200
    assert store.get_run("web")["roster"] == sorted([BOB, "Mustard", "White", ANN])
    assert ann.get(f"/tables/{table_id}").status_code == 302, "a finished table opens as its replay"


def test_a_bad_answer_is_a_400_and_the_game_goes_on(app, ann):
    table_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "character"})
    payload = poll(ann, table_id)
    while payload["pending"] is None:
        payload = work(ann, table_id) if payload["work"] else poll(ann, table_id)
        tables.WORK_INTERVAL = 0.0
    pending = payload["pending"]
    assert pending["kind"] == "movement" and pending["seat"] == 0
    bad = answer(ann, table_id, pending["seq"], {"move": "move", "to": "Attic"}, expect=400)
    assert "not one of the moves" in bad["error"]
    stale = answer(ann, table_id, pending["seq"] + 5, simple_answer(pending), expect=400)
    assert "out of date" in stale["error"]
    again = poll(ann, table_id)
    assert again["pending"] == pending and not again["broken"]
    good = answer(ann, table_id, pending["seq"], simple_answer(pending))
    assert good["seq"] == pending["seq"] + 1


def test_a_stranger_cannot_answer(app, ann, cat):
    table_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "character"})
    response = cat.post(
        f"/tables/{table_id}/answer",
        data={"csrf": csrf(cat), "seq": "0", "data": json.dumps({"move": "stay", "to": "Kitchen"})},
    )
    assert response.status_code == 403


def test_a_cold_registry_rebuilds_the_table_at_its_pending_decision(app, store, ann):
    tables.WORK_INTERVAL = 0.0
    table_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "character"})
    answered = 0
    payload = poll(ann, table_id)
    while answered < 3:
        if payload["pending"] is not None:
            payload = answer(ann, table_id, payload["pending"]["seq"], simple_answer(payload["pending"]))
            answered += 1
        elif payload["work"]:
            payload = work(ann, table_id)
        else:
            break
    live = app.extensions["tables"].game(table_id)
    while live.pending is None and not live.finished:
        payload = work(ann, table_id)

    cold = tables.TableRegistry(store).game(table_id)
    assert cold is not live
    assert cold.turns == live.turns and cold.entries == live.entries
    assert [repr(e) for e in cold.events] == [repr(e) for e in live.events]
    assert (cold.pending.seat, cold.pending.kind) == (live.pending.seat, live.pending.kind)
    assert cold.snapshot == live.snapshot
    assert cold.readings() == live.readings()


def test_autopilot_plays_the_seat_and_can_be_taken_back(app, store, ann):
    tables.WORK_INTERVAL = 0.0
    table_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "character"})
    response = ann.post(f"/tables/{table_id}/autopilot", data={"csrf": csrf(ann), "seat": "0", "on": "1"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["me"]["autopilot"] is True
    steps = 0
    while not payload["finished"] and steps < 3000:
        payload = work(ann, table_id)
        steps += 1
        assert payload["pending"] is None, "autopilot left a decision to the person"
    assert payload["finished"]
    game = app.extensions["tables"].game(table_id)
    assert game.entries and all(e["by"] == "autopilot" for e in game.entries)
    assert store.list_games("web") == [0]


def test_a_stranger_cannot_hand_a_seat_to_the_stand_in(app, ann, bob):
    table_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "character"})
    response = bob.post(f"/tables/{table_id}/autopilot", data={"csrf": csrf(bob), "seat": "0", "on": "1"})
    assert response.status_code == 403


def test_the_lobby_lists_tables_and_their_state(app, ann, bob):
    table_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "open"})
    page = bob.get("/").get_data(as_text=True)
    assert f"/tables/{table_id}" in page and "White (open)" in page and "ann as Scarlett" in page
    bob.post(f"/tables/{table_id}/sit", data={"csrf": csrf(bob), "token": "White"})
    page = bob.get(f"/tables/{table_id}").get_data(as_text=True)
    assert "bob (you)" in page and "Deal now" in page and "Leave the table" in page
    assert bob.post(f"/tables/{table_id}/leave", data={"csrf": csrf(bob)}).status_code == 302
    page = bob.get(f"/tables/{table_id}").get_data(as_text=True)
    assert "Sit here" in page and "Deal now" not in page


def test_an_open_table_is_not_dealt_until_every_open_seat_is_taken(app, ann, bob):
    """An open seat is reserved for someone (David, 2026-09-21): the deal
    is refused while one waits, and the button on the page is disabled."""
    table_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "open"})
    registry = app.extensions["tables"]
    assert registry.game(table_id) is None
    response = ann.post(f"/tables/{table_id}/deal", data={"csrf": csrf(ann)})
    assert response.status_code == 400 and "waiting for someone to sit as White" in response.get_data(as_text=True)
    page = ann.get(f"/tables/{table_id}").get_data(as_text=True)
    assert "disabled" in page.split("Deal now")[0].rsplit("<button", 1)[1]
    assert "dealt once every open seat is taken" in page
    assert registry.document(table_id)["status"] == "open"
    bob.post(f"/tables/{table_id}/sit", data={"csrf": csrf(bob), "token": "White"})
    assert ann.post(f"/tables/{table_id}/deal", data={"csrf": csrf(ann)}).status_code == 302
    assert registry.game(table_id).kinds == ["human", "character", "human"]


def test_a_table_can_be_ended_by_a_player_or_its_starter_and_leaves_the_lobby(app, store, ann, bob, cat):
    registry = app.extensions["tables"]
    table_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "open"})
    bob.post(f"/tables/{table_id}/sit", data={"csrf": csrf(bob), "token": "White"})
    ann.post(f"/tables/{table_id}/deal", data={"csrf": csrf(ann)})
    assert registry.game(table_id) is not None
    page = ann.get("/").get_data(as_text=True)
    assert "End table" in page
    assert "End table" not in cat.get("/").get_data(as_text=True)
    # A stranger cannot; a seated player can; the table is gone from the lobby and never recorded.
    assert cat.post(f"/tables/{table_id}/abandon", data={"csrf": csrf(cat)}).status_code == 403
    assert bob.post(f"/tables/{table_id}/abandon", data={"csrf": csrf(bob)}).status_code == 302
    document = registry.document(table_id)
    assert document["status"] == "abandoned" and document["abandoned_by"] == BOB
    assert registry.game(table_id) is None
    assert registry.in_progress() == []
    assert f"/tables/{table_id}" not in ann.get("/").get_data(as_text=True)
    assert ann.get(f"/tables/{table_id}").status_code == 404
    assert store.list_games("web") == []
    # The starter can end a Watch table too, and an open one; a second end is harmless.
    open_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "open"})
    assert ann.post(f"/tables/{open_id}/abandon", data={"csrf": csrf(ann)}).status_code == 302
    assert ann.post(f"/tables/{open_id}/abandon", data={"csrf": csrf(ann)}).status_code == 302
    assert registry.document(open_id)["status"] == "abandoned"
    # And the maintainer, from the CLI, with no account at all.
    cli_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "character"})
    tables.TableRegistry(store).abandon(cli_id)
    assert registry.document(cli_id)["status"] == "abandoned"


def test_a_seat_that_keeps_the_table_waiting_is_handed_to_the_stand_in(app, store, ann, monkeypatch):
    """After `AUTOPILOT_AFTER` seconds on a human seat, the next unit of
    work hands it over, flag and all, so a person who left never stalls
    the table (David, 2026-09-21)."""
    tables.WORK_INTERVAL = 0.0
    table_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "character"})
    registry = app.extensions["tables"]
    game = registry.game(table_id)
    payload = work(ann, table_id)  # the first turn: Scarlett's move, ours
    assert game.pending is not None and game.pending.seat == 0
    assert work(ann, table_id)["pending"] is not None, "handed over before the time was up"
    assert payload["me"]["autopilot"] is False
    monkeypatch.setattr(tables, "AUTOPILOT_AFTER", 0.0)
    payload = work(ann, table_id)
    assert payload["me"]["autopilot"] is True
    assert registry.document(table_id)["autopilot"] == {"0": True}
    steps = 0
    while not payload["finished"] and steps < 3000:
        payload = work(ann, table_id)
        steps += 1
        assert payload["pending"] is None, "the handed-over seat showed the person a decision"
    assert payload["finished"]
    assert all(e["by"] == "autopilot" for e in game.entries if e["seat"] == 0)


def test_a_player_who_is_out_is_answered_by_the_stand_in(app, store, ann):
    """A wrong accusation leaves a person only cards to show; the stand-in
    shows them, so the table never waits on someone who has left
    (David, 2026-09-21). The autopilot flag is not set: being out is
    its own reason."""
    tables.WORK_INTERVAL = 0.0
    table_id = new_table(ann, {"Scarlett": "me", "Mustard": "character", "White": "character"})
    registry = app.extensions["tables"]
    game = registry.game(table_id)
    hand = sorted(game.state.hands[0])
    accused = False
    payload = poll(ann, table_id)
    steps = 0
    while not payload["finished"] and steps < 3000:
        steps += 1
        pending = payload["pending"]
        if pending is None:
            payload = work(ann, table_id)
            continue
        assert not accused, "a player who is out was asked to decide"
        if pending["kind"] == "accusation":
            # Accuse with a card from our own hand: certainly wrong.
            suspect = next((c for c in hand if c in SUSPECTS), "Plum")
            weapon = next((c for c in hand if c in WEAPONS), "Rope")
            room = next((c for c in hand if c in ROOMS), "Hall")
            payload = answer(ann, table_id, pending["seq"], {"suspect": suspect, "weapon": weapon, "room": room})
            accused = True
        else:
            payload = answer(ann, table_id, pending["seq"], simple_answer(pending))
    assert accused and payload["finished"]
    assert not game.state.active[0]
    shown = [e for e in game.entries if e["seat"] == 0 and e["decision"] == "card_to_show" and e["by"] == "autopilot"]
    assert shown, "the stand-in never showed a card for the player who was out"
    assert not (registry.document(table_id).get("autopilot") or {}).get("0")


def test_unknown_tables_are_404(ann):
    assert ann.get("/tables/0000000000").status_code == 404
    assert ann.get("/tables/0000000000/poll").status_code == 404
    assert ann.post("/tables/0000000000/work", data={"csrf": csrf(ann)}).status_code == 404


# --- names ------------------------------------------------------------------


def test_reserved_names_are_refused_in_any_case(store):
    for name in ("Mustard", "plum", "FLOOR", "random", "Web", "envelope"):
        with pytest.raises(ValueError, match="taken"):
            users.add_user(store, name, "pw")
    users.add_user(store, "Mustardo", "pw")


# --- memory -----------------------------------------------------------------


def _finish_by_registry(registry, table_id):
    game = registry.game(table_id)
    tables.WORK_INTERVAL = 0.0
    while not game.finished:
        if game.pending is not None:
            registry.set_autopilot(table_id, game, game.pending.seat, True)
        registry.work(table_id, game)
    return game


def test_memory_off_reads_and_writes_nothing(store):
    registry = tables.TableRegistry(store)
    setup = TableSetup((SeatSpec("Scarlett", "human", ANN), SeatSpec("Mustard", "character", "Mustard"),
                        SeatSpec("White", "character", "White")), SEED, max_turns=12, remember=False)
    table_id = registry.create(setup, ANN)
    _finish_by_registry(registry, table_id)
    assert Logbook(store, "White").method() is None and Logbook(store, "Mustard").method() is None
    assert registry.document(table_id)["memory"] is None


def test_default_memory_writes_whites_counts_under_the_human_label(store):
    registry = tables.TableRegistry(store)
    setup = TableSetup((SeatSpec("Scarlett", "human", ANN), SeatSpec("Mustard", "character", "Mustard"),
                        SeatSpec("White", "character", "White")), SEED, max_turns=30)
    table_id = registry.create(setup, ANN)
    assert registry.document(table_id)["memory"] == {}, "nothing to snapshot from an empty logbook"
    game = _finish_by_registry(registry, table_id)
    white = Logbook(store, "White").method()
    assert white is not None and white["kind"] == "counts" and len(white["games"]) == 1
    counts = method_memory.priors(white)
    assert ANN in counts, "the person's suggestion pattern is remembered under their name"
    mustard = Logbook(store, "Mustard").method()
    assert mustard is not None and mustard["kind"] == "rows" and len(mustard["games"]) == 1
    assert game.setup.remember

    # A second table snapshots what is now there, and a rebuild loads the
    # snapshot rather than a document that moved on since.
    second = registry.create(setup, ANN)
    snapshot = registry.document(second)["memory"]
    assert snapshot["White"] == {"kind": "counts", "games": ["web/00000"]}
    assert snapshot["Mustard"]["kind"] == "rows" and snapshot["Mustard"]["games"] == ["web/00000"]
    live = registry.game(second)
    live.run(6)
    registry.save(second, live)
    _finish_by_registry(registry, table_id)  # already finished: a no-op
    cold = tables.TableRegistry(store).game(second)
    assert [repr(e) for e in cold.events] == [repr(e) for e in live.events]


def test_two_tables_finishing_keep_greens_learning(store):
    registry = tables.TableRegistry(store)
    setup = TableSetup((SeatSpec("Scarlett", "human", ANN), SeatSpec("Green", "character", "Green"),
                        SeatSpec("White", "character", "White")), SEED, max_turns=6, remember=True)
    first = registry.create(setup, ANN)
    second = registry.create(setup, ANN)
    _finish_by_registry(registry, first)
    after_one = Logbook(store, "Green").method()
    assert after_one is not None and after_one["games"] == 1
    _finish_by_registry(registry, second)
    after_two = Logbook(store, "Green").method()
    assert after_two["games"] == 2, "the second finish overwrote the first's learning"
    assert after_two["arms"] != method_memory.empty_memory("state")["arms"]
