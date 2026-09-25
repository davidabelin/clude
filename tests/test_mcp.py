"""A seat over MCP (Phase 9, docs/phase9-plan.md 3.5), on the SDK's
in-memory client against the server object: no network, no HTTP, no
model.

Pinned here: that the chat seat is an ordinary account in an ordinary
human seat, answering through the same registry the browser uses; that
a whole game plays through the tools with the characters driven by
`clude_turn` and `clude_answer`, every answer entered ``by="mcp"`` and
the record saved like any other; that a stale `seq` is refused and
reported and a doubled answer applied once; that the view is compact
(`since` cuts the events, the note comes only with since 0, one line
per seat and per card) and never carries `readings` or another seat's
hand; that a move is one line per room and answered by naming the room
(`toward`), the log still recording an ordinary move; that a reply with
nothing new leaves out the notepad and seats and says how long a person
can hold the table, and one call never holds longer than one poll; that
`accuse` folds the accusation into the answer before it and
is refused or set aside when it cannot apply; that `clude_autopilot`
hands the seat to the stand-in; that the notepad records a pass and
the floor's "one of" facts; that a seat has no head, only the floor's
numbers; that an ended table says so; that the note survives a cold rebuild
and never becomes an entry; and that the combined ASGI app serves the
lobby behind the gate and the endpoint only under its secret.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import anyio
import pytest
from mcp import Client
from mcp.types import LATEST_PROTOCOL_VERSION

import clude_constraints
from clude_core import board
from clude_core.domain import ROOMS, SUSPECTS, WEAPONS, skipped_players
from clude_storage import GameRecord, open_store
from clude_storage.records import node_from_json
from clude_training.table import SeatSpec, TableSetup
from clude_web import create_app, mcp, tables, users

ANN, CLAUDE = "ann", "claude"
SEED = 11
SECRET = "test-secret-0123456789abcdef"

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def store(tmp_path):
    return open_store(str(tmp_path))


@pytest.fixture
def app(tmp_path, store):
    for name in (ANN, CLAUDE):
        users.add_user(store, name, "pw")
        users.mark_password_prompted(store, name)
    return create_app({"TESTING": True, "STORE_URI": str(tmp_path)})


@pytest.fixture
def registry(app):
    return app.extensions["tables"]


@pytest.fixture
def server(registry, monkeypatch):
    """The server over the app's registry, with every pause removed so
    a game runs at full speed and a long-poll never waits on a clock."""
    monkeypatch.setattr(tables, "WORK_INTERVAL", 0.0)
    monkeypatch.setattr(mcp, "SLEEP_SECONDS", 0.0)
    monkeypatch.setattr(mcp, "POLL_SECONDS", 60.0)
    return mcp.build_server(registry, CLAUDE)


def open_table(registry, seed=SEED, extra=()):
    """A table with Scarlett's seat open beside Mustard and White (and
    `extra` seats), waiting in the lobby."""
    seats = (SeatSpec("Scarlett", "open"), SeatSpec("Mustard", "character", "Mustard"), SeatSpec("White", "character", "White"))
    return registry.create(TableSetup(seats + tuple(extra), seed), started_by=ANN)


def unwrap(result) -> dict:
    """A tool result as the dict the tool returned."""
    text = "".join(getattr(block, "text", "") for block in result.content)
    assert not result.is_error, text
    if result.structured_content is not None:
        return result.structured_content
    return json.loads(text)


def error_text(result) -> str:
    assert result.is_error
    return "".join(getattr(block, "text", "") for block in result.content)


def simple_answer(pending: dict):
    """A legal answer to any decision: toward the nearest room, a fixed
    suggestion, no accusation, the first card."""
    kind = pending["kind"]
    if kind == "movement":
        return {"toward": next(iter(pending["toward"]))}
    if kind == "suggestion":
        return {"suspect": "Plum", "weapon": "Rope"}
    if kind == "accusation":
        return None
    return {"card": pending["candidates"][0]}


def lands_in_a_room(pending: dict, room: str) -> bool:
    """Whether moving toward `room` ends the move in a room (that one,
    or one on the way), which puts the suggestion question next."""
    return "ending at row" not in pending["toward"][room]


async def play_out(client, table_id, max_steps=3000, on_view=None, fold_accusation=False, since=False):
    """Drive a table to its end through the tools as a player would:
    `clude_turn` once, then `clude_answer` (which waits for the next
    decision) until the game ends, `clude_turn` again only when an
    answer came back with nothing pending. With `fold_accusation`, the
    accusation is passed in the same call as the answer it follows;
    with `since`, every call passes the last `n_events` seen."""
    cursor = 0
    view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id, "since": cursor}))
    for _ in range(max_steps):
        if on_view is not None:
            on_view(view)
        if since:
            cursor = view["n_events"]
        if view["finished"]:
            return view
        pending = view["pending"]
        if pending is None:
            view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id, "since": cursor}))
            continue
        args = {"table_id": table_id, "seq": pending["seq"], "answer": simple_answer(pending), "since": cursor}
        if fold_accusation and (
            pending["kind"] == "suggestion"
            or (pending["kind"] == "movement" and not lands_in_a_room(pending, args["answer"]["toward"]))
        ):
            args["accuse"] = False
        view = unwrap(await client.call_tool("clude_answer", args))
        assert "error" not in view, view["error"]
    raise AssertionError("the game did not end")


# --- listing and sitting ------------------------------------------------------


async def test_tables_lists_an_open_table_and_mine_flips_after_sitting(server, registry):
    table_id = open_table(registry)
    async with Client(server) as client:
        listing = unwrap(await client.call_tool("clude_tables", {}))
        assert listing["you"] == CLAUDE
        [table] = listing["tables"]
        assert table["table_id"] == table_id
        assert table["status"] == "open"
        assert table["open_seats"] == ["Scarlett"]
        assert table["mine"] is False

        seated = unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        assert seated["mine"] is True and seated["my_token"] == "Scarlett"
        assert "dealt" in seated["message"]

        [table] = unwrap(await client.call_tool("clude_tables", {}))["tables"]
        assert table["mine"] is True and table["open_seats"] == []
        assert table["seats"][0] == {"seat": 0, "token": "Scarlett", "kind": "human", "label": CLAUDE}
        assert table["my_autopilot"] is False

    # The seat is an ordinary human seat in the stored setup.
    setup = TableSetup.from_dict(registry.document(table_id)["setup"])
    assert setup.seats[0] == SeatSpec("Scarlett", "human", CLAUDE)
    assert tables.viewer_seat(setup, CLAUDE) == 0


async def test_sitting_where_one_cannot_is_a_message_not_a_crash(server, registry):
    table_id = open_table(registry)
    async with Client(server) as client:
        result = await client.call_tool("clude_sit", {"table_id": table_id, "token": "Mustard"})
        assert "taken" in error_text(result)
        result = await client.call_tool("clude_sit", {"table_id": "nope", "token": "Scarlett"})
        assert "not waiting" in error_text(result)
        result = await client.call_tool("clude_turn", {"table_id": table_id})
        assert "not sitting" in error_text(result)
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        result = await client.call_tool("clude_turn", {"table_id": table_id})
        assert "not been dealt" in error_text(result)


# --- a whole game --------------------------------------------------------------


async def test_a_whole_game_plays_through_the_tools(server, registry, store):
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)

        seen_hands = set()
        kinds = []

        def check(view):
            assert "readings" not in view and "tokens" not in view
            assert view["me"]["seat"] == 0 and view["me"]["token"] == "Scarlett"
            assert set(view) >= {"events", "digest", "notepad", "note", "seats", "pending", "finished", "n_events"}
            assert view["seats"][0] == f"Scarlett: {CLAUDE} (you)" and view["seats"][1] == "Mustard: character"
            assert all(isinstance(line, str) for line in view["events"])
            assert set(view["notepad"]) == {"suspects", "weapons", "rooms", "one_of", "solution"}
            seen_hands.add(tuple(view["me"]["hand"]))
            assert len(view["events"]) <= mcp.MAX_EVENTS
            if view["pending"] is not None:
                kinds.append(view["pending"]["kind"])
                if view["pending"]["kind"] == "movement":
                    # One line per room, not every legal move (Phase 9f).
                    assert "options" not in view["pending"]
                    assert set(view["pending"]["toward"]) == set(ROOMS)
                    assert all(isinstance(line, str) and line for line in view["pending"]["toward"].values())

        final = await play_out(client, table_id, on_view=check)
    assert "accusation" in kinds, "the accusation question never came as a decision of its own"

    assert final["finished"] and final["over"] is not None
    assert len(seen_hands) == 1, "the hand changed under the seat"
    game = registry.game(table_id)
    mine = [e for e in game.entries if e.get("kind") == "answer" and e["seat"] == 0]
    assert mine and all(e["by"] == "mcp" for e in mine)
    assert not any("audit" in e for e in mine)

    # Recorded like any other web game, the chat seat a person under its account key.
    assert store.list_games("web") == [0]
    record = GameRecord.from_dict(store.get_game("web", 0))
    seat = next(s for s in record.seats if s.seat == 0)
    assert (seat.label, seat.kind) == (CLAUDE, "human")
    assert final["over"]["replay"] == "/replay/web/0"


async def test_the_digest_folds_the_lines_that_fell_off_the_front(server, registry, monkeypatch):
    monkeypatch.setattr(mcp, "MAX_EVENTS", 5)
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        digests = []
        await play_out(client, table_id, on_view=lambda view: digests.append(view["digest"]))
    assert digests[0] == ""
    assert any("suggestions" in d for d in digests), "no suggestion was ever folded into the digest"
    assert any("nobody could disprove" in d for d in digests), "no undisproved suggestion was ever named"
    assert all(d == "" or d.endswith(".") for d in digests)
    last = digests[-1]
    assert "earlier lines" in last and "are not shown" in last


# --- the seq guard ---------------------------------------------------------------


async def test_a_stale_seq_is_refused_and_a_doubled_answer_applied_once(server, registry):
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        pending = view["pending"]
        assert pending is not None
        seq = pending["seq"]
        game = registry.game(table_id)
        before = len(game.entries)

        stale = unwrap(
            await client.call_tool(
                "clude_answer", {"table_id": table_id, "seq": seq - 1, "answer": simple_answer(pending)}
            )
        )
        assert "out of date" in stale["error"]
        assert len(game.entries) == before

        first = unwrap(
            await client.call_tool("clude_answer", {"table_id": table_id, "seq": seq, "answer": simple_answer(pending)})
        )
        assert "error" not in first
        assert len(game.entries) == before + 1

        again = unwrap(
            await client.call_tool("clude_answer", {"table_id": table_id, "seq": seq, "answer": simple_answer(pending)})
        )
        assert "error" in again
        assert len(game.entries) == before + 1


# --- what the view shows and hides -------------------------------------------------


async def test_the_view_shows_only_this_seats_hand_and_no_readings(server, registry):
    table_id = open_table(registry, extra=(SeatSpec("Peacock", "human", ANN),))
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        game = registry.deal(table_id)
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
    assert "readings" not in view and "tokens" not in view
    assert sorted(view["me"]["hand"]) == sorted(game.state.hands[0])
    lines = card_lines(view["notepad"])
    obs = clude_constraints.observe(game.state, 0)
    for card in game.state.hands[3]:  # Ann's hand, Peacock's seat: named as hers only if the floor proved it
        assert (lines[card] == "Peacock") == (obs.mask.holder_of(card) == 3)
    for card in game.state.hands[0]:
        assert lines[card] == "me"
    assert view["seats"][3] == f"Peacock: {ANN}"
    assert view["seats"][0] == f"Scarlett: {CLAUDE} (you)"


def card_lines(pad: dict) -> dict:
    """Every card's line on a compact notepad, category flattened."""
    return {card: line for category in ("suspects", "weapons", "rooms") for card, line in pad[category].items()}


