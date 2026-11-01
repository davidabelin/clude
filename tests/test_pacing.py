"""The pacing harness measures the reaction queue as shipped (Phase 14
follow-up, docs/strategy-glossary.md "Reaction-queue pacing (2026-11-01)").

On a synthetic record and a draw forced to join: a turn serves three
lines (the soft cap), a trigger arriving on a full queue is counted and
draws nothing, the seats past the break are counted, a reply chain
reaches depth one and never two, the impatient mode drops what the
patient one serves, the game cap binds at forty-one, and `as_played`
counts only the stored ``reaction`` lines. The constants themselves are
pinned: the harness measures, it does not tune.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from clude_core import engine
from clude_core.events import GameOverEvent, RemarkEvent, SuggestionEvent
from clude_storage import GameRecord, SeatRecord
from clude_training import pacing
from clude_training.self_play import make_bots
from clude_web import chat

LABELS = ("Plum", "White", "Green", "david")
KINDS = ("llm", "llm", "llm", "human")


def _record(seed: int = 7, chat_turn: int = 2) -> GameRecord:
    bots, observer = make_bots("floor", len(LABELS))
    state, events = engine.run_game(len(LABELS), bots, seed=seed, max_turns=60, observer=observer)
    seats = [SeatRecord(p, state.suspects_in_play[p], LABELS[p], KINDS[p]) for p in range(len(LABELS))]
    record = GameRecord.from_game("pacing-test", 0, seed, state, events, seats)
    # A person's line, an as-played reaction (ignored on replay) and a
    # first-turn suggestion from a model seat's own on-turn remark.
    extra = [
        RemarkEvent(chat_turn, 3, "Who has the Rope?", "chat"),
        RemarkEvent(chat_turn, 0, "Quite.", "reaction"),
    ]
    new_events = []
    inserted = False
    for event in record.events:
        if not inserted and event.turn >= chat_turn:
            new_events.extend(extra)
            inserted = True
        new_events.append(event)
    return replace(record, events=new_events)


@pytest.fixture
def always(monkeypatch):
    monkeypatch.setattr(chat, "joins", lambda rng, p: True)


def test_the_queue_constants_are_the_shipped_ones():
    assert (chat.MAX_QUEUED, chat.PER_TURN, chat.PER_GAME) == (2, 2, 40)


def test_wrappers_are_the_model_seats_at_their_presets_or_a_set_dial():
    record = _record()
    wrappers = pacing.wrappers_for(record)
    assert sorted(wrappers) == [0, 1, 2], "the three llm seats, never the person"
    assert wrappers[0].profile.chattiness == pytest.approx(0.3), "Plum's current preset"
    forced = pacing.wrappers_for(record, chattiness=1.0)
    assert all(w.profile.chattiness == 1.0 for w in forced.values())
    assert isinstance(wrappers[0].backend, pacing.ReplyBackend) and wrappers[0].backend.last_refusal is None


def test_a_turn_carries_three_and_a_chain_stops_at_depth_one(always):
    record = _record()
    tally = pacing.measure(record, chattiness=1.0, patient=True)
    assert tally["served_total"] > 0 and tally["calls"] == tally["served_total"]
    assert max(int(k) for k in tally["served_per_turn"]) == chat.PER_TURN + chat.MAX_QUEUED - 1
    assert tally["turns_at_three_or_more"] >= 1
    assert set(map(int, tally["depth"])) <= {0, 1} and tally["depth"].get("1", 0) >= 1
    assert tally["longest_chain"] == 2
    assert tally["turn_cap_refusals"] >= 1, "a depth-two opportunity is refused by the turn cap"
    assert tally["opportunities"]["chat"] == 1 and tally["opportunities"]["suggestion"] >= 1
    assert tally["opportunities"].get("reply", 0) >= 1
    assert "reaction" not in tally["opportunities"], "the stored reaction is output, not input"


def test_the_sorted_scan_skips_later_seats_and_the_queue_can_be_full(always, monkeypatch):
    record = _record()
    patient = pacing.measure(record, chattiness=1.0, patient=True)
    # Three eligible seats on a person's line, two slots: the last is skipped.
    assert patient["skipped_by_position"]["2"] >= 1
    assert patient["triggers_full"] == 0, "the queue drains before the next event"
    impatient = pacing.measure(record, chattiness=1.0, patient=False)
    assert impatient["stale_drops"] >= 1 and patient["stale_drops"] == 0
    assert impatient["served_total"] <= patient["served_total"]


def test_the_game_cap_binds_at_forty_one(always):
    record = _record()
    # Many triggers: one chat line per turn from the person.
    events = []
    for turn in range(1, 60):
        events.append(RemarkEvent(turn, 3, f"Line {turn}.", "chat"))
    events.append(GameOverEvent(60, None, record.envelope))
    long = replace(record, events=events, turns=60)
    tally = pacing.measure(long, chattiness=1.0, patient=True)
    assert tally["served_total"] == chat.PER_GAME + 1 and tally["reached_game_cap"]
    assert tally["game_cap_refusals"] >= 1


def test_as_played_counts_the_stored_reactions_only():
    record = _record()
    played = pacing.as_played(record)
    assert played["reactions"] == 1 and played["per_character"] == {"Plum": 1}
    assert played["turns_with"] == {"1": 1}
    pooled = pacing.pool([pacing.measure(record, chattiness=1.0), pacing.measure(record, chattiness=1.0)])
    assert pooled["games"] == 2 and pooled["served_total"] == 2 * pacing.measure(record, chattiness=1.0)["served_total"]


def test_the_harness_restores_the_clock_and_the_draw():
    before = (chat.now, chat.delay, chat.joins)
    pacing.measure(_record(), chattiness=0.0)
    assert (chat.now, chat.delay, chat.joins) == before
