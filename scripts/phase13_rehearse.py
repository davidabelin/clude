"""Phase 13 rehearsal harness: do the characters converse?

Runs a scene as a real exchange -- each reply is fed to the next speaker, so
a thread can develop -- rather than collecting isolated lines. The talk gate
is isolated (`chattiness` 1.0) so a scene measures what the characters write
rather than what the reaction queue happened to publish; tuning the shipped
presets is step 6's, not this script's.

    # free: canned replies, checks the plumbing and the rendered requests
    python scripts\\phase13_rehearse.py --backend stub

    # paid: needs approval; --estimate first
    python scripts\\phase13_rehearse.py --estimate
    python scripts\\phase13_rehearse.py --backend anthropic --scenes film,jewels

Writes a transcript and a per-scene tally to --out. Nothing touches a live
store or the bucket: memory is read from --memory-store, read-only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from random import Random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clude_agents import build_character  # noqa: E402
from clude_agents.personality import PRESETS, Profile  # noqa: E402
from clude_llm.backend import LLMResult, NullBackend  # noqa: E402
from clude_llm.player import LLMCharacter, LLMSettings  # noqa: E402

ROSTER = ["Scarlett", "Mustard", "White", "Green", "Peacock", "Plum"]

# Each scene: an opening exchange and who is prompted first. The trigger is
# what `remark_prompt` reports as having just happened.
SCENES = {
    "film": {
        "opening": [
            ("Green", "I loved how that film let the scene end without telling us who was right."),
            ("Scarlett", "For once, I did not want someone to explain it to me."),
        ],
        "trigger": "Miss Scarlett replied to Mr. Green about the film.",
        "order": ["Green", "Scarlett", "Peacock", "White"],
    },
    "news": {
        "opening": [
            ("Mustard", "They had a piece on the roadworks this morning. Common sense, finally."),
            ("White", "The French coverage of the same scheme read rather differently."),
        ],
        "trigger": "Mrs. White answered the Colonel about the news.",
        "order": ["Mustard", "White", "Peacock", "Plum"],
    },
    "jewels": {
        "opening": [
            ("Peacock", "Colonel, that is a very particular pin. Is one permitted to ask?"),
            ("Mustard", "One is permitted to ask, madam."),
        ],
        "trigger": "Mrs. Peacock asked the Colonel about his pin.",
        "order": ["Mustard", "Peacock", "Scarlett", "Green"],
    },
    "scripts": {
        "opening": [
            ("Plum", "We are all of us running on somebody's script, if we are honest about it."),
            ("Scarlett", "Speak for yourself, Professor."),
        ],
        "trigger": "Miss Scarlett answered Professor Plum about the scripts.",
        "order": ["Plum", "Scarlett", "Mustard", "Peacock"],
    },
    "answered": {
        "opening": [
            ("White", "The Library has not been tested all evening."),
            ("Green", "You said that two turns ago, and it was true then too."),
        ],
        "trigger": "Mr. Green noted that the point had already been made.",
        "order": ["White", "Scarlett", "Peacock", "Green"],
    },
}

# Markers that a line is about the investigation. Only terms with no
# ordinary social sense: the first paid run showed that "suspect",
# "deduction", "silence", "notes" and even "square" (Mustard's square and
# compasses) fire on plain conversation, so they are excluded. Undercounting
# game talk is the safer error here, since the question is whether anything
# OTHER than the game gets said.
GAME_WORDS = {
    "accuse", "accuses", "accusing", "accusation", "envelope", "refute",
    "refuted", "refutes", "unrefuted", "suggestion", "suggestions",
    "threshold", "ballroom", "billiard", "conservatory", "candlestick",
    "revolver", "wrench", "lead_pipe",
}
GAME_PHRASES = (
    "my hand", "your hand", "his hand", "her hand", "the deal",
    "secret passage", "show me", "showed me", "i showed",
    "the library", "the kitchen", "the study", "the lounge", "the hall",
    "the dining", "turns and", "proved yet", "name your room", "announce your door",
)


def build(name, backend, settings, memory_store):
    """One wrapper with the gate open and its logbook attached read-only."""
    profile = PRESETS.get(name, Profile()).with_dials(chattiness=1.0)
    character = build_character(name, profile=profile)
    wrapper = LLMCharacter(character, backend, settings=settings)
    if memory_store:
        try:
            from clude_storage import open_store
            from clude_storage.logbooks import Logbook
            store = open_store(memory_store)
            wrapper.attach_logbook(Logbook(store, name))
        except Exception as exc:                      # pragma: no cover
            print(f"  (no logbook for {name}: {exc})")
    wrapper.new_game(table=ROSTER)
    return wrapper


HANDS = {
    0: ("Green", "Library", "Scarlett"), 1: ("Mustard", "Rope", "Kitchen"),
    2: ("White", "Knife", "Ballroom"), 3: ("Plum", "Revolver", "Study"),
    4: ("Peacock", "Wrench", "Hall"), 5: ("Candlestick", "Lead_Pipe", "Lounge"),
}
"""A fixed legal deal, so each seat has a real hand and floor to reason from."""


def observation(seat):
    """A minimal mid-game view: enough for remark_prompt, no real deal."""
    from dataclasses import replace
    from clude_constraints import propagate
    from clude_core.state import ClueObservation
    obs = ClueObservation(
        n_players=len(ROSTER), my_index=seat,
        own_hand=frozenset(HANDS[seat]),
        active_players=tuple(True for _ in ROSTER),
        hand_sizes={i: 3 for i in range(len(ROSTER))},
        suggestion_log=(), accusation_log=(), turn=12,
    )
    return replace(obs, mask=propagate(obs))


def classify(text):
    """game / other, erring toward 'other'. See GAME_WORDS."""
    low = text.lower()
    words = {w.strip(".,;:!?\"'\u2014-").lower() for w in text.split()}
    if words & GAME_WORDS or any(p in low for p in GAME_PHRASES):
        return "game"
    return "other"


def run_scene(key, scene, wrappers, rounds, verbose):
    # `wrappers` is built fresh per scene by the caller, so one scene's
    # talk cannot bleed into the next through a wrapper's own memory.
    talk = list(scene["opening"])
    lines = []
    order = scene["order"]
    for k in range(rounds):
        speaker = order[k % len(order)]
        wrapper = wrappers[speaker]
        seat = ROSTER.index(speaker)
        remarks = [(ROSTER.index(who), what) for who, what in talk]
        trigger = scene["trigger"] if k == 0 else f"{talk[-1][0]} spoke."
        try:
            say = wrapper.react(observation(seat), trigger,
                                names=list(ROSTER))
        except Exception as exc:
            say = None
            lines.append({"round": k + 1, "speaker": speaker, "error": str(exc)})
            if verbose:
                print(f"    {speaker}: <error: {exc}>")
            continue
        if not say:
            lines.append({"round": k + 1, "speaker": speaker, "say": "", "kind": "silent"})
            if verbose:
                print(f"    {speaker}: <silence>")
            continue
        talk.append((speaker, say))
        kind = classify(say)
        lines.append({"round": k + 1, "speaker": speaker, "say": say, "kind": kind})
        if verbose:
            print(f"    {speaker} [{kind}]: {say}")
    return {"scene": key, "opening": scene["opening"], "lines": lines}


class Metering:
    """Counts tokens and priced cost around any backend, so a rehearsal
    reports what it actually spent rather than an estimate."""

    def __init__(self, inner):
        self.inner = inner
        self.name = getattr(inner, "name", "inner")
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_tokens = 0
        self.cost = 0.0

    def complete(self, request):
        from clude_llm.anthropic_backend import PRICES_PER_MTOK, estimate_cost
        result = self.inner.complete(request)
        self.calls += 1
        self.input_tokens += result.input_tokens
        self.output_tokens += result.output_tokens
        self.cached_tokens += result.cached_tokens
        model = result.model if result.model in PRICES_PER_MTOK else "claude-opus-5"
        try:
            self.cost += estimate_cost(model, result.input_tokens,
                                       result.output_tokens, result.cached_tokens)
        except Exception:
            pass
        return result

    def report(self):
        return {"calls": self.calls, "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "cached_tokens": self.cached_tokens, "cost_usd": round(self.cost, 4)}


def stub_backend():
    """Canned replies, so the plumbing and prompts can be checked for free."""
    class Stub:
        name = "stub"

        def __init__(self):
            self.calls = 0
            self.requests = []

        def complete(self, request):
            self.calls += 1
            self.requests.append(request)
            return LLMResult(text=json.dumps({"say": f"(stub line {self.calls})"}),
                             stop_reason="end_turn", model="stub")
    return Stub()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", choices=["stub", "null", "anthropic"], default="stub")
    ap.add_argument("--scenes", default="all",
                    help=f"comma-separated, from: {','.join(SCENES)}")
    ap.add_argument("--rounds", type=int, default=6,
                    help="replies per scene (default 6, so a thread can develop)")
    ap.add_argument("--memory-store", default="data/phase13-rehearsal-store",
                    help="store to read logbooks from, read-only; '' for none")
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--effort", default="low")
    ap.add_argument("--max-tokens", type=int, default=200)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--out", default="data/phase13-rehearsal")
    ap.add_argument("--estimate", action="store_true",
                    help="print the call count and a cost estimate, call nothing")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    keys = list(SCENES) if args.scenes == "all" else [s.strip() for s in args.scenes.split(",")]
    unknown = [k for k in keys if k not in SCENES]
    if unknown:
        ap.error(f"unknown scene(s): {unknown}; have {list(SCENES)}")

    calls = len(keys) * args.rounds
    if args.estimate:
        # Opus-class pricing, deliberately rounded up; the system block is
        # cached across a scene's calls but assume it is not.
        # Measured on a stub run: ~2000 tokens of cached system block
        # (persona, rules, memory) plus ~250 of scene, and a one-line reply.
        sys_tok, scene_tok, out_tok = 2000, 250, 50
        rate_in, rate_cached, rate_out = 15e-6, 1.5e-6, 75e-6
        cold = calls * ((sys_tok + scene_tok) * rate_in + out_tok * rate_out)
        warm = (len(keys) * (sys_tok * rate_in)
                + calls * (scene_tok * rate_in + sys_tok * rate_cached
                           + out_tok * rate_out))
        print(f"scenes      : {', '.join(keys)}")
        print(f"rounds each : {args.rounds}")
        print(f"model calls : {calls}")
        print(f"per call    : ~{sys_tok} cached + {scene_tok} fresh in, <={out_tok} out")
        print(f"estimate    : ${warm:.2f} expected, ${cold:.2f} if nothing caches")
        print("approve before running with --backend anthropic")
        return 0

    if args.backend == "anthropic":
        from clude_llm.anthropic_backend import AnthropicBackend
        backend = Metering(AnthropicBackend())
    elif args.backend == "stub":
        backend = stub_backend()
    else:
        backend = NullBackend()

    settings = LLMSettings(model=args.model, effort=args.effort,
                           remark_max_tokens=args.max_tokens, speak=True)

    print(f"backend {args.backend}; chattiness forced to 1.0; "
          f"{len(keys)} scene(s) x {args.rounds} rounds")
    results = []
    for key in keys:
        print(f"\n  == {key} ==")
        wrappers = {}
        for name in ROSTER:
            wrappers[name] = build(name, backend, settings,
                                   args.memory_store or None)
            wrappers[name].rng = Random(args.seed)
        results.append(run_scene(key, SCENES[key], wrappers, args.rounds,
                                 not args.quiet))

    # tally
    tally = {"game": 0, "other": 0, "silent": 0, "error": 0}
    for r in results:
        for line in r["lines"]:
            if "error" in line:
                tally["error"] += 1
            else:
                tally[line["kind"]] += 1
    print("\n  lines:", ", ".join(f"{k} {v}" for k, v in tally.items()))
    spoke = tally["game"] + tally["other"]
    if spoke:
        print(f"  non-game share of spoken lines: {tally['other'] / spoke:.0%}")

    usage = backend.report() if isinstance(backend, Metering) else None
    if usage:
        print(f"  spent: ${usage['cost_usd']:.4f} over {usage['calls']} calls "
              f"({usage['input_tokens']} in, {usage['cached_tokens']} cached, "
              f"{usage['output_tokens']} out)")

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"rehearsal-{args.backend}.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"backend": args.backend, "model": args.model,
                   "chattiness": 1.0, "rounds": args.rounds,
                   "memory_store": args.memory_store,
                   "usage": usage, "tally": tally, "scenes": results},
                  fh, indent=2)
        fh.write("\n")
    print(f"  transcript: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