async def test_since_cuts_the_events_and_the_note_comes_only_with_zero(server, registry):
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        unwrap(await client.call_tool("clude_note", {"table_id": table_id, "text": "White has the Rope."}))
        registry.deal(table_id)
        first = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        assert first["note"] == "White has the Rope."
        assert first["events"] == [] and first["n_events"] == 0  # Scarlett moves first: nothing has happened
        pending = first["pending"]
        first = unwrap(
            await client.call_tool(
                "clude_answer", {"table_id": table_id, "seq": pending["seq"], "answer": simple_answer(pending)}
            )
        )
        assert first["note"] == "White has the Rope."
        assert first["events"] and first["events"][0].startswith(f"0 (turn 1) Scarlett ({CLAUDE}) moves")
        cursor = first["n_events"]
        pending = first["pending"]
        later = unwrap(
            await client.call_tool(
                "clude_answer",
                {"table_id": table_id, "seq": pending["seq"], "answer": simple_answer(pending), "since": cursor},
            )
        )
        assert "note" not in later
        assert later["n_events"] > cursor
        assert later["events"] and later["events"][0].startswith(f"{cursor} (turn ")
        assert len(later["events"]) == later["n_events"] - cursor
        assert later["digest"] == ""
        same = unwrap(await client.call_tool("clude_turn", {"table_id": table_id, "since": later["n_events"]}))
        assert same["events"] == [] and "note" not in same


