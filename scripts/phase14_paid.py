"""Prepare Phase 14's paid leash, chattiness and memory confirmation gate."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clude_llm import LLMSettings, open_backend
from clude_llm.backend import DEFAULT_MODEL
from clude_training.recalibrate_paid import paid_preflight, paid_screen
from clude_training.recalibration import FrozenCorpus

DEFAULT_CORPUS = ROOT / "data" / "phase14" / "corpus" / "manifest.json"
DEFAULT_STAGE = ROOT / "data" / "phase14" / "staged-methods"
DEFAULT_MEMORY = ROOT / "data" / "phase14" / "memory-snapshot"
DEFAULT_ROOT = ROOT / "data" / "phase14" / "paid"


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def cmd_preflight(args) -> int:
    report = paid_preflight(
        FrozenCorpus.open(args.manifest), args.stage, args.memory, args.output.parent / "games",
        model=args.model,
    )
    _atomic_json(args.output, report)
    print(json.dumps({
        "output": str(args.output), "model": report["model"],
        "quote": report["quote"], "paid_calls_made": 0,
        "approval_status": "required",
    }, indent=2))
    return 0


def cmd_run_screen(args) -> int:
    if not args.apply or not args.approval.strip():
        raise ValueError("paid screen requires both --apply and a recorded --approval reference")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is absent; no paid leg was started")
    preflight = json.loads(args.preflight.read_text(encoding="utf-8"))
    if preflight.get("approval_status") != "required" or preflight.get("paid_calls_made") != 0:
        raise ValueError("preflight is not the untouched approval request")
    if args.output.exists():
        raise FileExistsError(f"paid result already exists: {args.output}")
    settings = LLMSettings(model=args.model, debrief=False)
    backend = open_backend(
        "anthropic", model=settings.model, effort=settings.effort,
        max_tokens=settings.max_tokens, timeout=settings.timeout,
        server_fallbacks=settings.server_fallbacks,
    )

    def save(partial):
        document = {**partial, "approval_reference": args.approval}
        _atomic_json(args.output, document)

    result = paid_screen(
        FrozenCorpus.open(args.manifest), args.stage, args.memory, args.output.parent / "games",
        preflight, backend, model=args.model, on_update=save,
    )
    save(result)
    print(json.dumps({
        "output": str(args.output), "complete": result["complete"], "valid": result["valid"],
        "stopped": result.get("stopped"),
    }, indent=2))
    return 0 if result["complete"] and result["valid"] else 3


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = top.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--manifest", type=Path, default=DEFAULT_CORPUS)
    preflight.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    preflight.add_argument("--memory", type=Path, default=DEFAULT_MEMORY)
    preflight.add_argument("--model", default=DEFAULT_MODEL)
    preflight.add_argument("--output", type=Path, default=DEFAULT_ROOT / "preflight.json")
    preflight.set_defaults(fn=cmd_preflight)
    run = sub.add_parser("run-screen")
    run.add_argument("--manifest", type=Path, default=DEFAULT_CORPUS)
    run.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    run.add_argument("--memory", type=Path, default=DEFAULT_MEMORY)
    run.add_argument("--preflight", type=Path, default=DEFAULT_ROOT / "preflight.json")
    run.add_argument("--output", type=Path, default=DEFAULT_ROOT / "screen.json")
    run.add_argument("--model", default=DEFAULT_MODEL)
    run.add_argument("--approval", default="", help="User-provided approval reference recorded in the result.")
    run.add_argument("--apply", action="store_true", help="Actually make paid model calls.")
    run.set_defaults(fn=cmd_run_screen)
    return top


def main(argv: Optional[list[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.fn(args)
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(f"phase14-paid: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
