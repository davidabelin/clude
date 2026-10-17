"""Plan, run and evaluate Phase 14's three independent two-stage Plum trainings."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clude_training.recalibrate_plum import evaluate_plum_checkpoints
from clude_training.recalibration import FrozenCorpus, experiment_context

DEFAULT_ROOT = ROOT / "data" / "phase14" / "plum"
DEFAULT_CORPUS = ROOT / "data" / "phase14" / "corpus" / "manifest.json"
RUN_SEEDS = (141401, 141402, 141403)


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _commands(root: Path, workers: int, device: str, chunk: int = 1) -> list[dict]:
    commands = []
    trainer = ROOT / "scripts" / "train_plum.py"
    for run_number, seed in enumerate(RUN_SEEDS, 1):
        run = root / f"run-{run_number}"
        stage1 = run / "stage1"
        stage2 = run / "stage2"
        common = [
            sys.executable, str(trainer), "--iterations", "150", "--games", "512",
            "--workers", str(workers), "--chunk", str(chunk),
            "--shaping", "1.0", "--eval-every", "10",
            "--seed", str(seed), "--device", device,
        ]
        commands.append({
            "run": run_number,
            "stage": 1,
            "fresh_initialisation": True,
            "device": device,
            "chunk": chunk,
            "command": common + ["--out", str(stage1)],
            "output": str(stage1),
        })
        commands.append({
            "run": run_number,
            "stage": 2,
            "fresh_initialisation": False,
            "device": device,
            "chunk": chunk,
            "resume": str(stage1 / "latest.npz"),
            "command": common + [
                "--resume", str(stage1 / "latest.npz"),
                "--lr", "0.0001", "--entropy", "0.003", "--neurd-threshold", "4",
                "--eta", "0.05", "--out", str(stage2),
            ],
            "output": str(stage2),
        })
    return commands


def cmd_plan(args) -> int:
    corpus = FrozenCorpus.open(args.manifest)
    plan = {
        "phase": 14,
        "corpus_sha256": corpus.sha256,
        "context": experiment_context(args.manifest),
        "runs": 3,
        "games_per_stage": 150 * 512,
        "device": args.device,
        "chunk": args.chunk,
        "commands": _commands(args.output_root, args.workers, args.device, args.chunk),
        "status": "planned",
    }
    _atomic_json(args.output_root / "training.json", plan)
    print(json.dumps(plan, indent=2))
    return 0


def cmd_train(args) -> int:
    import torch

    requested_device = torch.device(args.device)
    if requested_device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA training was requested but torch.cuda.is_available() is false; "
            "install a CUDA-enabled PyTorch build before starting Phase 14"
        )
    corpus = FrozenCorpus.open(args.manifest)
    path = args.output_root / "training.json"
    current_context = experiment_context(args.manifest)
    plan = {
        "phase": 14,
        "corpus_sha256": corpus.sha256,
        "context": current_context,
        "runs": 3,
        "games_per_stage": 150 * 512,
        "device": str(requested_device),
        "chunk": args.chunk,
        "commands": _commands(args.output_root, args.workers, str(requested_device), args.chunk),
        "completed": [],
        "history": [],
        "status": "running",
    }
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        if previous.get("corpus_sha256") != corpus.sha256:
            raise ValueError("existing Plum training belongs to a different frozen corpus")
        if previous.get("device", "cpu") != str(requested_device):
            raise ValueError(
                "existing Plum training uses a different device; archive it and start "
                "a fresh three-run experiment"
            )
        if previous.get("status") != "planned" and not args.resume_run:
            raise FileExistsError(
                f"training manifest already started: {path}; use --resume-run deliberately"
            )
        previous_context = previous.get("context")
        plan["completed"] = previous.get("completed", [])
        plan["history"] = previous.get("history", [])
        if previous_context != current_context:
            if not args.resume_note:
                raise ValueError(
                    "code context changed during Plum training; provide --resume-note "
                    "to record the audited amendment"
                )
            for row in plan["completed"]:
                row.setdefault("context", previous_context)
            plan["history"].append({
                "event": "code_context_change",
                "after_completed": [
                    {"run": row["run"], "stage": row["stage"]}
                    for row in plan["completed"]
                ],
                "before": previous_context,
                "after": current_context,
                "note": args.resume_note,
            })
    _atomic_json(path, plan)
    completed = {(row["run"], row["stage"]) for row in plan["completed"]}
    for item in plan["commands"]:
        key = (item["run"], item["stage"])
        if key in completed:
            continue
        output = Path(item["output"])
        if output.exists() and any(output.iterdir()):
            raise FileExistsError(f"refusing to overwrite partial training directory: {output}")
        subprocess.run(item["command"], cwd=ROOT, check=True)
        plan["completed"].append({
            "run": item["run"], "stage": item["stage"],
            "checkpoint": str(output / "latest.npz"),
            "context": current_context,
        })
        _atomic_json(path, plan)
    plan["status"] = "complete"
    _atomic_json(path, plan)
    print(path)
    return 0


def cmd_evaluate(args) -> int:
    report = evaluate_plum_checkpoints(
        args.checkpoint,
        output=args.output,
        benchmark_games=args.benchmark_games,
        arena_games=args.arena_games,
        benchmark_seed=args.benchmark_seed,
        arena_seed=args.arena_seed,
        corpus_manifest=args.manifest,
    )
    print(json.dumps({
        "output": str(args.output), "candidates": len(report["candidates"]),
        "numerical_shortlist": report["numerical_shortlist"],
    }, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = top.add_subparsers(dest="command", required=True)
    for name, fn in (("plan", cmd_plan), ("train", cmd_train)):
        command = sub.add_parser(name)
        command.add_argument("--manifest", type=Path, default=DEFAULT_CORPUS)
        command.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
        command.add_argument("--workers", type=int, default=12)
        command.add_argument(
            "--chunk", type=int, default=1,
            help="Games per worker result; Phase 14 uses one to bound Windows IPC payloads.",
        )
        command.add_argument(
            "--device", default="cuda",
            help="PyTorch training device recorded in the plan (Phase 14 defaults to CUDA).",
        )
        if name == "train":
            command.add_argument(
                "--resume-run", action="store_true",
                help="Continue only stages recorded incomplete in the matching training manifest.",
            )
            command.add_argument(
                "--resume-note",
                help="Auditable reason for resuming after a code-context change.",
            )
        command.set_defaults(fn=fn)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--checkpoint", type=Path, action="append", required=True)
    evaluate.add_argument("--manifest", type=Path, default=DEFAULT_CORPUS)
    evaluate.add_argument("--output", type=Path, default=DEFAULT_ROOT / "evaluation.json")
    evaluate.add_argument("--benchmark-games", type=int, default=60)
    evaluate.add_argument("--arena-games", type=int, default=192)
    evaluate.add_argument("--benchmark-seed", type=int, default=141700)
    evaluate.add_argument("--arena-seed", type=int, default=241700)
    evaluate.set_defaults(fn=cmd_evaluate)
    return top


def main(argv: Optional[list[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.fn(args)
    except (FileNotFoundError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"phase14-plum: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
