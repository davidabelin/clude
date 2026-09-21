"""A seat over MCP (Phase 9, docs/phase9-plan.md 3.5), on the SDK's
in-memory client against the server object: no network, no HTTP, no
model.

Pinned here: that the chat seat is an ordinary account in an ordinary
human seat, answering through the same registry the browser uses; that
a whole game plays through the six tools with the characters driven by
`clude_turn`, every answer entered ``by="mcp"`` and the record saved
like any other; that a stale `seq` is refused and reported and a
doubled answer applied once; that the view never carries `readings` or
another seat's hand; that `head` is null without a head and the
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


async def play_out(client, table_id, max_steps=3000, on_view=None):
    """Drive a table to its end through the tools: `clude_turn` until a
    decision is ours or the game ends, `clude_answer` to answer it."""
    for _ in range(max_steps):
        view = unwrap(await client.call_tool("clude_turn", {"table_id": table_id}))
        if on_view is not None:
            on_view(view)
        if view["finished"]:
            return view
        pending = view["pending"]
        assert pending is not None, "clude_turn came back with nothing to do and the game not over"
        view = unwrap(
            await client.call_tool(
                "clude_answer", {"table_id": table_id, "seq": pending["seq"], "answer": simple_answer(pending)}
            )
        )
        assert "error" not in view, view["error"]
        if on_view is not None:
            on_view(view)
        if view["finished"]:
            return view
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

        def check(view):
            assert "readings" not in view and "tokens" not in view
            assert view["seat"] == 0 and view["me"]["seat"] == 0
            assert view["head"] is None
            assert set(view) >= {"events", "digest", "notepad", "note", "seats", "pending", "finished"}
            seen_hands.add(tuple(view["me"]["hand"]))
            assert len(view["events"]) <= mcp.MAX_EVENTS

        final = await play_out(client, table_id, on_view=check)

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
    text = json.dumps(view)
    for card in game.state.hands[3]:  # Ann's hand, Peacock's seat
        assert f'"{card}"' not in text or card in game.state.hands[0] or _named_in_public(card, view)
    assert view["seats"][3]["label"] == ANN and view["seats"][3]["me"] is False


def _named_in_public(card: str, view: dict) -> bool:
    """A card may be named in an event line (a suggestion names three)
    or on the notepad as a card whose holder is unknown; never as a
    card another seat is known to hold, unless the floor proved it."""
    rows = {row["card"]: row for row in view["notepad"]}
    return card in rows and rows[card]["holder"] != 0


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
    remarks = [line for line in view["events"] if line["kind"] == "remark"]
    assert remarks and "I have nothing to hide." in remarks[-1]["text"]
    game = registry.game(table_id)
    assert any(e.get("kind") == "chat" and e["seat"] == 0 for e in game.entries)


# --- the combined app -------------------------------------------------------------------


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


async def test_without_a_secret_the_endpoint_is_not_mounted(tmp_path, monkeypatch):
    monkeypatch.delenv("CLUDE_MCP_SECRET", raising=False)
    monkeypatch.setattr("clude_web.config.read_env_file", lambda *_a, **_k: None)
    combined = mcp.combined_app({"TESTING": True, "STORE_URI": str(tmp_path)})
    assert combined.state.mcp is None
    assert (await asgi(combined, "GET", "/"))["status"] == 302
    assert (await asgi(combined, "GET", f"/mcp/{SECRET}"))["status"] == 302  # Flask's gate, not the endpoint


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