# --- fewer calls: accuse folded in, and an answer that waits ---------------------


async def test_an_answer_waits_for_the_next_decision(server, registry):
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        pending = view["pending"]
        assert pending["kind"] == "movement"
        view = unwrap(
            await client.call_tool(
                "clude_answer", {"table_id": table_id, "seq": pending["seq"], "answer": simple_answer(pending)}
            )
        )
        # The turn went on to the next question, ours again, without a clude_turn.
        assert view["pending"] is not None and view["pending"]["seq"] > pending["seq"]
        assert view["pending"]["kind"] in ("suggestion", "accusation")
        pending = view["pending"]
        answer = simple_answer(pending)
        # Answer through to the end of the turn without waiting: the bots have not played.
        while pending is not None and pending["kind"] != "movement":
            view = unwrap(
                await client.call_tool(
                    "clude_answer", {"table_id": table_id, "seq": pending["seq"], "answer": answer, "wait": False}
                )
            )
            pending = view["pending"]
            answer = None if pending is None else simple_answer(pending)
        assert pending is None
        assert registry.game(table_id).pending is None


async def test_accuse_folds_the_accusation_into_the_answer_before_it(server, registry):
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        kinds = []
        final = await play_out(
            client, table_id, fold_accusation=True, since=True,
            on_view=lambda v: kinds.append(v["pending"]["kind"]) if v["pending"] else None,
        )
    assert final["finished"]
    assert "accusation" not in kinds, "an accusation question was still put as a decision of its own"
    game = registry.game(table_id)
    passed = [e for e in game.entries if e.get("kind") == "answer" and e["seat"] == 0 and e["decision"] == "accusation"]
    assert passed and all(e["by"] == "mcp" and e["data"] is None for e in passed)


