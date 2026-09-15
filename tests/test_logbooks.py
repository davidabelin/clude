"""Phase 7: logbooks -- the documents (`clude_storage.logbooks`), the
memory-depth renderer, and the `Logbook` over both store backends."""
from __future__ import annotations

import json

import pytest

from clude_core import engine
from clude_storage import (
    Dossier,
    GameRecord,
    GcsStore,
    LocalStore,
    Logbook,
    LogbookEntry,
    LogbookHead,
    SeatRecord,
    list_logbooks,
    memory_counts,
    render_entry,
    render_memory,
)
from clude_storage.logbooks import (
    entry_key,
    entry_outcome,
    head_key,
    method_key,
    normalize_flags,
    outcome_phrase,
)
from clude_training.self_play import make_bots
from tests.test_storage import _FakeClient

LABELS = ("Plum", "Mustard", "Green")


def _record(seed=7, labels=LABELS, run_id="r", index=0):
    n = len(labels)
    bots, observer = make_bots("floor", n)
    state, events = engine.run_game(n, bots, seed=seed, max_turns=120, observer=observer)
    seats = [
        SeatRecord(seat=p, suspect=state.suspects_in_play[p], label=labels[p], kind="character")
        for p in range(n)
    ]
    record = GameRecord.from_game(run_id, index, seed, state, events, seats)
    return GameRecord.from_dict(json.loads(json.dumps(record.to_dict())))


WRITTEN = {
    "title": "  The Ballroom stalemate ",
    "summary": "I counted every deal and still moved last.",
    "flags": ["Parking", "over confident", "parking", "", "slow-accuser", "a", "b", "c", "d"],
    "what_happened": "Mustard blundered into the Lounge and I let him.",
    "evaluations": [
        {"opponent": "Mustard", "evaluation": "Loud, transparent.", "notes": "Names his own cards."},
        {"opponent": "Scarlett", "evaluation": "Was not at the table."},
        "not a dict",
    ],
    "key_insights": ["A cleared room is a trap.", ""],
    "lessons_learned": ["Leave sooner."],
    "final_outcome": "I lost on time, not on logic.",
    "standing_instructions": [f"Instruction {i}" for i in range(12)],
    "dossiers": [
        {"opponent": "Mustard", "read": "Tells you what he holds if you wait."},
        {"opponent": "Green", "read": ""},
        {"opponent": "Peacock", "read": "Absent, so ignored."},
    ],
}


def test_keys_and_flags():
    assert head_key("Plum") == "logbooks/Plum/head.json"
    assert method_key("Plum") == "logbooks/Plum/method.json"
    assert entry_key("Plum", 12) == "logbooks/Plum/entries/0012.json"
    with pytest.raises(ValueError):
        entry_key("Plum", 0)
    with pytest.raises(ValueError):
        head_key("../Plum")
    assert normalize_flags(["Over Confident!", "parking", "PARKING", "", 3]) == ["over-confident", "parking"]
    assert len(normalize_flags([f"f{i}" for i in range(10)])) == 6


def test_entry_build_computes_the_facts_and_normalises_the_narrative():
    record = _record()
    entry = LogbookEntry.build("Plum", 1, record, 0, WRITTEN, model="claude-test")
    assert entry.game_id == "r/00000"
    assert entry.token == record.seats[0].suspect
    assert entry.opponents() == ["Mustard", "Green"]
    assert entry.date == record.created_at[:10]
    assert entry.title == "The Ballroom stalemate"
    assert entry.flags == ["parking", "over-confident", "slow-accuser", "a", "b", "c"]
    assert entry.key_insights == ["A cleared room is a trap."]
    assert len(entry.standing_instructions) == 8
    assert [e["opponent"] for e in entry.evaluations] == ["Mustard"]
    assert entry.dossiers == [{"opponent": "Mustard", "read": "Tells you what he holds if you wait."}]
    outcome = entry.outcome
    assert outcome["envelope"] == list(record.envelope)
    assert outcome["won"] == (record.winner == 0)
    assert outcome["winner"] == (record.seats[record.winner].label if record.winner is not None else None)
    assert isinstance(outcome["accused"], bool)
    back = LogbookEntry.from_dict(json.loads(json.dumps(entry.to_dict())))
    assert back == entry
    # An empty debrief still yields a well-formed entry.
    bare = LogbookEntry.build("Plum", 2, record, 0, None)
    assert bare.title == "" and bare.flags == [] and bare.dossiers == []


