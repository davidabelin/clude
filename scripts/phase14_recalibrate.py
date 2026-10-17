"""Phase 14 corpus, method staging, reporting and guarded promotion.

The command is read-only against its source by default.  ``snapshot`` and
``stage-methods`` write ignored local artifacts.  ``promote`` is a dry run
unless ``--apply`` is present; a production invocation additionally needs
the separately approved destination URI, expected live hashes and a local
backup directory.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clude_storage import open_store
from clude_training.recalibration import (
    FrozenCorpus,
    build_method_candidates,
    promote_methods,
    promote_plum_checkpoint,
    public_report,
    restore_methods,
    restore_plum_checkpoint,
    snapshot_narrative_logbooks,
    snapshot_corpus,
)

LIVE_STORE = "gs://clude-game-data/llm"
DEFAULT_CORPUS = ROOT / "data" / "phase14" / "corpus" / "manifest.json"
DEFAULT_STAGE = ROOT / "data" / "phase14" / "staged-methods"


def _write_json(path: Optional[Path], document: dict) -> None:
    text = json.dumps(document, indent=2) + "\n"
    if path is None:
        print(text, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(path)


def _expected(items: list[str]) -> dict[str, Optional[str]]:
    parsed: dict[str, Optional[str]] = {}
    for item in items:
        identity, separator, digest = item.partition("=")
        if not separator or not identity or not digest:
            raise ValueError(f"expected NAME=SHA256 or NAME=none, got {item!r}")
        if digest.lower() in ("none", "missing"):
            parsed[identity] = None
        elif len(digest) == 64 and all(c in "0123456789abcdefABCDEF" for c in digest):
            parsed[identity] = digest.lower()
        else:
            raise ValueError(f"not a SHA-256 digest: {digest!r}")
    return parsed


def cmd_snapshot(args) -> int:
    manifest = snapshot_corpus(
        open_store(args.source, credentials_path=args.credentials),
        args.destination,
        replace=args.replace,
    )
    print(json.dumps({
        "manifest": str(args.destination / "manifest.json"),
        "corpus_sha256": manifest["corpus_sha256"],
        "inventory": manifest["inventory"],
    }, indent=2))
    return 0


def cmd_stage(args) -> int:
    corpus = FrozenCorpus.open(args.manifest)
    green = json.loads(args.green_state.read_text(encoding="utf-8")) if args.green_state else None
    stage = build_method_candidates(corpus, args.destination, green_state=green)
    print(json.dumps({"stage": str(args.destination / "stage.json"), **stage}, indent=2))
    return 0


def cmd_report(args) -> int:
    report = public_report(FrozenCorpus.open(args.manifest), args.stage)
    _write_json(args.output, report)
    return 0


def cmd_promote(args) -> int:
    if not args.target:
        raise ValueError("promote requires an explicit --target URI")
    expected = _expected(args.expected)
    store = open_store(args.target, credentials_path=args.credentials)
    if args.restore_from:
        result = restore_methods(store, args.restore_from, expected, apply=args.apply)
    else:
        if args.stage is None or args.backup is None:
            raise ValueError("promotion requires --stage and --backup")
        result = promote_methods(store, args.stage, expected, args.backup, apply=args.apply)
    print(json.dumps(result, indent=2))
    if not args.apply:
        print("dry run only; no target or backup document was written")
    return 0


def cmd_promote_plum(args) -> int:
    if args.restore_from:
        result = restore_plum_checkpoint(
            args.restore_from, args.expected_target_hash, target=args.target, apply=args.apply
        )
    else:
        if args.checkpoint is None or args.backup is None:
            raise ValueError("Plum promotion requires --checkpoint and --backup")
        result = promote_plum_checkpoint(
            args.checkpoint,
            args.expected_target_hash,
            args.backup,
            target=args.target,
            apply=args.apply,
        )
    print(json.dumps(result, indent=2))
    if not args.apply:
        print("dry run only; committed weights and backup were not changed")
    return 0


def cmd_retrain_methods(args) -> int:
    from clude_training.recalibrate_methods import search_green, search_mustard, search_white

    corpus = FrozenCorpus.open(args.manifest)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    methods = ("mustard", "white", "green") if args.method == "all" else (args.method,)
    summaries = {}
    for method in methods:
        output = args.output_dir / f"{method}.json"
        if method == "mustard":
            result = search_mustard(
                corpus, output=output, arena_games=args.arena_games, arena_seed=args.arena_seed
            )
        elif method == "white":
            result = search_white(
                corpus, output=output, arena_games=args.arena_games, arena_seed=args.arena_seed + 100
            )
        else:
            result = search_green(
                corpus,
                output=output,
                training_games=args.green_training_games,
                validation_games=args.green_validation_games,
                training_seed=args.green_training_seed,
                validation_seed=args.green_validation_seed,
            )
        summaries[method] = {
            "output": str(output),
            "shortlist": result.get("shortlist"),
            "numerical_gate": result.get("numerical_gate"),
            "personality_gate": result.get("personality_gate"),
        }
    print(json.dumps(summaries, indent=2))
    return 0


def cmd_baseline(args) -> int:
    from clude_training.recalibration_baseline import capture_baseline

    result = capture_baseline(
        FrozenCorpus.open(args.manifest),
        output=args.output,
        benchmark_games=args.benchmark_games,
        arena_games=args.arena_games,
        benchmark_seed=args.benchmark_seed,
        arena_seed=args.arena_seed,
    )
    print(json.dumps({
        "output": str(args.output),
        "corpus_sha256": result["corpus_sha256"],
        "benchmark_games": result["benchmark"]["n_games"],
        "arena_games": result["plum_table"]["n_games"],
    }, indent=2))
    return 0


def cmd_snapshot_memory(args) -> int:
    manifest = snapshot_narrative_logbooks(
        open_store(args.source, credentials_path=args.credentials), args.destination
    )
    print(json.dumps({
        "manifest": str(args.destination / "manifest.json"),
        "snapshot_sha256": manifest["snapshot_sha256"],
        "documents": len(manifest["documents"]),
    }, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = top.add_subparsers(dest="command", required=True)

    snapshot = sub.add_parser("snapshot", help="Freeze the eligible post-landing-rule corpus locally.")
    snapshot.add_argument("--source", default=LIVE_STORE, help="Read-only source RecordStore URI.")
    snapshot.add_argument(
        "--destination", type=Path, default=DEFAULT_CORPUS.parent,
        help="Ignored local directory that will contain manifest.json and games/.",
    )
    snapshot.add_argument("--credentials", default=None, help="Optional GCS credentials path.")
    snapshot.add_argument("--replace", action="store_true", help="Replace an existing manifest deliberately.")
    snapshot.set_defaults(fn=cmd_snapshot)

    stage = sub.add_parser("stage-methods", help="Build method-only candidate documents from the train split.")
    stage.add_argument("--manifest", type=Path, default=DEFAULT_CORPUS)
    stage.add_argument("--destination", type=Path, default=DEFAULT_STAGE)
    stage.add_argument(
        "--green-state", type=Path, default=None,
        help="Selected fresh Green state document; omit until its 200-game training and validation pass.",
    )
    stage.set_defaults(fn=cmd_stage)

    report = sub.add_parser("report", help="Emit a privacy-safe corpus and staged-method report.")
    report.add_argument("--manifest", type=Path, default=DEFAULT_CORPUS)
    report.add_argument("--stage", type=Path, default=None)
    report.add_argument("--output", type=Path, default=None)
    report.set_defaults(fn=cmd_report)

    baseline = sub.add_parser("baseline", help="Capture current frozen-method benchmark and arenas.")
    baseline.add_argument("--manifest", type=Path, default=DEFAULT_CORPUS)
    baseline.add_argument("--output", type=Path, default=ROOT / "data" / "phase14" / "baseline.json")
    baseline.add_argument("--benchmark-games", type=int, default=60)
    baseline.add_argument("--arena-games", type=int, default=192)
    baseline.add_argument("--benchmark-seed", type=int, default=141300)
    baseline.add_argument("--arena-seed", type=int, default=241300)
    baseline.set_defaults(fn=cmd_baseline)

    memory = sub.add_parser(
        "snapshot-memory", help="Freeze character narrative logbooks for read-only paid comparisons."
    )
    memory.add_argument("--source", default=LIVE_STORE)
    memory.add_argument(
        "--destination", type=Path,
        default=ROOT / "data" / "phase14" / "memory-snapshot",
    )
    memory.add_argument("--credentials", default=None)
    memory.set_defaults(fn=cmd_snapshot_memory)

    retrain = sub.add_parser(
        "retrain-methods", help="Run the frozen-corpus Mustard, White or Green candidate search."
    )
    retrain.add_argument("--method", choices=("mustard", "white", "green", "all"), required=True)
    retrain.add_argument("--manifest", type=Path, default=DEFAULT_CORPUS)
    retrain.add_argument("--output-dir", type=Path, default=ROOT / "data" / "phase14" / "methods")
    retrain.add_argument("--arena-games", type=int, default=192)
    retrain.add_argument("--arena-seed", type=int, default=141400)
    retrain.add_argument("--green-training-games", type=int, default=200)
    retrain.add_argument("--green-validation-games", type=int, default=200)
    retrain.add_argument("--green-training-seed", type=int, default=141600)
    retrain.add_argument("--green-validation-seed", type=int, default=241600)
    retrain.set_defaults(fn=cmd_retrain_methods)

    promote = sub.add_parser("promote", help="Dry-run or apply a hash-guarded method-only promotion/restore.")
    promote.add_argument("--target", default="", help="Required RecordStore destination URI; no implicit live target.")
    promote.add_argument("--stage", type=Path, default=None)
    promote.add_argument("--backup", type=Path, default=None)
    promote.add_argument(
        "--restore-from", type=Path, default=None,
        help="Restore this method-only backup instead of promoting a stage.",
    )
    promote.add_argument(
        "--expected", action="append", default=[], metavar="NAME=SHA256",
        help="Expected current target hash; repeat per method (use NAME=none if absent).",
    )
    promote.add_argument("--credentials", default=None, help="Optional GCS credentials path.")
    promote.add_argument("--apply", action="store_true", help="Write after all guards pass; otherwise dry-run.")
    promote.set_defaults(fn=cmd_promote)

    plum = sub.add_parser(
        "promote-plum", help="Dry-run or apply one explicitly selected Plum checkpoint."
    )
    plum.add_argument("--checkpoint", type=Path, default=None)
    plum.add_argument("--target", type=Path, default=ROOT / "clude_agents" / "weights" / "plum.npz")
    plum.add_argument("--backup", type=Path, default=None)
    plum.add_argument("--restore-from", type=Path, default=None)
    plum.add_argument("--expected-target-hash", required=True)
    plum.add_argument("--apply", action="store_true")
    plum.set_defaults(fn=cmd_promote_plum)
    return top


def main(argv: Optional[list[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.fn(args)
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(f"phase14: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
