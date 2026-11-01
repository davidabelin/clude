"""Phase 13 rehearsal harness: do the characters converse?

Runs a scene as a real exchange: every speaker hears the scene's opening
and every reply before it (`LLMCharacter.hear`), so a thread can develop,
and each wrapper carries the Wikiclude canon so a character may look a
claim up or dispute it. The talk gate is isolated (`chattiness` 1.0 and
`react` called directly) so a scene measures what the characters write
rather than what the reaction queue happened to publish; tuning the
shipped presets is step 6's, not this script's.

    # free: canned replies, checks the plumbing and the rendered requests
    python scripts\\phase13_rehearse.py --backend stub

    # paid: needs approval; --estimate first
    python scripts\\phase13_rehearse.py --estimate
    python scripts\\phase13_rehearse.py --backend anthropic --scenes film,jewels

Writes a transcript and a per-scene tally to --out. Nothing touches a live
store or the bucket: memory is read from --memory-store, read-only.

History. The first harness (2026-10-14/15) built the list of remarks and
never passed it on, so every model saw only the trigger sentence and its
own earlier lines; the figures recorded then measured voice in isolation,
not conversation (docs/phase13-plan.md, 2026-11-01). This is harness 2.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from random import Random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clude_agents import build_character  # noqa: E402
from clude_agents.personality import PRESETS, Profile  # noqa: E402
from clude_core.events import RemarkEvent  # noqa: E402
from clude_llm import WikiCanon  # noqa: E402
from clude_llm.backend import LLMResult, NullBackend  # noqa: E402
from clude_llm.player import LLMCharacter, LLMSettings  # noqa: E402

HARNESS = 2
ROSTER = ["Scarlett", "Mustard", "White", "Green", "Peacock", "Plum"]

# Each scene: an opening exchange, who is prompted first, and the turn the
# fixed view is dated to (varied so no two scenes share "turn 12", which
# the first harness's transcripts kept echoing). A scene may seat a
# `person`: a scripted non-character participant at one seat, shown as
# the table screen would show them, whose lines enter only through
# `hear()`. The trigger is what `remark_prompt` reports as having just
# happened.
SCENES = {
    "film": {
        "turn": 9,
        "opening": [
            ("Green", "I loved how that film let the scene end without telling us who was right."),
            ("Scarlett", "For once, I did not want someone to explain it to me."),
        ],
        "trigger": "Miss Scarlett replied to Mr. Green about the film.",
        "order": ["Green", "Scarlett", "Peacock", "White"],
    },
    "news": {
        "turn": 4,
        "opening": [
            ("Mustard", "They had a piece on the roadworks this morning. Common sense, finally."),
            ("White", "The French coverage of the same scheme read rather differently."),
        ],
        "trigger": "Mrs. White answered the Colonel about the news.",
        "order": ["Mustard", "White", "Peacock", "Plum"],
    },
    "jewels": {
        "turn": 17,
        "opening": [
            ("Peacock", "Colonel, that is a very particular pin. Is one permitted to ask?"),
            ("Mustard", "One is permitted to ask, madam."),
        ],
        "trigger": "Mrs. Peacock asked the Colonel about his pin.",
        "order": ["Mustard", "Peacock", "Scarlett", "Green"],
    },
    "scripts": {
        "turn": 12,
        "opening": [
            ("Plum", "We are all of us running on somebody's script, if we are honest about it."),
            ("Scarlett", "Speak for yourself, Professor."),
        ],
        "trigger": "Miss Scarlett answered Professor Plum about the scripts.",
        "order": ["Plum", "Scarlett", "Mustard", "Peacock"],
    },
    "answered": {
        "turn": 25,
        "opening": [
            ("White", "The Library has not been tested all evening."),
            ("Green", "You said that two turns ago, and it was true then too."),
        ],
        "trigger": "Mr. Green noted that the point had already been made.",
        "order": ["White", "Scarlett", "Peacock", "Green"],
    },
    # A guest at Peacock's seat claims to be a regular. Recognition where the
    # logbooks justify it, uncertainty where they do not; names consistent.
    "bluff": {
        "turn": 6,
        "person": ("Peacock", "Peacock (Guest)"),
        "opening": [
            ("Peacock (Guest)", "Don't let the guest tag fool you, it's David, I couldn't log in tonight. "
                                "Professor, you still owe me a rematch from last week."),
        ],
        "trigger": 'Peacock (Guest) said: "Don\'t let the guest tag fool you, it\'s David, I couldn\'t log in tonight. '
                   'Professor, you still owe me a rematch from last week."',
        "order": ["Plum", "White", "Mustard", "Scarlett"],
    },
    # The same guest disputes a line of Plum's own article. A lookup or a
    # challenge is the point; the article is not engine authority.
    "biography": {
        "turn": 14,
        "person": ("Peacock", "Peacock (Guest)"),
        "opening": [
            ("Peacock (Guest)", "Wikiclude says you read the Wall Street Journal every morning over breakfast, "
                                "Professor. I have only ever seen you with the Economist."),
        ],
        "trigger": 'Peacock (Guest) said: "Wikiclude says you read the Wall Street Journal every morning over '
                   'breakfast, Professor. I have only ever seen you with the Economist."',
        "order": ["Plum", "White", "Green", "Scarlett"],
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


def build(name, backend, settings, memory_store, canon):
    """One wrapper with the gate open, the canon attached and its logbook
    read (never written: nothing here debriefs)."""
    profile = PRESETS.get(name, Profile()).with_dials(chattiness=1.0)
    character = build_character(name, profile=profile)
    wrapper = LLMCharacter(character, backend, settings=settings, canon=canon)
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


def observation(seat, turn=12):
    """A minimal mid-game view: enough for remark_prompt, no real deal."""
    from dataclasses import replace
    from clude_constraints import propagate
    from clude_core.state import ClueObservation
    obs = ClueObservation(
        n_players=len(ROSTER), my_index=seat,
        own_hand=frozenset(HANDS[seat]),
        active_players=tuple(True for _ in ROSTER),
        hand_sizes={i: 3 for i in range(len(ROSTER))},
        suggestion_log=(), accusation_log=(), turn=turn,
    )
    return replace(obs, mask=propagate(obs))


def classify(text):
    low = text.lower()
    if any(w in low.split() or f"{w}," in low or f"{w}." in low for w in GAME_WORDS):
        return "game"
    if any(p in low for p in GAME_PHRASES):
        return "game"
    return "other"


def scene_names(scene):
    """A label per seat as the table screen shows them: the token, and a
    person's display name after it for a seat a person holds."""
    names = list(ROSTER)
    person = scene.get("person")
    if person:
        names[ROSTER.index(person[0])] = person[1]
    return names


