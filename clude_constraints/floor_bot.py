"""`FloorBot`: a characterless player that acts on the deduction floor
alone -- Phase 5's standard self-play opponent (docs/phase5-plan.md,
section 4.1).

No belief method and no personality, so it is still "dumb" in the
six-methods sense, but unlike `clude_core.bots.RandomBot` it never
wastes a suggestion on a card it holds or one the floor has already
located, it heads for rooms the floor has not located yet, and it
accuses exactly when the floor has proven the envelope, never
otherwise. Its games therefore carry information and end by deduction,
which is what Mustard's training data, the benchmark's snapshots, and
the arena's fill seats all need. It is also the "does a character beat
a purely logical player" baseline, the way `uniform` is the belief
baseline in `clude_training.benchmark`.

Movement deviates from the plan's "uniform over legal moves", which
was measured not to work: suggesting drags the named suspect's token
into the suggester's room, so a table of uniform movers piles up in one
room that some player holds, and every later suggestion there is
refuted by the same player with the same card -- the floor plateaus
exactly as it does in `RandomBot` games (see the convergence note in
docs/cli.md). So a `FloorBot` prefers a legal move that lands in an
*open* room (one the floor has not located); failing that, the move
that gets closest to one; and once every room is located, a room
nobody else can refute (the envelope's or its own), where a suggestion
tests suspect and weapon cleanly. Uniform among ties, and uniform over
everything only when no room qualifies.

Implements `clude_core.engine.PlayerProtocol` and needs a masked
observation: run it with ``observer=clude_constraints.observe``.
"""
from __future__ import annotations

import random
from typing import Any, Optional

from clude_core import board
from clude_core.domain import ROOMS, SUSPECTS, WEAPONS
from clude_core.engine import MoveChoice
from clude_core.state import ClueObservation

from .propagator import ENVELOPE


class FloorBot:
    """Uniform over what the floor still leaves open; accuses only on proof.

    Parameters
    ----------
    rng : random.Random or None
        A private RNG for this bot's own draws. With None (the default,
        used by `clude_training.self_play`) it draws from the engine RNG
        passed into each decision, like `RandomBot`, so a seeded game is
        reproducible on its own. The arena gives each fill seat a private
        RNG instead, so that its draws never shift the shared dice.
    """

    name = "floor"

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng

    def reset(self, seed: "int | None") -> None:
        """Reseed the private RNG, if there is one."""
        if self._rng is not None:
            self._rng.seed(seed)

    def observe(self, transition: Any) -> None:
        """No-op -- nothing to learn across games."""
        return None

    def _draw(self, rng: random.Random) -> random.Random:
        return self._rng if self._rng is not None else rng

    @staticmethod
    def _require_mask(obs: ClueObservation):
        assert obs.mask is not None, (
            "FloorBot needs a masked observation: run the game with "
            "observer=clude_constraints.observe"
        )
        return obs.mask

    @staticmethod
    def target_rooms(obs: ClueObservation) -> list:
        """Rooms worth suggesting in, from the floor alone: the open ones
        (holder unknown), or once none are left, those nobody else can
        refute (the envelope's or this seat's own)."""
        mask = obs.mask
        open_rooms = [r for r in ROOMS if mask.holder_of(r) is None]
        if open_rooms:
            return open_rooms
        return [r for r in ROOMS if mask.holder_of(r) in (ENVELOPE, obs.my_index)]

    def choose_movement(
        self, obs: ClueObservation, choices: list[MoveChoice], rng: random.Random
    ) -> MoveChoice:
        """Land in a target room if any move does; else move closest to
        one; else uniform. Exactly one draw from the RNG either way."""
        self._require_mask(obs)
        draw = self._draw(rng)
        targets = self.target_rooms(obs)
        if not targets:
            return draw.choice(choices)
        landing = [c for c in choices if board.room_of(c.destination) in targets]
        if landing:
            return draw.choice(landing)

        def steps(choice: MoveChoice) -> int:
            distances = board.room_distances(choice.destination)
            return min(distances[r] for r in targets)

        best = min(steps(c) for c in choices)
        return draw.choice([c for c in choices if steps(c) == best])

    def choose_suggestion(
        self, obs: ClueObservation, room: str, rng: random.Random
    ) -> Optional[tuple[str, str]]:
        """Always suggests. Suspect and weapon are uniform over cards that
        are neither in this seat's hand nor located by the floor. Once a
        category has none left, name its proven envelope card if there
        is one -- nobody can refute it, so the suggestion tests the
        other named cards cleanly, the classic endgame move -- else any
        card of that category."""
        mask = self._require_mask(obs)
        draw = self._draw(rng)

        def open_cards(category: list) -> list:
            candidates = [
                c for c in category if c not in obs.own_hand and mask.holder_of(c) is None
            ]
            if candidates:
                return candidates
            proven = [c for c in category if mask.holder_of(c) == ENVELOPE]
            return proven or list(category)

        return (draw.choice(open_cards(SUSPECTS)), draw.choice(open_cards(WEAPONS)))

    def choose_accusation(
        self, obs: ClueObservation, rng: random.Random
    ) -> Optional[tuple[str, str, str]]:
        """The proven envelope, or None while any category is still open."""
        return self._require_mask(obs).solution()

    def choose_card_to_show(
        self, obs: ClueObservation, candidates: list[str], shown_to: int, rng: random.Random
    ) -> str:
        """Uniform over the matching cards -- unchanged from `RandomBot`."""
        return self._draw(rng).choice(candidates)
