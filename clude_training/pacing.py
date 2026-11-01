"""Measure the web reaction queue's pacing offline, without changing it.

A saved game's events are replayed, one at a time, through a real
`clude_web.chat.Reactions` instance sitting on a minimal table adapter,
with a backend that always answers a remark and a clock that never makes
anyone wait. What the harness counts is what the live code never
records: how often a trigger finds the queue already full, how many
seats the sorted-order scan never reaches, how many queued reactions a
turn change drops, how many lines a turn and a game actually carry
(the caps are checked only when the floor is opened, so a turn can
carry ``PER_TURN + MAX_QUEUED - 1`` and a game ``PER_GAME + 1``), how
deep reply chains run, and who gets to speak, by seat position and by
character.

Nothing here alters `clude_web.chat`; the queue's constants are read,
not set, and the only patched names are its clock and its draw, so the
mechanism measured is the one shipped. Model seats are seeded exactly
as `clude_training.table.build_table` seeds them at a live table.
"""
from __future__ import annotations

import json
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from typing import Optional

from clude_agents import build_character
from clude_agents.personality import PRESETS
from clude_core.events import AccusationEvent, GameOverEvent, MoveEvent, RemarkEvent, SuggestionEvent
from clude_llm import LLMCharacter, LLMResult, LLMSettings, ScriptedBackend
from clude_storage import GameRecord
from clude_training.replay import state_from_record
from clude_web import chat
from clude_web.chat import MAX_QUEUED, PER_GAME, PER_TURN, REACTION, Reactions
from clude_web.users import display_name

ON_TURN_ABOUTS = ("move", "suggest", "accuse", "show")
"""`RemarkEvent.about` values of a seat's own on-turn line."""

COST_PER_LINE = 1.6490 / 210
"""Dollars one off-turn line cost in Phase 14's chattiness screen at the
0.5 preset ($1.6490 for 210 lines); a projection, not a measurement."""


class ReplyBackend(ScriptedBackend):
    """Answers every remark request with a line, so a draw that joins is
    a line that is served; on-turn requests never arrive here."""

    name = "pacing-reply"
    last_refusal = None

    def __init__(self, line: str = "Noted.") -> None:
        super().__init__([])
        self.line = line

    def complete(self, request):
        self.requests.append(request)
        self.calls += 1
        return LLMResult(text=json.dumps({"say": self.line}), stop_reason="end_turn", model=self.name)


@dataclass
class ReplayTable:
    """The slice of a table `Reactions` reads: the model seats, a growing
    event log, the engine state at the replayed moment, and `remark`."""

    record: GameRecord
    wrappers: dict
    labels: list
    events: list = field(default_factory=list)
    finished: bool = False
    turn: int = 0
    suggestions: int = 0
    _states: dict = field(default_factory=dict)

    @property
    def state(self):
        base = self._states.get(self.suggestions)
        if base is None:
            base = state_from_record(self.record, self.suggestions)
            self._states[self.suggestions] = base
        return replace(base, turn=self.turn)

    def names(self) -> list:
        """What the table screen would call each seat: the token, and a
        person's capitalised display name after it (`tables.seat_names`)."""
        out = []
        for seat in sorted(self.record.seats, key=lambda s: s.seat):
            if seat.kind == "human":
                out.append(f"{seat.suspect} ({display_name(seat.label)})")
            else:
                out.append(seat.suspect)
        return out

    def remark(self, seat: int, text: str, about: str, audit=None) -> None:
        event = RemarkEvent(self.turn, seat, text, about)
        self.events.append(event)
        for other, wrapper in self.wrappers.items():
            if other != seat:
                wrapper.hear(event)


