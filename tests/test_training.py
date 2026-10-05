"""Phase 4: self-play snapshot generation and the belief-quality
benchmark, plus the post-game replay helpers in `clude_training.trace`.
"""
from __future__ import annotations

import json
import math

import numpy as np

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
    2026-09-11), and since Phase 5b's rank reward they must actually
    *separate*: the Phase 4 reward left all five arms within a percent
    of each other, so Thompson sampling picked among them at random.
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
    means = [c.mean for c in green.candidates.values()]
    assert max(means) - min(means) > 0.1, "Green's arms did not separate"


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


# ---------------------------------------------------------------------
# Phase 12, N4: rollouts for training Plum
# ---------------------------------------------------------------------


def _weights():
    from clude_agents.deep_nash import init_weights

    return init_weights(seed=5)


def test_draw_table_seats_the_network_at_least_once_and_is_seeded():
    from clude_core.domain import SUSPECTS
    from clude_training import rollout

    seen = set()
    for seed in range(40):
        suspects, kinds = rollout.draw_table(seed, 3 + seed % 4, "mixed")
        assert len(suspects) == len(kinds) == 3 + seed % 4
        assert list(suspects) == [s for s in SUSPECTS if s in suspects]  # board order
        assert rollout.NET in kinds
        for token, kind in zip(suspects, kinds):
            assert kind in (rollout.NET, rollout.FLOOR, token) and not (token == "Plum" and kind == "Plum")
        seen.update(kinds)
        assert rollout.draw_table(seed, 3 + seed % 4, "mixed") == (suspects, kinds)
    assert rollout.FLOOR in seen and any(k not in (rollout.NET, rollout.FLOOR) for k in seen)
    assert rollout.draw_table(3, 4, "self")[1] == [rollout.NET] * 4
    with pytest.raises(ValueError):
        rollout.draw_table(1, 3, "league")


def test_play_one_records_legal_decisions_and_the_outcome():
    from clude_agents.deep_nash import CHOICE_SIZE, STATE_SIZE
    from clude_core.domain import ALL_CARDS
    from clude_training import rollout

    weights = _weights()
    trace = rollout.play_one(weights, seed=5, n_players=4, population="mixed", max_turns=80)
    assert trace.n_players == 4 and len(trace.rewards) == 4 and trace.net_seats
    assert trace.decisions, "the network seat decided nothing"
    for d in trace.decisions:
        assert d.seat in trace.net_seats and d.head in rollout.HEADS
        assert d.state.shape == (STATE_SIZE,) and d.possible.shape == (len(ALL_CARDS),)
        if d.head == "move":
            assert d.choices is not None and d.choices.shape[1] == CHOICE_SIZE
            assert 0 <= d.action < len(d.choices) and d.candidates is None
        else:
            assert d.choices is None and 0 <= d.action < len(d.candidates) <= 6
    for card in trace.envelope:
        assert card in ALL_CARDS
    if trace.winner is not None:
        assert trace.rewards[trace.winner] == 1.0 and not trace.capped
    assert all(r in (-1.0, 0.0, 1.0) for r in trace.rewards)
    assert sum(1 for r in trace.rewards if r == 1.0) <= 1

    arrays = trace.to_arrays()
    n = len(trace.decisions)
    assert arrays["states"].shape == (n, STATE_SIZE) and arrays["envelope"].shape == (n, len(ALL_CARDS))
    assert arrays["envelope"][0].sum() == 3.0 and arrays["possible"].shape == (n, len(ALL_CARDS))
    assert arrays["choice_offsets"].shape == (n + 1,) and arrays["candidate_offsets"].shape == (n + 1,)
    assert arrays["choice_offsets"][-1] == len(arrays["choices"])
    assert arrays["candidate_offsets"][-1] == len(arrays["candidates"])
    moves = arrays["head"] == 0
    assert (np.diff(arrays["choice_offsets"])[moves] > 0).all() and (np.diff(arrays["choice_offsets"])[~moves] == 0).all()
    assert (arrays["reward"] == np.array([trace.rewards[s] for s in arrays["seat"]])).all()

    again = rollout.play_one(weights, seed=5, n_players=4, population="mixed", max_turns=80)
    assert [d.action for d in again.decisions] == [d.action for d in trace.decisions] and again.rewards == trace.rewards


def test_rollout_batch_is_the_same_in_a_pool_as_in_this_process():
    from clude_training import rollout

    weights = _weights()
    seeds = list(range(4))
    serial = rollout.rollout_batch(weights, seeds, lambda s: 3 + s % 2, "mixed", workers=1, max_turns=60)
    parallel = rollout.rollout_batch(weights, seeds, lambda s: 3 + s % 2, "mixed", workers=2, max_turns=60)
    assert [t.seed for t in serial] == seeds
    for a, b in zip(serial, parallel):
        assert a.kinds == b.kinds and a.rewards == b.rewards and a.turns == b.turns
        assert [d.action for d in a.decisions] == [d.action for d in b.decisions]
    fixed = rollout.rollout_batch(weights, seeds[:2], 3, "self", workers=1, max_turns=60)
    assert all(t.n_players == 3 and t.kinds == [rollout.NET] * 3 for t in fixed)


def test_evaluate_reports_plum_on_the_two_standard_tables():
    from clude_training import rollout

    report = rollout.evaluate(_weights(), n_games=2, seed=7007, max_turns=60)
    assert set(report) == {"tuned", "plum"}
    for table in report.values():
        assert table["games"] == 2
        assert 0.0 <= table["win_rate"] <= 1.0 and 0.0 <= table["wrong_rate"] <= 1.0
        assert 0.0 <= table["capped"] <= 1.0 and table["mean_turns"] > 0
