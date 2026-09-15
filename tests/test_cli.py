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


def test_play_store_writes_a_record_and_logbook_commands_read_the_store(cli, capsys, tmp_path):
    from clude_storage import GameRecord, LocalStore, Logbook, LogbookEntry

    out = _run(
        cli, capsys, "play", *SMALL_GAME, "--roster", "Plum,Scarlett",
        "--store", str(tmp_path), "--run-id", "smoke",
    )
    assert "record: run smoke game 0 in" in out
    store = LocalStore(tmp_path)
    assert store.list_games("smoke") == [0]
    record = GameRecord.from_dict(store.get_game("smoke", 0))
    assert [s.kind for s in record.seats] == ["character", "character", "floor"]
    assert record.seats[0].profile["memory"] == 0.0
    out = _run(cli, capsys, "store", "--uri", str(tmp_path))
    assert "smoke: 1 game records" in out

    out = _run(cli, capsys, "logbook", "list", "--uri", str(tmp_path))
    assert "no logbooks" in out
    out = _run(cli, capsys, "logbook", "show", "--uri", str(tmp_path), "--identity", "Plum")
    assert "no logbook for Plum" in out

    Logbook(store, "Plum").add_entry(LogbookEntry.build(
        "Plum", 1, record, 0,
        {"title": "First night", "summary": "Short.", "flags": ["opening"],
         "standing_instructions": ["Leave cleared rooms."],
         "dossiers": [{"opponent": "Scarlett", "read": "Accuses early."}]},
    ))
    out = _run(cli, capsys, "logbook", "list", "--uri", str(tmp_path))
    assert "Plum: 1 entries; 1 games:" in out
    out = _run(cli, capsys, "logbook", "show", "--uri", str(tmp_path), "--identity", "Plum")
    assert "head: serial 1" in out and "#0001" in out and "First night" in out
    assert "Your read on Scarlett" in out
    out = _run(cli, capsys, "logbook", "show", "--uri", str(tmp_path), "--identity", "Plum", "--entry", "1")
    assert out.startswith("=== Entry #0001")
    out = _run(cli, capsys, "logbook", "show", "--uri", str(tmp_path), "--identity", "Plum", "--memory", "1")
    assert "Full entries" in out
    out = _run(cli, capsys, "logbook", "show", "--uri", str(tmp_path), "--identity", "Plum", "--raw")
    assert json.loads(out)["serial"] == 1
    with pytest.raises(SystemExit):
        cli.main(["logbook", "show", "--uri", str(tmp_path), "--identity", "Plum", "--entry", "7"])
    out = _run(cli, capsys, "logbook", "reset", "--uri", str(tmp_path), "--identity", "Plum", "--keep-entries")
    assert "1 documents removed (entries kept)" in out
    out = _run(cli, capsys, "logbook", "reset", "--uri", str(tmp_path), "--identity", "Plum")
    assert "1 documents removed" in out
    out = _run(cli, capsys, "logbook", "list", "--uri", str(tmp_path))
    assert "no logbooks" in out or "Plum: 0 entries" in out


def test_play_and_arena_with_logbooks_feed_method_memory(cli, capsys, tmp_path):
    from clude_storage import GameRecord, LocalStore, Logbook
    from clude_training import memory

    uri = str(tmp_path)
    game = ("play", "--players", "3", "--seed", "3", "--max-turns", "40", "--roster", "Mustard,White,Green")
    with pytest.raises(SystemExit):
        cli.main([*game, "--logbook"])  # no store to default to
    out = _run(cli, capsys, *game, "--store", uri, "--run-id", "m1", "--logbook")
    assert "method memory updated for Mustard, White, Green" in out
    out = _run(cli, capsys, *game, "--seed", "4", "--store", uri, "--run-id", "m2", "--logbook")
    assert "method memory updated for Mustard, White, Green" in out
    out = _run(cli, capsys, *game, "--seed", "5", "--logbook", uri, "--logbook-readonly")
    assert "read-only, nothing written" in out
    store = LocalStore(tmp_path)
    assert memory.n_games(Logbook(store, "Mustard").method()) == 2

    out = _run(cli, capsys, "logbook", "list", "--uri", uri)
    assert "Mustard's tree:" in out and "from 2 stored games" in out
    assert "White's chains: 2 stored games" in out and "Green's posteriors after 2 games" in out
    out = _run(cli, capsys, "logbook", "show", "--uri", uri, "--identity", "White")
    assert "method memory: White's chains" in out
    out = _run(cli, capsys, "logbook", "rebuild", "--uri", uri, "--identity", "Mustard")
    assert "rebuilt from 2 game records" in out
    out = _run(cli, capsys, "logbook", "rebuild", "--uri", uri, "--identity", "Green")
    assert "accumulated live" in out
    out = _run(cli, capsys, "logbook", "rebuild", "--uri", uri, "--identity", "Plum")
    assert "memoryless" in out

    out = _run(
        cli, capsys, "arena", "--games", "2", "--players", "3", "--roster", "Mustard,floor",
        "--seed", "3", "--logbook", uri,
    )
    assert "logbooks: " in out and "(read and written)" in out and "loaded at the start for Mustard" in out
    assert memory.n_games(Logbook(store, "Mustard").method()) == 4
    out = _run(
        cli, capsys, "sweep", "--dial", "memory", "--values", "0", "1", "--games", "1", "--seed", "3",
        "--players", "3", "--roster", "Mustard,floor", "--logbook", uri,
    )
    assert "sweep of memory on Mustard" in out
    assert memory.n_games(Logbook(store, "Mustard").method()) == 4
    out = _run(
        cli, capsys, "train-mustard", "--games", "2", "--seed", "7", "--max-depth", "3",
        "--min-samples-leaf", "5", "--eval-games", "0", "--logbook", uri,
    )
    assert "memory rows from 4 stored games" in out

    # An LLM seat on the null backend writes no entry, and says so.
    out = _run(
        cli, capsys, "play", "--players", "3", "--seed", "3", "--max-turns", "40",
        "--roster", "Scarlett,floor", "--llm", "--llm-backend", "null", "--logbook", uri,
    )
    assert "Scarlett wrote no entry (error: null backend" in out
    out = _run(cli, capsys, "prompt", "--players", "3", "--seed", "3", "--roster", "Scarlett,floor",
               "--logbook", uri)
    assert "=== memory: Scarlett has nothing to read back" in out
    from clude_storage import LogbookEntry
    record = GameRecord.from_dict(store.get_game("m1", 0))
    Logbook(store, "Mustard").add_entry(LogbookEntry.build(
        "Mustard", 1, record, 0, {"standing_instructions": ["Bluster less."], "summary": "S.", "flags": ["x"]},
    ))
    out = _run(cli, capsys, "prompt", "--players", "3", "--seed", "3", "--roster", "Mustard,White,Green",
               "--logbook", uri, "--memory", "0.5")
    assert "=== memory (" in out and "Bluster less." in out and "Entries #0001 to #0001" in out
    with pytest.raises(SystemExit):
        cli.main(["train-mustard", "--games", "2", "--seed", "7", "--eval-games", "0", "--logbook", str(tmp_path / "empty")])


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
        cli.main(["arena", "--games", "1", "--set", "Scarlett.charm=1"])
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


