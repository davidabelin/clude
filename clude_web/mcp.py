"""A seat at a clude table, over MCP (Phase 9, docs/phase9-plan.md).

A Claude in a chat window plays one seat of a live game through the six
tools here. Nothing in this module is a new game: every call goes
through the same `TableRegistry` the web screens use, so the chat seat
is an ordinary account (`config.mcp_account`, ``claude``) in an ordinary
human seat, answering the engine's `DecisionRequest`s from outside it
exactly as a browser does, and a game with one is indistinguishable in
the store from a game without -- except that its answers are entered
``by="mcp"``.

Three things about a chat player shape the design:

- **Forgetful.** A new conversation knows nothing, and an old one may
  have lost its early turns. So every call returns a view that fully
  reconstitutes the player -- hand, position, notepad, the recent log,
  a digest of what fell off its front, the seat's own note, and the
  decision on the table. No client-side state, ever.
- **Slow and expensive.** A tool call costs the model a round trip and
  the person a spinner, so `clude_turn` long-polls: it drives the bot
  seats itself (`TableRegistry.work`, one unit a second, exactly as
  `table.js` does from a browser) and comes back with the seat's own
  decision, the end of the game, or a timeout. One call per decision.
- **Prone to retrying.** `clude_answer` is guarded by `seq`, which
  `TableGame.answer` refuses when stale, so a doubled submission is
  refused rather than applied twice.

The tool docstrings are not documentation, they are the prompt: the
only instructions the model gets about how to play. Read them as written
for the player.

**The head.** A seat may be taken with ``head=True``: it then receives,
in every view, the numbers its token's own character method produces --
Plum's posterior, Peacock's belief and plausibility, Green's arm -- as
`WebGame.head_reading` builds them, in the method's own shape, read-only
and advisory. Off by default: a seat with no head reasons from the log
alone, which is the cheaper arm and the more surprising one. The arm is
fixed when the seat is taken and recorded in the table's setup.

**Serving.** `build_server` makes the server over any registry (a test
gives it a registry over a temp store and the SDK's in-memory client);
`combined_app` is what Cloud Run runs: the Flask app and the MCP
endpoint in one ASGI app sharing one registry, the endpoint under a
secret path (`config.mcp_secret`) since the login gate does not cover
it. Two processes over one store would each cache a table and the loser
of a race would drop an entry, which is why the endpoint is mounted
beside Flask and not served on its own.
"""
from __future__ import annotations

import re
import time
from typing import Optional

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from clude_training.table import TableError, TableSetup

from . import config, tables

__all__ = ["build_server", "combined_app", "seat_view", "digest"]

POLL_SECONDS = 25.0
"""How long `clude_turn` holds the connection: under the client's own
timeout, and well under Cloud Run's 300 s."""

SLEEP_SECONDS = 1.0
"""The pause between two units of bot work while `clude_turn` waits:
the browser's polling beat, so a person and a chat seat at one table
drive the same work and neither starves the other."""

MAX_EVENTS = 60
"""Event lines kept verbatim in a view; older ones become the digest."""

INSTRUCTIONS = """\
clude is a game of Clue (the classic board game) played at a web table by \
a mix of people and six characters, each running its own probability \
method. Through these tools you sit at a table as one of the suspects and \
play a seat yourself, reasoning from the log and your hand. The usual \
round: clude_tables to find a table with an open seat, clude_sit to take \
it, then clude_turn (which waits for your decision) and clude_answer, \
over and over, with clude_say for table talk and clude_note for what you \
want to remember. Every call returns everything you need to know; nothing \
has to be remembered between calls.\
"""


# --- shaping what the model sees --------------------------------------------


def digest(game, dropped: list) -> str:
    """The event lines that fell off the front of the view, in a line
    or two: counts, and the suggestions nobody could disprove, which are
    the facts a player carries in their head. Deliberately lossy;
    anything the seat wants to keep beyond this belongs in its note."""
    if not dropped:
        return ""
    suggestions = [line for line in dropped if line["kind"] == "suggestion"]
    undisproved = [
        line for line in suggestions
        if getattr(game.events[line["i"]], "suggestion", None) is not None
        and game.events[line["i"]].suggestion.refuter is None
    ]
    parts = [
        f"{len(dropped)} earlier lines (turns {dropped[0]['turn']} to {dropped[-1]['turn']}) are not shown"
    ]
    if suggestions:
        parts.append(f"{len(suggestions)} suggestions, {len(suggestions) - len(undisproved)} disproved")
    if undisproved:
        parts.append(
            "nobody could disprove: "
            + "; ".join(f"turn {line['turn']}, {line['text']}" for line in undisproved[-4:])
        )
    return ". ".join(parts) + "."


