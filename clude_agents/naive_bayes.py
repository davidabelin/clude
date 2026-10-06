"""Scarlett's multiplicative, independence-assuming suggestion evidence.

Unrefuted suggestions boost their cards; unknown-card refutations decay
them. Raw scores are masked/normalized per category. Repeated evidence can
compound into overconfidence because joint hand constraints are not a
posterior model here. See docs/strategy-glossary.md.
"""
from __future__ import annotations

from typing import Any

from clude_agents.base import ClueBelief, SeededAgentMixin, mask_and_normalize
from clude_core.domain import ALL_CARDS
from clude_core.state import ClueObservation

# Multiplicative, independence-assuming "boosts" -- the sloppy part.
# An unrefuted suggestion is fairly strong evidence its three cards are
# the envelope's (nobody could show them), so it boosts hard.
UNREFUTED_BOOST = 2.0
# A suggestion refuted by an unknown card is much weaker evidence -- the
# refuter holds *one* of the three, which is evidence *against* each of
# them individually being the envelope's (legacy's `_soft_update_refuter`
# boosted the refuter's holder-marginal for these cards; translated to
# Scarlett's envelope-only marginal here, that same fact is a
# probability *decrease*, since a fixed card's holder-probabilities sum
# to 1 across all holders including the envelope).
REFUTED_UNKNOWN_DECAY = 1.0 / 1.5


class NaiveBayesAgent(SeededAgentMixin):
    """Independent, multiplicative evidence updates -- fast, and
    overconfident exactly where independence fails."""

    name = "Scarlett"

    def select_action(self, obs: ClueObservation) -> ClueBelief:
        """Fold every suggestion into an independent multiplicative
        boost/decay, then mask and renormalize. See module docstring for
        the two update rules."""
        assert obs.mask is not None, (
            "select_action requires a masked observation (see clude_constraints.observe)"
        )
        raw = {c: 1.0 for c in ALL_CARDS}
        for s in obs.suggestion_log:
            cards = s.cards()
            if s.refuter is None:
                for c in cards:
                    raw[c] *= UNREFUTED_BOOST
            elif s.card_shown is None:
                for c in cards:
                    raw[c] *= REFUTED_UNKNOWN_DECAY
            # else: a specific card_shown is already a hard fact the mask
            # resolves directly; no soft update needed.
        return ClueBelief(probabilities=mask_and_normalize(raw, obs.mask))

    def observe(self, transition: Any) -> None:
        """No-op -- see module Notes: nothing incremental to update."""
        return None