def wrappers_for(record: GameRecord, chattiness: Optional[float] = None, line: str = "Noted.") -> dict:
    """Model seats for a replay: every ``llm`` seat of a web record, or
    every character seat of an arena record (which has no model seats of
    its own). Each gets its current preset, or the preset at `chattiness`,
    and is reset with the game's seed exactly as a live table would."""
    seats = sorted(record.seats, key=lambda s: s.seat)
    kinds = {seat.kind for seat in seats}
    wanted = "llm" if "llm" in kinds else "character"
    labels = [seat.label for seat in seats]
    wrappers = {}
    for seat in seats:
        if seat.kind != wanted or seat.label not in PRESETS:
            continue
        profile = PRESETS[seat.label]
        if chattiness is not None:
            profile = profile.with_dials(chattiness=chattiness)
        wrapper = LLMCharacter(
            build_character(seat.label, profile=profile), ReplyBackend(line),
            settings=LLMSettings(debrief=False),
        )
        wrapper.reset(record.seed)
        wrapper.new_game(labels)
        wrappers[seat.seat] = wrapper
    return wrappers


def _actor_of(event) -> Optional[int]:
    if isinstance(event, SuggestionEvent):
        return event.suggestion.suggester
    if isinstance(event, AccusationEvent):
        return event.accusation.accuser
    if isinstance(event, RemarkEvent):
        return event.seat
    if isinstance(event, MoveEvent):
        return event.player
    return None


def _trigger_kind(event) -> Optional[str]:
    """The opportunity an event opens in `Reactions.scan`, or None."""
    if isinstance(event, SuggestionEvent):
        return "suggestion"
    if isinstance(event, AccusationEvent):
        return "accusation"
    if isinstance(event, RemarkEvent):
        if event.about == REACTION:
            return None
        return "chat" if event.about == "chat" else "on_turn_remark"
    return None


@dataclass
class Tally:
    """One replay's counts. Seats are indexed by their seat number; the
    `position` maps give the same counts by rank in the sorted scan."""

    game: str
    seats: int
    turns: int
    model_seats: list
    chattiness: dict
    opportunities: Counter = field(default_factory=Counter)
    turn_cap_refusals: int = 0
    game_cap_refusals: int = 0
    triggers_full: int = 0
    skipped_by_break: Counter = field(default_factory=Counter)
    eligible: Counter = field(default_factory=Counter)
    draws: Counter = field(default_factory=Counter)
    joined: Counter = field(default_factory=Counter)
    served: Counter = field(default_factory=Counter)
    stale_drops: int = 0
    served_per_turn: Counter = field(default_factory=Counter)
    depth: Counter = field(default_factory=Counter)
    longest_chain: int = 0
    calls: int = 0

    def to_dict(self) -> dict:
        served_total = sum(self.served.values())
        position = {str(i): seat for i, seat in enumerate(sorted(self.model_seats))}
        by_position = lambda counter: {  # noqa: E731
            rank: counter.get(seat, 0) for rank, seat in position.items()
        }
        return {
            "game": self.game,
            "seats": self.seats,
            "turns": self.turns,
            "model_seats": sorted(self.model_seats),
            "chattiness": self.chattiness,
            "opportunities": dict(sorted(self.opportunities.items())),
            "turn_cap_refusals": self.turn_cap_refusals,
            "game_cap_refusals": self.game_cap_refusals,
            "triggers_full": self.triggers_full,
            "skipped_by_break": {str(k): v for k, v in sorted(self.skipped_by_break.items())},
            "eligible": {str(k): v for k, v in sorted(self.eligible.items())},
            "draws": {str(k): v for k, v in sorted(self.draws.items())},
            "joined": {str(k): v for k, v in sorted(self.joined.items())},
            "served": {str(k): v for k, v in sorted(self.served.items())},
            "served_total": served_total,
            "served_by_position": by_position(self.served),
            "eligible_by_position": by_position(self.eligible),
            "draws_by_position": by_position(self.draws),
            "skipped_by_position": by_position(self.skipped_by_break),
            "stale_drops": self.stale_drops,
            "served_per_turn": {str(k): v for k, v in sorted(self.served_per_turn.items())},
            "turns_at_three_or_more": sum(v for k, v in self.served_per_turn.items() if k >= 3),
            "depth": {str(k): v for k, v in sorted(self.depth.items())},
            "longest_chain": self.longest_chain,
            "reached_game_cap": served_total >= PER_GAME,
            "calls": self.calls,
            "projected_cost": round(served_total * COST_PER_LINE, 4),
        }


