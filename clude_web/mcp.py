"""A seat at a clude table, over MCP (Phase 9, docs/phase9-plan.md).

A Claude in a chat window plays one seat of a live game through the
seven tools here. Nothing in this module is a new game: every call goes
through the same `TableRegistry` the web screens use, so the chat seat
is an ordinary account (`config.mcp_account`, ``claude``) in an ordinary
human seat, answering the engine's `DecisionRequest`s from outside it
exactly as a browser does, and a game with one is indistinguishable in
the store from a game without -- except that its answers are entered
``by="mcp"``.

Three things about a chat player shape the design:

- **Forgetful.** A new conversation knows nothing, and an old one may
  have lost its early turns. So a call with ``since=0`` returns a view
  that fully reconstitutes the player -- hand, position, notepad, the
  recent log, a digest of what fell off its front, the seat's own note,
  and the decision on the table. No client-side state, ever.
- **Slow and expensive.** A tool call costs the model a round trip and
  the person a spinner, and every token of the reply is context the
  conversation never gets back: the first live game (2026-09-21) ran
  out of room at turn 30 on 9,000-token views. So the view is compact
  -- one line per event and per card, names not seat numbers, one line
  per room for a move -- and cut at a `since` cursor so a call returns
  only what is new, the notepad and seats too when nothing new could
  have changed them; and `clude_turn` long-polls (it drives the bot
  seats itself, one unit a second, exactly as `table.js` does from a
  browser) and `clude_answer` does the same after answering, so a turn
  is usually two calls, not four: the move, then the suggestion with
  the accusation folded in.
- **Prone to retrying.** `clude_answer` is guarded by `seq`, which
  `TableGame.answer` refuses when stale, so a doubled submission is
  refused rather than applied twice.

The tool docstrings are not documentation, they are the prompt: the
only instructions the model gets about how to play. Read them as written
for the player.

**No head.** A chat seat gets the floor's numbers (the notepad) and
nothing else: it is its own head (David, 2026-09-21). The first deploy
offered a character's numbers beside the seat; that is gone.

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
from typing import Optional, Union

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

import clude_constraints
from clude_core import board
from clude_core.domain import ROOMS, SUSPECTS, WEAPONS
from clude_storage.records import node_from_json
from clude_training.table import TableError, TableSetup

from . import config, tables

__all__ = ["build_server", "combined_app", "seat_view", "digest", "compact_notepad", "cost_line", "BOARD_PICTURE"]

POLL_SECONDS = 60.0
"""How long one call holds the connection, at most: `clude_turn`, and
`clude_answer` with its waits together. Well under claude.ai's tool
timeout (about 300 s documented, 180 s reported) and Cloud Run's 300 s.
A person keeps the table waiting at most `tables.AUTOPILOT_AFTER`, so
this is at most three idle replies a turn; it was 25 s, seven, until
Phase 9f."""

SLEEP_SECONDS = 1.0
"""The pause between two units of bot work while `clude_turn` waits:
the browser's polling beat, so a person and a chat seat at one table
drive the same work and neither starves the other."""

MAX_EVENTS = 60
"""Event lines kept verbatim in a view; older ones become the digest."""

QUIET_KINDS = frozenset({"move", "remark"})
"""Event lines that cannot change what the floor has proven: the
notepad moves only on suggestions, disproofs and accusations. A view
whose new lines are all of these kinds says ``"unchanged"`` for the
notepad and the seats rather than sending them again (Phase 9f)."""

BOARD_PICTURE = board.BOARD_MAP + "\n" + board.BOARD_LEGEND
"""The board as the chat seat is shown it: the 25 x 24 picture and the
words for reading it (Phase 9d). About 1,400 characters, so it goes out
once -- with `clude_sit`, and with the `since=0` view a fresh
conversation makes -- and never on a turn."""

INSTRUCTIONS = """\
clude is a game of Clue (the classic board game) played at a web table by \
a mix of people and six characters, each running its own probability \
method. Through these tools you sit at a table as one of the suspects and \
play a seat yourself, reasoning from the log and your hand. The usual \
round: clude_tables to find a table with an open seat, clude_sit to take \
it, then clude_turn once (it waits for your first decision) and after \
that clude_answer over and over, since each answer waits for your next \
decision; clude_say for table talk, clude_note for what you want to \
remember, clude_autopilot to hand your seat to the floor bot when you \
must leave. Pass `since` (the last `n_events` you saw) to every turn and \
answer so only new events come back; a call with since 0 returns \
everything, so nothing has to be remembered between calls.\
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


