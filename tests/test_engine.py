import hashlib
import random

import pytest

from clude_core import board, engine
from clude_core.bots import RandomBot
from clude_core.domain import ALL_CARDS
from clude_core.events import AccusationEvent, GameOverEvent, MoveEvent, RemarkEvent, SuggestionEvent
from clude_core.state import ClueObservation


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


def test_legal_moves_in_room_offer_stay_only_to_a_summoned_token():
    """Classic rule: a token may stay and suggest only when another
    player's suggestion moved it into the room since its last turn."""
    rng = random.Random(0)
    state = engine.setup(3, rng)
    state.positions[0] = "Kitchen"
    assert engine.MoveChoice("stay", "Kitchen") not in engine.legal_moves(state, 0, roll=3)
    assert all(c.kind != "stay" for c in engine.legal_moves(state, 0, roll=3))
    state.summoned[0] = True
    choices = engine.legal_moves(state, 0, roll=3)
    assert engine.MoveChoice("stay", "Kitchen") in choices
    engine.apply_move(state, 0, engine.MoveChoice("stay", "Kitchen"))
    assert state.positions[0] == "Kitchen"


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
    assert state.summoned[white_player]  # may stay and suggest there on its next turn
    assert not state.summoned[0]  # the suggester was already in the room


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


# ---------------------------------------------------------------------
# Phase 5a: the PlayerProtocol seam and observer injection
# ---------------------------------------------------------------------

# Event-log fingerprints of seeded RandomBot games. Building an
# observation per decision consumes no RNG, so the Phase 5a seam was
# verified byte-identical against fingerprints captured on the Phase 4
# engine; these were then regenerated once, after the Phase 5b board fix
# (tokens can leave a room through its doors, `board.reachable`), and
# again on 2026-09-15 when the ring board was replaced by the Classic
# grid and rules (`docs/board-plan.md`). They must not change again
# unless the rules or the event types themselves do -- regenerate
# deliberately if so.
GOLDEN_GAMES = {
    (1, 4): ("72dfa754d120be46f99bd14aa24b39f132225eb0270083bbe1ddfe130971d5d5", 68),
    (2, 3): ("8896c8999affb4a996baea17381c55f9f17354021557f052653fc43470d5d211", 53),
    (3, 5): ("7f67caf5202062f3313987322e8ac5e69eba2246a3d065a7d85d224b28f1c855", 123),
    (4, 6): ("64bde24a2b371381d4acde5a9b28212d2b10c1c9674ea68175b86c84007ebd91", 136),
    (42, 4): ("b85b4685ee4e0e58058b6deff32b9fe4c93fa6096a9eec27da14731e0f4d68aa", 141),
}


def test_boxed_in_corridor_token_may_stay():
    rng = random.Random(0)
    state = engine.setup(3, rng)
    cell = board.Square(24, 16)  # the dead-end square between the Hall and the Study
    state.positions[0] = cell
    state.positions[1] = board.Square(23, 16)  # its only neighbour
    choices = engine.legal_moves(state, 0, roll=6)
    assert choices == [engine.MoveChoice("stay", cell)]
    engine.apply_move(state, 0, choices[0])
    assert state.positions[0] == cell


def test_a_corridor_token_must_use_its_whole_roll():
    rng = random.Random(0)
    state = engine.setup(3, rng)
    state.positions[0] = board.Square(7, 4)  # outside the Kitchen door
    state.positions[1] = board.Square(1, 7)  # the others well away
    state.positions[2] = board.Square(1, 8)
    choices = engine.legal_moves(state, 0, roll=2)
    destinations = {c.destination for c in choices}
    assert "Kitchen" in destinations  # entering a room ends the move early
    assert board.Square(7, 3) not in destinations  # one step is not a two
    assert all(c.kind == "move" for c in choices)


@pytest.mark.parametrize("seed,n_players", sorted(GOLDEN_GAMES))
def test_seeded_random_games_match_the_pre_seam_golden_logs(seed, n_players):
    expected_digest, expected_events = GOLDEN_GAMES[(seed, n_players)]
    bots = {p: RandomBot() for p in range(n_players)}
    _state, events = engine.run_game(n_players, bots, seed=seed, max_turns=200)
    digest = hashlib.sha256("\n".join(repr(e) for e in events).encode()).hexdigest()
    assert len(events) == expected_events
    assert digest == expected_digest


