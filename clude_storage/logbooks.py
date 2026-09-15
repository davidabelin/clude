"""Logbooks: one identity's persistent memory (Phase 7), as documents in
a `RecordStore` beside the game records.

An identity is a `SeatRecord.label`: a character name whichever token
it plays, or later a human's display name. Under ``logbooks/<identity>``
a logbook holds::

    entries/NNNN.json   one immutable entry per game, zenbot-shaped
                        (docs/zenbot_memories.json minus the koans):
                        computed facts plus what the identity's own
                        model wrote about the game
    head.json           the rolling state the identity reads back: its
                        standing instructions, a dossier per opponent
                        it has met, a tally, and an index of the flags
                        its entries carry
    method.json         the method's numeric memory (Mustard's rows,
                        White's counts, Green's posteriors); an opaque
                        document owned by `clude_training.memory`

`render_memory` turns the head and entries into the text block an
LLM-piloted character is given before a game, at the depth its
`memory` dial asks for (docs/phase7-plan.md): the head alone at 0, a
one-line index of entries (summary and flags) up to 0.5, and whole
entries above that, every entry at 1. It is pure text so the CLI can
show exactly what a character would read.

Nothing here calls a model; `clude_llm.logbook` writes the entries.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .records import GameRecord
from .stores import validate_run_id

LOGBOOK_VERSION = 1
LOGBOOKS_PREFIX = "logbooks"

MAX_STANDING_INSTRUCTIONS = 8
MAX_FLAGS = 6
SUMMARY_WORDS = 40
"""Advertised bound on an entry's `summary`; clipped at 1.5x."""
READ_WORDS = 60
"""Advertised bound on a dossier's `read`; clipped at 1.5x."""

_FLAG_JUNK = re.compile(r"[^a-z0-9]+")


# ---------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------


def logbook_prefix(identity: str) -> str:
    """``logbooks/<identity>``; `identity` must be a safe path segment."""
    return f"{LOGBOOKS_PREFIX}/{validate_run_id(identity)}"


def head_key(identity: str) -> str:
    return f"{logbook_prefix(identity)}/head.json"


def method_key(identity: str) -> str:
    return f"{logbook_prefix(identity)}/method.json"


def entries_prefix(identity: str) -> str:
    return f"{logbook_prefix(identity)}/entries"


def entry_key(identity: str, serial: int) -> str:
    if int(serial) <= 0:
        raise ValueError("entry serials start at 1")
    return f"{entries_prefix(identity)}/{int(serial):04d}.json"


# ---------------------------------------------------------------------
# Normalisation of what a model wrote
# ---------------------------------------------------------------------


def normalize_flag(text) -> str:
    """``"Over Confident!"`` -> ``"over-confident"``; empty if nothing is left."""
    if not isinstance(text, str):
        return ""
    return _FLAG_JUNK.sub("-", text.strip().lower()).strip("-")


def normalize_flags(items) -> list:
    """Normalised, de-duplicated flags in their original order, at most
    `MAX_FLAGS` of them."""
    seen: list = []
    for item in items or []:
        flag = normalize_flag(item)
        if flag and flag not in seen:
            seen.append(flag)
    return seen[:MAX_FLAGS]


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _lines(items, cap: Optional[int] = None) -> list:
    cleaned = [_text(item) for item in (items or []) if _text(item)]
    return cleaned[:cap] if cap else cleaned


def _clip_words(text: str, advertised: int) -> str:
    """Cut `text` at 1.5 times the advertised word bound; the prompt
    states the bound, this only guards the stored size."""
    words = text.split()
    limit = int(advertised * 1.5)
    return text if len(words) <= limit else " ".join(words[:limit])


def _date_of(record: GameRecord) -> str:
    stamp = record.created_at or ""
    if len(stamp) >= 10 and stamp[4] == "-" and stamp[7] == "-":
        return stamp[:10]
    return datetime.now(timezone.utc).date().isoformat()


# ---------------------------------------------------------------------
# Entries
# ---------------------------------------------------------------------


def entry_table(record: GameRecord) -> list:
    """Who sat where: ``[{"seat", "label", "token"}, ...]`` in seat order."""
    return [
        {"seat": s.seat, "label": s.label, "token": s.suspect}
        for s in sorted(record.seats, key=lambda s: s.seat)
    ]