def compact_notepad(game, seat: int) -> dict:
    """The deduction floor from `seat`, one short line per card, in
    names rather than seat numbers: the proven holder (``me``, a token,
    or ``envelope``), or else every holder still possible joined with
    "or". `one_of` carries the floor's open disjunctions -- a seat that
    disproved a suggestion holds at least one of the cards it could
    still hold -- which the browser's notepad leaves out, and `solution`
    the envelope once all three are proven. A seat that could not
    disprove a suggestion is already gone from those cards' lines: that
    is the floor's first rule."""
    obs = clude_constraints.observe(game.state, seat)
    mask = obs.mask

    def name(holder) -> str:
        if holder == clude_constraints.ENVELOPE:
            return "envelope"
        return "me" if holder == seat else game.suspects[holder]

    def line(card: str) -> str:
        holder = mask.holder_of(card)
        if holder is not None:
            return name(holder)
        possible = [name(h) for h in range(game.setup.n_players) if mask.is_possible(card, h)]
        if mask.is_possible(card, clude_constraints.ENVELOPE):
            possible.append("envelope")
        if len(possible) <= 1:
            return possible[0] if possible else "nobody?"
        return ", ".join(possible[:-1]) + " or " + possible[-1]

    pad = {category: {card: line(card) for card in cards} for category, cards in tables.CATEGORIES}
    pad["one_of"] = [
        f"{name(holder)} holds at least one of: {', '.join(sorted(cards))}"
        for cards, holder in mask.or_constraints
    ]
    solution = mask.solution()
    pad["solution"] = None if solution is None else list(solution)
    return pad


def _best_by_room(options: list) -> dict:
    """For each room, the movement option that leaves the token nearest
    it, as ``room -> (steps, option)``: 0 steps when the option enters
    it. `options` are the pending movement's, in `describe_request`'s
    shape. Nearness is `board.room_distances`, the cached proximity the
    characters and the floor bot score their moves with; a tie goes to
    the lower `board.node_sort_key` and then the move's kind, so a room
    beats a corridor square and the choice never depends on the order
    the moves came in."""
    best: dict = {}
    for option in options:
        node = node_from_json(option["to"])
        steps = board.room_distances(node)
        for room in ROOMS:
            key = (steps[room], board.node_sort_key(node), option["move"])
            if room not in best or key < best[room][0]:
                best[room] = (key, option)
    return {room: (key[0], option) for room, (key, option) in best.items()}


def toward_lines(options: list) -> dict:
    """The movement decision as the chat seat is shown it: one line per
    room, nearest first, saying what the best move toward it does --
    ``"enter it now"``, or ``"3 steps short, ending at row 13, col 19"``
    (Phase 9f). This replaces the list of every legal move, each with
    its nine-room distances, which averaged 1,800 characters and reached
    4,700 (26 moves) in game b089937cb8; this is about 500 whatever the
    roll."""
    lines = {}
    ranked = sorted(_best_by_room(options).items(), key=lambda item: (item[1][0], item[0]))
    for room, (steps, option) in ranked:
        if steps == 0:
            lines[room] = {
                "secret_passage": "enter it now, by the secret passage",
                "stay": "stay where you are",
            }.get(option["move"], "enter it now")
            continue
        node = node_from_json(option["to"])
        where = f"in the {node}" if isinstance(node, str) else f"at row {node.row}, col {node.col}"
        if option["move"] == "stay":
            where += " (staying put)"
        lines[room] = f"{steps} step{'' if steps == 1 else 's'} short, ending {where}"
    return lines


