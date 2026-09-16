"""Phase 6b: the LLM wrapper on fake backends.

The invariants: a backend that never answers reproduces the headless
character byte for byte; every failure mode falls back to the
character's own choice; no reply can name a card the engine did not
offer; menus draw no RNG; the schemas are fixed objects; the prompt
shows a seat only what it may see.
"""
from __future__ import annotations

import importlib.util
import json
import os
import random
import re
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import clude_constraints
from clude_agents import build_character
from clude_agents.character import Character
from clude_agents.naive_bayes import NaiveBayesAgent
from clude_agents.personality import DIALS, PRESETS, Profile
from clude_core import engine
from clude_core.board import HallwayCell, Square
from clude_core.domain import ALL_CARDS, ROOMS, SUSPECTS, WEAPONS, Suggestion
from clude_core.engine import MoveChoice
from clude_core.events import GameOverEvent, MoveEvent, RemarkEvent
from clude_llm import (
    LABELS,
    LLMCharacter,
    LLMRequest,
    LLMResult,
    LLMSettings,
    NullBackend,
    Persona,
    RecordingBackend,
    ReplayBackend,
    ReplayMiss,
    ScriptedBackend,
    accusation_menu,
    build_llm_character,
    load_persona,
    load_rules,
    movement_menu,
    open_backend,
    parse_response,
    schema_for,
    show_menu,
    suggestion_menu,
    system_prompt,
    user_prompt,
)
from clude_llm.anthropic_backend import FALLBACK_BETA, AnthropicBackend, estimate_cost
from clude_llm.backend import DEFAULT_MODEL
from clude_llm.schema import CHOICE_SCHEMA, SUGGEST_SCHEMA
from clude_storage import GameRecord, SeatRecord
from clude_training.arena import fill_seed

from tests.test_agents import make_obs
from tests.test_character import GOLDEN_CHARACTER_GAMES, _digest

CLI_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "clude_cli.py"

ENGINE_RNG = random.Random(0)
PERSONA = Persona("Test", "You are a test persona.", "test")
RULES = "Answer with the JSON asked for."
TIP = Suggestion(1, "Mustard", "Rope", "Kitchen", None, 1, None)  # unrefuted: tips the belief


def _obs(own=(), n_players=3, log=(), turn=None):
    sizes = {p: 6 for p in range(n_players)}
    if own:
        sizes[0] = len(own)
    return make_obs(n_players, 0, set(own), sizes, list(log), turn=turn)


def _character(profile: Profile, seed: int = 0, **kwargs) -> Character:
    character = Character(NaiveBayesAgent(), profile, **kwargs)
    character.reset(seed)
    return character


def _wrapped(profile: Profile, responses, seed: int = 0, settings=None) -> LLMCharacter:
    return LLMCharacter(
        _character(profile, seed), ScriptedBackend(responses),
        persona=PERSONA, settings=settings, rules=RULES,
    )


def _llm_game(seed, n_players, roster, make_backend, max_turns=200, settings=None, **dials):
    """`tests.test_character._character_game` with every character wrapped."""
    from clude_training.arena import seat_lineup

    labels, suspects = seat_lineup(list(roster) + ["floor"] * (n_players - len(roster)))
    players, wrappers = {}, {}
    for seat, name in enumerate(labels):
        if name in PRESETS:
            profile = PRESETS[name].with_dials(**dials) if dials else None
            wrapper = LLMCharacter(
                build_character(name, profile), make_backend(),
                persona=PERSONA, settings=settings, rules=RULES,
            )
            wrapper.reset(seat)
            players[seat] = wrappers[seat] = wrapper
        else:
            players[seat] = clude_constraints.FloorBot(rng=random.Random(fill_seed(seed, seat)))
    state, events = engine.run_game(
        n_players, players, seed=seed, max_turns=max_turns, observer=clude_constraints.observe,
        suspects=suspects,
    )
    return state, events, wrappers


# ---------------------------------------------------------------------
# dials
# ---------------------------------------------------------------------


def test_the_two_phase_6_dials_exist_and_old_profiles_still_load():
    assert "leash" in DIALS and "chattiness" in DIALS
    assert (Profile().leash, Profile().chattiness) == (0.25, 0.5)
    for name, preset in PRESETS.items():
        assert (preset.leash, preset.chattiness) == (0.25, 0.5), name
    five = {dial: 0.3 for dial in DIALS if dial not in ("leash", "chattiness")}
    assert Profile.from_dict(five).leash == 0.25
    assert Profile(leash=0.0).with_dials(chattiness=1.0).chattiness == 1.0
    with pytest.raises(ValueError):
        Profile(leash=1.5)


# ---------------------------------------------------------------------
# the headless twin
# ---------------------------------------------------------------------


