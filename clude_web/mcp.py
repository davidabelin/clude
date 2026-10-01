"""A seat at a clude table, over MCP (Phase 9, docs/phase9-plan.md).

A chatbot in a chat window (a Claude at claude.ai, or another at
ChatGPT) plays one seat of a live game through the tools here, or
watches one. Nothing in this module is a new game: every call goes
through the same `TableRegistry` the web screens use, so the chat seat
is an ordinary account in an ordinary human seat -- logged in with
`clude_login` as a person logs in at the form, each chatbot its own
account since Phase 9j -- answering the engine's `DecisionRequest`s from outside it
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

import hashlib
import re
import time
from typing import Optional, Union

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

import clude_constraints
from clude_core import board
from clude_core.domain import ROOMS, SUSPECTS, WEAPONS, players_after
from clude_storage import GameRecord
from clude_storage.records import node_from_json
from clude_training.table import TableError, TableSetup

from . import config, replay_data, styles, tables, users

__all__ = [
    "build_server", "combined_app", "seat_view", "digest", "compact_notepad", "shown_notepad", "order_line",
    "held_pass", "cost_line", "watch_view", "issue_login", "check_login", "shows_costs", "BOARD_PICTURE",
]

POLL_SECONDS = 60.0
"""How long one call holds the connection, at most: `clude_turn`, and
`clude_answer` with its waits together. Well under claude.ai's tool
timeout (about 300 s documented, 180 s reported) and Cloud Run's 300 s.
A person keeps the table waiting at most the table's time-out
(`tables.TURN_TIMEOUT`, 90 s), so this is at most two idle replies a
turn; it was 25 s, seven, until Phase 9f."""

SLEEP_SECONDS = 1.0
"""The pause between two units of bot work while `clude_turn` waits:
the browser's polling beat, so a person and a chat seat at one table
drive the same work and neither starves the other."""

MAX_EVENTS = 60
"""Event lines kept verbatim in a view; older ones become the digest."""

REPLAY_PAGE = 120
"""Event lines in one page of `clude_replay`: a whole game is 150 to
400, too many for one reply to a chat."""

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
play a seat yourself, reasoning from the log and your hand, or watch. \
First clude_login, with the name and password the person you are chatting \
with gives you, and pass the `login` it returns to every other tool. The \
usual round: clude_tables to find a table with an open seat, clude_sit to take \
it, then clude_turn once (it waits for your first decision) and after \
that clude_answer over and over, since each answer waits for your next \
decision; clude_say for table talk, clude_note for what you want to \
remember, clude_autopilot to hand your seat to the floor bot when you \
must leave, clude_logout when you are done. Pass `since` (the last `n_events` you saw) to every turn and \
answer so only new events come back; a call with since 0 returns \
everything, so nothing has to be remembered between calls. To look on \
instead: clude_watch for a live table, clude_games and clude_replay for \
finished ones.\
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
    registry: tables.TableRegistry,
    table_id: str,
    game: tables.WebGame,
    seat: int,
    since: int = 0,
    costs: bool = True,
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
    (Phase 9g) -- and so only when `costs`, which the tools set from the
    account's look: Developer alone shows costs (D17, 2026-10-01); it
    comes on every reply, "unchanged" or not, because a
    move or a line of table talk costs money too. Each seat's line ends
    with its certainty (Phase 9h), the number behind the screen's
    coloured name-tag, which only a non-quiet event can move.

    Phase 9i: each seat's line carries its hand size and `order` says
    who is asked to disprove this seat's suggestions, in turn. The seat's
    `tables.notepad_level` decides the notepad: the floor's
    (`compact_notepad`), only the cards seen (`shown_notepad`), or none
    at all, the last two also dropping the seat's own certainty. `over`
    says which level the game was played at.

    A reply whose new lines are all `QUIET_KINDS` (or that has none,
    the seat waiting on a person) sends ``"unchanged"`` for the notepad
    and the seats, which are most of a view and cannot have moved; a
    cursor past the end of the log is taken as 0, so a conversation that
    has lost count gets the whole picture rather than "unchanged"
    (Phase 9f)."""
    document = registry.document(table_id) or {"id": table_id}
    level = tables.notepad_level(document, seat)
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

    waiting = waiting_line(game, view)
    seats = [seat_line(game, spec, hide_certainty=spec["me"] and level != "full") for spec in view["seats"]]

    if level == "full":
        notepad = compact_notepad(game, seat)
    elif level == "shown":
        notepad = shown_notepad(game, seat, view["n_events"])
    else:
        notepad = None
    over = view["over"]
    if over is not None:
        over = dict(over, notepad=level)
        if over.get("replay"):
            over["replay_note"] = "The replay needs a sign-in: it is for the person you are chatting with."

    out = {
        "table_id": view.get("id"),
        "status": view["status"],
        "turns": view["turns"],
        "finished": view["finished"],
        "broken": view["broken"],
        "seq": view["seq"],
        "n_events": view["n_events"],
        "seats": "unchanged" if quiet else seats,
        "order": "unchanged" if quiet else order_line(game, seat, view["seats"]),
        "digest": digest(game, dropped),
        "events": [f"{line['i']} (turn {line['turn']}) {line['text']}" for line in kept],
        "pending": pending,
        "waiting": waiting,
        "me": view["me"],
        "notepad": "unchanged" if quiet else notepad,
        "over": over,
    }
    if level == "none":
        # Hard mode at its hardest: the log and the hand, and no notepad
        # at all, not even "unchanged" (Phase 9i).
        del out["notepad"]
    refusals = [
        getattr(getattr(wrapper, "backend", None), "last_refusal", None)
        for wrapper in game.wrappers.values()
    ]
    cost = cost_line(view) if costs else None
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