async def test_accuse_still_lands_when_a_card_is_shown_in_between(server, registry):
    """Phase 9d. The accusation question ends the turn, but it rarely
    follows the answer immediately: a suggestion is refuted first, and a
    refuter who is not a plain bot pauses the game in between.

    Built to force exactly that. Mustard is a person on autopilot and
    sits directly after the chat seat, so it is asked to refute first;
    naming a card from its hand stops the game on its `card_to_show`
    between the suggestion and the accusation question. Before the fix
    `accuse` was tested against whatever was pending the instant the
    answer landed, so here it was set aside every time and the
    accusation came back as a decision of its own -- the extra round
    trip the chat seat reported.
    """
    seats = (
        SeatSpec("Scarlett", "open"),
        SeatSpec("Mustard", "human", ANN),
        SeatSpec("White", "character", "White"),
        SeatSpec("Plum", "character", "Plum"),
    )
    table_id = registry.create(TableSetup(seats, SEED), started_by=ANN)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        game = registry.game(table_id)
        registry.set_autopilot(table_id, game, 1, True)

        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        for _ in range(400):
            pending = view["pending"]
            assert pending is not None and not view["finished"], "never reached a suggestion"
            if pending["kind"] == "suggestion":
                held = set(game.state.hands[1])
                suspect = next((c for c in SUSPECTS if c in held), None)
                weapon = next((c for c in WEAPONS if c in held), None)
                if suspect or weapon:
                    break
            view = unwrap(await client.call_tool(
                "clude_answer",
                {"table_id": table_id, "seq": pending["seq"], "answer": simple_answer(pending)},
            ))
        else:
            raise AssertionError("never reached a suggestion the seat next door could refute")

        answer = {
            "suspect": suspect or "Plum",
            "weapon": weapon or "Rope",
        }
        entries_before = len(game.entries)
        folded = unwrap(await client.call_tool(
            "clude_answer",
            {"table_id": table_id, "seq": pending["seq"], "answer": answer, "accuse": False},
        ))

    assert "error" not in folded, folded.get("error")
    assert "notice" not in folded, folded["notice"]
    answers = [e for e in game.entries[entries_before:] if e.get("kind") == "answer"]
    decisions = [(e["seat"], e["decision"]) for e in answers]
    assert (1, "card_to_show") in decisions, f"nothing was shown in between: {decisions}"
    assert (0, "accusation") in decisions, f"the accusation was not folded in: {decisions}"
    passed = [e for e in answers if e["seat"] == 0 and e["decision"] == "accusation"]
    assert all(e["by"] == "mcp" and e["data"] is None for e in passed)


class _Refusing:
    """A wrapper whose backend is refusing, for the view to notice."""

    class backend:
        last_refusal = "budget: this table's $2.00 is spent"


async def test_the_view_says_when_the_models_have_gone_dark(server, registry):
    """Phase 9d, the chat seat's fourth report. A spent budget leaves the
    characters playing their own methods and silent, which from the seat
    looks like the table has gone mechanical for no reason -- the browser
    is told, the chat seat was not. One line, only when it is true."""
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        game = registry.game(table_id)

        quiet = mcp.seat_view(registry, table_id, game, 0, since=0)
        assert "models" not in quiet, "the notice went out with nothing refusing"

        game.table.wrappers[1] = _Refusing()
        spent = mcp.seat_view(registry, table_id, game, 0, since=0)
        assert "budget is spent" in spent["models"]
        assert "own methods" in spent["models"]


async def test_table_talk_does_not_stale_the_decision_waiting_on_the_seat(server, registry):
    """Phase 9d, the chat seat's first report: "whenever anyone speaks
    while a decision is waiting for me, the seq moves on, and my answer
    comes back as out of date" -- four tries for one suggestion.

    `seq` now counts answers, not entries, so the seat's own line and
    anyone else's leave a waiting decision answerable.
    """
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        pending = view["pending"]
        seq = pending["seq"]
        game = registry.game(table_id)
        entries_before = len(game.entries)

        unwrap(await client.call_tool("clude_say", {"table_id": table_id, "text": "Anyone been in the Study?"}))
        registry.say(table_id, game, 1, "Not lately.")
        assert len(game.entries) > entries_before, "the lines were not logged"
        assert game.seq == seq, "table talk moved the seq"

        answered = unwrap(
            await client.call_tool(
                "clude_answer", {"table_id": table_id, "seq": seq, "answer": simple_answer(pending)}
            )
        )
        assert "error" not in answered, answered.get("error")


async def test_the_board_comes_once_with_the_seat_and_with_a_fresh_view(server, registry):
    """Phase 9d: the chat seat asked for the map once rather than every
    turn. It rides with `clude_sit` and with a `since=0` view (what a
    fresh conversation calls), and never on a turn."""
    table_id = open_table(registry)
    async with Client(server) as client:
        seated = unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        assert seated["board"] == mcp.BOARD_PICTURE
        assert "Legend:" in seated["board"] and "K Kitchen" in seated["board"]

        registry.deal(table_id)
        fresh = unwrap(await client.call_tool("clude_turn", {"table_id": table_id, "since": 0}))
        assert fresh["board"] == mcp.BOARD_PICTURE
        assert fresh["me"]["at"] is not None

        played = unwrap(
            await client.call_tool(
                "clude_answer",
                {"table_id": table_id, "seq": fresh["pending"]["seq"],
                 "answer": simple_answer(fresh["pending"]), "since": 0},
            )
        )
        assert played["n_events"] > 0
        on = unwrap(await client.call_tool("clude_turn", {"table_id": table_id, "since": played["n_events"]}))
        assert "board" not in on, "the board went out again on a turn"
        assert "note" not in on, "the note went out again on a turn"


