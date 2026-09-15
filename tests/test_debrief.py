"""Phase 7c: narrative memory -- the debrief that writes an entry, the
memory block read back at the `memory` dial's depth, and the request and
backend changes that carry it. Everything runs on fake backends."""
from __future__ import annotations

import json
import random

import pytest

from clude_agents.personality import PRESETS, Profile
from clude_core import engine
from clude_core.engine import MoveChoice
from clude_llm import (
    LLMCharacter,
    LLMRequest,
    LLMResult,
    LLMSettings,
    LOGBOOK_KIND,
    LOGBOOK_SCHEMA,
    NullBackend,
    RecordingBackend,
    ReplayBackend,
    ScriptedBackend,
    debrief_prompt,
    parse_response,
    resolve_opponents,
    schema_for,
)
from clude_llm.anthropic_backend import AnthropicBackend
from clude_llm.schema import CHOICE_SCHEMA
from clude_storage import GameRecord, LocalStore, Logbook, LogbookEntry, SeatRecord
from clude_training.self_play import make_bots
from tests.test_llm import PERSONA, RULES, _FakeClient, _character, _obs, _response

DEBRIEF = {
    "title": "Opening night",
    "summary": "Rushed the Kitchen and was lucky the floor caught up.",
    "flags": ["Rushing", "kitchen"],
    "what_happened": "I named the Kitchen three times and nobody could refute it.",
    "evaluations": [
        {"opponent": "Mrs. Peacock", "evaluation": "Cautious.", "notes": "Never repeated a card."},
        {"opponent": "P2 White (floor)", "evaluation": "Purely logical.", "notes": ""},
        {"opponent": "Professor Plum", "evaluation": "Was not at this table.", "notes": ""},
    ],
    "key_insights": ["Peacock waits for proof."],
    "lessons_learned": ["Accuse when the floor says so, not before."],
    "final_outcome": "A win, on the floor's arithmetic more than mine.",
    "standing_instructions": ["Accuse when the floor has proven all three."],
    "dossiers": [
        {"opponent": "Mrs. Peacock", "read": "Slow to accuse; her silence means nothing."},
        {"opponent": "floor", "read": "Logic only."},
    ],
}


def _record(seed=3, labels=("Scarlett", "Peacock", "floor"), run_id="r", index=0):
    n = len(labels)
    bots, observer = make_bots("floor", n)
    state, events = engine.run_game(n, bots, seed=seed, max_turns=120, observer=observer)
    seats = [
        SeatRecord(seat=p, suspect=state.suspects_in_play[p], label=labels[p],
                   kind="floor" if labels[p] == "floor" else "character")
        for p in range(n)
    ]
    record = GameRecord.from_game(run_id, index, seed, state, events, seats)
    return GameRecord.from_dict(json.loads(json.dumps(record.to_dict())))


def _wrapper(profile=None, responses=(), store=None, identity="Scarlett"):
    wrapper = LLMCharacter(
        _character(profile or Profile(), seed=0), ScriptedBackend(list(responses)),
        persona=PERSONA, rules=RULES,
    )
    wrapper.reset(0)
    if store is not None:
        wrapper.attach_logbook(Logbook(store, identity))
    return wrapper


# ---------------------------------------------------------------------
# schema, request, backends
# ---------------------------------------------------------------------


def test_logbook_schema_and_parse():
    assert schema_for(LOGBOOK_KIND) is LOGBOOK_SCHEMA
    assert set(LOGBOOK_SCHEMA["required"]) == set(DEBRIEF)
    assert LOGBOOK_SCHEMA["additionalProperties"] is False
    assert "maxItems" not in json.dumps(LOGBOOK_SCHEMA)
    assert parse_response(LOGBOOK_KIND, json.dumps(DEBRIEF)) == DEBRIEF
    with pytest.raises(ValueError):
        parse_response(LOGBOOK_KIND, "[1, 2]")
    with pytest.raises(KeyError):
        schema_for("dance")


