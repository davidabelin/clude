"""Offline sizing and guarded paid-screen helpers for Phase 14."""
from __future__ import annotations

import json
import math
from collections import Counter, deque
from pathlib import Path

from clude_agents import AGENT_SPECS, Character
from clude_agents.bandit import BanditAgent
from clude_agents.decision_tree import DecisionTreeAgent
from clude_agents.markov import MarkovAgent
from clude_agents.personality import PRESETS
from clude_core.events import AccusationEvent, RemarkEvent, SuggestionEvent
from clude_llm import LLMCharacter, LLMResult, LLMSettings, ScriptedBackend, WikiCanon
from clude_llm.anthropic_backend import estimate_cost
from clude_storage import GameRecord, LocalStore, Logbook
from clude_training import memory as method_memory
from clude_training.arena import DEFAULT_ROSTER, run_arena
from clude_training.recalibration import (
    FrozenCorpus,
    experiment_context,
    load_staged_methods,
    verify_narrative_logbooks,
)
from clude_training.replay import seat_view
from clude_web import replay_data

LEASH_GAMES = 8
CHAT_GAMES = 8
MEMORY_GAMES = 8
PAID_VALUES = (0.0, 0.25, 0.5, 0.75, 1.0)
CHARS_PER_TOKEN = 4


class FirstAllowedBackend(ScriptedBackend):
    """Offline backend that answers each schema with its first option."""

    name = "phase14-offline"

    def __init__(self) -> None:
        super().__init__([])

    def complete(self, request):
        self.requests.append(request)
        self.calls += 1
        answer = {}
        for name, field in request.schema.get("properties", {}).items():
            if name == "say":
                answer[name] = "Noted." if request.kind == "remark" else ""
            elif field.get("enum"):
                answer[name] = field["enum"][0]
            elif field.get("type") == "string":
                answer[name] = ""
        return LLMResult(text=json.dumps(answer), stop_reason="end_turn", model=self.name)


def _request_chars(request) -> int:
    return sum(map(len, (request.system, request.user, request.memory, request.canon))) + len(
        json.dumps(request.schema, sort_keys=True)
    ) + len(json.dumps(list(request.tools), sort_keys=True))


def _request_summary(requests: list, model: str, output_tokens_per_call: int) -> dict:
    input_tokens = sum(math.ceil(_request_chars(request) / CHARS_PER_TOKEN) for request in requests)
    output_tokens = len(requests) * output_tokens_per_call
    cost = estimate_cost(model, input_tokens, output_tokens, 0)
    kinds = Counter(request.kind for request in requests)
    widths = []
    for request in requests:
        enums = [
            len(field["enum"])
            for field in request.schema.get("properties", {}).values()
            if field.get("enum")
        ]
        widths.extend(enums)
    return {
        "calls": len(requests),
        "kinds": dict(sorted(kinds.items())),
        "input_tokens_no_cache": input_tokens,
        "assumed_output_tokens": output_tokens,
        "estimated_list_price_cost": cost,
        "mean_menu_width": sum(widths) / len(widths) if widths else None,
        "max_menu_width": max(widths, default=None),
    }


def _documents(stage_dir: Path) -> tuple[dict, dict]:
    stage, documents = load_staged_methods(stage_dir)
    missing = sorted({"Mustard", "White", "Green"} - set(documents))
    if missing:
        raise ValueError(f"paid preflight requires accepted staged methods; missing {missing}")
    return stage, documents


def _agent(name: str, documents: dict):
    if name == "Mustard":
        return DecisionTreeAgent(extra_rows=method_memory.extra_rows(documents[name]))
    if name == "White":
        return MarkovAgent(priors=method_memory.priors(documents[name]))
    if name == "Green":
        return BanditAgent()
    return AGENT_SPECS[name].factory()


def _overrides(documents: dict, roster) -> tuple[dict, dict]:
    names = set(roster)
    overrides = {
        name: _agent(name, documents) for name in ("Mustard", "White", "Green") if name in names
    }
    states = (
        {"Green": {"arms": documents["Green"].get("arms", {})}}
        if "Green" in overrides else {}
    )
    return overrides, states