@pytest.mark.parametrize("seed,n_players,roster", sorted(GOLDEN_CHARACTER_GAMES))
def test_a_backend_that_never_answers_reproduces_the_headless_game(seed, n_players, roster):
    digest, n_events = GOLDEN_CHARACTER_GAMES[(seed, n_players, roster)]
    _state, events, wrappers = _llm_game(seed, n_players, roster, NullBackend)
    assert len(events) == n_events
    assert _digest(events) == digest
    assert not any(isinstance(e, RemarkEvent) for e in events)
    for wrapper in wrappers.values():
        assert wrapper.decisions
        called = [d for d in wrapper.decisions if d.called]
        assert called and all(d.fallback.startswith("error: null backend") for d in called)
        assert all(d.fallback is None for d in wrapper.decisions if not d.called)
        assert wrapper.llm_calls == len(called) == wrapper.fallbacks


class _NeverValid:
    """Every reply is wrong in a different way; none can ever be played."""

    name = "never-valid"

    def __init__(self):
        self.n = 0

    def complete(self, request):
        self.n += 1
        if self.n % 7 == 0:
            raise RuntimeError("backend exploded")
        bad = [
            LLMResult(text="not json at all"),
            LLMResult(text=json.dumps({"choice": "Z", "suspect": "Z", "weapon": "Z", "say": "x"})),
            LLMResult(text=json.dumps({"pick": "A"})),
            LLMResult(text=json.dumps({"choice": "A", "suspect": "A", "weapon": "A", "say": "x"}),
                      stop_reason="refusal"),
            LLMResult(error="boom"),
        ]
        return bad[self.n % len(bad)]


@pytest.mark.parametrize("seed,n_players,roster", sorted(GOLDEN_CHARACTER_GAMES))
def test_an_adversary_with_full_rope_cannot_move_a_single_event(seed, n_players, roster):
    digest, n_events = GOLDEN_CHARACTER_GAMES[(seed, n_players, roster)]
    _state, events, wrappers = _llm_game(
        seed, n_players, roster, _NeverValid, leash=1.0, chattiness=1.0
    )
    assert len(events) == n_events and _digest(events) == digest
    reasons = {d.fallback.split(":")[0] for w in wrappers.values() for d in w.decisions if d.called}
    assert reasons >= {"malformed", "refusal", "error"}


# ---------------------------------------------------------------------
# menus
# ---------------------------------------------------------------------


def test_menus_draw_no_rng_and_the_leash_bounds_what_is_allowed():
    obs = make_obs(3, 0, {"Scarlett", "Knife"}, {0: 2, 1: 8, 2: 8}, [TIP], turn=1)
    tight = _character(Profile(leash=0.0, bluff_rate=0.2), seed=1)
    loose = _character(Profile(leash=1.0, bluff_rate=0.2), seed=1)
    choices = [
        MoveChoice("move", "Ballroom"),
        MoveChoice("move", "Kitchen"),
        MoveChoice("move", Square(7, 4)),
    ]
    before = tight.rng.getstate()

    menu = movement_menu(tight, obs, choices)
    assert tight.rng.getstate() == before
    assert [o.label for o in menu.options] == ["A", "B", "C"]
    assert menu.options[0].action == MoveChoice("move", "Kitchen") and menu.top is menu.options[0]
    assert menu.single() is menu.options[0]
    assert [o.score for o in menu.options] == sorted((o.score for o in menu.options), reverse=True)
    assert menu.options[0].text == "enter the Kitchen" and "corridor square" in menu.options[-1].text
    assert all(o.allowed for o in movement_menu(loose, obs, choices).options)

    suggestion = suggestion_menu(tight, obs)
    assert tight.rng.getstate() == before
    suspects = suggestion.suspect
    assert suspects.top.action == "Mustard" and suspects.single() is suspects.top
    bluff = next(o for o in suspects.options if o.action == "Scarlett")
    assert "bluff" in bluff.note and not bluff.allowed  # no rope: no bluffing
    assert suggestion.single() == (suspects.single(), suggestion.weapon.single())
    assert suggestion.weapon.single().action == "Rope"
    loose_bluff = next(o for o in suggestion_menu(loose, obs).suspect.options if o.action == "Scarlett")
    assert loose_bluff.allowed
    honest = _character(Profile(leash=1.0, bluff_rate=0.0), seed=1)
    assert not next(o for o in suggestion_menu(honest, obs).suspect.options if o.action == "Scarlett").allowed

    shown = Suggestion(1, "Mustard", "Rope", "Kitchen", refuter=0, shown_to=1, card_shown="Rope")
    obs2 = make_obs(3, 0, {"Rope", "Mustard"}, {0: 2, 1: 8, 2: 8}, [shown], turn=1)
    secretive = _character(Profile(leash=0.0, secrecy=1.0), seed=1)
    show = show_menu(secretive, obs2, ["Mustard", "Rope"], 1)
    assert show.top.action == "Rope" and show.single().action == "Rope"
    assert "this player" in show.top.note and {o.action for o in show.options} == {"Mustard", "Rope"}
    careless = _character(Profile(leash=0.0, secrecy=0.0), seed=1)
    assert len(show_menu(careless, obs2, ["Mustard", "Rope"], 1).allowed()) == 2  # all tie at 0
    assert tight.n_calls == 1  # every menu reused the one cached belief