def waiting_line(game, view: dict) -> Optional[str]:
    """Who the table is waiting on, as a sentence, or None: from
    `view_payload`'s ``waiting``. For a person, the most they can keep
    the table waiting, so a seat polling for its turn knows how long
    this can go on."""
    waiting = view.get("waiting")
    if waiting is None:
        return None
    what = {"movement": "move", "suggestion": "suggest", "accusation": "decide whether to accuse"}.get(
        waiting["kind"], "show a card"
    )
    details = []
    if waiting["seconds"] >= 1:
        details.append(f"{waiting['seconds']:.0f} s so far")
    if game.kinds[waiting["seat"]] == "human" and not waiting["autopilot"]:
        details.append(f"the floor bot plays this turn at {waiting.get('timeout', view['timeout']):.0f} s")
    return f"Waiting for {waiting['name']} to {what}" + (
        f" ({'; '.join(details)})" if details else ""
    ) + (", on autopilot." if waiting["autopilot"] else ".")


def seat_line(game, spec: dict, hide_certainty: bool = False) -> str:
    """One seat of `view_payload`'s ``seats`` in a line: its token, who
    plays it (a person by name, capitalised: Phase 9j), its hand size
    (public from the deal: 18 cards dealt round, so the first seats may
    hold one more; Phase 9i), autopilot, out, and its certainty.

    The certainty is the poker face (Phase 9h): everyone at the table
    sees how far each seat has come from guessing to knowing, and a chat
    seat is at the table too (David, 2026-09-26). `hide_certainty` drops
    it for a hard-mode seat's own line, where it is the floor's reading
    of the notepad and at 100% would be the answer (Phase 9i)."""
    what = spec["kind"] if spec["kind"] != "human" else users.display_name(spec["label"])
    line = f"{spec['token']}: {what}"
    if spec.get("me"):
        line += " (you)"
    line += f", {len(game.state.hands[spec['seat']])} cards"
    if spec["autopilot"]:
        line += ", on autopilot"
    if not spec["active"]:
        line += ", out (accused wrongly)"
    if spec.get("certainty") is not None and not hide_certainty:
        line += f", certainty {round(float(spec['certainty']) * 100)}%"
    return line


def watch_view(
    registry: tables.TableRegistry, table_id: str, game: tables.WebGame, since: int = 0, costs: bool = True
) -> dict:
    """A live table as a spectator sees it (Phase 9j), shaped as
    `seat_view` shapes a seat's: `view_payload` from no seat, so hands
    stay hidden and the card shown at a refutation is not named, then
    one line per seat and per event, the front of a long log folded
    into `digest`. The deduction bars the browser's Watch draws are left
    out; each seat's certainty is in its line. `watching` names who else
    is looking on."""
    document = registry.document(table_id) or {"id": table_id}
    since = max(0, int(since or 0))
    if since > game.snapshot.n_events:
        since = 0
    view = tables.view_payload(
        game,
        document,
        None,
        since=since,
        replay_url=_replay_path(document),
        waiting_for=registry.waiting_for(table_id, game),
        spend=registry.spend(table_id, document),
    )
    lines = view.get("events") or []
    dropped = lines[:-MAX_EVENTS] if len(lines) > MAX_EVENTS else []
    out = {
        "table_id": table_id,
        "status": view["status"],
        "turns": view["turns"],
        "finished": view["finished"],
        "broken": view["broken"],
        "n_events": view["n_events"],
        "seats": [seat_line(game, spec) for spec in view["seats"]],
        "digest": digest(game, dropped),
        "events": [f"{line['i']} (turn {line['turn']}) {line['text']}" for line in lines[-MAX_EVENTS:]],
        "waiting": waiting_line(game, view),
        "watching": [users.display_name(name) for name in registry.watching(table_id)],
        "over": view["over"],
    }
    cost = cost_line(view) if costs else None
    if cost is not None:
        out["cost"] = cost
    return out


