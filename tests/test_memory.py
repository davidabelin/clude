"""Phase 7b: method memory -- the three per-method hooks and
`clude_training.memory` over stored records."""
from __future__ import annotations

import json

import pytest

from clude_agents import build_character
from clude_agents.bandit import BanditAgent, RevealedOutcome
from clude_agents.base import ClueBelief
from clude_agents.decision_tree import DecisionTreeAgent, _generate_training_rows, rows_from_view
from clude_agents.markov import MarkovAgent, PRIOR_MASS, prior_cells, transition_counts
from clude_core import engine
from clude_core.domain import ALL_CARDS, Suggestion
from clude_storage import GameRecord, LocalStore, Logbook, SeatRecord
from clude_training import memory
from clude_training.replay import snapshots_from_record
from clude_training.self_play import generate_snapshots, make_bots
from tests.test_agents import make_obs


def _record(seed=7, labels=("Mustard", "White", "Green"), run_id="r", index=0):
    n = len(labels)
    bots, observer = make_bots("floor", n)
    state, events = engine.run_game(n, bots, seed=seed, max_turns=120, observer=observer)
    seats = [
        SeatRecord(seat=p, suspect=state.suspects_in_play[p], label=labels[p], kind="character")
        for p in range(n)
    ]
    record = GameRecord.from_game(run_id, index, seed, state, events, seats)
    return GameRecord.from_dict(json.loads(json.dumps(record.to_dict())))


# ---------------------------------------------------------------------
# Mustard
# ---------------------------------------------------------------------


def test_rows_from_view_is_the_training_row_builder():
    snaps = list(generate_snapshots(1, seed=3, checkpoints=(0.5, 1.0), player_counts=(3,)))
    rows = [row for snap in snaps for row in rows_from_view(snap.obs, snap.envelope)]
    assert rows == _generate_training_rows(1, 3, (0.5, 1.0), "floor")
    assert rows and all(len(x) == 8 and y in (0, 1) for x, y in rows)


def test_mustard_trains_on_extra_rows_and_forgets_them_on_demand():
    default = DecisionTreeAgent()
    base_tree = default.tree
    snaps = list(generate_snapshots(2, seed=99, checkpoints=(1.0,), player_counts=(4,)))
    rows = [row for snap in snaps for row in rows_from_view(snap.obs, snap.envelope)]
    remembering = DecisionTreeAgent(extra_rows=rows)
    assert remembering.n_extra_rows == len(rows)
    assert remembering.tree is not base_tree
    assert remembering.tree.n_samples == base_tree.n_samples + len(rows)
    remembering.set_extra_rows([])
    assert remembering.n_extra_rows == 0
    assert remembering.tree is base_tree  # back to the cached default
    assert DecisionTreeAgent().tree is base_tree  # the default never moved


# ---------------------------------------------------------------------
# White
# ---------------------------------------------------------------------


def test_transition_counts_and_prior_cells():
    assert transition_counts([]) == {"00": 0, "01": 0, "10": 0, "11": 0}
    assert transition_counts([0, 1, 1, 0]) == {"00": 0, "01": 1, "10": 1, "11": 1}
    plain = prior_cells(None)
    assert plain == {(0, 0): 1.0, (0, 1): 1.0, (1, 0): 1.0, (1, 1): 1.0}
    assert sum(plain.values()) == pytest.approx(PRIOR_MASS)
    repeater = prior_cells({"00": 0, "01": 0, "10": 0, "11": 36})
    assert sum(repeater.values()) == pytest.approx(PRIOR_MASS)
    assert repeater[(1, 1)] > 3.0 and repeater[(0, 0)] < 0.2


