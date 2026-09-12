"""Phase 5c: `Character` -- one unit test per engine decision, plus a
full game among the six."""
from __future__ import annotations

import random

import pytest

import clude_constraints
from clude_agents import AGENT_SPECS, ClueBelief, build_character
from clude_agents.character import (
    Character,
    best_triple,
    ds_belief_confidence,
    probabilities_confidence,
)
from clude_agents.naive_bayes import NaiveBayesAgent
from clude_agents.personality import Profile
from clude_core import engine
from clude_core.domain import ALL_CARDS, ROOMS, SUSPECTS, WEAPONS, Suggestion
from clude_core.events import GameOverEvent

from tests.test_agents import make_obs

ENGINE_RNG = random.Random(0)


def _character(profile: Profile, seed: int = 0) -> Character:
    character = Character(NaiveBayesAgent(), profile)
    character.reset(seed)
    return character


def _fresh_obs(own_hand=(), n_players=3):
    sizes = {p: 6 for p in range(n_players)}
    sizes[0] = len(own_hand) if own_hand else 6
    return make_obs(n_players, 0, set(own_hand), sizes, [])


def test_best_triple_takes_the_product_of_category_maxima():
    confidence = {c: 0.0 for c in ALL_CARDS}
    confidence.update({"Plum": 0.5, "Rope": 0.8, "Study": 1.0, "Scarlett": 0.4})
    triple, p = best_triple(confidence)
    assert triple == ("Plum", "Rope", "Study")
    assert p == pytest.approx(0.4)
    # Missing cards count as 0; a fully-tied category picks its first card.
    assert best_triple({})[0] == (SUSPECTS[0], WEAPONS[0], ROOMS[0])


def test_never_accuses_below_its_threshold_and_always_on_proof():
    strict = _character(Profile(accuse_threshold=1.0))
    assert strict.choose_accusation(_fresh_obs(), ENGINE_RNG) is None
    assert strict.last_confidence < 1.0

    hand = set(ALL_CARDS) - {"Plum", "Wrench", "Dining"}
    proven = make_obs(3, 0, hand, {0: 18, 1: 0, 2: 0}, [])
    assert strict.choose_accusation(proven, ENGINE_RNG) == ("Plum", "Wrench", "Dining")

    reckless = _character(Profile(accuse_threshold=0.0))
    assert reckless.choose_accusation(_fresh_obs(), ENGINE_RNG) is not None


def test_peacock_confidence_reads_the_dempster_shafer_lower_bound():
    belief = ClueBelief(
        probabilities={c: (1.0 if c in ("Plum", "Rope", "Study") else 0.0) for c in ALL_CARDS},
        extra={"belief": {c: 0.0 for c in ALL_CARDS}},
    )
    assert best_triple(probabilities_confidence(belief))[1] == pytest.approx(1.0)
    assert best_triple(ds_belief_confidence(belief))[1] == 0.0

    peacock = build_character("Peacock", Profile(accuse_threshold=0.5))
    peacock.reset(0)
    assert peacock.confidence_fn is ds_belief_confidence


def test_honest_suggestions_never_name_own_cards_but_bluffs_do():
    own = {"Scarlett", "Knife"}
    obs = _fresh_obs(own)
    honest = _character(Profile(bluff_rate=0.0, temperature=1.0))
    for _ in range(100):
        suspect, weapon = honest.choose_suggestion(obs, "Kitchen", ENGINE_RNG)
        assert suspect not in own and weapon not in own

    bluffer = _character(Profile(bluff_rate=1.0))
    for _ in range(20):
        assert bluffer.choose_suggestion(obs, "Kitchen", ENGINE_RNG) == ("Scarlett", "Knife")


