"""Phase 12, N4: the rollout that records Plum's games for training, and
the training script's loop on a handful of games (torch is optional,
so the script's tests skip without it)."""
from __future__ import annotations

import faulthandler
import json
import random
import sys
from pathlib import Path

import numpy as np
import pytest

from clude_agents import deep_nash as dn
from clude_training import rollout as R
from clude_training.arena import seat_lineup

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def weights():
    return dn.init_weights(11)


def test_rollout_records_every_decision_of_a_network_seat(weights):
    episodes = R.play_games(weights, [40, 41, 42], 0, R.RolloutConfig(self_play=1.0, max_turns=60))
    assert episodes and all(set(ep.lineup) == {R.NET_LABEL} for ep in episodes)
    for ep in episodes:
        assert ep.states.shape == (len(ep), dn.STATE_SIZE) and ep.states.dtype == np.float32
        assert ep.reward in (-1.0, 0.0, 1.0) and ep.reward == (1.0 if ep.won else -1.0 if ep.out else 0.0)
        assert all(0 <= i < 6 for i in ep.envelope[:2]) and 0 <= ep.envelope[2] < 9
        for kind, action, option, gain in zip(ep.kinds, ep.actions, ep.options, ep.gains):
            if kind == R.KIND_MOVE:
                assert option.shape[1] == dn.CHOICE_SIZE and 0 <= action < len(option) and gain == 0.0
            elif kind in (R.KIND_SUSPECT, R.KIND_WEAPON):
                assert option.dtype == np.int16 and 0 <= action < len(option) and gain == 0.0
            else:
                assert kind == R.KIND_BELIEF and option is None and action == -1 and gain >= 0.0
        assert 0.0 <= ep.gains.sum() <= 1.0 + 1e-9
    stats = R.RolloutStats.of(episodes).to_dict()
    assert stats["games"] == 3 and stats["episodes"] == len(episodes) and stats["mixed_episodes"] == 0


def test_rollout_is_deterministic_per_seed_and_seats_characters_at_their_tokens(weights):
    config = R.RolloutConfig(self_play=0.0, max_turns=60)
    first = R.play_games(weights, [50, 51, 52, 53], 0, config)
    again = R.play_games(weights, [50, 51, 52, 53], 0, config)
    assert [ep.lineup for ep in first] == [ep.lineup for ep in again]
    assert all(
        np.array_equal(a.states, b.states) and np.array_equal(a.actions, b.actions) and a.reward == b.reward
        for a, b in zip(first, again)
    )
    sizes = {ep.n_players for ep in first}
    assert sizes <= {3, 4, 5, 6} and len(sizes) >= 2
    for ep in first:
        assert R.NET_LABEL in ep.lineup and len(ep.lineup) == ep.n_players
        labels, suspects = seat_lineup(ep.lineup)
        assert list(labels) == list(ep.lineup)  # already in seat order
        for label, suspect in zip(labels, suspects):
            if label in R.CHARACTERS:
                assert suspect == label  # a character plays its own token
        assert len([l for l in ep.lineup if l in R.CHARACTERS]) == len({l for l in ep.lineup if l in R.CHARACTERS})


def test_draw_lineup_mixes_the_population_with_at_least_one_network_seat():
    rng = random.Random(3)
    draws = [R.draw_lineup(rng, 4, 0.0) for _ in range(200)]
    assert all(R.NET_LABEL in d and len(d) == 4 for d in draws)
    assert all(len([l for l in d if l in R.CHARACTERS]) == len({l for l in d if l in R.CHARACTERS}) for d in draws)
    assert any(R.FLOOR_LABEL in d for d in draws) and any(any(l in R.CHARACTERS for l in d) for d in draws)
    assert all(R.draw_lineup(rng, 5, 1.0) == [R.NET_LABEL] * 5 for _ in range(10))


def test_playing_with_swaps_the_registry_plums_weights(weights):
    from clude_agents import build_agent

    before = build_agent("Plum").weights
    with dn.playing_with(weights):
        assert build_agent("Plum").weights is weights
    assert build_agent("Plum").weights is before
    with pytest.raises(ValueError):
        with dn.playing_with({"trunk1_w": weights["trunk1_w"]}):
            pass


@pytest.fixture(scope="module")
def train_plum():
    """The training script as a module, with pytest's faulthandler off
    while it is in use: on Windows that handler reports a first-chance
    access violation inside torch's MKL as "Windows fatal exception",
    which torch itself handles and the tests survive, but the noise
    hides the real result (2026-10-06)."""
    pytest.importorskip("torch")
    faulthandler.disable()
    sys.path.insert(0, str(ROOT / "scripts"))
    import train_plum as T

    yield T
    faulthandler.enable()


def test_torch_network_matches_the_numpy_forward_pass(train_plum, weights):
    import torch

    T = train_plum
    episodes = R.play_games(weights, [60], 0, R.RolloutConfig(self_play=1.0, max_turns=40))
    ep = episodes[0]
    i = int(np.flatnonzero(ep.kinds == R.KIND_MOVE)[0])
    x = ep.states[i].astype(np.float64)
    numpy_heads = dn.forward(weights, x)
    numpy_moves = dn.move_scores(weights, numpy_heads["hidden"], ep.options[i].astype(np.float64))
    net = T.PlumNet.from_numpy(weights)
    with torch.no_grad():
        h = net.trunk(torch.as_tensor(x[None], dtype=torch.float32))
        heads = net.heads(h)
        moves = net.move_logits(h, torch.as_tensor(ep.options[i][None]), torch.ones(1, len(ep.options[i]), dtype=torch.bool))
    assert abs(heads["belief"][0].numpy() - numpy_heads["belief"]).max() < 1e-5
    assert abs(float(heads["value"][0]) - numpy_heads["value"]) < 1e-5
    assert abs(moves[0].numpy() - numpy_moves).max() < 1e-5
    back = net.to_numpy()
    assert all(abs(back[k] - weights[k]).max() < 1e-6 for k in weights)


def test_training_loop_writes_a_curve_and_exports_the_documented_layout(train_plum, tmp_path):
    T = train_plum
    out = tmp_path / "run"
    args = T.parse_args([
        "--iterations", "2", "--games", "6", "--workers", "1", "--max-turns", "40",
        "--eval-every", "2", "--eval-games", "3", "--bench-games", "3", "--minibatch", "256",
        "--out", str(out), "--seed", "5", "--quiet",
    ])
    last = T.train(args)
    lines = [json.loads(l) for l in (out / "curve.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [l["iteration"] for l in lines] == [1, 2] and last == lines[-1]
    assert set(lines[0]["loss"]) == {"policy", "value", "belief", "entropy"}
    assert lines[0]["rollout"]["games"] == 6 and lines[0]["steps"] > 0
    assert "eval" in lines[1] and set(lines[1]["eval"]["log_loss"]) == {"0.25", "0.5", "0.75", "1.0"}
    assert lines[1]["eval"]["plum_table"]["games"] == 3
    assert (out / "config.json").exists() and (out / "best.npz").exists()
    for name in ("latest.npz", "checkpoint-000002.npz"):
        back = dn.load_weights(out / name)
        assert {k: v.shape for k, v in back.items()} == dn.WEIGHT_SHAPES
    # the trained weights play through the ordinary agent
    agent = dn.DeepNashAgent(dn.load_weights(out / "latest.npz"))
    agent.reset(0)
    ep = R.play_games(dn.load_weights(out / "latest.npz"), [70], 0, R.RolloutConfig(self_play=1.0, max_turns=20))
    assert ep and len(ep[0]) > 0