def test_the_accusation_menu_applies_the_leash_symmetrically():
    def character(threshold, leash, confidence):
        return _character(
            Profile(accuse_threshold=threshold, leash=leash), confidence_fn=lambda belief: confidence
        )

    obs = _obs()
    middling = {c: 0.0 for c in ALL_CARDS}
    middling.update({"Plum": 0.9, "Rope": 0.9, "Study": 0.85})  # P(correct) = 0.6885
    both = accusation_menu(character(0.8, 0.25, middling), obs)  # cutoff 0.6: early accusing open
    accuse, pass_ = both.options
    assert accuse.allowed and pass_.allowed and both.top is pass_ and both.single() is None
    assert accuse.action == ("Plum", "Rope", "Study") and accuse.score == pytest.approx(0.6885)
    tight = accusation_menu(character(0.8, 0.0, middling), obs)  # no rope: only the headless answer
    assert tight.single() is tight.options[1]
    too_low = accusation_menu(character(0.8, 0.1, middling), obs)  # cutoff 0.72 > 0.6885
    assert too_low.single() is too_low.options[1]
    sure = {c: 1.0 for c in ALL_CARDS}
    proven = accusation_menu(character(0.8, 0.0, sure), obs)
    assert proven.single() is proven.options[0] and proven.top is proven.options[0]
    roped = accusation_menu(character(0.8, 0.25, sure), obs)  # may hold back, with rope
    assert roped.single() is None and roped.top is roped.options[0]


# ---------------------------------------------------------------------
# the wrapper's decisions
# ---------------------------------------------------------------------


def test_a_valid_leashed_choice_is_played_and_its_line_buffered():
    obs = _obs()
    choices = [MoveChoice("move", room) for room in ROOMS[:3]]
    talker = _wrapped(Profile(leash=1.0, chattiness=1.0), [{"choice": "c", "say": "  Follow me.  "}])
    menu = movement_menu(talker.character, obs, choices)
    assert talker.choose_movement(obs, choices, ENGINE_RNG) == menu.option("C").action
    assert talker.take_remarks() == ["Follow me."] and talker.take_remarks() == []
    decision = talker.decisions[-1]
    assert decision.called and decision.fallback is None and decision.chosen == "C" and decision.spoke
    assert decision.deviated == (menu.option("C").score < menu.top.score)
    assert decision.menu["options"][2]["label"] == "C" and decision.menu["kind"] == "move"
    fresh = _character(Profile(leash=1.0, chattiness=1.0))
    assert talker.character.rng.getstate() == fresh.rng.getstate()  # the LLM path spent no character RNG

    quiet = _wrapped(Profile(leash=1.0, chattiness=0.0), [{"choice": "B", "say": "Shh."}])
    quiet.choose_movement(obs, choices, ENGINE_RNG)
    assert quiet.take_remarks() == [] and quiet.decisions[-1].said == "Shh." and not quiet.decisions[-1].spoke
    muted = _wrapped(
        Profile(leash=1.0, chattiness=1.0), [{"choice": "B", "say": "Shh."}], settings=LLMSettings(speak=False)
    )
    muted.choose_movement(obs, choices, ENGINE_RNG)
    assert muted.take_remarks() == []


BAD_REPLIES = [
    "not json",
    {"choice": "Z", "say": ""},
    {"pick": "A"},
    {"choice": "L", "say": ""},  # a real letter, but no such option among four
    RuntimeError("boom"),
    LLMResult(text='{"choice": "A", "say": ""}', stop_reason="refusal"),
    LLMResult(error="rate limited"),
]


def test_every_failure_mode_falls_back_to_the_characters_own_choice():
    profile = Profile(leash=1.0, temperature=1.0)
    twin = _character(profile, seed=3)
    wrapped = _wrapped(profile, BAD_REPLIES, seed=3)
    obs = _obs()
    choices = [MoveChoice("move", room) for room in ROOMS[:4]]
    reasons = []
    for _ in BAD_REPLIES:
        assert wrapped.choose_movement(obs, choices, ENGINE_RNG) == twin.choose_movement(obs, choices, ENGINE_RNG)
        reasons.append(wrapped.decisions[-1].fallback)
    assert wrapped.llm_calls == wrapped.fallbacks == len(BAD_REPLIES)
    assert [r.split(":")[0] for r in reasons] == [
        "malformed", "malformed", "malformed", "unknown_label", "error", "refusal", "error",
    ]
    assert "RuntimeError" in reasons[4] and "rate limited" in reasons[6]


def test_disallowed_letters_and_an_exhausted_budget_fall_back():
    obs = make_obs(3, 0, set(), {0: 6, 1: 6, 2: 6}, [TIP], turn=1)
    choices = [
        MoveChoice("move", "Kitchen"),
        MoveChoice("move", "Ballroom"),
        MoveChoice("move", Square(7, 4)),
    ]
    wrapped = _wrapped(Profile(leash=0.3, temperature=0.0), [], settings=LLMSettings(max_calls_per_game=1))
    menu = movement_menu(wrapped.character, obs, choices)
    assert len(menu.allowed()) == 2, "the setup needs a real choice plus one option the leash rules out"
    disallowed = next(o for o in menu.options if not o.allowed)
    wrapped.backend.responses = [{"choice": disallowed.label, "say": ""}, {"choice": "A", "say": ""}]

    assert wrapped.choose_movement(obs, choices, ENGINE_RNG) == MoveChoice("move", "Kitchen")
    assert wrapped.decisions[-1].fallback == "not_allowed"
    wrapped.choose_movement(obs, choices, ENGINE_RNG)  # the budget was one call
    assert wrapped.decisions[-1].fallback == "budget" and not wrapped.decisions[-1].called
    assert wrapped.llm_calls == 1
    wrapped.new_game()
    assert wrapped.choose_movement(obs, choices, ENGINE_RNG) == menu.option("A").action
    assert wrapped.decisions[-1].called and wrapped.decisions[-1].fallback is None and wrapped.llm_calls == 2


