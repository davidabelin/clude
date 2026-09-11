"""`GameState` (engine-internal, omniscient) and `ClueObservation` (the
per-player-perspective contract every future agent consumes).

`ClueObservation.mask` carries the deduction floor's `ConstraintResult`
(Phase 3, `clude_constraints`). It defaults to `None` here rather than
being required, purely to avoid a circular import: `clude_constraints`
already depends on `clude_core` (for `ClueObservation` itself), so
`clude_core` cannot import it back at runtime -- the `ConstraintResult`
import below is `TYPE_CHECKING`-only. `ClueObservation.for_player` never
populates `mask`; use `clude_constraints.observe(state, viewer)` to get a
fully masked observation. By convention every observation an agent's
`select_action` receives has `mask` populated -- see `clude_agents/base.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from .board import Node
from .domain import Accusation, Suggestion

if TYPE_CHECKING:
    from clude_constraints import ConstraintResult


@dataclass
class GameState:
    """Full, omniscient game state. Lives only inside the engine -- no
    agent ever sees this directly."""

    suspects_in_play: list[str]
    hands: dict[int, frozenset[str]]
    envelope: tuple[str, str, str]
    positions: dict[int, Node]
    active: list[bool]
    turn: int = 0
    suggestion_log: list[Suggestion] = field(default_factory=list)
    accusation_log: list[Accusation] = field(default_factory=list)

    @property
    def n_players(self) -> int:
        return len(self.suspects_in_play)

    def hand_sizes(self) -> dict[int, int]:
        return {p: len(h) for p, h in self.hands.items()}


@dataclass(frozen=True)
class ClueObservation:
    """One player's view of the game: their own hand, every suggestion
    (with `card_shown` redacted unless they were the suggester or the
    refuter), and every accusation. Built fresh each time via `for_player`
    -- never mutated or cached, so it can never go stale.
    """

    n_players: int
    my_index: int
    own_hand: frozenset[str]
    active_players: tuple[bool, ...]
    hand_sizes: dict[int, int]
    suggestion_log: tuple[Suggestion, ...]
    accusation_log: tuple[Accusation, ...]
    turn: int
    mask: "Optional[ConstraintResult]" = None

    @staticmethod
    def for_player(state: GameState, viewer: int) -> "ClueObservation":
        redacted = []
        for s in state.suggestion_log:
            visible_card = (
                s.card_shown if viewer in (s.suggester, s.refuter) else None
            )
            redacted.append(
                Suggestion(
                    suggester=s.suggester,
                    suspect=s.suspect,
                    weapon=s.weapon,
                    room=s.room,
                    refuter=s.refuter,
                    shown_to=s.shown_to,
                    card_shown=visible_card,
                )
            )
        return ClueObservation(
            n_players=state.n_players,
            my_index=viewer,
            own_hand=state.hands[viewer],
            active_players=tuple(state.active),
            hand_sizes=state.hand_sizes(),
            suggestion_log=tuple(redacted),
            accusation_log=tuple(state.accusation_log),
            turn=state.turn,
        )
