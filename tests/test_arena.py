"""Phase 5d: the arena and dial sweeps, on tiny configurations."""
from __future__ import annotations

import json

import pytest

from clude_agents.personality import Profile
from clude_training.arena import (
    ArenaResult,
    PlayerStats,
    SeatOutcome,
    binomial_std,
    lineup_for_game,
    parse_roster,
    run_arena,
)
from clude_training.sweep import SweepResult, SweepRow, pooled_stats, sweep_dial


def test_lineup_rotates_truncates_and_fills():
    roster = ("A", "B", "C")
    assert lineup_for_game(roster, 0, 3) == ["A", "B", "C"]
    assert lineup_for_game(roster, 1, 3) == ["B", "C", "A"]
    assert lineup_for_game(roster, 4, 2) == ["B", "C"]
    assert lineup_for_game(roster, 2, 5) == ["C", "A", "B", "floor", "floor"]


def test_seat_lineup_locks_characters_to_their_own_tokens_in_board_order():
    from clude_training.arena import seat_lineup

    assert seat_lineup(["Plum", "Mustard", "Green"]) == (["Mustard", "Green", "Plum"], ["Mustard", "Green", "Plum"])
    assert seat_lineup(["Plum", "Scarlett", "floor"]) == (["Scarlett", "floor", "Plum"], ["Scarlett", "Mustard", "Plum"])
    assert seat_lineup(["floor", "floor", "floor"]) == (["floor"] * 3, ["Scarlett", "Mustard", "White"])
    labels, suspects = seat_lineup(["White", "floor", "random", "Peacock"])
    assert labels == ["floor", "random", "White", "Peacock"]
    assert suspects == ["Scarlett", "Mustard", "White", "Peacock"]


def test_parse_roster_validates():
    assert parse_roster(["Scarlett", " floor ", "Plum"]) == ("Scarlett", "floor", "Plum")
    with pytest.raises(ValueError):
        parse_roster(["Scarlett", "Scarlett"])
    with pytest.raises(ValueError):
        parse_roster(["Nobody"])
    with pytest.raises(ValueError):
        parse_roster([])


def test_binomial_std_and_player_stats_arithmetic():
    assert binomial_std(0, 0) != binomial_std(0, 0)  # NaN
    assert binomial_std(5, 10) == pytest.approx(0.5 / 10 ** 0.5)
    stats = PlayerStats("x", "character")
    assert stats.reshow_rate != stats.reshow_rate  # NaN before any choice
    stats.record(
        SeatOutcome("x", "character", 0, "Scarlett", True, True, False, 12, 2, 1, 5, 2, 1), 4, 0.02
    )
    stats.record(SeatOutcome("x", "character", 1, "Mustard", False, True, True, 30, 1, 0, 3))
    stats.record(SeatOutcome("x", "character", 2, "White", False, False, False, None, 0, 0, 4))
    assert stats.games == 3 and stats.wins == 1
    assert stats.win_rate == pytest.approx(1 / 3)
    assert stats.wrong_accusation_rate == pytest.approx(1 / 3)
    assert stats.never_accused_rate == pytest.approx(1 / 3)
    assert stats.mean_first_accusation_turn == pytest.approx(21.0)
    assert stats.mean_cards_leaked == pytest.approx(1.0)
    assert stats.ms_per_call == pytest.approx(5.0)
    assert stats.reshow_rate == pytest.approx(0.5)
    json.dumps(stats.to_dict())
    other = PlayerStats("y", "character")
    other.record(SeatOutcome("y", "character", 0, "Plum", True, True, False, 8, 3, 2, 6))
    stats.merge(other)
    assert stats.games == 4 and stats.wins == 2


