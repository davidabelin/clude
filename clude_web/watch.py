"""Watching a headless game being played, a turn at a time.

The engine seam from step 1 is what makes this possible without threads:
`engine.game_steps` yields a `TurnComplete` at the end of every turn, so
"next turn" is simply "advance the generator to the next marker". The
generator lives in memory; what is saved is only the setup and how many
turns have been played, because a game is deterministic per seed --
feeding a fresh generator the same setup and running it the same number
of turns rebuilds it exactly, which is how a watched game survives a
cold Cloud Run instance (`docs/phase8.1-plan.md` 3.3).

**What a spectator may see.** The hands and the envelope stay hidden
until the game is over (3.2). That rules out the replay's per-card bars
here, and not only for the obvious reason: every seat's own hand is
proven to that seat from the first turn, and all the hands together are
exactly the eighteen cards that are *not* the answer. Show every seat's
card-by-card view and the envelope is on screen before anyone moves. So
a seat's block here is Direction D's compact bar -- how many cards it
has placed, and how sure it is in each category -- naming no card. A
refutation is described as *who* disproved it, never *what* they showed.
When the game ends it is saved as an ordinary record and opens as a
replay, where everything is laid face up.

Nothing here spends money: every seat is headless (3.6).
"""
from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

import clude_constraints
from clude_agents import AGENT_SPECS, build_agent
from clude_core import engine
from clude_core.domain import ROOMS, SUSPECTS, WEAPONS
from clude_core.events import GameOverEvent
from clude_storage import GameRecord, SeatRecord
from clude_training.arena import headless_table, parse_roster, seat_kind

from . import replay_data

WATCH_PREFIX = "watch"
"""Store folder holding one document per watched game."""

WEB_RUN = "web"
"""The run every game played through the web app is saved under, so it
shows in the lobby beside the arena's runs and opens as a replay."""

MAX_TURNS = 300
"""The turn cap, as `clude_cli.py play` has it."""

CATEGORIES = (("suspects", SUSPECTS), ("weapons", WEAPONS), ("rooms", ROOMS))

_SAVE_LOCK = threading.Lock()
"""Serialises picking the next game index in the web run. One instance
(`--max-instances 1`) with a few threads, so a process lock is enough."""


