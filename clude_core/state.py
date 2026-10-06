"""Omniscient GameState and the per-seat ClueObservation contract.

for_player redacts shown cards but leaves mask unset. Use
clude_constraints.observe to attach fresh deduction results. The mask type
is imported only under TYPE_CHECKING to avoid a core/constraints cycle.
Agents receive observations, never the full deal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from .board import Node
from .domain import Accusation, SUSPECTS, Suggestion

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
    # True for a seat whose token a suggestion moved into a room since its
    # last turn: it may stay there and suggest (board.py, Rules). Empty
    # for a state built without it (older tests, replay), which reads as
    # all False.
    summoned: list[bool] = field(default_factory=list)
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
    suspects_in_play: tuple[str, ...] = ()

    @property
    def suspects(self) -> tuple[str, ...]:
        """The suspect token in each seat, in seat order. An observation
        built by hand without `suspects_in_play` (older tests) gets the
        first `n_players` suspects, which is what the engine seated
        before characters were locked to their own tokens."""
        return self.suspects_in_play or tuple(SUSPECTS[: self.n_players])

    @staticmethod
    def for_player(state: GameState, viewer: int) -> "ClueObservation":
        """Build viewer's redacted observation, leaving mask unset.

        Reuse suggestions visible to the suggester/refuter; copy others with
        card_shown=None. Use clude_constraints.observe to attach deductions.
        """
        redacted = []
        for s in state.suggestion_log:
            if s.card_shown is None or viewer in (s.suggester, s.refuter):
                redacted.append(s)
                continue
            redacted.append(
                Suggestion(
                    suggester=s.suggester,
                    suspect=s.suspect,
                    weapon=s.weapon,
                    room=s.room,
                    refuter=s.refuter,
                    shown_to=s.shown_to,
                    card_shown=None,
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
            suspects_in_play=tuple(state.suspects_in_play),
        )
