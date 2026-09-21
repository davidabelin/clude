"""A table with seats answered from outside the engine: who sits where,
the players built for it, and a game driven through `engine.game_steps`
that stops whenever such a seat has to decide (Phase 8.2,
docs/phase8-plan.md 3.1).

Every seat has a `SeatSpec`: a token, a kind, a label, and an LLM-only
memory-depth dial. New setups default to remembering through the web
registry; its memory snapshot joins the setup and entries for rebuilds.
A character
plays its own token, as it always has (`arena.seat_lineup`); a floor bot
takes a free one; a *human* seat -- and in Phase 8.3 an LLM-piloted seat
driven from here rather than from inside the engine -- has no player
object at all and is listed in `game_steps`'s `external` set, so the
generator yields a `DecisionRequest` for each of its decisions and waits.
`TableGame` holds that generator, keeps the request it is stopped on as
`pending`, and takes answers as plain data (`encode_answer` /
`decode_answer`), checked before they are sent in: an answer that fails
`engine.check_answer` inside the generator would finish it for everyone,
so the check runs here first and a bad answer is only ever a refusal.

Every answer becomes an *entry* in an ordered log, with the length of
the event log at the moment it was applied. A game is deterministic per
seed, every pause is deterministic given the entries before it, and a
paused game is therefore fully described by its setup and its entries:
`TableGame.rebuild` replays them into a fresh generator and lands on the
same pause, which is how a web table survives a cold instance
(`docs/architecture.md`, "Resumable"). Nothing here imports Flask; the
CLI drives a terminal seat through the same class (``play --human``).
"""
from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field
from typing import Optional

import clude_constraints
from clude_agents import AGENT_SPECS, build_character
from clude_core import board, engine
from clude_core.bots import RandomBot
from clude_core.domain import ROOMS, SUSPECTS, WEAPONS
from clude_core.engine import DecisionRequest, MoveChoice
from clude_core.events import GameOverEvent, RemarkEvent
from clude_storage.records import node_from_json, node_to_json

from .arena import Table, fill_seed, lineup_for_game, parse_roster

__all__ = [
    "EXTERNAL_KINDS",
    "MAX_TURNS",
    "SEAT_KINDS",
    "SeatSpec",
    "Speaker",
    "TableError",
    "TableGame",
    "TableSetup",
    "TableSnapshot",
    "build_table",
    "decode_answer",
    "describe_request",
    "encode_answer",
    "seat_specs",
]

MAX_TURNS = 300
"""The turn cap, as `clude_cli.py play` and the Watch screen have it."""

SEAT_KINDS: tuple = ("character", "floor", "random", "human", "open", "llm")
"""Stored seat kinds: ``character`` means headless, ``floor`` means floorbot.
``open`` is a seat waiting for a person and
cannot be dealt; ``llm`` is Phase 8.3's, an LLM-piloted character answered
from the driver rather than from inside the engine."""

EXTERNAL_KINDS: frozenset = frozenset({"human", "llm"})
"""The kinds with no player object: their decisions pause the game."""


class TableError(ValueError):
    """An answer or a document the table refuses, with a message fit to
    show the person who sent it."""


# --- seats -------------------------------------------------------------