async def test_accuse_given_too_early_or_malformed_is_set_aside_or_refused(server, registry):
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        pending = view["pending"]
        assert pending["kind"] == "movement"
        before = len(registry.game(table_id).entries)

        bad = unwrap(
            await client.call_tool(
                "clude_answer",
                {"table_id": table_id, "seq": pending["seq"], "answer": simple_answer(pending), "accuse": True},
            )
        )
        assert "error" in bad and "accuse" in bad["error"]
        assert len(registry.game(table_id).entries) == before, "a refused accuse applied the move anyway"
        bad = unwrap(
            await client.call_tool(
                "clude_answer",
                {"table_id": table_id, "seq": pending["seq"], "answer": simple_answer(pending),
                 "accuse": {"suspect": "Nobody", "weapon": "Rope", "room": "Hall"}},
            )
        )
        assert "error" in bad and len(registry.game(table_id).entries) == before

        # A move into a room: the suggestion question comes first, so accuse waits.
        into_room = next((room for room, line in pending["toward"].items() if line.startswith("enter")), None)
        if into_room is not None:
            view = unwrap(
                await client.call_tool(
                    "clude_answer",
                    {"table_id": table_id, "seq": pending["seq"], "answer": {"toward": into_room}, "accuse": False},
                )
            )
            assert "error" not in view
            assert view["pending"]["kind"] == "suggestion"
            assert "notice" in view and "not applied" in view["notice"]


async def test_the_notepad_records_a_pass_and_the_one_of_facts(server, registry):
    """A seat asked to disprove who could not is struck from the three
    cards, and a seat who disproved without showing us the card holds
    one of what it could still hold: both on the compact notepad, which
    says what the browser's rows say, names for seat numbers."""
    table_id = open_table(registry, extra=(SeatSpec("Peacock", "character", "Peacock"),))
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        game = registry.deal(table_id)
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        for _ in range(40):  # well into the game, so there are passes and disproofs to check
            if view["finished"] or view["pending"] is None:
                break
            pending = view["pending"]
            view = unwrap(
                await client.call_tool(
                    "clude_answer", {"table_id": table_id, "seq": pending["seq"], "answer": simple_answer(pending)}
                )
            )
    pad = view["notepad"]
    lines = card_lines(pad)
    obs = clude_constraints.observe(game.state, 0)
    passes = 0
    for s in obs.suggestion_log:
        for skipped in skipped_players(game.setup.n_players, s.suggester, s.refuter):
            passes += 1
            for card in s.cards():
                assert game.suspects[skipped] not in lines[card], (card, lines[card])
    assert passes, "nobody ever passed on a suggestion"
    assert pad["one_of"] == [
        f"{game.suspects[holder]} holds at least one of: {', '.join(sorted(cards))}"
        for cards, holder in obs.mask.or_constraints
    ]
    assert pad["solution"] is None or len(pad["solution"]) == 3
    for row in tables.notepad(game, 0):
        if row["holder"] is not None:
            expected = "envelope" if row["holder"] == "envelope" else ("me" if row["holder"] == 0 else game.suspects[row["holder"]])
            assert lines[row["card"]] == expected
        else:
            names = [("me" if seat == 0 else game.suspects[seat]) for seat in row["possible"]] + (["envelope"] if row["envelope"] else [])
            assert lines[row["card"]] == ", ".join(names[:-1]) + " or " + names[-1]


# --- autopilot ----------------------------------------------------------------------


async def test_autopilot_hands_the_seat_to_the_stand_in_and_back(server, registry):
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        assert view["pending"] is not None and view["me"]["autopilot"] is False
        on = unwrap(await client.call_tool("clude_autopilot", {"table_id": table_id}))
        assert on["autopilot"] is True and "floor bot" in on["message"]
        [table] = unwrap(await client.call_tool("clude_tables", {}))["tables"]
        assert table["my_autopilot"] is True
        # The stand-in answered the decision that was ours, and plays on.
        game = registry.game(table_id)
        assert game.pending is None or game.pending.seat != 0
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        assert view["me"]["autopilot"] is True
        assert view["seats"][0].endswith("(you), on autopilot")
        assert view["pending"] is None
        off = unwrap(await client.call_tool("clude_autopilot", {"table_id": table_id, "on": False}))
        assert off["autopilot"] is False and "clude_turn" in off["message"]
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        assert view["finished"] or view["pending"] is not None
    game = registry.game(table_id)
    stood_in = [e for e in game.entries if e.get("kind") == "answer" and e["seat"] == 0 and e["by"] == "autopilot"]
    assert stood_in


# --- no head: the floor's numbers and nothing else ---------------------------------


async def test_a_seat_gets_the_floors_numbers_and_no_characters(server, registry):
    """A chat seat is its own head (David, 2026-09-21): no `head` in the
    view, no `head` on `clude_sit`, and a stored setup from the first
    deploy with a ``head`` key reads back as a plain human seat."""
    table_id = open_table(registry)
    async with Client(server) as client:
        seated = unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        assert "head" not in seated and "head" not in seated["seats"][0]
        result = await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett", "head": True})
        assert result.is_error  # no such argument any more
        registry.deal(table_id)
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
    assert "head" not in view and "readings" not in view
    assert set(view["notepad"]) == {"suspects", "weapons", "rooms", "one_of", "solution"}
    assert SeatSpec.from_dict({"token": "Plum", "kind": "human", "label": "x", "head": True}) == SeatSpec("Plum", "human", "x")
    assert "head" not in SeatSpec("Plum", "human", "x").to_dict()


async def test_an_ended_table_says_so(server, registry):
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        registry.abandon(table_id, ANN)
        result = await client.call_tool("clude_turn", {"table_id": table_id})
        assert "ended" in error_text(result)
        assert unwrap(await client.call_tool("clude_tables", {}))["tables"] == []


# --- the note -------------------------------------------------------------------------


