"""Phase 14 evaluation and paired tournaments for Plum checkpoints."""
from __future__ import annotations

import hashlib
import json
import math
import random
from itertools import combinations
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
TOURNAMENT_VERSION = 1
TOURNAMENT_CONTEXTS = {
    "plum_table": {"roster": PLUM_TABLE, "player_counts": (3,)},
    "mixed_tables": {"roster": DEFAULT_ROSTER, "player_counts": (3, 4, 5, 6)},
}
BALANCED_TOURNAMENT_VERSION = 1
BALANCED_GAMES_PER_LINEUP = {3: 24, 4: 24, 5: 48, 6: 240}


def balanced_plum_lineups() -> tuple[dict, ...]:
    """All 26 rosters containing Plum, weighted equally by table size."""
    opponents = tuple(label for label in DEFAULT_ROSTER if label != "Plum")
    rows = []
    for n_players in (3, 4, 5, 6):
        games = BALANCED_GAMES_PER_LINEUP[n_players]
        for opponent_group in combinations(opponents, n_players - 1):
            roster = ("Plum",) + opponent_group
            rows.append({
                "id": f"{n_players}-" + "-".join(opponent_group),
                "n_players": n_players,
                "games": games,
                "roster": roster,
            })
    return tuple(rows)


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


def _plum_game_rows(result) -> list[dict]:
    """Keep the paired evidence needed by the tournament without full records."""
    rows = []
    for game in result.games:
        outcome = next(
            (item for item in game.seat_outcomes if item.label == "Plum"), None
        )
        if outcome is None:
            continue
        rows.append({
            "game_index": game.game_index,
            "seed": game.seed,
            "n_players": game.n_players,
            "won": outcome.won,
            "wrong_accusation": outcome.wrong_accusation,
            "turns": game.turns,
        })
    return rows


def _tournament_arena_summary(result) -> dict:
    stats = result.per_player["Plum"]
    return {
        "run_id": result.run_id,
        "games_run": result.n_games,
        "games_with_plum": stats.games,
        "seed": result.seed,
        "roster": list(result.roster),
        "player_counts": list(result.player_counts),
        "wins": stats.wins,
        "win_rate": stats.win_rate,
        "wrong_accusations": stats.games_with_wrong_accusation,
        "mean_turns": result.mean_turns,
        "games": _plum_game_rows(result),
    }


def _paired_win_interval(left: dict, right: dict, key: str, samples: int = 5000) -> dict:
    """Bootstrap right-minus-left win rate from their common game seeds."""
    left_games = {row["seed"]: row for row in left["games"]}
    right_games = {row["seed"]: row for row in right["games"]}
    seeds = sorted(set(left_games) & set(right_games))
    differences = [
        float(right_games[seed]["won"]) - float(left_games[seed]["won"])
        for seed in seeds
    ]
    if not differences:
        return {"delta": float("nan"), "low": float("nan"), "high": float("nan"), "n_pairs": 0}
    delta = sum(differences) / len(differences)
    if len(differences) == 1 or len(set(differences)) == 1:
        low = high = delta
    else:
        bootstrap_seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16)
        rng = random.Random(bootstrap_seed)
        means = sorted(
            sum(differences[rng.randrange(len(differences))] for _ in differences) / len(differences)
            for _ in range(samples)
        )
        low = means[max(0, math.floor(0.025 * (samples - 1)))]
        high = means[min(samples - 1, math.ceil(0.975 * (samples - 1)))]
    return {"delta": delta, "low": low, "high": high, "n_pairs": len(differences)}


def _benchmark_loss_gate(baseline: dict, candidate: dict) -> dict:
    baseline_cells = baseline["per_agent"]["Plum"]
    candidate_cells = candidate["per_agent"]["Plum"]
    rows = []
    for checkpoint, before in baseline_cells.items():
        after = candidate_cells[checkpoint]
        rows.append({
            "checkpoint": checkpoint,
            "baseline": before["log_loss"],
            "candidate": after["log_loss"],
            "delta": after["log_loss"] - before["log_loss"],
            "within_0.02": after["log_loss"] <= before["log_loss"] + 0.02,
        })
    return {"passes": all(row["within_0.02"] for row in rows), "rows": rows}


