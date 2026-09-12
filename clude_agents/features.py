"""Shared, deterministic feature extraction and scoring for the
personality layer's sampled decisions (Phase 5c).

Room choice is not the same problem as belief (docs/architecture.md):
this module is the *shared arithmetic* half of that split -- per-choice
numbers computed from the agent's own belief and the board -- while the
pick itself is per-character (`AgentProtocol.choose_destination`, whose
default `SeededAgentMixin` implementation is `pick_destination` below,
overridable by any agent).

No opponent-danger feature yet: docs/phase5-plan.md defers `w_danger`
until a measured signal exists.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from random import Random
from typing import Optional

from clude_core import board
from clude_core.board import room_distances
from clude_core.domain import ROOMS
from clude_core.engine import MoveChoice
from clude_core.state import ClueObservation

from .personality import Profile

__all__ = [
    "DISTANCE_DISCOUNT",
    "ChoiceFeatures",
    "pick_destination",
    "room_distances",
    "room_features",
    "sample_softmax",
    "score_choices",
]

DISTANCE_DISCOUNT = 0.7
"""Per-step discount applied to a room's value when a hallway choice
only heads toward it: a room three steps away is worth 0.7^3 of the
same room reached now."""

GREEDY_TEMPERATURE = 1e-9
"""Below this, `sample_softmax` is an argmax with uniform tie-breaking."""


@dataclass(frozen=True)
class ChoiceFeatures:
    """Per-choice numbers for one legal movement option.

    Parameters
    ----------
    choice : MoveChoice
        The option these features describe.
    room : str or None
        The room this choice lands in *this turn*, or None for a hallway
        cell.
    target : str
        The room this choice is heading for: the landing room itself, or
        for a hallway cell the room with the best distance-discounted
        value from there.
    information : float
        The agent's masked P(target's card is the envelope's), times
        `DISTANCE_DISCOUNT` per step still to go. In [0, 1].
    proximity : float
        1.0 when landing in a room (a suggestion this turn), else
        ``1 / (1 + steps to the nearest room)``. In (0, 1].
    steps_to_target : int
    """

    choice: MoveChoice
    room: Optional[str]
    target: str
    information: float
    proximity: float
    steps_to_target: int


def _best_target(p: dict, distances: dict) -> str:
    """The room with the best distance-discounted value; ties go to the
    nearer room, then to name order, so the choice is deterministic."""
    return max(ROOMS, key=lambda r: (p[r] * DISTANCE_DISCOUNT ** distances[r], -distances[r], r))


def room_features(obs: ClueObservation, belief, choices: list) -> list:
    """Feature vector per legal move, in the same order as `choices`.

    Parameters
    ----------
    obs : ClueObservation
        Unused today beyond documenting the perspective; reserved for
        the danger features docs/phase5-plan.md defers.
    belief : ClueBelief
        This agent's own masked belief -- `information` reads its room
        probabilities straight off it, no new computation.
    choices : list[MoveChoice]
        From `engine.legal_moves`; a ``"stay"`` choice carries its room.

    Returns
    -------
    list[ChoiceFeatures]
    """
    del obs  # perspective is implicit in `belief`; kept for the future danger features
    p = belief.probabilities
    result = []
    for choice in choices:
        landing = board.room_of(choice.destination)
        if landing is not None:
            result.append(ChoiceFeatures(choice, landing, landing, p[landing], 1.0, 0))
            continue
        distances = room_distances(choice.destination)
        target = _best_target(p, distances)
        nearest = min(distances.values())
        result.append(
            ChoiceFeatures(
                choice=choice,
                room=None,
                target=target,
                information=p[target] * DISTANCE_DISCOUNT ** distances[target],
                proximity=1.0 / (1.0 + nearest),
                steps_to_target=distances[target],
            )
        )
    return result


def score_choices(features: list, profile: Profile) -> list:
    """`curiosity`-weighted blend of information and proximity per choice,
    in [0, 1]: 1 = chase the most probable room, 0 = get into any room."""
    c = profile.curiosity
    return [c * f.information + (1.0 - c) * f.proximity for f in features]


def sample_softmax(scores: list, temperature: float, rng: Random) -> int:
    """Index of one option drawn from softmax(scores / temperature).

    Parameters
    ----------
    scores : list[float]
        Non-empty. Meant to be on a [0, 1] scale so one temperature
        means the same thing across decisions.
    temperature : float
        >= 0. At or below `GREEDY_TEMPERATURE` this is an argmax with a
        uniform draw among exact ties; otherwise higher is more random.
    rng : random.Random
        The caller's seeded RNG (never the engine's).

    Raises
    ------
    ValueError
        If `scores` is empty.
    """
    if not scores:
        raise ValueError("sample_softmax needs at least one score")
    top = max(scores)
    if temperature <= GREEDY_TEMPERATURE:
        best = [i for i, s in enumerate(scores) if s >= top - 1e-12]
        return rng.choice(best)
    weights = [math.exp((s - top) / temperature) for s in scores]
    return rng.choices(range(len(scores)), weights=weights, k=1)[0]


def pick_destination(features: list, profile: Profile, rng: Random) -> MoveChoice:
    """The default room-choice decision: softmax over `score_choices`."""
    scores = score_choices(features, profile)
    return features[sample_softmax(scores, profile.temperature, rng)].choice
