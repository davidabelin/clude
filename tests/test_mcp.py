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
hand; that `accuse` folds the accusation into the answer before it and
is refused or set aside when it cannot apply; that `clude_autopilot`
hands the seat to the stand-in; that the notepad records a pass and
the floor's "one of" facts; that `head` is null without a head and the
method's own shape with one, equal to a fresh agent's belief on a
rebuilt game as on the live one; that the note survives a cold rebuild
and never becomes an entry; and that the combined ASGI app serves the
lobby behind the gate and the endpoint only under its secret.
"""
from __future__ import annotations

import json

import anyio
import pytest
from mcp import Client
from mcp.types import LATEST_PROTOCOL_VERSION

import clude_constraints
from clude_agents import build_agent
from clude_core.domain import ROOMS, skipped_players
from clude_storage import GameRecord, open_store
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
            or (pending["kind"] == "movement" and args["answer"]["to"] not in ROOMS)
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
        assert seated["head"] is False
        assert "dealt" in seated["message"]

        [table] = unwrap(await client.call_tool("clude_tables", {}))["tables"]
        assert table["mine"] is True and table["open_seats"] == []
        assert table["seats"][0] == {"seat": 0, "token": "Scarlett", "kind": "human", "label": CLAUDE, "head": False}
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
            assert view["head"] is None
            assert set(view) >= {"events", "digest", "notepad", "note", "seats", "pending", "finished", "n_events"}
            assert view["seats"][0] == f"Scarlett: {CLAUDE} (you)" and view["seats"][1] == "Mustard: character"
            assert all(isinstance(line, str) for line in view["events"])
            assert set(view["notepad"]) == {"suspects", "weapons", "rooms", "one_of", "solution"}
            seen_hands.add(tuple(view["me"]["hand"]))
            assert len(view["events"]) <= mcp.MAX_EVENTS
            if view["pending"] is not None:
                kinds.append(view["pending"]["kind"])
                if view["pending"]["kind"] == "movement":
                    assert all(set(o) == {"move", "to", "room"} for o in view["pending"]["options"])

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
        into_room = next((o for o in pending["options"] if o["room"]), None)
        if into_room is not None:
            view = unwrap(
                await client.call_tool(
                    "clude_answer",
                    {"table_id": table_id, "seq": pending["seq"], "answer": {"move": into_room["move"], "to": into_room["to"]},
                     "accuse": False},
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


# --- the head ---------------------------------------------------------------------


async def test_a_head_is_the_tokens_own_fresh_belief_live_and_rebuilt(server, registry, store):
    seats = (SeatSpec("Scarlett", "character", "Scarlett"), SeatSpec("Mustard", "character", "Mustard"), SeatSpec("Peacock", "open"))
    table_id = registry.create(TableSetup(seats, SEED), started_by=ANN)
    async with Client(server) as client:
        seated = unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Peacock", "head": True}))
        assert seated["head"] is True
        game = registry.deal(table_id)
        seat = tables.viewer_seat(game.setup, CLAUDE)
        assert game.setup.seats[seat].head is True
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        for _ in range(4):  # a few decisions in, so the belief has moved
            if view["finished"] or view["pending"] is None:
                break
            pending = view["pending"]
            view = unwrap(
                await client.call_tool(
                    "clude_answer", {"table_id": table_id, "seq": pending["seq"], "answer": simple_answer(pending)}
                )
            )
            view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))

    head = view["head"]
    assert head["method"].startswith("Dempster-Shafer")
    assert head["shape"] == "belief_plausibility"
    assert set(head["extra"]) == {"belief", "plausibility"}
    assert head["turn"] == game.state.turn

    reader = build_agent("Peacock")
    reader.reset(SEED)
    belief = reader.select_action(clude_constraints.observe(game.state, seat))
    assert head["probabilities"] == {card: round(float(p), 4) for card, p in belief.probabilities.items()}

    cold = tables.TableRegistry(store).game(table_id)
    assert cold is not game
    assert cold.head_reading(seat) == game.head_reading(seat)
    assert cold.setup.seats[seat].head is True

    # The head is data on the seat, refused where it makes no sense.
    with pytest.raises(ValueError):
        SeatSpec("Mustard", "character", "Mustard", head=True)
    with pytest.raises(ValueError):
        SeatSpec("Plum", "floor", head=True)
    assert SeatSpec.from_dict({"token": "Plum", "kind": "human", "label": "x"}).head is False
    assert "head" not in SeatSpec("Plum", "human", "x").to_dict()


async def test_without_a_head_the_view_says_so(server, registry):
    table_id = open_table(registry)
    async with Client(server) as client:
        unwrap(await client.call_tool("clude_sit", {"table_id": table_id, "token": "Scarlett"}))
        registry.deal(table_id)
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
    assert "head" in view and view["head"] is None


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