def entry_outcome(record: GameRecord, seat: int) -> dict:
    """The facts of the game from `seat`'s side: who won, whether this
    seat accused and was right, the envelope, how the game ended."""
    labels = {s.seat: s.label for s in record.seats}
    own_accusation = None
    wrong_accusers: set = set()
    for event in record.events:
        accusation = getattr(event, "accusation", None)
        if accusation is None:
            continue
        if not accusation.correct:
            wrong_accusers.add(accusation.accuser)
        if accusation.accuser == seat:
            own_accusation = accusation
    winner = record.winner
    everyone_out = winner is None and len(wrong_accusers) >= record.n_players
    return {
        "winner": labels.get(winner) if winner is not None else None,
        "winner_seat": winner,
        "won": winner == seat,
        "turns": record.turns,
        "accused": own_accusation is not None,
        "accusation": (
            [own_accusation.suspect, own_accusation.weapon, own_accusation.room]
            if own_accusation is not None else None
        ),
        "accusation_correct": None if own_accusation is None else bool(own_accusation.correct),
        "envelope": list(record.envelope),
        "everyone_out": everyone_out,
        "hit_cap": winner is None and not everyone_out,
    }


def outcome_phrase(outcome: dict) -> str:
    """One clause: ``won in 24 turns``, ``lost; Mustard won in 19 turns``, ..."""
    turns = outcome.get("turns")
    winner = outcome.get("winner")
    if outcome.get("won"):
        return f"won in {turns} turns"
    if outcome.get("accused") and outcome.get("accusation_correct") is False:
        tail = f"; {winner} won" if winner else "; nobody won"
        return f"accused wrongly and was eliminated{tail}"
    if winner:
        return f"lost; {winner} won in {turns} turns"
    if outcome.get("hit_cap"):
        return f"nobody won (turn cap at {turns})"
    return "nobody won (every player eliminated)"


