"""Smoke tests for `scripts/clude_cli.py`: every subcommand runs end to
end on a tiny configuration and prints the landmarks docs/cli.md
describes. Deeper checks of the underlying functions live in
`tests/test_training.py` (trace, benchmark), `tests/test_arena.py`
(arena, sweep), `tests/test_storage.py` and `tests/test_agents.py`.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "clude_cli.py"


@pytest.fixture(scope="module")
def cli():
    spec = importlib.util.spec_from_file_location("clude_cli", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(cli, capsys, *argv) -> str:
    assert cli.main(list(argv)) == 0
    return capsys.readouterr().out


SMALL_GAME = ("--players", "3", "--seed", "1", "--max-turns", "40")


def test_agents_lists_all_six_with_their_dials(cli, capsys):
    out = _run(cli, capsys, "agents")
    for name in ("Scarlett", "Plum", "Peacock", "Mustard", "Green", "White"):
        assert name in out
    assert "accuse_threshold=" in out
    assert "accuses on DS belief" in out


def test_play_verbose_prints_events_and_outcome(cli, capsys):
    out = _run(cli, capsys, "play", *SMALL_GAME, "--verbose", "--hands")
    assert "turn 1:" in out
    assert "Envelope:" in out
    assert "dealt hands" in out


def test_play_with_a_character_roster(cli, capsys):
    out = _run(cli, capsys, "play", *SMALL_GAME, "--roster", "Plum,Scarlett", "--verbose")
    assert "seats: P0 Scarlett (Plum), P1 Mustard (Scarlett), P2 White (floor)" in out
    assert "suggests" in out
    out = _run(cli, capsys, "play", *SMALL_GAME, "--roster", "floor")
    assert "roster=floor" in out
    with pytest.raises(SystemExit):
        cli.main(["play", *SMALL_GAME, "--roster", "Nobody"])


def test_trace_prints_every_step_and_the_accusation_test(cli, capsys):
    out = _run(
        cli, capsys, "trace", *SMALL_GAME, "--agents", "Scarlett,Peacock", "--every", "5",
    )
    assert "--- k=0:" in out
    assert "Scarlett" in out and "Peacock" in out
    assert "bel/pl of top" in out  # Peacock's extra
    assert "P(correct)=" in out
    assert "steps x 2 agents" in out


def test_trace_rejects_unknown_agent(cli):
    with pytest.raises(SystemExit):
        cli.main(["trace", *SMALL_GAME, "--agents", "Nobody"])


def test_floor_grid_and_convergence(cli, capsys):
    grid = _run(cli, capsys, "floor", *SMALL_GAME, "--at", "3")
    assert "Env" in grid
    assert "envelope proven:" in grid
    assert "after k=3" in grid

    convergence = _run(cli, capsys, "floor", *SMALL_GAME, "--convergence")
    assert "first k with the envelope proven" in convergence


def test_floor_rejects_out_of_range_checkpoint(cli):
    with pytest.raises(SystemExit):
        cli.main(["floor", *SMALL_GAME, "--at", "9999"])


def test_benchmark_subset_json_export_and_bot_switch(cli, capsys, tmp_path):
    path = tmp_path / "bench.json"
    out = _run(
        cli, capsys, "benchmark", "--games", "2", "--seed", "5", "--checkpoints", "1.0",
        "--agents", "Scarlett,Plum", "--players", "3", "--json", str(path), "--bot", "random",
    )
    assert "Scarlett" in out and "uniform" in out
    assert "random-bot games" in out
    assert "Plum fell back to sampling" in out
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["n_games"] == 2
    assert data["bot"] == "random"
    assert set(data["per_agent"]) == {"Scarlett", "Plum", "uniform"}
    assert data["per_agent"]["Scarlett"]["1.0"]["n_calls"] == data["n_snapshots"]
    out = _run(cli, capsys, "benchmark", "--games", "2", "--seed", "5", "--agents", "White", "--players", "3")
    assert "floor-bot games" in out


def test_train_mustard_reports_tree_and_held_out_score(cli, capsys):
    out = _run(
        cli, capsys, "train-mustard", "--games", "2", "--seed", "7", "--max-depth", "3",
        "--min-samples-leaf", "5", "--render", "--eval-games", "1", "--eval-seed", "99",
    )
    assert "training set:" in out
    assert "floor-bot games" in out
    assert "tree:" in out
    assert "leaf p=" in out
    assert "held-out evaluation" in out
    assert "Mustard" in out and "uniform" in out


def test_train_mustard_warns_when_eval_seeds_overlap_training(cli, capsys):
    out = _run(
        cli, capsys, "train-mustard", "--games", "2", "--seed", "7",
        "--eval-games", "1", "--eval-seed", "7", "--bot", "random",
    )
    assert "WARNING" in out


def test_snapshots_describes_the_distribution(cli, capsys):
    out = _run(cli, capsys, "snapshots", "--games", "3", "--seed", "2", "--players", "3")
    assert "label_rate" in out
    assert "3 players: 3 games" in out
    assert "floor-bot games" in out


def test_arena_runs_stores_and_exports(cli, capsys, tmp_path):
    store = tmp_path / "records"
    path = tmp_path / "arena.json"
    out = _run(
        cli, capsys, "arena", "--games", "2", "--seed", "3", "--roster", "Scarlett,White",
        "--players", "3", "--max-turns", "40", "--store", str(store), "--run-id", "smoke",
        "--set", "Scarlett.accuse_threshold=0.9", "--json", str(path),
    )
    assert "Scarlett" in out and "floor" in out
    assert "win%" in out and "decided by a correct accusation" in out
    assert "records: run smoke" in out
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["profiles"]["Scarlett"]["accuse_threshold"] == 0.9
    assert (store / "runs" / "smoke.json").exists()
    assert len(list((store / "games" / "smoke").glob("*.json"))) == 2

    listing = _run(cli, capsys, "store", "--uri", str(store))
    assert "smoke: 2 game records" in listing
    detail = _run(cli, capsys, "store", "--uri", str(store), "--run", "smoke")
    assert "run smoke: 2 games" in detail and "Scarlett" in detail
    with pytest.raises(SystemExit):
        cli.main(["arena", "--games", "1", "--set", "Scarlett.chattiness=1"])
    with pytest.raises(SystemExit):
        cli.main(["arena", "--games", "1", "--roster", "Nobody"])


def test_sweep_prints_a_row_per_value_and_a_verdict(cli, capsys):
    out = _run(
        cli, capsys, "sweep", "--dial", "accuse_threshold", "--values", "0.0", "1.0",
        "--games", "2", "--seed", "3", "--roster", "Scarlett,floor", "--players", "3",
        "--max-turns", "40",
    )
    assert "sweep of accuse_threshold on Scarlett" in out
    assert "monotone:" in out
    assert "2 values x 2 games" in out
    with pytest.raises(SystemExit):
        cli.main(["sweep", "--dial", "secrecy", "--values", "0.5", "--roster", "floor", "--games", "1"])