def seat_view(registry: tables.TableRegistry, table_id: str, game: tables.WebGame, seat: int) -> dict:
    """One self-contained picture of the table from `seat`: the screen's
    `view_payload` from that seat, trimmed twice over. `readings` and
    `tokens` are dropped -- every seat's bars are Watch's business, and
    a player's is its own -- the event lines are capped at `MAX_EVENTS`
    with the rest folded into `digest`, and the seat's `note` and its
    `head` (None without one, and the tools say so) are added."""
    document = registry.document(table_id) or {"id": table_id}
    view = tables.view_payload(
        game, document, seat, replay_url=_replay_path(document), waiting_for=registry.waiting_for(table_id, game)
    )
    for noise in ("readings", "tokens"):
        view.pop(noise, None)
    lines = view.get("events") or []
    dropped = lines[:-MAX_EVENTS] if len(lines) > MAX_EVENTS else []
    view["events"] = lines[-MAX_EVENTS:]
    view["digest"] = digest(game, dropped)
    view["seat"] = seat
    view["note"] = registry.note(table_id, seat)
    view["head"] = game.head_reading(seat)
    return view


def _replay_path(document: dict) -> Optional[str]:
    ref = document.get("record")
    if not ref:
        return None
    return f"/replay/{ref['run_id']}/{ref['index']}"


def _listing(document: dict, account: str) -> dict:
    """One table as `clude_tables` lists it."""
    setup = TableSetup.from_dict(document["setup"])
    mine = tables.viewer_seat(setup, account)
    return {
        "table_id": document["id"],
        "status": document.get("status", "playing"),
        "turns": int(document.get("turns", 0)),
        "seats": [
            {"seat": seat, "token": spec.token, "kind": spec.kind, "label": spec.label, "head": spec.head}
            for seat, spec in enumerate(setup.seats)
        ],
        "open_seats": [setup.seats[seat].token for seat in setup.open_seats],
        "mine": mine is not None,
        "my_token": None if mine is None else setup.seats[mine].token,
    }


# --- the server ---------------------------------------------------------------