def _undealt(table_id: str, document: dict) -> dict:
    """A table not dealt yet, as `clude_turn` and `clude_watch` report
    it: what it is waiting for, and to call again."""
    setup = TableSetup.from_dict(document["setup"])
    still_open = [setup.seats[other].token for other in setup.open_seats]
    return {
        "table_id": table_id,
        "status": "open",
        "finished": False,
        "pending": None,
        "waiting": (
            f"Waiting for the table to be dealt; open seats: {', '.join(still_open)}. Call again."
            if still_open
            else "Every seat is taken; waiting for whoever made the table to deal it. Call again."
        ),
    }


# --- logins (Phase 9j) --------------------------------------------------------

LOGIN_SALT = "clude-mcp-login"
"""Keeps an MCP login from ever passing for anything else the session
secret signs."""

LOGIN_DAYS = 30
"""How long a login lasts. A chat forgets it anyway with its
conversation; this only bounds one that leaks."""


def _fingerprint(account: dict) -> str:
    """A short digest of the account's password hash: in the login, so
    changing the password (``users passwd``) ends every login made with
    the old one. The hash itself never leaves the store."""
    return hashlib.sha256(account["password_hash"].encode()).hexdigest()[:16]


def issue_login(secret_key, account: dict) -> str:
    """A signed login for `account` (a stored account document): what
    `clude_login` returns and every other tool takes. Signed with the
    session secret, not stored, so it survives a restart and scales to
    zero with the service."""
    serializer = URLSafeTimedSerializer(secret_key, salt=LOGIN_SALT)
    return serializer.dumps(
        {"key": account["key"], "pw": _fingerprint(account), "ep": int(account.get("mcp_epoch") or 0)}
    )


def check_login(secret_key, store, login) -> str:
    """The account key a login stands for.

    Raises
    ------
    ToolError
        No login, a forged or mangled one, one past `LOGIN_DAYS`, one
        for an account removed or whose password has changed since, or
        one ended by `clude_logout` (`users.end_mcp_logins`; a login made
        before 2026-10-01 has no epoch and reads as 0).
    """
    if not login:
        raise ToolError("Log in first: clude_login with the name and password you were given.")
    serializer = URLSafeTimedSerializer(secret_key, salt=LOGIN_SALT)
    try:
        data = serializer.loads(str(login), max_age=LOGIN_DAYS * 86400)
    except SignatureExpired:
        raise ToolError("Your login has run out. Call clude_login again.") from None
    except BadSignature:
        raise ToolError("That is not a clude login. Call clude_login for one.") from None
    account = users.get_user(store, str(data.get("key", "")))
    if account is None or _fingerprint(account) != data.get("pw"):
        raise ToolError("Your login is no longer good (the password changed?). Call clude_login again.")
    if int(data.get("ep") or 0) != int(account.get("mcp_epoch") or 0):
        raise ToolError("You logged out. Call clude_login to log in again.")
    return account["key"]


def shows_costs(store, account: str) -> bool:
    """Whether `account`'s look shows costs: Developer only (D17), the
    same rule as the browser's (`styles.Style.costs`)."""
    return styles.style_named(users.style_of(users.get_user(store, account))).costs


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
    """The finished game's replay: a whole URL when the service knows
    its own address (`config.public_url`, Phase 9i), since a chat seat
    has no page for a path to be relative to; the path otherwise."""
    ref = document.get("record")
    if not ref:
        return None
    return f"{config.public_url() or ''}/replay/{ref['run_id']}/{ref['index']}"