def test_request_key_and_backend_params_change_only_with_a_memory_block():
    plain = LLMRequest("sys", "user", CHOICE_SCHEMA, "move")
    assert plain.key() == LLMRequest("sys", "user", CHOICE_SCHEMA, "move", memory="").key()
    assert plain.key() == LLMRequest("sys", "user", CHOICE_SCHEMA, "move", effort="max", max_tokens=9).key()
    remembering = LLMRequest("sys", "user", CHOICE_SCHEMA, "move", memory="From your logbook: ...")
    assert remembering.key() != plain.key()

    fake = _FakeClient(_response('{"choice": "A", "say": ""}'))
    backend = AnthropicBackend(client=fake)
    backend.complete(plain)
    call = fake.beta.messages.calls[-1]
    assert call["system"] == [{"type": "text", "text": "sys", "cache_control": {"type": "ephemeral"}}]
    assert call["max_tokens"] == 2048 and call["output_config"]["effort"] == "low"

    backend.complete(LLMRequest("sys", "user", LOGBOOK_SCHEMA, LOGBOOK_KIND,
                                memory="From your logbook: ...", effort="medium", max_tokens=4096))
    call = fake.beta.messages.calls[-1]
    assert call["system"] == [
        {"type": "text", "text": "sys", "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "From your logbook: ...", "cache_control": {"type": "ephemeral"}},
    ]
    assert call["max_tokens"] == 4096 and call["output_config"]["effort"] == "medium"
    assert call["output_config"]["format"]["schema"] is LOGBOOK_SCHEMA


def test_recording_stores_the_memory_block_once_and_replays_it(tmp_path):
    path = tmp_path / "rec.json"
    recorder = RecordingBackend(ScriptedBackend([{"choice": "A", "say": "one"}]), path)
    first = LLMRequest("sys", "user one", CHOICE_SCHEMA, "move", memory="block")
    second = LLMRequest("sys", "user two", CHOICE_SCHEMA, "move", memory="block")
    recorder.complete(first)
    recorder.complete(second)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["systems"]) == 2  # the system prompt and the block, each once
    assert all("memory" in entry for entry in data["entries"].values())
    replay = ReplayBackend(path)
    assert replay.complete(first).text == '{"choice": "A", "say": "one"}'
    assert replay.complete(second).ok and replay.hits == 2


# ---------------------------------------------------------------------
# read-back
# ---------------------------------------------------------------------


def _seed_logbook(store, n=2, identity="Scarlett"):
    logbook = Logbook(store, identity)
    for serial in range(1, n + 1):
        written = dict(DEBRIEF, title=f"Game {serial}", summary=f"Summary {serial}.")
        logbook.add_entry(LogbookEntry.build(
            identity, serial, _record(seed=serial, index=serial - 1), 0,
            resolve_opponents(written, _record(seed=serial, index=serial - 1), 0),
        ))
    return logbook


def test_read_back_follows_the_memory_dial_and_rides_every_decision(tmp_path):
    store = LocalStore(tmp_path)
    _seed_logbook(store, n=2)
    obs = _obs(own=("Rope",))
    choices = [MoveChoice("move", "Kitchen"), MoveChoice("move", "Study")]
    rng = random.Random(0)

    shallow = _wrapper(Profile(memory=0.0, leash=1.0), [{"choice": "A", "say": ""}], store)
    shallow.new_game(["Scarlett", "Peacock", "floor"])
    assert shallow.memory_block.startswith("From your logbook, written by you after earlier games (2 games:")
    assert "Your read on Peacock" in shallow.memory_block and "Entries" not in shallow.memory_block
    shallow.choose_movement(obs, choices, rng)
    request = shallow.backend.requests[-1]
    assert request.memory == shallow.memory_block and request.kind == "move"

    deep = _wrapper(Profile(memory=0.5, leash=1.0), [{"choice": "A", "say": ""}], store)
    deep.new_game(["Scarlett", "Peacock", "floor"])
    assert "Entries #0001 to #0002 of 2" in deep.memory_block
    assert "Full entries" not in deep.memory_block
    assert len(deep.memory_block) > len(shallow.memory_block)

    # No logbook, or an empty one, leaves the request exactly as Phase 6 sent it.
    bare = _wrapper(Profile(memory=0.5, leash=1.0), [{"choice": "A", "say": ""}])
    bare.new_game(["Scarlett", "Peacock", "floor"])
    bare.choose_movement(obs, choices, random.Random(0))
    empty = _wrapper(Profile(memory=1.0, leash=1.0), [{"choice": "A", "say": ""}], LocalStore(tmp_path / "empty"))
    empty.new_game(["Scarlett", "Peacock", "floor"])
    empty.choose_movement(obs, choices, random.Random(0))
    assert empty.memory_block == "" and bare.memory_block == ""
    assert empty.backend.requests[-1].key() == bare.backend.requests[-1].key()