def test_white_uses_a_remembered_prior_only_for_a_seat_the_table_names():
    log = [
        Suggestion(1, "Mustard", "Rope", "Kitchen", refuter=2, shown_to=1, card_shown=None),
        Suggestion(1, "Mustard", "Knife", "Kitchen", refuter=2, shown_to=1, card_shown=None),
        Suggestion(2, "Green", "Rope", "Study", refuter=1, shown_to=2, card_shown=None),
        Suggestion(2, "Green", "Rope", "Study", refuter=1, shown_to=2, card_shown=None),
    ]
    obs = make_obs(3, 0, set(), {0: 6, 1: 6, 2: 6}, log, turn=4)
    plain = MarkovAgent()
    plain.reset(0)
    baseline = plain.select_action(obs)

    priors = {"Mustard": {"00": 0, "01": 0, "10": 0, "11": 40}}
    remembering = MarkovAgent(priors=priors)
    remembering.reset(0)
    # No table yet: the prior has nobody to attach to.
    assert remembering.select_action(obs) == baseline
    remembering.set_table(["White", "Mustard", "Green"])
    informed = remembering.select_action(obs)
    assert informed.extra["repeat_probability"][1] > baseline.extra["repeat_probability"][1]
    assert informed.extra["repeat_probability"][2] == baseline.extra["repeat_probability"][2]
    assert informed.probabilities != baseline.probabilities
    # A table that seats the remembered label elsewhere moves the prior with it.
    remembering.set_table(["White", "Green", "Mustard"])
    moved = remembering.select_action(obs)
    assert moved.extra["repeat_probability"][1] == baseline.extra["repeat_probability"][1]
    assert moved.extra["repeat_probability"][2] > baseline.extra["repeat_probability"][2]
    remembering.set_priors(None)
    assert remembering.select_action(obs) == baseline


# ---------------------------------------------------------------------
# Green
# ---------------------------------------------------------------------


def _teach_green(agent, rounds=5):
    envelope = ("Scarlett", "Candlestick", "Kitchen")
    for _ in range(rounds):
        agent._last_predictions = {
            name: ClueBelief(probabilities={c: (1.0 if c in envelope else 0.0) for c in ALL_CARDS})
            if name == "Plum"
            else ClueBelief(probabilities={c: 0.0 for c in ALL_CARDS})
            for name in agent.arms
        }
        agent.observe(RevealedOutcome(envelope=envelope))


def test_green_posteriors_survive_a_reset_through_state_dict():
    agent = BanditAgent()
    agent.reset(0)
    _teach_green(agent)
    state = json.loads(json.dumps(agent.state_dict()))
    learned = {name: (c.alpha, c.beta) for name, c in agent.candidates.items()}
    assert learned["Plum"] != (1.0, 1.0)
    agent.reset(0)
    assert all((c.alpha, c.beta) == (1.0, 1.0) for c in agent.candidates.values())
    assert agent.load_state(state) == 5
    assert {name: (c.alpha, c.beta) for name, c in agent.candidates.items()} == learned
    assert agent.load_state({"arms": {"Nobody": [2, 2], "Plum": [0, 1], "White": "bad"}}) == 0
    assert agent.load_state({}) == 0


# ---------------------------------------------------------------------
# The memory documents
# ---------------------------------------------------------------------


def test_contributions_from_a_record():
    record = _record()
    rows = memory.mustard_rows(record)
    expected = sum(
        len(rows_from_view(snap.obs, snap.envelope))
        for snap in snapshots_from_record(record, (0.5, 1.0))
    )
    assert len(rows) == expected > 0
    assert all(len(row) == 9 and row[-1] in (0, 1) for row in rows)
    counts = memory.white_counts(record)
    assert set(counts) <= {"Mustard", "White", "Green"}
    assert all(set(c) == {"00", "01", "10", "11"} for c in counts.values())
    assert memory.game_id_of(record) == "r/00000"
    assert memory.kind_for("Mustard") == "rows" and memory.kind_for("Plum") is None
    with pytest.raises(ValueError):
        memory.empty_memory("dreams")