def test_single_option_menus_never_call_the_model():
    wrapped = _wrapped(Profile(leash=0.5), [{"choice": "A", "say": "x"}])
    obs = _obs(own={"Rope"})
    assert wrapped.choose_card_to_show(obs, ["Rope"], 1, ENGINE_RNG) == "Rope"
    assert wrapped.choose_movement(obs, [MoveChoice("stay", "Kitchen")], ENGINE_RNG) == MoveChoice("stay", "Kitchen")
    assert wrapped.llm_calls == 0 and wrapped.backend.calls == 0
    assert [d.called for d in wrapped.decisions] == [False, False]
    assert all(d.fallback is None and d.chosen == "A" for d in wrapped.decisions)


def test_a_suggestion_takes_both_letters_or_falls_back_whole():
    obs = _obs(own={"Scarlett", "Knife"})
    wrapped = _wrapped(
        Profile(leash=1.0, bluff_rate=0.2, chattiness=1.0),
        [{"suspect": "B", "weapon": "A", "say": "Well now."}, {"suspect": "A", "weapon": "Q", "say": ""}],
    )
    menu = suggestion_menu(wrapped.character, obs)
    assert wrapped.choose_suggestion(obs, "Kitchen", ENGINE_RNG) == (
        menu.suspect.option("B").action, menu.weapon.option("A").action,
    )
    assert wrapped.decisions[-1].chosen == "B/A" and wrapped.take_remarks() == ["Well now."]
    suspect, weapon = wrapped.choose_suggestion(obs, "Kitchen", ENGINE_RNG)  # a bad weapon letter
    assert wrapped.decisions[-1].fallback.startswith("malformed")
    assert suspect in SUSPECTS and weapon in WEAPONS
    bluff = next(o for o in menu.suspect.options if o.action == "Scarlett")
    assert bluff.allowed
    wrapped.backend.responses = [{"suspect": bluff.label, "weapon": "A", "say": ""}]
    wrapped.backend.calls = 0
    assert wrapped.choose_suggestion(obs, "Kitchen", ENGINE_RNG)[0] == "Scarlett"  # a chosen bluff is legal


def test_the_llm_may_hold_back_or_jump_within_the_rope():
    hand = set(ALL_CARDS) - {"Plum", "Wrench", "Dining"}
    proven = make_obs(3, 0, hand, {0: 18, 1: 0, 2: 0}, [])
    cautious = _wrapped(Profile(accuse_threshold=0.8, leash=0.25), [{"choice": "B", "say": "Not yet."}])
    assert cautious.choose_accusation(proven, ENGINE_RNG) is None  # held back at P = 1.0
    assert cautious.decisions[-1].deviated and cautious.last_confidence == pytest.approx(1.0)
    eager = _wrapped(Profile(accuse_threshold=0.8, leash=0.25), [{"choice": "A", "say": "It was Plum!"}])
    assert eager.choose_accusation(proven, ENGINE_RNG) == ("Plum", "Wrench", "Dining")
    assert not eager.decisions[-1].deviated
    tight = _wrapped(Profile(accuse_threshold=0.8, leash=0.0), [{"choice": "B", "say": ""}])
    assert tight.choose_accusation(proven, ENGINE_RNG) == ("Plum", "Wrench", "Dining")
    assert tight.llm_calls == 0


class _RandomLetters:
    """Random letters among the first four, with a line most of the time."""

    name = "random-letters"

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        data = {
            "choice": self.rng.choice(LABELS[:4]),
            "suspect": self.rng.choice(LABELS[:4]),
            "weapon": self.rng.choice(LABELS[:4]),
            "say": self.rng.choice(["Ha.", "", "I wonder.", "Not so fast."]),
        }
        return LLMResult(text=json.dumps(data), model="random", input_tokens=10, output_tokens=5)