def _leash_values(character: str) -> tuple:
    current = PRESETS[character].leash
    return tuple(dict.fromkeys((0.0, current, min(1.0, current + 0.25), 1.0)))


def analyse_leash(documents: dict, model: str) -> dict:
    rows = []
    all_requests = []
    for character in PRESETS:
        roster = (character, "floor")
        overrides, states = _overrides(documents, roster)
        for value in _leash_values(character):
            backend = FirstAllowedBackend()
            result = run_arena(
                n_games=LEASH_GAMES,
                seed=143000,
                roster=roster,
                player_counts=(3,),
                profiles={character: PRESETS[character].with_dials(leash=value)},
                llm_backend=backend,
                llm_settings=LLMSettings(model=model, debrief=False),
                llm_characters=(character,),
                llm_canon=WikiCanon(),
                agent_overrides=overrides,
                agent_states=states,
                run_id=f"phase14-preflight-leash-{character.lower()}-{value:g}",
            )
            summary = _request_summary(backend.requests, model, 60)
            rows.append({
                "character": character, "value": value, "games": LEASH_GAMES,
                "decisions": result.per_player[character].llm_decisions, **summary,
            })
            all_requests.extend(backend.requests)
    return {"rows": rows, "total": _request_summary(all_requests, model, 60)}


def analyse_memory(documents: dict, memory_root: Path, model: str) -> dict:
    manifest = verify_narrative_logbooks(memory_root)
    store = LocalStore(memory_root)
    sizes = []
    for character in PRESETS:
        book = Logbook(store, character)
        for value in PAID_VALUES:
            block = book.memory(value)
            sizes.append({
                "character": character, "value": value, "characters": len(block),
                "words": len(block.split()), "estimated_tokens": math.ceil(len(block) / CHARS_PER_TOKEN),
            })

    rows = []
    all_requests = []
    overrides, states = _overrides(documents, DEFAULT_ROSTER)
    for value in PAID_VALUES:
        backend = FirstAllowedBackend()
        profiles = {name: PRESETS[name].with_dials(memory=value) for name in PRESETS}
        result = run_arena(
            n_games=MEMORY_GAMES,
            seed=143100,
            roster=DEFAULT_ROSTER,
            player_counts=(4,),
            profiles=profiles,
            llm_backend=backend,
            llm_settings=LLMSettings(model=model, debrief=False),
            llm_canon=WikiCanon(),
            logbook_store=store,
            logbooks_readonly=True,
            agent_overrides=overrides,
            agent_states=states,
            run_id=f"phase14-preflight-memory-{value:g}",
        )
        summary = _request_summary(backend.requests, model, 60)
        rows.append({
            "value": value, "games": MEMORY_GAMES,
            "decisions": sum(stats.llm_decisions for stats in result.per_player.values()),
            **summary,
        })
        all_requests.extend(backend.requests)
    return {
        "snapshot_sha256": manifest["snapshot_sha256"],
        "prompt_sizes": sizes,
        "rows": rows,
        "total": _request_summary(all_requests, model, 60),
    }


def _base_chat_records(corpus: FrozenCorpus, documents: dict, root: Path) -> list[GameRecord]:
    store = LocalStore(root)
    run_id = "phase14-preflight-chat"
    indices = store.list_games(run_id)
    if len(indices) != CHAT_GAMES:
        overrides, states = _overrides(documents, DEFAULT_ROSTER)
        run_arena(
            n_games=CHAT_GAMES,
            seed=143200,
            roster=DEFAULT_ROSTER,
            player_counts=(4,),
            agent_overrides=overrides,
            agent_states=states,
            store=store,
            run_id=run_id,
        )
        indices = store.list_games(run_id)
    return [GameRecord.from_dict(store.get_game(run_id, index)) for index in indices]


