"""Tables: games played on the web, with people, characters and floor
bots in any mix of seats (Phase 8.2, docs/phase8-plan.md 3.2).

`clude_training.table.TableGame` is the driver; this module is what the
web app puts around it. A `TableRegistry` keeps the live games in memory
as a cache and the truth in the store, one document per table under
``tables/``: the setup, the ordered entry log, the turn count, the
status (``open`` while seats wait for people, ``playing``, ``finished``)
and who sits where. A game missing from memory -- a restarted process, a
fresh Cloud Run instance -- is rebuilt from its document by replaying
its entries, single-flight, so two polls arriving together do not both
replay it (`docs/architecture.md`, "Resumable").

**Who drives the game.** Nothing here runs between requests: the
service is billed per request and has CPU only while one is in flight,
so bot turns happen inside `work`, which any client calls when its poll
says work is due. The game lock is taken without blocking there, so the
first caller is the worker and the rest come straight back; `poll` never
takes the lock at all, reading the driver's published snapshot, so six
browsers polling never queue behind a slow turn.

**What each viewer sees.** `view_payload` describes the game from one
seat: the card shown at a refutation is named only to the two seats
involved (`ClueObservation.for_player`'s rule) and never to a spectator;
a seated person also gets their hand, the deduction floor's notepad from
their own view and, when the game is stopped on them, the decision as
data in the shape `decode_answer` takes back. Watch's compact readings
of every seat are shown to everyone (David, 2026-09-18).

Nothing here spends money: an LLM seat on the web is Phase 8.3.
"""
from __future__ import annotations

import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import clude_constraints
from clude_agents import AGENT_SPECS, build_agent
from clude_agents.bandit import RevealedOutcome
from clude_core import engine
from clude_core.domain import ALL_CARDS, ROOMS, SUSPECTS, WEAPONS
from clude_core.events import GameOverEvent, SuggestionEvent
from clude_storage import GameRecord, Logbook, SeatRecord
from clude_training import memory as method_memory
from clude_training.table import (
    MAX_TURNS,
    SeatSpec,
    TableError,
    TableGame,
    TableSetup,
)

from . import board_svg, replay_data

TABLES_PREFIX = "tables"
"""Store folder holding one document per table."""

WEB_RUN = "web"
"""The run every game played through the web app is saved under, so it
shows in the lobby beside the arena's runs and opens as a replay."""

DOCUMENT_VERSION = 2
"""1 was Watch's ``watch/<id>`` document (setup and a turn count); 2 is
a table: seats, an entry log, a status and the memory snapshot."""

WORK_INTERVAL = 1.5
"""Seconds between two bot turns played by `work`: the table's beat, so
a run of bot turns reads at a human pace rather than as one lump."""

AUTOPILOT_AFTER = 600.0
"""Seconds a seat may keep the table waiting before anyone seated may
hand it to the stand-in."""

CATEGORIES = (("suspects", SUSPECTS), ("weapons", WEAPONS), ("rooms", ROOMS))

