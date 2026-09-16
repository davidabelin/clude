"""Plum -- exact posterior by enumerating consistent deals.

Built fresh (no legacy basis). Correct and slow by design: a real
backtracking CSP search over every still-unresolved card, respecting
per-holder hand-size capacity, the one-envelope-card-per-category rule,
and `mask.or_constraints` jointly -- the joint structure a per-card
marginal (Scarlett's method) cannot see, which is exactly why
`clude_constraints.propagator` exposes `or_constraints` separately (see
docs/architecture.md).

Falls back to weighted random sampling once the search tree exceeds a
node budget (early game, 5-6 players), trading exactness for a noisier
but still-informative estimate -- see `Notes` below.
"""
from __future__ import annotations

from typing import Any

from clude_agents.base import CATEGORIES, ClueBelief, SeededAgentMixin, mask_and_normalize
from clude_constraints import ENVELOPE, ConstraintResult, Holder
from clude_core.domain import ALL_CARDS
from clude_core.state import ClueObservation

DEFAULT_NODE_BUDGET = 200_000
# 10,000 samples since 2026-09-15. On the Classic grid he exhausts the
# node budget in 490 of 1080 benchmark calls (the early game is too open
# for any budget worth affording: ten times the nodes only takes that to
# 384 and costs four times the time), so the fallback's noise, not the
# search, is what his mid-game numbers are made of. Five times the
# samples take his 50%-checkpoint log-loss from 1.75 to 1.44 at about
# twice the time per call; it does not make him better than uniform
# there (1.35). See docs/strategy-glossary.md, "Tuned presets on the
# grid".
DEFAULT_SAMPLE_BUDGET = 10_000


def _holder_order(holder: Holder) -> tuple:
    """Sort key giving holder sets a fixed iteration order: seats in
    order, then the envelope.

    `mask.possible_holders` values are frozensets mixing seat ints with
    the string `ENVELOPE`, and a str's hash -- hence its position in
    set iteration -- changes with every Python process (hash
    randomization). Iterating them raw made the search order, the node
    budget cutoff, and the sampling fallback's draws differ between
    processes for the same seed, which broke arena reproducibility at
    5-6 players (tests/test_determinism.py).
    """
    return (1, 0) if holder == ENVELOPE else (0, holder)


class _Search:
    """Mutable backtracking state, shared by exact search and the
    sampling fallback. Card domains are fixed at construction (taken
    from `mask.possible_holders`, in `_holder_order`) and never mutated;
    only `assignment`/`capacity`/`envelope_used` change as cards are
    placed and unplaced along the current path.
    """

    def __init__(self, obs: ClueObservation, mask: ConstraintResult):
        self.unresolved = sorted(
            (c for c in ALL_CARDS if mask.holder_of(c) is None),
            key=lambda c: len(mask.possible_holders[c]),  # most-constrained-first
        )
        self.domains: dict[str, tuple[Holder, ...]] = {
            c: tuple(sorted(mask.possible_holders[c], key=_holder_order)) for c in self.unresolved
        }
        self.capacity: dict[int, int] = {
            p: mask.hand_sizes[p] - sum(1 for c in ALL_CARDS if mask.holder_of(c) == p)
            for p in range(obs.n_players)
        }
        self.category_of = {c: i for i, cat in enumerate(CATEGORIES) for c in cat}
        self.envelope_used = [
            any(mask.holder_of(c) == ENVELOPE for c in cat) for cat in CATEGORIES
        ]
        # Constraints already satisfied by a hard-resolved card need no
        # further checking during search.
        self.or_constraints = [
            (tuple(cards), holder)
            for cards, holder in mask.or_constraints
            if not any(mask.holder_of(c) == holder for c in cards)
        ]
        self.assignment: dict[str, Holder] = {}
        self.envelope_counts: dict[str, int] = {c: 0 for c in self.unresolved}
        self.completions = 0
        self.nodes = 0

    def can_place(self, card: str, holder: Holder) -> bool:
        if holder == ENVELOPE:
            return not self.envelope_used[self.category_of[card]]
        return self.capacity[holder] > 0

    def place(self, card: str, holder: Holder) -> None:
        self.assignment[card] = holder
        if holder == ENVELOPE:
            self.envelope_used[self.category_of[card]] = True
        else:
            self.capacity[holder] -= 1

    def unplace(self, card: str, holder: Holder) -> None:
        del self.assignment[card]
        if holder == ENVELOPE:
            self.envelope_used[self.category_of[card]] = False
        else:
            self.capacity[holder] += 1

    def constraint_satisfiable(self, cards: tuple, holder: Holder) -> bool:
        """True if `holder` already holds one of `cards`, or some
        still-unassigned member of `cards` could yet go to `holder`."""
        if any(self.assignment.get(c) == holder for c in cards):
            return True
        return any(
            c not in self.assignment and holder in self.domains[c] for c in cards
        )

    def backtrack(self, index: int, node_budget: int) -> bool:
        """Depth-first search from `unresolved[index]`. Returns False if
        the node budget ran out before the search finished; the caller
        must then treat `completions`/`envelope_counts` as incomplete.
        """
        if index == len(self.unresolved):
            self.completions += 1
            for card, holder in self.assignment.items():
                if holder == ENVELOPE:
                    self.envelope_counts[card] += 1
            return True

        card = self.unresolved[index]
        for holder in self.domains[card]:
            self.nodes += 1
            if self.nodes > node_budget:
                return False
            if not self.can_place(card, holder):
                continue
            self.place(card, holder)
            ok_so_far = all(
                self.constraint_satisfiable(cards, h) for cards, h in self.or_constraints
            )
            budget_ok = True
            if ok_so_far:
                budget_ok = self.backtrack(index + 1, node_budget)
            self.unplace(card, holder)
            if not budget_ok:
                return False
        return True