def _tournament_verdict(report: dict) -> dict:
    """Rank entrants, but name a winner only after all predeclared gates pass."""
    entrants = report["entrants"]
    incumbent = report["incumbent"]
    blocks = report["blocks"]
    benchmark = report["benchmark"]
    loss_gates = {
        name: (
            {"passes": True, "rows": []}
            if name == incumbent
            else _benchmark_loss_gate(benchmark[incumbent], benchmark[name])
        )
        for name in entrants
    }
    totals = {}
    for name in entrants:
        rows = [
            blocks[block][context][name]
            for block in blocks
            for context in TOURNAMENT_CONTEXTS
        ]
        games = sum(row["games_with_plum"] for row in rows)
        totals[name] = {
            "games": games,
            "wins": sum(row["wins"] for row in rows),
            "win_rate": sum(row["wins"] for row in rows) / games,
            "wrong_accusations": sum(row["wrong_accusations"] for row in rows),
            "loss_gate": loss_gates[name],
        }
    ranking = sorted(entrants, key=lambda name: (-totals[name]["win_rate"], name))
    confirmation = report["confirmation_block"]
    pairwise = {}
    for left in entrants:
        pairwise[left] = {}
        for right in entrants:
            if left == right:
                continue
            intervals = [
                _paired_win_interval(
                    blocks[confirmation][context][left],
                    blocks[confirmation][context][right],
                    f"{confirmation}|{context}|{left}|{right}",
                )
                for context in TOURNAMENT_CONTEXTS
            ]
            pairwise[left][right] = {
                "right_minus_left": intervals,
                "all_contexts_positive": all(row["low"] > 0 for row in intervals),
            }
    winner = ranking[0]
    safety_passes = (
        totals[winner]["wrong_accusations"] == 0
        and totals[winner]["loss_gate"]["passes"]
    )
    beats_every_rival = all(
        pairwise[rival][winner]["all_contexts_positive"]
        for rival in entrants if rival != winner
    )
    clear_winner = winner if safety_passes and beats_every_rival else None
    return {
        "ranking_by_pooled_win_rate": ranking,
        "totals": totals,
        "confirmation_pairwise": pairwise,
        "clear_winner": clear_winner,
        "decision": (
            f"{clear_winner} is the clear winner"
            if clear_winner
            else "no clear winner under the predeclared safety and paired-confidence gates"
        ),
        "winner_rule": (
            "zero wrong accusations across both blocks, benchmark log-loss no more than 0.02 "
            "above the incumbent at every checkpoint, and a positive lower 95% paired-bootstrap "
            "bound against every rival in each confirmation context"
        ),
    }


def run_plum_tournament(
    entrants: dict[str, Path],
    *,
    output: Path,
    corpus_manifest: Optional[Path] = None,
    benchmark_games: int = 120,
    benchmark_seed: int = 341700,
    selection_games: int = 384,
    selection_seed: int = 441700,
    confirmation_games: int = 768,
    confirmation_seed: int = 541700,
) -> dict:
    """Run or resume a two-block, paired four-way Plum tournament."""
    entrants = {name: Path(path) for name, path in entrants.items()}
    if "incumbent" not in entrants:
        raise ValueError("the tournament requires an entrant named 'incumbent'")
    if len(entrants) != 4:
        raise ValueError("the Phase 14 Plum tournament requires exactly four entrants")
    hashes = {name: file_hash(path) for name, path in entrants.items()}
    configuration = {
        "version": TOURNAMENT_VERSION,
        "entrants": {
            name: {"checkpoint": str(path), "weights_sha256": hashes[name]}
            for name, path in entrants.items()
        },
        "benchmark_games": benchmark_games,
        "benchmark_seed": benchmark_seed,
        "blocks": {
            "selection": {"games": selection_games, "seed": selection_seed},
            "confirmation": {"games": confirmation_games, "seed": confirmation_seed},
        },
        "contexts": {
            name: {
                "roster": list(value["roster"]),
                "player_counts": list(value["player_counts"]),
            }
            for name, value in TOURNAMENT_CONTEXTS.items()
        },
    }
    report = {
        "phase": 14,
        "experiment": "plum-four-way-tournament",
        "configuration": configuration,
        "context": experiment_context(corpus_manifest),
        "entrants": list(entrants),
        "incumbent": "incumbent",
        "selection_block": "selection",
        "confirmation_block": "confirmation",
        "benchmark": {},
        "blocks": {"selection": {}, "confirmation": {}},
        "complete": False,
        "verdict": None,
    }
    if output.exists():
        previous = json.loads(output.read_text(encoding="utf-8"))
        if previous.get("configuration") != configuration:
            raise ValueError("existing tournament output has a different configuration")
        report = previous
    for name, path in entrants.items():
        if name not in report["benchmark"]:
            weights = deep_nash.load_weights(path)
            result = run_benchmark(
                n_games=benchmark_games,
                seed=benchmark_seed,
                agents={"Plum": deep_nash.DeepNashAgent(weights)},
            )
            report["benchmark"][name] = result.to_dict()
            _atomic_json(output, report)
    for block_name, games, seed in (
        ("selection", selection_games, selection_seed),
        ("confirmation", confirmation_games, confirmation_seed),
    ):
        for context_name, context in TOURNAMENT_CONTEXTS.items():
            context_results = report["blocks"][block_name].setdefault(context_name, {})
            for name, path in entrants.items():
                if name in context_results:
                    continue
                weights = deep_nash.load_weights(path)
                result = run_arena(
                    n_games=games,
                    seed=seed,
                    roster=context["roster"],
                    player_counts=context["player_counts"],
                    run_id=f"phase14-plum-tournament-{block_name}-{context_name}-{name}",
                    agent_overrides={"Plum": deep_nash.DeepNashAgent(weights)},
                )
                context_results[name] = _tournament_arena_summary(result)
                _atomic_json(output, report)
    report["complete"] = True
    report["verdict"] = _tournament_verdict(report)
    _atomic_json(output, report)
    return report