_SAVE_LOCK = threading.Lock()
"""Serialises picking the next game index in the web run, and the
method-memory updates at a finish. One instance (`--max-instances 1`)
with a few threads, so a process lock is enough."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def table_key(table_id: str) -> str:
    return f"{TABLES_PREFIX}/{table_id}.json"


# --- the form -------------------------------------------------------------


def parse_table_form(form, me: str) -> TableSetup:
    """A `TableSetup` from the lobby's table form: one select per token
    named ``seat-<Token>`` reading *empty*, *me*, *character*, *floor* or
    *open*, an optional seed, and *remember*.

    Parameters
    ----------
    form : Mapping
        The request form.
    me : str
        The account key of the person submitting it: the label of the
        seat they take.

    Raises
    ------
    ValueError
        With a message fit to show on the form.
    """
    seats = []
    mine = 0
    for token in SUSPECTS:
        value = (form.get(f"seat-{token}") or "empty").strip().lower()
        if value == "empty":
            continue
        if value == "me":
            seats.append(SeatSpec(token, "human", me))
            mine += 1
        elif value == "character":
            seats.append(SeatSpec(token, "character", token))
        elif value == "floor":
            seats.append(SeatSpec(token, "floor"))
        elif value == "open":
            seats.append(SeatSpec(token, "open"))
        else:
            raise ValueError(f"{token}'s seat has an unknown occupant.")
    if mine > 1:
        raise ValueError("You can only sit in one seat.")
    if not seats:
        raise ValueError("Pick who sits at the table.")
    if not engine.MIN_PLAYERS <= len(seats) <= engine.MAX_PLAYERS:
        raise ValueError(
            f"A table seats {engine.MIN_PLAYERS} to {engine.MAX_PLAYERS}; "
            f"{len(seats)} {'is' if len(seats) == 1 else 'are'} taken."
        )
    raw_seed = (form.get("seed") or "").strip()
    if raw_seed:
        try:
            seed = int(raw_seed)
        except ValueError:
            raise ValueError("The seed must be a whole number, or left blank.") from None
    else:
        seed = secrets.randbelow(1_000_000)
    remember = (form.get("remember") or "").strip().lower() in ("1", "on", "true", "yes")
    try:
        return TableSetup(tuple(seats), seed, MAX_TURNS, remember)
    except ValueError as exc:
        raise ValueError(str(exc)) from None


# --- the game with what the screens ask of it ----------------------------


class WebGame(TableGame):
    """A `TableGame` plus the readings the screens ask for: Watch's
    compact bar per seat, this turn's lines and the last suggestion.
    `advance` is Watch's name for `run`."""

    def __init__(self, setup: TableSetup, prepare=None) -> None:
        super().__init__(setup, prepare)
        self._readings_at = -1
        self._readings: list = []

    advance = TableGame.run

    def turn_lines(self) -> list:
        """``(kind, text)`` for every event of the most recent turn, with
        the card shown at any refutation kept private."""
        suspects = self.suspects
        return [
            replay_data.describe_event(event, suspects, reveal=False)
            for event in self.turn_events()
            if not isinstance(event, GameOverEvent)
        ]

    def last_suggestion(self):
        """The most recent suggestion as a private line, or None -- what
        Direction D has "spoken" under the board."""
        log = self.state.suggestion_log
        if not log:
            return None
        return replay_data.suggestion_line(log[-1], self.suspects, reveal=False)

    def readings(self) -> list:
        """Each seat's compact bar: cards placed, and per category how
        many are placed, whether the answer is proven, and how sure the
        seat's own method is. Names no card.

        Beliefs come from a fresh agent per reading, reset with the game
        seed -- never from the agent actually playing, whose RNG a
        reading would disturb and so change the rest of the game. That
        makes a reading a pure function of the seat, the seed and its
        view, so a rebuilt game reads exactly as the live one did; it is
        cached per event-log length because a fresh Plum reading is most
        of a second. A human seat's bar shows what its floor has placed
        and no confidence.
        """
        n_events = len(self.events)
        if n_events == self._readings_at:
            return self._readings
        out = []
        for seat, label in enumerate(self.table.labels):
            obs = clude_constraints.observe(self.state, seat)
            probabilities = {}
            if label in AGENT_SPECS:
                reader = build_agent(label)
                reader.reset(self.setup.seed)
                probabilities = reader.select_action(obs).probabilities
            groups = []
            placed = 0
            for name, cards in CATEGORIES:
                holders = [obs.mask.holder_of(card) for card in cards]
                known = sum(1 for h in holders if h is not None)
                placed += known
                groups.append(
                    {
                        "name": name,
                        "size": len(cards),
                        "placed": known,
                        "solved": any(h == clude_constraints.ENVELOPE for h in holders),
                        "confidence": (
                            max(probabilities.get(card, 0.0) for card in cards)
                            if probabilities
                            else None
                        ),
                    }
                )
            out.append(
                {
                    "seat": seat,
                    "suspect": self.table.suspects[seat],
                    "label": label,
                    "method": replay_data.seat_method(label),
                    "active": bool(self.state.active[seat]),
                    "placed": placed,
                    "total": len(ALL_CARDS),
                    "groups": groups,
                }
            )
        self._readings_at, self._readings = n_events, out
        return out


