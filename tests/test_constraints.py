import random

import pytest

from clude_constraints import ENVELOPE, ConstraintError, propagate
from clude_core import engine
from clude_core.bots import RandomBot
from clude_core.domain import ALL_CARDS, Suggestion
from clude_core.state import ClueObservation


def make_obs(n_players, my_index, own_hand, hand_sizes, suggestion_log):
    return ClueObservation(
        n_players=n_players,
        my_index=my_index,
        own_hand=frozenset(own_hand),
        active_players=tuple(True for _ in range(n_players)),
        hand_sizes=hand_sizes,
        suggestion_log=tuple(suggestion_log),
        accusation_log=(),
        turn=len(suggestion_log),
    )


def test_category_rule_infers_last_suspect_is_the_envelope():
    obs = make_obs(
        n_players=3,
        my_index=0,
        own_hand={"Scarlett", "Mustard", "White", "Green", "Peacock"},
        hand_sizes={0: 5, 1: 8, 2: 8},
        suggestion_log=[],
    )
    result = propagate(obs)
    assert result.holder_of("Plum") == ENVELOPE


def test_or_constraint_collapses_once_alternatives_are_ruled_out():
    # Viewer holds two of the three named cards, so the refuter's OR
    # constraint over the third card should collapse to a hard fact.
    suggestion = Suggestion(
        suggester=1, suspect="Mustard", weapon="Rope", room="Kitchen",
        refuter=2, shown_to=1, card_shown=None,
    )
    obs = make_obs(
        n_players=3,
        my_index=0,
        own_hand={"Mustard", "Rope"},
        hand_sizes={0: 2, 1: 9, 2: 9},
        suggestion_log=[suggestion],
    )
    result = propagate(obs)
    assert result.holder_of("Kitchen") == 2


def test_contradiction_raises():
    suggestion = Suggestion(
        suggester=1, suspect="Mustard", weapon="Rope", room="Kitchen",
        refuter=2, shown_to=1, card_shown="Rope",  # contradicts viewer's own hand below
    )
    obs = make_obs(
        n_players=3,
        my_index=0,
        own_hand={"Rope"},
        hand_sizes={0: 1, 1: 1, 2: 1},
        suggestion_log=[suggestion],
    )
    with pytest.raises(ConstraintError):
        propagate(obs)


def test_hand_size_saturation_eliminates_a_full_hand_from_other_cards():
    suggestion = Suggestion(
        suggester=0, suspect="Scarlett", weapon="Knife", room="Study",
        refuter=1, shown_to=0, card_shown="Knife",
    )
    obs = make_obs(
        n_players=3,
        my_index=0,
        own_hand={"Lounge"},
        hand_sizes={0: 1, 1: 1, 2: 18},
        suggestion_log=[suggestion],
    )
    result = propagate(obs)
    assert result.holder_of("Knife") == 1
    # Player 1's hand is now full (1 card); they can't hold anything else.
    assert not result.is_possible("Conservatory", 1)
    # Player 0 (viewer) is likewise saturated by their own single-card hand.
    assert not result.is_possible("Conservatory", 0)


def _true_holder(state, card):
    if card in state.envelope:
        return ENVELOPE
    for p, hand in state.hands.items():
        if card in hand:
            return p
    raise AssertionError(f"{card} not found in any hand or the envelope")


@pytest.mark.parametrize("seed", range(15))
def test_propagator_is_sound_across_real_games(seed):
    """The floor must never rule out the truth, and never raise on real
    (non-contradictory) game evidence."""
    n_players = 3 + seed % 4  # 3..6
    bots = {p: RandomBot() for p in range(n_players)}
    state, _events = engine.run_game(n_players, bots, seed=seed, max_turns=150)

    for viewer in range(n_players):
        obs = ClueObservation.for_player(state, viewer)
        result = propagate(obs)
        for card in ALL_CARDS:
            assert result.is_possible(card, _true_holder(state, card)), (
                f"seed={seed} viewer={viewer} card={card}: floor eliminated the truth"
            )


def test_propagator_can_reach_full_certainty_given_enough_play():
    """At least one seed, for at least one player, should fully converge --
    the Phase 2 convergence property from docs/phase-plan.md."""
    solved_any = False
    for seed in range(25):
        n_players = 4
        bots = {p: RandomBot() for p in range(n_players)}
        state, _events = engine.run_game(n_players, bots, seed=seed, max_turns=400)
        for viewer in range(n_players):
            obs = ClueObservation.for_player(state, viewer)
            result = propagate(obs)
            if result.solution() == state.envelope:
                solved_any = True
                break
        if solved_any:
            break
    assert solved_any, "no viewer in any sampled game reached full certainty"
