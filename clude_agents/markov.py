"""White -- Markov model over opponents' suggestion patterns.

Starting point: `legacy/opponent_model.py`'s heuristic ("a player who
repeats a card probably doesn't hold it"), reworked into an actual
first-order Markov chain and its documented-inversion bug fixed (the
legacy README flags `estimated_knowledge` as ambiguous between "knows
where it is" and "probably doesn't hold it" -- this module commits to
one direction, stated below).

For each opponent, encodes their suggestion history as a sequence of
repeat(1)/new(0) symbols -- did this suggestion re-name at least one
card they'd already named before, or was it all new cards -- and fits a
two-state first-order Markov chain to it. A player currently in a
high-P(repeat) regime is read as still fishing for information about
those cards (hasn't been shown them, doesn't hold them), which raises
suspicion toward the *envelope* for cards they keep re-naming without
resolution. This is White's character: he reads suggestion behavior, not
card content -- strong on who's close to solving, weak on the envelope
itself if a player's pattern is atypical (a chatty human, say).

Notes
-----
Recomputes from scratch every call from `obs.suggestion_log`; `reset`/
`observe` are no-ops. Direction of the heuristic (repeats raise, not
lower, suspicion for envelope) is a stated modeling choice, not a
derived fact -- see module docstring above.

Absence of evidence (changed in Phase 5b, docs/phase5-plan.md 4.3):
every still-unresolved card starts at the floor's uniform prior (raw
score 1) and the Markov evidence is *added* on top, so a card no
opponent has named yet is merely unsuspicious, not impossible. Before
this, such cards scored exactly 0 and accounted for 79% of White's
log-loss in the Phase 4 benchmark. The method itself is unchanged.

`ClueBelief.extra` also carries per-opponent ``repeat_probability`` and
a ``closeness`` proxy (how much evidence that opponent has been shown:
each refuted suggestion of theirs showed them one card, each unrefuted
one proved them up to three, squashed to [0, 1)). Nothing consumes
``closeness`` yet; it is there so an `urgency` dial has something to
read if one is ever added.

Phase 7 memory: the chain's Laplace prior (one phantom count per
transition cell) can be replaced, per opponent *identity*, by the
transition frequencies that identity showed in earlier games
(`prior_cells`), at the same total mass by default, so the live
sequence weighs exactly as it did and only the starting shape of the
chain is informed. `priors` maps a roster label to its `transition_counts`
summed over stored games (`clude_training.memory` keeps them in White's
logbook); `set_table` says which label sits in which seat this game.
With no priors, or no table, nothing changes.
"""
from __future__ import annotations

from typing import Any, Optional

from clude_agents.base import ClueBelief, SeededAgentMixin, mask_and_normalize
from clude_core.domain import ALL_CARDS
from clude_core.state import ClueObservation

# Laplace-smoothed transition-count prior so a short/empty sequence
# returns the neutral P(repeat) = 0.5 rather than an undefined ratio.
_PRIOR = 1.0
# Total pseudo-count of the transition prior: the four cells at `_PRIOR`.
# A remembered opponent's prior is spread over the cells at this mass.
PRIOR_MASS = 4.0
# The floor's own prior for an unresolved card, before any Markov
# evidence is added; the same scale as one repeat-weighted mention.
_BASE_SCORE = 1.0
# Half-saturation point of the `closeness` proxy, in evidence units.
_CLOSENESS_HALF = 6.0

TRANSITION_KEYS: tuple = ("00", "01", "10", "11")
"""Transition cells as JSON keys: ``"ab"`` for a step from symbol a to b."""


def transition_counts(symbols: list) -> dict:
    """How often each repeat/new transition occurs in a symbol sequence,
    keyed by `TRANSITION_KEYS`; all zero for fewer than two symbols."""
    counts = {key: 0 for key in TRANSITION_KEYS}
    for a, b in zip(symbols, symbols[1:]):
        counts[f"{a}{b}"] += 1
    return counts


def prior_cells(counts: Optional[dict] = None, mass: float = PRIOR_MASS) -> dict:
    """The chain's four prior cells: `mass` pseudo-counts spread by the
    transition frequencies in `counts` with one phantom count per cell,
    so an identity never seen repeating still can. With no counts every
    cell gets ``mass / 4`` -- the plain Laplace prior at the default
    mass."""
    counts = counts or {}
    total = sum(float(counts.get(key, 0)) for key in TRANSITION_KEYS) + 4.0
    return {
        (int(key[0]), int(key[1])): mass * (float(counts.get(key, 0)) + 1.0) / total
        for key in TRANSITION_KEYS
    }


