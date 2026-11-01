"""Measure the reaction queue's pacing over saved games (docs/strategy-glossary.md,
"Reaction-queue pacing (2026-11-01)").

Replays the frozen Phase 14 ``web-2`` records and the eight preflight
arena games through the real `clude_web.chat.Reactions` class with a
backend that always answers, at the current chattiness presets and at
1.0, patient (the queue drains before play moves on, as at a bot or
model table) and impatient (a person answers before a queued line is
due). Nothing is changed and nothing is paid for.

    python scripts\\pacing_measure.py
    python scripts\\pacing_measure.py --records web-2 --conditions presets --mode patient
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clude_storage import GameRecord, LocalStore
from clude_training import pacing
from clude_web.chat import MAX_QUEUED, PER_GAME, PER_TURN

SOURCES = {
    "web-2": (ROOT / "data" / "phase14" / "corpus", "web-2"),
    "preflight": (ROOT / "data" / "phase14" / "paid" / "games", "phase14-preflight-chat"),
}


def load_records(name: str) -> list:
    root, run_id = SOURCES[name]
    store = LocalStore(root)
    return [GameRecord.from_dict(store.get_game(run_id, index)) for index in store.list_games(run_id)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--records", default="web-2,preflight")
    ap.add_argument("--conditions", default="presets,1.0")
    ap.add_argument("--mode", default="patient,impatient")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "pacing" / f"pacing-{date.today():%Y%m%d}.json")
    args = ap.parse_args(argv)
    records = {name: load_records(name) for name in args.records.split(",")}
    talking = {name: [r for r in rs if any(s.kind in ("llm", "character") for s in r.seats)] for name, rs in records.items()}
    result = {
        "date": str(date.today()),
        "constants": {"MAX_QUEUED": MAX_QUEUED, "PER_TURN": PER_TURN, "PER_GAME": PER_GAME},
        "cost_per_line": pacing.COST_PER_LINE,
        "as_played": {},
        "conditions": [],
    }
    for name, rs in records.items():
        if name == "web-2":
            played = [pacing.as_played(r) for r in rs]
            result["as_played"][name] = {"games": played, "reactions": sum(p["reactions"] for p in played)}
    for name, rs in talking.items():
        for condition in args.conditions.split(","):
            chattiness = None if condition == "presets" else float(condition)
            for mode in args.mode.split(","):
                games = [pacing.measure(r, chattiness=chattiness, patient=(mode == "patient")) for r in rs]
                row = {
                    "records": name, "condition": condition, "mode": mode,
                    "games": games, "pooled": pacing.pool(games),
                }
                result["conditions"].append(row)
                p = row["pooled"]
                print(
                    f"{name:9} {condition:7} {mode:9} games={p['games']:2} opp={p['opportunities_total']:4} "
                    f"draws={p['draws']:4} joined={p['joined']:4} served={p['served_total']:4} "
                    f"turn3+={p['turns_at_three_or_more']:3} full={p['triggers_full']:3} "
                    f"skipped={p['skipped_by_break']:3} stale={p['stale_drops']:3} "
                    f"depth2+={p['depth_two_or_deeper']:3} cap={p['games_at_cap']:2} "
                    f"cost~${p['projected_cost']:.2f}"
                )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