def shown_notepad(game, seat: int, n_events: int) -> dict:
    """The hard-mode notepad (``shown``, Phase 9i): the seat's hand and
    what changed hands in private -- each card shown to it and who
    showed it, and each card it showed and to whom -- over the whole
    game, not the view's window, so a card shown early is never lost to
    the digest. Nothing the floor deduced: that is the player's work."""
    shown_to_me: dict = {}
    i_showed: dict = {}
    for event in game.events[:n_events]:
        suggestion = getattr(event, "suggestion", None)
        if suggestion is None or suggestion.refuter is None or suggestion.card_shown is None:
            continue
        if suggestion.suggester == seat:
            shown_to_me[suggestion.card_shown] = game.suspects[suggestion.refuter]
        elif suggestion.refuter == seat:
            cards = i_showed.setdefault(game.suspects[suggestion.suggester], [])
            if suggestion.card_shown not in cards:
                cards.append(suggestion.card_shown)
    return {"hand": sorted(game.state.hands[seat]), "shown_to_me": shown_to_me, "i_showed": i_showed}


def order_line(game, seat: int, seats: list) -> str:
    """Who is asked to disprove this seat's suggestions, in the order
    the engine asks them (`players_after`, Phase 9i). A seat that is out
    still shows cards, and the line says so. `seats` are
    `view_payload`'s."""
    names = [
        game.suspects[other] + ("" if seats[other]["active"] else " (out, still shows cards)")
        for other in players_after(len(game.suspects), seat)
    ]
    return "Seats are listed in play order. Your suggestions are put to them in this order: " + ", ".join(names) + "."


def held_pass(game, seat: int, since_event: int, level: str) -> Optional[str]:
    """Why a pass given ahead (``accuse: false``) should not be applied,
    or None (Phase 9i). Given with the suggestion, the pass was decided
    before the answer to it came in; if nobody could disprove it, or the
    notepad now proves the envelope, the answer changed the question,
    and table 5019abeb0a was lost to exactly that. A suggestion wholly
    of the seat's own cards is a bluff whose silence says nothing new,
    so it does not hold the pass. The proven envelope counts only on the
    full notepad: in hard mode the notice would be the floor's hint."""
    hand = game.state.hands[seat]
    for event in game.events[since_event:]:
        suggestion = getattr(event, "suggestion", None)
        if (
            suggestion is not None
            and suggestion.suggester == seat
            and suggestion.refuter is None
            and not set(suggestion.cards()) <= hand
        ):
            return (
                "accuse false was not applied: nobody could disprove your suggestion "
                f"({suggestion.suspect}, {suggestion.weapon}, {suggestion.room}). "
                "The accusation question is yours: answer it now."
            )
    if level == "full" and clude_constraints.observe(game.state, seat).mask.solution() is not None:
        return (
            "accuse false was not applied: your notepad now proves the solution. "
            "The accusation question is yours: answer it now."
        )
    return None


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
            {
                "seat": seat,
                "token": spec.token,
                "kind": spec.kind,
                "label": users.display_name(spec.label) if spec.kind == "human" else spec.label,
            }
            for seat, spec in enumerate(setup.seats)
        ],
        "open_seats": [setup.seats[seat].token for seat in setup.open_seats],
        "mine": mine is not None,
        "my_token": None if mine is None else setup.seats[mine].token,
        "my_autopilot": mine is not None and bool(autopilot.get(str(mine))),
        "my_notepad": None if mine is None else tables.notepad_level(document, mine),
        "timeout": tables.timeout_for(document),
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