def test_outcome_phrases_cover_every_ending():
    assert outcome_phrase({"won": True, "turns": 24}) == "won in 24 turns"
    assert outcome_phrase({"won": False, "winner": "Mustard", "turns": 19}) == "lost; Mustard won in 19 turns"
    wrong = {"won": False, "accused": True, "accusation_correct": False, "winner": "Green", "turns": 9}
    assert outcome_phrase(wrong) == "accused wrongly and was eliminated; Green won"
    assert outcome_phrase({"won": False, "winner": None, "hit_cap": True, "turns": 200}) == "nobody won (turn cap at 200)"
    assert outcome_phrase({"won": False, "winner": None, "hit_cap": False}) == "nobody won (every player eliminated)"
    record = _record()
    out = entry_outcome(record, 1)
    assert out["hit_cap"] is False or record.winner is None


def test_head_absorbs_entries_and_rebuilds_from_them():
    record = _record()
    head = LogbookHead.empty("Plum")
    assert head.is_empty()
    first = LogbookEntry.build("Plum", 1, record, 0, WRITTEN)
    head.absorb(first)
    assert head.serial == 1
    assert head.tally["games"] == 1 and head.tally["last_game_id"] == "r/00000"
    assert head.standing_instructions == first.standing_instructions
    assert set(head.dossiers) == {"Mustard", "Green"}
    assert head.dossiers["Mustard"] == Dossier("Tells you what he holds if you wait.", 1, first.date, 1)
    assert head.dossiers["Green"] == Dossier("", 1, "", 0)  # present, no read yet
    assert head.flags["parking"] == [1]

    # A second entry with no standing instructions keeps the old list,
    # revises only the dossier it rewrote, and counts every opponent.
    second = LogbookEntry.build(
        "Plum", 2, _record(seed=8, index=1), 0,
        {"flags": ["parking"], "dossiers": [{"opponent": "Green", "read": "Copies whoever spoke last."}]},
    )
    head.absorb(second)
    assert head.serial == 2 and head.tally["games"] == 2
    assert head.standing_instructions == first.standing_instructions
    assert head.dossiers["Mustard"].games_together == 2 and head.dossiers["Mustard"].serial == 1
    assert head.dossiers["Green"] == Dossier("Copies whoever spoke last.", 2, second.date, 2)
    assert head.flags["parking"] == [1, 2]
    back = LogbookHead.from_dict(json.loads(json.dumps(head.to_dict())))
    assert back == head


def _entries(n, identity="Plum"):
    entries = []
    for serial in range(1, n + 1):
        written = {
            "title": f"Game {serial}",
            "summary": f"Summary {serial}.",
            "flags": ["parking"] if serial % 2 else ["bluffing", "parking"],
            "what_happened": f"Things happened in game {serial}.",
            "lessons_learned": [f"Lesson {serial}"],
            "standing_instructions": [f"Rule {serial}"],
            "dossiers": [{"opponent": "Mustard", "read": f"Read {serial}."}],
        }
        entries.append(LogbookEntry.build(identity, serial, _record(seed=serial, index=serial - 1), 0, written))
    return entries


def test_memory_counts_hit_the_four_anchors_and_are_monotone():
    assert memory_counts(4, 0.0) == (0, 0)
    assert memory_counts(4, 0.25) == (2, 0)
    assert memory_counts(4, 0.5) == (4, 0)
    assert memory_counts(4, 0.75) == (4, 2)
    assert memory_counts(4, 1.0) == (4, 4)
    assert memory_counts(0, 1.0) == (0, 0)
    assert memory_counts(10, 0.3) == (6, 0)  # float noise must not round up to 7
    previous = (0, 0)
    for step in range(0, 101):
        counts = memory_counts(7, step / 100)
        assert counts >= previous
        previous = counts
    with pytest.raises(ValueError):
        memory_counts(3, 1.5)


