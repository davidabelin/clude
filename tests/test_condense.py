"""Condensing a logbook: the digest a character's own model writes over its
entries, the flag merges it makes, and what read-back and the debrief show
afterwards. Everything runs on scripted backends."""
from __future__ import annotations

import json

import pytest

from clude_agents.personality import Profile
from clude_llm import (
    CONDENSE_KIND,
    CONDENSE_SCHEMA,
    LLMResult,
    LLMSettings,
    ScriptedBackend,
    condense_logbook,
    condense_prompt,
    condense_request,
    load_persona,
    load_rules,
    parse_response,
    schema_for,
)
from clude_llm.player import CONDENSE_MAX_TOKENS
from clude_llm.prompt import system_prompt
from clude_storage import LocalStore, Logbook, LogbookDigest, LogbookEntry, LogbookHead
from tests.test_debrief import DEBRIEF, _wrapper
from tests.test_debrief import _record as _debrief_record
from tests.test_logbooks import _entries, _record

DIGEST = {
    "overview": "Four games of parking; I win when I leave a room early.",
    "flag_map": [{"flag": "bluffing", "into": "parking"}, {"flag": "never-used", "into": "parking"}],
    "themes": [
        {"flag": "parking", "lesson": "Leave a room once nobody can refute it."},
        {"flag": "Bluffing", "lesson": "Merged into parking, so this repeat is dropped."},
    ],
}


def _logbook(tmp_path, n, identity="Scarlett"):
    logbook = Logbook(LocalStore(tmp_path), identity)
    for entry in _entries(n, identity):  # odd serials carry parking, even ones bluffing and parking
        logbook.add_entry(entry)
    return logbook


def test_condense_schema_and_parse():
    assert schema_for(CONDENSE_KIND) is CONDENSE_SCHEMA
    assert set(CONDENSE_SCHEMA["required"]) == set(DIGEST)
    assert CONDENSE_SCHEMA["additionalProperties"] is False
    assert parse_response(CONDENSE_KIND, json.dumps(DIGEST)) == DIGEST
    with pytest.raises(ValueError):
        parse_response(CONDENSE_KIND, "not json")


def test_condense_prompt_first_and_incremental():
    entries = _entries(3, "Scarlett")
    head = LogbookHead.empty("Scarlett")
    for entry in entries:
        head.absorb(entry)
    first = condense_prompt("Scarlett", head, None, entries)
    assert first.startswith("No game is on. This is a quiet hour with your logbook, Miss Scarlett: condense it.")
    assert "Fold entries #0001 to #0003" in first and "You have no digest yet" in first
    assert all(f"=== Entry #{serial:04d}," in first for serial in (1, 2, 3))
    assert "Standing instructions to yourself:\n  - Rule 3" in first
    assert "Flags you have used, with how many entries carry each: parking (3), bluffing (1)." in first
    assert first.endswith("Your identity in the logbook is Scarlett. Answer with JSON only.\n")

    digest = LogbookDigest(
        "Scarlett", 2, date="2026-10-08", overview="Earlier games.",
        themes=[{"flag": "parking", "lesson": "Leave sooner."}],
    )
    later = condense_prompt("Scarlett", head, digest, entries[2:])
    assert "Your digest so far, which these entries extend:" in later and "Earlier games." in later
    assert "- parking (3 games, latest #0003): Leave sooner." in later
    assert "=== Entry #0003," in later and "=== Entry #0002," not in later
    assert "folding in your previous overview" in later
    assert "Carry forward what still holds from your digest so far and from these entries; " in later
    assert "previous overview" not in first and "Carry forward what still holds; drop" in first


def test_condense_writes_the_digest_and_merges_flags(tmp_path):
    logbook = _logbook(tmp_path, 4)
    reply = LLMResult(
        text=json.dumps(DIGEST), stop_reason="end_turn", model="claude-test",
        input_tokens=900, output_tokens=120,
    )
    backend = ScriptedBackend([reply])
    report = condense_logbook(logbook, backend, LLMSettings(debrief_effort="high", debrief_timeout=99.0))
    assert report["called"] and report["fallback"] is None
    assert (report["through"], report["themes"], report["merged"], report["entries_renamed"]) == (4, 1, 1, 2)
    assert report["input_tokens"] == 900 and report["model"] == "claude-test"

    request = backend.requests[0]
    assert request.kind == CONDENSE_KIND and request.schema is CONDENSE_SCHEMA
    assert (request.effort, request.timeout, request.max_tokens) == ("high", 99.0, CONDENSE_MAX_TOKENS)
    assert request.system == system_prompt(load_persona("Scarlett"), load_rules())
    assert request.memory == ""

    digest = logbook.digest()
    assert digest.through == 4 and digest.model == "claude-test"
    assert digest.themes == [{"flag": "parking", "lesson": "Leave a room once nobody can refute it."}]
    assert digest.renamed == {"bluffing": "parking"}
    assert all(entry.flags == ["parking"] for entry in logbook.entries())
    head = logbook.head()
    assert head.flags == {"parking": [1, 2, 3, 4]}
    assert logbook.rebuild_head() == head
    memory = logbook.memory(1.0)
    assert "Your digest of entries #0001 to #0004" in memory and "=== Entry" not in memory

    # Nothing new: no call. A later entry is folded in on its own.
    assert condense_logbook(logbook, backend) == {"called": False, "fallback": "nothing new"}
    assert backend.calls == 1
    logbook.add_entry(LogbookEntry.build("Scarlett", 5, _record(seed=5, index=4), 0, {"flags": ["Bluffing"]}))
    request, entries, previous = condense_request(logbook)
    assert [entry.serial for entry in entries] == [5] and previous.through == 4
    assert "Your digest so far" in request.user and "=== Entry #0004," not in request.user


@pytest.mark.parametrize("reply", [
    "not json",
    {"overview": " ", "flag_map": [{"flag": "bluffing", "into": "parking"}], "themes": []},
    LLMResult(text="", stop_reason="refusal"),
    LLMResult(error="overloaded"),
    RuntimeError("connection reset"),
])
def test_condense_failures_write_nothing(tmp_path, reply):
    logbook = _logbook(tmp_path, 2)
    before = ([entry.to_dict() for entry in logbook.entries()], logbook.head())
    report = condense_logbook(logbook, ScriptedBackend([reply]))
    assert report["called"] and report["fallback"]
    assert logbook.digest() is None
    assert ([entry.to_dict() for entry in logbook.entries()], logbook.head()) == before


def test_debrief_and_read_back_after_condensing(tmp_path):
    store = LocalStore(tmp_path)
    logbook = _logbook(tmp_path, 3)
    logbook.save_digest(LogbookDigest("Scarlett", 2, date="2026-10-08", overview="Two games, folded."))
    wrapper = _wrapper(Profile(memory=1.0), responses=[DEBRIEF], store=store)
    assert "Two games, folded." in wrapper.memory_block
    assert "=== Entry #0003," in wrapper.memory_block and "=== Entry #0002," not in wrapper.memory_block

    entry = wrapper.debrief(_debrief_record(), 0)
    assert entry is not None and entry.serial == 4
    user = wrapper.backend.requests[-1].user
    assert "Your digest of entries #0001 to #0002" in user and "Two games, folded." in user
    assert "Entries since your digest, most recent last (summary and flags):" in user
    assert "- #0003 (" in user and "- #0001 (" not in user
