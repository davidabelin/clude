"""Rebuild a finished game from its stored `GameRecord` (Phase 7a): the
engine's omniscient `GameState`, any seat's masked `ClueObservation` at
any point, and the same `Snapshot`s that
`clude_training.self_play.generate_snapshots` would have yielded for it.

`clude_storage.records` has promised since Phase 5d that "a seat's own
redacted view is rebuilt from `events`"; this is where that happens. A
record carries the deal, the seats and the ordered event log but not
positions or who is still active, so those are folded from the events:
a `MoveEvent` places its player, a `SuggestionEvent` also drags the
named suspect's token into the room (as `engine.resolve_suggestion`
does, without a move event of its own), and a wrong `AccusationEvent`
eliminates its accuser. Folding in event order reproduces the engine's
final state field for field (`tests/test_replay.py`).

Consumers: Phase 7's method memory (Mustard's training rows and White's
per-opponent counts come from `snapshots_from_record` and `seat_view`),
the debrief prompt, and later Phase 8's post-game replay of every
character's belief trace.
"""
from __future__ import annotations

from typing import Iterator, Optional

import clude_constraints
from clude_core import board
from clude_core.domain import SUSPECTS
from clude_core.events import AccusationEvent, MoveEvent, SuggestionEvent
from clude_core.state import ClueObservation, GameState
from clude_storage import GameRecord
from clude_training.self_play import DEFAULT_CHECKPOINTS, Snapshot, truncate_state


def state_from_record(record: GameRecord, k: Optional[int] = None) -> GameState:
    """The engine's `GameState` at the end of a recorded game, or, with
    `k`, as `self_play.truncate_state` would cut it after the first `k`
    suggestions (accusations cleared, everyone active, `turn` = `k`).

    Raises
    ------
    ValueError
        If `k` is outside ``0 .. n_suggestions``.
    """
    n = record.n_players
    seats = sorted(record.seats, key=lambda s: s.seat)
    suspects = [s.suspect for s in seats] if len(seats) == n else list(SUSPECTS[:n])
    positions = {p: board.start_position(suspects[p]) for p in range(n)}
    active = [True] * n
    suggestion_log = []
    accusation_log = []
    for event in record.events:
        if isinstance(event, MoveEvent):
            positions[event.player] = event.destination
        elif isinstance(event, SuggestionEvent):
            suggestion = event.suggestion
            suggestion_log.append(suggestion)
            for p, name in enumerate(suspects):
                if name == suggestion.suspect:
                    positions[p] = suggestion.room
                    break
        elif isinstance(event, AccusationEvent):
            accusation = event.accusation
            accusation_log.append(accusation)
            if not accusation.correct:
                active[accusation.accuser] = False
    state = GameState(
        suspects_in_play=suspects,
        hands={int(p): frozenset(cards) for p, cards in record.hands.items()},
        envelope=tuple(record.envelope),
        positions=positions,
        active=active,
        turn=record.turns,
        suggestion_log=suggestion_log,
        accusation_log=accusation_log,
    )
    if k is None:
        return state
    if not 0 <= k <= len(suggestion_log):
        raise ValueError(f"k={k} is outside 0..{len(suggestion_log)} for this record")
    return truncate_state(state, k)


def seat_view(record: GameRecord, seat: int, k: Optional[int] = None) -> ClueObservation:
    """`seat`'s masked observation of a recorded game, redacted exactly
    as the engine redacted it live (`ClueObservation.for_player`) and
    masked by the floor (`clude_constraints.observe`); with `k`, after
    the first `k` suggestions."""
    return clude_constraints.observe(state_from_record(record, k), seat)


def snapshots_from_record(
    record: GameRecord, checkpoints: tuple = DEFAULT_CHECKPOINTS
) -> Iterator[Snapshot]:
    """The `Snapshot`s `generate_snapshots` would have yielded for this
    game: one masked view per (checkpoint, viewer), each paired with the
    envelope. A game with no suggestions yields nothing."""
    state = state_from_record(record)
    total = len(state.suggestion_log)
    if total == 0:
        return
    for checkpoint in checkpoints:
        k = max(1, round(total * checkpoint))
        snap_state = truncate_state(state, k)
        for viewer in range(state.n_players):
            yield Snapshot(
                obs=clude_constraints.observe(snap_state, viewer),
                envelope=state.envelope,
                game_index=record.game_index,
                viewer=viewer,
                checkpoint=checkpoint,
            )
