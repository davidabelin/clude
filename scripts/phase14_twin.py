"""Plum's paired legs at his three-seat table: headless, with the model, and
with the model reading his logbook (docs/strategy-glossary.md, "Plum twin
comparison at his three-seat table (2026-11-01)").

Twenty-four games at seed 143300, roster Plum, Mustard, Green, with Mustard
and Green playing the Phase 14 released method documents and Plum the
committed Run 3 weights. The headless leg is free; the two model legs are
paid and seed-paired with it. Every paid subcommand prints its quote and
refuses to run without ``--approve``; a ceiling backend stops a leg that
overruns, which marks it invalid.

    python scripts\\phase14_twin.py headless
    python scripts\\phase14_twin.py quote
    python scripts\\phase14_twin.py model --approve
    python scripts\\phase14_twin.py memory --approve
    python scripts\\phase14_twin.py analyse

Nothing is written to data/llm or the bucket: the logbook snapshot is read
only, and no debrief is written.
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

from clude_agents.personality import PRESETS
from clude_llm import LLMResult, LLMSettings, NullBackend, WikiCanon, open_backend
from clude_llm.anthropic_backend import estimate_cost
from clude_storage import LocalStore
from clude_training.arena import run_arena
from clude_training.recalibrate_paid import (
    FirstAllowedBackend,
    _arena_usage,
    _documents,
    _overrides,
    _request_summary,
)
from clude_training.recalibration import experiment_context, verify_narrative_logbooks
from clude_training.sweep import _bootstrap_interval
from clude_web.config import anthropic_key

PHASE_ROOT = ROOT / "data" / "phase14"
MANIFEST = PHASE_ROOT / "corpus" / "manifest.json"
STAGE = PHASE_ROOT / "staged-methods"
MEMORY = PHASE_ROOT / "memory-snapshot-20261101"
STORE = PHASE_ROOT / "paid" / "twin-games"
OUTPUT = PHASE_ROOT / "paid" / "twin-plum.json"
SEED = 143300
GAMES = 24
ROSTER = ("Plum", "Mustard", "Green")
MODEL = "claude-opus-5"
DEPTH = 1.0
"""The memory depth of leg B: what a new lobby seat reads (the profile's
own default is 0, the condensed read-back)."""
MEASURED_COST_PER_GAME = 3.5642 / 24
MEASURED_COST_PER_CALL = 3.5642 / 327
"""Phase 14's 24-pair leash confirmation at 0.35: $3.5642 over 24 games and
327 calls, Plum alone with the model and the canon, no logbook."""
MEMORY_COST_FACTOR = 5.0502 / 3.4689
MEMORY_COST_PER_CALL = 5.0502 / 303
"""Phase 14's memory screen at depth 1: $5.0502 over 303 calls with four
model seats each reading a logbook, against $3.4689 at depth 0."""
CEILING = {"model": 6.0, "memory": 9.0}
BOTH_CEILING = 15.0
"""The pair was approved at about $8 with a $12 ceiling; after the model leg
cost $5.3430 and the logbook leg was quoted at $6.95 to $7.80, David approved
running it on 2026-11-01 (the day's total staying under the approved $16)."""
LEGS = ("headless", "model", "memory")
METRICS = ("won", "wrong_accusation", "cards_leaked", "own_cards_named", "suggestions", "turns")


class CeilingBackend:
    """Prices every reply at list price and, once the running total passes
    the cap, refuses: the wrapper falls back to the headless choice and the
    leg is recorded as stopped. `last_refusal` is what `chat.refusing`
    reads, so a web table would stop queueing the seat too."""

    def __init__(self, inner, cap: float) -> None:
        self.inner = inner
        self.cap = cap
        self.name = getattr(inner, "name", "anthropic")
        self.spent = 0.0
        self.calls = 0
        self.refused = 0
        self.last_refusal = None

    def complete(self, request):
        if self.spent >= self.cap:
            self.refused += 1
            self.last_refusal = "ceiling"
            return LLMResult(error=f"ceiling: ${self.spent:.4f} reached ${self.cap:.2f}")
        result = self.inner.complete(request)
        self.calls += 1
        model = result.model if result.model else MODEL
        self.spent += estimate_cost(model, result.input_tokens, result.output_tokens, result.cached_tokens) or 0.0
        return result


def load() -> dict:
    if OUTPUT.exists():
        return json.loads(OUTPUT.read_text(encoding="utf-8"))
    return {
        "phase": 14,
        "kind": "plum-twin",
        "date": str(date.today()),
        "seed": SEED,
        "games": GAMES,
        "roster": list(ROSTER),
        "model": MODEL,
        "memory_depth": DEPTH,
        "legs": {},
        "complete": False,
    }


def save(document: dict) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_name(OUTPUT.name + ".tmp")
    temporary.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)