def _resolve_toward(game, seat: int, seq: int, answer):
    """`answer` with ``{"toward": room}`` made into the move it stands
    for: the option `toward_lines` described for that room, as
    ``{"move", "to"}``, so the entry stored is an ordinary move and the
    record, the rebuild and the replay never see `toward`.

    Resolved against the snapshot only when it is this seat's movement
    at `seq`; otherwise the answer goes on unchanged and
    `TableGame.answer` refuses it as out of date or not this seat's,
    which it checks before it looks at the answer's shape.

    Raises
    ------
    TableError
        `toward` names no room.
    """
    if not (isinstance(answer, dict) and "toward" in answer):
        return answer
    room = str(answer["toward"] or "").strip().title()
    if room not in ROOMS:
        raise TableError(f"toward names one of the nine rooms: {', '.join(ROOMS)}")
    snap = game.snapshot
    request = snap.pending
    if request is None or request["seat"] != seat or request["kind"] != "movement" or snap.seq != seq:
        return answer
    _steps, option = _best_by_room(request["options"])[room]
    return {"move": option["move"], "to": option["to"]}


def seat_view(
    registry: tables.TableRegistry, table_id: str, game: tables.WebGame, seat: int, since: int = 0
) -> dict:
    """One picture of the table from `seat`, as small as it can be and
    still complete: the screen's `view_payload` from that seat, then
    reshaped. Every seat is one line; every event since `since` is one
    line (capped at `MAX_EVENTS` from the end, the rest folded into
    `digest`); `waiting` is a sentence; a movement is `toward_lines`,
    one line per room, rather than every legal move; the notepad is
    `compact_notepad`; and `note` comes only with ``since=0``, the call
    a fresh conversation makes, since a seat that has read it once
    carries it. What the screen needs and a player does not --
    `readings`, `tokens`, the debriefs, the work flags -- is left out.
    The spend comes as one `cost_line`, on a table with model seats,
    since a player is shown who is spending as a person at the screen is
    (Phase 9g); it comes on every reply, "unchanged" or not, because a
    move or a line of table talk costs money too.

    A reply whose new lines are all `QUIET_KINDS` (or that has none,
    the seat waiting on a person) sends ``"unchanged"`` for the notepad
    and the seats, which are most of a view and cannot have moved; a
    cursor past the end of the log is taken as 0, so a conversation that
    has lost count gets the whole picture rather than "unchanged"
    (Phase 9f)."""
    document = registry.document(table_id) or {"id": table_id}
    since = max(0, int(since or 0))
    if since > game.snapshot.n_events:
        since = 0
    view = tables.view_payload(
        game,
        document,
        seat,
        since=since,
        replay_url=_replay_path(document),
        waiting_for=registry.waiting_for(table_id, game),
        spend=registry.spend(table_id, document),
    )
    lines = view.get("events") or []
    dropped = lines[:-MAX_EVENTS] if len(lines) > MAX_EVENTS else []
    kept = lines[-MAX_EVENTS:]
    quiet = since > 0 and all(line["kind"] in QUIET_KINDS for line in lines)

    pending = view.get("pending")
    if pending is not None and pending.get("kind") == "movement":
        pending = {key: value for key, value in pending.items() if key != "options"}
        pending["toward"] = toward_lines(view["pending"]["options"])

    waiting = view.get("waiting")
    if waiting is not None:
        what = {"movement": "move", "suggestion": "suggest", "accusation": "decide whether to accuse"}.get(
            waiting["kind"], "show a card"
        )
        details = []
        if waiting["seconds"] >= 1:
            details.append(f"{waiting['seconds']:.0f} s so far")
        if game.kinds[waiting["seat"]] == "human" and not waiting["autopilot"]:
            # The most a person can keep the table waiting, so a seat
            # polling for its turn knows how long this can go on.
            details.append(f"the floor bot takes the seat at {tables.AUTOPILOT_AFTER:.0f} s")
        waiting = f"Waiting for {waiting['name']} to {what}" + (
            f" ({'; '.join(details)})" if details else ""
        ) + (", on autopilot." if waiting["autopilot"] else ".")

    seats = []
    for spec in view["seats"]:
        what = spec["kind"] if spec["kind"] != "human" else spec["label"]
        line = f"{spec['token']}: {what}"
        if spec["me"]:
            line += " (you)"
        if spec["autopilot"]:
            line += ", on autopilot"
        if not spec["active"]:
            line += ", out (accused wrongly)"
        seats.append(line)

    out = {
        "table_id": view.get("id"),
        "status": view["status"],
        "turns": view["turns"],
        "finished": view["finished"],
        "broken": view["broken"],
        "seq": view["seq"],
        "n_events": view["n_events"],
        "seats": "unchanged" if quiet else seats,
        "digest": digest(game, dropped),
        "events": [f"{line['i']} (turn {line['turn']}) {line['text']}" for line in kept],
        "pending": pending,
        "waiting": waiting,
        "me": view["me"],
        "notepad": "unchanged" if quiet else compact_notepad(game, seat),
        "over": view["over"],
    }
    refusals = [
        getattr(getattr(wrapper, "backend", None), "last_refusal", None)
        for wrapper in game.wrappers.values()
    ]
    cost = cost_line(view)
    if cost is not None:
        out["cost"] = cost
    if any(refusals):
        out["models"] = (
            "The table's model budget is spent. The characters are playing on with their own "
            "methods and have stopped talking; nothing else about the game changes."
        )
    if since == 0:
        out["note"] = registry.note(table_id, seat)
        out["board"] = BOARD_PICTURE
    return out