def _wrappers_for_record(record: GameRecord, value: float, documents: dict, store, backend) -> dict:
    labels = [seat.label for seat in sorted(record.seats, key=lambda seat: seat.seat)]
    wrappers = {}
    for seat, name in enumerate(labels):
        if name not in AGENT_SPECS:
            continue
        spec = AGENT_SPECS[name]
        character = Character(
            _agent(name, documents),
            profile=PRESETS[name].with_dials(chattiness=value),
            confidence_fn=spec.confidence_fn,
        )
        wrapper = LLMCharacter(
            character, backend, settings=LLMSettings(debrief=False), canon=WikiCanon()
        )
        wrapper.attach_logbook(Logbook(store, name))
        wrapper.reset(record.seed)
        if name == "Green":
            wrapper.character.agent.load_state({"arms": documents["Green"].get("arms", {})})
        wrapper.new_game(labels)
        wrappers[seat] = wrapper
    return wrappers


def _simulate_reactions(record: GameRecord, value: float, documents: dict, store, backend) -> dict:
    """Replay fixed game triggers through off-turn reply draws and the backend.

    ``opportunities`` counts suggestion/accusation events, not individual seat
    offers. Several seats and reply chains can answer one event. Keep game
    events fixed, cap spoken replies at two per turn and forty per game, and
    return calls, usage and lines. A real backend spends money; this does not
    play new games or measure how replies change their outcomes.
    """
    labels = [seat.label for seat in sorted(record.seats, key=lambda seat: seat.seat)]
    wrappers = _wrappers_for_record(record, value, documents, store, backend)
    total = 0
    served_turn = Counter()
    suggestions = 0
    opportunities = 0
    for event in record.events:
        if isinstance(event, SuggestionEvent):
            suggestions += 1
            actor = event.suggestion.suggester
        elif isinstance(event, AccusationEvent):
            actor = event.accusation.accuser
        else:
            continue
        opportunities += 1
        trigger = replay_data.describe_event(event, labels, reveal=False)[1]
        queue = deque()

        def offer(speaker: int, depth: int, text: str) -> None:
            queued = {seat for seat, _depth, _text in queue}
            for seat, wrapper in sorted(wrappers.items()):
                if seat == speaker or seat in queued or len(queue) >= 2:
                    continue
                if wrapper.rng.random() < wrapper.profile.chattiness ** (depth + 1):
                    queue.append((seat, depth, text))

        offer(actor, 0, trigger)
        while queue and total < 40 and served_turn[event.turn] < 2:
            seat, depth, queued_trigger = queue.popleft()
            obs = seat_view(record, seat, suggestions)
            text = wrappers[seat].react(obs, queued_trigger, labels)
            if not text:
                continue
            total += 1
            served_turn[event.turn] += 1
            remark = RemarkEvent(event.turn, seat, text, "reaction")
            for other, wrapper in wrappers.items():
                if other != seat:
                    wrapper.hear(remark)
            offer(seat, depth + 1, f'{labels[seat]} said: "{text}"')
    decisions = [decision for wrapper in wrappers.values() for decision in wrapper.decisions]
    return {
        "opportunities": opportunities,
        "calls": sum(int(decision.called) for decision in decisions),
        "spoken": total,
        "fallbacks": sum(int(decision.fallback is not None) for decision in decisions),
        "input_tokens": sum(decision.input_tokens for decision in decisions),
        "output_tokens": sum(decision.output_tokens for decision in decisions),
        "cached_tokens": sum(decision.cached_tokens for decision in decisions),
    }


def analyse_chattiness(
    corpus: FrozenCorpus, documents: dict, memory_root: Path, work_root: Path, model: str
) -> dict:
    verify_narrative_logbooks(memory_root)
    store = LocalStore(memory_root)
    records = _base_chat_records(corpus, documents, work_root)
    rows = []
    all_requests = []
    for value in PAID_VALUES:
        backend = FirstAllowedBackend()
        totals = Counter()
        for record in records:
            totals.update(_simulate_reactions(record, value, documents, store, backend))
        summary = _request_summary(backend.requests, model, 35)
        rows.append({"value": value, "games": len(records), **dict(totals), **summary})
        all_requests.extend(backend.requests)
    return {"rows": rows, "total": _request_summary(all_requests, model, 35)}