@dataclass
class LogbookEntry:
    """One game, as one identity's logbook records it. The first block of
    fields is computed from the `GameRecord`; the rest is what the
    identity's own model wrote at the debrief (`build` normalises it).

    Parameters
    ----------
    identity : str
        Whose logbook this is (`SeatRecord.label`).
    serial : int
        1-based position in that logbook.
    seat : int
        The seat the identity occupied in this game.
    date : str
        ISO date the game was recorded on.
    game_id : str
        ``<run_id>/<index>``, the record this entry describes.
    token : str
        The suspect token the identity played.
    table : list
        `entry_table` of the game.
    outcome : dict
        `entry_outcome` from this seat.
    model : str or None
        The model that wrote the entry.
    title, summary, what_happened, final_outcome : str
    flags : list[str]
        Short keywords shared across entries; `normalize_flags`.
    evaluations : list[dict]
        ``{"opponent", "evaluation", "notes"}`` per opponent judged.
    key_insights, lessons_learned, standing_instructions : list[str]
    dossiers : list[dict]
        ``{"opponent", "read"}``: the rewritten read on each opponent
        present that the model chose to revise.
    """

    identity: str
    serial: int
    seat: int
    date: str
    game_id: str
    token: str
    table: list
    outcome: dict
    model: Optional[str] = None
    title: str = ""
    summary: str = ""
    flags: list = field(default_factory=list)
    what_happened: str = ""
    evaluations: list = field(default_factory=list)
    key_insights: list = field(default_factory=list)
    lessons_learned: list = field(default_factory=list)
    final_outcome: str = ""
    standing_instructions: list = field(default_factory=list)
    dossiers: list = field(default_factory=list)
    version: int = LOGBOOK_VERSION

    def opponents(self) -> list:
        """Labels of the other seats, de-duplicated, in seat order."""
        seen: list = []
        for row in self.table:
            if row["seat"] != self.seat and row["label"] not in seen:
                seen.append(row["label"])
        return seen

    @classmethod
    def build(
        cls,
        identity: str,
        serial: int,
        record: GameRecord,
        seat: int,
        written: Optional[dict] = None,
        model: Optional[str] = None,
    ) -> "LogbookEntry":
        """An entry for `seat`'s game, its facts computed from `record`
        and its narrative taken from `written` (the model's JSON, any
        field optional): text stripped, lists cleaned and capped, flags
        normalised, evaluations and dossiers kept only for opponents who
        were at the table."""
        written = dict(written or {})
        table = entry_table(record)
        token = next((row["token"] for row in table if row["seat"] == seat), f"seat {seat}")
        entry = cls(
            identity=identity,
            serial=int(serial),
            seat=int(seat),
            date=_date_of(record),
            game_id=f"{record.run_id}/{record.game_index:05d}",
            token=token,
            table=table,
            outcome=entry_outcome(record, seat),
            model=model,
            title=_text(written.get("title")),
            summary=_clip_words(_text(written.get("summary")), SUMMARY_WORDS),
            flags=normalize_flags(written.get("flags")),
            what_happened=_text(written.get("what_happened")),
            key_insights=_lines(written.get("key_insights")),
            lessons_learned=_lines(written.get("lessons_learned")),
            final_outcome=_text(written.get("final_outcome")),
            standing_instructions=_lines(
                written.get("standing_instructions"), MAX_STANDING_INSTRUCTIONS
            ),
        )
        present = set(entry.opponents())
        for item in written.get("evaluations") or []:
            if not isinstance(item, dict):
                continue
            opponent = _text(item.get("opponent"))
            if opponent in present and (_text(item.get("evaluation")) or _text(item.get("notes"))):
                entry.evaluations.append({
                    "opponent": opponent,
                    "evaluation": _text(item.get("evaluation")),
                    "notes": _text(item.get("notes")),
                })
        for item in written.get("dossiers") or []:
            if not isinstance(item, dict):
                continue
            opponent = _text(item.get("opponent"))
            read = _clip_words(_text(item.get("read")), READ_WORDS)
            if opponent in present and read:
                entry.dossiers.append({"opponent": opponent, "read": read})
        return entry

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "identity": self.identity,
            "serial": self.serial,
            "seat": self.seat,
            "date": self.date,
            "game_id": self.game_id,
            "token": self.token,
            "table": [dict(row) for row in self.table],
            "outcome": dict(self.outcome),
            "model": self.model,
            "title": self.title,
            "summary": self.summary,
            "flags": list(self.flags),
            "what_happened": self.what_happened,
            "evaluations": [dict(item) for item in self.evaluations],
            "key_insights": list(self.key_insights),
            "lessons_learned": list(self.lessons_learned),
            "final_outcome": self.final_outcome,
            "standing_instructions": list(self.standing_instructions),
            "dossiers": [dict(item) for item in self.dossiers],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LogbookEntry":
        return cls(
            identity=data["identity"],
            serial=int(data["serial"]),
            seat=int(data["seat"]),
            date=data.get("date", ""),
            game_id=data.get("game_id", ""),
            token=data.get("token", ""),
            table=[dict(row) for row in data.get("table", [])],
            outcome=dict(data.get("outcome", {})),
            model=data.get("model"),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            flags=list(data.get("flags", [])),
            what_happened=data.get("what_happened", ""),
            evaluations=[dict(item) for item in data.get("evaluations", [])],
            key_insights=list(data.get("key_insights", [])),
            lessons_learned=list(data.get("lessons_learned", [])),
            final_outcome=data.get("final_outcome", ""),
            standing_instructions=list(data.get("standing_instructions", [])),
            dossiers=[dict(item) for item in data.get("dossiers", [])],
            version=int(data.get("version", LOGBOOK_VERSION)),
        )