def frozen() -> dict:
    stage, documents = _documents(STAGE)
    manifest = verify_narrative_logbooks(MEMORY)
    context = experiment_context(MANIFEST)
    return {
        "stage": stage, "documents": documents, "manifest": manifest, "context": context,
        "hashes": {
            "corpus_sha256": context["corpus_sha256"],
            "weights_sha256": context["weights_sha256"],
            "method_stage_sha256": stage["documents"],
            "memory_snapshot_sha256": manifest["snapshot_sha256"],
        },
    }


def check_frozen(document: dict, inputs: dict) -> None:
    recorded = document.get("hashes")
    if recorded is None:
        raise RuntimeError("run the headless leg first; it records the frozen inputs")
    for name, value in inputs["hashes"].items():
        if recorded[name] != value:
            raise RuntimeError(f"{name} changed since the headless leg")


def spent_so_far(document: dict) -> float:
    return sum(leg.get("usage", {}).get("list_price_cost", 0.0) for leg in document["legs"].values())


def arena_kwargs(inputs: dict, leg: str, backend, store) -> dict:
    overrides, states = _overrides(inputs["documents"], ROSTER)
    kwargs = dict(
        n_games=GAMES, seed=SEED, roster=ROSTER, player_counts=(3,),
        agent_overrides=overrides, agent_states=states,
        store=store, run_id=f"phase14-twin-plum-{leg}-{SEED}",
    )
    if leg != "headless":
        kwargs.update(
            llm_backend=backend, llm_settings=LLMSettings(model=MODEL, debrief=False),
            llm_characters=("Plum",), llm_canon=WikiCanon(),
        )
    if leg == "memory":
        kwargs.update(
            logbook_store=LocalStore(MEMORY), logbooks_readonly=True, logbook_characters=("Plum",),
            profiles={"Plum": PRESETS["Plum"].with_dials(memory=DEPTH)},
        )
    return kwargs


def plum_outcomes(arena: dict) -> list:
    out = []
    for game in arena["games"]:
        plum = next(item for item in game["seat_outcomes"] if item["label"] == "Plum")
        out.append({**plum, "turns": game["turns"]})
    return out


def quote_for(inputs: dict, leg: str) -> dict:
    """An offline replay of the leg with the first-option backend sizes the
    requests; the measured figure is Phase 14's confirmation at this table."""
    backend = FirstAllowedBackend()
    kwargs = arena_kwargs(inputs, leg, backend, None)
    kwargs["run_id"] = f"preflight-{kwargs['run_id']}"
    run_arena(**kwargs)
    per_game = GAMES * MEASURED_COST_PER_GAME * (MEMORY_COST_FACTOR if leg == "memory" else 1.0)
    offline = _request_summary(backend.requests, MODEL, 60)
    per_call = offline["calls"] * (MEMORY_COST_PER_CALL if leg == "memory" else MEASURED_COST_PER_CALL)
    return {
        "leg": leg,
        "offline": offline,
        "by_measured_game": round(per_game, 4),
        "by_measured_call": round(per_call, 4),
        "measured_estimate": round(max(per_game, per_call), 4),
        "ceiling": CEILING[leg],
    }


def cmd_headless(args) -> int:
    document = load()
    if "headless" in document["legs"]:
        raise FileExistsError("the headless leg is already recorded")
    inputs = frozen()
    store = LocalStore(STORE)
    plain = run_arena(**arena_kwargs(inputs, "headless", None, store))
    twin = run_arena(**{**arena_kwargs(inputs, "model", NullBackend(), None), "run_id": f"phase14-twin-plum-null-{SEED}"})
    for a, b in zip(plain.games, twin.games):
        if a.seed != b.seed or a.turns != b.turns or a.winner_label != b.winner_label:
            raise RuntimeError(f"the null-backend twin diverged from the headless leg at game {a.game_index}")
    document["hashes"] = inputs["hashes"]
    document["context"] = inputs["context"]
    document["legs"]["headless"] = {
        "arena": plain.to_dict(), "stats": plain.per_player["Plum"].to_dict(),
        "usage": {"calls": 0, "fallbacks": 0, "list_price_cost": 0.0}, "valid": True,
        "null_twin_identical": True,
    }
    save(document)
    print(json.dumps({"leg": "headless", "wins": document["legs"]["headless"]["stats"]["wins"],
                      "mean_turns": plain.mean_turns, "null_twin_identical": True}, indent=2))
    return 0


def cmd_quote(args) -> int:
    document = load()
    inputs = frozen()
    check_frozen(document, inputs)
    quotes = [quote_for(inputs, leg) for leg in ("model", "memory") if leg not in document["legs"]]
    print(json.dumps({"spent_so_far": round(spent_so_far(document), 4), "both_ceiling": BOTH_CEILING,
                      "quotes": quotes}, indent=2))
    return 0