def _balanced_game_rows(report: dict, block: str, entrant: str, n_players: Optional[int] = None) -> list[dict]:
    rows = []
    for lineup in report["configuration"]["lineups"]:
        if n_players is not None and lineup["n_players"] != n_players:
            continue
        summary = report["blocks"][block][lineup["id"]][entrant]
        rows.extend(summary["games"])
    return rows


def _balanced_interval(
    report: dict,
    block: str,
    left: str,
    right: str,
    *,
    n_players: Optional[int] = None,
) -> dict:
    before = {"games": _balanced_game_rows(report, block, left, n_players)}
    after = {"games": _balanced_game_rows(report, block, right, n_players)}
    size = "all" if n_players is None else str(n_players)
    return _paired_win_interval(before, after, f"balanced|{block}|{size}|{left}|{right}")


def _balanced_tournament_verdict(report: dict) -> dict:
    """Name a winner only from the untouched, equally weighted confirmation block."""
    entrants = report["entrants"]
    incumbent = report["incumbent"]
    confirmation = report["confirmation_block"]
    loss_gates = {
        name: (
            {"passes": True, "rows": []}
            if name == incumbent
            else _benchmark_loss_gate(report["benchmark"][incumbent], report["benchmark"][name])
        )
        for name in entrants
    }
    totals = {}
    for name in entrants:
        block_rows = {
            block: _balanced_game_rows(report, block, name)
            for block in (report["selection_block"], confirmation)
        }
        rows = block_rows[report["selection_block"]] + block_rows[confirmation]
        totals[name] = {
            "games": len(rows),
            "wins": sum(int(row["won"]) for row in rows),
            "win_rate": sum(int(row["won"]) for row in rows) / len(rows),
            "wrong_accusations": sum(int(row["wrong_accusation"]) for row in rows),
            "wrong_accusations_are_advisory": True,
            "loss_gate": loss_gates[name],
            "by_table_size": {
                str(size): {
                    "games": len(size_rows := [row for row in rows if row["n_players"] == size]),
                    "wins": sum(int(row["won"]) for row in size_rows),
                    "win_rate": sum(int(row["won"]) for row in size_rows) / len(size_rows),
                }
                for size in (3, 4, 5, 6)
            },
        }
    ranking = sorted(entrants, key=lambda name: (-totals[name]["win_rate"], name))
    pairwise = {}
    for left in entrants:
        pairwise[left] = {}
        for right in entrants:
            if left == right:
                continue
            pairwise[left][right] = {
                "right_minus_left": _balanced_interval(report, confirmation, left, right),
                "by_table_size": {
                    str(size): _balanced_interval(
                        report, confirmation, left, right, n_players=size,
                    )
                    for size in (3, 4, 5, 6)
                },
            }
    leader = ranking[0]
    beats_every_rival = all(
        pairwise[rival][leader]["right_minus_left"]["low"] > 0
        for rival in entrants if rival != leader
    )
    clear_winner = leader if loss_gates[leader]["passes"] and beats_every_rival else None
    return {
        "ranking_by_pooled_win_rate": ranking,
        "totals": totals,
        "confirmation_pairwise": pairwise,
        "clear_winner": clear_winner,
        "decision": (
            f"{clear_winner} is the clear balanced-tournament winner"
            if clear_winner
            else "no clear winner under the paired confirmation rule"
        ),
        "winner_rule": (
            "highest pooled win rate, benchmark log-loss no more than 0.02 above the incumbent "
            "at every checkpoint, and a positive lower 95% paired-bootstrap bound against "
            "every rival over the equally weighted confirmation block; wrong accusations are advisory"
        ),
    }