def test_render_memory_at_each_depth():
    entries = _entries(4)
    head = LogbookHead.empty("Plum")
    for entry in entries:
        head.absorb(entry)

    assert render_memory(LogbookHead.empty("Plum"), [], 1.0) == ""
    shallow = render_memory(head, entries, 0.0, opponents=["Mustard", "Green"])
    assert shallow.startswith("From your logbook, written by you after earlier games (4 games:")
    assert "Standing instructions to yourself:\n- Rule 4" in shallow
    assert "Your read on Mustard (4 games together, revised after entry #0004): Read 4." in shallow
    assert "Green" not in shallow.split("Your read on Mustard")[1]  # no read on Green yet
    assert "Entries" not in shallow and "Full entries" not in shallow

    index_half = render_memory(head, entries, 0.25, opponents=["Mustard"])
    assert "Entries #0003 to #0004 of 4, most recent last:" in index_half
    assert "- #0003 (" in index_half and "- #0001 (" not in index_half
    assert "Flags across these entries: parking (2), bluffing (1)" in index_half

    index_all = render_memory(head, entries, 0.5, opponents=["Mustard"])
    assert "Entries #0001 to #0004 of 4" in index_all
    assert "Summary 1." in index_all and "[flags: parking]" in index_all
    assert "Full entries" not in index_all

    half_full = render_memory(head, entries, 0.75, opponents=["Mustard"])
    assert "Full entries, most recent last:" in half_full
    assert "=== Entry #0003," in half_full and "=== Entry #0002," not in half_full
    assert "Things happened in game 4." in half_full
    assert "Rule 3" not in half_full  # old standing instructions are not repeated

    everything = render_memory(head, entries, 1.0, opponents=["Mustard"])
    assert all(f"=== Entry #{s:04d}," in everything for s in range(1, 5))
    lengths = [len(render_memory(head, entries, d / 10, opponents=["Mustard"])) for d in range(11)]
    assert lengths == sorted(lengths)

    # Every dossier when no table is given (the CLI's view).
    assert "Your read on Mustard" in render_memory(head, entries, 0.0)
    text = render_entry(entries[0])
    assert text.startswith("=== Entry #0001, ") and "Title: Game 1" in text and "Lessons learned:\n- Lesson 1" in text


def _exercise_logbook(store):
    assert list_logbooks(store) == []
    logbook = Logbook(store, "Plum")
    assert not logbook.exists()
    assert logbook.head().is_empty()
    assert logbook.next_serial() == 1
    assert logbook.memory(1.0) == ""

    entries = _entries(2)
    head = logbook.add_entry(entries[0])
    assert head.serial == 1
    assert logbook.next_serial() == 2
    logbook.add_entry(entries[1])
    assert logbook.serials() == [1, 2]
    assert logbook.entry(2).title == "Game 2"
    assert [e.serial for e in logbook.entries()] == [1, 2]
    assert logbook.head().tally["games"] == 2
    assert list_logbooks(store) == ["Plum"]
    assert "Entries #0001 to #0002 of 2" in logbook.memory(0.5, opponents=["Mustard"])
    with pytest.raises(ValueError):
        logbook.add_entry(entries[1])  # serial reused
    with pytest.raises(ValueError):
        logbook.add_entry(LogbookEntry.build("Green", 3, _record(), 2, {}))
    with pytest.raises(KeyError):
        logbook.entry(9)

    assert logbook.method() is None
    logbook.save_method({"games": {"r/00000": [[0.5, 1]]}})
    assert logbook.method() == {"games": {"r/00000": [[0.5, 1]]}}

    # Forget the head but keep the archive; the head can be rebuilt.
    removed = logbook.reset(keep_entries=True)
    assert removed == 2
    assert logbook.head().is_empty() and logbook.serials() == [1, 2] and logbook.method() is None
    assert logbook.next_serial() == 3
    rebuilt = logbook.rebuild_head()
    assert rebuilt.serial == 2 and rebuilt.tally["games"] == 2
    assert rebuilt == logbook.head()

    # Forget everything.
    assert logbook.reset() == 3
    assert not logbook.exists()
    assert logbook.serials() == [] and logbook.head().is_empty()
    assert logbook.reset() == 0


def test_logbook_over_a_local_store(tmp_path):
    _exercise_logbook(LocalStore(tmp_path / "records"))
    assert Logbook(LocalStore(tmp_path), "Plum").head().is_empty()
    with pytest.raises(ValueError):
        Logbook(LocalStore(tmp_path), "no/slashes")


def test_logbook_over_a_gcs_store_double():
    _exercise_logbook(GcsStore("clude-game-data", "arena", client=_FakeClient()))