async def test_the_note_survives_a_cold_rebuild_and_is_never_an_entry(server, registry, store):
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        assert unwrap(await client.call_tool("clude_note", {"table_id": table_id}))["note"] == ""
        written = unwrap(await client.call_tool("clude_note", {"table_id": table_id, "text": "Plum has the Rope."}))
        assert written["note"] == "Plum has the Rope."
        registry.deal(table_id)
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        assert view["note"] == "Plum has the Rope."
        too_long = unwrap(await client.call_tool("clude_note", {"table_id": table_id, "text": "x" * (tables.MAX_NOTE + 1)}))
        assert "error" in too_long and too_long["note"] == "Plum has the Rope."

    live = registry.game(table_id)
    assert not any("note" in entry or "Rope." in json.dumps(entry) for entry in live.entries)
    cold_registry = tables.TableRegistry(store)
    cold = cold_registry.game(table_id)
    assert cold.entries == live.entries
    assert cold_registry.note(table_id, 0) == "Plum has the Rope."


# --- saying ----------------------------------------------------------------------------


async def test_a_line_is_said_at_the_table_and_an_empty_one_refused(server, registry):
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        said = unwrap(await client.call_tool("clude_say", {"table_id": table_id, "text": "  I have   nothing to hide. "}))
        assert said == {"said": "I have nothing to hide."}
        refused = unwrap(await client.call_tool("clude_say", {"table_id": table_id, "text": "   "}))
        assert "error" in refused
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
    remarks = [line for line in view["events"] if "I have nothing to hide." in line]
    assert remarks and remarks[-1].split(" ", 1)[0].isdigit()
    game = registry.game(table_id)
    assert any(e.get("kind") == "chat" and e["seat"] == 0 for e in game.entries)


# --- moving toward a room (Phase 9f) ------------------------------------------------------


def nearest(options: list, room: str) -> int:
    """How near `room` the best of the offered moves leaves the token:
    the brute force the `toward` lines are checked against."""
    return min(board.room_distances(node_from_json(option["to"]))[room] for option in options)


async def test_toward_takes_the_move_that_ends_nearest_the_room(server, registry):
    """The chat seat's report after game b089937cb8: 15-25 moves a turn,
    each with nine distances, when all it wanted was the one heading for
    the room it had in mind. Every room's line agrees with a brute force
    over the moves the engine offered, nearest first, and answering with
    the room makes that move, entered in the log as an ordinary one."""
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        game = registry.game(table_id)
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        moves = 0
        for _ in range(400):
            if view["finished"] or moves >= 12:
                break
            pending = view["pending"]
            if pending["kind"] != "movement":
                view = unwrap(await client.call_tool(
                    "clude_answer", {"table_id": table_id, "seq": pending["seq"], "answer": simple_answer(pending)}
                ))
                continue
            options = game.snapshot.pending["options"]
            for room, line in pending["toward"].items():
                steps = nearest(options, room)
                if steps == 0:
                    assert line.startswith(("enter it now", "stay where you are")), (room, line)
                else:
                    assert line.startswith(f"{steps} step{'' if steps == 1 else 's'} short, ending "), (room, line)
            ranked = [nearest(options, room) for room in pending["toward"]]
            assert ranked == sorted(ranked), "the rooms are not nearest first"

            room = ROOMS[moves % len(ROOMS)]
            before = len(game.entries)
            view = unwrap(await client.call_tool(
                "clude_answer",
                {"table_id": table_id, "seq": pending["seq"], "answer": {"toward": f" {room.lower()} "}},
            ))
            assert "error" not in view, view.get("error")
            entry = game.entries[before]
            assert entry["seat"] == 0 and entry["decision"] == "movement" and entry["by"] == "mcp"
            assert set(entry["data"]) == {"move", "to"}, "toward reached the log"
            assert board.room_distances(node_from_json(entry["data"]["to"]))[room] == nearest(options, room)
            moves += 1
    assert moves >= 3, "too few moves to check"  # each checks all nine rooms' lines


async def test_toward_an_unknown_room_is_refused_and_a_move_named_outright_still_works(server, registry):
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        game = registry.game(table_id)
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        pending = view["pending"]
        assert pending["kind"] == "movement"
        before = len(game.entries)

        refused = unwrap(await client.call_tool(
            "clude_answer", {"table_id": table_id, "seq": pending["seq"], "answer": {"toward": "Cellar"}}
        ))
        assert "nine rooms" in refused["error"]
        stale = unwrap(await client.call_tool(
            "clude_answer", {"table_id": table_id, "seq": pending["seq"] + 1, "answer": {"toward": "Hall"}}
        ))
        assert "out of date" in stale["error"]
        assert len(game.entries) == before and game.pending.kind == "movement"

        option = game.snapshot.pending["options"][-1]
        move = {"move": option["move"], "to": option["to"]}
        view = unwrap(await client.call_tool(
            "clude_answer", {"table_id": table_id, "seq": pending["seq"], "answer": move, "wait": False}
        ))
        assert "error" not in view, view.get("error")
        assert game.entries[before]["data"] == move


# --- waiting on a person (Phase 9f) ----------------------------------------------------------


def a_person_next_door(registry):
    """Scarlett's seat open for the chat seat, Mustard played by Ann
    from a browser and seated next, White a character."""
    seats = (
        SeatSpec("Scarlett", "open"),
        SeatSpec("Mustard", "human", ANN),
        SeatSpec("White", "character", "White"),
        SeatSpec("Plum", "character", "Plum"),
    )
    return registry.create(TableSetup(seats, SEED), started_by=ANN)


