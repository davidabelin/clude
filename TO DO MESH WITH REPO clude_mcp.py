"""A seat at a clude table, over MCP (draft).

The point of this module is to let a Claude sitting in a chat window play
one seat of a live game. Nothing here is a new game: every call goes
through the same `TableRegistry` the web screens use, so the chat seat is
just another external seat answering the engine's `DecisionRequest`s, and
a game with one is indistinguishable, in the store, from a game without.

Three things shape the design, all of them consequences of what a chat
player is:

Forgetful. A new conversation knows nothing, and even an old one may have
lost the early turns out of its context. So every call returns a payload
that fully reconstitutes a player: hand, position, notepad, a digest of
the turns that fell off the end, and the decision now on the table. No
client-side state, ever.

Slow and expensive. Each tool call costs the model a round trip and the
user several seconds of watching a spinner. So `turn` long-polls: it
holds the connection, drives the bot seats itself, and comes back either
with the chat seat's decision or with a summary of what happened while it
waited. One call per decision, not five.

Prone to retrying. `answer` is guarded by `seq`, which `WebGame.answer`
already refuses when stale, so a doubled submission is rejected rather
than applied twice. Do not remove that guard for the sake of convenience.

The tool docstrings below are not documentation, they are the prompt: they
are the only instructions the model gets about how to play. Written for
the reader, not the maintainer.

The head. A chat seat may optionally be given the numbers its character's
own method produces -- Peacock's Dempster-Shafer, Plum's exact Bayes, and
so on -- as a head on the headless generator. Default off: a seat with no
head reasons from the log alone, which is the cheaper arm and the more
surprising one. The reading is read-only; it never decides anything, and
the seat is free to disagree with it.

Two rules make this data rather than a feature. The arm is fixed when the
seat is taken and recorded in the table document, because a game whose
seat gained or lost its numbers halfway through measures nothing. And the
reading is the method's own output in the method's own shape -- belief and
plausibility for Dempster-Shafer, a posterior for Plum -- never flattened
to a common vector, since the differences between the six are the entire
point of having six.

Wiring (four places to check against the repo before this runs):

1. `table_payload` -- the view builder currently reached as `_payload` in
   `clude_web.views`. If it stays private, give it a public name.
2. `open_store` -- whatever `clude_cli` uses to turn a `--uri` into a
   `LocalStore` or `GcsStore`.
3. `registry.answer` -- takes no `by`, while `WebGame.answer` does and
   already knows the value ``"llm"``. Thread it through so the entry
   records that the chat seat, not a human, gave this answer; the
   logbooks and any later analysis will want to know.
4. `WebGame.head_reading(seat)` and a `head` field on the seat spec --
   neither exists yet. The sketch is in `webgame_head_reading.py`; it
   belongs next to `stand_in_answer` in `clude_training/table.py`, not
   here, so that the API-driven arm of a sweep and this one read the same
   numbers and a test can prove it without MCP in the way.

Identity. The chat seat is an ordinary account, made once with
`clude_cli users add claude --uri ...`, named here by `CLUDE_MCP_ACCOUNT`.
Seat ownership then resolves through `tables.viewer_seat` exactly as it
does for a browser, and no permission code needs to learn about MCP.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Optional

try:  # the official SDK, or the standalone package
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    from fastmcp import FastMCP

from clude_web import tables
from clude_web.views import _payload as table_payload  # (1)

try:
    from clude_storage import open_store  # (2)
except ImportError:  # pragma: no cover
    open_store = None


ACCOUNT = os.environ.get("CLUDE_MCP_ACCOUNT", "claude")
STORE_URI = os.environ.get("CLUDE_STORE_URI", "data/llm")

POLL_SECONDS = float(os.environ.get("CLUDE_MCP_POLL", "25"))
"""How long `turn` holds the connection. Under the client's own timeout,
and well under Cloud Run's."""

MAX_EVENTS = 60
"""Events kept verbatim in a payload; older ones become the digest."""

HEAD_DEFAULT = os.environ.get("CLUDE_MCP_HEAD", "").strip().lower() in ("1", "on", "true", "yes")
"""Whether a chat seat takes its character's numbers unless told otherwise.
Off: clueless is the default arm."""

mcp = FastMCP("clude")

_registry_singleton: Optional[tables.TableRegistry] = None


def _registry() -> tables.TableRegistry:
    """The one registry for this process.

    If this module is mounted beside the Flask app (see `combined_app`),
    swap this for the app's own `app.extensions["tables"]`: two registries
    over one store in one process would each cache games the other is
    changing.
    """
    global _registry_singleton
    if _registry_singleton is None:
        if open_store is None:
            raise RuntimeError("wire up clude_storage.open_store (see the module docstring)")
        _registry_singleton = tables.TableRegistry(open_store(STORE_URI))
    return _registry_singleton


# --- shaping what the model sees -------------------------------------------