def test_arena_with_logbooks_learns_between_games_and_stays_paired_read_only(tmp_path):
    from clude_storage import LocalStore, Logbook
    from clude_training import memory

    store = LocalStore(tmp_path)
    settings = dict(
        n_games=2, seed=5, roster=("Mustard", "White", "Green"), player_counts=(3,), max_turns=50,
    )
    plain = run_arena(**settings)
    assert plain.memory == {}

    # Empty logbooks change nothing, read-only or not.
    empty = run_arena(**settings, logbook_store=store, logbooks_readonly=True)
    assert [g.to_dict() for g in empty.games] == [g.to_dict() for g in plain.games]
    assert empty.memory == {
        "store": str(tmp_path), "readonly": True, "characters": ["Green", "Mustard", "White"], "loaded": [],
    }
    assert Logbook(store, "Mustard").method() is None

    learning = run_arena(**settings, logbook_store=store)
    assert learning.memory["readonly"] is False
    for label in ("Mustard", "White", "Green"):
        assert memory.n_games(Logbook(store, label).method()) == 2, label
    assert Logbook(store, "floor").method() is None
    # The first game is played on empty memory, so it is the plain one.
    assert learning.games[0].to_dict() == plain.games[0].to_dict()

    # A fixed memory, read-only, reproduces itself and writes nothing.
    again = run_arena(**settings, logbook_store=store, logbooks_readonly=True)
    once_more = run_arena(**settings, logbook_store=store, logbooks_readonly=True)
    assert [g.to_dict() for g in again.games] == [g.to_dict() for g in once_more.games]
    assert sorted(again.memory["loaded"]) == ["Green", "Mustard", "White"]
    assert memory.n_games(Logbook(store, "Mustard").method()) == 2
    assert json.loads(json.dumps(again.to_dict()))["memory"]["readonly"] is True

    # A sweep reads the same logbooks at every value and never writes.
    sweep = sweep_dial(
        "curiosity", [0.2, 0.8], n_games=1, seed=5, roster=("Mustard", "floor"), characters=["Mustard"],
        player_counts=(3,), max_turns=40, logbook_store=store,
    )
    assert all(r.memory["readonly"] for r in sweep.results)
    assert memory.n_games(Logbook(store, "Mustard").method()) == 2

    # A logbook for one character leaves the others exactly as they play without memory.
    only = run_arena(**{**settings, "n_games": 1}, logbook_store=store, run_id="only", logbook_characters=["Mustard"])
    assert only.memory["characters"] == ["Mustard"] and only.memory["loaded"] == ["Mustard"]
    assert memory.n_games(Logbook(store, "Mustard").method()) == 3
    assert memory.n_games(Logbook(store, "White").method()) == 2
    with pytest.raises(ValueError):
        run_arena(**settings, logbook_store=store, logbook_characters=["Plum"])


def test_seat_outcome_counts_reshows_only_where_there_was_a_choice():
    from clude_core.domain import Suggestion
    from clude_core.events import GameOverEvent
    from clude_training.arena import seat_outcome

    state = __import__("clude_core").engine.setup(3, __import__("random").Random(0))
    hand = set(state.hands[1])
    two = sorted(hand)[:2]  # two cards seat 1 holds
    other = next(c for c in state.hands[0])
    state.suggestion_log.extend([
        # one candidate: forced, not a choice
        Suggestion(0, two[0], other, "Kitchen", refuter=1, shown_to=0, card_shown=two[0]),
        # two candidates, re-showed the already-exposed card
        Suggestion(2, two[0], two[1], "Kitchen", refuter=1, shown_to=2, card_shown=two[0]),
        # two candidates, showed a fresh one
        Suggestion(0, two[0], two[1], "Kitchen", refuter=1, shown_to=0, card_shown=two[1]),
    ])
    events = [GameOverEvent(3, None, state.envelope)]
    outcome = seat_outcome(state, events, 1, "x", "character")
    assert (outcome.reshow_choices, outcome.reshows) == (2, 1)
    assert outcome.cards_leaked == 2


