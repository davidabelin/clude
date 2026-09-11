import random

import pytest

from clude_core import board, engine
from clude_core.bots import RandomBot
from clude_core.domain import ALL_CARDS
from clude_core.events import GameOverEvent


def test_setup_deals_every_card_exactly_once():
    rng = random.Random(0)
    state = engine.setup(4, rng)
    dealt = set(state.envelope)
    for hand in state.hands.values():
        assert not (hand & dealt), "a card was dealt to more than one holder"
        dealt |= hand
    assert dealt == set(ALL_CARDS)


def test_setup_rejects_out_of_range_player_counts():
    rng = random.Random(0)
    with pytest.raises(ValueError):
        engine.setup(2, rng)
    with pytest.raises(ValueError):
        engine.setup(7, rng)


def test_setup_hand_sizes_are_balanced():
    rng = random.Random(0)
    state = engine.setup(4, rng)
    sizes = sorted(state.hand_sizes().values())
    assert sizes[-1] - sizes[0] <= 1  # round-robin deal, at most 1 apart


def test_legal_moves_in_room_include_stay():
    rng = random.Random(0)
    state = engine.setup(3, rng)
    state.positions[0] = "Kitchen"
    choices = engine.legal_moves(state, 0, roll=3)
    assert engine.MoveChoice("stay") in choices


def test_legal_moves_in_room_with_passage_offer_it():
    rng = random.Random(0)
    state = engine.setup(3, rng)
    state.positions[0] = "Kitchen"
    choices = engine.legal_moves(state, 0, roll=1)
    assert engine.MoveChoice("secret_passage", "Study") in choices


def test_resolve_suggestion_moves_suspect_token_into_room():
    rng = random.Random(0)
    state = engine.setup(3, rng)  # suspects: Scarlett, Mustard, White
    state.positions[0] = "Library"
    bots = {p: RandomBot() for p in range(3)}
    engine.resolve_suggestion(state, suggester=0, suspect="White", weapon="Rope", bots=bots, rng=rng)
    white_player = state.suspects_in_play.index("White")
    assert state.positions[white_player] == "Library"


def test_resolve_suggestion_finds_refuter_holding_a_named_card():
    rng = random.Random(0)
    state = engine.setup(3, rng)
    state.positions[0] = "Library"
    # Force player 1 to hold the room card so they must refute.
    state.hands[1] = frozenset({"Library"})
    state.hands[2] = frozenset(state.hands[2] - {"Library"})
    bots = {p: RandomBot() for p in range(3)}
    suggestion = engine.resolve_suggestion(
        state, suggester=0, suspect=state.suspects_in_play[0], weapon="Rope", bots=bots, rng=rng
    )
    assert suggestion.refuter == 1
    assert suggestion.card_shown == "Library"


def test_resolve_accusation_correct_does_not_eliminate():
    rng = random.Random(0)
    state = engine.setup(3, rng)
    suspect, weapon, room = state.envelope
    accusation = engine.resolve_accusation(state, 0, suspect, weapon, room)
    assert accusation.correct
    assert state.active[0] is True


def test_resolve_accusation_wrong_eliminates_accuser():
    rng = random.Random(0)
    state = engine.setup(3, rng)
    wrong = tuple(c for c in ALL_CARDS if c not in state.envelope)[:3]
    accusation = engine.resolve_accusation(state, 0, *wrong)
    assert not accusation.correct
    assert state.active[0] is False


def test_run_game_terminates_and_is_deterministic_given_a_seed():
    bots = {p: RandomBot() for p in range(4)}
    state_a, events_a = engine.run_game(4, bots, seed=42, max_turns=200)
    bots = {p: RandomBot() for p in range(4)}
    state_b, events_b = engine.run_game(4, bots, seed=42, max_turns=200)

    assert isinstance(events_a[-1], GameOverEvent)
    assert state_a.envelope == state_b.envelope
    assert len(events_a) == len(events_b)


def test_run_game_ends_with_at_most_one_correct_accusation():
    bots = {p: RandomBot() for p in range(5)}
    state, events = engine.run_game(5, bots, seed=7, max_turns=300)
    correct = [e for e in events if hasattr(e, "accusation") and e.accusation.correct]
    assert len(correct) <= 1
    if correct:
        assert isinstance(events[-1], GameOverEvent)
        assert events[-1].winner == correct[0].accusation.accuser
