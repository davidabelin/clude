"""Phase 4: self-play snapshot generation and the belief-quality
benchmark, plus the post-game replay helpers in `clude_training.trace`.
"""
from __future__ import annotations

import json
import math

import pytest

from clude_agents import build_agent
from clude_core import engine
from clude_core.bots import RandomBot
from clude_training.benchmark import _Accumulator, run_benchmark
from clude_training.self_play import generate_snapshots
from clude_training.trace import belief_trace, floor_convergence


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


def test_generate_snapshots_can_fix_the_table_size():
    snaps = list(generate_snapshots(3, seed=1, checkpoints=(1.0,), player_counts=(5,)))
    assert snaps
    assert all(s.obs.n_players == 5 for s in snaps)


# ---------------------------------------------------------------------
# Post-game replay: belief_trace / floor_convergence
# ---------------------------------------------------------------------


def _finished_game(seed=3, n_players=3, max_turns=60):
    bots = {p: RandomBot() for p in range(n_players)}
    state, _events = engine.run_game(n_players, bots, seed=seed, max_turns=max_turns)
    assert state.suggestion_log, "need a game with at least one suggestion"
    return state


def _scarlett(seed=0):
    agent = build_agent("Scarlett")
    agent.reset(seed)
    return {"Scarlett": agent}


def test_belief_trace_covers_every_suggestion_and_ends_on_the_full_game():
    state = _finished_game()
    steps = belief_trace(state, viewer=0, agents=_scarlett())
    total = len(state.suggestion_log)
    assert [s.k for s in steps] == list(range(total + 1))
    assert steps[0].suggestion is None
    assert steps[-1].suggestion == steps[-1].obs.suggestion_log[-1]
    assert len(steps[-1].obs.suggestion_log) == total
    assert all(set(s.beliefs) == {"Scarlett"} for s in steps)
    assert all(s.obs.my_index == 0 and s.obs.mask is not None for s in steps)


def test_belief_trace_every_keeps_both_endpoints():
    state = _finished_game()
    total = len(state.suggestion_log)
    steps = belief_trace(state, viewer=1, agents=_scarlett(), every=4)
    ks = [s.k for s in steps]
    assert ks[0] == 0 and ks[-1] == total
    assert all(k % 4 == 0 for k in ks[1:-1])
    with pytest.raises(ValueError):
        belief_trace(state, viewer=1, agents=_scarlett(), every=0)


def test_floor_convergence_is_monotone_for_every_viewer():
    state = _finished_game(seed=4, n_players=4, max_turns=120)
    points = floor_convergence(state)
    assert [p.k for p in points] == list(range(len(state.suggestion_log) + 1))
    for viewer in range(state.n_players):
        located = [p.resolved[viewer] for p in points]
        assert located == sorted(located), f"viewer {viewer} lost a located card"
        assert all(0 <= n <= 21 for n in located)
        # Once proven, the envelope stays proven.
        solved = [p.solved[viewer] for p in points]
        assert solved == sorted(solved)


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


def test_benchmark_accepts_an_agent_subset_and_records_call_cost():
    result = run_benchmark(
        n_games=3, seed=11, checkpoints=(1.0,), agents=_scarlett(), player_counts=(3,)
    )
    assert set(result.per_agent) == {"Scarlett", "uniform"}
    assert result.n_snapshots == 3 * 3  # three 3-player games, one checkpoint
    cell = result.per_agent["Scarlett"][1.0]
    assert cell.n_calls == result.n_snapshots
    assert cell.seconds >= 0.0 and cell.ms_per_call >= 0.0
    assert result.per_agent["uniform"][1.0].n_calls == 0

    data = result.to_dict()
    json.dumps(data)  # must be serializable as-is
    assert data["per_agent"]["Scarlett"]["1.0"]["n_calls"] == cell.n_calls
    assert data["player_counts"] == [3]


def test_benchmark_counts_plums_sampling_fallbacks():
    from clude_agents.exact_enum import ExactEnumAgent

    # A one-node budget forces the fallback on every unresolved snapshot.
    plum = ExactEnumAgent(node_budget=1, sample_budget=20)
    result = run_benchmark(n_games=2, seed=11, checkpoints=(0.5,), agents={"Plum": plum})
    cell = result.per_agent["Plum"][0.5]
    assert cell.sampled_calls > 0
    assert cell.sampled_calls <= cell.n_calls