# ---------------------------------------------------------------------
# The head
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class Dossier:
    """The rolling read on one opponent.

    Parameters
    ----------
    read : str
        The identity's current read, in its own words; empty until its
        model has written one.
    games_together : int
        Games this identity and the opponent have shared, entry or not.
    updated : str
        Date of the entry that last revised `read`.
    serial : int
        That entry's serial (0 if never revised).
    """

    read: str = ""
    games_together: int = 0
    updated: str = ""
    serial: int = 0

    def to_dict(self) -> dict:
        return {
            "read": self.read,
            "games_together": self.games_together,
            "updated": self.updated,
            "serial": self.serial,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Dossier":
        return cls(
            read=data.get("read", ""),
            games_together=int(data.get("games_together", 0)),
            updated=data.get("updated", ""),
            serial=int(data.get("serial", 0)),
        )


def _empty_tally() -> dict:
    return {"games": 0, "won": 0, "wrong_accusations": 0, "never_accused": 0, "last_game_id": None}


@dataclass
class LogbookHead:
    """What an identity reads back before a game: the mutable summary of
    its logbook, rewritten as each entry is absorbed.

    Parameters
    ----------
    identity : str
    serial : int
        The last entry absorbed (0 for a fresh head).
    tally : dict
        ``games``, ``won``, ``wrong_accusations``, ``never_accused``,
        ``last_game_id``, over the games with an entry.
    standing_instructions : list[str]
        The last entry's list, whole; an entry with none leaves the
        previous list standing.
    dossiers : dict[str, Dossier]
        Per opponent label; only the opponents present at a game are
        touched by its entry.
    flags : dict[str, list[int]]
        Flag -> serials of the entries carrying it.
    """

    identity: str
    serial: int = 0
    tally: dict = field(default_factory=_empty_tally)
    standing_instructions: list = field(default_factory=list)
    dossiers: dict = field(default_factory=dict)
    flags: dict = field(default_factory=dict)
    version: int = LOGBOOK_VERSION

    @classmethod
    def empty(cls, identity: str) -> "LogbookHead":
        return cls(identity=identity)

    def is_empty(self) -> bool:
        return (
            self.serial == 0 and not self.standing_instructions and not self.dossiers
            and self.tally.get("games", 0) == 0
        )

    def absorb(self, entry: LogbookEntry) -> None:
        """Fold one entry in: serial, tally, standing instructions, the
        dossiers of the opponents present, the flag index."""
        self.serial = max(self.serial, entry.serial)
        outcome = entry.outcome
        self.tally["games"] = self.tally.get("games", 0) + 1
        self.tally["won"] = self.tally.get("won", 0) + (1 if outcome.get("won") else 0)
        wrong = outcome.get("accused") and outcome.get("accusation_correct") is False
        self.tally["wrong_accusations"] = self.tally.get("wrong_accusations", 0) + (1 if wrong else 0)
        self.tally["never_accused"] = (
            self.tally.get("never_accused", 0) + (0 if outcome.get("accused") else 1)
        )
        self.tally["last_game_id"] = entry.game_id
        if entry.standing_instructions:
            self.standing_instructions = list(entry.standing_instructions)
        reads = {item["opponent"]: item["read"] for item in entry.dossiers}
        for label in entry.opponents():
            old = self.dossiers.get(label, Dossier())
            if label in reads:
                self.dossiers[label] = Dossier(
                    reads[label], old.games_together + 1, entry.date, entry.serial
                )
            else:
                self.dossiers[label] = Dossier(
                    old.read, old.games_together + 1, old.updated, old.serial
                )
        for flag in entry.flags:
            serials = self.flags.setdefault(flag, [])
            if entry.serial not in serials:
                serials.append(entry.serial)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "identity": self.identity,
            "serial": self.serial,
            "tally": dict(self.tally),
            "standing_instructions": list(self.standing_instructions),
            "dossiers": {label: d.to_dict() for label, d in self.dossiers.items()},
            "flags": {flag: list(serials) for flag, serials in self.flags.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LogbookHead":
        tally = _empty_tally()
        tally.update(data.get("tally", {}))
        return cls(
            identity=data["identity"],
            serial=int(data.get("serial", 0)),
            tally=tally,
            standing_instructions=list(data.get("standing_instructions", [])),
            dossiers={
                label: Dossier.from_dict(d) for label, d in data.get("dossiers", {}).items()
            },
            flags={flag: [int(s) for s in serials] for flag, serials in data.get("flags", {}).items()},
            version=int(data.get("version", LOGBOOK_VERSION)),
        )


# ---------------------------------------------------------------------
# Rendering: what a character reads
# ---------------------------------------------------------------------


def _share(n: int, fraction: float) -> int:
    """``ceil(n * fraction)`` guarded against float noise, at least 1."""
    if n <= 0:
        return 0
    return min(n, max(1, math.ceil(round(n * fraction, 9))))


def memory_counts(n_entries: int, depth: float) -> tuple:
    """``(indexed, full)``: how many of the most recent entries appear
    in the one-line index and how many in full at `depth`:
    none below 0, the whole index at 0.5, half the entries in full at
    0.75, everything at 1 (docs/phase7-plan.md, "Read-back").

    Raises
    ------
    ValueError
        If `depth` is outside [0, 1].
    """
    if not 0.0 <= depth <= 1.0:
        raise ValueError(f"memory depth must be in [0, 1], got {depth!r}")
    if depth <= 0.0 or n_entries <= 0:
        return 0, 0
    indexed = n_entries if depth >= 0.5 else _share(n_entries, depth / 0.5)
    full = 0 if depth <= 0.5 else _share(n_entries, (depth - 0.5) / 0.5)
    return indexed, full


def _versus(entry: LogbookEntry) -> str:
    opponents = entry.opponents()
    return f"as {entry.token} vs {', '.join(opponents)}" if opponents else f"as {entry.token}"


def render_index_line(entry: LogbookEntry) -> str:
    """One line for the index: serial, date, table, outcome, summary, flags."""
    line = f"- #{entry.serial:04d} ({entry.date}) {_versus(entry)}: {outcome_phrase(entry.outcome)}."
    if entry.summary:
        line += f" {entry.summary}"
    if entry.flags:
        line += f" [flags: {', '.join(entry.flags)}]"
    return line


def render_entry(entry: LogbookEntry, full: bool = False) -> str:
    """A whole entry as text, for the memory block and the CLI. The
    standing instructions and dossiers it carried are left out unless
    `full`: the head holds their current versions, and the memory block
    shows the head."""
    lines = [
        f"=== Entry #{entry.serial:04d}, {entry.date}, {_versus(entry)}: "
        f"{outcome_phrase(entry.outcome)} ===",
    ]
    if entry.title:
        lines.append(f"Title: {entry.title}")
    if entry.summary:
        lines.append(f"Summary: {entry.summary}")
    if entry.what_happened:
        lines.append(f"What happened: {entry.what_happened}")
    if entry.evaluations:
        lines.append("Evaluations:")
        for item in entry.evaluations:
            note = f" {item['notes']}" if item.get("notes") else ""
            lines.append(f"- {item['opponent']}: {item.get('evaluation', '')}{note}".rstrip())
    if entry.key_insights:
        lines.append("Key insights:")
        lines.extend(f"- {item}" for item in entry.key_insights)
    if entry.lessons_learned:
        lines.append("Lessons learned:")
        lines.extend(f"- {item}" for item in entry.lessons_learned)
    if entry.final_outcome:
        lines.append(f"Final outcome: {entry.final_outcome}")
    if entry.flags:
        lines.append(f"Flags: {', '.join(entry.flags)}")
    if full and entry.standing_instructions:
        lines.append("Standing instructions written:")
        lines.extend(f"- {item}" for item in entry.standing_instructions)
    if full and entry.dossiers:
        lines.append("Dossiers revised:")
        lines.extend(f"- {item['opponent']}: {item.get('read', '')}".rstrip() for item in entry.dossiers)
    return "\n".join(lines)


def render_head(head: LogbookHead, opponents=None) -> list:
    """The head as lines: the tally, the standing instructions, and the
    dossiers on `opponents` (every dossier when None)."""
    if head.is_empty():
        return []
    t = head.tally
    games = t.get("games", 0)
    lines = [
        f"From your logbook, written by you after earlier games "
        f"({games} game{'s' if games != 1 else ''}: won {t.get('won', 0)}, "
        f"{t.get('wrong_accusations', 0)} wrong accusation"
        f"{'s' if t.get('wrong_accusations', 0) != 1 else ''}, "
        f"never accused in {t.get('never_accused', 0)}):"
    ]
    if head.standing_instructions:
        lines.append("Standing instructions to yourself:")
        lines.extend(f"- {item}" for item in head.standing_instructions)
    labels = list(opponents) if opponents is not None else sorted(head.dossiers)
    for label in labels:
        dossier = head.dossiers.get(label)
        if dossier is None or not dossier.read:
            continue
        n = dossier.games_together
        lines.append(
            f"Your read on {label} ({n} game{'s' if n != 1 else ''} together, "
            f"revised after entry #{dossier.serial:04d}): {dossier.read}"
        )
    return lines


def render_memory(head: LogbookHead, entries: list, depth: float, opponents=None) -> str:
    """The memory block for a character at `depth` (its `memory` dial):
    `render_head`, then at depth > 0 an index of the most recent
    entries with the flags recurring across them, then above 0.5 the
    most recent entries in full (`memory_counts`). Entries are given
    most recent last. Empty string for an empty logbook.

    Parameters
    ----------
    head : LogbookHead
    entries : list[LogbookEntry]
        Every entry, ascending by serial.
    depth : float
        In [0, 1].
    opponents : sequence of str or None
        The labels at this table, whose dossiers to show; None shows
        every dossier (the CLI's view).
    """
    lines = render_head(head, opponents)
    entries = sorted(entries, key=lambda e: e.serial)
    indexed, full = memory_counts(len(entries), depth)
    if indexed:
        shown = entries[-indexed:]
        counts = Counter(flag for entry in shown for flag in entry.flags)
        if counts:
            recurring = ", ".join(
                f"{flag} ({n})" for flag, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
            )
            lines.append(f"Flags across these entries: {recurring}")
        lines.append(
            f"Entries #{shown[0].serial:04d} to #{shown[-1].serial:04d} of "
            f"{len(entries)}, most recent last:"
        )
        lines.extend(render_index_line(entry) for entry in shown)
    if full:
        lines.append("Full entries, most recent last:")
        lines.extend(render_entry(entry) for entry in entries[-full:])
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------
# The logbook over a store
# ---------------------------------------------------------------------


class Logbook:
    """One identity's logbook in a `RecordStore`.

    Parameters
    ----------
    store : RecordStore
    identity : str
        A `SeatRecord.label`; must be a safe path segment.
    """

    def __init__(self, store, identity: str) -> None:
        self.store = store
        self.identity = validate_run_id(identity)

    def __repr__(self) -> str:
        return f"Logbook({self.identity!r} in {self.store.describe()})"

    # -- head ---------------------------------------------------------

    def head(self) -> LogbookHead:
        """The stored head, or an empty one."""
        try:
            return LogbookHead.from_dict(self.store.get_doc(head_key(self.identity)))
        except KeyError:
            return LogbookHead.empty(self.identity)

    def save_head(self, head: LogbookHead) -> str:
        return self.store.put_doc(head_key(self.identity), head.to_dict())

    # -- entries ------------------------------------------------------

    def serials(self) -> list:
        """Serials of the stored entries, ascending."""
        names = self.store.list_docs(entries_prefix(self.identity))
        return sorted(int(name) for name in names if name.isdigit())

    def entry(self, serial: int) -> LogbookEntry:
        """One entry; `KeyError` if absent."""
        return LogbookEntry.from_dict(self.store.get_doc(entry_key(self.identity, serial)))

    def entries(self) -> list:
        """Every stored entry, ascending by serial."""
        return [self.entry(serial) for serial in self.serials()]

    def next_serial(self) -> int:
        serials = self.serials()
        return max(self.head().serial, serials[-1] if serials else 0) + 1

    def add_entry(self, entry: LogbookEntry) -> LogbookHead:
        """Store `entry`, fold it into the head, store the head; returns
        the new head.

        Raises
        ------
        ValueError
            If the entry belongs to another identity or reuses a serial.
        """
        if entry.identity != self.identity:
            raise ValueError(f"entry for {entry.identity!r} offered to {self.identity!r}'s logbook")
        if entry.serial in self.serials():
            raise ValueError(f"{self.identity} already has entry #{entry.serial:04d}")
        self.store.put_doc(entry_key(self.identity, entry.serial), entry.to_dict())
        head = self.head()
        head.absorb(entry)
        self.save_head(head)
        return head

    # -- method memory ------------------------------------------------

    def method(self) -> Optional[dict]:
        """The method's numeric memory document, or None."""
        try:
            return self.store.get_doc(method_key(self.identity))
        except KeyError:
            return None

    def save_method(self, document: dict) -> str:
        return self.store.put_doc(method_key(self.identity), document)

    # -- maintenance --------------------------------------------------

    def rebuild_head(self) -> LogbookHead:
        """Recompute the head from the entries alone and store it."""
        head = LogbookHead.empty(self.identity)
        for entry in self.entries():
            head.absorb(entry)
        self.save_head(head)
        return head

    def reset(self, keep_entries: bool = False) -> int:
        """Forget: the head and method memory go, and the entries too
        unless `keep_entries`. Returns how many documents were removed."""
        removed = 0
        removed += int(self.store.delete_doc(head_key(self.identity)))
        removed += int(self.store.delete_doc(method_key(self.identity)))
        if not keep_entries:
            for serial in self.serials():
                removed += int(self.store.delete_doc(entry_key(self.identity, serial)))
        return removed

    def exists(self) -> bool:
        """True if any document of this logbook is stored."""
        return bool(self.serials()) or not self.head().is_empty() or self.method() is not None

    # -- what a character reads ---------------------------------------

    def memory(self, depth: float, opponents=None) -> str:
        """`render_memory` of this logbook at `depth`; entries are only
        read from the store when the depth needs them."""
        head = self.head()
        entries = self.entries() if depth > 0.0 else []
        return render_memory(head, entries, depth, opponents)


def list_logbooks(store) -> list:
    """Identities with a logbook folder in `store`, sorted."""
    return store.list_folders(LOGBOOKS_PREFIX)
