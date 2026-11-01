"""Capture Phase 14's pre-training benchmark and arenas, and benchmark the
six released methods together on the Run 3 snapshots (2026-11-01)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from clude_agents import build_agent
from clude_agents.bandit import BanditAgent
from clude_agents.decision_tree import DecisionTreeAgent
from clude_agents.markov import MarkovAgent
from clude_training import memory as method_memory
from clude_training.arena import DEFAULT_ROSTER, run_arena
from clude_training.benchmark import run_benchmark
from clude_training.recalibration import FrozenCorpus, experiment_context, load_staged_methods

PLUM_TABLE = ("Plum", "Mustard", "Green")
SIX = ("Scarlett", "Mustard", "White", "Green", "Peacock", "Plum")
SIX_GAMES = 120
SIX_SEED = 641600
ARENA_SIX_GAMES = 480
ARENA_SIX_SEED = 143400
"""Phase 14's Plum benchmark: 120 floor-player games at seed 641600 give the
2,160 snapshots Run 3 was scored on, so the six methods are scored on the
same positions."""


def _atomic_json(path: Optional[Path], value: dict) -> None:
    if path is None:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def capture_baseline(
    corpus: FrozenCorpus,
    *,
    output: Optional[Path] = None,
    benchmark_games: int = 60,
    arena_games: int = 192,
    benchmark_seed: int = 141300,
    arena_seed: int = 241300,
) -> dict:
    """Measure the frozen current methods without reading the live store."""
    mustard_doc = corpus.baseline_method("Mustard") or method_memory.empty_memory("rows")
    white_doc = corpus.baseline_method("White") or method_memory.empty_memory("counts")
    green_doc = corpus.baseline_method("Green") or method_memory.empty_memory("state")
    agents = {name: build_agent(name) for name in ("Scarlett", "Plum", "Peacock")}
    agents.update({
        "Mustard": DecisionTreeAgent(extra_rows=method_memory.extra_rows(mustard_doc)),
        "White": MarkovAgent(priors=method_memory.priors(white_doc)),
        "Green": BanditAgent(),
    })
    green_state = {"arms": green_doc.get("arms", {})}
    benchmark = run_benchmark(
        n_games=benchmark_games,
        seed=benchmark_seed,
        agents=agents,
        agent_states={"Green": green_state},
    )

    def overrides():
        return {
            "Mustard": DecisionTreeAgent(extra_rows=method_memory.extra_rows(mustard_doc)),
            "White": MarkovAgent(priors=method_memory.priors(white_doc)),
            "Green": BanditAgent(),
        }

    plum_table = run_arena(
        n_games=arena_games,
        seed=arena_seed,
        roster=PLUM_TABLE,
        player_counts=(3,),
        agent_overrides={key: value for key, value in overrides().items() if key in PLUM_TABLE},
        agent_states={"Green": green_state},
        run_id=f"phase14-baseline-plum-table-{arena_seed}",
    )
    six = run_arena(
        n_games=arena_games,
        seed=arena_seed,
        roster=DEFAULT_ROSTER,
        agent_overrides=overrides(),
        agent_states={"Green": green_state},
        run_id=f"phase14-baseline-six-{arena_seed}",
    )
    result = {
        "phase": 14,
        "corpus_sha256": corpus.sha256,
        "context": experiment_context(corpus.root / "manifest.json"),
        "method_sha256": corpus.manifest["baseline"]["method_sha256"],
        "benchmark": benchmark.to_dict(),
        "plum_table": plum_table.to_dict(),
        "six_character": six.to_dict(),
        "complete": True,
    }
    _atomic_json(output, result)
    return result
def _three(value) -> str:
    return "-" if value is None else f"{value:.3f}"


def glossary_rows(benchmark: dict) -> list[str]:
    """Markdown rows in the Run 3 table's format, best final log-loss first:
    ``| Method | 25% | 50% | 75% | 100% | Top-1 at 100% | ms per call at 50% |``."""
    rows = []
    per_agent = benchmark["per_agent"]
    order = sorted(per_agent, key=lambda name: per_agent[name]["1.0"]["log_loss"])
    for name in order:
        cells = per_agent[name]
        label = "uniform (baseline)" if name == "uniform" else name
        ms = cells["0.5"].get("ms_per_call") if name != "uniform" else None
        rows.append(
            f"| {label} | " + " | ".join(_three(cells[k]["log_loss"]) for k in ("0.25", "0.5", "0.75", "1.0"))
            + f" | {_three(cells['1.0']['top1_accuracy'])} | {_three(ms)} |"
        )
    return rows


def benchmark_six(
    stage_dir: Path,
    *,
    output: Optional[Path] = None,
    games: int = SIX_GAMES,
    seed: int = SIX_SEED,
    corpus_manifest: Optional[Path] = None,
    expected: Optional[dict] = None,
) -> dict:
    """Score the six methods as released, plus the floor's uniform baseline,
    on one set of floor-player snapshots.

    Mustard, White and Green are built from the hash-checked staged
    documents (`load_staged_methods`), as `capture_baseline` builds them;
    Scarlett, Peacock and Plum come from the registry, Plum with the
    committed weights. Nothing is read from or written to a store. With
    `expected` -- ``{"uniform": {...}, "Plum": {...}}`` rows of an earlier
    run at the same seed and size, as `BenchmarkResult.to_dict()` lays
    them out -- the matching rows must agree to three decimals, which
    proves the snapshots are the same ones.

    Raises
    ------
    ValueError
        If the stage is missing a method, or an `expected` row disagrees.
    """
    stage, documents = load_staged_methods(stage_dir)
    missing = sorted({"Mustard", "White", "Green"} - set(documents))
    if missing:
        raise ValueError(f"the stage is missing {missing}")
    agents = {name: build_agent(name) for name in ("Scarlett", "Peacock", "Plum")}
    agents.update({
        "Mustard": DecisionTreeAgent(extra_rows=method_memory.extra_rows(documents["Mustard"])),
        "White": MarkovAgent(priors=method_memory.priors(documents["White"])),
        "Green": BanditAgent(),
    })
    green_state = {"arms": documents["Green"].get("arms", {})}
    result = run_benchmark(n_games=games, seed=seed, agents=agents, agent_states={"Green": green_state})
    benchmark = result.to_dict()
    for name, row in (expected or {}).items():
        for checkpoint, cells in row.items():
            got = benchmark["per_agent"][name][checkpoint]
            for key in ("log_loss", "top1_accuracy"):
                if round(got[key], 3) != round(cells[key], 3):
                    raise ValueError(
                        f"{name} at {checkpoint}: {key} {got[key]:.3f} differs from the expected {cells[key]:.3f}"
                    )
    document = {
        "phase": 14,
        "kind": "six-method-benchmark",
        "games": games,
        "seed": seed,
        "context": experiment_context(corpus_manifest),
        "method_stage_sha256": stage["documents"],
        "benchmark": benchmark,
        "glossary_rows": glossary_rows(benchmark),
        "checked_against": sorted(expected or {}),
        "complete": True,
    }
    _atomic_json(output, document)
    return document
def _pct(value) -> str:
    return f"{100 * value:.1f}"


def arena_rows(arena: dict) -> list[str]:
    """One Markdown row per character in the Phase 14 control's format:
    ``| Character | Seat-games | Won % | Accused wrongly % | First accusation
    (turn) | Never accused % | Own cards shown | Own cards named | Re-shown % |``."""
    rows = []
    for name in SIX:
        stats = arena["per_player"].get(name)
        if stats is None:
            continue
        first = stats["mean_first_accusation_turn"]
        rows.append(
            f"| {name} | {stats['games']} | {_pct(stats['win_rate'])} | {_pct(stats['wrong_accusation_rate'])} | "
            f"{'-' if first is None else f'{first:.1f}'} | {_pct(stats['never_accused_rate'])} | "
            f"{stats['mean_cards_leaked']:.2f} | {stats['mean_own_cards_named']:.2f} | {_pct(stats['reshow_rate'])} |"
        )
    return rows


def arena_six(
    stage_dir: Path,
    *,
    output: Optional[Path] = None,
    games: int = ARENA_SIX_GAMES,
    seed: int = ARENA_SIX_SEED,
    corpus_manifest: Optional[Path] = None,
    store=None,
) -> dict:
    """Play the six characters as released against one another, headless,
    cycling three- to six-seat tables, for the biographies' infobox record.

    Mustard, White and Green come from the hash-checked staged documents,
    the rest from the registry (Plum with the committed weights); nothing is
    read from or written to a logbook store. With `store`, every game's
    record is kept under ``arena-six-<seed>``.

    Raises
    ------
    ValueError
        If the stage is missing a method.
    """
    stage, documents = load_staged_methods(stage_dir)
    missing = sorted({"Mustard", "White", "Green"} - set(documents))
    if missing:
        raise ValueError(f"the stage is missing {missing}")
    overrides = {
        "Mustard": DecisionTreeAgent(extra_rows=method_memory.extra_rows(documents["Mustard"])),
        "White": MarkovAgent(priors=method_memory.priors(documents["White"])),
        "Green": BanditAgent(),
    }
    states = {"Green": {"arms": documents["Green"].get("arms", {})}}
    result = run_arena(
        n_games=games, seed=seed, roster=DEFAULT_ROSTER, player_counts=(3, 4, 5, 6),
        agent_overrides=overrides, agent_states=states, store=store, run_id=f"arena-six-{seed}",
    )
    arena = result.to_dict()
    document = {
        "phase": 14,
        "kind": "six-character-arena",
        "games": games,
        "seed": seed,
        "player_counts": [3, 4, 5, 6],
        "context": experiment_context(corpus_manifest),
        "method_stage_sha256": stage["documents"],
        "mean_turns": result.mean_turns,
        "arena": arena,
        "glossary_rows": arena_rows(arena),
        "complete": True,
    }
    _atomic_json(output, document)
    return document