def _stationary_repeat_probability(symbols: list, cells: Optional[dict] = None) -> float:
    """First-order Markov chain over a repeat(1)/new(0) symbol sequence;
    returns P(state=1) under the chain's stationary distribution.

    For a 2-state chain with transition probabilities p01 (0->1) and
    p10 (1->0), the stationary probability of state 1 is
    ``p01 / (p01 + p10)`` -- standard detailed-balance result for a
    2-state Markov chain. `cells` replaces the Laplace prior counts
    (`prior_cells`); None is the plain prior.
    """
    if cells is None:
        counts = {(0, 0): _PRIOR, (0, 1): _PRIOR, (1, 0): _PRIOR, (1, 1): _PRIOR}
    else:
        counts = dict(cells)
    for a, b in zip(symbols, symbols[1:]):
        counts[(a, b)] += 1
    p01 = counts[(0, 1)] / (counts[(0, 0)] + counts[(0, 1)])
    p10 = counts[(1, 0)] / (counts[(1, 0)] + counts[(1, 1)])
    denom = p01 + p10
    return p01 / denom if denom > 0 else 0.5


def suggestion_patterns(suggestion_log, seats) -> tuple:
    """Each listed seat's suggestion history as White reads it.

    Returns
    -------
    (named_counts, symbols, evidence) : tuple[dict, dict, dict]
        Per seat: how often it has named each card; its repeat(1)/new(0)
        symbol per suggestion (did it re-name a card it had named
        before); and its evidence total (1 per refuted suggestion, 3 per
        unrefuted one). Public information only, so the same for every
        viewer.
    """
    named_counts: dict = {p: {} for p in seats}
    symbols: dict = {p: [] for p in seats}
    evidence: dict = {p: 0.0 for p in seats}
    for s in suggestion_log:
        p = s.suggester
        if p not in named_counts:
            continue
        cards = s.cards()
        is_repeat = any(named_counts[p].get(c, 0) > 0 for c in cards)
        symbols[p].append(1 if is_repeat else 0)
        for c in cards:
            named_counts[p][c] = named_counts[p].get(c, 0) + 1
        evidence[p] += 1.0 if s.refuter is not None else 3.0
    return named_counts, symbols, evidence


class MarkovAgent(SeededAgentMixin):
    """Reads suggestion-repetition patterns per opponent, not card
    content -- strong on people, weak on unusual play.

    Parameters
    ----------
    priors : dict or None
        Phase 7 memory: roster label -> `transition_counts` from earlier
        games; see the module notes.
    prior_mass : float
        Total pseudo-count each remembered prior is spread over.
    """

    name = "White"

    def __init__(self, priors: Optional[dict] = None, prior_mass: float = PRIOR_MASS) -> None:
        super().__init__()
        self.priors: dict = dict(priors or {})
        self.prior_mass = prior_mass
        self.table: list = []

    def set_priors(self, priors: Optional[dict]) -> None:
        """Replace the per-identity transition priors."""
        self.priors = dict(priors or {})

    def set_table(self, labels) -> None:
        """Who sits where this game: roster labels by seat index. Called
        by `Character.new_game`; only matters with `priors`."""
        self.table = list(labels)

    def _cells_for(self, seat: int) -> Optional[dict]:
        if not self.priors or seat >= len(self.table):
            return None
        counts = self.priors.get(self.table[seat])
        return prior_cells(counts, self.prior_mass) if counts else None

    def select_action(self, obs: ClueObservation) -> ClueBelief:
        """Fit each opponent's repeat/new Markov chain, then weight
        still-unresolved cards they've re-named by that opponent's
        current P(repeat), on top of a uniform prior."""
        assert obs.mask is not None, (
            "select_action requires a masked observation (see clude_constraints.observe)"
        )
        mask = obs.mask
        opponents = [p for p in range(obs.n_players) if p != obs.my_index]
        named_counts, symbols, evidence = suggestion_patterns(obs.suggestion_log, opponents)

        raw: dict = {c: _BASE_SCORE for c in ALL_CARDS if mask.holder_of(c) is None}
        repeat_probability: dict = {}
        for p in opponents:
            repeat_prob = _stationary_repeat_probability(symbols[p], self._cells_for(p))
            repeat_probability[p] = repeat_prob
            for c, n in named_counts[p].items():
                if c not in raw:
                    continue  # already resolved; nothing left for White to add
                raw[c] += n * repeat_prob

        closeness = {p: e / (e + _CLOSENESS_HALF) for p, e in evidence.items()}
        return ClueBelief(
            probabilities=mask_and_normalize(raw, mask),
            extra={
                "named_counts": named_counts,
                "repeat_probability": repeat_probability,
                "closeness": closeness,
            },
        )

    def observe(self, transition: Any) -> None:
        """No-op -- see module Notes: nothing incremental to update."""
        return None
