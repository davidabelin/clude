"""Run Phase 14's headless pooled, isolated and confirmation dial sweeps."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clude_agents.bandit import BanditAgent
from clude_agents.decision_tree import DecisionTreeAgent
from clude_agents.markov import MarkovAgent
from clude_agents.personality import PRESETS
from clude_training import memory as method_memory
from clude_training.recalibration import (
    FrozenCorpus,
    experiment_context,
    load_staged_methods,
)
from clude_training.sweep import (
    PHASE14_HEADLESS_GRIDS,
    phase14_isolated_values,
    sweep_dial,
)

DEFAULT_CORPUS = ROOT / "data" / "phase14" / "corpus" / "manifest.json"
DEFAULT_STAGE = ROOT / "data" / "phase14" / "staged-methods"
DEFAULT_OUTPUT = ROOT / "data" / "phase14" / "sweeps"
INTERLEAVED_ROSTER = (
    "Scarlett", "floor", "Mustard", "floor", "White", "floor",
    "Green", "floor", "Peacock", "floor", "Plum", "floor",
)
SCREEN_DIALS = ("accuse_threshold", "bluff_rate", "curiosity", "secrecy", "temperature")


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _methods(stage_dir: Path) -> tuple[dict, dict, dict]:
    stage, documents = load_staged_methods(stage_dir)
    missing = sorted({"Mustard", "White", "Green"} - set(documents))
    if missing:
        raise ValueError(f"headless sweeps require accepted staged methods; missing {missing}")
    overrides = {
        "Mustard": DecisionTreeAgent(extra_rows=method_memory.extra_rows(documents["Mustard"])),
        "White": MarkovAgent(priors=method_memory.priors(documents["White"])),
        "Green": BanditAgent(),
    }
    states = {"Green": {"arms": documents["Green"].get("arms", {})}}
    return stage, overrides, states


def _context(manifest: Path, stage: dict) -> dict:
    return {
        **experiment_context(manifest),
        "method_stage_sha256": stage["documents"],
        "roster_design": "characters interleaved with FloorBot",
    }


def cmd_pooled(args) -> int:
    corpus = FrozenCorpus.open(args.manifest)
    stage, overrides, states = _methods(args.stage)
    context = _context(args.manifest, stage)
    summary = {"corpus_sha256": corpus.sha256, "sweeps": {}, "complete": False}
    _atomic_json(args.output / "pooled.json", summary)
    for dial, values in PHASE14_HEADLESS_GRIDS.items():
        path = args.output / "pooled" / f"{dial}.json"
        result = sweep_dial(
            dial, values, n_games=args.games, seed=args.seed, roster=INTERLEAVED_ROSTER,
            characters=None, metadata=context, agent_overrides=overrides, agent_states=states,
            run_id=f"phase14-pooled-{dial}",
            on_update=lambda partial, path=path: _atomic_json(path, partial.to_dict()),
        )
        data = result.to_dict()
        _atomic_json(path, data)
        summary["sweeps"][dial] = {
            "path": str(path), "complete": data["complete"],
            "characters": data["characters"], "not_applicable": data["not_applicable"],
        }
        _atomic_json(args.output / "pooled.json", summary)
    summary["complete"] = True
    _atomic_json(args.output / "pooled.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


def cmd_isolated(args) -> int:
    corpus = FrozenCorpus.open(args.manifest)
    stage, overrides, states = _methods(args.stage)
    context = _context(args.manifest, stage)
    summary = {"corpus_sha256": corpus.sha256, "screens": {}, "complete": False}
    _atomic_json(args.output / "isolated.json", summary)
    for character in PRESETS:
        for dial in SCREEN_DIALS:
            if character == "Plum" and dial == "curiosity":
                summary["screens"][f"{character}.{dial}"] = {"status": "N/A"}
                continue
            values = phase14_isolated_values(dial, getattr(PRESETS[character], dial))
            path = args.output / "isolated" / character / f"{dial}.json"
            result = sweep_dial(
                dial, values, n_games=args.games, seed=args.seed,
                roster=INTERLEAVED_ROSTER, characters=(character,), metadata=context,
                agent_overrides=overrides, agent_states=states,
                run_id=f"phase14-isolated-{character.lower()}-{dial}",
                on_update=lambda partial, path=path: _atomic_json(path, partial.to_dict()),
            )
            data = result.to_dict()
            _atomic_json(path, data)
            summary["screens"][f"{character}.{dial}"] = {"status": "complete", "path": str(path)}
            _atomic_json(args.output / "isolated.json", summary)
    summary["complete"] = True
    _atomic_json(args.output / "isolated.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


def _confirmation_gate(data: dict, change: dict) -> dict:
    current, proposed = data["rows"]
    win_delta = proposed["win_rate"] - current["win_rate"]
    wrong_delta = proposed["wrong_accusation_rate"] - current["wrong_accusation_rate"]
    length_delta = (proposed["mean_turns"] - current["mean_turns"]) / current["mean_turns"]
    footprint_metric = change["footprint_metric"]
    paired = data["paired_deltas"][1]["metrics"].get(footprint_metric)
    direction = change["expected_direction"]
    replicated = bool(paired) and (
        (direction == "increasing" and paired["low"] > 0)
        or (direction == "decreasing" and paired["high"] < 0)
    )
    return {
        "win_rate_delta": win_delta,
        "wrong_accusation_rate_delta": wrong_delta,
        "game_length_fraction_delta": length_delta,
        "footprint_metric": footprint_metric,
        "expected_direction": direction,
        "footprint_replicated": replicated,
        "guardrails_pass": (
            win_delta >= -0.05 and wrong_delta <= 0.05 and abs(length_delta) <= 0.10
        ),
        "numerical_gate": (
            replicated and win_delta >= -0.05 and wrong_delta <= 0.05 and abs(length_delta) <= 0.10
        ),
        "personality_gate": "pending human review",
        "accepted": False,
    }


def cmd_confirm(args) -> int:
    changes = json.loads(args.proposals.read_text(encoding="utf-8")).get("changes", [])
    stage, overrides, states = _methods(args.stage)
    context = _context(args.manifest, stage)
    summary = {"changes": [], "complete": False}
    _atomic_json(args.output / "confirmation.json", summary)
    for change in changes:
        character, dial = change["character"], change["dial"]
        current = float(getattr(PRESETS[character], dial))
        proposed = float(change["proposed"])
        path = args.output / "confirmation" / character / f"{dial}.json"
        result = sweep_dial(
            dial, (current, proposed), n_games=args.games, seed=args.seed,
            roster=INTERLEAVED_ROSTER, characters=(character,), metadata=context,
            agent_overrides=overrides, agent_states=states,
            run_id=f"phase14-confirm-{character.lower()}-{dial}",
            on_update=lambda partial, path=path: _atomic_json(path, partial.to_dict()),
        )
        data = result.to_dict()
        data["confirmation_gate"] = _confirmation_gate(data, change)
        _atomic_json(path, data)
        summary["changes"].append({
            "character": character, "dial": dial, "path": str(path),
            **data["confirmation_gate"],
        })
        _atomic_json(args.output / "confirmation.json", summary)
    summary["complete"] = True
    _atomic_json(args.output / "confirmation.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    top.add_argument("--manifest", type=Path, default=DEFAULT_CORPUS)
    top.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    top.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    sub = top.add_subparsers(dest="command", required=True)
    pooled = sub.add_parser("pooled")
    pooled.add_argument("--games", type=int, default=200)
    pooled.add_argument("--seed", type=int, default=142000)
    pooled.set_defaults(fn=cmd_pooled)
    isolated = sub.add_parser("isolated")
    isolated.add_argument("--games", type=int, default=96)
    isolated.add_argument("--seed", type=int, default=242000)
    isolated.set_defaults(fn=cmd_isolated)
    confirm = sub.add_parser("confirm")
    confirm.add_argument("--proposals", type=Path, required=True)
    confirm.add_argument("--games", type=int, default=192)
    confirm.add_argument("--seed", type=int, default=342000)
    confirm.set_defaults(fn=cmd_confirm)
    return top


def main(argv: Optional[list[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.fn(args)
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(f"phase14-sweeps: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
