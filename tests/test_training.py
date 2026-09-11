"""Phase 4: self-play snapshot generation and the belief-quality
benchmark.
"""
from __future__ import annotations

import math

import pytest

from clude_training.benchmark import _Accumulator, run_benchmark
from clude_training.self_play import generate_snapshots


def test_generate_snapshots_shape():
    checkpoints = (0.5, 1.0)
    snaps = list(generate_snapshots(n_games=4, seed=1, checkpoints=checkpoints))
    assert snaps, "expected at least one snapshot"
    for snap in snaps:
        assert snap.checkpoint in checkpoints
        assert snap.obs.mask is not None
        assert len(snap.envelope) == 3
        assert 0 <= snap.viewer < snap.obs.n_players

    # Every game/checkpoint combination should contribute one snapshot
    # per player at the table.
    seen = {(s.game_index, s.checkpoint) for s in snaps}
    for game_index, checkpoint in seen:
        viewers = {s.viewer for s in snaps if s.game_index == game_index and s.checkpoint == checkpoint}
        assert len(viewers) >= 3  # Clue's minimum table size


def test_generate_snapshots_is_reproducible():
    a = [(s.game_index, s.viewer, s.checkpoint, s.envelope) for s in generate_snapshots(5, seed=9)]
    b = [(s.game_index, s.viewer, s.checkpoint, s.envelope) for s in generate_snapshots(5, seed=9)]
    assert a == b


# ---------------------------------------------------------------------
# _Accumulator arithmetic, on synthetic beliefs (no self-play involved)
# ---------------------------------------------------------------------


def _all_cards():
    from clude_core.domain import ALL_CARDS

    return ALL_CARDS


def test_accumulator_perfect_predictor_scores_zero_loss():
    envelope = ("Scarlett", "Candlestick", "Kitchen")
    probs = {c: (1.0 if c in envelope else 0.0) for c in _all_cards()}
    acc = _Accumulator()
    acc.update(probs, envelope)
    assert acc.brier == pytest.approx(0.0)
    assert acc.log_loss == pytest.approx(0.0, abs=1e-6)
    assert acc.top1_accuracy == pytest.approx(1.0)


def test_accumulator_uniform_predictor_matches_closed_form():
    from clude_core.domain import ROOMS, SUSPECTS, WEAPONS

    envelope = ("Scarlett", "Candlestick", "Kitchen")
    probs = {}
    for category in (SUSPECTS, WEAPONS, ROOMS):
        for c in category:
            probs[c] = 1.0 / len(category)
    acc = _Accumulator()
    acc.update(probs, envelope)

    # Brier, averaged over all 21 cards: each category contributes
    # (n-1) cards at (1/n - 0)^2 and 1 card at (1/n - 1)^2.
    expected_brier_sum = 0.0
    expected_cards = 0
    for category in (SUSPECTS, WEAPONS, ROOMS):
        n = len(category)
        expected_brier_sum += (n - 1) * (1.0 / n) ** 2 + (1.0 / n - 1.0) ** 2
        expected_cards += n
    assert acc.brier == pytest.approx(expected_brier_sum / expected_cards)
    assert acc.log_loss == pytest.approx(
        sum(math.log(len(c)) for c in (SUSPECTS, WEAPONS, ROOMS)) / 3
    )


def test_accumulator_top1_ties_go_to_first_in_category_order():
    from clude_core.domain import ROOMS, SUSPECTS, WEAPONS

    envelope = ("Mustard", "Rope", "Kitchen")  # Mustard isn't first in SUSPECTS
    probs = {c: 1.0 / len(SUSPECTS) for c in SUSPECTS}
    probs.update({c: 1.0 / len(WEAPONS) for c in WEAPONS})
    probs.update({c: 1.0 / len(ROOMS) for c in ROOMS})
    acc = _Accumulator()
    acc.update(probs, envelope)
    # A fully tied suspect category can't pick out Mustard by chance,
    # so top-1 must miss at least the suspect category.
    assert acc.top1_accuracy < 1.0


# ---------------------------------------------------------------------
# End-to-end benchmark smoke test
# ---------------------------------------------------------------------


def test_benchmark_runs_and_beats_the_uniform_baseline():
    result = run_benchmark(n_games=10, seed=123, checkpoints=(1.0,))
    names = set(result.per_agent)
    assert names == {"Scarlett", "Plum", "Peacock", "Mustard", "Green", "White", "uniform"}

    uniform_brier = result.per_agent["uniform"][1.0].brier
    # At least one real method should beat pure ignorance on Brier score
    # at game end -- otherwise the benchmark isn't measuring anything.
    best_real_brier = min(
        result.per_agent[name][1.0].brier for name in names if name != "uniform"
    )
    assert best_real_brier < uniform_brier

    for name in names:
        acc = result.per_agent[name][1.0]
        assert acc.n_cards > 0
        assert 0.0 <= acc.top1_accuracy <= 1.0
        assert acc.brier >= 0.0


def test_benchmark_lets_green_learn_across_games():
    """Green's posteriors must not reset between games (David's call,
    2026-09-11): after enough self-play, at least one arm's Beta
    posterior should have moved measurably away from the Beta(1, 1)
    prior every arm starts at.
    """
    result = run_benchmark(n_games=20, seed=321, checkpoints=(1.0,))
    green = result.agents["Green"]
    assert any(
        (c.alpha, c.beta) != (1.0, 1.0) for c in green.candidates.values()
    ), "Green's posteriors never moved -- is he being reset between games?"
    # Every candidate should have accumulated many observations (5 arms
    # x 1 checkpoint x n_players-ish viewers per game x 20 games).
    total_evidence = sum(c.alpha + c.beta - 2.0 for c in green.candidates.values())
    assert total_evidence > 50