def _sample_once(obs: ClueObservation, mask: ConstraintResult, rng) -> "dict[str, Holder] | None":
    """One randomized constructive attempt at a consistent deal. Returns
    None if the random order painted itself into a corner."""
    sample = _Search(obs, mask)
    order = list(sample.unresolved)
    rng.shuffle(order)
    for card in order:
        choices = list(sample.domains[card])
        rng.shuffle(choices)
        placed = next((h for h in choices if sample.can_place(card, h)), None)
        if placed is None:
            return None
        sample.place(card, placed)
    if not all(sample.constraint_satisfiable(c, h) for c, h in sample.or_constraints):
        return None
    return sample.assignment


def _exact_or_sampled_scores(
    obs: ClueObservation,
    mask: ConstraintResult,
    node_budget: int,
    sample_budget: int,
    rng,
) -> tuple[dict[str, float], dict[str, Any]]:
    """Return ``(raw_scores, diagnostics)``.

    ``diagnostics`` reports which path produced the scores so callers
    (the benchmark's timing/fallback columns, the trace CLI) can see how
    often Plum actually gets to be exact: ``method`` is ``"resolved"``
    (nothing left to search), ``"exact"`` (search finished within
    `node_budget`) or ``"sampled"`` (fallback); ``nodes`` is the search
    nodes visited; ``completions`` counts consistent deals found by exact
    search; ``valid_samples`` counts accepted rejection samples.
    """
    search = _Search(obs, mask)
    diagnostics: dict[str, Any] = {
        "method": "resolved", "nodes": 0, "completions": 0, "valid_samples": 0,
    }
    if not search.unresolved:
        return {}, diagnostics

    finished = search.backtrack(0, node_budget)
    diagnostics["nodes"] = search.nodes
    if finished and search.completions > 0:
        diagnostics["method"] = "exact"
        diagnostics["completions"] = search.completions
        return {c: n / search.completions for c, n in search.envelope_counts.items()}, diagnostics

    # Sampling fallback: noisier, and biased toward whatever random
    # construction order happens to survive most often -- an honest
    # approximation, not a fix, which is Plum's whole point past a
    # certain table size (see module docstring).
    counts = {c: 0 for c in search.unresolved}
    valid_samples = 0
    for _ in range(sample_budget):
        assignment = _sample_once(obs, mask, rng)
        if assignment is None:
            continue
        valid_samples += 1
        for card, holder in assignment.items():
            if holder == ENVELOPE:
                counts[card] += 1

    diagnostics["method"] = "sampled"
    diagnostics["valid_samples"] = valid_samples
    if valid_samples == 0:
        return {}, diagnostics
    return {c: n / valid_samples for c, n in counts.items()}, diagnostics


class ExactEnumAgent(SeededAgentMixin):
    """Correct in principle, exhaustive when it can afford to be, honest
    about sampling noise when it can't."""

    name = "Plum"

    def __init__(
        self,
        node_budget: int = DEFAULT_NODE_BUDGET,
        sample_budget: int = DEFAULT_SAMPLE_BUDGET,
    ) -> None:
        super().__init__()
        self.node_budget = node_budget
        self.sample_budget = sample_budget

    def select_action(self, obs: ClueObservation) -> ClueBelief:
        """Enumerate (or sample) consistent deals and take the empirical
        marginal P(card is the envelope's) over completions.

        `ClueBelief.extra` carries the search diagnostics documented on
        `_exact_or_sampled_scores` (``method``, ``nodes``, ...), so a
        caller can tell an exact answer from a sampled one.
        """
        assert obs.mask is not None, (
            "select_action requires a masked observation (see clude_constraints.observe)"
        )
        raw, diagnostics = _exact_or_sampled_scores(
            obs, obs.mask, self.node_budget, self.sample_budget, self.rng
        )
        return ClueBelief(probabilities=mask_and_normalize(raw, obs.mask), extra=diagnostics)

    def observe(self, transition: Any) -> None:
        """No-op -- recomputed from scratch every call, like the
        deduction floor itself."""
        return None