def run_balanced_plum_tournament(
    entrants: dict[str, Path],
    *,
    output: Path,
    corpus_manifest: Optional[Path] = None,
    benchmark_games: int = 120,
    benchmark_seed: int = 641600,
    selection_seed: int = 641700,
    confirmation_seed: int = 741700,
) -> dict:
    """Run or resume the paired 26-line-up Phase 14 Plum tournament."""
    entrants = {name: Path(path) for name, path in entrants.items()}
    if "incumbent" not in entrants:
        raise ValueError("the tournament requires an entrant named 'incumbent'")
    if len(entrants) != 4:
        raise ValueError("the Phase 14 Plum tournament requires exactly four entrants")
    lineups = balanced_plum_lineups()
    seed_blocks = {}
    for block, first_seed in (("selection", selection_seed), ("confirmation", confirmation_seed)):
        cursor = first_seed
        seed_blocks[block] = {}
        for lineup in lineups:
            seed_blocks[block][lineup["id"]] = cursor
            cursor += lineup["games"]
    hashes = {name: file_hash(path) for name, path in entrants.items()}
    configuration = {
        "version": BALANCED_TOURNAMENT_VERSION,
        "entrants": {
            name: {"checkpoint": str(path), "weights_sha256": hashes[name]}
            for name, path in entrants.items()
        },
        "benchmark_games": benchmark_games,
        "benchmark_seed": benchmark_seed,
        "selection_seed": selection_seed,
        "confirmation_seed": confirmation_seed,
        "games_per_block_per_entrant": sum(row["games"] for row in lineups),
        "lineups": [
            {**row, "roster": list(row["roster"])}
            for row in lineups
        ],
        "seed_blocks": seed_blocks,
    }
    report = {
        "phase": 14,
        "experiment": "plum-balanced-26-lineup-tournament",
        "configuration": configuration,
        "context": experiment_context(corpus_manifest),
        "entrants": list(entrants),
        "incumbent": "incumbent",
        "selection_block": "selection",
        "confirmation_block": "confirmation",
        "benchmark": {},
        "blocks": {"selection": {}, "confirmation": {}},
        "complete": False,
        "verdict": None,
    }
    if output.exists():
        previous = json.loads(output.read_text(encoding="utf-8"))
        if previous.get("configuration") != configuration:
            raise ValueError("existing balanced tournament output has a different configuration")
        report = previous
    for name, path in entrants.items():
        if name not in report["benchmark"]:
            result = run_benchmark(
                n_games=benchmark_games,
                seed=benchmark_seed,
                agents={"Plum": deep_nash.DeepNashAgent(deep_nash.load_weights(path))},
            )
            report["benchmark"][name] = result.to_dict()
            _atomic_json(output, report)
    for block in ("selection", "confirmation"):
        for lineup in lineups:
            lineup_results = report["blocks"][block].setdefault(lineup["id"], {})
            for name, path in entrants.items():
                if name in lineup_results:
                    continue
                result = run_arena(
                    n_games=lineup["games"],
                    seed=seed_blocks[block][lineup["id"]],
                    roster=lineup["roster"],
                    player_counts=(lineup["n_players"],),
                    run_id=f"phase14-plum-balanced-{block}-{lineup['id']}-{name}",
                    agent_overrides={
                        "Plum": deep_nash.DeepNashAgent(deep_nash.load_weights(path)),
                    },
                )
                lineup_results[name] = _tournament_arena_summary(result)
                _atomic_json(output, report)
    report["complete"] = True
    report["verdict"] = _balanced_tournament_verdict(report)
    _atomic_json(output, report)
    return report


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