# --- describing the game to one viewer -------------------------------------


def seat_names(game) -> list:
    """What each seat is called on a table screen: the token, and for a
    person their name after it, since a human plays a token that is not
    their own name."""
    names = []
    for seat, token in enumerate(game.suspects):
        if game.kinds[seat] == "human":
            names.append(f"{token} ({game.labels[seat]})")
        else:
            names.append(token)
    return names


def describe_for(event, game, names: list, viewer: Optional[int]) -> tuple:
    """`replay_data.describe_event` from one seat's point of view: the
    card shown at a refutation is named only to the suggester and the
    refuter, never to a spectator; and a person whose token a suggestion
    dragged into a room is told they may stay and suggest there, since
    the drag has no event of its own."""
    reveal = False
    note = ""
    if isinstance(event, SuggestionEvent):
        s = event.suggestion
        reveal = viewer is not None and viewer in (s.suggester, s.refuter)
        if viewer is not None and s.suggester != viewer and game.suspects[viewer] == s.suspect:
            note = f" Your token was called to the {s.room}; on your turn you may stay and suggest there."
    kind, text = replay_data.describe_event(event, names, reveal=reveal)
    return kind, text + note


def notepad(game, viewer: int) -> list:
    """The deduction floor from `viewer`'s seat: for every card, who is
    proven to hold it (a seat index, ``"envelope"``, or None) and which
    holders are still possible. The auto-filled detective sheet every
    cludebot gets, so the person gets it too."""
    obs = clude_constraints.observe(game.state, viewer)
    rows = []
    for category, cards in CATEGORIES:
        for card in cards:
            holder = obs.mask.holder_of(card)
            possible = [seat for seat in range(game.setup.n_players) if obs.mask.is_possible(card, seat)]
            rows.append(
                {
                    "card": card,
                    "category": category,
                    "holder": holder,
                    "possible": possible,
                    "envelope": obs.mask.is_possible(card, clude_constraints.ENVELOPE),
                }
            )
    return rows


def viewer_seat(setup: TableSetup, me: Optional[str]) -> Optional[int]:
    """The seat `me` (an account key) holds at this table, or None."""
    if not me:
        return None
    for seat, spec in enumerate(setup.seats):
        if spec.kind == "human" and spec.label == me:
            return seat
    return None