def test_run_arena_small_table_reports_every_label():
    result = run_arena(n_games=3, seed=21, roster=("Scarlett", "White"), player_counts=(3,), max_turns=60)
    assert isinstance(result, ArenaResult)
    assert set(result.per_player) == {"Scarlett", "White", "floor"}
    for label, stats in result.per_player.items():
        assert stats.games == 3
        assert 0 <= stats.wins <= stats.games
        assert stats.games_with_wrong_accusation <= stats.games
    assert result.per_player["Scarlett"].n_calls > 0
    assert result.per_player["floor"].n_calls == 0
    assert len(result.games) == 3
    # Seats are fixed by token: the rotation changes only who sits out, never where anyone sits.
    assert [tuple(g.labels) for g in result.games] == [("Scarlett", "floor", "White")] * 3
    data = result.to_dict()
    json.dumps(data)
    assert data["profiles"]["Scarlett"]["accuse_threshold"] == pytest.approx(0.15)
    table = result.summary_table()
    assert "Scarlett" in table and "floor" in table and "win%" in table


def test_run_arena_is_paired_across_profiles():
    """Same seed, different dials: identical deals."""
    a = run_arena(n_games=2, seed=33, roster=("Scarlett", "floor"), player_counts=(3,), max_turns=40)
    b = run_arena(
        n_games=2, seed=33, roster=("Scarlett", "floor"), player_counts=(3,), max_turns=40,
        profiles={"Scarlett": Profile(accuse_threshold=1.0)},
    )
    assert [g.seed for g in a.games] == [g.seed for g in b.games]
    assert b.profiles["Scarlett"]["accuse_threshold"] == 1.0


def test_sweep_of_accuse_threshold_moves_wrong_accusations():
    sweep = sweep_dial(
        "accuse_threshold", [0.0, 1.0], n_games=2, seed=41, roster=("Scarlett", "floor"),
        player_counts=(3,), max_turns=40,
    )
    assert sweep.characters == ("Scarlett",)
    assert [row.value for row in sweep.rows] == [0.0, 1.0]
    reckless, strict = sweep.rows
    assert reckless.stats.games_with_accusation == 2  # accuses on turn 1 at threshold 0
    assert strict.stats.wrong_accusation_rate == 0.0  # only ever accuses on proof
    assert sweep.monotone("wrong_accusation_rate") in ("decreasing", "flat")
    assert sweep.monotone("mean_first_accusation_turn") in ("increasing", "flat", None)
    json.dumps(sweep.to_dict())
    assert "monotone:" in sweep.summary_table()
    with pytest.raises(ValueError):
        sweep_dial("charm", [0.5], n_games=1, roster=("Scarlett",))
    with pytest.raises(ValueError):
        sweep_dial("secrecy", [0.5], n_games=1, roster=("floor",))
    with pytest.raises(ValueError):
        sweep_dial("secrecy", [0.5], n_games=1, roster=("Scarlett",), characters=["Plum"])


def _row(value, wrong_rate):
    stats = PlayerStats("x", "character")
    stats.games = 10
    stats.games_with_wrong_accusation = int(round(wrong_rate * 10))
    return SweepRow(value=value, stats=stats, mean_turns=50.0)


def test_sweep_monotone_verdicts():
    def sweep(rates):
        return SweepResult("accuse_threshold", tuple(range(len(rates))), ("x",), ("x",),
                           rows=[_row(i, r) for i, r in enumerate(rates)])

    assert sweep([0.9, 0.5, 0.1]).monotone("wrong_accusation_rate") == "decreasing"
    assert sweep([0.1, 0.1, 0.5]).monotone("wrong_accusation_rate") == "increasing"
    assert sweep([0.3, 0.3, 0.3]).monotone("wrong_accusation_rate") == "flat"
    assert sweep([0.1, 0.5, 0.2]).monotone("wrong_accusation_rate") is None
    assert sweep([0.5]).monotone("wrong_accusation_rate") is None
    assert sweep([0.5, 0.1]).monotone("mean_first_accusation_turn") is None  # NaN: nobody accused
    pooled = pooled_stats({"a": _row(0, 0.5).stats, "b": _row(0, 0.1).stats}, ("a", "b"))
    assert pooled.games == 20 and pooled.games_with_wrong_accusation == 6
