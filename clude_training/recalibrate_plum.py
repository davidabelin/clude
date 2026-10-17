"""Phase 14 evaluation of explicitly named Plum checkpoints."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from clude_agents import deep_nash
from clude_training.arena import DEFAULT_ROSTER, run_arena
from clude_training.benchmark import run_benchmark
from clude_training.recalibration import experiment_context, file_hash
from clude_training.sweep import SweepResult

PLUM_TABLE = ("Plum", "Mustard", "Green")
BENCHMARK_GAMES = 60
ARENA_GAMES = 192
BENCHMARK_SEED = 141700
ARENA_SEED = 241700


def _atomic_json(path: Optional[Path], value: dict) -> None:
    if path is None:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _measure(weights: dict, benchmark_games: int, arena_games: int, benchmark_seed: int, arena_seed: int):
    with deep_nash.playing_with(weights):
        benchmark = run_benchmark(
            n_games=benchmark_games,
            seed=benchmark_seed,
            agents={"Plum": deep_nash.DeepNashAgent(weights)},
        )
        plum_table = run_arena(
            n_games=arena_games,
            seed=arena_seed,
            roster=PLUM_TABLE,
            player_counts=(3,),
            run_id=f"phase14-plum-table-{arena_seed}",
        )
        six = run_arena(
            n_games=arena_games,
            seed=arena_seed,
            roster=DEFAULT_ROSTER,
            run_id=f"phase14-six-table-{arena_seed}",
        )
    return benchmark, plum_table, six


def _arena_summary(result) -> dict:
    stats = result.per_player["Plum"]
    return {
        "run_id": result.run_id,
        "games": result.n_games,
        "seed": result.seed,
        "player_counts": list(result.player_counts),
        "mean_turns": result.mean_turns,
        "Plum": stats.to_dict(),
    }


def evaluate_plum_checkpoints(
    checkpoints: Iterable[Path],
    *,
    output: Optional[Path] = None,
    benchmark_games: int = BENCHMARK_GAMES,
    arena_games: int = ARENA_GAMES,
    benchmark_seed: int = BENCHMARK_SEED,
    arena_seed: int = ARENA_SEED,
    corpus_manifest: Optional[Path] = None,
) -> dict:
    """Compare candidate checkpoints with current weights on untouched seeds."""
    checkpoints = [Path(path) for path in checkpoints]
    if not checkpoints:
        raise ValueError("at least one explicit Plum checkpoint is required")
    current = deep_nash.load_weights(deep_nash.WEIGHTS_PATH)
    baseline_benchmark, baseline_plum, baseline_six = _measure(
        current, benchmark_games, arena_games, benchmark_seed, arena_seed
    )
    report = {
        "method": "Plum",
        "context": experiment_context(corpus_manifest),
        "benchmark_games": benchmark_games,
        "arena_games": arena_games,
        "benchmark_seed": benchmark_seed,
        "arena_seed": arena_seed,
        "baseline": {
            "weights_sha256": file_hash(deep_nash.WEIGHTS_PATH),
            "benchmark": baseline_benchmark.to_dict(),
            "plum_table": _arena_summary(baseline_plum),
            "six_character": _arena_summary(baseline_six),
        },
        "candidates": [],
        "complete": False,
    }
    _atomic_json(output, report)
    for path in checkpoints:
        weights = deep_nash.load_weights(path)
        benchmark, plum_table, six = _measure(
            weights, benchmark_games, arena_games, benchmark_seed, arena_seed
        )
        loss_checks = []
        for checkpoint in benchmark.checkpoints:
            candidate_loss = benchmark.per_agent["Plum"][checkpoint].log_loss
            baseline_loss = baseline_benchmark.per_agent["Plum"][checkpoint].log_loss
            loss_checks.append({
                "checkpoint": checkpoint,
                "candidate": candidate_loss,
                "baseline": baseline_loss,
                "within_0.02": candidate_loss <= baseline_loss + 0.02,
            })
        arena_checks = []
        for name, baseline, candidate in (
            ("plum_table", baseline_plum, plum_table),
            ("six_character", baseline_six, six),
        ):
            before = baseline.per_player["Plum"]
            after = candidate.per_player["Plum"]
            paired = SweepResult(
                dial="accuse_threshold", values=(0.0, 1.0), characters=("Plum",),
                roster=baseline.roster, results=[baseline, candidate],
            ).paired_deltas()[1]
            arena_checks.append({
                "arena": name,
                "win_rate_delta": after.win_rate - before.win_rate,
                "wrong_accusations": after.games_with_wrong_accusation,
                "paired": paired,
                "passes": (
                    after.win_rate - before.win_rate >= -0.05
                    and after.games_with_wrong_accusation == 0
                ),
            })
        candidate = {
            "checkpoint": str(path),
            "weights_sha256": file_hash(path),
            "benchmark": benchmark.to_dict(),
            "plum_table": _arena_summary(plum_table),
            "six_character": _arena_summary(six),
            "loss_gate": {"passes": all(row["within_0.02"] for row in loss_checks), "rows": loss_checks},
            "arena_gate": {"passes": all(row["passes"] for row in arena_checks), "rows": arena_checks},
        }
        candidate["numerical_gate"] = candidate["loss_gate"]["passes"] and candidate["arena_gate"]["passes"]
        candidate["personality_gate"] = "pending human review"
        candidate["ready_for_promotion"] = False
        report["candidates"].append(candidate)
        _atomic_json(output, report)
    report["complete"] = True
    report["numerical_shortlist"] = [
        candidate["checkpoint"] for candidate in report["candidates"] if candidate["numerical_gate"]
    ]
    report["selected_checkpoint"] = None
    report["selection_note"] = "Select explicitly only after personality review; the trainer never exports."
    _atomic_json(output, report)
    return report