async def test_a_reply_with_nothing_new_is_short_and_says_how_long_a_person_can_take(server, registry, monkeypatch):
    """The chat seat's second report: four or five empty replies in a
    row while David thought, each a whole view. One with nothing new now
    leaves out the notepad and the seats, which cannot have changed, and
    says how long a person can hold the table before the floor bot takes
    their seat."""
    monkeypatch.setattr(mcp, "POLL_SECONDS", 0.05)
    table_id = a_person_next_door(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        while view["pending"] is not None:  # the chat seat's first turn, then Ann holds the table
            view = unwrap(await client.call_tool(
                "clude_answer",
                {"table_id": table_id, "seq": view["pending"]["seq"], "answer": simple_answer(view["pending"])},
            ))
        assert not view["finished"]
        cursor = view["n_events"]

        idle = unwrap(await client.call_tool("clude_turn", {"table_id": table_id, "since": cursor}))
        assert idle["events"] == [] and idle["pending"] is None and idle["n_events"] == cursor
        assert idle["notepad"] == "unchanged" and idle["seats"] == "unchanged"
        assert f"Mustard ({ANN})" in idle["waiting"]
        assert f"the floor bot takes the seat at {tables.AUTOPILOT_AFTER:.0f} s" in idle["waiting"]
        assert idle["me"]["hand"] and "note" not in idle and "board" not in idle

        full = unwrap(await client.call_tool("clude_turn", {"table_id": table_id, "since": 0}))
        assert isinstance(full["notepad"], dict) and isinstance(full["seats"], list)
        # A cursor past the end is a conversation that has lost count: it gets everything.
        lost = unwrap(await client.call_tool("clude_turn", {"table_id": table_id, "since": cursor + 50}))
        assert lost["notepad"] == full["notepad"] and "board" in lost and "note" in lost


async def test_the_notepad_goes_out_again_only_after_something_that_can_change_it(server, registry):
    """Moves and table talk never change what the floor has proven; a
    suggestion, a disproof, an accusation or the end may. Checked from
    every cursor in a game well under way."""
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        for _ in range(30):
            if view["finished"] or view["pending"] is None:
                break
            view = unwrap(await client.call_tool(
                "clude_answer",
                {"table_id": table_id, "seq": view["pending"]["seq"], "answer": simple_answer(view["pending"])},
            ))
    game = registry.game(table_id)
    kinds = [line["kind"] for line in tables.view_payload(game, registry.document(table_id), 0)["events"]]
    assert "suggestion" in kinds and "move" in kinds
    seen = set()
    for cursor in range(1, len(kinds) + 1):
        view = mcp.seat_view(registry, table_id, game, 0, since=cursor)
        quiet = all(kind in mcp.QUIET_KINDS for kind in kinds[cursor:])
        assert (view["notepad"] == "unchanged") == quiet, (cursor, kinds[cursor:])
        assert (view["seats"] == "unchanged") == quiet, cursor
        if not quiet:
            assert view["notepad"] == mcp.compact_notepad(game, 0)
        seen.add(quiet)
    assert seen == {True, False}


async def test_one_call_holds_for_one_poll_at_most(server, registry, monkeypatch):
    """`accuse` folded into a suggestion a person must disprove waited
    twice -- for the accusation question, then for the next decision --
    each a whole `POLL_SECONDS`, so at 60 s one call could hold two
    minutes, near the 180 s a client was reported to allow. One deadline
    now covers the call. Timed on a stand-in clock that moves a second
    each time the table is found waiting, so the machine's speed never
    matters."""
    table_id = a_person_next_door(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        game = registry.game(table_id)
        registry.set_autopilot(table_id, game, 1, True)  # Ann plays by the stand-in until the suggestion
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        held = set(game.state.hands[1])
        for _ in range(400):
            pending = view["pending"]
            assert pending is not None and not view["finished"], "never reached a suggestion"
            if pending["kind"] == "suggestion":
                suspect = next((c for c in SUSPECTS if c in held), None)
                weapon = next((c for c in WEAPONS if c in held), None)
                if suspect or weapon:
                    break
            view = unwrap(await client.call_tool(
                "clude_answer", {"table_id": table_id, "seq": pending["seq"], "answer": simple_answer(pending)}
            ))
        else:
            raise AssertionError("never reached a suggestion Ann could disprove")

        registry.set_autopilot(table_id, game, 1, False)  # now she keeps the table waiting
        clock = [0.0]

        def tick(_seconds):
            clock[0] += 1.0

        monkeypatch.setattr(mcp, "time", SimpleNamespace(monotonic=lambda: clock[0], sleep=tick))
        monkeypatch.setattr(mcp, "POLL_SECONDS", 10.0)
        folded = unwrap(await client.call_tool(
            "clude_answer",
            {"table_id": table_id, "seq": pending["seq"],
             "answer": {"suspect": suspect or "Plum", "weapon": weapon or "Rope"}, "accuse": False},
        ))
    assert "not applied" in folded["notice"]
    assert folded["pending"] is None and "show a card" in folded["waiting"]
    assert clock[0] <= mcp.POLL_SECONDS + 1, f"one call held {clock[0]:.0f} s against a {mcp.POLL_SECONDS:.0f} s poll"


# --- the combined app -------------------------------------------------------------------


DISCOVERY_PATHS = [
    f"/.well-known/{name}{suffix}"
    for name in ("oauth-protected-resource", "oauth-authorization-server")
    for suffix in ("", "/", "/mcp", f"/mcp/{SECRET}")
] + ["/.well-known/openid-configuration"]


async def asgi(app, method: str, path: str, body: bytes = b"", headers=()):
    """One request through an ASGI app, with no HTTP client: the status,
    the headers and the body."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers],
        "client": ("127.0.0.1", 1),
        "server": ("testserver", 80),
    }
    messages = [{"type": "http.request", "body": body, "more_body": False}]

    async def receive():
        return messages.pop(0) if messages else {"type": "http.disconnect"}

    out = {"status": None, "headers": {}, "body": b""}

    async def send(message):
        if message["type"] == "http.response.start":
            out["status"] = message["status"]
            out["headers"] = {k.decode().lower(): v.decode() for k, v in message.get("headers", [])}
        elif message["type"] == "http.response.body":
            out["body"] += message.get("body", b"")

    await app(scope, receive, send)
    return out


async def test_the_combined_app_serves_the_lobby_behind_the_gate_and_the_endpoint_under_its_secret(app, tmp_path):
    combined = mcp.combined_app({"TESTING": True, "STORE_URI": str(tmp_path)}, secret=SECRET)
    assert combined.state.mcp is not None
    # One registry: the MCP server plays on the Flask app's own tables.
    assert combined.state.mcp.registry is combined.state.flask.extensions["tables"]
    assert combined.state.mcp.account == "claude"
    async with combined.router.lifespan_context(combined):
        home = await asgi(combined, "GET", "/")
        assert home["status"] == 302 and "/login" in home["headers"]["location"]
        login = await asgi(combined, "GET", "/login")
        assert login["status"] == 200 and b"csrf" in login["body"]

        # A bare /mcp is not the endpoint: it falls through to Flask, whose gate redirects.
        assert (await asgi(combined, "GET", "/mcp"))["status"] == 302
        assert (await asgi(combined, "POST", "/mcp/wrong-secret-0123456789"))["status"] == 404
        assert (await asgi(combined, "GET", "/mcp/wrong-secret-0123456789/"))["status"] == 404

        initialize = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": LATEST_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"},
                },
            }
        ).encode()
        hello = await asgi(
            combined,
            "POST",
            f"/mcp/{SECRET}",
            initialize,
            headers=(
                ("content-type", "application/json"),
                ("accept", "application/json, text/event-stream"),
                ("host", "clude-648214345192.us-central1.run.app"),
            ),
        )
        assert hello["status"] == 200, hello["body"][:300]
        assert b"clude" in hello["body"]


async def test_discovery_returns_json_404_without_redirecting_to_login(tmp_path):
    combined = mcp.combined_app({"TESTING": True, "STORE_URI": str(tmp_path)}, secret=SECRET)
    for path in DISCOVERY_PATHS:
        response = await asgi(combined, "GET", path)
        assert response["status"] == 404, (path, response)
        assert response["headers"]["content-type"] == "application/json", path
        assert json.loads(response["body"]) == {"error": "Not found"}, path
        assert "location" not in response["headers"], path


async def test_without_a_secret_the_endpoint_is_not_mounted(tmp_path, monkeypatch):
    monkeypatch.delenv("CLUDE_MCP_SECRET", raising=False)
    monkeypatch.setattr("clude_web.config.read_env_file", lambda *_a, **_k: None)
    combined = mcp.combined_app({"TESTING": True, "STORE_URI": str(tmp_path)})
    assert combined.state.mcp is None
    assert (await asgi(combined, "GET", "/"))["status"] == 302
    assert (await asgi(combined, "GET", f"/mcp/{SECRET}"))["status"] == 302  # Flask's gate, not the endpoint
    for path in DISCOVERY_PATHS:
        response = await asgi(combined, "GET", path)
        assert response["status"] == 302 and "/login" in response["headers"]["location"], path


def test_a_short_or_unsafe_secret_is_refused(tmp_path):
    for bad in ("short", "has space in it 0123456789", "slash/0123456789abcdef"):
        with pytest.raises(RuntimeError):
            mcp.combined_app({"TESTING": True, "STORE_URI": str(tmp_path)}, secret=bad)


def test_three_overlapping_flask_requests_run_on_three_threads(tmp_path):
    """asgiref's default bridge runs every WSGI request on one thread,
    one at a time; the combined app's does not, or one slow turn would
    hold every poll. Three requests that overlap must land on three
    threads."""
    import threading
    import time

    from clude_web import auth

    combined = mcp.combined_app({"TESTING": True, "STORE_URI": str(tmp_path)}, secret=SECRET)
    bridge = next(route.app for route in combined.routes if route.path == "")
    assert type(bridge).__name__ == "_Bridge"
    seen = []
    flask_app = combined.state.flask

    @auth.public
    def _thread():
        seen.append(threading.current_thread().name)
        time.sleep(0.2)
        return "ok"

    flask_app.add_url_rule("/__thread", "_thread", _thread)

    async def probe():
        async def one():
            assert (await asgi(combined, "GET", "/__thread"))["status"] == 200

        async with anyio.create_task_group() as tg:
            for _ in range(3):
                tg.start_soon(one)

    anyio.run(probe)
    assert len(seen) == 3
    assert len(set(seen)) == 3, f"the requests were serialised onto {set(seen)}"