def view_payload(
    game: WebGame,
    document: dict,
    viewer: Optional[int],
    since: int = 0,
    replay_url: Optional[str] = None,
    waiting_for: float = 0.0,
) -> dict:
    """Everything the table screen needs, from `viewer`'s seat, as one
    JSON-ready object: the seats, the tokens' points on the board, the
    event lines since `since`, the decision if it is the viewer's,
    what the game is waiting on otherwise, the viewer's hand and
    notepad, every seat's compact reading, and the ending.

    Reads the driver's snapshot and never its lock, so a poll comes back
    while a turn is being played; the lines are cut at the snapshot's
    event count so a half-appended turn is never described.
    """
    snap = game.snapshot
    names = seat_names(game)
    autopilot = document.get("autopilot") or {}
    seats = [
        {
            "seat": seat,
            "token": token,
            "label": game.labels[seat],
            "name": names[seat],
            "kind": game.kinds[seat],
            "active": bool(snap.active[seat]),
            "autopilot": bool(autopilot.get(str(seat))),
            "me": seat == viewer,
        }
        for seat, token in enumerate(game.suspects)
    ]
    points = board_svg.token_points({game.suspects[seat]: node for seat, node in snap.positions.items()})
    events = [
        {"i": index, "turn": getattr(event, "turn", 0), "kind": kind, "text": text}
        for index, event in enumerate(game.events[:snap.n_events])
        if index >= since
        for kind, text in [describe_for(event, game, names, viewer)]
    ]

    pending = None
    waiting = None
    if snap.pending is not None:
        request = snap.pending
        who = request["seat"]
        if who == viewer:
            pending = dict(request)
            pending["seq"] = snap.seq
            if request["kind"] == "movement":
                pending["options"] = [
                    dict(option, x=x, y=y)
                    for option in request["options"]
                    for x, y in [board_svg.node_centre(_node_of(option["to"]))]
                ]
            if request.get("shown_to") is not None:
                pending["shown_to_name"] = names[request["shown_to"]]
        waiting = {
            "seat": who,
            "name": names[who],
            "kind": request["kind"],
            "seconds": round(waiting_for, 1),
            "autopilot": bool(autopilot.get(str(who))),
        }

    me = None
    pad = None
    if viewer is not None:
        me = {
            "seat": viewer,
            "token": game.suspects[viewer],
            "hand": sorted(game.state.hands[viewer]),
            "active": bool(snap.active[viewer]),
            "autopilot": bool(autopilot.get(str(viewer))),
        }
        pad = notepad(game, viewer)

    over = None
    if snap.finished and game.events and isinstance(game.events[-1], GameOverEvent):
        final = game.events[-1]
        over = {
            "winner": None if final.winner is None else names[final.winner],
            "envelope": list(final.solution),
            "replay": replay_url,
        }

    return {
        "id": document.get("id"),
        "status": "finished" if snap.finished else "playing",
        "turns": snap.turns,
        "finished": snap.finished,
        "broken": snap.broken,
        "seq": snap.seq,
        "n_events": snap.n_events,
        "seats": seats,
        "tokens": {token: [round(x, 1), round(y, 1)] for token, (x, y) in points.items()},
        "events": events,
        "pending": pending,
        "waiting": waiting,
        "work": (not snap.finished) and snap.pending is None and not snap.broken,
        "offer_autopilot": (
            waiting is not None and not waiting["autopilot"] and waiting_for >= AUTOPILOT_AFTER
        ),
        "me": me,
        "notepad": pad,
        "readings": game.readings(),
        "over": over,
        "remember": game.setup.remember,
    }


def _node_of(data):
    from clude_storage.records import node_from_json

    return node_from_json(data)


# --- the registry -----------------------------------------------------------


