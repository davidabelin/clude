"""Uniform-random dumb bot -- Phase 1's only player. No inference.

Implements `engine.RandomBotProtocol`. Suggestion and accusation
probabilities are arbitrary constants tuned only so headless test games
exercise every code path (refutation, elimination, a correct accusation)
without an implausible number of turns; they carry no game-design meaning.
"""
from __future__ import annotations

import random
from typing import Optional

from .domain import ROOMS, SUSPECTS, WEAPONS
from .engine import MoveChoice

SUGGEST_PROBABILITY = 0.9
ACCUSE_PROBABILITY = 0.03


class RandomBot:
    def choose_movement(self, choices: list[MoveChoice], rng: random.Random) -> MoveChoice:
        return rng.choice(choices)

    def choose_suggestion(
        self, room: str, own_hand: frozenset[str], rng: random.Random
    ) -> Optional[tuple[str, str]]:
        if rng.random() > SUGGEST_PROBABILITY:
            return None
        return (rng.choice(SUSPECTS), rng.choice(WEAPONS))

    def choose_accusation(self, rng: random.Random) -> Optional[tuple[str, str, str]]:
        if rng.random() > ACCUSE_PROBABILITY:
            return None
        return (rng.choice(SUSPECTS), rng.choice(WEAPONS), rng.choice(ROOMS))

    def choose_card_to_show(self, candidates: list[str], rng: random.Random) -> str:
        return rng.choice(candidates)