def _digest(dropped: list[dict]) -> str:
    """The turns that fell off the front of the log, in a line or two.

    Deliberately lossy and deliberately not clever: counts and the few
    facts a player would actually carry in their head. Anything the seat
    wants to keep beyond this it should have written to its notepad.
    """
    if not dropped:
        return ""
    suggestions = [e for e in dropped if e.get("kind") == "suggestion"]
    shown = [e for e in suggestions if e.get("refuter") is not None]
    unrefuted = [e for e in suggestions if e.get("refuter") is None]
    parts = [f"{len(dropped)} earlier events"]
    if suggestions:
        parts.append(f"{len(suggestions)} suggestions, {len(shown)} refuted")
    if unrefuted:
        which = "; ".join(
            f"turn {e.get('turn')}: {e.get('suspect')}/{e.get('weapon')}/{e.get('room')} went unrefuted"
            for e in unrefuted[-4:]
        )
        parts.append(which)
    return ". ".join(parts) + "."


def _view(table_id: str, seat: int) -> dict:
    """One self-contained picture of the table from `seat`.

    Trimmed twice over: the log is capped and the rest summarised, and the
    spectator extras are dropped. `readings` in particular must not go out
    whole -- those are every bot's probability readings, and a player seat
    has no business seeing another seat's. What may go out, and only when
    this seat took a head, is this seat's own.
    """
    game = _registry().game(table_id)
    payload = table_payload(table_id, game, 0)

    events = payload.get("events") or []
    kept = events[-MAX_EVENTS:]
    digest = _digest(events[: -MAX_EVENTS or None])

    for noise in ("readings", "tokens"):
        payload.pop(noise, None)

    payload["events"] = kept
    payload["digest"] = digest
    payload["seat"] = seat
    payload["head"] = _head(game, seat)
    return payload


def _head(game, seat: int) -> Optional[dict]:
    """This seat's own reading, if it was seated with a head.

    None means clueless, and the tools say so rather than quietly omitting
    the field: a seat that cannot tell which arm it is in will narrate
    confidence it does not have.
    """
    spec = game.setup.seats[seat]
    if not getattr(spec, "head", False):
        return None
    method = tables.replay_data.seat_method(spec.token)
    return {"method": method, "reading": game.head_reading(seat)}  # (4)


def _my_seat(table_id: str) -> int:
    """This account's seat at a table, or an error the model can act on."""
    game = _registry().game(table_id)
    seat = tables.viewer_seat(game.setup, ACCOUNT)
    if seat is None:
        raise ValueError(
            f"You are not sitting at table {table_id}. Use clude_tables to find one with an open seat."
        )
    return seat


# --- the tools --------------------------------------------------------------


@mcp.tool()
def clude_tables() -> dict:
    """List the clude tables you could join or are already sitting at.

    clude is a game of Clue (the classic board game) played by a mix of
    people and characters. Each character runs its own probability method;
    you are none of them -- you are yourself, reasoning from the log.

    Returns each table's id, its seats, whether one is open, and whether
    you already hold one.
    """
    registry = _registry()
    out = []
    for document in registry.in_progress():
        setup = tables.TableSetup.from_dict(document["setup"])
        out.append(
            {
                "table_id": document["id"],
                "status": document.get("status", "playing"),
                "turns": document.get("turns", 0),
                "seats": [
                    {"token": spec.token, "kind": spec.kind, "label": spec.label}
                    for spec in setup.seats
                ],
                "open_seats": [spec.token for spec in setup.open_seats],
                "mine": tables.viewer_seat(setup, ACCOUNT) is not None,
            }
        )
    return {"tables": out, "you": ACCOUNT}


@mcp.tool()
def clude_sit(table_id: str, token: str, head: bool = HEAD_DEFAULT) -> dict:
    """Take an open seat at a table, as one of the six suspects.

    `token` is a suspect name from that table's open seats: Scarlett,
    Mustard, White, Green, Peacock or Plum. Returns your hand and the
    state of the table; the game starts when whoever made the table deals.

    `head` decides how you play the whole game, and cannot be changed once
    you are seated:

    - false (the default): you reason from the log and your hand alone.
    - true: you also receive, every turn, the numbers your character's own
      method produces -- Plum computes an exact posterior, Peacock belief
      and plausibility intervals, Green a bandit's estimates, and so on.
      They arrive in `head.reading`, in that method's own shape, and they
      are advisory. The method cannot see the table talk or read anyone's
      hesitation; you can. Where you disagree with it, say why.

    Ask which arm is wanted if it has not been said. The two produce
    different data and it matters which one this game is.
    """
    registry = _registry()
    registry.sit(table_id, token, ACCOUNT, head=bool(head))  # (4)
    seat = _my_seat(table_id)
    return _view(table_id, seat)