def paid_preflight(
    corpus: FrozenCorpus,
    stage_dir: Path,
    memory_root: Path,
    work_root: Path,
    *,
    model: str,
) -> dict:
    """Run every free analysis and return a conservative paid quote."""
    stage, documents = _documents(stage_dir)
    leash = analyse_leash(documents, model)
    memory = analyse_memory(documents, memory_root, model)
    chat = analyse_chattiness(corpus, documents, memory_root, work_root, model)
    screen_costs = [
        section["total"]["estimated_list_price_cost"] for section in (leash, memory, chat)
    ]
    screen_cost = sum(cost or 0.0 for cost in screen_costs)
    # Worst case: all three paid dials need a 24-pair confirmation. Scale
    # each screen's no-cache estimate by confirmation games / screen games.
    confirm = 0.0
    for section, games in ((leash, LEASH_GAMES * len(leash["rows"])),
                           (memory, MEMORY_GAMES * len(PAID_VALUES)),
                           (chat, CHAT_GAMES * len(PAID_VALUES))):
        cost = section["total"]["estimated_list_price_cost"] or 0.0
        confirm += cost * (48 / games)
    return {
        "phase": 14,
        "context": experiment_context(corpus.root / "manifest.json"),
        "corpus_sha256": corpus.sha256,
        "method_stage_sha256": stage["documents"],
        "memory_snapshot_sha256": memory["snapshot_sha256"],
        "model": model,
        "assumptions": {
            "chars_per_input_token": CHARS_PER_TOKEN,
            "decision_output_tokens_per_call": 60,
            "remark_output_tokens_per_call": 35,
            "cache_discount": "none; conservative upper estimate",
            "confirmation": "worst case, all three paid dials shortlisted for 24 paired games",
            "fixture_refresh": "excluded; quote separately after final acceptance",
        },
        "leash": leash,
        "chattiness": chat,
        "memory": memory,
        "quote": {
            "screen_estimate": round(screen_cost, 2),
            "confirmation_ceiling": round(confirm, 2),
            "approval_ceiling": round(screen_cost + confirm, 2),
        },
        "paid_calls_made": 0,
        "approval_status": "required",
    }


def _arena_usage(result) -> dict:
    stats = list(result.per_player.values())
    return {
        "calls": sum(row.llm_calls for row in stats),
        "fallbacks": sum(row.llm_fallbacks for row in stats),
        "input_tokens": sum(row.llm_input_tokens for row in stats),
        "output_tokens": sum(row.llm_output_tokens for row in stats),
        "cached_tokens": sum(row.llm_cached_tokens for row in stats),
        "list_price_cost": round(sum(game.cost or 0.0 for game in result.games), 6),
    }


def _assert_frozen_inputs(
    preflight: dict, corpus: FrozenCorpus, stage: dict, memory_manifest: dict
) -> None:
    context = experiment_context(corpus.root / "manifest.json")
    checks = {
        "corpus_sha256": (preflight["corpus_sha256"], corpus.sha256),
        "code_sha256": (preflight["context"]["code_sha256"], context["code_sha256"]),
        "weights_sha256": (preflight["context"]["weights_sha256"], context["weights_sha256"]),
        "method_stage_sha256": (preflight["method_stage_sha256"], stage["documents"]),
        "memory_snapshot_sha256": (
            preflight["memory_snapshot_sha256"], memory_manifest["snapshot_sha256"],
        ),
    }
    changed = {name: {"expected": old, "actual": new} for name, (old, new) in checks.items() if old != new}
    if changed:
        raise RuntimeError(f"paid inputs changed after preflight: {changed}")