class TableRegistry:
    """The tables: live games in memory, their documents in the store.

    In memory is a cache, not the truth. Every change is written through
    to the store, and a game missing from memory is rebuilt from its
    document by replaying its entries (`WebGame.rebuild`), single-flight.
    """

    def __init__(self, store) -> None:
        self.store = store
        self._games: dict = {}
        self._lock = threading.Lock()
        self._building: dict = {}
        self._last_work: dict = {}
        self._pending_since: dict = {}

    # -- documents -----------------------------------------------------

    def document(self, table_id: str):
        """The stored document, or None for an unknown or malformed id."""
        try:
            return self.store.get_doc(table_key(table_id))
        except (KeyError, ValueError):
            return None

    def _put(self, document: dict) -> dict:
        document["updated"] = _now()
        self.store.put_doc(table_key(document["id"]), document)
        return document

    def create(self, setup, started_by: Optional[str]) -> str:
        """A new table. Deals at once when no seat is open; otherwise the
        table waits in the lobby for people to sit (`sit`, `deal`).
        `setup` may be a Watch setup (anything with `to_table_setup`)."""
        if hasattr(setup, "to_table_setup"):
            setup = setup.to_table_setup()
        table_id = secrets.token_hex(5)
        document = {
            "version": DOCUMENT_VERSION,
            "id": table_id,
            "setup": setup.to_dict(),
            "entries": [],
            "turns": 0,
            "status": "open" if setup.open_seats else "playing",
            "autopilot": {},
            "started_by": started_by,
            "created": _now(),
            "updated": _now(),
            "finished": False,
            "record": None,
            "memory": None,
        }
        if not setup.open_seats:
            self._deal(document, setup)
        self._put(document)
        return table_id

    def _deal(self, document: dict, setup: TableSetup) -> WebGame:
        """Build the game for a table whose seats are all filled, taking
        the memory snapshot first so a rebuild loads the same memory."""
        document["setup"] = setup.to_dict()
        document["memory"] = self._snapshot(setup) if setup.remember else None
        document["status"] = "playing"
        game = WebGame(setup, self._prepare(setup, document["memory"]))
        with self._lock:
            self._games[document["id"]] = game
        self._pending_since[document["id"]] = time.monotonic()
        return game

    # -- memory --------------------------------------------------------

    def _snapshot(self, setup: TableSetup) -> dict:
        out = {}
        for spec in setup.seats:
            if spec.kind == "character":
                snap = method_memory.snapshot(Logbook(self.store, spec.label), spec.label)
                if snap is not None:
                    out[spec.label] = snap
        return out

    def _prepare(self, setup: TableSetup, snapshot: Optional[dict]):
        if not setup.remember or not snapshot:
            return None

        def prepare(table) -> None:
            for seat, label in enumerate(table.labels):
                if table.kinds[seat] == "character" and label in snapshot:
                    method_memory.load_snapshot(table.players[seat], Logbook(self.store, label), snapshot[label])

        return prepare

    def _remember(self, game: WebGame, record: GameRecord) -> None:
        """After a finished game with "characters remember" on: fold the
        game into Mustard's and White's memory and save Green's arms.

        Green's document is his live posteriors, overwritten wholesale,
        and two tables can finish in either order, so his arms are first
        reloaded from the latest document and only then shown this game's
        outcome (`observe`, as the arena does) and saved. Under the save
        lock, so two finishes cannot interleave.
        """
        for seat, label in enumerate(game.labels):
            if game.kinds[seat] != "character" or method_memory.kind_for(label) is None:
                continue
            character = game.table.players[seat]
            logbook = Logbook(self.store, label)
            if method_memory.kind_for(label) == "state":
                method_memory.load_into(character, logbook)
                character.observe(RevealedOutcome(envelope=game.state.envelope))
            method_memory.update(logbook, record, character)

    # -- live games ----------------------------------------------------

    def game(self, table_id: str) -> Optional[WebGame]:
        """The live game, rebuilt from the store if it is not in memory,
        single-flight. None for an unknown id or a table not yet dealt."""
        with self._lock:
            cached = self._games.get(table_id)
            if cached is not None:
                return cached
            event = self._building.get(table_id)
            builder = event is None
            if builder:
                event = self._building[table_id] = threading.Event()
        if not builder:
            event.wait(300)
            with self._lock:
                return self._games.get(table_id)
        try:
            document = self.document(table_id)
            if document is None or document.get("status") == "open":
                return None
            setup = TableSetup.from_dict(document["setup"])
            game = WebGame.rebuild(
                setup,
                list(document.get("entries", [])),
                int(document.get("turns", 0)),
                self._prepare(setup, document.get("memory")),
            )
            with self._lock:
                self._games.setdefault(table_id, game)
                game = self._games[table_id]
            self._pending_since.setdefault(table_id, time.monotonic())
            return game
        finally:
            event.set()
            with self._lock:
                self._building.pop(table_id, None)

    def save(self, table_id: str, game: TableGame, record_ref=None) -> dict:
        """Write the game's entries and turn count through, if they moved
        since the document was written (a put is a round trip on GCS)."""
        document = self.document(table_id) or {"id": table_id, "version": DOCUMENT_VERSION}
        changed = (
            record_ref is not None
            or document.get("turns") != game.turns
            or len(document.get("entries", [])) != len(game.entries)
            or document.get("finished") != game.finished
            or document.get("setup") != game.setup.to_dict()
        )
        if not changed:
            return document
        document.update(
            {
                "setup": game.setup.to_dict(),
                "entries": list(game.entries),
                "turns": game.turns,
                "finished": game.finished,
                "status": "finished" if game.finished else "playing",
            }
        )
        if record_ref is not None:
            document["record"] = record_ref
        return self._put(document)

    def waiting_for(self, table_id: str, game: TableGame) -> float:
        """Seconds the game has been stopped on its pending request."""
        if game.pending is None:
            return 0.0
        return max(0.0, time.monotonic() - self._pending_since.get(table_id, time.monotonic()))

    def _moved(self, table_id: str) -> None:
        self._pending_since[table_id] = time.monotonic()

    # -- driving -------------------------------------------------------

    def work(self, table_id: str, game: WebGame) -> str:
        """One unit of bot work, if any is due: a bot turn no sooner than
        `WORK_INTERVAL` after the last, or the stand-in's answers for a
        seat on autopilot -- and, after a turn that stops on such a seat,
        those answers too, so a seat handed to the stand-in never shows
        the person a decision. Never waits for the lock. Returns what
        happened: ``"busy"``, ``"waiting"``, ``"turn"``, ``"autopilot"``,
        ``"finished"`` or ``"nothing"``."""
        if not game.lock.acquire(blocking=False):
            return "busy"
        try:
            if game.finished or game.broken:
                return "finished" if game.finished else "nothing"
            document = self.document(table_id) or {}
            autopilot = document.get("autopilot") or {}

            def stand_in_plays() -> bool:
                played = False
                while (
                    game.pending is not None
                    and autopilot.get(str(game.pending.seat))
                    and not game.finished
                ):
                    game.autopilot()
                    played = True
                return played

            did = "nothing"
            if game.pending is not None:
                did = "autopilot" if stand_in_plays() else "waiting"
            else:
                now = time.monotonic()
                if now - self._last_work.get(table_id, 0.0) < WORK_INTERVAL:
                    did = "waiting"
                else:
                    game.run(1)
                    self._last_work[table_id] = now
                    did = "turn"
                    stand_in_plays()
            if did in ("turn", "autopilot"):
                self._moved(table_id)
                self.save(table_id, game)
                if game.finished:
                    self.finish(table_id, game)
            return did
        finally:
            game.lock.release()

    def answer(self, table_id: str, game: WebGame, seat: int, seq: int, data) -> None:
        """One seat's decision, sent in under the lock; a `TableError`
        leaves the game as it was."""
        with game.lock:
            game.answer(seat, seq, data)
            self._moved(table_id)
            self.save(table_id, game)
            if game.finished:
                self.finish(table_id, game)

    def set_autopilot(self, table_id: str, game: WebGame, seat: int, on: bool) -> dict:
        """Hand `seat` to the stand-in, or take it back. With it on and
        the game stopped on that seat, the stand-in answers at once."""
        document = self.document(table_id)
        if document is None:
            raise TableError("no such table")
        flags = document.setdefault("autopilot", {})
        flags[str(seat)] = bool(on)
        self._put(document)
        if on:
            with game.lock:
                if game.pending is not None and game.pending.seat == seat and not game.finished:
                    game.autopilot()
                    self._moved(table_id)
                    self.save(table_id, game)
                    if game.finished:
                        self.finish(table_id, game)
        return document

    # -- seats before the deal -----------------------------------------

    def sit(self, table_id: str, me: str, token: str) -> dict:
        """Take an open seat at a table waiting for people."""
        document = self.document(table_id)
        if document is None or document.get("status") != "open":
            raise TableError("that table is not waiting for players")
        setup = TableSetup.from_dict(document["setup"])
        if viewer_seat(setup, me) is not None:
            raise TableError("you are already sitting at this table")
        for seat, spec in enumerate(setup.seats):
            if spec.token == token:
                if spec.kind != "open":
                    raise TableError(f"{token}'s seat is taken")
                setup = setup.with_seat(seat, SeatSpec(token, "human", me))
                break
        else:
            raise TableError(f"there is no {token} seat at this table")
        document["setup"] = setup.to_dict()
        return self._put(document)

    def leave(self, table_id: str, me: str) -> dict:
        """Give up a seat at a table not yet dealt."""
        document = self.document(table_id)
        if document is None or document.get("status") != "open":
            raise TableError("that table is not waiting for players")
        setup = TableSetup.from_dict(document["setup"])
        seat = viewer_seat(setup, me)
        if seat is None:
            raise TableError("you are not sitting at this table")
        setup = setup.with_seat(seat, SeatSpec(setup.seats[seat].token, "open"))
        document["setup"] = setup.to_dict()
        return self._put(document)

    def deal(self, table_id: str) -> WebGame:
        """Deal a waiting table: open seats still empty go to floor bots."""
        document = self.document(table_id)
        if document is None:
            raise TableError("no such table")
        if document.get("status") != "open":
            game = self.game(table_id)
            if game is None:
                raise TableError("that table cannot be dealt")
            return game
        setup = TableSetup.from_dict(document["setup"]).dealt()
        game = self._deal(document, setup)
        self._put(document)
        return game

    # -- listing ---------------------------------------------------------

    def in_progress(self) -> list:
        """Every unfinished table's document, newest first."""
        documents = []
        for key in self.store.list_docs(TABLES_PREFIX):
            document = self.document(key)
            if document is not None and document.get("status") != "finished":
                documents.append(document)
        return sorted(documents, key=lambda d: d.get("created", ""), reverse=True)

    # -- the end -----------------------------------------------------------

    def record(self, game: WebGame, run_id: str, game_index: int) -> GameRecord:
        """The finished game as an ordinary record: a human seat is
        recorded under the person's account key with ``kind="human"``,
        the identity every logbook keys on."""
        if not game.finished:
            raise ValueError("a game in progress has no record yet")
        seats = []
        for seat, label in enumerate(game.labels):
            kind = game.kinds[seat]
            player = game.table.players.get(seat)
            profile = getattr(player, "profile", None)
            seats.append(
                SeatRecord(
                    seat=seat,
                    suspect=game.suspects[seat],
                    label=label,
                    kind=kind,
                    profile=profile.to_dict() if profile is not None else None,
                )
            )
        return GameRecord.from_game(
            run_id=run_id,
            game_index=game_index,
            seed=game.setup.seed,
            state=game.state,
            events=game.events,
            seats=seats,
        )

    def finish(self, table_id: str, game: WebGame) -> dict:
        """Save a finished game into the web run, once, and let the
        characters remember it if the table asked. Returns
        ``{"run_id", "index"}``; a second call returns the first's."""
        document = self.document(table_id) or {}
        if document.get("record"):
            return document["record"]
        with _SAVE_LOCK:
            document = self.document(table_id) or {}
            if document.get("record"):
                return document["record"]
            index = max(self.store.list_games(WEB_RUN), default=-1) + 1
            record = self.record(game, WEB_RUN, index)
            self.store.put_game(WEB_RUN, index, record.to_dict())
            add_to_web_run(self.store, record, game.setup.max_turns)
            if game.setup.remember:
                self._remember(game, record)
        ref = {"run_id": WEB_RUN, "index": index}
        self.save(table_id, game, record_ref=ref)
        return ref