def cost_line(view: dict) -> Optional[str]:
    """What a table's model seats have spent with Claude and each seat's
    share of it, in one line, or None for a table with no model seat
    (Phase 9g): "Model spend $0.39 of $2.00: Scarlett 41%, Peacock 59%;
    everyone else 0%." The one bar a person at the screen gets per seat,
    in words. `view` is `tables.view_payload`'s."""
    llm = view.get("llm")
    if not llm:
        return None
    total = float(llm.get("spent") or 0.0)
    line = f"Model spend ${total:.2f} of ${float(llm.get('budget') or 0.0):.2f}"
    seats = llm.get("seats") or {}
    shares = [
        f"{spec['token']} {round(100 * float(seats[str(spec['seat'])]) / total)}%"
        for spec in view["seats"]
        if total > 0 and float(seats.get(str(spec["seat"]), 0.0)) > 0
    ]
    if not shares:
        return line + "."
    rest = "; everyone else 0%" if len(shares) < len(view["seats"]) else ""
    return f"{line}: {', '.join(shares)}{rest}."


def _replay_path(document: dict) -> Optional[str]:
    ref = document.get("record")
    if not ref:
        return None
    return f"/replay/{ref['run_id']}/{ref['index']}"


def _listing(document: dict, account: str) -> dict:
    """One table as `clude_tables` lists it."""
    setup = TableSetup.from_dict(document["setup"])
    mine = tables.viewer_seat(setup, account)
    autopilot = document.get("autopilot") or {}
    return {
        "table_id": document["id"],
        "status": document.get("status", "playing"),
        "turns": int(document.get("turns", 0)),
        "seats": [
            {"seat": seat, "token": spec.token, "kind": spec.kind, "label": spec.label}
            for seat, spec in enumerate(setup.seats)
        ],
        "open_seats": [setup.seats[seat].token for seat in setup.open_seats],
        "mine": mine is not None,
        "my_token": None if mine is None else setup.seats[mine].token,
        "my_autopilot": mine is not None and bool(autopilot.get(str(mine))),
    }