def test_update_is_idempotent_and_rebuild_agrees(tmp_path):
    store = LocalStore(tmp_path)
    first, second = _record(seed=7, index=0), _record(seed=8, index=1)
    for record in (first, second):
        store.put_game("r", record.game_index, record.to_dict())
    mustard = build_character("Mustard")
    white = build_character("White")
    plum = build_character("Plum")

    logbook = Logbook(store, "Mustard")
    assert memory.load_into(mustard, logbook) is False  # nothing stored yet
    assert memory.update(logbook, first, mustard) is True
    assert memory.update(logbook, first, mustard) is False  # already absorbed
    assert memory.update(logbook, second, mustard) is True
    incremental = logbook.method()
    assert memory.n_games(incremental) == 2
    assert memory.rebuild(logbook, store, "rows") == (2, 0)
    assert logbook.method() == incremental
    rows = memory.extra_rows(incremental)
    assert rows == memory.extra_rows(logbook.method())
    assert memory.load_into(mustard, logbook) is True
    assert mustard.agent.n_extra_rows == len(rows) > 0
    assert "rows from 2 stored games" in memory.describe_memory(incremental)

    white_book = Logbook(store, "White")
    assert memory.update(white_book, first, white) is True
    assert memory.update(white_book, second, white) is True
    summed = memory.priors(white_book.method())
    assert summed and all(sum(c.values()) > 0 for c in summed.values())
    assert memory.load_into(white, white_book) is True
    assert white.agent.priors == summed
    assert memory.rebuild(white_book, store, "counts") == (2, 0)
    assert memory.priors(white_book.method()) == summed
    assert "White's chains: 2 stored games" in memory.describe_memory(white_book.method())

    assert memory.update(Logbook(store, "Plum"), first, plum) is False
    assert memory.load_into(plum, Logbook(store, "Plum")) is False
    assert memory.describe_memory(None) == "no method memory"
    # A document of the wrong kind is ignored, not misread.
    Logbook(store, "Mustard").save_method(white_book.method())
    assert memory.load_into(mustard, Logbook(store, "Mustard")) is False


def test_rebuild_skips_ring_era_records_by_default(tmp_path):
    store = LocalStore(tmp_path)
    grid, ring = _record(seed=7, run_id="grid"), _record(seed=8, run_id="ring")
    store.put_game("grid", grid.game_index, grid.to_dict())
    store.put_game("ring", ring.game_index, {**ring.to_dict(), "version": 2})
    logbook = Logbook(store, "Mustard")
    assert memory.rebuild(logbook, store, "rows") == (1, 1)
    assert list(logbook.method()["games"]) == ["grid/00000"]
    assert memory.rebuild(logbook, store, "rows", min_version=1) == (2, 0)


def test_green_memory_is_saved_live_and_restored_after_reset(tmp_path):
    store = LocalStore(tmp_path)
    green = build_character("Green")
    green.reset(3)
    _teach_green(green.agent)
    logbook = Logbook(store, "Green")
    assert memory.update(logbook, _record(), green) is True
    assert memory.update(logbook, _record(), green) is True  # live state: every game counts
    doc = logbook.method()
    assert doc["kind"] == "state" and doc["games"] == 2
    assert "Green's posteriors after 2 games" in memory.describe_memory(doc)
    learned = green.agent.state_dict()
    green.reset(3)
    assert green.agent.state_dict() != learned
    assert memory.load_into(green, logbook) is True
    assert green.agent.state_dict() == learned
    with pytest.raises(ValueError):
        memory.rebuild(logbook, store, "state")


def test_new_game_reaches_white_and_leaves_the_rest_alone():
    white = build_character("White")
    white.new_game(["Plum", "White", "floor"])
    assert white.agent.table == ["Plum", "White", "floor"]
    plum = build_character("Plum")
    plum.new_game(["Plum", "White", "floor"])  # no set_table: no error, no effect
    plum.new_game()
