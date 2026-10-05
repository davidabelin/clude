"""Phase 12, N4: the trainer (`scripts/train_plum.py`). Skipped without
torch, which is a developer dependency only (`requirements.txt`)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def trainer():
    spec = importlib.util.spec_from_file_location("train_plum", REPO / "scripts" / "train_plum.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_torch_net_mirrors_the_numpy_forward_pass(trainer):
    from clude_agents import deep_nash
    from clude_training import rollout

    weights = deep_nash.init_weights(seed=9, head_scale=1.0)
    net = trainer.TorchNet.from_numpy(weights)
    back = net.to_numpy()
    assert set(back) == set(deep_nash.WEIGHT_SHAPES)
    assert all(np.abs(back[k] - weights[k]).max() < 1e-6 for k in weights)

    trace = rollout.play_one(weights, seed=3, n_players=4, population="self", max_turns=40)
    batch = trainer.stack_traces([trace])
    states = torch.as_tensor(batch["states"], dtype=torch.float32)
    with torch.no_grad():
        hidden = net.trunk(states)
        heads = net.heads(hidden)
        logits, _h, _heads = trainer.option_logits(net, batch, torch.device("cpu"))
    for i, d in enumerate(trace.decisions):
        ref = deep_nash.forward(weights, d.state)
        assert np.abs(heads["belief"][i].numpy() - ref["belief"]).max() < 1e-4
        assert abs(float(heads["value"][i]) - ref["value"]) < 1e-4
        rows = batch["row_decision"] == i
        if d.head == "move":
            expected = deep_nash.move_scores(weights, ref["hidden"], d.choices)
        else:
            expected = ref[d.head][d.candidates]
        assert np.abs(logits[rows].numpy() - expected).max() < 1e-4
    assert batch["row_action"].sum() == len(trace.decisions)


def test_a_short_run_fits_what_it_sees_and_leaves_its_records(trainer, tmp_path):
    from clude_agents import deep_nash
    from clude_training import rollout

    out = tmp_path / "run"
    export = tmp_path / "plum.npz"
    # One batch, fitted hard: a few hundred games of untrained play carry
    # no envelope signal a held-out batch would show (the smoke run in
    # docs/deepnash-plan.md 11 is where generalisation is measured), but
    # the plumbing must at least fit what it is shown.
    args = trainer.parse_args([
        "--games", "16", "--batch", "16", "--epochs", "30", "--workers", "1", "--seed", "11",
        "--lr", "3e-3", "--max-turns", "40", "--eval-every", "1", "--eval-games", "2", "--bench-games", "2",
        "--out", str(out), "--export", str(export), "--quiet",
    ])
    seeds = [args.seed * 100_003 + i for i in range(args.batch)]
    seen = trainer.stack_traces(rollout.rollout_batch(
        deep_nash.init_weights(args.seed), seeds, trainer.table_size, "mixed", 1, 40,
    ))
    device = torch.device("cpu")

    def belief_on(weights):
        net = trainer.TorchNet.from_numpy(weights)
        with torch.no_grad():
            return float(trainer.losses(net, net, seen, args, device)["belief"])

    before = belief_on(deep_nash.init_weights(args.seed))
    final = trainer.train(args)
    assert set(final) == set(deep_nash.WEIGHT_SHAPES)
    after = belief_on(final)
    assert after < before - 0.1, (before, after)
    curve = [json.loads(line) for line in (out / "curve.jsonl").read_text().splitlines()]
    assert len(curve) == 1 and curve[-1]["games"] == 16
    assert set(curve[0]) >= {"policy", "value", "belief", "entropy", "kl_ref", "net_reward", "capped", "self_play"}
    evals = [json.loads(line) for line in (out / "eval.jsonl").read_text().splitlines()]
    assert [e["update"] for e in evals] == [1]
    assert set(evals[-1]["tables"]) == {"tuned", "plum"} and "0.5" in evals[-1]["benchmark"]
    assert (out / "ckpt-0001.npz").exists() and (out / "final.npz").exists() and (out / "args.json").exists()
    loaded = deep_nash.load_weights(export)
    assert all(np.abs(loaded[k] - final[k]).max() < 1e-6 for k in final)
    agent = deep_nash.DeepNashAgent(loaded)
    agent.reset(0)

    resumed = trainer.parse_args([
        "--games", "16", "--batch", "8", "--workers", "2", "--resume", str(export), "--max-turns", "40",
        "--eval-every", "0", "--out", str(tmp_path / "run2"), "--quiet",
    ])
    trainer.train(resumed)
    curve = [json.loads(line) for line in (tmp_path / "run2" / "curve.jsonl").read_text().splitlines()]
    assert len(curve) == 2 and (tmp_path / "run2" / "final.npz").exists()