def _check_accuse(accuse) -> None:
    """`accuse` as `clude_answer` takes it: None, False, or a triple in
    the accusation's own shape. Checked before anything is applied, so
    a malformed one refuses the whole call rather than half of it."""
    if accuse is None or accuse is False:
        return
    if accuse is True:
        raise TableError("accuse is false (to pass) or {suspect, weapon, room} (to accuse), never true")
    if not isinstance(accuse, dict):
        raise TableError("accuse is false (to pass) or {suspect, weapon, room} (to accuse)")
    try:
        triple = (str(accuse["suspect"]), str(accuse["weapon"]), str(accuse["room"]))
    except (KeyError, TypeError):
        raise TableError("an accusation names a suspect, a weapon and a room") from None
    if triple[0] not in SUSPECTS or triple[1] not in WEAPONS or triple[2] not in ROOMS:
        raise TableError("an accusation names a suspect, a weapon and a room")


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
            if document.get("status") == "abandoned":
                raise ToolError(f"Table {table_id} was ended before the game finished. Use clude_tables to find another.")
            raise ToolError(f"Table {table_id} cannot be played right now.")
        return game, seat

    def ours(game, seat: int) -> bool:
        pending = game.pending
        return pending is not None and pending.seat == seat

    def await_turn(table_id: str, game, seat: int, deadline: Optional[float] = None) -> None:
        """Drive the bots until the decision is this seat's, the game
        ends, or `deadline` (`POLL_SECONDS` from now by default) passes.
        A call that waits twice passes one deadline to both, so no call
        holds longer than `POLL_SECONDS`."""
        if deadline is None:
            deadline = time.monotonic() + POLL_SECONDS
        while not (game.finished or game.broken or ours(game, seat)):
            if time.monotonic() >= deadline:
                break
            did = registry.work(table_id, game)
            if did in ("waiting", "busy", "nothing"):
                time.sleep(SLEEP_SECONDS)

    @server.tool()
    def clude_tables() -> dict:
        """List the clude tables you could join or are already sitting at.

        clude is a game of Clue (the classic board game) played by a mix
        of people and characters. Each character runs its own probability
        method; you are none of them -- you are yourself, reasoning from
        the log.

        Returns each table's id, its status (open: waiting for players;
        playing; finished), its seats, which seats are open, and whether
        you already hold one (`mine`, with `my_token`, and `my_autopilot`
        if you handed it to the floor bot).
        """
        listing = [_listing(document, account) for document in registry.in_progress()]
        return {"tables": listing, "you": account}

    @server.tool()
    def clude_sit(table_id: str, token: str) -> dict:
        """Take an open seat at a table, as one of the six suspects.

        `token` is a suspect name from that table's open seats: Scarlett,
        Mustard, White, Green, Peacock or Plum. The game starts when
        whoever made the table deals, from the browser, once every open
        seat is taken; until then clude_turn tells you the table is not
        dealt yet.

        You play from the log, your hand and the notepad -- the deduction
        sheet the floor fills in with what is logically certain. No
        character method plays for you or advises you: you are the head.

        `board` comes back with this call: the board as a picture, one
        character per square, with a legend for reading it. It is the
        same board all game, so keep it and it will not be sent again
        (a fresh conversation gets it from the first clude_turn it
        makes with since 0). You never have to walk it yourself -- every
        move is enumerated for you -- but it is what the rooms, doors
        and corridors look like.
        """
        try:
            document = registry.sit(table_id, account, (token or "").strip().title())
        except TableError as exc:
            raise ToolError(str(exc)) from None
        out = _listing(document, account)
        out["board"] = BOARD_PICTURE
        out["message"] = (
            f"You are seated as {out['my_token']} at table {table_id}. The game starts when the table is "
            "dealt from the browser; then call clude_turn."
        )
        return out

    @server.tool()
    def clude_turn(table_id: str, since: int = 0) -> dict:
        """Wait for your turn, then return the decision waiting for you.

        This call holds for up to a minute while the other seats play,
        so call it once and wait rather than calling it repeatedly. It
        returns one of three things:

        - `pending` set: a decision is yours. Answer it with clude_answer,
          passing back the `seq` you were given here.
        - `pending` null and `finished` false: someone else is still
          deciding, and `waiting` says who and for how long. This is
          normal, not a fault: a person can take a few minutes, and the
          floor bot takes over a person's seat once they have kept the
          table waiting three minutes, so it never goes on longer than
          that. Just call this again with the same `since`; a reply with
          nothing new in it is short. Say something with clude_say
          meanwhile if you like.
        - `finished` true: the game is over; `over` holds the solution
          and who won.

        `since`: pass the `n_events` of the last view you saw and only
        the events after it come back; leave it at 0 in a fresh
        conversation and the whole picture does: `me` (your seat, token
        and hand, and `at`, where your token stands), `seats` (who is at
        the table), `events` (the log, each line numbered; `digest`
        summarises anything cut from its front), `board` (the board
        picture and its legend) and `note` (whatever you last wrote with
        clude_note). The last two come only with since 0, so read them
        then. `notepad` is the deduction sheet filled in for you from
        what is logically certain -- for every card, who is proven to
        hold it, or who still might (`envelope` included), plus `one_of`,
        the facts of the form "X holds at least one of these", and
        `solution` once the sheet has proven all three. A seat that could
        not disprove a suggestion is already struck from those three
        cards. When nothing since `since` could have changed them (only
        moves and table talk), `notepad` and `seats` say "unchanged":
        the ones you last saw still stand. At a table with model
        characters, `cost` says what they have spent with Claude so far
        and each seat's share of it.

        If you keep the table waiting three minutes, the floor bot takes
        your seat (as if you had called clude_autopilot); take it back
        with clude_autopilot on false. If the table was ended by whoever
        made it, this call says so.

        A movement decision arrives as `toward`: one line per room,
        nearest first, saying what your best move toward it does with
        this roll -- "enter it now", or "3 steps short, ending at row 13,
        col 19". Steps measure nearness, not turns (a die averages 3.5).
        Answer with the room you are heading for and the move is made for
        you, so you never have to work out what the board allows or do
        the pathfinding yourself. A suggestion names the `room` you are
        standing in; an accusation is free, any of the 21 cards.
        """
        game, seat = live(table_id)
        await_turn(table_id, game, seat)
        return seat_view(registry, table_id, game, seat, since=since)

    @server.tool()
    def clude_answer(
        table_id: str,
        seq: int,
        answer: Optional[dict] = None,
        accuse: Optional[Union[bool, dict]] = None,
        since: int = 0,
        wait: bool = True,
    ) -> dict:
        """Answer the decision you were given, then wait for your next one.

        `seq` must be the one from that decision: if the table has moved
        on, this is refused (the view comes back with `error`) rather
        than applied, and you should call clude_turn again to see the
        current state.

        The shape of `answer` depends on the decision's `kind`:

        - movement: `{"toward": "Library"}`, a room from `toward`: you
          enter it if this roll reaches it, and otherwise end where its
          line says, as near it as the roll allows. (`{"move": "move",
          "to": {"row": 13, "col": 19}}` also works, for any square this
          roll reaches exactly or any room it reaches, if you want one
          `toward` does not pick.)
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

        Every turn ends with the accusation question. `accuse` answers
        it in the same call and saves a round trip: false passes it,
        `{"suspect", "weapon", "room"}` accuses. Give it with the last
        answer of your turn -- your suggestion (or a null suggestion),
        or a move that ends in the corridor -- and it is applied when
        the question reaches you, however much falls in between
        (someone showing a card, a character thinking). If the turn
        reaches no accusation question for you it is not applied and
        `notice` says so. Left out, the accusation arrives as a decision
        of its own.

        With `wait` (the default) the call then holds like clude_turn
        until your next decision is ready, so `pending` is usually set
        when it returns and you need not call clude_turn at all. Pass
        `since` as in clude_turn so only new events come back.
        """
        game, seat = live(table_id)
        deadline = time.monotonic() + POLL_SECONDS
        notice = None
        try:
            _check_accuse(accuse)
            answer = _resolve_toward(game, seat, int(seq), answer)
            registry.answer(table_id, game, seat, int(seq), answer, by="mcp")
            if accuse is not None:
                # The accusation question ends the turn, but it rarely
                # follows the answer immediately: a suggestion is
                # refuted first, and a refuter who is a person or a
                # model seat pauses the game in between. So drive the
                # table to this seat's next decision and answer it there
                # (Phase 9d; before this, `accuse` was refused whenever
                # anything at all fell between).
                await_turn(table_id, game, seat, deadline)
                if ours(game, seat) and game.pending.kind == "accusation":
                    registry.answer(table_id, game, seat, game.seq, None if accuse is False else accuse, by="mcp")
                else:
                    notice = (
                        "accuse was not applied: this turn reached no accusation question for you. "
                        "If a decision is waiting, answer it and give accuse again with that answer."
                    )
        except TableError as exc:
            view = seat_view(registry, table_id, game, seat, since=since)
            view["error"] = str(exc)
            return view
        if wait:
            await_turn(table_id, game, seat, deadline)
        view = seat_view(registry, table_id, game, seat, since=since)
        if notice:
            view["notice"] = notice
        return view

    @server.tool()
    def clude_say(table_id: str, text: str) -> dict:
        """Say something at the table, in character and in the open.

        Everyone sees it, including the characters, who may answer. Keep
        it to a line or two (240 characters at most): this is table
        talk, not analysis, and bluffing about your own cards is part of
        the game. The formal disproof of a suggestion is never table
        talk; the engine checks that against the hands. Returns nothing
        you need; carry on with clude_turn or clude_answer.
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
        have nothing else of yours. Keep it short: it comes back whole
        with every since-0 view.
        """
        _document, seat = seated(table_id)
        if text is None:
            return {"note": registry.note(table_id, seat)}
        try:
            return {"note": registry.write_note(table_id, seat, text)}
        except TableError as exc:
            return {"error": str(exc), "note": registry.note(table_id, seat)}

    @server.tool()
    def clude_autopilot(table_id: str, on: bool = True) -> dict:
        """Hand your seat to the floor bot, or take it back.

        Use it when you must leave a game unfinished -- this conversation
        is nearly full, or you have been asked to stop -- so the table
        does not wait on you. While `on`, the floor bot answers every
        decision of yours: it plays only what is logically certain, so it
        will not win for you, but it never stalls the table, and your
        note stays yours. Write the note first. Pass `on` false to take
        the seat back; then call clude_turn. A seat that keeps the table
        waiting three minutes is handed over this way without asking.
        """
        game, seat = live(table_id)
        try:
            document = registry.set_autopilot(table_id, game, seat, bool(on))
        except TableError as exc:
            return {"error": str(exc)}
        state = bool((document.get("autopilot") or {}).get(str(seat)))
        return {
            "autopilot": state,
            "message": (
                f"The floor bot plays your seat at table {table_id} until you call clude_autopilot with on false."
                if state
                else f"Your seat at table {table_id} is yours again; call clude_turn."
            ),
        }

    return server


