"""Phase 5c: `Character` -- one unit test per engine decision, plus a
full game among the six. Phase 6a adds the pure scoring helpers the LLM
wrapper builds its menus from, and golden fingerprints of seeded
character games that the split must not have moved."""
from __future__ import annotations

import hashlib
import random

import pytest

import clude_constraints
from clude_agents import AGENT_SPECS, ClueBelief, build_character
from clude_agents.character import (
    Character,
    best_triple,
    cards_exposed,
    ds_belief_confidence,
    probabilities_confidence,
    show_scores,
    suggestion_candidates,
)
from clude_agents.naive_bayes import NaiveBayesAgent
from clude_agents.personality import Profile
from clude_core import engine
from clude_core.domain import ALL_CARDS, ROOMS, SUSPECTS, WEAPONS, Suggestion
from clude_core.events import GameOverEvent
from clude_training.arena import fill_seed

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


def _character_game(seed: int, n_players: int, roster: tuple, max_turns: int = 200):
    """Each character on its own token (reset with its seat index),
    `FloorBot`s on the lowest free tokens, seats in board order: the way
    `scripts/clude_cli.py play` and the arena seat a table
    (`seat_lineup`)."""
    from clude_training.arena import seat_lineup

    lineup = list(roster) + ["floor"] * (n_players - len(roster))
    labels, suspects = seat_lineup(lineup)
    players = {}
    for seat, label in enumerate(labels):
        if label in AGENT_SPECS:
            character = build_character(label)
            character.reset(seat)
            players[seat] = character
        else:
            players[seat] = clude_constraints.FloorBot(rng=random.Random(fill_seed(seed, seat)))
    return engine.run_game(
        n_players, players, seed=seed, max_turns=max_turns, observer=clude_constraints.observe,
        suspects=suspects,
    )


def _digest(events) -> str:
    return hashlib.sha256("\n".join(repr(e) for e in events).encode()).hexdigest()


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
        engine.MoveChoice("move", engine.board.Square(8, 9)),
        engine.MoveChoice("move", "Ballroom"),
        engine.MoveChoice("move", engine.board.Square(8, 10)),
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


# ---------------------------------------------------------------------
# Phase 6a: the pure scoring helpers behind each decision
# ---------------------------------------------------------------------


def test_suggestion_candidates_are_the_honest_options_with_belief_scores():
    own = {"Scarlett", "Knife"}
    obs = _fresh_obs(own)
    character = _character(Profile())
    belief = character.select_action(obs)
    suspects, scores = suggestion_candidates(obs, belief, SUSPECTS)
    assert suspects == [c for c in SUSPECTS if c != "Scarlett"]
    assert scores == [belief.probabilities[c] for c in suspects]
    weapons, _ = suggestion_candidates(obs, belief, WEAPONS)
    assert "Knife" not in weapons and len(weapons) == len(WEAPONS) - 1


def test_cards_exposed_and_show_scores_match_the_decision():
    shown_before = Suggestion(1, "Mustard", "Rope", "Kitchen", refuter=0, shown_to=1, card_shown="Rope")
    obs = make_obs(3, 0, {"Rope", "Mustard", "Knife"}, {0: 3, 1: 8, 2: 7}, [shown_before], turn=1)
    assert cards_exposed(obs, 1) == ({"Rope"}, {"Rope"})
    assert cards_exposed(obs, 2) == (set(), {"Rope"})
    candidates = ["Knife", "Mustard", "Rope"]
    assert show_scores(candidates, {"Rope"}, {"Rope"}, 1.0) == [0.0, 0.0, 1.0]
    assert show_scores(candidates, set(), {"Rope"}, 0.5) == [0.0, 0.0, 0.25]
    assert show_scores(candidates, {"Rope"}, {"Rope"}, 0.0) == [0.0, 0.0, 0.0]