def seat_of(scene, who):
    """The seat a scene speaker holds, by token or by a person's display name."""
    names = scene_names(scene)
    return names.index(who) if who in names else ROSTER.index(who)


def run_scene(key, scene, wrappers, rounds, verbose):
    # `wrappers` is built fresh per scene by the caller, so one scene's
    # talk cannot bleed into the next through a wrapper's own memory.
    names = scene_names(scene)
    turn = scene.get("turn", 12)
    talk = list(scene["opening"])
    for who, what in talk:
        heard = RemarkEvent(turn, seat_of(scene, who), what, "chat")
        for wrapper in wrappers.values():
            wrapper.hear(heard)
    lines = []
    order = scene["order"]
    for k in range(rounds):
        speaker = order[k % len(order)]
        wrapper = wrappers[speaker]
        seat = ROSTER.index(speaker)
        if k == 0:
            trigger = scene["trigger"]
        else:
            who, what = talk[-1]
            trigger = f'{names[seat_of(scene, who)]} said: "{what}"'
        try:
            say = wrapper.react(observation(seat, turn), trigger, names=names)
        except Exception as exc:
            say = None
            lines.append({"round": k + 1, "speaker": speaker, "turn": turn, "error": str(exc)})
            if verbose:
                print(f"    {speaker}: <error: {exc}>")
            continue
        lookups = list(wrapper.decisions[-1].lookups) if wrapper.decisions else []
        if not say:
            lines.append({"round": k + 1, "speaker": speaker, "turn": turn, "say": "",
                          "kind": "silent", "lookups": lookups})
            if verbose:
                print(f"    {speaker}: <silence>")
            continue
        talk.append((speaker, say))
        heard = RemarkEvent(turn, seat, say, "reaction")
        for name, other in wrappers.items():
            if name != speaker:
                other.hear(heard)
        kind = classify(say)
        lines.append({"round": k + 1, "speaker": speaker, "turn": turn, "say": say,
                      "kind": kind, "lookups": lookups})
        if verbose:
            marks = f" [{kind}" + (f", looked up {', '.join(lookups)}" if lookups else "") + "]"
            print(f"    {speaker}{marks}: {say}")
    return {"scene": key, "turn": turn, "person": scene.get("person"),
            "opening": scene["opening"], "lines": lines}


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
    ap.add_argument("--memory-store", default="data/phase14/memory-snapshot-20261101",
                    help="store to read logbooks from, read-only; '' for none")
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--effort", default="low")
    ap.add_argument("--max-tokens", type=int, default=200)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--out", default="data/phase13-rehearsal-2")
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
        # The first harness measured $0.0046 a call (30 calls, $0.1373) with
        # the system block cached; harness 2 adds the heard lines and the
        # canon index to every request, so allow twice that, and a cold
        # figure with nothing cached (about 2,000 system tokens a call at
        # $5 per million in, 50 tokens out at $25).
        measured, warm_each = 0.0046, 0.0092
        cold_each = 2600 * 5e-6 + 50 * 25e-6
        print(f"scenes      : {', '.join(keys)}")
        print(f"rounds each : {args.rounds}")
        print(f"model calls : {calls}")
        print(f"estimate    : ${calls * warm_each:.2f} expected "
              f"(twice the measured ${measured} a call), ${calls * cold_each:.2f} if nothing caches")
        print("approve before running with --backend anthropic")
        return 0

    if args.backend == "anthropic":
        from clude_llm.anthropic_backend import AnthropicBackend
        from clude_web.config import anthropic_key
        backend = Metering(AnthropicBackend(model=args.model, effort=args.effort,
                                            api_key=anthropic_key()))
    elif args.backend == "stub":
        backend = stub_backend()
    else:
        backend = NullBackend()

    settings = LLMSettings(model=args.model, effort=args.effort,
                           remark_max_tokens=args.max_tokens, speak=True)
    canon = WikiCanon()

    print(f"backend {args.backend}; harness {HARNESS}; chattiness forced to 1.0; "
          f"{len(keys)} scene(s) x {args.rounds} rounds")
    results = []
    for key in keys:
        print(f"\n  == {key} ==")
        scene = SCENES[key]
        person = scene.get("person")
        wrappers = {}
        for name in ROSTER:
            if person and name == person[0]:
                continue
            wrappers[name] = build(name, backend, settings, args.memory_store or None, canon)
            wrappers[name].rng = Random(args.seed)
        results.append(run_scene(key, scene, wrappers, args.rounds, not args.quiet))

    # tally
    tally = {"game": 0, "other": 0, "silent": 0, "error": 0, "lookups": 0}
    for r in results:
        for line in r["lines"]:
            if "error" in line:
                tally["error"] += 1
            else:
                tally[line["kind"]] += 1
                tally["lookups"] += len(line.get("lookups", []))
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
        json.dump({"harness": HARNESS, "date": str(date.today()), "hears": True, "canon": True,
                   "backend": args.backend, "model": args.model, "effort": args.effort,
                   "chattiness": 1.0, "rounds": args.rounds,
                   "memory_store": args.memory_store,
                   "usage": usage, "tally": tally, "scenes": results},
                  fh, indent=2)
        fh.write("\n")
    print(f"  transcript: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
