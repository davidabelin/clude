"""Phase 6a: `clude_agents.explain`, the plain-text views of a seat's
knowledge that the CLI prints and the LLM prompt is built from. Every
function is checked to work from an observation and labels alone."""
from __future__ import annotations

from clude_agents import ClueBelief, build_character
from clude_agents.explain import (
    CATEGORY_TAGS,
    describe_suggestion,
    format_accusation_test,
    format_belief,
    format_extra,
    format_mask,
    seat_label,
    seat_labels,
)
from clude_agents.personality import Profile
from clude_core.domain import ALL_CARDS, ROOMS, SUSPECTS, WEAPONS, Suggestion

from tests.test_agents import make_obs

SUSPECTS_IN_PLAY = SUSPECTS[:3]


def test_seat_labels_name_the_token_and_a_different_occupant():
    assert seat_label(SUSPECTS_IN_PLAY, 1) == "P1 Mustard"
    assert seat_label(SUSPECTS_IN_PLAY, 1, ["Scarlett", "Plum", "floor"]) == "P1 Mustard (Plum)"
    assert seat_labels(SUSPECTS_IN_PLAY, ["Scarlett", "Plum", "floor"]) == [
        "P0 Scarlett", "P1 Mustard (Plum)", "P2 White (floor)",
    ]


def test_describe_suggestion_names_the_card_only_when_visible():
    names = seat_labels(SUSPECTS_IN_PLAY)
    hidden = Suggestion(0, "Plum", "Rope", "Kitchen", refuter=2, shown_to=0, card_shown=None)
    assert describe_suggestion(hidden, names, 4) == (
        "turn 4: P0 Scarlett suggests Plum/Rope/Kitchen -- P2 White showed a card (hidden)"
    )
    visible = Suggestion(0, "Plum", "Rope", "Kitchen", refuter=2, shown_to=0, card_shown="Rope")
    assert describe_suggestion(visible, names).endswith("P2 White showed Rope")
    unrefuted = Suggestion(1, "Plum", "Rope", "Kitchen", refuter=None, shown_to=1, card_shown=None)
    assert describe_suggestion(unrefuted, names) == (
        "P1 Mustard suggests Plum/Rope/Kitchen -- nobody could refute"
    )


def test_format_belief_ranks_possible_cards_and_stars_proven_ones():
    hand = set(ALL_CARDS) - {"Plum", "Wrench", "Dining", "Rope", "Knife"}
    obs = make_obs(3, 0, hand, {0: len(hand), 1: 1, 2: 1}, [])
    character = build_character("Scarlett")
    character.reset(0)
    belief = character.select_action(obs)
    text = format_belief(belief.probabilities, obs.mask, top=2)
    suspect_part, weapon_part, room_part = text.split("  |  ")
    assert suspect_part == "S: Plum*"          # the only suspect not in hand: proven
    assert room_part == "R: Dining*"
    assert weapon_part.startswith("W: ") and weapon_part.count(" 0.") == 2
    shown = weapon_part[3:].split()[0::2]
    assert len(shown) == 2 and set(shown) <= {"Wrench", "Rope", "Knife"}
    everything = format_belief(belief.probabilities, obs.mask, top=1, all_cards=True)
    assert everything.split("  |  ")[1].count(" 0.") == 3
    assert [tag for tag, _ in CATEGORY_TAGS] == ["S", "W", "R"]


def test_format_extra_covers_each_method_and_is_empty_otherwise():
    flat = {c: 1.0 / 21 for c in ALL_CARDS}
    assert format_extra(ClueBelief(flat, {"method": "exact", "completions": 5, "nodes": 30})) == (
        "[exact: 5 deals, 30 nodes]"
    )
    assert "sampled" in format_extra(
        ClueBelief(flat, {"method": "sampled", "valid_samples": 40, "nodes": 999})
    )
    assert format_extra(ClueBelief(flat, {"selected_arm": "Plum"})) == "[arm: Plum]"
    ds = ClueBelief(
        flat,
        {"belief": {c: 0.0 for c in ALL_CARDS}, "plausibility": {c: 1.0 for c in ALL_CARDS}},
    )
    assert format_extra(ds) == "[bel/pl of top: S 0.00/1.00 W 0.00/1.00 R 0.00/1.00]"
    assert format_extra(ClueBelief(flat, {})) == ""


def test_format_accusation_test_compares_against_the_threshold():
    character = build_character("Scarlett", Profile(accuse_threshold=0.9))
    character.reset(0)
    obs = make_obs(3, 0, set(), {0: 6, 1: 6, 2: 6}, [])
    text = format_accusation_test(character, character.select_action(obs))
    assert text.startswith("[P(correct)=") and text.endswith("<0.90]")
    hand = set(ALL_CARDS) - {"Plum", "Wrench", "Dining"}
    proven = make_obs(3, 0, hand, {0: 18, 1: 0, 2: 0}, [])
    assert format_accusation_test(character, character.select_action(proven)) == (
        "[P(correct)=1.00 >=0.90]"
    )


def test_format_mask_has_a_column_per_seat_and_the_envelope():
    obs = make_obs(4, 0, {"Rope"}, {0: 1, 1: 6, 2: 6, 3: 5}, [])
    grid = format_mask(obs.mask, 4).splitlines()
    assert grid[0].split() == ["card", "P0", "P1", "P2", "P3", "Env"]
    assert len(grid) == 1 + len(SUSPECTS) + len(WEAPONS) + len(ROOMS)
    rope = next(line for line in grid if line.startswith("Rope"))
    assert rope.split()[1:] == ["#", ".", ".", ".", "."]