class _Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        self.t += 1.0
        return self.t


@contextmanager
def _instrumented(reactions: Reactions, table: ReplayTable, tally: Tally, kind_of: dict):
    """Patch the queue's clock and draw, and wrap `opportunity` so each
    call's eligibility, free slots and draws are counted before the real
    method runs. Restored on exit."""
    original_now, original_delay, original_joins = chat.now, chat.delay, chat.joins
    chat.now = _Clock()
    chat.delay = lambda rng: 0.0
    by_rng = {id(w.rng): seat for seat, w in table.wrappers.items()}
    drawn: list = []

    def joins(rng, probability):
        seat = by_rng.get(id(rng))
        outcome = original_joins(rng, probability)
        drawn.append(seat)
        tally.draws[seat] += 1
        if outcome:
            tally.joined[seat] += 1
        return outcome

    chat.joins = joins
    real_opportunity = reactions.opportunity

    def opportunity(actor, trigger, depth=0):
        kind = "reply" if depth else kind_of["current"]
        if table.finished or reactions.total >= PER_GAME:
            tally.game_cap_refusals += 1
            return real_opportunity(actor, trigger, depth)
        if reactions.served_turn.get(table.turn, 0) >= PER_TURN:
            tally.turn_cap_refusals += 1
            return real_opportunity(actor, trigger, depth)
        tally.opportunities[kind] += 1
        queued = {r.seat for r in reactions.queue}
        eligible = [
            seat for seat, wrapper in sorted(table.wrappers.items())
            if seat != actor and seat not in queued and not chat.refusing(wrapper)
        ]
        free = max(0, MAX_QUEUED - len(reactions.queue))
        if eligible and free == 0:
            tally.triggers_full += 1
        for seat in eligible:
            tally.eligible[seat] += 1
        # The scan breaks once enough seats have joined, so which seats
        # never draw depends on the draws before them: count the eligible
        # seats whose RNG this call did not consult.
        drawn.clear()
        queued_now = real_opportunity(actor, trigger, depth)
        for seat in eligible:
            if seat not in drawn:
                tally.skipped_by_break[seat] += 1
        return queued_now

    reactions.opportunity = opportunity
    try:
        yield
    finally:
        chat.now, chat.delay, chat.joins = original_now, original_delay, original_joins


def measure(
    record: GameRecord,
    *,
    chattiness: Optional[float] = None,
    patient: bool = True,
    line: str = "Noted.",
) -> dict:
    """Replay `record` through a real `Reactions` queue and count.

    Parameters
    ----------
    record : GameRecord
        A saved game. Its own ``reaction`` remarks are skipped (they were
        the live queue's output); every other event is an input.
    chattiness : float or None
        None plays each seat at its current preset; a value sets every
        model seat's dial to it.
    patient : bool
        True drains the queue after every event, which is what
        `TableRegistry.work` does while it answers ``waiting``: a bot or
        model turn never moves past a queued reaction. False leaves the
        queue alone after a person's own events, so the next turn's
        `due()` drops what was queued, an upper bound on the stale drops a
        quick human can cause.
    """
    wrappers = wrappers_for(record, chattiness, line)
    seats = sorted(record.seats, key=lambda s: s.seat)
    labels = [seat.label for seat in seats]
    table = ReplayTable(record=record, wrappers=wrappers, labels=labels)
    reactions = Reactions(table, table.names)
    tally = Tally(
        game=f"{record.run_id}/{record.game_index:05d}",
        seats=record.n_players,
        turns=record.turns,
        model_seats=sorted(wrappers),
        chattiness={labels[s]: wrappers[s].profile.chattiness for s in wrappers},
    )
    human_seats = {seat.seat for seat in seats if seat.kind == "human"}
    kind_of = {"current": None}
    chain = 0

    def drain():
        nonlocal chain
        while True:
            reaction = reactions.due()
            if reaction is None:
                return
            before = reactions.total
            said = reactions.serve(reaction)
            if said:
                tally.served[reaction.seat] += 1
                tally.depth[reaction.depth] += 1
                chain = max(chain, reaction.depth + 1)
            elif reactions.total == before:
                pass  # silence: no line, no count

    with _instrumented(reactions, table, tally, kind_of):
        for event in record.events:
            if isinstance(event, RemarkEvent) and event.about == REACTION:
                continue
            if event.turn != table.turn:
                table.turn = event.turn
                before = len(reactions.queue)
                reactions.due()
                tally.stale_drops += before - len(reactions.queue)
            if isinstance(event, GameOverEvent):
                table.finished = True
            table.events.append(event)
            if isinstance(event, SuggestionEvent):
                table.suggestions += 1
            kind_of["current"] = _trigger_kind(event)
            reactions.scan()
            if patient or _actor_of(event) not in human_seats:
                drain()
        drain()
    tally.longest_chain = chain
    tally.served_per_turn = Counter(reactions.served_turn.values())
    tally.calls = sum(w.backend.calls for w in wrappers.values())
    return tally.to_dict()


