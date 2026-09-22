"""Tables with people, LLM characters, silent headless characters and
floorbots in any mix of seats (Phase 8.2, docs/phase8-plan.md 3.2).

New tables remember by default. The registry loads and updates method
memory for Mustard, White and Green in either character mode, and
attaches LLM narrative logbooks at each seat's saved memory depth.

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

**The model at the table (Phase 8.3a).** An ``llm`` seat is the token's
own character piloted by the model from outside the engine: `work`
answers its pending decision through `TableGame.llm_answer`, one call
per request so the screen reads "Plum is thinking" rather than freezing,
and the answer is stored with its audit and the lines it said, so a
rebuild never asks the model again. Every backend is a `MeteredBackend`
over the table's budget and the service's daily cap (`LLMConfig`), and
past either the wrapper's fallback plays the headless character. Without
a key (`LLMConfig` None) the lobby disables LLM seats and nothing
here can spend.

**A chat seat (Phase 9).** `clude_web.mcp` seats a Claude in a chat
window through this same registry: an ordinary account in an ordinary
human seat, answering with ``by="mcp"``. What it adds here is small: a
free-text note per seat on the document, never an entry, so a rebuild
does not see it. It gets the floor's numbers (the notepad) and nothing
more: a chat player is its own head (David, 2026-09-21; the "head" of
the first deploy, a character's numbers beside the seat, is gone).

**A table nobody is playing.** A human seat that keeps the table
waiting `AUTOPILOT_AFTER` seconds is handed to the stand-in by the next
unit of `work`, whoever drives it, and a seat put out by a wrong
accusation is answered by the stand-in from then on (it only shows
cards), so a person who left never stalls a table for good. A table
that should not go on at all is `abandon`ed: by anyone seated, by
whoever started it, or from the CLI (`tables abandon`); it leaves the
lobby and is never recorded. And a table is not dealt while an open
seat waits for its person.
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
from clude_llm.backend import DEFAULT_MODEL
from clude_llm.metered import Ledger, MeteredBackend
from clude_storage import GameRecord, Logbook, SeatRecord
from clude_training import memory as method_memory
from clude_training.table import (
    MAX_TURNS,
    SeatSpec,
    TableError,
    TableGame,
    TableSetup,
)

from . import board_svg, chat, replay_data

from dataclasses import dataclass

MAX_LINE = 240
"""Characters a person may type in one line of chat (Phase 8.3b): it
lives in records for ever and in every later prompt."""

MAX_NOTE = 8000
"""Characters a chat seat may keep in its note (Phase 9): a page of
deductions, kept on the table document and read back every call."""

def clean_line(text) -> str:
    """A person's line fit to keep: control characters out, whitespace
    collapsed, at most `MAX_LINE` characters.

    Raises
    ------
    TableError
        Empty once cleaned, or too long.
    """
    text = "" if text is None else str(text)
    kept = "".join(ch if ch.isprintable() else " " for ch in text)
    line = " ".join(kept.split())
    if not line:
        raise TableError("Say something, or nothing.")
    if len(line) > MAX_LINE:
        raise TableError(f"A line is at most {MAX_LINE} characters; that one is {len(line)}.")
    return line


def anthropic_backend(model: str, key: str):
    """The real backend, built only when a table with model seats is
    dealt or rebuilt, never at app start (the SDK is imported here)."""
    from clude_llm.anthropic_backend import AnthropicBackend  # noqa: PLC0415

    return AnthropicBackend(model, api_key=key)


@dataclass(frozen=True)
class LLMConfig:
    """How the service reaches the model (Phase 8.3a).

    Parameters
    ----------
    key : str
        The workspace-scoped API key.
    model : str
        The model id every table uses; must be priced (`estimate_cost`).
    budget : float
        Dollars a table may spend by default; the lobby form may lower
        or raise it.
    daily_cap : float
        Dollars the whole service may spend in one UTC day.
    make_backend : Callable[[str, str], LLMBackend]
        ``(model, key)`` to the backend one seat calls through; the real
        one by default, a scripted one in tests.
    """

    key: str
    model: str = DEFAULT_MODEL
    budget: float = 2.0
    daily_cap: float = 10.0
    make_backend: object = anthropic_backend

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

AUTOPILOT_AFTER = 180.0
"""Seconds a human seat may keep the table waiting before `work` hands
it to the stand-in (and before anyone seated may do so by hand). Ten
minutes until 2026-09-21; three on David's word."""

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