@dataclass(frozen=True)
class SeatSpec:
    """One seat: the token it plays, what occupies it, and the label the
    occupant is recorded under.

    Parameters
    ----------
    token : str
        A suspect name: the token, and the seat's place in the turn order.
    kind : str
        One of `SEAT_KINDS`: ``character`` is the silent headless method;
        ``llm`` adds Claude's persona, leashed choices and table talk.
    label : str
        The occupant's identity, which is what `SeatRecord.label` and a
        logbook are keyed by: a character's own name (seat-locked, so it
        equals `token`), ``"floor"`` or ``"random"`` for a bot, a human's
        account key, and empty for an open seat.
    head : bool
        Whether a human seat is shown its token's own character numbers
        as a "head" (Phase 9, a chat seat over MCP): read-only, advisory,
        fixed when the seat is taken. Only a human seat may have one -- a
        character *is* its head, and a bot has none.
    memory : float
        An LLM seat's narrative logbook depth, from 0 (the condensed head)
        to 1 (every entry in full). Applies when the table remembers;
        independent of numeric method memory. Other seat kinds keep 0.
    """

    token: str
    kind: str
    label: str = ""
    head: bool = False
    memory: float = 0.0

    def __post_init__(self) -> None:
        if self.token not in SUSPECTS:
            raise ValueError(f"{self.token!r} is not a suspect")
        if self.kind not in SEAT_KINDS:
            raise ValueError(f"unknown seat kind {self.kind!r}; expected one of {SEAT_KINDS}")
        if not 0.0 <= self.memory <= 1.0:
            raise ValueError("memory must be a number from 0 to 1")
        if self.memory and self.kind != "llm":
            raise ValueError("only an LLM seat has a narrative memory dial")
        if self.head and self.kind != "human":
            raise ValueError(f"only a human seat takes a head, not a {self.kind} seat")
        if self.head and self.token not in AGENT_SPECS:
            raise ValueError(f"there is no character for {self.token} to be a head")
        if self.kind in ("character", "llm"):
            if self.token not in AGENT_SPECS:
                raise ValueError(f"there is no character for {self.token}")
            if self.label != self.token:
                raise ValueError(
                    f"{self.token}'s token is played by {self.token} or by nobody, never by {self.label!r}"
                )
        elif self.kind in ("floor", "random"):
            if not self.label:
                object.__setattr__(self, "label", self.kind)
            elif self.label != self.kind:
                raise ValueError(f"a {self.kind} seat is labelled {self.kind!r}, not {self.label!r}")
        elif self.kind == "human":
            if not self.label.strip():
                raise ValueError("a human seat needs a name")
        elif self.label:
            raise ValueError("an open seat has no occupant to label")

    @property
    def external(self) -> bool:
        return self.kind in EXTERNAL_KINDS

    def to_dict(self) -> dict:
        out = {"token": self.token, "kind": self.kind, "label": self.label}
        if self.head:  # only when set, so every stored setup reads as before
            out["head"] = True
        if self.kind == "llm":
            out["memory"] = self.memory
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "SeatSpec":
        return cls(
            str(data["token"]), str(data["kind"]), str(data.get("label", "")),
            bool(data.get("head", False)), float(data.get("memory", 0.0)),
        )


def _board_order(specs) -> tuple:
    return tuple(sorted(specs, key=lambda spec: SUSPECTS.index(spec.token)))


def seat_specs(lineup, humans: Optional[dict] = None) -> tuple:
    """Seat a lineup of bot labels and a set of humans, the way
    `arena.seat_lineup` seats a lineup: a character on its own token,
    every bot on the lowest token nobody has claimed, seats in the
    board's order. With no humans this is exactly `seat_lineup`'s
    seating (a test pins it).

    Parameters
    ----------
    lineup : sequence of str
        Character names and bot labels (``floor``, ``random``), as
        `arena.lineup_for_game` gives them.
    humans : dict or None
        Token -> the person's label. A human may take any token that is
        not a seated character's own.

    Raises
    ------
    ValueError
        A human on a seated character's token, two humans on one token,
        or a label that is neither a character nor a bot kind.
    """
    humans = dict(humans or {})
    characters = [label for label in lineup if label in AGENT_SPECS]
    for token in humans:
        if token in characters:
            raise ValueError(
                f"{token} is at the table, so nobody else can play the {token} token"
            )
    taken = set(characters) | set(humans)
    free = [s for s in SUSPECTS if s not in taken]
    specs = []
    for label in lineup:
        if label in AGENT_SPECS:
            specs.append(SeatSpec(label, "character", label))
        elif label in ("floor", "random"):
            if not free:
                raise ValueError("more players than tokens")
            specs.append(SeatSpec(free.pop(0), label, label))
        else:
            raise ValueError(f"unknown lineup entry {label!r}")
    for token, name in humans.items():
        specs.append(SeatSpec(token, "human", name))
    return _board_order(specs)