def test_movement_scores_and_accusation_test_are_pure():
    """The menu helpers read the belief and draw nothing from the RNG, so
    a wrapper can call them and then fall back to the sampled decision
    with the RNG stream exactly where the headless character had it."""
    obs = _fresh_obs()
    choices = [engine.MoveChoice("move", r) for r in ROOMS[:4]]
    character = _character(Profile(temperature=1.0), seed=5)
    before = character.rng.getstate()

    features, scores = character.movement_scores(obs, choices)
    assert [f.choice for f in features] == choices
    assert len(scores) == len(choices) and all(0.0 <= s <= 1.0 for s in scores)
    triple, confidence = character.accusation_test(obs)
    assert len(triple) == 3 and 0.0 <= confidence <= 1.0
    belief = character.select_action(obs)
    suggestion_candidates(obs, belief, SUSPECTS)
    cards_exposed(obs, 1)

    assert character.rng.getstate() == before
    assert character.n_calls == 1
    # And the decision reports the very numbers the pure view computed.
    character.choose_accusation(obs, ENGINE_RNG)
    assert (character.last_triple, character.last_confidence) == (triple, confidence)


# ---------------------------------------------------------------------
# Full games: determinism and golden fingerprints
# ---------------------------------------------------------------------

# Event-log fingerprints of seeded character games, captured on the
# Phase 5 code immediately before Phase 6a split scoring from sampling
# and re-captured on 2026-09-14 when characters were locked to their
# own tokens (`seat_lineup`): every seat moved, so every game did; and
# again on 2026-09-15 when the ring board gave way to the Classic grid
# and rules (`docs/board-plan.md`), which moved every game once more.
# They pin the character layer the way `tests/test_engine.py`'s goldens
# pin the rules engine: a change here means a character's behaviour
# moved, which no Phase 6 work is supposed to do. Regenerate
# deliberately if a method or a preset is meant to change.
GOLDEN_CHARACTER_GAMES = {
    (23, 5, ("Scarlett", "Peacock", "Mustard", "White")): (
        "3ef05cd41317619ed82411e70633aed0d2463c5add2e1d1d1edbf83ad373930b", 50,
    ),
    (9, 3, ("Scarlett", "White", "Mustard")): (
        "ba1b9c48e89beca34df2010db716881f75143afcfd056b466f741acd00117247", 173,
    ),
    (31, 4, ("Peacock", "Scarlett")): (
        "bd5c46703ea3ae0e07a6a298d7f4fce45770002868a8b8d12587791a223be056", 62,
    ),
}
GOLDEN_FOUR_CHARACTER_GAME = (
    "bda8a34137a283e15e68b43c3f1c77eaff09fd60e02ee0907fa0e9fbd527d827", 183,
)


@pytest.mark.parametrize("seed,n_players,roster", sorted(GOLDEN_CHARACTER_GAMES))
def test_seeded_character_games_match_the_pre_split_golden_logs(seed, n_players, roster):
    expected_digest, expected_events = GOLDEN_CHARACTER_GAMES[(seed, n_players, roster)]
    _state, events = _character_game(seed, n_players, roster)
    assert len(events) == expected_events
    assert _digest(events) == expected_digest


def test_six_characters_play_a_full_game_deterministically():
    roster = tuple(sorted(AGENT_SPECS)[:4])  # Green, Mustard, Peacock, Plum: the expensive four
    state_a, events_a = _character_game(17, 4, roster, max_turns=120)
    state_b, events_b = _character_game(17, 4, roster, max_turns=120)
    assert isinstance(events_a[-1], GameOverEvent)
    assert [repr(e) for e in events_a] == [repr(e) for e in events_b]
    assert state_a.suggestion_log, "characters in a room always suggest"
    for accusation in state_a.accusation_log:
        assert accusation.accuser in range(4)
    expected_digest, expected_events = GOLDEN_FOUR_CHARACTER_GAME
    assert len(events_a) == expected_events
    assert _digest(events_a) == expected_digest