def remember_from_form(form) -> bool:
    """Read the remembering choice, enabled when no field is supplied.

    Checkbox forms send a trailing hidden ``remember=0`` so unchecking
    explicitly opts out; the checked checkbox's first value is ``1``.
    """
    return str(form.get("remember", "1")).strip().lower() in ("1", "on", "true", "yes")


def parse_table_form(form, me: str, llm: Optional[LLMConfig] = None) -> TableSetup:
    """A `TableSetup` from the lobby's table form: one select per token
    named ``seat-<Token>``. Labels, in order: empty, open, floorbot,
    me (signed-in name), X (LLM), X (headless). Stored form values remain
    ``empty``, ``open``, ``floor``, ``me``, ``llm``, ``character``.
    LLM seats require `llm`; ``memory-<Token>`` sets their logbook depth
    in [0, 1], default 0. Remembering defaults on; ``remember=0`` opts out.
    An optional seed fixes the deal.

    Parameters
    ----------
    form : Mapping
        The request form.
    me : str
        The account key of the person submitting it: the label of the
        seat they take.
    llm : LLMConfig or None
        Whether model seats may be asked for.

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
        elif value == "llm":
            if llm is None:
                raise ValueError("LLM seats are not available here: the service has no key.")
            try:
                memory = float(form.get(f"memory-{token}", "0") or "0")
            except (TypeError, ValueError):
                raise ValueError(f"{token}'s memory must be a number from 0 to 1.") from None
            seats.append(SeatSpec(token, "llm", token, memory=memory))
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
    remember = remember_from_form(form)
    try:
        return TableSetup(tuple(seats), seed, MAX_TURNS, remember)
    except ValueError as exc:
        raise ValueError(str(exc)) from None


def parse_budget(form, llm: Optional[LLMConfig]) -> Optional[float]:
    """The table's model budget from the form's ``budget`` field, in
    dollars: the config's default when blank; None without a config.

    Raises
    ------
    ValueError
        With a message fit to show on the form.
    """
    if llm is None:
        return None
    raw = (form.get("budget") or "").strip().lstrip("$")
    if not raw:
        return float(llm.budget)
    try:
        budget = float(raw)
    except ValueError:
        raise ValueError("The budget must be a number of dollars, or left blank.") from None
    if budget < 0:
        raise ValueError("The budget cannot be negative.")
    return round(budget, 2)


# --- the game with what the screens ask of it ----------------------------


class WebGame(TableGame):
    """A `TableGame` plus the readings the screens ask for: Watch's
    compact bar per seat, this turn's lines and the last suggestion.
    `advance` is Watch's name for `run`."""

    def __init__(self, setup: TableSetup, prepare=None, llm_backend=None) -> None:
        super().__init__(setup, prepare, llm_backend)
        self.table_id: str = ""
        self.reactions = chat.Reactions(self, lambda: seat_names(self))
        self._readings_at = -1
        self._readings: list = []

    advance = TableGame.run

    def fresh_belief(self, seat: int, label: str):
        """What a fresh `label` agent believes from `seat`'s view: built,
        reset with the game seed, shown the seat's observation through
        the floor (`clude_constraints.observe`, the door the engine's own
        bot sees through) and asked once. A pure function of the seat,
        the seed and the view, so a rebuilt game reads exactly as the
        live one did; never the agent actually playing, whose RNG a
        reading would disturb."""
        obs = clude_constraints.observe(self.state, seat)
        reader = build_agent(label)
        reader.reset(self.setup.seed)
        return reader.select_action(obs)

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
                probabilities = self.fresh_belief(seat, label).probabilities
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
        wrapper = game.wrappers.get(who)
        waiting = {
            "seat": who,
            "name": names[who],
            "kind": request["kind"],
            "seconds": round(waiting_for, 1),
            "autopilot": bool(autopilot.get(str(who))),
            "model": game.kinds[who] == "llm",
            "no_model": game.kinds[who] == "llm" and wrapper is None,
            "refused": getattr(getattr(wrapper, "backend", None), "last_refusal", None),
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

    debriefs = None
    if document.get("debriefs"):
        debriefs = {
            "pending": [names[seat] for seat in pending_debriefs(document)],
            "done": [
                names[int(seat)] for seat, state in document["debriefs"].items()
                if (state or {}).get("status") == "done"
            ],
            "failed": [
                names[int(seat)] for seat, state in document["debriefs"].items()
                if (state or {}).get("status") == "failed"
            ],
        }
    wrapping_up = bool(debriefs and debriefs["pending"] and game.wrappers)

    llm = document.get("llm")
    if llm:
        backends = [getattr(w, "backend", None) for w in game.wrappers.values()]
        llm = dict(
            llm,
            spent=round(max([getattr(b, "known_spent", 0.0) for b in backends] + [float(llm.get("spent", 0.0))]), 4),
            refused={
                str(seat): getattr(getattr(w, "backend", None), "last_refusal", None)
                for seat, w in game.wrappers.items()
                if getattr(getattr(w, "backend", None), "last_refusal", None)
            },
        )

    return {
        "id": document.get("id"),
        "llm": llm,
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
        "work": (
            wrapping_up
            or (
                (not snap.finished)
                and not snap.broken
                and (
                    snap.pending is None
                    or bool(waiting and waiting["model"] and not waiting["no_model"])
                    or game.reactions.pending
                )
            )
        ),
        "chatter": game.reactions.pending,
        "debriefs": debriefs,
        "wrapping_up": wrapping_up,
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

    def __init__(self, store, llm: Optional[LLMConfig] = None) -> None:
        self.store = store
        self.llm = llm
        self.ledger = Ledger(store) if llm is not None else None
        self._games: dict = {}
        self._lock = threading.Lock()
        self._building: dict = {}
        self._last_work: dict = {}
        self._pending_since: dict = {}

    def _backend_factory(self, document: dict):
        """``seat -> MeteredBackend`` for a table with model seats, or None
        when this service has no key (its stored answers still replay)."""
        llm = self.llm
        if llm is None or not document.get("llm"):
            return None
        budget = float(document["llm"].get("budget", llm.budget))
        table_id = document["id"]

        def factory(seat: int):
            return MeteredBackend(
                llm.make_backend(llm.model, llm.key), self.ledger, table_id, budget, llm.daily_cap, llm.model
            )

        return factory

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

    def create(self, setup, started_by: Optional[str], budget: Optional[float] = None) -> str:
        """A new table. Deals at once when no seat is open; otherwise the
        table waits in the lobby for people to sit (`sit`, `deal`).
        `setup` may be a Watch setup (anything with `to_table_setup`).
        `budget` is the table's model spend in dollars, for a table with
        ``llm`` seats.

        Raises
        ------
        ValueError
            Model seats asked for on a service with no key.
        """
        if hasattr(setup, "to_table_setup"):
            setup = setup.to_table_setup()
        table_id = secrets.token_hex(5)
        model_seats = [seat for seat, kind in enumerate(setup.kinds) if kind == "llm"]
        if model_seats and self.llm is None:
            raise ValueError("LLM seats are not available here: the service has no key.")
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
            "llm": (
                {"model": self.llm.model, "budget": float(self.llm.budget if budget is None else budget), "spent": 0.0}
                if model_seats
                else None
            ),
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
        game = WebGame(setup, self._prepare(setup, document["memory"]), self._backend_factory(document))
        game.table_id = document["id"]
        with self._lock:
            self._games[document["id"]] = game
        self._pending_since[document["id"]] = time.monotonic()
        return game

    # -- memory --------------------------------------------------------

    def _snapshot(self, setup: TableSetup) -> dict:
        out = {}
        for spec in setup.seats:
            if spec.kind in ("character", "llm"):
                snap = method_memory.snapshot(Logbook(self.store, spec.label), spec.label)
                if snap is not None:
                    out[spec.label] = snap
        return out

    def _prepare(self, setup: TableSetup, snapshot: Optional[dict]):
        """What runs after the players are built and before the deal, with
        "characters remember" on: each character's method memory from the
        snapshot, and for a model seat (Phase 8.3c) its logbook attached,
        so it reads its notes back at the `memory` dial's depth and can
        write an entry at the end."""
        if not setup.remember:
            return None
        snapshot = snapshot or {}

        def prepare(table) -> None:
            for seat, label in enumerate(table.labels):
                kind = table.kinds[seat]
                if kind == "character" and label in snapshot:
                    method_memory.load_snapshot(table.players[seat], Logbook(self.store, label), snapshot[label])
                elif kind == "llm" and seat in table.wrappers:
                    wrapper = table.wrappers[seat]
                    logbook = Logbook(self.store, label)
                    if label in snapshot:
                        method_memory.load_snapshot(wrapper.character, logbook, snapshot[label])
                    wrapper.attach_logbook(logbook)

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
            if game.kinds[seat] not in ("character", "llm") or method_memory.kind_for(label) is None:
                continue
            if game.kinds[seat] == "llm":
                if seat not in game.wrappers:
                    continue
                character = game.wrappers[seat].character
            else:
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
            if document is None or document.get("status") in ("open", "abandoned"):
                return None
            setup = TableSetup.from_dict(document["setup"])
            game = WebGame.rebuild(
                setup,
                list(document.get("entries", [])),
                int(document.get("turns", 0)),
                self._prepare(setup, document.get("memory")),
                self._backend_factory(document),
            )
            game.table_id = table_id
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
        if document.get("llm") and game.wrappers:
            spent = max(getattr(w.backend, "known_spent", 0.0) for w in game.wrappers.values())
            document["llm"]["spent"] = round(max(spent, float(document["llm"].get("spent", 0.0))), 4)
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
        the person a decision. A human seat that is out (a wrong
        accusation) is the stand-in's too, since all it can do is show
        cards; and a human seat that has kept the table waiting
        `AUTOPILOT_AFTER` seconds is handed to the stand-in here, its
        flag set as if its owner had pressed the button, so a person who
        left never stalls a table for good (David, 2026-09-21). Never
        waits for the lock. Returns what
        happened: ``"busy"``, ``"waiting"``, ``"turn"``, ``"autopilot"``,
        ``"model"`` (one decision by a model seat, Phase 8.3a),
        ``"reaction"`` (one off-turn line, 8.3b), ``"debrief"`` (one
        logbook entry after the game, 8.3c), ``"finished"`` or
        ``"nothing"``. A queued reaction is served before anything else,
        and while one waits to be due no bot or model plays, so the
        chatter lands before the next move; a person's own answer is
        never held."""
        if not game.lock.acquire(blocking=False):
            return "busy"
        try:
            if game.finished or game.broken:
                if game.finished and self.debrief_one(table_id, game) is not None:
                    return "debrief"
                return "finished" if game.finished else "nothing"
            document = self.document(table_id) or {}
            autopilot = document.get("autopilot") or {}
            game.reactions.scan()
            reaction = game.reactions.due()
            if reaction is not None:
                said = game.reactions.serve(reaction)
                if said:
                    self.save(table_id, game)
                return "reaction"
            if game.reactions.pending:
                return "waiting"

            def stands_in_for(seat: int) -> bool:
                return bool(autopilot.get(str(seat))) or not game.state.active[seat]

            def stand_in_plays() -> bool:
                played = False
                while game.pending is not None and stands_in_for(game.pending.seat) and not game.finished:
                    game.autopilot()
                    played = True
                return played

            def hand_over_if_stalled() -> bool:
                """A human seat that has kept the table waiting too long
                goes to the stand-in, flag and all."""
                pending = game.pending
                if pending is None or game.kinds[pending.seat] != "human" or stands_in_for(pending.seat):
                    return False
                if self.waiting_for(table_id, game) < AUTOPILOT_AFTER:
                    return False
                autopilot[str(pending.seat)] = True
                document.setdefault("autopilot", {})[str(pending.seat)] = True
                self._put(document)
                return True

            def model_plays() -> bool:
                if game.pending is None or game.kinds[game.pending.seat] != "llm":
                    return False
                if game.pending.seat not in game.wrappers:
                    return False
                game.llm_answer()
                return True

            did = "nothing"
            if game.pending is not None:
                if stand_in_plays():
                    did = "autopilot"
                    if model_plays():
                        did = "model"
                elif model_plays():
                    did = "model"
                    stand_in_plays()
                elif hand_over_if_stalled() and stand_in_plays():
                    did = "autopilot"
                else:
                    did = "waiting"
            else:
                now = time.monotonic()
                if now - self._last_work.get(table_id, 0.0) < WORK_INTERVAL:
                    did = "waiting"
                else:
                    game.run(1)
                    self._last_work[table_id] = now
                    did = "turn"
                    stand_in_plays()
            if did in ("turn", "autopilot", "model"):
                game.reactions.scan()
                self._moved(table_id)
                self.save(table_id, game)
                if game.finished:
                    self.finish(table_id, game)
            return did
        finally:
            game.lock.release()

    def say(self, table_id: str, game: WebGame, seat: int, text) -> str:
        """A seated person's line (Phase 8.3b): cleaned, said at the table
        as a ``chat`` remark every speaker hears, stored as an entry, and
        an opportunity for the model seats to answer. Never read by the
        engine: the formal refutation stays checked against the hands.

        Raises
        ------
        TableError
            An empty or over-long line, or a finished table.
        """
        line = clean_line(text)
        with game.lock:
            if game.finished:
                raise TableError("The game is over.")
            game.remark(seat, line, "chat")
            game.reactions.scan()
            self.save(table_id, game)
        return line

    def answer(self, table_id: str, game: WebGame, seat: int, seq: int, data, by: str = "human") -> None:
        """One seat's decision, sent in under the lock; a `TableError`
        leaves the game as it was. `by` is recorded in the entry: a
        browser answers as ``"human"``, a chat seat as ``"mcp"``."""
        with game.lock:
            game.answer(seat, seq, data, by=by)
            self._moved(table_id)
            self.save(table_id, game)
            if game.finished:
                self.finish(table_id, game)

    def set_autopilot(self, table_id: str, game: WebGame, seat: int, on: bool) -> dict:
        """Hand `seat` to the stand-in, or take it back. With it on and
        the game stopped on that seat, the stand-in answers at once,
        every decision of that seat's until the turn passes on, so the
        seat never shows a decision again until it is taken back."""
        document = self.document(table_id)
        if document is None:
            raise TableError("no such table")
        flags = document.setdefault("autopilot", {})
        flags[str(seat)] = bool(on)
        self._put(document)
        if on:
            with game.lock:
                played = False
                while game.pending is not None and game.pending.seat == seat and not game.finished:
                    game.autopilot()
                    played = True
                if played:
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
                try:
                    setup = setup.with_seat(seat, SeatSpec(token, "human", me))
                except ValueError as exc:
                    raise TableError(str(exc)) from None
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
        """Deal a waiting table. Refused while an open seat is still
        waiting for its person (David, 2026-09-21: a seat marked open is
        reserved for someone, so it never goes to a floor bot by
        default); the table is dealt when every seat is taken."""
        document = self.document(table_id)
        if document is None:
            raise TableError("no such table")
        if document.get("status") != "open":
            game = self.game(table_id)
            if game is None:
                raise TableError("that table cannot be dealt")
            return game
        setup = TableSetup.from_dict(document["setup"])
        if setup.open_seats:
            waiting = ", ".join(setup.seats[seat].token for seat in setup.open_seats)
            raise TableError(f"the table is still waiting for someone to sit as {waiting}")
        setup = setup.dealt()
        game = self._deal(document, setup)
        self._put(document)
        return game

    # -- notes (Phase 9) -------------------------------------------------

    def abandon(self, table_id: str, me: Optional[str] = None) -> dict:
        """End a table for good, whatever its state: it leaves the lobby,
        its live game is dropped, and nothing is recorded. `me` must be
        seated at it or have started it; None is the maintainer (the
        CLI), who may end any table. A finished table is left alone."""
        document = self.document(table_id)
        if document is None:
            raise TableError("no such table")
        if document.get("status") == "abandoned":
            return document
        if document.get("status") == "finished" and not pending_debriefs(document):
            raise TableError("that table is over already")
        if me is not None:
            setup = TableSetup.from_dict(document["setup"])
            if viewer_seat(setup, me) is None and document.get("started_by", "").lower() != me.lower():
                raise TableError("only someone at the table, or whoever started it, can end it")
        document["status"] = "abandoned"
        document["abandoned_by"] = me or "cli"
        document.pop("debriefs", None)
        self._put(document)
        with self._lock:
            self._games.pop(table_id, None)
        self._pending_since.pop(table_id, None)
        return document

    def note(self, table_id: str, seat: int) -> str:
        """The seat's free-text note: what a chat seat wrote itself to
        outlive its conversation. Empty when nothing was written."""
        document = self.document(table_id) or {}
        return str((document.get("notes") or {}).get(str(seat), ""))

    def write_note(self, table_id: str, seat: int, text: str) -> str:
        """Replace the seat's note wholesale, at most `MAX_NOTE`
        characters. Kept on the document and never as an entry, so a
        rebuild does not replay it and the engine never reads it; no
        lock, since it touches no game.

        Raises
        ------
        TableError
            No such table, or a note too long.
        """
        document = self.document(table_id)
        if document is None:
            raise TableError("no such table")
        text = "" if text is None else str(text)
        if len(text) > MAX_NOTE:
            raise TableError(f"A note is at most {MAX_NOTE} characters; that one is {len(text)}.")
        document.setdefault("notes", {})[str(seat)] = text
        self._put(document)
        return text

    # -- listing ---------------------------------------------------------

    def in_progress(self) -> list:
        """Every unfinished table's document, newest first, and every
        finished one still wrapping up (a debrief pending, Phase 8.3c).
        An abandoned table is gone from here."""
        documents = []
        for key in self.store.list_docs(TABLES_PREFIX):
            document = self.document(key)
            if document is None:
                continue
            status = document.get("status")
            if status == "abandoned":
                continue
            if status != "finished" or pending_debriefs(document):
                documents.append(document)
        return sorted(documents, key=lambda d: d.get("created", ""), reverse=True)

    # -- debriefs (Phase 8.3c) ------------------------------------------------

    def _set_debriefs(self, table_id: str, seats: list) -> None:
        document = self.document(table_id)
        if document is None or not seats:
            return
        document["debriefs"] = {str(seat): {"status": "pending"} for seat in seats}
        self._put(document)

    def debrief_one(self, table_id: str, game: WebGame) -> Optional[int]:
        """Write one pending debrief: the seat's wrapper reads the finished
        record face up and adds a logbook entry with its dossiers on
        everyone present, people by their account key (42 s and about
        $0.09 with Claude). Returns the seat served, or None when nothing
        was pending. Marks the document ``done`` with the serial, or
        ``failed`` with the reason."""
        document = self.document(table_id) or {}
        pending = pending_debriefs(document)
        if not pending or not document.get("record"):
            return None
        seat = pending[0]
        wrapper = game.wrappers.get(seat)
        entry_state: dict
        if wrapper is None:
            entry_state = {"status": "failed", "reason": "no model on this server"}
        else:
            ref = document["record"]
            record = GameRecord.from_dict(self.store.get_game(ref["run_id"], ref["index"]))
            entry = wrapper.debrief(record, seat)
            if entry is not None:
                entry_state = {"status": "done", "serial": entry.serial}
            else:
                entry_state = {"status": "failed", "reason": str(wrapper.last_debrief.get("fallback"))}
        document = self.document(table_id) or document
        document.setdefault("debriefs", {})[str(seat)] = entry_state
        self._put(document)
        return seat

    # -- the end -----------------------------------------------------------

    def record(self, game: WebGame, run_id: str, game_index: int) -> GameRecord:
        """The finished game as an ordinary record: a human seat is
        recorded under the person's account key with ``kind="human"``,
        the identity every logbook keys on."""
        if not game.finished:
            raise ValueError("a game in progress has no record yet")
        document = self.document(getattr(game, "table_id", "")) or {}
        model = (document.get("llm") or {}).get("model") or (self.llm.model if self.llm else None)
        seats = []
        llm_log: dict = {}
        for seat, label in enumerate(game.labels):
            kind = game.kinds[seat]
            player = game.table.players.get(seat) or game.wrappers.get(seat)
            profile = getattr(player, "profile", None)
            seats.append(
                SeatRecord(
                    seat=seat,
                    suspect=game.suspects[seat],
                    label=label,
                    kind=kind,
                    profile=profile.to_dict() if profile is not None else None,
                    model=model if kind == "llm" else None,
                )
            )
            if kind == "llm":
                llm_log[seat] = [
                    entry["audit"] for entry in game.entries
                    if entry.get("kind") == "answer" and entry.get("seat") == seat and entry.get("audit")
                ]
        return GameRecord.from_game(
            run_id=run_id,
            game_index=game_index,
            seed=game.setup.seed,
            state=game.state,
            events=game.events,
            seats=seats,
            llm_log=llm_log or None,
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
        if game.setup.remember:
            self._set_debriefs(
                table_id,
                [seat for seat, kind in enumerate(game.kinds) if kind == "llm" and seat in game.wrappers],
            )
        return ref


def pending_debriefs(document: dict) -> list:
    """The seats whose debrief is still to be written, in seat order."""
    debriefs = document.get("debriefs") or {}
    return sorted(int(seat) for seat, state in debriefs.items() if (state or {}).get("status") == "pending")


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
