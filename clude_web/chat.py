"""Off-turn talk at a web table (Phase 8.3b, docs/phase8-plan.md 4.3).

An *opportunity* opens whenever something worth answering lands in the
event log: a line a person typed, a character's on-turn remark, a
suggestion resolving, an accusation. Each model seat other than the
actor joins with probability `chattiness` on its wrapper's own RNG (the
dial gating participation, as `CLAUDE.md` proposes), squared for a reply
to a reply so a conversation tails off. Of those that want to speak at
most `MAX_QUEUED` are queued, each due a few seconds later, and
`TableRegistry.work` serves one due reaction per request, so replies
arrive one at a time a few seconds apart and the table reads at a human
pace; bot turns wait while a reaction is queued, so the chatter lands
before the next move. A queued reaction is dropped once the turn has
moved on. `PER_TURN` and `PER_GAME` cap the lines, and the table's
dollar budget bounds the rest.

The queue lives in memory only. A served line is a ``reaction`` entry
(`TableGame.remark`) and so rebuilds exactly; what was still queued on a
cold instance is simply gone, which a table with people at it accepts:
the past is exact, the future may branch.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

import clude_constraints
from clude_core.events import AccusationEvent, RemarkEvent, SuggestionEvent

from . import replay_data

MAX_QUEUED = 2
"""Reactions queued at once, over every open opportunity."""

PER_TURN = 2
"""Off-turn lines served in one turn."""

PER_GAME = 40
"""Off-turn lines served in one game."""

DELAY = (2.0, 8.0)
"""Seconds a reaction waits before it is due, drawn uniformly."""

REACTION = "reaction"
"""The `RemarkEvent.about` of a served line."""


def now() -> float:
    return time.monotonic()


def delay(rng) -> float:
    return rng.uniform(*DELAY)


def joins(rng, probability: float) -> bool:
    return rng.random() < probability


@dataclass
class Reaction:
    seat: int
    due: float
    turn: int
    trigger: str
    depth: int = 0


class Reactions:
    """The off-turn talk of one game: the queue, the caps, and the scan
    of the event log that opens opportunities.

    Parameters
    ----------
    game : TableGame
        With `wrappers` (the model seats), `state`, `events`, `remark`
        and `finished`.
    names_of : Callable[[], list]
        A label per seat, as the table screen shows them; called late,
        since the names are the table module's to make.
    """

    def __init__(self, game, names_of: Callable[[], list]) -> None:
        self.game = game
        self.names_of = names_of
        self.queue: list = []
        self.served_turn: dict = {}
        self.total = 0
        self._scanned = 0

    @property
    def pending(self) -> bool:
        return bool(self.queue)

    def opportunity(self, actor: Optional[int], trigger: str, depth: int = 0) -> list:
        """Open the floor: each model seat but `actor` draws whether to
        speak; the takers are queued, up to `MAX_QUEUED` in all. Returns
        the seats queued."""
        game = self.game
        if game.finished or self.total >= PER_GAME:
            return []
        turn = game.state.turn
        if self.served_turn.get(turn, 0) >= PER_TURN:
            return []
        queued = []
        for seat, wrapper in sorted(game.wrappers.items()):
            if seat == actor or any(r.seat == seat for r in self.queue):
                continue
            if len(self.queue) + len(queued) >= MAX_QUEUED:
                break
            probability = wrapper.profile.chattiness ** (depth + 1)
            if joins(wrapper.rng, probability):
                queued.append(Reaction(seat, now() + delay(wrapper.rng), turn, trigger, depth))
        self.queue.extend(queued)
        return [r.seat for r in queued]

    def scan(self) -> None:
        """Open an opportunity for every event since the last scan that
        deserves one: a chat line, an on-turn remark, a suggestion
        resolving, an accusation. Served reactions open their own reply
        opportunity in `serve`, so they are skipped here."""
        game = self.game
        events = game.events
        if self._scanned >= len(events):
            return
        names = self.names_of()
        for event in events[self._scanned:]:
            if isinstance(event, SuggestionEvent):
                actor = event.suggestion.suggester
                trigger = replay_data.describe_event(event, names, reveal=False)[1]
            elif isinstance(event, AccusationEvent):
                actor = event.accusation.accuser
                trigger = replay_data.describe_event(event, names, reveal=False)[1]
            elif isinstance(event, RemarkEvent) and event.about != REACTION:
                actor = event.seat
                trigger = f'{names[event.seat]} said: "{event.text}"'
            else:
                continue
            self.opportunity(actor, trigger)
        self._scanned = len(events)

    def due(self) -> Optional[Reaction]:
        """The first reaction whose time has come, after dropping any
        the game has moved past."""
        turn = self.game.state.turn
        self.queue = [r for r in self.queue if r.turn == turn]
        moment = now()
        for reaction in self.queue:
            if reaction.due <= moment:
                return reaction
        return None

    def serve(self, reaction: Reaction) -> Optional[str]:
        """Ask the seat's model for its line and, if it has one, say it at
        the table (a ``reaction`` entry, heard by every other speaker) and
        open the floor for a reply. Returns the line, or None."""
        if reaction in self.queue:
            self.queue.remove(reaction)
        game = self.game
        wrapper = game.wrappers.get(reaction.seat)
        if wrapper is None or game.finished:
            return None
        names = self.names_of()
        obs = clude_constraints.observe(game.state, reaction.seat)
        text = wrapper.react(obs, reaction.trigger, names)
        if not text:
            return None
        game.remark(reaction.seat, text, REACTION)
        self._scanned = len(game.events)
        turn = game.state.turn
        self.served_turn[turn] = self.served_turn.get(turn, 0) + 1
        self.total += 1
        self.opportunity(reaction.seat, f'{names[reaction.seat]} said: "{text}"', depth=reaction.depth + 1)
        return text


__all__ = ["DELAY", "MAX_QUEUED", "PER_GAME", "PER_TURN", "REACTION", "Reaction", "Reactions"]