@dataclass(frozen=True)
class WatchSetup:
    """Everything that decides a watched game: with the engine
    deterministic per seed, this and a turn count *are* the game."""

    roster: tuple
    n_players: int
    seed: int
    max_turns: int = MAX_TURNS

    def to_dict(self) -> dict:
        return {
            "roster": list(self.roster),
            "n_players": self.n_players,
            "seed": self.seed,
            "max_turns": self.max_turns,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WatchSetup":
        return cls(
            roster=tuple(data["roster"]),
            n_players=int(data["n_players"]),
            seed=int(data["seed"]),
            max_turns=int(data.get("max_turns", MAX_TURNS)),
        )


def parse_setup(form) -> WatchSetup:
    """A `WatchSetup` from the lobby's new-game form.

    The roster is the characters ticked, each at most once; the seats
    they leave empty are filled with `floor` bots, as `play` fills them.
    Characters are seat-locked (CLAUDE.md), so each plays its own token.

    Raises
    ------
    ValueError
        With a message fit to show on the form: no character ticked, more
        characters than seats, a table size outside 3-6, or a seed that
        is not a whole number.
    """
    chosen = [name for name in form.getlist("characters") if name in AGENT_SPECS]
    if not chosen:
        raise ValueError("Pick at least one character to watch.")
    try:
        n_players = int(form.get("n_players", "") or 0)
    except ValueError:
        raise ValueError("The table size must be a number from 3 to 6.") from None
    if not engine.MIN_PLAYERS <= n_players <= engine.MAX_PLAYERS:
        raise ValueError("The table size must be from 3 to 6.")
    if len(chosen) > n_players:
        raise ValueError(
            f"{len(chosen)} characters will not fit at a table of {n_players}. "
            "Untick some, or make the table bigger."
        )
    raw_seed = (form.get("seed") or "").strip()
    if raw_seed:
        try:
            seed = int(raw_seed)
        except ValueError:
            raise ValueError("The seed must be a whole number, or left blank.") from None
    else:
        seed = secrets.randbelow(1_000_000)
    roster = tuple(parse_roster(chosen))
    return WatchSetup(roster=roster, n_players=n_players, seed=seed)


class WatchGame:
    """One headless game, advanced a turn at a time through
    `engine.game_steps`.

    Every seat is played by its own object, so the generator never asks
    for a decision: it only ever pauses at a `TurnComplete`. The
    `LiveGame` handle it yields first is how this reads the board and the
    log while the game is paused.
    """

    def __init__(self, setup: WatchSetup) -> None:
        self.setup = setup
        self.table = headless_table(setup.roster, setup.n_players, setup.seed)
        self._steps = engine.game_steps(
            setup.n_players,
            self.table.players,
            seed=setup.seed,
            max_turns=setup.max_turns,
            observer=self.table.observer,
            suspects=self.table.suspects,
        )
        self._live = next(self._steps)
        self.turns = 0
        self.finished = False
        self.previous_mark = 0
        """Length of the event log before the most recent turn, so the
        screen can show exactly that turn's lines."""
        self.lock = threading.Lock()

    @property
    def state(self):
        return self._live.state

    @property
    def events(self) -> list:
        return self._live.events

    def advance(self, turns: int = 1) -> int:
        """Play up to `turns` more turns; returns how many were played.

        Notices the end of the game eagerly -- a correct accusation, the
        turn cap, or every seat eliminated -- so the turn that ends it is
        also the turn that says so, rather than leaving one more click
        that plays nothing.
        """
        played = 0
        while played < turns and not self.finished:
            mark = len(self.events)
            try:
                item = next(self._steps)
            except StopIteration:
                self.finished = True
                break
            if isinstance(item, engine.TurnComplete):
                played += 1
                self.turns += 1
                self.previous_mark = mark
                if self._over():
                    self._drain()
        return played

    def play_to_end(self) -> int:
        """Play every remaining turn; returns how many that was."""
        return self.advance(self.setup.max_turns + 1)

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

    @property
    def suspects(self) -> list:
        return list(self.table.suspects)

    def turn_lines(self) -> list:
        """``(kind, text)`` for every event of the most recent turn, with
        the card shown at any refutation kept private."""
        suspects = self.suspects
        return [
            replay_data.describe_event(event, suspects, reveal=False)
            for event in self.events[self.previous_mark:]
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
        seat's own method is. Names no card (see the module docstring).

        Beliefs come from a fresh agent per reading, reset with the game
        seed -- never from the agent actually playing, whose RNG a reading
        would disturb and so change the rest of the game. That makes a
        reading a pure function of the seat, the seed and its view, so a
        rebuilt game reads exactly as the live one did. For White and
        Green it is the same stateless reading the replay gives, with the
        same caveat (`replay_data.TRACE_LIMITATION`).
        """
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
                    "total": sum(len(cards) for _, cards in CATEGORIES),
                    "groups": groups,
                }
            )
        return out

    def record(self, run_id: str, game_index: int) -> GameRecord:
        """The finished game as an ordinary record, so it lists and
        replays like any arena game."""
        if not self.finished:
            raise ValueError("a game in progress has no record yet")
        seats = []
        for seat, label in enumerate(self.table.labels):
            player = self.table.players[seat]
            profile = getattr(player, "profile", None)
            seats.append(
                SeatRecord(
                    seat=seat,
                    suspect=self.table.suspects[seat],
                    label=label,
                    kind=seat_kind(label),
                    profile=profile.to_dict() if profile is not None else None,
                )
            )
        return GameRecord.from_game(
            run_id=run_id,
            game_index=game_index,
            seed=self.setup.seed,
            state=self.state,
            events=self.events,
            seats=seats,
        )


def watch_key(watch_id: str) -> str:
    return f"{WATCH_PREFIX}/{watch_id}.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class WatchRegistry:
    """The watched games: live objects in memory, their setup and turn
    count in the store.

    In memory is a cache, not the truth. Every change is written through
    to the store, and a game missing from memory -- a restarted process,
    a fresh Cloud Run instance -- is rebuilt from its document by
    replaying the same number of turns.
    """

    def __init__(self, store) -> None:
        self.store = store
        self._games: dict = {}
        self._lock = threading.Lock()

    def create(self, setup: WatchSetup, started_by: str) -> str:
        watch_id = secrets.token_hex(5)
        game = WatchGame(setup)
        with self._lock:
            self._games[watch_id] = game
        self.store.put_doc(
            watch_key(watch_id),
            {
                "version": 1,
                "id": watch_id,
                "setup": setup.to_dict(),
                "turns": 0,
                "started_by": started_by,
                "created": _now(),
                "updated": _now(),
                "finished": False,
                "record": None,
            },
        )
        return watch_id

    def document(self, watch_id: str):
        """The stored document, or None for an unknown or malformed id."""
        try:
            return self.store.get_doc(watch_key(watch_id))
        except (KeyError, ValueError):
            return None

    def game(self, watch_id: str):
        """The live game, rebuilt from the store if it is not in memory.
        None for an unknown id."""
        with self._lock:
            cached = self._games.get(watch_id)
        if cached is not None:
            return cached
        document = self.document(watch_id)
        if document is None:
            return None
        game = WatchGame(WatchSetup.from_dict(document["setup"]))
        game.advance(int(document.get("turns", 0)))
        with self._lock:
            self._games.setdefault(watch_id, game)
            return self._games[watch_id]

    def save(self, watch_id: str, game: WatchGame, record_ref=None) -> dict:
        document = self.document(watch_id) or {"id": watch_id, "version": 1}
        document.update(
            {
                "setup": game.setup.to_dict(),
                "turns": game.turns,
                "finished": game.finished,
                "updated": _now(),
            }
        )
        if record_ref is not None:
            document["record"] = record_ref
        self.store.put_doc(watch_key(watch_id), document)
        return document

    def in_progress(self) -> list:
        """Every unfinished watched game's document, newest first."""
        documents = []
        for key in self.store.list_docs(WATCH_PREFIX):
            document = self.document(key)
            if document is not None and not document.get("finished"):
                documents.append(document)
        return sorted(documents, key=lambda d: d.get("created", ""), reverse=True)

    def finish(self, watch_id: str, game: WatchGame) -> dict:
        """Save a finished game into the web run, once. Returns
        ``{"run_id", "index"}``; a second call returns the first's."""
        document = self.document(watch_id) or {}
        if document.get("record"):
            return document["record"]
        with _SAVE_LOCK:
            index = max(self.store.list_games(WEB_RUN), default=-1) + 1
            record = game.record(WEB_RUN, index)
            self.store.put_game(WEB_RUN, index, record.to_dict())
            _add_to_web_run(self.store, record, game.setup)
        ref = {"run_id": WEB_RUN, "index": index}
        self.save(watch_id, game, record_ref=ref)
        return ref


def _add_to_web_run(store, record: GameRecord, setup: WatchSetup) -> None:
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
            "max_turns": setup.max_turns,
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
            "hit_cap": record.winner is None and record.turns >= setup.max_turns,
        }
    )
    summary["games"].sort(key=lambda g: g["game_index"])
    summary["n_games"] = len(summary["games"])
    summary["roster"] = sorted({label for g in summary["games"] for label in g["labels"]})
    summary["player_counts"] = sorted({g["n_players"] for g in summary["games"]})
    store.put_run(WEB_RUN, summary)
