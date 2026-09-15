"""Phase 7a: rebuilding a game from its stored record
(`clude_training.replay`)."""
from __future__ import annotations

import json

import pytest

import clude_constraints
from clude_core import engine
from clude_core.bots import RandomBot
from clude_storage import GameRecord, SeatRecord
from clude_training.replay import seat_view, snapshots_from_record, state_from_record
from clude_training.self_play import DEFAULT_MAX_TURNS, generate_snapshots, make_bots, truncate_state


def _record_of(state, events, seed):
    seats = [
        SeatRecord(seat=p, suspect=state.suspects_in_play[p], label="floor", kind="floor")
        for p in range(state.n_players)
    ]
    record = GameRecord.from_game("replay", 0, seed, state, events, seats)
    # Through JSON, as a stored record would come back.
    return GameRecord.from_dict(json.loads(json.dumps(record.to_dict())))


def _floor_game(seed, n_players, max_turns=120):
    bots, observer = make_bots("floor", n_players)
    state, events = engine.run_game(n_players, bots, seed=seed, max_turns=max_turns, observer=observer)
    return state, _record_of(state, events, seed)


def _random_game(seed, n_players, max_turns=80):
    bots = {p: RandomBot() for p in range(n_players)}
    state, events = engine.run_game(n_players, bots, seed=seed, max_turns=max_turns)
    return state, _record_of(state, events, seed)


def _assert_same_state(rebuilt, state):
    assert rebuilt.suspects_in_play == state.suspects_in_play
    assert rebuilt.hands == state.hands
    assert rebuilt.envelope == state.envelope
    assert rebuilt.positions == state.positions
    assert rebuilt.active == state.active
    assert rebuilt.turn == state.turn
    assert rebuilt.suggestion_log == state.suggestion_log
    assert rebuilt.accusation_log == state.accusation_log


def test_state_from_record_reproduces_a_floor_game_field_for_field():
    for seed, n_players in ((3, 3), (5, 4), (8, 6)):
        state, record = _floor_game(seed, n_players)
        assert state.suggestion_log, "the check needs a game with suggestions"
        _assert_same_state(state_from_record(record), state)


def test_state_from_record_folds_eliminations_and_token_drags():
    # Random bots accuse wrongly and get eliminated, and their
    # suggestions drag other tokens into rooms without a move event.
    saw_elimination = saw_drag = False
    for seed in range(1, 12):
        state, record = _random_game(seed, 4)
        _assert_same_state(state_from_record(record), state)
        saw_elimination |= not all(state.active)
        saw_drag |= any(
            s.suspect in state.suspects_in_play and state.suspects_in_play.index(s.suspect) != s.suggester
            for s in state.suggestion_log
        )
    assert saw_elimination and saw_drag


def test_seat_view_matches_the_live_observation_at_every_checkpoint():
    state, record = _floor_game(5, 4)
    for k in range(len(state.suggestion_log) + 1):
        cut = truncate_state(state, k)
        for viewer in range(state.n_players):
            assert seat_view(record, viewer, k) == clude_constraints.observe(cut, viewer)
    for viewer in range(state.n_players):
        assert seat_view(record, viewer) == clude_constraints.observe(state, viewer)
    with pytest.raises(ValueError):
        state_from_record(record, k=len(state.suggestion_log) + 1)
    with pytest.raises(ValueError):
        state_from_record(record, k=-1)


def test_snapshots_from_record_match_generate_snapshots_on_the_same_game():
    checkpoints = (0.5, 1.0)
    live = list(generate_snapshots(1, seed=11, checkpoints=checkpoints, player_counts=(4,)))
    bots, observer = make_bots("floor", 4)
    state, events = engine.run_game(4, bots, seed=11, max_turns=DEFAULT_MAX_TURNS, observer=observer)
    record = _record_of(state, events, 11)
    replayed = list(snapshots_from_record(record, checkpoints))
    assert len(replayed) == len(live) == 2 * 4
    for mine, theirs in zip(replayed, live):
        assert (mine.viewer, mine.checkpoint, mine.envelope) == (theirs.viewer, theirs.checkpoint, theirs.envelope)
        assert mine.obs == theirs.obs
        assert mine.obs.mask == theirs.obs.mask


def test_a_game_without_suggestions_yields_no_snapshots():
    state, record = _random_game(2, 3, max_turns=1)
    assert not state.suggestion_log or True  # one turn may or may not suggest
    record.events = [e for e in record.events if not hasattr(e, "suggestion")]
    assert list(snapshots_from_record(record)) == []