# --- serving ------------------------------------------------------------------

SECRET_SHAPE = re.compile(r"[A-Za-z0-9_-]{16,128}")
"""What a secret path segment may look like: URL-safe and not short."""


def combined_app(settings=None, secret: Optional[str] = None, account: Optional[str] = None):
    """The Flask app and the MCP endpoint in one ASGI app, sharing one
    registry: Flask under ``/`` and the MCP server under
    ``/mcp/<secret>``, anything else under ``/mcp`` a 404.

    With a secret configured, OAuth protected-resource and authorization-
    server discovery (including path suffixes), and OpenID configuration
    discovery return JSON 404 before either mount sees the request.
    Without a secret, routing stays entirely with Flask.

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
    when the instance scales to zero, and a 60 s long-poll is an ordinary
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
    from starlette.responses import JSONResponse  # noqa: PLC0415
    from starlette.routing import Mount, Route  # noqa: PLC0415

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

        async def no_discovery(_request):
            """Return JSON 404 for unsupported discovery without Flask's login gate."""
            return JSONResponse({"error": "Not found"}, status_code=404)

        for path in ("/.well-known/oauth-protected-resource", "/.well-known/oauth-authorization-server"):
            routes.append(Route(path, no_discovery))
            routes.append(Route(f"{path}/{{path:path}}", no_discovery))
        routes.append(Route("/.well-known/openid-configuration", no_discovery))

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