# ---------------------------------------------------------------------
# the debrief
# ---------------------------------------------------------------------


def test_resolve_opponents_maps_every_alias_to_the_roster_label():
    record = _record()
    resolved = resolve_opponents(DEBRIEF, record, 0)
    assert [e["opponent"] for e in resolved["evaluations"]] == ["Peacock", "floor", "Professor Plum"]
    assert [d["opponent"] for d in resolved["dossiers"]] == ["Peacock", "floor"]
    # Peacock pilots the Mustard token here, so the token's name is hers too.
    token = resolve_opponents({"dossiers": [{"opponent": "Colonel Mustard", "read": "x"}]}, record, 0)
    assert token["dossiers"][0]["opponent"] == "Peacock"
    # The seat's own names never resolve to an opponent.
    own = resolve_opponents({"dossiers": [{"opponent": "Miss Scarlett", "read": "me"}]}, record, 0)
    assert own["dossiers"][0]["opponent"] == "Miss Scarlett"


def test_debrief_writes_an_entry_and_the_next_prompt_shows_it(tmp_path):
    store = LocalStore(tmp_path)
    record = _record()
    wrapper = _wrapper(Profile(), [DEBRIEF], store)
    wrapper.new_game(["Scarlett", "Peacock", "floor"])
    before = wrapper.character.rng.getstate()

    entry = wrapper.debrief(record, 0)
    assert entry is not None and entry.serial == 1 and entry.title == "Opening night"
    assert entry.flags == ["rushing", "kitchen"]
    assert [e["opponent"] for e in entry.evaluations] == ["Peacock", "floor"]
    assert [d["opponent"] for d in entry.dossiers] == ["Peacock", "floor"]
    assert entry.outcome["envelope"] == list(record.envelope)
    assert entry.model == "scripted"
    assert wrapper.character.rng.getstate() == before
    assert wrapper.summary()["entries"] == 1 and wrapper.llm_calls == 1
    assert wrapper.last_debrief["fallback"] is None and wrapper.last_debrief["serial"] == 1
    head = Logbook(store, "Scarlett").head()
    assert head.serial == 1 and head.dossiers["Peacock"].read.startswith("Slow to accuse")
    assert head.flags == {"rushing": [1], "kitchen": [1]}

    request = wrapper.backend.requests[-1]
    assert request.kind == LOGBOOK_KIND and request.schema is LOGBOOK_SCHEMA
    assert request.effort == "medium" and request.max_tokens == 4096 and request.memory == ""
    prompt = request.user
    assert prompt.startswith("The game is over. This is your debrief, Miss Scarlett")
    assert "The deal, face up" in prompt and "P1 Mustard (Peacock) held:" in prompt
    assert f"The envelope was {'/'.join(record.envelope)}." in prompt
    assert "Name opponents by their roster label: Peacock, floor." in prompt
    assert "Empty: this is your first entry." in prompt
    assert "Your final belief against the truth:" in prompt
    assert "(none: every decision had one option" in prompt  # no decisions were recorded

    # The second debrief sees the head, the index and the flag counts.
    wrapper.backend = ScriptedBackend([dict(DEBRIEF, title="Second", flags=["rushing"])])
    second = wrapper.debrief(_record(seed=4, index=1), 0)
    assert second.serial == 2
    prompt = wrapper.backend.requests[-1].user
    assert "Standing instructions to yourself:" in prompt
    assert "Earlier entries, most recent last" in prompt and "- #0001 (" in prompt
    assert "Flags you have used: kitchen (1), rushing (1)." in prompt
    assert Logbook(store, "Scarlett").head().flags["rushing"] == [1, 2]


