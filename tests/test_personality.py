"""Phase 5c: `Profile`, presets, and the shared feature/scoring helpers."""
from __future__ import annotations

import random

import pytest

from clude_agents import AGENT_SPECS, ClueBelief
from clude_agents.features import (
    DISTANCE_DISCOUNT,
    pick_destination,
    room_distances,
    room_features,
    sample_softmax,
    score_choices,
)
from clude_agents.personality import DIALS, NEUTRAL, PRESETS, Profile, preset
from clude_core import board
from clude_core.domain import ALL_CARDS, ROOMS
from clude_core.engine import MoveChoice


# ---------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------


def test_profile_validates_ranges():
    Profile(accuse_threshold=0.0, bluff_rate=1.0, curiosity=0.5, secrecy=1.0, temperature=0.0)
    with pytest.raises(ValueError):
        Profile(accuse_threshold=1.5)
    with pytest.raises(ValueError):
        Profile(bluff_rate=-0.1)
    with pytest.raises(ValueError):
        Profile(temperature=-1.0)


def test_profile_round_trips_through_dict_and_rejects_unknown_dials():
    original = Profile(accuse_threshold=0.42, bluff_rate=0.3, curiosity=0.9, secrecy=0.1, temperature=0.7)
    assert Profile.from_dict(original.to_dict()) == original
    assert set(original.to_dict()) == set(DIALS)
    assert Profile.from_dict({}) == NEUTRAL
    with pytest.raises(ValueError):
        Profile.from_dict({"charm": 0.5})
    with pytest.raises(ValueError):
        original.with_dials(urgency=0.5)
    assert original.with_dials(secrecy=0.9).secrecy == 0.9
    assert original.with_dials(secrecy=0.9).bluff_rate == 0.3


def test_every_suspect_has_a_preset_and_the_registry_carries_it():
    assert set(PRESETS) == set(AGENT_SPECS)
    for name, spec in AGENT_SPECS.items():
        assert spec.profile == preset(name)
    with pytest.raises(KeyError):
        preset("Nobody")


def test_mustard_and_white_stay_neutral_on_accusing():
    """The 'don't encode the flaw twice' rule: their wrong accusations
    must be attributable to the method, not a dial."""
    assert PRESETS["Mustard"].accuse_threshold == NEUTRAL.accuse_threshold
    assert PRESETS["White"].accuse_threshold == NEUTRAL.accuse_threshold


# ---------------------------------------------------------------------
# features
# ---------------------------------------------------------------------


def test_room_distances_use_hallways_and_secret_passages():
    from_kitchen = room_distances("Kitchen")
    assert from_kitchen["Kitchen"] == 0
    assert from_kitchen["Study"] == 1  # secret passage
    assert from_kitchen["Ballroom"] == 7  # the door square, five along, the Ballroom's west door
    cell = board.Square(7, 4)  # outside the Kitchen door
    from_cell = room_distances(cell)
    assert from_cell["Kitchen"] == 1
    assert from_cell["Ballroom"] == 6
    assert set(from_cell) == set(ROOMS)


def _belief(room_probs: dict) -> ClueBelief:
    probs = {c: 0.0 for c in ALL_CARDS}
    probs.update(room_probs)
    return ClueBelief(probabilities=probs)


def test_room_features_land_now_or_head_for_the_best_discounted_room():
    belief = _belief({"Kitchen": 0.6, "Ballroom": 0.4})
    choices = [
        MoveChoice("move", "Ballroom"),
        MoveChoice("move", board.Square(7, 4)),  # outside the Kitchen door
    ]
    landing, hallway = room_features(None, belief, choices)
    assert landing.room == "Ballroom" and landing.proximity == 1.0
    assert landing.information == pytest.approx(0.4)
    assert hallway.room is None
    assert hallway.target == "Kitchen"
    assert hallway.information == pytest.approx(0.6 * DISTANCE_DISCOUNT)
    assert hallway.proximity == pytest.approx(0.5)


def test_score_choices_blends_by_curiosity():
    belief = _belief({"Kitchen": 0.6, "Ballroom": 0.4})
    choices = [
        MoveChoice("move", "Ballroom"),
        MoveChoice("move", board.Square(7, 4)),  # outside the Kitchen door
    ]
    features = room_features(None, belief, choices)
    greedy_for_rooms = score_choices(features, Profile(curiosity=0.0))
    assert greedy_for_rooms[0] > greedy_for_rooms[1]  # landing now beats walking
    curious = score_choices(features, Profile(curiosity=1.0))
    assert curious[0] == pytest.approx(0.4)
    assert curious[1] == pytest.approx(0.6 * DISTANCE_DISCOUNT)


def test_sample_softmax_is_greedy_at_zero_temperature_and_random_when_hot():
    rng = random.Random(0)
    scores = [0.1, 0.9, 0.3]
    assert all(sample_softmax(scores, 0.0, rng) == 1 for _ in range(20))
    hot = {sample_softmax(scores, 100.0, rng) for _ in range(200)}
    assert hot == {0, 1, 2}
    ties = {sample_softmax([0.5, 0.5, 0.1], 0.0, rng) for _ in range(50)}
    assert ties == {0, 1}
    with pytest.raises(ValueError):
        sample_softmax([], 0.1, rng)


def test_pick_destination_prefers_a_room_when_incurious():
    belief = _belief({"Kitchen": 0.6, "Ballroom": 0.4})
    choices = [
        MoveChoice("move", board.Square(7, 4)),  # outside the Kitchen door
        MoveChoice("move", "Ballroom"),
    ]
    features = room_features(None, belief, choices)
    choice = pick_destination(features, Profile(curiosity=0.0, temperature=0.0), random.Random(0))
    assert choice == MoveChoice("move", "Ballroom")