def test_random_letters_play_a_legal_game_and_the_table_hears_each_other():
    seeds = iter(range(100))
    state, events, wrappers = _llm_game(
        8, 3, ("Scarlett", "White", "Mustard"), lambda: _RandomLetters(next(seeds)),
        leash=1.0, chattiness=1.0,
    )
    assert isinstance(events[-1], GameOverEvent)
    for suggestion in state.suggestion_log:
        if suggestion.refuter is not None:
            assert suggestion.card_shown in state.hands[suggestion.refuter]  # reveal integrity
    assert all(isinstance(e.destination, (str, Square)) for e in events if isinstance(e, MoveEvent))
    played = [d for w in wrappers.values() for d in w.decisions if d.called and d.fallback is None]
    assert played, "some random letters must land on allowed options"
    remarks = [e for e in events if isinstance(e, RemarkEvent)]
    assert remarks and {r.about for r in remarks} <= {"move", "suggest", "accuse", "show"}
    assert sum(w.remarks_made for w in wrappers.values()) == len(remarks)
    for seat, wrapper in wrappers.items():
        assert any(s != seat for s, _ in wrapper.transcript), "heard somebody else"
        assert wrapper.input_tokens == 10 * wrapper.llm_calls
        assert wrapper.game_tokens == 15 * wrapper.llm_calls
    assert any("Table talk" in r.user for w in wrappers.values() for r in w.backend.requests)


# ---------------------------------------------------------------------
# prompt, schema, backends, records, personas
# ---------------------------------------------------------------------


def test_the_prompt_shows_the_seat_only_what_it_may_see():
    hidden = Suggestion(1, "Plum", "Rope", "Kitchen", refuter=2, shown_to=1, card_shown=None)
    obs = make_obs(3, 0, {"Scarlett", "Knife"}, {0: 2, 1: 8, 2: 8}, [hidden], turn=3)
    character = build_character("Scarlett", Profile(leash=1.0))
    character.reset(0)
    belief = character.select_action(obs)
    menu = movement_menu(character, obs, [MoveChoice("move", "Kitchen"), MoveChoice("move", "Study")])
    text = user_prompt(obs, belief, character, menu, [(1, "Watch me."), (0, "Hm.")])
    assert text.startswith("You are Miss Scarlett, seat P0 Scarlett. Turn 3.")
    assert "Your hand: Knife, Scarlett." in text
    assert "P2 White showed a card (hidden)" in text and "showed Rope" not in text
    assert 'P1 Mustard: "Watch me."' in text and 'P0 Scarlett: "Hm."' in text
    assert "  A. enter the" in text and "Proven in the envelope: nothing yet." in text
    assert text.rstrip().endswith('"say": "<one short line in your voice, or an empty string>"}')
    with pytest.raises(ValueError):
        user_prompt(replace(obs, mask=None), belief, character, menu)

    suggest = user_prompt(obs, belief, character, suggestion_menu(character, obs), [])
    assert "Suspect options" in suggest and "Weapon options" in suggest
    assert "Your bluff rate is 0.10" in suggest and '"suspect": "<letter>"' in suggest

    other_seat = make_obs(3, 1, {"Scarlett", "Knife"}, {0: 8, 1: 2, 2: 8}, [], turn=1)
    text1 = user_prompt(other_seat, character.select_action(other_seat), character, accusation_menu(character, other_seat))
    assert text1.startswith("You are Miss Scarlett, playing the Mustard token as seat P1 Mustard.")
    assert "Decision: whether to accuse." in text1
    assert "Best accusation by your numbers: " in text1 and "with P(correct)" in text1

    # Peacock's belief is all zeros until something is proven: the "best
    # accusation" line must not dress a tie-break up as a view (it would
    # name cards from her own hand).
    peacock = build_character("Peacock")
    peacock.reset(0)
    fresh = make_obs(3, 0, {"Candlestick", "Study"}, {0: 2, 1: 8, 2: 8}, [], turn=1)
    text2 = user_prompt(fresh, peacock.select_action(fresh), peacock, accusation_menu(peacock, fresh))
    assert "nothing stands out yet (P(correct) 0.00)" in text2 and "Candlestick/" not in text2


def test_schemas_are_fixed_objects_and_parsing_is_strict():
    assert schema_for("move") is schema_for("show") is schema_for("accuse") is CHOICE_SCHEMA
    assert schema_for("suggest") is SUGGEST_SCHEMA
    assert CHOICE_SCHEMA["properties"]["choice"]["enum"] == list(LABELS)
    assert CHOICE_SCHEMA["additionalProperties"] is False
    assert SUGGEST_SCHEMA["required"] == ["suspect", "weapon", "say"]
    assert parse_response("move", '{"choice": " b ", "say": " hi "}') == {"choice": "B", "say": "hi"}
    assert parse_response("suggest", '{"suspect": "a", "weapon": "C", "say": 3}') == {
        "suspect": "A", "weapon": "C", "say": "",
    }
    for bad in ("nope", "[1]", '{"say": "x"}', '{"choice": "AA"}', '{"choice": 1}', '{"choice": "M"}'):
        with pytest.raises(ValueError):
            parse_response("move", bad)
    with pytest.raises(KeyError):
        schema_for("dance")