def test_debrief_failures_write_nothing(tmp_path):
    store = LocalStore(tmp_path)
    record = _record()

    nothing = _wrapper(Profile(), [DEBRIEF])
    assert nothing.debrief(record, 0) is None
    assert nothing.last_debrief == {"called": False, "fallback": "no logbook"}

    off = _wrapper(Profile(), [DEBRIEF], store)
    off.settings = LLMSettings(debrief=False)
    assert off.debrief(record, 0) is None and off.backend.calls == 0

    for responses, reason in (
        ("not json at all", "malformed"),
        ([LLMResult(text="{}", stop_reason="refusal")], "refusal"),
        ([RuntimeError("boom")], "error: RuntimeError"),
    ):
        wrapper = _wrapper(Profile(), responses if isinstance(responses, list) else [responses], store)
        assert wrapper.debrief(record, 0) is None
        assert wrapper.last_debrief["fallback"].startswith(reason)
        assert wrapper.summary()["entries"] == 0
    null = LLMCharacter(_character(Profile()), NullBackend(), persona=PERSONA, rules=RULES)
    null.attach_logbook(Logbook(store, "Scarlett"))
    assert null.debrief(record, 0) is None and null.last_debrief["fallback"].startswith("error")
    assert Logbook(store, "Scarlett").serials() == []


# ---------------------------------------------------------------------
# the arena
# ---------------------------------------------------------------------


class _KindBackend:
    """Answers by request kind: the first option for a decision, a fixed
    entry for the debrief."""

    name = "kinds"

    def __init__(self):
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        if request.kind == LOGBOOK_KIND:
            reply = dict(DEBRIEF, dossiers=[{"opponent": "floor", "read": "Logic only."}])
        elif request.kind == "suggest":
            reply = {"suspect": "A", "weapon": "A", "say": ""}
        else:
            reply = {"choice": "A", "say": ""}
        return LLMResult(text=json.dumps(reply), stop_reason="end_turn", model="kinds")


def test_arena_debriefs_llm_seats_and_reads_the_logbook_back(tmp_path):
    from clude_training.arena import run_arena

    store = LocalStore(tmp_path)
    backend = _KindBackend()
    profiles = {"Scarlett": PRESETS["Scarlett"].with_dials(memory=0.5, leash=1.0)}
    result = run_arena(
        n_games=2, seed=9, roster=("Scarlett", "floor"), player_counts=(3,), max_turns=60,
        llm_backend=backend, profiles=profiles, logbook_store=store,
    )
    logbook = Logbook(store, "Scarlett")
    assert logbook.serials() == [1, 2]
    assert result.per_player["Scarlett"].llm_entries == 2
    assert "entries" in result.llm_table()
    debriefs = [r for r in backend.requests if r.kind == LOGBOOK_KIND]
    assert len(debriefs) == 2 and all(r.memory == "" for r in debriefs)
    decisions = [r for r in backend.requests if r.kind != LOGBOOK_KIND]
    first_game = [r for r in decisions if r.memory == ""]
    second_game = [r for r in decisions if "From your logbook" in r.memory]
    assert first_game and second_game
    assert "Entries #0001 to #0001 of 1" in second_game[0].memory
    assert logbook.head().tally["games"] == 2
    assert result.to_dict()["per_player"]["Scarlett"]["llm_entries"] == 2

    frozen = run_arena(
        n_games=1, seed=9, roster=("Scarlett", "floor"), player_counts=(3,), max_turns=60,
        llm_backend=_KindBackend(), profiles=profiles, logbook_store=store, logbooks_readonly=True,
    )
    assert logbook.serials() == [1, 2] and frozen.per_player["Scarlett"].llm_entries == 0