def add_to_web_run(store, record: GameRecord, max_turns: int) -> None:
    """Append one game to the web run's summary, in the same shape the
    arena writes, so the lobby lists it with no special case."""
    try:
        summary = store.get_run(WEB_RUN)
    except KeyError:
        summary = {
            "run_id": WEB_RUN,
            "seed": None,
            "roster": [],
            "player_counts": [],
            "max_turns": max_turns,
            "per_player": {},
            "games": [],
        }
    labels = [s.label for s in sorted(record.seats, key=lambda s: s.seat)]
    winner = labels[record.winner] if record.winner is not None else None
    summary["games"] = [g for g in summary.get("games", []) if g["game_index"] != record.game_index]
    summary["games"].append(
        {
            "game_index": record.game_index,
            "seed": record.seed,
            "n_players": record.n_players,
            "labels": labels,
            "winner_label": winner,
            "turns": record.turns,
            "n_suggestions": record.n_suggestions,
            "n_accusations": record.n_accusations,
            "hit_cap": record.winner is None and record.turns >= max_turns,
        }
    )
    summary["games"].sort(key=lambda g: g["game_index"])
    summary["n_games"] = len(summary["games"])
    summary["roster"] = sorted({label for g in summary["games"] for label in g["labels"]})
    summary["player_counts"] = sorted({g["n_players"] for g in summary["games"]})
    store.put_run(WEB_RUN, summary)