def test_recording_and_replay_backends_round_trip(tmp_path):
    path = tmp_path / "llm" / "rec.json"
    inner = ScriptedBackend([{"choice": "A", "say": "one"}, {"choice": "B", "say": "two"}])
    recorder = RecordingBackend(inner, path)
    first_request = LLMRequest("sys", "user one", CHOICE_SCHEMA, "move")
    second_request = LLMRequest("sys", "user two", CHOICE_SCHEMA, "move")
    first, second = recorder.complete(first_request), recorder.complete(second_request)
    assert len(recorder) == 2 and path.exists()

    replay = ReplayBackend(path)
    assert replay.complete(first_request).text == first.text
    assert replay.complete(second_request).text == second.text and replay.hits == 2
    with pytest.raises(ReplayMiss):
        replay.complete(LLMRequest("sys", "user three", CHOICE_SCHEMA, "move"))
    lenient = ReplayBackend(path, strict=False)
    assert not lenient.complete(LLMRequest("sys", "user three", CHOICE_SCHEMA, "move")).ok
    assert lenient.misses == 1
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["systems"]) == 1 and set(data["entries"]) == {first_request.key(), second_request.key()}

    assert isinstance(open_backend("null"), NullBackend)
    assert isinstance(open_backend(f"replay:{path}"), ReplayBackend)
    with pytest.raises(ValueError):
        open_backend("bogus")
    with pytest.raises(FileNotFoundError):
        ReplayBackend(tmp_path / "missing.json")


def test_records_carry_the_model_and_the_decision_audit():
    state, events, wrappers = _llm_game(3, 3, ("Scarlett",), NullBackend, max_turns=30)
    seats = [
        SeatRecord(0, state.suspects_in_play[0], "Scarlett", "llm", PRESETS["Scarlett"].to_dict(), model="claude-opus-5"),
        SeatRecord(1, state.suspects_in_play[1], "floor", "floor"),
        SeatRecord(2, state.suspects_in_play[2], "floor", "floor"),
    ]
    log = {0: [d.to_dict() for d in wrappers[0].decisions]}
    record = GameRecord.from_game("llm-smoke", 0, 3, state, events, seats, llm_log=log)
    back = GameRecord.from_dict(json.loads(json.dumps(record.to_dict())))
    assert back.seats[0].model == "claude-opus-5" and back.seats[1].model is None
    assert back.seats[0].profile["leash"] == 0.25
    assert back.llm_log == log and set(back.llm_log) == {0}
    assert back.llm_log[0][0]["kind"] in ("move", "suggest", "accuse", "show")
    assert GameRecord.from_game("x", 0, 3, state, events, seats).llm_log is None


def test_personas_and_rules_load_and_the_wrapper_keeps_the_characters_surface(tmp_path):
    rules = load_rules()
    assert "accuse" in rules and "show" in rules
    default = load_persona("Plum", tmp_path)  # no file there: the registry default
    assert default.source == "default" and "Professor Plum" in default.text and "enumeration" in default.text
    (tmp_path / "Plum.md").write_text("# Plum\nDry, precise.\n", encoding="utf-8")
    assert load_persona("Plum", tmp_path).text.startswith("# Plum")

    wrapper = build_llm_character("Plum", NullBackend())
    assert wrapper.name == "Plum" and wrapper.profile == PRESETS["Plum"] and wrapper.persona.name == "Plum"
    assert wrapper.system_prompt().startswith(wrapper.persona.text.strip())
    wrapper.reset(2)
    obs = make_obs(3, 0, {"Rope"}, {0: 1, 1: 9, 2: 8}, [])
    assert wrapper.select_action(obs) is wrapper.character.select_action(obs)
    assert wrapper.n_calls == 1 and wrapper.seconds >= 0.0
    assert wrapper.confidence_fn is wrapper.character.confidence_fn
    assert isinstance(wrapper, engine.SpeakingPlayer)
    assert wrapper.summary()["backend"] == "null" and wrapper.summary()["model"] == "claude-opus-5"


# ---------------------------------------------------------------------
# the Anthropic backend, on a fake client and (opt-in) live
# ---------------------------------------------------------------------


class _FakeMessages:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class _FakeClient:
    """The two `create` entry points the backend may use."""

    def __init__(self, response=None, error=None):
        self.messages = _FakeMessages(response, error)
        self.beta = SimpleNamespace(messages=_FakeMessages(response, error))