def build_server(registry: tables.TableRegistry, account: Optional[str] = None) -> MCPServer:
    """The MCP server over `registry`, playing as `account`.

    Parameters
    ----------
    registry : TableRegistry
        The one registry of the process: the Flask app's own when served
        beside it (`combined_app`), a fresh one over a temp store in a
        test. Never a second registry over a store another one holds.
    account : str or None
        The account key the chat seat sits as; `config.mcp_account`
        (``claude``) by default. An ordinary account, made with
        ``users add``; seat ownership then resolves through
        `tables.viewer_seat` exactly as for a browser.
    """
    account = (account or config.mcp_account()).strip().lower()
    server = MCPServer("clude", instructions=INSTRUCTIONS)
    server.registry = registry  # what this server plays on, for a test to check
    server.account = account

    def seated(table_id: str) -> tuple:
        """The table's document and this account's seat there, or a
        `ToolError` the model can act on."""
        document = registry.document(table_id)
        if document is None:
            raise ToolError(f"There is no table {table_id}. Use clude_tables to see the tables.")
        seat = tables.viewer_seat(TableSetup.from_dict(document["setup"]), account)
        if seat is None:
            raise ToolError(
                f"You are not sitting at table {table_id}. Use clude_tables to find one with an open seat."
            )
        return document, seat

    def live(table_id: str) -> tuple:
        """The live game and this account's seat, or a `ToolError`."""
        document, seat = seated(table_id)
        game = registry.game(table_id)
        if game is None:
            if document.get("status") == "open":
                raise ToolError(
                    f"Table {table_id} has not been dealt yet; whoever made it deals from the browser. "
                    "Call clude_turn again in a little while."
                )
            raise ToolError(f"Table {table_id} cannot be played right now.")
        return game, seat

    @server.tool()
    def clude_tables() -> dict:
        """List the clude tables you could join or are already sitting at.

        clude is a game of Clue (the classic board game) played by a mix
        of people and characters. Each character runs its own probability
        method; you are none of them -- you are yourself, reasoning from
        the log.

        Returns each table's id, its status (open: waiting for players;
        playing; finished), its seats, which seats are open, and whether
        you already hold one (`mine`, with `my_token`).
        """
        listing = [_listing(document, account) for document in registry.in_progress()]
        return {"tables": listing, "you": account}

    @server.tool()
    def clude_sit(table_id: str, token: str, head: bool = False) -> dict:
        """Take an open seat at a table, as one of the six suspects.

        `token` is a suspect name from that table's open seats: Scarlett,
        Mustard, White, Green, Peacock or Plum. The game starts when
        whoever made the table deals, from the browser; until then
        clude_turn tells you the table is not dealt yet.

        `head` decides how you play the whole game and cannot be changed
        once you are seated:

        - false (the default): you reason from the log and your hand alone.
        - true: you also receive, every turn, the numbers your token's own
          character method produces -- Plum computes an exact posterior,
          Peacock belief and plausibility bounds, Green a bandit's
          estimates, and so on. They arrive in `head`, in that method's
          own shape, and they are advisory: the method cannot see the
          table talk or read anyone's hesitation; you can. Where you
          disagree with it, say why.

        Ask which arm is wanted if it has not been said. The two produce
        different data and it matters which one this game is.
        """
        try:
            document = registry.sit(table_id, account, (token or "").strip().title(), head=bool(head))
        except TableError as exc:
            raise ToolError(str(exc)) from None
        out = _listing(document, account)
        out["head"] = bool(head)
        out["message"] = (
            f"You are seated as {out['my_token']} at table {table_id}. The game starts when the table is "
            "dealt from the browser; then call clude_turn."
        )
        return out

    @server.tool()
    def clude_turn(table_id: str) -> dict:
        """Wait for your turn, then return the decision waiting for you.

        This call holds for up to half a minute while the other seats
        play, so call it once and wait rather than calling it repeatedly.
        It returns one of three things:

        - `pending` set: a decision is yours. Answer it with clude_answer,
          passing back the `seq` you were given here.
        - `pending` null and `finished` false: the table is still moving
          (another person may be thinking). Say something with clude_say
          if you like, then call this again.
        - `finished` true: the game is over; `over` holds the solution
          and who won.

        What comes back is everything you need and nothing you have to
        remember: `me` is your seat, token and hand; `seats` who is at
        the table; `events` the recent log (`digest` summarises what fell
        off its front); `notepad` the deduction sheet filled in for you
        from what is logically certain (for every card, who is proven to
        hold it, or which seats still might, and whether it could still
        be in the envelope); `note` whatever you last wrote with
        clude_note. `head` is null if you are playing clueless, and
        otherwise carries your character's own numbers for this
        position -- advisory, not an instruction.

        Every decision arrives with its legal answers already
        enumerated, so you never have to work out what the board allows,
        only which of the listed options you want.
        """
        game, seat = live(table_id)
        deadline = time.monotonic() + POLL_SECONDS
        while True:
            if game.finished or game.broken:
                break
            pending = game.pending
            if pending is not None and pending.seat == seat:
                break
            if time.monotonic() >= deadline:
                break
            did = registry.work(table_id, game)
            if did in ("waiting", "busy", "nothing"):
                time.sleep(SLEEP_SECONDS)
        return seat_view(registry, table_id, game, seat)

    @server.tool()
    def clude_answer(table_id: str, seq: int, answer: Optional[dict] = None) -> dict:
        """Answer the decision clude_turn gave you, and see what follows.

        `seq` must be the one from that decision: if the table has moved
        on, this is refused (the view comes back with `error`) rather
        than applied, and you should call clude_turn again to see the
        current state.

        The shape of `answer` depends on the decision's `kind`:

        - movement: `{"move": ..., "to": ...}`, copied from one of the
          listed `options` (each also names the `room` it leads to, or
          null for a corridor square). Copy both fields from the same
          option.
        - suggestion: `{"suspect": "Plum", "weapon": "Rope"}`; the room
          is the one you are standing in (`room`). Pass null to make no
          suggestion.
        - accusation: null to say nothing, or `{"suspect": ..., "weapon":
          ..., "room": ...}` to end the game on it. A wrong accusation
          puts you out for good, so only when you are sure.
        - card_to_show: `{"card": ...}`, one of the listed `candidates`,
          cards from your own hand that disprove someone's suggestion.
          You must show one when you can, and only the suggester sees
          which.

        Returns the table as it stands after your answer; the next
        decision may already be yours (`pending`), or call clude_turn.
        """
        game, seat = live(table_id)
        try:
            registry.answer(table_id, game, seat, int(seq), answer, by="mcp")
        except TableError as exc:
            view = seat_view(registry, table_id, game, seat)
            view["error"] = str(exc)
            return view
        return seat_view(registry, table_id, game, seat)

    @server.tool()
    def clude_say(table_id: str, text: str) -> dict:
        """Say something at the table, in character and in the open.

        Everyone sees it, including the characters, who may answer. Keep
        it to a line or two (240 characters at most): this is table
        talk, not analysis, and bluffing about your own cards is part of
        the game. The formal disproof of a suggestion is never table
        talk; the engine checks that against the hands. Returns nothing
        you need; carry on with clude_turn.
        """
        game, seat = live(table_id)
        try:
            line = registry.say(table_id, game, seat, text)
        except TableError as exc:
            return {"error": str(exc)}
        return {"said": line}

    @server.tool()
    def clude_note(table_id: str, text: Optional[str] = None) -> dict:
        """Read or replace your note, the one thing of yours that outlives
        this conversation.

        With no `text`, returns what is written. With `text`, replaces it
        wholly, so include anything you still want to keep (8,000
        characters at most).

        Write down what you have deduced and how you know it, not what
        the log already says: which cards you have seen and from whom,
        which suggestions went undisproved, what you have ruled out, what
        you told the table. A later call, in a later conversation, will
        have nothing else of yours.
        """
        _document, seat = seated(table_id)
        if text is None:
            return {"note": registry.note(table_id, seat)}
        try:
            return {"note": registry.write_note(table_id, seat, text)}
        except TableError as exc:
            return {"error": str(exc), "note": registry.note(table_id, seat)}

    return server