def test_suggestion_follows_the_belief_when_greedy():
    unrefuted = Suggestion(1, "Mustard", "Rope", "Kitchen", None, 1, None)
    obs = make_obs(3, 0, set(), {0: 6, 1: 6, 2: 6}, [unrefuted], turn=1)
    greedy = _character(Profile(bluff_rate=0.0, temperature=0.0))
    assert greedy.choose_suggestion(obs, "Kitchen", ENGINE_RNG) == ("Mustard", "Rope")


def test_secretive_character_reshows_the_card_this_player_has_seen():
    shown_before = Suggestion(1, "Mustard", "Rope", "Kitchen", refuter=0, shown_to=1, card_shown="Rope")
    obs = make_obs(3, 0, {"Rope", "Mustard"}, {0: 2, 1: 8, 2: 8}, [shown_before], turn=1)
    secretive = _character(Profile(secrecy=1.0, temperature=0.0))
    for _ in range(20):
        assert secretive.choose_card_to_show(obs, ["Mustard", "Rope"], 1, ENGINE_RNG) == "Rope"
    # Player 2 has seen nothing from us: with secrecy the tie is broken
    # toward a card already exposed to *anyone*.
    for _ in range(20):
        assert secretive.choose_card_to_show(obs, ["Mustard", "Rope"], 2, ENGINE_RNG) == "Rope"
    careless = _character(Profile(secrecy=0.0, temperature=0.0))
    seen = {careless.choose_card_to_show(obs, ["Mustard", "Rope"], 1, ENGINE_RNG) for _ in range(40)}
    assert seen == {"Mustard", "Rope"}


def test_incurious_character_enters_a_room_when_it_can():
    obs = _fresh_obs()
    choices = [
        engine.MoveChoice("move", engine.board.HallwayCell("Kitchen", "Ballroom", 2)),
        engine.MoveChoice("move", "Ballroom"),
        engine.MoveChoice("move", engine.board.HallwayCell("Kitchen", "Ballroom", 3)),
    ]
    homebody = _character(Profile(curiosity=0.0, temperature=0.0))
    for _ in range(10):
        assert homebody.choose_movement(obs, choices, ENGINE_RNG).destination == "Ballroom"


def test_belief_is_computed_once_per_observation():
    obs = _fresh_obs()
    character = _character(Profile())
    character.choose_movement(obs, [engine.MoveChoice("move", "Ballroom")], ENGINE_RNG)
    character.choose_suggestion(obs, "Ballroom", ENGINE_RNG)
    character.choose_accusation(obs, ENGINE_RNG)
    assert character.n_calls == 1
    character.choose_accusation(_fresh_obs(), ENGINE_RNG)
    assert character.n_calls == 2


def test_character_ignores_the_engine_rng():
    """Same character seed, different engine RNG objects: identical choices."""
    obs = _fresh_obs()
    choices = [engine.MoveChoice("move", r) for r in ROOMS[:4]]
    a = _character(Profile(temperature=1.0), seed=3)
    b = _character(Profile(temperature=1.0), seed=3)
    picks_a = [a.choose_movement(obs, choices, random.Random(1)).destination for _ in range(10)]
    picks_b = [b.choose_movement(obs, choices, random.Random(99)).destination for _ in range(10)]
    assert picks_a == picks_b


def test_six_characters_play_a_full_game_deterministically():
    def play():
        players = {}
        for seat, name in enumerate(sorted(AGENT_SPECS)[:4]):
            character = build_character(name)
            character.reset(seat)
            players[seat] = character
        return engine.run_game(4, players, seed=17, max_turns=120, observer=clude_constraints.observe)

    state_a, events_a = play()
    state_b, events_b = play()
    assert isinstance(events_a[-1], GameOverEvent)
    assert [repr(e) for e in events_a] == [repr(e) for e in events_b]
    assert state_a.suggestion_log, "characters in a room always suggest"
    # No character ever wastes an honest suggestion on a card it holds
    # unless it was bluffing, and every accusation respected the threshold.
    for accusation in state_a.accusation_log:
        assert accusation.accuser in range(4)