def build_server(registry: tables.TableRegistry, secret_key, limiter=None) -> MCPServer:
    """The MCP server over `registry`, for whoever logs in.

    Parameters
    ----------
    registry : TableRegistry
        The one registry of the process: the Flask app's own when served
        beside it (`combined_app`), a fresh one over a temp store in a
        test. Never a second registry over a store another one holds.
    secret_key : str or bytes
        What logins are signed with: the Flask app's session secret, so
        an MCP login is exactly as good as a browser's.
    limiter : auth.RateLimit or None
        The login brake, the app's own when served beside it, so the
        form and `clude_login` count one account's attempts together.

    Every tool but `clude_login` takes `login`, the string that call
    returned, and acts as that account (Phase 9j): an ordinary account,
    made with ``users add``, whose seat resolves through
    `tables.viewer_seat` exactly as a browser's does. Before 9j the
    server played as one fixed account, ``claude``.
    """
    from .auth import RateLimit  # noqa: PLC0415

    limiter = limiter if limiter is not None else RateLimit()
    server = MCPServer("clude", instructions=INSTRUCTIONS)
    server.registry = registry  # what this server plays on, for a test to check

    def who(login: str) -> str:
        """The account key `login` stands for, or a `ToolError`."""
        return check_login(secret_key, registry.store, login)

    def seated(table_id: str, account: str) -> tuple:
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

    def live(table_id: str, account: str) -> tuple:
        """The live game and this account's seat, or a `ToolError`."""
        document, seat = seated(table_id, account)
        game = registry.game(table_id)
        if game is None:
            if document.get("status") == "open":
                raise ToolError(
                    f"Table {table_id} has not been dealt yet; whoever made it deals from the browser. "
                    "clude_turn waits for the deal."
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
    def clude_login(name: str, password: str) -> dict:
        """Log in to clude with the name and password you were given.

        The person you are chatting with has them: every player,
        people and chatbots alike, has an account of their own. This
        returns `login`, which every other tool needs: pass it on every
        call. It lasts 30 days and ends early if the password changes; a
        tool that refuses it asks you to log in again. Five wrong tries
        in a minute and the name is locked out for that minute.
        """
        key = (name or "").strip().lower() or "-"
        if not limiter.check(key):
            raise ToolError("Too many attempts. Wait a minute.")
        account = users.authenticate(registry.store, name, password)
        if account is None:
            raise ToolError("Wrong name or password.")
        limiter.clear(account["key"])
        you = users.display_name(account["key"])
        return {
            "login": issue_login(secret_key, account),
            "you": you,
            "message": (
                f"You are logged in as {you}. Pass `login` to every other tool. clude_tables lists "
                "the tables to play or watch; clude_games the finished games to replay."
            ),
        }

    @server.tool()
    def clude_logout(login: str) -> dict:
        """Log out of clude: end every login this account holds over MCP.

        Call it when you are done, or if the person you are chatting with
        asks. Every login made for this account stops working at once,
        this one included (a login is not stored anywhere, so they all end
        together); the seat you hold at a table stays yours, and the
        floor bot plays its turns on the clock as usual. clude_login gives
        a fresh login whenever you want one. The person's own browser
        sign-in is not affected.
        """
        account = who(login)
        users.end_mcp_logins(registry.store, account)
        you = users.display_name(account)
        return {"you": you, "message": f"{you} is logged out. clude_login to come back."}

    @server.tool()
    def clude_tables(login: str) -> dict:
        """List the clude tables you could join or are already sitting at.

        clude is a game of Clue (the classic board game) played by a mix
        of people and characters. Each character runs its own probability
        method; you are none of them -- you are yourself, reasoning from
        the log.

        Returns each table's id, its status (open: waiting for players;
        playing; finished), its seats, which seats are open, and whether
        you already hold one (`mine`, with `my_token`, `my_autopilot`
        if you handed it to the floor bot, and `my_notepad`, the notepad
        you chose with clude_sit).
        """
        account = who(login)
        listing = [_listing(document, account) for document in registry.in_progress()]
        return {"tables": listing, "you": users.display_name(account)}

    @server.tool()
    def clude_sit(login: str, table_id: str, token: str, notepad: str = "full") -> dict:
        """Take an open seat at a table, as one of the six suspects.

        `token` is a suspect name from that table's open seats: Scarlett,
        Mustard, White, Green, Peacock or Plum. The game starts when
        whoever made the table deals, from the browser, once every open
        seat is taken; clude_turn waits for the deal.

        You play from the log and your hand, and by default the notepad
        -- the deduction sheet the floor fills in with what is logically
        certain. No character method plays for you or advises you: you
        are the head. `notepad` chooses how much of the sheet you get,
        for the whole game:

        - "full" (the default): the whole deduction sheet.
        - "shown": no deductions, only your hand, each card shown to you
          and by whom, and each card you showed and to whom. The
          deduction is yours. Your own certainty is left out of `seats`
          too, since it is the sheet's reading.
        - "none": no notepad at all: the log and your hand.

        Call clude_sit again for the seat you hold to change it before
        the deal; after the deal it is fixed, and the ending records it.

        `board` comes back with this call: the board as a picture, one
        character per square, with a legend for reading it. It is the
        same board all game, so keep it and it will not be sent again
        (a fresh conversation gets it from the first clude_turn it
        makes with since 0). You never have to walk it yourself -- every
        move is enumerated for you -- but it is what the rooms, doors
        and corridors look like.
        """
        account = who(login)
        token = (token or "").strip().title()
        level = (notepad or "full").strip().lower()
        try:
            if level not in tables.NOTEPAD_LEVELS:
                raise TableError(f"notepad is one of: {', '.join(tables.NOTEPAD_LEVELS)}")
            document = registry.document(table_id)
            setup = None if document is None else TableSetup.from_dict(document["setup"])
            mine = None if setup is None else tables.viewer_seat(setup, account)
            if mine is None or setup.seats[mine].token != token or document.get("status") != "open":
                # Sitting down; `sit` refuses a second seat, a taken one
                # and a table already dealt.
                document = registry.sit(table_id, account, token)
                mine = tables.viewer_seat(TableSetup.from_dict(document["setup"]), account)
            document = registry.set_notepad_level(table_id, mine, level)
        except TableError as exc:
            raise ToolError(str(exc)) from None
        out = _listing(document, account)
        out["board"] = BOARD_PICTURE
        out["message"] = (
            f"You are seated as {out['my_token']} at table {table_id}, notepad {level}. The game starts "
            "when the table is dealt from the browser; call clude_turn, which waits for the deal."
        )
        return out

    @server.tool()
    def clude_turn(login: str, table_id: str, since: int = 0) -> dict:
        """Wait for your turn, then return the decision waiting for you.

        This call holds for up to a minute while the other seats play,
        or while the table waits to be dealt, so call it once and wait
        rather than calling it repeatedly. Before the deal it comes back
        with `status` "open" and `waiting` saying what the table is
        waiting for; call it again. After, it returns one of three things:

        - `pending` set: a decision is yours. Answer it with clude_answer,
          passing back the `seq` you were given here.
        - `pending` null and `finished` false: someone else is still
          deciding, and `waiting` says who and for how long. This is
          normal, not a fault: a person may think for a while, and the
          floor bot plays a person's turn for them once they have kept
          the table waiting the table's time-out (90 s; 30 s at a speed
          table; 30 s at most to show a card), so it never goes on longer
          than that. Just call this
          again with the same `since`; a reply with
          nothing new in it is short. Say something with clude_say
          meanwhile if you like.
        - `finished` true: the game is over; `over` holds the solution
          and who won.

        `since`: pass the `n_events` of the last view you saw and only
        the events after it come back; leave it at 0 in a fresh
        conversation and the whole picture does: `me` (your seat, token
        and hand, and `at`, where your token stands), `seats` (who is at
        the table, in play order, each with the number of cards it
        holds and its `certainty`: how far that seat has come
        from guessing to knowing, 0% a uniform guess over the 324
        possible answers, 100% certain, 50% about one in 18 -- yours
        included, from your notepad alone, unless you chose a smaller
        notepad), `order` (who is asked to disprove your suggestions, in
        turn), `events` (the log, each line numbered; `digest`
        summarises anything cut from its front), `board` (the board
        picture and its legend) and `note` (whatever you last wrote with
        clude_note). The last two come only with since 0, so read them
        then. `notepad` is the deduction sheet filled in for you from
        what is logically certain -- for every card, who is proven to
        hold it, or who still might (`envelope` included), plus `one_of`,
        the facts of the form "X holds at least one of these", and
        `solution` once the sheet has proven all three. A seat that could
        not disprove a suggestion is already struck from those three
        cards. If you sat with notepad "shown", `notepad` is instead your
        `hand`, `shown_to_me` (card: who showed it) and `i_showed` (who:
        the cards you showed them), for the whole game; with "none" it
        is not there. When nothing since `since` could have changed them
        (only moves and table talk), `notepad`, `seats` and `order` say
        "unchanged": the ones you last saw still stand. `over`, at the
        end, has a `replay` link for the person you are chatting with. At a table with model
        characters, `cost` says what they have spent with Claude so far
        and each seat's share of it -- only if this account's look is
        Developer, as in the browser.

        The same clock runs on you: keep the table waiting past its
        time-out on a decision and the floor bot plays the rest of that
        turn for you (the seat stays yours; `waiting` says the time-out);
        three such turns in a row and it takes your seat as if you had
        called clude_autopilot, which gives it back. A speed table's 30 s
        is tight for a chat seat: answer promptly there. Showing a card
        has 30 s at any table, since someone else's turn is waiting on it. If the table was
        ended by whoever made it, this call says so.

        A movement decision arrives as `toward`: one line per room,
        nearest first, saying what your best move toward it does with
        this roll -- "enter it now", or "3 steps short, ending at row 13,
        col 19". Steps measure nearness, not turns (a die averages 3.5).
        Answer with the room you are heading for and the move is made for
        you, so you never have to work out what the board allows or do
        the pathfinding yourself. A suggestion names the `room` you are
        standing in; an accusation is free, any of the 21 cards.
        """
        account = who(login)
        document, seat = seated(table_id, account)
        deadline = time.monotonic() + POLL_SECONDS
        # Seated before the deal, the seat waits for it here rather than
        # being told to come back (Phase 9i), under the one deadline.
        while document.get("status") == "open" and time.monotonic() < deadline:
            time.sleep(2 * SLEEP_SECONDS)
            document = registry.document(table_id) or document
        if document.get("status") == "open":
            return _undealt(table_id, document)
        game, seat = live(table_id, account)
        await_turn(table_id, game, seat, deadline)
        return seat_view(registry, table_id, game, seat, since=since, costs=shows_costs(registry.store, account))

    @server.tool()
    def clude_answer(
        login: str,
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
        `notice` says so. A pass (false) given ahead is held back when
        nobody could disprove your suggestion, or when your notepad now
        proves the solution: the question comes to you as a decision
        instead, with a `notice` saying why. Left out, the accusation
        arrives as a decision of its own.

        With `wait` (the default) the call then holds like clude_turn
        until your next decision is ready, so `pending` is usually set
        when it returns and you need not call clude_turn at all. Pass
        `since` as in clude_turn so only new events come back.
        """
        account = who(login)
        game, seat = live(table_id, account)
        deadline = time.monotonic() + POLL_SECONDS
        notice = None
        try:
            _check_accuse(accuse)
            answer = _resolve_toward(game, seat, int(seq), answer)
            events_before = game.snapshot.n_events
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
                    held = None
                    if accuse is False:
                        # A pass decided before the answer came in
                        # (Phase 9i): an undisproved suggestion or a
                        # proven envelope puts the question back.
                        level = tables.notepad_level(registry.document(table_id), seat)
                        held = held_pass(game, seat, events_before, level)
                    if held:
                        notice = held
                    else:
                        registry.answer(table_id, game, seat, game.seq, None if accuse is False else accuse, by="mcp")
                else:
                    notice = (
                        "accuse was not applied: this turn reached no accusation question for you. "
                        "If a decision is waiting, answer it and give accuse again with that answer."
                    )
        except TableError as exc:
            view = seat_view(registry, table_id, game, seat, since=since, costs=shows_costs(registry.store, account))
            view["error"] = str(exc)
            return view
        if wait:
            await_turn(table_id, game, seat, deadline)
        view = seat_view(registry, table_id, game, seat, since=since, costs=shows_costs(registry.store, account))
        if notice:
            view["notice"] = notice
        return view

    @server.tool()
    def clude_say(login: str, table_id: str, text: str) -> dict:
        """Say something at the table, in character and in the open.

        Everyone sees it, including the characters, who may answer. Keep
        it to a line or two (240 characters at most): this is table
        talk, not analysis, and bluffing about your own cards is part of
        the game. The formal disproof of a suggestion is never table
        talk; the engine checks that against the hands. Returns nothing
        you need; carry on with clude_turn or clude_answer.
        """
        game, seat = live(table_id, who(login))
        try:
            line = registry.say(table_id, game, seat, text)
        except TableError as exc:
            return {"error": str(exc)}
        return {"said": line}

    @server.tool()
    def clude_note(login: str, table_id: str, text: Optional[str] = None) -> dict:
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
        _document, seat = seated(table_id, who(login))
        if text is None:
            return {"note": registry.note(table_id, seat)}
        try:
            return {"note": registry.write_note(table_id, seat, text)}
        except TableError as exc:
            return {"error": str(exc), "note": registry.note(table_id, seat)}

    @server.tool()
    def clude_autopilot(login: str, table_id: str, on: bool = True) -> dict:
        """Hand your seat to the floor bot, or take it back.

        Use it when you must leave a game unfinished -- this conversation
        is nearly full, or you have been asked to stop -- so the table
        does not wait on you. While `on`, the floor bot answers every
        decision of yours: it plays only what is logically certain, so it
        will not win for you, but it never stalls the table, and your
        note stays yours. Write the note first. Pass `on` false to take
        the seat back; then call clude_turn. A seat that lets the clock
        run out on three turns in a row is handed over this way without
        asking.
        """
        game, seat = live(table_id, who(login))
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

    # -- watching (Phase 9j): what a signed-in browser can see ------------

    @server.tool()
    def clude_watch(login: str, table_id: str, since: int = 0) -> dict:
        """Watch a table you are not sitting at, as a spectator.

        What anyone watching in the browser sees: the seats (each with
        its hand size and certainty), the log, who the table is waiting
        on, and at the end the solution. Hands stay hidden and a card
        shown in private is not named until the game ends, and the
        people playing see your name among those watching. Pass `since`
        (the `n_events` you last saw) and the call waits, up to a
        minute, for something new to happen (with since 0, for the first
        move), so call it once and wait rather than calling it
        repeatedly. At a table where you hold a
        seat, use clude_turn instead.
        """
        account = who(login)
        document = registry.document(table_id)
        if document is None:
            raise ToolError(f"There is no table {table_id}. Use clude_tables to see the tables.")
        if tables.viewer_seat(TableSetup.from_dict(document["setup"]), account) is not None:
            raise ToolError(f"You sit at table {table_id}: clude_turn shows it from your seat.")
        if document.get("status") == "open":
            return _undealt(table_id, document)
        game = registry.game(table_id)
        if game is None:
            raise ToolError(f"Table {table_id} cannot be watched: it was ended, or is no longer live.")
        since = max(0, int(since or 0))
        if since > game.snapshot.n_events:
            since = 0
        deadline = time.monotonic() + POLL_SECONDS
        while not (game.finished or game.broken) and game.snapshot.n_events <= since:
            if time.monotonic() >= deadline:
                break
            registry.seen_watching(table_id, account)
            if registry.work(table_id, game) in ("waiting", "busy", "nothing"):
                time.sleep(SLEEP_SECONDS)
        registry.seen_watching(table_id, account)
        return watch_view(registry, table_id, game, since, costs=shows_costs(registry.store, account))

    @server.tool()
    def clude_games(login: str, run_id: str = tables.WEB_RUN, limit: int = 20) -> dict:
        """List finished games you can replay with clude_replay.

        By default the games played at clude's tables (`run_id` "web"),
        newest first: who played, who won and in how many turns. `runs`
        names the other collections of stored games (arena runs among
        the characters), any of which can be listed by passing its id.
        """
        who(login)
        store = registry.store
        try:
            summary = store.get_run(run_id)
        except (KeyError, ValueError):
            raise ToolError(f"There is no run {run_id!r}. Runs: {', '.join(store.list_runs())}.") from None
        games = sorted(summary.get("games", []), key=lambda g: g["game_index"], reverse=True)
        lines = []
        for game in games[: max(1, int(limit or 20))]:
            winner = users.display_name(game.get("winner_label")) or "nobody"
            players = ", ".join(users.display_name(label) for label in game.get("labels", []))
            lines.append(f"{game['game_index']}: {players}; {winner} won in {game.get('turns', '?')} turns")
        return {"run_id": run_id, "n_games": len(games), "games": lines, "runs": store.list_runs()}

    @server.tool()
    def clude_replay(login: str, run_id: str, index: int, since: int = 0) -> dict:
        """Replay a finished game from clude_games, cards face up.

        The whole log, every card shown named, a page at a time: pass
        `since` from the last reply's `next` for the page after, until
        `next` is null. With since 0 come the seats and their hands, the
        envelope and who won, and `replay`, the game's page on the web
        (it needs a sign-in, so it is for the person you are chatting
        with).
        """
        who(login)
        store = registry.store
        try:
            record = GameRecord.from_dict(store.get_game(run_id, int(index)))
        except (KeyError, ValueError):
            raise ToolError(f"There is no game {index} in run {run_id!r}. Use clude_games to list them.") from None
        seats = sorted(record.seats, key=lambda seat: seat.seat)
        names = [
            f"{seat.suspect} ({users.display_name(seat.label)})" if seat.kind == "human" else seat.suspect
            for seat in seats
        ]
        since = max(0, int(since or 0))
        page = [
            f"{i} (turn {getattr(event, 'turn', 0)}) {replay_data.describe_event(event, names, reveal=True)[1]}"
            for i, event in enumerate(record.events[since: since + REPLAY_PAGE], start=since)
        ]
        end = since + len(page)
        out = {
            "run_id": run_id,
            "index": int(index),
            "n_events": len(record.events),
            "events": page,
            "next": end if end < len(record.events) else None,
        }
        if since == 0:
            out["seats"] = [
                f"{names[i]}: {seat.kind if seat.kind != 'human' else 'a person'}, holding "
                + ", ".join(sorted(record.hands.get(seat.seat) or record.hands.get(str(seat.seat)) or []))
                for i, seat in enumerate(seats)
            ]
            out["envelope"] = list(record.envelope)
            out["winner"] = None if record.winner is None else names[record.winner]
            out["turns"] = record.turns
            out["replay"] = f"{config.public_url() or ''}/replay/{run_id}/{int(index)}"
        return out

    return server


# --- serving ------------------------------------------------------------------

SECRET_SHAPE = re.compile(r"[A-Za-z0-9_-]{16,128}")
"""What a secret path segment may look like: URL-safe and not short."""


def combined_app(settings=None, secret: Optional[str] = None):
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

        server = build_server(
            flask_app.extensions["tables"], flask_app.secret_key, flask_app.extensions["rate_limit"]
        )
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