def cmd_paid(args) -> int:
    leg = args.command
    document = load()
    if leg in document["legs"]:
        raise FileExistsError(f"the {leg} leg is already recorded")
    if leg == "memory" and "model" not in document["legs"]:
        raise RuntimeError("run the model leg before the memory leg")
    inputs = frozen()
    check_frozen(document, inputs)
    quote = quote_for(inputs, leg)
    spent = spent_so_far(document)
    remaining = BOTH_CEILING - spent
    cap = min(CEILING[leg], remaining)
    print(json.dumps({"quote": quote, "spent_so_far": round(spent, 4), "cap_for_this_leg": round(cap, 4)}, indent=2))
    if quote["measured_estimate"] > cap:
        raise RuntimeError("the estimate exceeds the remaining ceiling; not run")
    if not args.approve:
        print("add --approve to run this paid leg")
        return 1
    if not anthropic_key():
        raise RuntimeError("no ANTHROPIC_API_KEY in the environment or .env")
    settings = LLMSettings(model=MODEL, debrief=False)
    inner = open_backend(
        "anthropic", model=MODEL, effort=settings.effort, max_tokens=settings.max_tokens,
        timeout=settings.timeout, server_fallbacks=settings.server_fallbacks, api_key=anthropic_key(),
    )
    backend = CeilingBackend(inner, cap)
    arena = run_arena(**arena_kwargs(inputs, leg, backend, LocalStore(STORE)))
    usage = _arena_usage(arena)
    usage["ceiling_refusals"] = backend.refused
    row = {
        "arena": arena.to_dict(), "stats": arena.per_player["Plum"].to_dict(), "usage": usage,
        "quote": quote, "cap": cap, "valid": usage["fallbacks"] == 0 and backend.refused == 0,
    }
    if not row["valid"]:
        row["stopped"] = "ceiling" if backend.refused else "fallback"
    document["legs"][leg] = row
    save(document)
    print(json.dumps({"leg": leg, "wins": row["stats"]["wins"], "wrong": row["stats"]["games_with_wrong_accusation"],
                      "calls": usage["calls"], "fallbacks": usage["fallbacks"],
                      "list_price_cost": usage["list_price_cost"], "valid": row["valid"]}, indent=2))
    return 0 if row["valid"] else 3


def paired(left: dict, right: dict, key: str) -> dict:
    a, b = plum_outcomes(left["arena"]), plum_outcomes(right["arena"])
    if len(a) != len(b) or any(x["seat"] != y["seat"] for x, y in zip(a, b)):
        raise RuntimeError(f"{key}: the legs are not seat-paired")
    return {
        name: _bootstrap_interval([float(y[name]) - float(x[name]) for x, y in zip(a, b)],
                                  f"phase14-twin-plum|{key}|{name}", 4000)
        for name in METRICS
    }


def cmd_analyse(args) -> int:
    document = load()
    legs = document["legs"]
    pairs = {}
    for left, right in (("headless", "model"), ("headless", "memory"), ("model", "memory")):
        if left in legs and right in legs and legs[left]["valid"] and legs[right]["valid"]:
            pairs[f"{left}/{right}"] = paired(legs[left], legs[right], f"{left}/{right}")
    document["paired_deltas"] = pairs
    document["complete"] = all(leg in legs and legs[leg]["valid"] for leg in LEGS)
    save(document)
    rows = []
    for leg in LEGS:
        if leg not in legs:
            continue
        stats, usage, arena = legs[leg]["stats"], legs[leg]["usage"], legs[leg]["arena"]
        mean_turns = sum(g["turns"] for g in arena["games"]) / len(arena["games"])
        rows.append(
            f"| {leg} | {stats['games']} | {stats['wins']} | {100 * stats['wins'] / stats['games']:.1f} | "
            f"{stats['games_with_wrong_accusation']} | {mean_turns:.2f} | {usage['calls']} | ${usage['list_price_cost']:.4f} |"
        )
    print("\n".join(rows))
    for key, metrics in pairs.items():
        for name, interval in metrics.items():
            print(f"{key} {name}: {interval['delta']:+.4f} ({interval['low']:+.4f} to {interval['high']:+.4f}), n={interval['n_pairs']}")
    print(OUTPUT)
    return 0


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = top.add_subparsers(dest="command", required=True)
    sub.add_parser("headless", help="The free leg, plus a null-backend twin that must match it.").set_defaults(fn=cmd_headless)
    sub.add_parser("quote", help="Size the paid legs offline; nothing is called.").set_defaults(fn=cmd_quote)
    for leg in ("model", "memory"):
        paid = sub.add_parser(leg, help=f"The paid {leg} leg; prints its quote and needs --approve.")
        paid.add_argument("--approve", action="store_true")
        paid.set_defaults(fn=cmd_paid)
    sub.add_parser("analyse", help="Paired deltas and the glossary rows.").set_defaults(fn=cmd_analyse)
    return top


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.fn(args)
    except (FileExistsError, FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(f"phase14-twin: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