def _response(text, stop_reason="end_turn", model="claude-opus-5"):
    usage = SimpleNamespace(input_tokens=1200, output_tokens=40, cache_read_input_tokens=900)
    content = [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(content=content, stop_reason=stop_reason, model=model, usage=usage)


def test_anthropic_backend_builds_the_call_and_maps_the_reply():
    request = LLMRequest("sys", "user", CHOICE_SCHEMA, "move")
    fake = _FakeClient(_response('{"choice": "A", "say": "Hm."}'))
    backend = AnthropicBackend(client=fake)
    result = backend.complete(request)
    assert result.ok and parse_response("move", result.text)["choice"] == "A"
    assert (result.input_tokens, result.output_tokens, result.cached_tokens) == (1200, 40, 900)
    assert result.model == "claude-opus-5" and result.seconds >= 0.0
    assert not fake.messages.calls, "server fallbacks go through the beta entry point"
    call = fake.beta.messages.calls[-1]
    assert call["betas"] == [FALLBACK_BETA] and call["fallbacks"] == "default"
    assert call["model"] == DEFAULT_MODEL == "claude-opus-5" and call["max_tokens"] == 2048
    assert call["system"] == [{"type": "text", "text": "sys", "cache_control": {"type": "ephemeral"}}]
    assert call["messages"] == [{"role": "user", "content": "user"}]
    assert call["output_config"] == {"format": {"type": "json_schema", "schema": CHOICE_SCHEMA}, "effort": "low"}
    assert "thinking" not in call  # Opus 5 thinks adaptively by default; effort sets the depth

    plain = AnthropicBackend(model="claude-sonnet-5", effort="medium", server_fallbacks=False,
                             client=_FakeClient(_response("{}", model="claude-sonnet-5")))
    plain.complete(request)
    call = plain.client.messages.calls[-1]
    assert "betas" not in call and "fallbacks" not in call
    assert call["model"] == "claude-sonnet-5" and call["output_config"]["effort"] == "medium"

    refused = AnthropicBackend(client=_FakeClient(_response('{"choice": "A", "say": ""}', "refusal")))
    result = refused.complete(request)
    assert not result.ok and result.stop_reason == "refusal"
    broken = AnthropicBackend(client=_FakeClient(error=RuntimeError("429 rate limited")))
    result = broken.complete(request)
    assert not result.ok and result.error.startswith("RuntimeError: 429") and result.text is None

    assert estimate_cost("claude-opus-5", 1000, 100, 9000) == pytest.approx((1000 * 5 + 9000 * 0.5 + 100 * 25) / 1e6)
    assert estimate_cost("mystery-model", 1, 1) is None


def test_open_backend_builds_the_anthropic_backend_without_touching_the_network(tmp_path):
    backend = open_backend("anthropic", model="claude-sonnet-5", effort="high", timeout=5.0)
    assert isinstance(backend, AnthropicBackend)
    assert (backend.model, backend.effort, backend.timeout) == ("claude-sonnet-5", "high", 5.0)
    recorder = open_backend(f"record:{tmp_path / 'r.json'}")
    assert isinstance(recorder, RecordingBackend) and isinstance(recorder.inner, AnthropicBackend)


@pytest.mark.skipif(
    not os.environ.get("CLUDE_LLM_LIVE"),
    reason="set CLUDE_LLM_LIVE=1 (with ANTHROPIC_API_KEY or an `ant auth login` profile) to call the API",
)
def test_anthropic_backend_live_smoke():
    """One real decision, twice: a valid letter comes back, and the second
    call reads the persona + rules prefix from the cache."""
    backend = AnthropicBackend(os.environ.get("CLUDE_LLM_MODEL", DEFAULT_MODEL))
    system = system_prompt(load_persona("Scarlett"), load_rules())
    user = (
        "You are Miss Scarlett, seat P0 Scarlett. Turn 1.\n"
        "Decision: where to move.\n"
        "Options (best first by your method's score; choose one letter):\n"
        "  A. enter the Kitchen -- score 0.60; a suggestion there this turn\n"
        "  B. enter the Study -- score 0.40; a suggestion there this turn\n"
        'Answer with JSON only: {"choice": "<letter>", "say": "<one short line in your voice, or an empty string>"}\n'
    )
    request = LLMRequest(system, user, CHOICE_SCHEMA, "move")
    first = backend.complete(request)
    assert first.ok, first.error
    assert parse_response("move", first.text)["choice"] in ("A", "B")
    assert first.input_tokens > 0 and first.output_tokens > 0
    second = backend.complete(request)
    assert second.ok, second.error
    assert second.cached_tokens > 0, "the system prefix should be served from the prompt cache"


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"

# (fixture, seed, players, roster, envelope, winner, tally) per recorded game.
# Both re-recorded on 2026-09-14 when characters were locked to their own
# tokens (the seat labels in every prompt moved, so every key did), on
# 2026-09-15 for the Classic board (every menu moved), and again that day
# when the re-measurement retuned the presets: the per-turn prompt states
# the character's own accuse_threshold, so Scarlett's move from 0.15 to
# 0.3 rekeyed seed 1 and Plum's retuned curiosity and sample budget
# rekeyed seed 2.
RECORDED_GAMES = [
    (
        "llm_seed1.json", "1", "3", "Scarlett,Peacock",
        "Mustard/Rope/Ballroom", "P1 Mustard (floor)",
        "Turns played: 41; suggestions: 18; accusations: 1",
    ),
    (
        "llm_seed2.json", "2", "4", "Plum,Mustard,Green,White",
        "Scarlett/Candlestick/Ballroom", "P1 White",
        "Turns played: 10; suggestions: 2; accusations: 1",
    ),
]


@pytest.mark.parametrize(
    "fixture,seed,players,roster,envelope,winner,tally", RECORDED_GAMES,
    ids=[row[0].removesuffix(".json") for row in RECORDED_GAMES],
)
def test_recorded_llm_games_replay_offline(
    capsys, fixture, seed, players, roster, envelope, winner, tally
):
    """The recorded games in `tests/fixtures/` replay byte for byte with
    no network: the wrapper's only source of answers is the recording, so
    a miss means the prompt moved, not that the model changed its mind.

    `LLMRequest.key()` hashes the system prompt, so editing any persona
    file or `rules.md` invalidates every key here and these start
    missing. Re-record the affected game, e.g.

        python scripts/clude_cli.py play --seed 1 --players 3 \\
            --roster Scarlett,Peacock --llm \\
            --llm-backend record:tests/fixtures/llm_seed1.json --verbose

    and update its row in `RECORDED_GAMES` from the transcript it prints.
    The envelope follows from the seed and stays put; the winner and the
    turn count do not, because the model's choices are its own and are
    not reproducible across recordings."""
    path = FIXTURE_DIR / fixture
    if not path.exists():
        pytest.skip(f"missing fixture {path}")
    spec = importlib.util.spec_from_file_location("clude_cli", CLI_SCRIPT)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    argv = [
        "play", "--seed", seed, "--players", players, "--roster", roster,
        "--llm", "--llm-backend", f"replay:{path}", "--verbose",
    ]
    assert cli.main(argv) == 0
    out = capsys.readouterr().out
    assert f"Envelope: {envelope}" in out
    assert f"Winner: {winner}" in out
    assert tally in out
    # A strict replay turns a prompt change into a miss, which the wrapper
    # swallows as a fallback; no seat may fall back or the recording is stale.
    assert not re.search(r", [1-9]\d* fallbacks", out)


# ---------------------------------------------------------------------
# the arena and sweeps with LLM seats
# ---------------------------------------------------------------------


def test_arena_wraps_characters_and_the_null_backend_pairs_with_the_headless_run(tmp_path):
    from clude_storage import LocalStore
    from clude_training.arena import run_arena

    kwargs = dict(n_games=3, seed=5, roster=("Scarlett", "White", "floor"), player_counts=(3,), max_turns=60)
    plain = run_arena(**kwargs)
    store = LocalStore(tmp_path)
    twin = run_arena(**kwargs, llm_backend=NullBackend(), store=store, run_id="llm-smoke")
    assert [g.winner_label for g in twin.games] == [g.winner_label for g in plain.games]
    assert [g.turns for g in twin.games] == [g.turns for g in plain.games]
    stats = twin.per_player["Scarlett"]
    assert stats.kind == "llm" and stats.llm_decisions > 0 and stats.llm_calls > 0
    assert stats.llm_asked == stats.llm_calls == stats.llm_fallbacks and stats.fallback_rate == 1.0
    assert stats.llm_played == 0 and stats.remarks_per_game == 0.0
    assert stats.deviation_rate != stats.deviation_rate  # NaN: nothing was played
    assert twin.per_player["floor"].kind == "floor" and twin.per_player["floor"].llm_decisions == 0
    assert twin.llm == {"backend": "null", "model": "claude-opus-5", "characters": ["Scarlett", "White"]}
    assert "LLM seats:" in twin.summary_table() and "LLM seats:" not in plain.summary_table()
    assert plain.run_id == "arena-5-3" and run_arena(**kwargs, llm_backend=NullBackend()).run_id == "llm-5-3"
    json.dumps(twin.to_dict())

    record = GameRecord.from_dict(store.get_game("llm-smoke", 0))
    llm_seats = [s for s in record.seats if s.kind == "llm"]
    assert llm_seats and all(s.model == "claude-opus-5" for s in llm_seats)
    assert set(record.llm_log) == {s.seat for s in llm_seats}
    assert all(record.llm_log[s.seat] for s in llm_seats)

    subset = run_arena(**kwargs, llm_backend=NullBackend(), llm_characters=["White"])
    assert subset.per_player["Scarlett"].kind == "character" and subset.per_player["White"].kind == "llm"
    with pytest.raises(ValueError):
        run_arena(**kwargs, llm_backend=NullBackend(), llm_characters=["Plum"])


def test_arena_llm_columns_move_with_a_talking_backend_and_the_leash_sweeps():
    from clude_training.arena import run_arena
    from clude_training.sweep import sweep_dial

    loose = {"Scarlett": PRESETS["Scarlett"].with_dials(leash=1.0, chattiness=1.0)}
    result = run_arena(
        n_games=2, seed=9, roster=("Scarlett", "floor"), player_counts=(3,), max_turns=60,
        llm_backend=_RandomLetters(11), profiles=loose,
    )
    s = result.per_player["Scarlett"]
    assert s.llm_played > 0 and s.remarks_per_game > 0 and s.tokens_per_game > 0
    assert 0.0 <= s.fallback_rate < 1.0 and 0.0 <= s.deviation_rate <= 1.0
    assert "talk/g" in result.summary_table()

    sweep = sweep_dial(
        "leash", [0.0, 1.0], n_games=2, seed=9, roster=("Scarlett", "floor"), player_counts=(3,),
        max_turns=60, llm_backend=_RandomLetters(3),
    )
    zero, full = sweep.rows
    # No rope still lets the model pick among *ties* on the character's own
    # score, so calls can happen at leash 0; deviations cannot.
    assert zero.stats.llm_deviations == 0 and (zero.stats.deviation_rate in (0.0,) or zero.stats.llm_played == 0)
    assert full.stats.llm_calls > 0 and full.stats.llm_calls >= zero.stats.llm_calls
    assert "deviate%" in sweep.summary_table()
    assert sweep.to_dict()["monotone"]["deviation_rate"] in ("increasing", "flat", None)