def test_play_with_llm_seats_on_the_null_backend_matches_the_headless_game(cli, capsys):
    roster = ("--roster", "Scarlett,Peacock")
    plain = _run(cli, capsys, "play", *SMALL_GAME, *roster, "--verbose")
    llm = _run(cli, capsys, "play", *SMALL_GAME, *roster, "--verbose", "--llm", "--llm-backend", "null")
    assert "LLM seats:" in llm and "backend null" in llm and "0 remarks" in llm
    assert llm.split("\nLLM seats:")[0] == plain  # the null backend is the headless twin, line for line
    subset = _run(
        cli, capsys, "play", *SMALL_GAME, *roster, "--llm", "--llm-backend", "null",
        "--llm-characters", "Peacock",
    )
    trailer = subset.split("LLM seats:")[1]
    assert trailer.count(" decisions,") == 1 and "P1 Mustard (Peacock)" in trailer
    with pytest.raises(SystemExit):
        cli.main(["play", *SMALL_GAME, *roster, "--llm", "--llm-backend", "bogus"])
    with pytest.raises(SystemExit):
        cli.main(["play", *SMALL_GAME, *roster, "--llm", "--llm-backend", "null", "--llm-characters", "Nobody"])


def test_prompt_prints_the_system_and_user_prompt_without_calling(cli, capsys):
    out = _run(cli, capsys, "prompt", *SMALL_GAME, "--roster", "Scarlett,Peacock", "--viewer", "1", "--at", "2")
    assert "=== system" in out and "persona" in out and "Mrs. Peacock" in out
    assert "=== user" in out and "seat P1, after k=2" in out
    assert "Suspect options" in out and "Answer with JSON only" in out
    move = _run(cli, capsys, "prompt", *SMALL_GAME, "--roster", "Scarlett,Peacock", "--decision", "move", "--roll", "3")
    assert "Decision: where to move." in move
    for decision in ("accuse", "show"):
        assert "=== user" in _run(cli, capsys, "prompt", *SMALL_GAME, "--roster", "Scarlett,Peacock", "--decision", decision)
    borrowed = _run(cli, capsys, "prompt", *SMALL_GAME, "--roster", "Scarlett,Peacock", "--viewer", "2", "--agent", "Plum")
    assert "Professor Plum" in borrowed and "playing the White token" in borrowed
    with pytest.raises(SystemExit):
        cli.main(["prompt", *SMALL_GAME, "--roster", "Scarlett,Peacock", "--viewer", "2"])
    with pytest.raises(SystemExit):
        cli.main(["prompt", *SMALL_GAME, "--roster", "Scarlett,Peacock", "--at", "999"])


def test_arena_and_sweep_take_llm_seats_on_the_null_backend(cli, capsys, tmp_path):
    out = _run(
        cli, capsys, "arena", "--games", "2", "--seed", "3", "--roster", "Scarlett,White",
        "--players", "3", "--max-turns", "40", "--llm", "--llm-backend", "null",
        "--store", str(tmp_path), "--json", str(tmp_path / "a.json"),
    )
    assert "LLM seats:" in out and "fallb%" in out and "estimated LLM cost" in out
    assert (tmp_path / "runs" / "llm-3-2.json").exists()
    data = json.loads((tmp_path / "a.json").read_text(encoding="utf-8"))
    assert data["llm"]["backend"] == "null" and data["per_player"]["Scarlett"]["kind"] == "llm"
    assert data["per_player"]["Scarlett"]["fallback_rate"] == 1.0
    out = _run(
        cli, capsys, "sweep", "--dial", "leash", "--values", "0", "1", "--games", "1", "--seed", "3",
        "--roster", "Scarlett,floor", "--players", "3", "--max-turns", "40", "--llm", "--llm-backend", "null",
    )
    assert "sweep of leash on Scarlett" in out and "deviate%" in out
    with pytest.raises(SystemExit):
        cli.main([
            "arena", "--games", "1", "--roster", "Scarlett,floor", "--players", "3",
            "--llm", "--llm-backend", "null", "--llm-characters", "Plum",
        ])
