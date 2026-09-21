"""Sketch: `WebGame.head_reading(seat)` -- the head on a headless generator.

Belongs in `clude_training/table.py`, beside `stand_in_answer`, not in the
MCP module. Two reasons. A sweep's LLM seats go through the API backend,
not through MCP, and both arms must read numbers produced the same way or
the comparison is between transports rather than between players. And here
it is testable with no network and no MCP client: build a game, play it
headless, assert the reading at turn N equals what the character's own bot
holds at turn N. That test is the whole guarantee.

The shadow is built the same way `stand_in` builds its floor bot -- once
per game, per seat -- but with the character's spec rather than
`FloorBot`, and it is never asked to decide. It only watches.

Two properties worth preserving:

Rebuildable. The shadow is fed from the event log, so a cold instance that
replayed a table's entries has a shadow in the same state, exactly as the
game itself does. Nothing new to persist, nothing new to go stale.

Sealed. `observer(state, seat)` is what the engine gives that seat's own
bot; the shadow must be fed through the same door and no other. If it ever
sees `state.envelope` or another seat's hand the arm is worthless and no
test will tell you, because the numbers will look better.
"""
from __future__ import annotations

from typing import Optional

from clude_core import engine


class _HeadMixin:
    """The part of WebGame this sketch is about."""

    def _shadow(self, seat: int):
        """The character's own strategy for `seat`, watching only.

        Built on first use and kept with the game, like the floor bots.
        Deterministic per game and seat: the same seed feeds it, so two
        processes holding the same table agree.
        """
        if seat in self._shadows:
            return self._shadows[seat]
        token = self.setup.seats[seat].token
        spec = AGENT_SPECS[token]
        shadow = spec.build(seat=seat, n_players=self.setup.n_players,
                            rng=Random(fill_seed(self.setup.seed, seat)))
        self._shadows[seat] = shadow
        self._feed(seat, shadow, upto=len(self.events))
        return shadow

    def _feed(self, seat: int, shadow, upto: int) -> None:
        """Show the shadow every event this seat has seen, from where it
        left off. A suggestion's refutation is the delicate one: the seat
        learns *which* card only when it was the suggester or the refuter,
        and the shadow must learn exactly as much and no more -- the same
        asymmetry `observer` already encodes.
        """
        start = self._shadow_at.get(seat, 0)
        for event in self.events[start:upto]:
            shadow.observe(self.view_of(event, seat))
        self._shadow_at[seat] = upto

    def head_reading(self, seat: int) -> Optional[dict]:
        """What this seat's method currently believes, in its own shape.

        Returns whatever the method natively produces -- a posterior over
        the envelope for Plum, belief/plausibility pairs for Peacock, arm
        estimates for Green -- with a `shape` naming which, so the reader
        knows how to read it. Do not normalise these into a common vector:
        the six methods disagreeing in kind, and not only in number, is
        the thing under study.

        None if the seat has no head, which is the default.
        """
        if not getattr(self.setup.seats[seat], "head", False):
            return None
        shadow = self._shadow(seat)
        self._feed(seat, shadow, upto=len(self.events))
        return {
            "shape": shadow.reading_shape,   # "posterior" | "belief_plausibility" | ...
            "turn": self.state.turn,
            **shadow.reading(),
        }
