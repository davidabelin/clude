"""Uniform-random PlayerProtocol implementation for exercising rules.

Decision probabilities are test-data choices, not inference or tuned
strategy. RandomBot draws from the engine RNG. Use FloorBot for purposeful
self-play that gathers information and ends by deduction.
"""
from __future__ import annotations

import random
from typing import Optional

from .domain import ROOMS, SUSPECTS, WEAPONS
from .engine import MoveChoice
from .state import ClueObservation

SUGGEST_PROBABILITY = 0.9
ACCUSE_PROBABILITY = 0.03


class RandomBot:
    name = "random"

    def choose_movement(
        self, obs: ClueObservation, choices: list[MoveChoice], rng: random.Random
    ) -> MoveChoice:
        return rng.choice(choices)

    def choose_suggestion(
        self, obs: ClueObservation, room: str, rng: random.Random
    ) -> Optional[tuple[str, str]]:
        if rng.random() > SUGGEST_PROBABILITY:
            return None
        return (rng.choice(SUSPECTS), rng.choice(WEAPONS))

    def choose_accusation(
        self, obs: ClueObservation, rng: random.Random
    ) -> Optional[tuple[str, str, str]]:
        if rng.random() > ACCUSE_PROBABILITY:
            return None
        return (rng.choice(SUSPECTS), rng.choice(WEAPONS), rng.choice(ROOMS))

    def choose_card_to_show(
        self, obs: ClueObservation, candidates: list[str], shown_to: int, rng: random.Random
    ) -> str:
        return rng.choice(candidates)