class _Probe(RandomBot):
    """A RandomBot that checks what the engine hands it: every
    observation is from its own seat, the accusation observation already
    contains this turn's suggestion, and the refuter's observation does
    not yet contain the suggestion being refuted."""

    def __init__(self, seat):
        self.seat = seat
        self.pending = None
        self.checked = 0

    def choose_movement(self, obs, choices, rng):
        assert obs.my_index == self.seat
        self.pending = None
        return super().choose_movement(obs, choices, rng)

    def choose_suggestion(self, obs, room, rng):
        assert obs.my_index == self.seat
        self.pending = super().choose_suggestion(obs, room, rng)
        if self.pending is not None:
            self.pending = (*self.pending, room, len(obs.suggestion_log))
        return self.pending[:2] if self.pending else None

    def choose_accusation(self, obs, rng):
        assert obs.my_index == self.seat
        if self.pending is not None:
            suspect, weapon, room, n_before = self.pending
            last = obs.suggestion_log[-1]
            assert len(obs.suggestion_log) == n_before + 1
            assert (last.suspect, last.weapon, last.room) == (suspect, weapon, room)
            assert last.suggester == self.seat
            self.checked += 1
        return super().choose_accusation(obs, rng)

    def choose_card_to_show(self, obs, candidates, shown_to, rng):
        assert obs.my_index == self.seat
        assert shown_to != self.seat
        assert all(c in obs.own_hand for c in candidates)
        self.checked += 1
        return super().choose_card_to_show(obs, candidates, shown_to, rng)


def test_engine_hands_each_seat_its_own_fresh_observation():
    probes = {p: _Probe(p) for p in range(4)}
    engine.run_game(4, probes, seed=7, max_turns=60)  # seed 7: twenty shows on the grid board
    assert sum(p.checked for p in probes.values()) > 10


def test_observer_is_injected_and_defaults_to_for_player():
    seen = []

    def recording_observer(state, viewer):
        obs = ClueObservation.for_player(state, viewer)
        seen.append((viewer, obs.my_index, obs.mask))
        return obs

    bots = {p: RandomBot() for p in range(3)}
    engine.run_game(3, bots, seed=5, max_turns=20, observer=recording_observer)
    assert seen, "the observer was never called"
    assert all(viewer == my_index for viewer, my_index, _mask in seen)
    assert all(mask is None for _viewer, _my_index, mask in seen)  # for_player sets no mask


def test_for_player_redacts_only_what_the_viewer_may_not_see():
    bots = {p: RandomBot() for p in range(4)}
    state, _events = engine.run_game(4, bots, seed=11, max_turns=80)
    shown = [s for s in state.suggestion_log if s.card_shown is not None]
    assert shown, "need at least one refutation with a card shown"
    for viewer in range(4):
        obs = ClueObservation.for_player(state, viewer)
        for original, visible in zip(state.suggestion_log, obs.suggestion_log):
            entitled = viewer in (original.suggester, original.refuter)
            assert visible.card_shown == (original.card_shown if entitled else None)
            assert visible.cards() == original.cards()


# ---------------------------------------------------------------------
# Phase 6a: the SpeakingPlayer hook
# ---------------------------------------------------------------------


class _Talker(RandomBot):
    """A RandomBot that buffers one line per decision, so the engine's
    `SpeakingPlayer` hook has something to drain."""

    def __init__(self):
        self.lines = []
        self.heard = []

    def hear(self, remark):
        self.heard.append(remark)

    def take_remarks(self):
        out, self.lines = self.lines, []
        return out

    def choose_movement(self, obs, choices, rng):
        self.lines.append("Off I go.")
        return super().choose_movement(obs, choices, rng)

    def choose_suggestion(self, obs, room, rng):
        self.lines.append(f"Something happened in the {room}.")
        return super().choose_suggestion(obs, room, rng)

    def choose_accusation(self, obs, rng):
        self.lines.append("Hmm.")
        return super().choose_accusation(obs, rng)

    def choose_card_to_show(self, obs, candidates, shown_to, rng):
        self.lines.append("Have a look at this.")
        return super().choose_card_to_show(obs, candidates, shown_to, rng)


def test_speaking_players_remarks_follow_their_decisions_and_change_nothing_else():
    assert isinstance(_Talker(), engine.SpeakingPlayer)
    assert not isinstance(RandomBot(), engine.SpeakingPlayer)

    bots = {0: _Talker(), 1: RandomBot(), 2: RandomBot()}
    _state, events = engine.run_game(3, bots, seed=5, max_turns=30)
    remarks = [e for e in events if isinstance(e, RemarkEvent)]
    assert remarks and all(r.seat == 0 for r in remarks)
    assert {r.about for r in remarks} >= {"move", "accuse"}
    assert not bots[0].lines, "every buffered line was drained"
    assert not bots[0].heard, "nobody else at this table speaks"

    for i, event in enumerate(events):
        if not isinstance(event, RemarkEvent):
            continue
        previous = events[i - 1]
        if event.about == "move":
            assert isinstance(previous, MoveEvent) and previous.player == 0
        elif event.about == "suggest":
            assert isinstance(previous, SuggestionEvent) and previous.suggestion.suggester == 0
        elif event.about == "show":
            assert isinstance(previous, SuggestionEvent) and previous.suggestion.refuter == 0
        elif event.about == "accuse" and isinstance(previous, AccusationEvent):
            assert previous.accusation.accuser == 0
        assert event.turn == previous.turn

    # Remarks are the only difference: the same seed with a silent bot
    # in seat 0 plays the identical game.
    _state, silent = engine.run_game(3, {p: RandomBot() for p in range(3)}, seed=5, max_turns=30)
    assert [e for e in events if not isinstance(e, RemarkEvent)] == silent