def paid_screen(
    corpus: FrozenCorpus,
    stage_dir: Path,
    memory_root: Path,
    work_root: Path,
    preflight: dict,
    backend,
    *,
    model: str,
    on_update=None,
) -> dict:
    """Run the approved paid screens, stopping on the first fallback."""
    stage, documents = _documents(stage_dir)
    memory_manifest = verify_narrative_logbooks(memory_root)
    _assert_frozen_inputs(preflight, corpus, stage, memory_manifest)
    result = {
        "phase": 14,
        "model": model,
        "preflight_quote": preflight["quote"],
        "corpus_sha256": corpus.sha256,
        "code_sha256": preflight["context"]["code_sha256"],
        "weights_sha256": preflight["context"]["weights_sha256"],
        "method_stage_sha256": stage["documents"],
        "memory_snapshot_sha256": memory_manifest["snapshot_sha256"],
        "leash": [], "chattiness": [], "memory": [], "complete": False, "valid": True,
    }

    def updated():
        if on_update is not None:
            on_update(result)

    for character in PRESETS:
        roster = (character, "floor")
        overrides, states = _overrides(documents, roster)
        for value in _leash_values(character):
            _assert_frozen_inputs(preflight, corpus, stage, memory_manifest)
            arena = run_arena(
                n_games=LEASH_GAMES, seed=143000, roster=roster, player_counts=(3,),
                profiles={character: PRESETS[character].with_dials(leash=value)},
                llm_backend=backend, llm_settings=LLMSettings(model=model, debrief=False),
                llm_characters=(character,), llm_canon=WikiCanon(),
                agent_overrides=overrides, agent_states=states,
                run_id=f"phase14-paid-leash-{character.lower()}-{value:g}",
            )
            usage = _arena_usage(arena)
            result["leash"].append({
                "character": character, "value": value, "games": LEASH_GAMES,
                "stats": arena.per_player[character].to_dict(), "usage": usage,
            })
            updated()
            if usage["fallbacks"]:
                result.update({"valid": False, "stopped": "leash fallback"})
                updated()
                return result

    records = _base_chat_records(corpus, documents, work_root)
    memory_store = LocalStore(memory_root)
    for value in PAID_VALUES:
        _assert_frozen_inputs(preflight, corpus, stage, memory_manifest)
        totals = Counter()
        for record in records:
            totals.update(_simulate_reactions(record, value, documents, memory_store, backend))
            if totals["fallbacks"]:
                break
        totals["list_price_cost"] = estimate_cost(
            model, totals["input_tokens"], totals["output_tokens"], totals["cached_tokens"]
        )
        result["chattiness"].append({"value": value, "games": len(records), **dict(totals)})
        updated()
        if totals["fallbacks"]:
            result.update({"valid": False, "stopped": "chattiness fallback"})
            updated()
            return result

    overrides, states = _overrides(documents, DEFAULT_ROSTER)
    for value in PAID_VALUES:
        _assert_frozen_inputs(preflight, corpus, stage, memory_manifest)
        profiles = {name: PRESETS[name].with_dials(memory=value) for name in PRESETS}
        arena = run_arena(
            n_games=MEMORY_GAMES, seed=143100, roster=DEFAULT_ROSTER, player_counts=(4,),
            profiles=profiles, llm_backend=backend,
            llm_settings=LLMSettings(model=model, debrief=False), llm_canon=WikiCanon(),
            logbook_store=memory_store, logbooks_readonly=True,
            agent_overrides=overrides, agent_states=states,
            run_id=f"phase14-paid-memory-{value:g}",
        )
        usage = _arena_usage(arena)
        result["memory"].append({
            "value": value, "games": MEMORY_GAMES,
            "per_character": {name: stats.to_dict() for name, stats in arena.per_player.items()},
            "usage": usage,
        })
        updated()
        if usage["fallbacks"]:
            result.update({"valid": False, "stopped": "memory fallback"})
            updated()
            return result
    result["complete"] = True
    updated()
    return result
