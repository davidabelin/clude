"""Capture Phase 14's pre-training benchmark and arenas."""
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
from clude_training.recalibration import FrozenCorpus, experiment_context

PLUM_TABLE = ("Plum", "Mustard", "Green")


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