@mcp.tool()
def clude_turn(table_id: str) -> dict:
    """Wait for your turn, then return the decision waiting for you.

    This call blocks for up to half a minute while the other seats play,
    so call it once and wait rather than calling it repeatedly. It returns
    one of three things:

    - `pending` set: a decision is yours. Answer it with clude_answer,
      passing back the `seq` you were given here.
    - `pending` null and `finished` false: the table is still moving. Say
      something with clude_say if you like, then call this again.
    - `finished` true: the game is over; `over` holds the solution and who
      won.

    What comes back is everything you need and nothing you have to
    remember: `me` is your hand, suspect and position; `events` is the
    recent log; `digest` summarises what fell off the front of it;
    `notepad` is whatever you last wrote with clude_note. `head` is null
    if you are playing clueless, and otherwise carries your character's
    own numbers for this position -- advisory, not an instruction.

    Every decision arrives with its legal answers already enumerated, so
    you never have to work out what the board allows -- only which of the
    listed options you want.
    """
    seat = _my_seat(table_id)
    registry = _registry()
    deadline = time.monotonic() + POLL_SECONDS

    while True:
        game = registry.game(table_id)
        if game.finished or game.broken:
            break
        if game.pending is not None and game.pending.seat == seat:
            break
        if time.monotonic() >= deadline:
            break
        # Not ours: push the table along one unit of bot work, or idle if
        # another worker has it or the interval says wait.
        if game.pending is None:
            did = registry.work(table_id, game)
            if not did or did == "waiting":
                time.sleep(1.0)
        else:
            time.sleep(1.0)  # another seat is being asked

    return _view(table_id, seat)


@mcp.tool()
def clude_answer(table_id: str, seq: int, answer: dict | None) -> dict:
    """Answer the decision clude_turn gave you, and see what follows.

    `seq` must be the one from that decision: if the table has moved on,
    this is refused rather than applied, and you should call clude_turn
    again to see the current state.

    The shape of `answer` depends on the decision's `kind`:

    - movement: `{"move": ..., "to": ...}`, copied from one of the
      listed `options`. Copy both fields from the same option.
    - suggestion: `{"suspect": "Plum", "weapon": "Rope"}` -- the room is
      the one you are standing in. Pass null to make no suggestion.
    - accusation: null to say nothing, or `{"suspect": ..., "weapon":
      ..., "room": ...}` to end the game on it. A wrong accusation puts
      you out for good, so only when you are sure.
    - refute: `{"card": ...}`, one of the listed `candidates` -- cards
      from your own hand that answer someone's suggestion. You must show
      one when you can, and only the suggester sees which.

    Returns the table as it stands after your answer.
    """
    seat = _my_seat(table_id)
    registry = _registry()
    game = registry.game(table_id)
    try:
        registry.answer(table_id, game, seat, int(seq), answer)  # (3) by="llm"
    except tables.TableError as exc:
        view = _view(table_id, seat)
        view["error"] = str(exc)
        return view
    return _view(table_id, seat)


@mcp.tool()
def clude_say(table_id: str, text: str) -> dict:
    """Say something at the table, in character and in the open.

    Everyone sees it, including the other characters, who may answer. Keep
    it to a line or two -- this is table talk, not analysis, and bluffing
    is part of the game. Returns nothing you need; carry on with
    clude_turn.
    """
    seat = _my_seat(table_id)
    registry = _registry()
    game = registry.game(table_id)
    chat = getattr(registry, "chat", None)
    if chat is not None:
        chat(table_id, game, seat, text)
    else:  # pragma: no cover -- until the registry grows one
        game.remark(seat, text, about="chat")
    return {"said": text}


@mcp.tool()
def clude_note(table_id: str, text: str | None = None) -> dict:
    """Read or replace your notepad -- the one thing that outlives you.

    With no `text`, returns what is written. With `text`, replaces it
    wholly, so include anything you still want to keep.

    Write down what you have deduced and how you know it, not what the log
    already says: which cards you have seen and from whom, which
    suggestions went unrefuted, what you have ruled out. A later call, in
    a later conversation, will have nothing else of yours.
    """
    seat = _my_seat(table_id)
    registry = _registry()
    game = registry.game(table_id)
    if text is None:
        return {"notepad": game.notepad(seat)}
    game.write_notepad(seat, text)
    registry.save(table_id, game)
    return {"notepad": text}


# --- serving ----------------------------------------------------------------


def combined_app():
    """The Flask app and this MCP server in one process, sharing one
    registry: Flask under `/`, MCP at `/mcp`.

    Worth the small ceremony. Two Cloud Run services over one bucket would
    each hold their own cache of a table and write the whole document
    back, and the loser of a race drops an entry -- the one failure mode
    this codebase has otherwise designed out.
    """
    from asgiref.wsgi import WsgiToAsgi
    from starlette.applications import Starlette
    from starlette.routing import Mount

    from clude_web import create_app

    flask_app = create_app()
    global _registry_singleton
    _registry_singleton = flask_app.extensions["tables"]

    return Starlette(
        routes=[
            Mount("/mcp", app=mcp.streamable_http_app()),
            Mount("/", app=WsgiToAsgi(flask_app)),
        ]
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
