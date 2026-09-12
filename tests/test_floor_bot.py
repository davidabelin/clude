"""Phase 5b: `FloorBot`, the standard self-play opponent."""
from __future__ import annotations

import random
from dataclasses import replace

import pytest

import clude_constraints
from clude_constraints import ENVELOPE, FloorBot
from clude_core import engine
from clude_core.domain import ALL_CARDS, SUSPECTS, WEAPONS
from clude_core.events import GameOverEvent
from clude_training.self_play import generate_snapshots

from tests.test_agents import make_obs


def test_floor_bot_needs_a_masked_observation():
    obs = make_obs(3, 0, set(), {0: 6, 1: 6, 2: 6}, [])
    unmasked = replace(obs, mask=None)
    bot = FloorBot()
    with pytest.raises(AssertionError):
        bot.choose_suggestion(unmasked, "Kitchen", random.Random(0))


def test_floor_bot_never_names_own_or_located_cards_when_others_remain():
    own = {"Scarlett", "Knife"}
    obs = make_obs(3, 0, own, {0: 2, 1: 8, 2: 8}, [])
    bot = FloorBot()
    rng = random.Random(1)
    for _ in range(200):
        suspect, weapon = bot.choose_suggestion(obs, "Kitchen", rng)
        assert suspect not in own and weapon not in own
        assert obs.mask.holder_of(suspect) is None
        assert obs.mask.holder_of(weapon) is None


def test_floor_bot_accuses_exactly_when_the_floor_proves_the_envelope():
    open_obs = make_obs(3, 0, set(), {0: 6, 1: 6, 2: 6}, [])
    assert FloorBot().choose_accusation(open_obs, random.Random(0)) is None

    # One card of each category is left for the envelope: hand sizes of
    # 0 for the others force the floor to prove all three.
    hand = set(ALL_CARDS) - {"Plum", "Wrench", "Dining"}
    proven = make_obs(3, 0, hand, {0: 18, 1: 0, 2: 0}, [])
    assert proven.mask.solution() == ("Plum", "Wrench", "Dining")
    assert FloorBot().choose_accusation(proven, random.Random(0)) == ("Plum", "Wrench", "Dining")


def test_floor_bot_games_end_by_deduction():
    winners = 0
    for seed in range(6):
        n_players = 3 + seed % 4
        bots = {p: FloorBot() for p in range(n_players)}
        state, events = engine.run_game(
            n_players, bots, seed=seed, max_turns=150, observer=clude_constraints.observe
        )
        final = events[-1]
        assert isinstance(final, GameOverEvent)
        # A FloorBot is never wrong: it only accuses on proof.
        assert all(a.correct for a in state.accusation_log)
        if final.winner is not None:
            winners += 1
            assert state.accusation_log[-1].cards() == state.envelope
    assert winners >= 4, "FloorBot games should usually end with a correct accusation"


def test_floor_bot_private_rng_leaves_the_dice_alone():
    """Two tables of FloorBots with private RNGs, seeded differently,
    must play the same deal with the same rolls: the engine RNG is only
    ever drawn for setup and dice."""
    def play(private_seed):
        bots = {p: FloorBot(rng=random.Random(private_seed + p)) for p in range(3)}
        state, events = engine.run_game(
            3, bots, seed=9, max_turns=40, observer=clude_constraints.observe
        )
        return state, events

    state_a, _ = play(100)
    state_b, _ = play(200)
    assert state_a.envelope == state_b.envelope
    assert state_a.hands == state_b.hands


def test_floor_snapshots_reach_solved_states():
    solved = 0
    total = 0
    for snap in generate_snapshots(8, seed=30, checkpoints=(1.0,), bot="floor"):
        total += 1
        solved += int(snap.obs.mask.solution() is not None)
    assert total > 0
    assert solved > 0, "no FloorBot game reached a proven envelope for any viewer"


def test_generate_snapshots_rejects_an_unknown_bot():
    with pytest.raises(ValueError):
        list(generate_snapshots(1, seed=1, bot="clever"))


def test_floor_bot_fallback_names_any_card_when_a_category_is_exhausted():
    # Every suspect is either held by the viewer or proven; every weapon
    # too -- the bot must still return something rather than crash.
    hand = set(SUSPECTS[:5]) | set(WEAPONS[:5]) | {"Kitchen"}
    obs = make_obs(3, 0, hand, {0: 11, 1: 5, 2: 5}, [])
    assert obs.mask.holder_of(SUSPECTS[5]) == ENVELOPE
    suspect, weapon = FloorBot().choose_suggestion(obs, "Kitchen", random.Random(0))
    assert suspect in SUSPECTS and weapon in WEAPONS