def as_played(record: GameRecord) -> dict:
    """What the stored game shows: its off-turn lines per turn and per seat."""
    seats = sorted(record.seats, key=lambda s: s.seat)
    labels = {seat.seat: seat.label for seat in seats}
    per_turn: Counter = Counter()
    per_seat: Counter = Counter()
    for event in record.events:
        if isinstance(event, RemarkEvent) and event.about == REACTION:
            per_turn[event.turn] += 1
            per_seat[event.seat] += 1
    histogram = Counter(per_turn.values())
    return {
        "game": f"{record.run_id}/{record.game_index:05d}",
        "seats": record.n_players,
        "turns": record.turns,
        "reactions": sum(per_turn.values()),
        "turns_with": {str(k): v for k, v in sorted(histogram.items())},
        "per_seat": {str(k): v for k, v in sorted(per_seat.items())},
        "per_character": {labels[k]: v for k, v in sorted(per_seat.items())},
    }


def pool(tallies: list) -> dict:
    """Sum a condition's per-game tallies into one row."""
    keys = (
        "turn_cap_refusals", "game_cap_refusals", "triggers_full", "stale_drops",
        "served_total", "calls", "turns_at_three_or_more",
    )
    out = {key: sum(t[key] for t in tallies) for key in keys}
    out["games"] = len(tallies)
    out["opportunities"] = dict(sum((Counter(t["opportunities"]) for t in tallies), Counter()))
    out["opportunities_total"] = sum(out["opportunities"].values())
    out["draws"] = sum(sum(t["draws"].values()) for t in tallies)
    out["joined"] = sum(sum(t["joined"].values()) for t in tallies)
    out["skipped_by_break"] = sum(sum(t["skipped_by_break"].values()) for t in tallies)
    out["depth"] = dict(sorted(sum((Counter({int(k): v for k, v in t["depth"].items()}) for t in tallies), Counter()).items()))
    out["depth_two_or_deeper"] = sum(v for k, v in out["depth"].items() if k >= 2)
    out["served_per_turn"] = dict(sorted(sum((Counter({int(k): v for k, v in t["served_per_turn"].items()}) for t in tallies), Counter()).items()))
    out["games_at_cap"] = sum(1 for t in tallies if t["reached_game_cap"])
    out["longest_chain"] = max((t["longest_chain"] for t in tallies), default=0)
    for name in ("eligible", "draws", "served", "skipped"):
        out[f"{name}_by_position"] = dict(sum((Counter(t[f"{name}_by_position"]) for t in tallies), Counter()))
    out["projected_cost"] = round(out["served_total"] * COST_PER_LINE, 4)
    return out


__all__ = ["COST_PER_LINE", "ReplayTable", "ReplyBackend", "Tally", "as_played", "measure", "pool", "wrappers_for"]