@dataclass(frozen=True)
class TableSetup:
    """Everything that decides a table's game: with the engine
    deterministic per seed, this and the entry log *are* the game.

    Parameters
    ----------
    seats : tuple of SeatSpec
        Kept in the board's order whatever order they arrive in.
    seed : int
    max_turns : int
    remember : bool
        True for new tables by default. The web layer loads and updates
        supported method memory for headless and LLM characters, and
        attaches narrative logbooks to LLM seats for read-back and debrief.
        The driver itself does no storage I/O; CLI logbooks remain explicit.
    """

    seats: tuple
    seed: int
    max_turns: int = MAX_TURNS
    remember: bool = True

    def __post_init__(self) -> None:
        seats = _board_order(self.seats)
        object.__setattr__(self, "seats", seats)
        n = len(seats)
        if not engine.MIN_PLAYERS <= n <= engine.MAX_PLAYERS:
            raise ValueError(
                f"a table seats {engine.MIN_PLAYERS} to {engine.MAX_PLAYERS}, not {n}"
            )
        tokens = [spec.token for spec in seats]
        if len(set(tokens)) != n:
            raise ValueError("two seats share a token")
        people = [spec.label for spec in seats if spec.kind == "human"]
        if len(set(people)) != len(people):
            raise ValueError("one person cannot sit in two seats")

    # -- derived -----------------------------------------------------------

    @property
    def n_players(self) -> int:
        return len(self.seats)

    @property
    def suspects(self) -> list:
        """Seat -> token, in seat (turn) order."""
        return [spec.token for spec in self.seats]

    @property
    def labels(self) -> list:
        """Seat -> label; an open seat reads as the floor bot that will
        fill it."""
        return [spec.label or "floor" for spec in self.seats]

    @property
    def kinds(self) -> list:
        return [spec.kind for spec in self.seats]

    @property
    def external(self) -> frozenset:
        """The seat indices `game_steps` pauses for."""
        return frozenset(seat for seat, spec in enumerate(self.seats) if spec.external)

    @property
    def open_seats(self) -> list:
        return [seat for seat, spec in enumerate(self.seats) if spec.kind == "open"]

    def dealt(self) -> "TableSetup":
        """This setup with every open seat filled by a floor bot: what
        gets built when the table is dealt."""
        seats = tuple(
            SeatSpec(spec.token, "floor") if spec.kind == "open" else spec for spec in self.seats
        )
        return TableSetup(seats, self.seed, self.max_turns, self.remember)

    def with_seat(self, seat: int, spec: SeatSpec) -> "TableSetup":
        """This setup with one seat replaced (a person sitting down or
        standing up before the deal)."""
        seats = list(self.seats)
        if spec.token != seats[seat].token:
            raise ValueError("a seat keeps its token")
        seats[seat] = spec
        return TableSetup(tuple(seats), self.seed, self.max_turns, self.remember)

    # -- construction ------------------------------------------------------

    @classmethod
    def from_roster(
        cls,
        roster,
        n_players: int,
        seed: int,
        *,
        humans: Optional[dict] = None,
        max_turns: int = MAX_TURNS,
        remember: bool = True,
    ) -> "TableSetup":
        """The table ``clude_cli.py play`` seats for `roster` at
        `n_players`, plus any `humans` (token -> label) in seats of
        their own. With no humans it is `arena.headless_table`'s table
        exactly, which is what lets `headless_table` build through here.

        Raises
        ------
        ValueError
            From `parse_roster` and `seat_specs`, or when the humans do
            not fit the table.
        """
        humans = dict(humans or {})
        n_bots = n_players - len(humans)
        if n_bots < 0:
            raise ValueError(f"{len(humans)} people will not fit at a table of {n_players}")
        entries = [str(item).strip() for item in roster if str(item).strip()]
        if n_bots == 0:
            lineup = []
        elif entries:
            lineup = lineup_for_game(parse_roster(entries), 0, n_bots)
        else:
            lineup = ["floor"] * n_bots
        return cls(seat_specs(lineup, humans), seed, max_turns, remember)

    def to_dict(self) -> dict:
        return {
            "seats": [spec.to_dict() for spec in self.seats],
            "seed": self.seed,
            "max_turns": self.max_turns,
            "remember": self.remember,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TableSetup":
        """Restore a saved setup, preserving its remembering choice.

        Legacy documents without ``remember`` retain the old False
        behavior so rebuilding an existing game never enables memory.
        """
        return cls(
            tuple(SeatSpec.from_dict(item) for item in data["seats"]),
            int(data["seed"]),
            int(data.get("max_turns", MAX_TURNS)),
            bool(data.get("remember", False)),
        )


def build_table(setup: TableSetup, llm_backend=None) -> tuple:
    """The players for `setup`, built as `arena.headless_table` builds
    them: each character with its preset dials (an LLM seat overrides
    narrative ``memory`` with its saved dial) and reset with the game
    seed, each floor bot with a private RNG from `fill_seed`, and every
    character told who it is sitting with -- humans by their labels, so
    White's per-opponent priors find them. External seats get no player
    object. An ``llm`` seat (Phase 8.3a) gets an `LLMCharacter` in
    `Table.wrappers`, reset and told the table like a character, when
    `llm_backend(seat)` is given to build its backend; without one -- a
    rebuild, which must never call a model -- the seat has no wrapper and
    its stored answers are simply replayed.

    Returns
    -------
    (Table, frozenset)
        The table and the external seat indices for `game_steps`.

    Raises
    ------
    ValueError
        On an open seat: fill it first (`TableSetup.dealt`).
    """
    if setup.open_seats:
        raise ValueError("an open seat cannot be dealt; fill it first (TableSetup.dealt)")
    labels = setup.labels
    players: dict = {}
    wrappers: dict = {}
    for seat, spec in enumerate(setup.seats):
        if spec.kind == "character":
            character = build_character(spec.label)
            character.reset(setup.seed)
            players[seat] = character
        elif spec.kind == "floor":
            players[seat] = clude_constraints.FloorBot(rng=random.Random(fill_seed(setup.seed, seat)))
        elif spec.kind == "random":
            players[seat] = RandomBot()
        elif spec.kind == "llm" and llm_backend is not None:
            from clude_llm import LLMCharacter  # noqa: PLC0415 -- only a table with model seats needs it

            profile = AGENT_SPECS[spec.label].profile.with_dials(memory=spec.memory)
            wrapper = LLMCharacter(build_character(spec.label, profile), llm_backend(seat))
            wrapper.reset(setup.seed)
            wrappers[seat] = wrapper
    for seat, spec in enumerate(setup.seats):
        if spec.kind == "character":
            players[seat].new_game(labels)
        elif seat in wrappers:
            wrappers[seat].new_game(labels)
    table = Table(
        players=players,
        labels=labels,
        suspects=setup.suspects,
        observer=clude_constraints.observe,
        kinds=setup.kinds,
        wrappers=wrappers,
    )
    return table, setup.external


# --- answers as data ---------------------------------------------------


def encode_answer(kind: str, answer):
    """An engine answer as JSON-ready data: the inverse of `decode_answer`.

    A movement is ``{"move": kind, "to": node}`` with the node through
    `records.node_to_json` (a boxed-in "stay" carries a square); a
    suggestion ``{"suspect", "weapon"}`` or None; an accusation
    ``{"suspect", "weapon", "room"}`` or None; a card ``{"card"}``.
    """
    if kind == "movement":
        return {"move": answer.kind, "to": node_to_json(answer.destination)}
    if kind == "suggestion":
        return None if answer is None else {"suspect": answer[0], "weapon": answer[1]}
    if kind == "accusation":
        if answer is None:
            return None
        return {"suspect": answer[0], "weapon": answer[1], "room": answer[2]}
    if kind == "card_to_show":
        return {"card": answer}
    raise ValueError(f"unknown decision kind {kind!r}")


def decode_answer(request: DecisionRequest, data):
    """The engine answer `data` describes for `request`, checked against
    what was offered.

    Raises
    ------
    TableError
        With a message fit to show: a move not on the list, a card the
        seat does not hold, a suggestion or accusation naming no such
        card, or data in the wrong shape.
    """
    kind = request.kind
    try:
        if kind == "movement":
            node = data.get("to")
            choice = MoveChoice(str(data["move"]), None if node is None else node_from_json(node))
            if choice not in request.choices:
                raise TableError("that move is not one of the moves offered")
            return choice
        if kind == "suggestion":
            if data is None:
                return None
            suspect, weapon = str(data["suspect"]), str(data["weapon"])
            if suspect not in SUSPECTS or weapon not in WEAPONS:
                raise TableError("a suggestion names a suspect and a weapon")
            return suspect, weapon
        if kind == "accusation":
            if data is None:
                return None
            triple = (str(data["suspect"]), str(data["weapon"]), str(data["room"]))
            if triple[0] not in SUSPECTS or triple[1] not in WEAPONS or triple[2] not in ROOMS:
                raise TableError("an accusation names a suspect, a weapon and a room")
            return triple
        if kind == "card_to_show":
            card = str(data["card"])
            if card not in request.candidates:
                raise TableError(f"you must show one of: {', '.join(request.candidates)}")
            return card
    except (KeyError, TypeError, AttributeError) as exc:
        raise TableError("that answer is not in the shape the decision needs") from exc
    raise TableError(f"unknown decision kind {kind!r}")


def describe_request(request: DecisionRequest) -> dict:
    """A `DecisionRequest` without its observation, JSON-ready: what a
    screen needs to put the decision to a person, each movement option
    already in the shape `decode_answer` takes back."""
    out: dict = {"seat": request.seat, "kind": request.kind}
    if request.kind == "movement":
        out["options"] = [
            {
                "move": choice.kind,
                "to": node_to_json(choice.destination),
                "room": board.room_of(choice.destination),
            }
            for choice in request.choices
        ]
    elif request.kind == "suggestion":
        out["room"] = request.room
    elif request.kind == "card_to_show":
        out["candidates"] = list(request.candidates)
        out["shown_to"] = request.shown_to
    return out


# --- the driver ----------------------------------------------------------


@dataclass(frozen=True)
class TableSnapshot:
    """What a reader may see of a `TableGame` without taking its lock:
    republished after every advance, immutable, so a poll never waits
    behind a slow turn.

    `n_events` bounds the event log a reader should look at, `seq` is the
    entry count an answer must quote, and `pending` is
    `describe_request` of the request the game is stopped on, or None.
    """

    turns: int
    finished: bool
    n_events: int
    seq: int
    pending: Optional[dict]
    positions: dict
    active: tuple
    previous_mark: int
    broken: Optional[str] = None


class Speaker:
    """An external seat's voice in the engine (Phase 8.3a): what
    `game_steps` drains and makes hear in that seat's place.

    Live, it fronts the seat's `LLMCharacter`: the lines the wrapper
    offered with a decision are drained here, at the event they belong
    to, and recorded in `said` so the entry can store them. On a rebuild
    the stored lines are put on `queue` first and returned instead, so
    the events match without a call; a wrapper present at the rebuild
    (a warm instance about to play on) is reminded of its own lines and
    hears everyone else's.
    """

    def __init__(self, seat: int, inner=None) -> None:
        self.seat = seat
        self.inner = inner
        self.queue: list = []
        self.said: list = []

    def take_remarks(self) -> list:
        if self.queue:
            lines, self.queue = self.queue, []
            if self.inner is not None:
                for text in lines:
                    self.inner._remember(self.seat, text)
        else:
            lines = list(self.inner.take_remarks()) if self.inner is not None else []
        self.said.extend(lines)
        return lines

    def hear(self, remark: RemarkEvent) -> None:
        if self.inner is not None:
            self.inner.hear(remark)

    def drain_said(self) -> list:
        lines, self.said = self.said, []
        return lines


class TableGame:
    """One game at a table, driven through `engine.game_steps` and paused
    whenever an external seat must decide.

    `run` plays until the next such request, the end of a turn, or the
    end of the game; `answer` takes one seat's decision as data, checks
    it, sends it in and runs on to the next pause; `rebuild` replays a
    stored entry log into a fresh game. The `lock` is for callers that
    share a game between threads (the web app); the class itself does not
    take it, so a single-threaded driver such as the CLI never pays for
    it.
    """

    def __init__(self, setup: TableSetup, prepare=None, llm_backend=None) -> None:
        """`prepare(table)`, if given, runs after the players are built
        and before the game deals: where the web app loads the
        supported method memory and LLM narrative logbooks ("characters
        remember", enabled by default for new web tables).
        `llm_backend(seat)`, if given, builds the backend of each ``llm``
        seat's wrapper (`build_table`); without it those seats can only
        replay stored answers."""
        self.setup = setup
        self.table, self.external = build_table(setup, llm_backend)
        if prepare is not None:
            prepare(self.table)
        self.speakers: dict = {
            seat: Speaker(seat, self.table.wrappers.get(seat))
            for seat, spec in enumerate(setup.seats)
            if spec.kind == "llm"
        }
        self._seat_rngs: dict = {}
        self._steps = engine.game_steps(
            setup.n_players,
            self.table.players,
            seed=setup.seed,
            max_turns=setup.max_turns,
            observer=self.table.observer,
            suspects=self.table.suspects,
            external=self.external,
            speakers=self.speakers,
        )
        self._live = next(self._steps)
        self.pending: Optional[DecisionRequest] = None
        self.entries: list = []
        self.turns = 0
        self.finished = False
        self.previous_mark = 0
        """Length of the event log before the most recent completed turn,
        so a screen can show exactly that turn's lines."""
        self._turn_mark = 0
        self._stand_ins: dict = {}
        self.broken: Optional[str] = None
        self.lock = threading.Lock()
        self._snapshot: Optional[TableSnapshot] = None
        self._publish()

    # -- reading -----------------------------------------------------------

    @property
    def state(self):
        return self._live.state

    @property
    def events(self) -> list:
        return self._live.events

    @property
    def labels(self) -> list:
        return list(self.table.labels)

    @property
    def suspects(self) -> list:
        return list(self.table.suspects)

    @property
    def kinds(self) -> list:
        return list(self.table.kinds)

    @property
    def seq(self) -> int:
        """The entry count: what the next answer must quote."""
        return len(self.entries)

    @property
    def snapshot(self) -> TableSnapshot:
        return self._snapshot

    def _publish(self) -> None:
        self._snapshot = TableSnapshot(
            turns=self.turns,
            finished=self.finished,
            n_events=len(self.events),
            seq=len(self.entries),
            pending=None if self.pending is None else describe_request(self.pending),
            positions=dict(self.state.positions),
            active=tuple(self.state.active),
            previous_mark=self.previous_mark,
            broken=self.broken,
        )

    def turn_events(self) -> list:
        """The events of the most recent completed turn."""
        return list(self.events[self.previous_mark:self._turn_mark])

    # -- advancing ---------------------------------------------------------

    def run(self, turns: int = 1) -> int:
        """Play up to `turns` more turns; returns how many completed.
        Stops early on a request for an external seat (kept as
        `pending`) and does nothing while one is waiting."""
        if self.pending is not None or self.finished or self.broken:
            return 0
        return self._resume(turns=turns)

    def play_to_end(self) -> int:
        """Play every remaining turn, or up to the next external request."""
        return self.run(self.setup.max_turns + 1)

    @property
    def wrappers(self) -> dict:
        """Seat -> the LLM wrapper piloting it, for the seats that have one."""
        return self.table.wrappers

    def answer(self, seat: int, seq: int, data, by: str = "human", audit=None) -> None:
        """Send one decision in for the seat the game is stopped on.

        Parameters
        ----------
        seat : int
            Must be `pending`'s seat.
        seq : int
            Must equal the entry count, so a stale or doubled submission
            is refused rather than applied twice.
        data
            As `encode_answer` shapes it.
        by : str
            Who answered, for the entry: ``"human"``, ``"autopilot"``,
            ``"llm"``, or ``"mcp"`` (a chat seat, Phase 9: a human seat
            answered through the MCP server, with no audit attached).
        audit : dict or None
            An LLM seat's `Decision.to_dict()` for the entry (Phase 8.3a),
            which becomes the record's `llm_log` and rebuilds the
            wrapper's audit on a cold instance.

        Raises
        ------
        TableError
            With a message fit to show, leaving the game exactly as it
            was.
        """
        request = self.pending
        if self.broken:
            raise TableError(f"this table is broken: {self.broken}")
        if request is None:
            raise TableError("nothing is waiting for an answer")
        if seat != request.seat:
            raise TableError("it is not this seat's decision")
        if seq != len(self.entries):
            raise TableError("that answer is out of date; the table has moved on")
        value = decode_answer(request, data)
        try:
            engine.check_answer(request, value)
        except ValueError as exc:
            raise TableError(str(exc)) from exc
        entry = {
            "kind": "answer",
            "seat": seat,
            "decision": request.kind,
            "data": encode_answer(request.kind, value),
            "at": len(self.events),
            "by": by,
        }
        if audit is not None:
            entry["audit"] = audit
        self.entries.append(entry)
        self.pending = None
        try:
            self._resume(answer=value, ready=True, turns=1)
        finally:
            said = [[who, text] for who, speaker in sorted(self.speakers.items()) for text in speaker.drain_said()]
            if said:
                entry["said"] = said
                self._publish()

    def llm_answer(self) -> None:
        """Let the pending seat's LLM wrapper decide (Phase 8.3a): one
        `choose_*` call on the request's own observation, within the
        character's leash and with the character as the fallback, stored
        as an entry with its audit and the lines it said, so a rebuild
        never asks the model again.

        Raises
        ------
        TableError
            When nothing is pending, or the pending seat has no wrapper
            (a table built without a backend).
        """
        request = self.pending
        if request is None:
            raise TableError("nothing is waiting for an answer")
        wrapper = self.table.wrappers.get(request.seat)
        if wrapper is None:
            raise TableError(f"seat {request.seat} has no model to answer for it")
        rng = self._seat_rngs.get(request.seat)
        if rng is None:
            rng = self._seat_rngs[request.seat] = random.Random(fill_seed(self.setup.seed, request.seat))
        if request.kind == "movement":
            value = wrapper.choose_movement(request.obs, request.choices, rng)
        elif request.kind == "suggestion":
            value = wrapper.choose_suggestion(request.obs, request.room, rng)
        elif request.kind == "accusation":
            value = wrapper.choose_accusation(request.obs, rng)
        else:
            value = wrapper.choose_card_to_show(request.obs, request.candidates, request.shown_to, rng)
        audit = wrapper.decisions[-1].to_dict() if wrapper.decisions else None
        self.answer(request.seat, len(self.entries), encode_answer(request.kind, value), by="llm", audit=audit)

    def remark(self, seat: int, text: str, about: str = "chat", audit: Optional[dict] = None) -> None:
        """Append a line of table talk from an external seat as a
        `RemarkEvent`, logged as an entry so a rebuild puts it back at the
        same place (Phase 8.3). Allowed only while the game is paused,
        which is the only time a driver holds it. `audit` is the model's
        `Decision.to_dict()` behind an off-turn line, stored so a rebuild
        can give it back to the wrapper (8.3d)."""
        entry = {"kind": about, "seat": seat, "text": text, "at": len(self.events)}
        if audit:
            entry["audit"] = audit
        self.entries.append(entry)
        remark = RemarkEvent(self.state.turn, seat, text, about)
        self.events.append(remark)
        for who, speaker in self.speakers.items():
            if who != seat:
                speaker.hear(remark)
        for who, player in self.table.players.items():
            if who != seat and isinstance(player, engine.SpeakingPlayer):
                player.hear(remark)
        self._publish()

    def stand_in_answer(self) -> dict:
        """What the floor bot for the pending seat would answer, as data:
        the plain, characterless player, so a seat on autopilot never
        impersonates a character. Deterministic per game and seat."""
        request = self.pending
        if request is None:
            raise TableError("nothing is waiting for an answer")
        bot = self._stand_ins.get(request.seat)
        if bot is None:
            bot = clude_constraints.FloorBot(rng=random.Random(fill_seed(self.setup.seed, request.seat)))
            self._stand_ins[request.seat] = bot
        rng = random.Random(0)  # unused: the bot has a private RNG
        if request.kind == "movement":
            value = bot.choose_movement(request.obs, request.choices, rng)
        elif request.kind == "suggestion":
            value = bot.choose_suggestion(request.obs, request.room, rng)
        elif request.kind == "accusation":
            value = bot.choose_accusation(request.obs, rng)
        else:
            value = bot.choose_card_to_show(request.obs, request.candidates, request.shown_to, rng)
        return encode_answer(request.kind, value)

    def autopilot(self) -> None:
        """Answer the pending request with `stand_in_answer`, recorded as
        an entry like any other so a rebuild never needs the stand-in."""
        request = self.pending
        if request is None:
            raise TableError("nothing is waiting for an answer")
        self.answer(request.seat, len(self.entries), self.stand_in_answer(), by="autopilot")

    def _resume(self, answer=None, ready: bool = False, turns: int = 1) -> int:
        """Drive the generator until a request for an external seat, until
        `turns` turns have completed, or until the game ends. Returns the
        turns completed. Notices the three endings eagerly, as the Watch
        screen did, so the turn that ends the game is the one that says so."""
        played = 0
        try:
            while not self.finished:
                try:
                    item = self._steps.send(answer) if ready else next(self._steps)
                except StopIteration:
                    self.finished = True
                    break
                ready, answer = False, None
                if isinstance(item, DecisionRequest):
                    self.pending = item
                    break
                if isinstance(item, engine.TurnComplete):
                    played += 1
                    self.turns += 1
                    self.previous_mark = self._turn_mark
                    self._turn_mark = len(self.events)
                    if self._over():
                        self._drain()
                    if played >= turns:
                        break
        except Exception as exc:  # the generator died: nothing can be sent in again
            self.broken = f"{type(exc).__name__}: {exc}"
            self.finished = True
            raise
        finally:
            self._publish()
        return played

    def _over(self) -> bool:
        return (
            (bool(self.events) and isinstance(self.events[-1], GameOverEvent))
            or self.turns >= self.setup.max_turns
            or not any(self.state.active)
        )

    def _drain(self) -> None:
        """Let the generator finish once the game is known to be over. In
        each of the three endings it returns without drawing a die or
        asking anyone anything, so this changes nothing but the flag."""
        try:
            item = next(self._steps)
        except StopIteration:
            self.finished = True
            return
        raise RuntimeError(f"the game went on after it should have ended: {item!r}")

    # -- rebuilding --------------------------------------------------------

    @classmethod
    def rebuild(cls, setup: TableSetup, entries: list, turns: int, prepare=None, llm_backend=None) -> "TableGame":
        """A game brought back to where it was from its setup, its entry
        log and its turn count: every answer is sent in at the request it
        answered, every remark put back at the event it followed, and the
        turns played afterwards played again.

        Raises
        ------
        TableError
            When the log does not replay: an answer whose request never
            comes, or comes for another seat or decision, which means the
            stored document and the code disagree.
        """
        game = cls(setup, prepare, llm_backend)
        for index, entry in enumerate(entries):
            if entry.get("kind") == "answer":
                for who, text in entry.get("said") or []:
                    game.speakers[int(who)].queue.append(str(text))
                wrapper = game.table.wrappers.get(int(entry["seat"]))
                if wrapper is not None and entry.get("audit"):
                    from clude_llm import Decision  # noqa: PLC0415

                    wrapper.decisions.append(Decision(**entry["audit"]))
                while game.pending is None and not game.finished:
                    game._resume(turns=1)
                request = game.pending
                expected = (int(entry["seat"]), str(entry["decision"]))
                if request is None or (request.seat, request.kind) != expected:
                    got = "the end of the game" if request is None else f"{request.kind} for seat {request.seat}"
                    raise TableError(
                        f"entry {index} answers {expected[1]} for seat {expected[0]}, but the game reached {got}"
                    )
                game.answer(
                    request.seat, len(game.entries), entry["data"],
                    by=str(entry.get("by", "human")), audit=entry.get("audit"),
                )
            else:
                target = int(entry["at"])
                while len(game.events) < target and game.pending is None and not game.finished:
                    game._resume(turns=1)
                if len(game.events) != target:
                    raise TableError(
                        f"entry {index} was said after event {target}, which the game does not reach"
                    )
                seat, text = int(entry["seat"]), str(entry["text"])
                game.remark(seat, text, str(entry["kind"]), audit=entry.get("audit"))
                if entry.get("kind") == "reaction":
                    # `remark` fans a line to everyone else; the wrapper
                    # that said it live remembered it itself (`react`), so
                    # a wrapper present at the rebuild is reminded here,
                    # and its decision given back, as for an answer above.
                    speaker = game.speakers.get(seat)
                    if speaker is not None and speaker.inner is not None:
                        speaker.inner._remember(seat, text)
                        if entry.get("audit"):
                            from clude_llm import Decision  # noqa: PLC0415

                            speaker.inner.decisions.append(Decision(**entry["audit"]))
        while not game.finished and game.pending is None and game.turns < turns:
            game._resume(turns=1)
        return game