# --- serving ------------------------------------------------------------------

SECRET_SHAPE = re.compile(r"[A-Za-z0-9_-]{16,128}")
"""What a secret path segment may look like: URL-safe and not short."""


def combined_app(settings=None, secret: Optional[str] = None, account: Optional[str] = None):
    """The Flask app and the MCP endpoint in one ASGI app, sharing one
    registry: Flask under ``/`` and the MCP server under
    ``/mcp/<secret>``, anything else under ``/mcp`` a 404.

    Parameters
    ----------
    settings : dict or None
        Passed to `create_app`.
    secret : str or None
        The path segment; `config.mcp_secret` when None. With no secret
        at all the endpoint is not mounted and the app is the Flask app
        under an ASGI bridge, so a deploy without the secret still
        serves the game.
    account : str or None
        The chat seat's account; `config.mcp_account` when None.

    Notes
    -----
    Flask's requests run in a thread pool (the bridge is asgiref's, made
    non-thread-sensitive: asgiref's default would run every WSGI request
    on one thread, one at a time), so the game lock and the registry's
    threading model are unchanged from the threaded gunicorn worker. The
    MCP transport is stateless with JSON responses: no session to lose
    when the instance scales to zero, and a 25 s long-poll is an ordinary
    request. The SDK's localhost-only host check is switched off, since
    the secret path is the guard and the Host is Cloud Run's.

    Raises
    ------
    RuntimeError
        A secret that is not URL-safe or is too short.
    """
    from asgiref.sync import sync_to_async  # noqa: PLC0415
    from asgiref.wsgi import WsgiToAsgi, WsgiToAsgiInstance  # noqa: PLC0415
    from mcp.server.transport_security import TransportSecuritySettings  # noqa: PLC0415
    from starlette.applications import Starlette  # noqa: PLC0415
    from starlette.routing import Mount  # noqa: PLC0415

    from . import create_app  # noqa: PLC0415

    class _Instance(WsgiToAsgiInstance):
        # The class dict holds the SyncToAsync object; through the class
        # it would come back bound.
        run_wsgi_app = sync_to_async(
            WsgiToAsgiInstance.__dict__["run_wsgi_app"].func, thread_sensitive=False
        )

    class _Bridge(WsgiToAsgi):
        async def __call__(self, scope, receive, send):
            await _Instance(self.wsgi_application, self.duplicate_header_limit)(scope, receive, send)

    flask_app = create_app(settings)
    secret = config.mcp_secret() if secret is None else secret
    routes = []
    lifespan = None
    server = None
    if secret:
        if not SECRET_SHAPE.fullmatch(secret):
            raise RuntimeError(
                f"{config.MCP_SECRET_ENV} must be 16 to 128 URL-safe characters (letters, digits, - and _)"
            )
        server = build_server(flask_app.extensions["tables"], account)
        endpoint = server.streamable_http_app(
            streamable_http_path=f"/{secret}",
            stateless_http=True,
            json_response=True,
            transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        )
        routes.append(Mount("/mcp", app=endpoint))

        def lifespan(_app):
            return server.session_manager.run()

    routes.append(Mount("/", app=_Bridge(flask_app)))
    app = Starlette(routes=routes, lifespan=lifespan)
    app.state.flask = flask_app
    app.state.mcp = server
    return app
