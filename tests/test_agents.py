"""Phase 3: the six strategy agents.

The most important property here mirrors Phase 2's own soundness test
(`tests/test_constraints.py`): no agent may ever assign nonzero
probability to a card the deduction floor has ruled out for the
envelope, or anything but 1.0 to a card it has already proven. Each
agent's own distinguishing behavior gets one or two targeted tests on
top of that shared invariant.
"""
from __future__ import annotations

import itertools

import pytest

import clude_agents
from clude_agents.bandit import RevealedOutcome
from clude_agents.base import mask_and_normalize
from clude_agents.decision_tree import _build_tree, _predict
from clude_agents.exact_enum import ExactEnumAgent
from clude_agents.markov import MarkovAgent
from clude_agents.naive_bayes import NaiveBayesAgent
from clude_constraints import ENVELOPE, propagate
from clude_core import engine
from clude_core.bots import RandomBot
from clude_core.domain import ALL_CARDS, ROOMS, SUSPECTS, WEAPONS, Suggestion
from clude_core.state import ClueObservation

import clude_constraints

CATEGORIES = (SUSPECTS, WEAPONS, ROOMS)
ALL_SUSPECT_NAMES = ("Scarlett", "Plum", "Peacock", "Mustard", "Green", "White")


def make_obs(n_players, my_index, own_hand, hand_sizes, suggestion_log, turn=None):
    obs = ClueObservation(
        n_players=n_players,
        my_index=my_index,
        own_hand=frozenset(own_hand),
        active_players=tuple(True for _ in range(n_players)),
        hand_sizes=hand_sizes,
        suggestion_log=tuple(suggestion_log),
        accusation_log=(),
        turn=turn if turn is not None else len(suggestion_log),
    )
    from dataclasses import replace

    return replace(obs, mask=propagate(obs))


def _true_holder(state, card):
    if card in state.envelope:
        return ENVELOPE
    for p, hand in state.hands.items():
        if card in hand:
            return p
    raise AssertionError(f"{card} not found anywhere")


def _assert_sums_to_one(probs):
    for category in CATEGORIES:
        total = sum(probs[c] for c in category)
        assert abs(total - 1.0) < 1e-6, (category, total)


def _assert_never_contradicts_mask(probs, mask):
    for card in ALL_CARDS:
        if not mask.is_possible(card, ENVELOPE):
            assert probs[card] == 0.0, f"{card}: nonzero on an eliminated card"
        if mask.holder_of(card) == ENVELOPE:
            assert probs[card] == 1.0, f"{card}: not certain on a proven card"


# ---------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------


def test_registry_lists_all_six_suspects():
    names = {spec.name for spec in clude_agents.list_agent_specs()}
    assert names == set(ALL_SUSPECT_NAMES)


def test_build_agent_unknown_name_raises():
    with pytest.raises(KeyError):
        clude_agents.build_agent("Nobody")


def test_build_agent_returns_a_working_instance_per_suspect():
    for name in ALL_SUSPECT_NAMES:
        agent = clude_agents.build_agent(name)
        assert agent.name == name
        agent.reset(0)


# ---------------------------------------------------------------------
# mask_and_normalize
# ---------------------------------------------------------------------


def test_mask_and_normalize_resolved_category_is_one_hot():
    obs = make_obs(
        n_players=3,
        my_index=0,
        own_hand={"Scarlett", "Mustard", "White", "Green", "Peacock"},
        hand_sizes={0: 5, 1: 8, 2: 8},
        suggestion_log=[],
    )
    probs = mask_and_normalize({c: 1.0 for c in ALL_CARDS}, obs.mask)
    assert probs["Plum"] == 1.0
    for s in SUSPECTS:
        if s != "Plum":
            assert probs[s] == 0.0


def test_mask_and_normalize_uniform_fallback_when_no_evidence():
    obs = make_obs(
        n_players=3, my_index=0, own_hand=set(),
        hand_sizes={0: 6, 1: 6, 2: 6}, suggestion_log=[],
    )
    probs = mask_and_normalize({}, obs.mask)
    for category in CATEGORIES:
        possible = [c for c in category if obs.mask.is_possible(c, ENVELOPE)]
        for c in possible:
            assert probs[c] == pytest.approx(1.0 / len(possible))


def test_mask_and_normalize_renormalizes_proportionally():
    obs = make_obs(
        n_players=3, my_index=0, own_hand=set(),
        hand_sizes={0: 6, 1: 6, 2: 6}, suggestion_log=[],
    )
    raw = {c: 0.0 for c in ALL_CARDS}
    raw["Scarlett"] = 3.0
    raw["Mustard"] = 1.0
    probs = mask_and_normalize(raw, obs.mask)
    assert probs["Scarlett"] == pytest.approx(3.0 / 4.0)
    assert probs["Mustard"] == pytest.approx(1.0 / 4.0)
    for s in SUSPECTS:
        if s not in ("Scarlett", "Mustard"):
            assert probs[s] == 0.0


# ---------------------------------------------------------------------
# Shared soundness property, across all six agents and real self-play
# ---------------------------------------------------------------------


@pytest.mark.parametrize("suspect_name", ALL_SUSPECT_NAMES)
@pytest.mark.parametrize("seed", range(5))
def test_agent_never_contradicts_the_deduction_floor(suspect_name, seed):
    n_players = 3 + seed % 4
    bots = {p: RandomBot() for p in range(n_players)}
    state, _events = engine.run_game(n_players, bots, seed=seed, max_turns=80)
    agent = clude_agents.build_agent(suspect_name)
    agent.reset(seed)

    for viewer in range(n_players):
        obs = clude_constraints.observe(state, viewer)
        belief = agent.select_action(obs)
        _assert_sums_to_one(belief.probabilities)
        _assert_never_contradicts_mask(belief.probabilities, obs.mask)


# ---------------------------------------------------------------------
# Scarlett -- naive Bayes
# ---------------------------------------------------------------------


def test_naive_bayes_unrefuted_suggestion_raises_belief_for_named_cards():
    baseline = make_obs(
        n_players=3, my_index=0, own_hand=set(),
        hand_sizes={0: 6, 1: 6, 2: 6}, suggestion_log=[],
    )
    unrefuted = Suggestion(
        suggester=1, suspect="Mustard", weapon="Rope", room="Kitchen",
        refuter=None, shown_to=1, card_shown=None,
    )
    with_evidence = make_obs(
        n_players=3, my_index=0, own_hand=set(),
        hand_sizes={0: 6, 1: 6, 2: 6}, suggestion_log=[unrefuted], turn=1,
    )
    agent = NaiveBayesAgent()
    agent.reset(0)
    base_belief = agent.select_action(baseline).probabilities
    evidenced_belief = agent.select_action(with_evidence).probabilities
    assert evidenced_belief["Mustard"] > base_belief["Mustard"]
    assert evidenced_belief["Rope"] > base_belief["Rope"]
    assert evidenced_belief["Kitchen"] > base_belief["Kitchen"]


# ---------------------------------------------------------------------
# Plum -- exact enumeration, checked against an independent brute force
# ---------------------------------------------------------------------


def _brute_force_envelope_marginal(obs, mask, max_states=50_000):
    """Independent reference enumerator: exhaustively try every
    assignment of unresolved cards to holders and tally how often each
    lands on ENVELOPE, for differential testing against `ExactEnumAgent`.
    Returns None if the state space is too large to brute-force.
    """
    unresolved = [c for c in ALL_CARDS if mask.holder_of(c) is None]
    domains = [sorted(mask.possible_holders[c], key=str) for c in unresolved]
    size = 1
    for d in domains:
        size *= len(d)
        if size > max_states:
            return None

    category_of = {c: i for i, cat in enumerate(CATEGORIES) for c in cat}
    base_capacity = {
        p: mask.hand_sizes[p] - sum(1 for c in ALL_CARDS if mask.holder_of(c) == p)
        for p in range(obs.n_players)
    }
    base_envelope_used = [
        any(mask.holder_of(c) == ENVELOPE for c in cat) for cat in CATEGORIES
    ]

    counts = {c: 0 for c in unresolved}
    completions = 0
    for combo in itertools.product(*domains):
        capacity = dict(base_capacity)
        envelope_used = list(base_envelope_used)
        ok = True
        for card, holder in zip(unresolved, combo):
            if holder == ENVELOPE:
                cat_i = category_of[card]
                if envelope_used[cat_i]:
                    ok = False
                    break
                envelope_used[cat_i] = True
            else:
                if capacity[holder] <= 0:
                    ok = False
                    break
                capacity[holder] -= 1
        if not ok:
            continue
        assignment = dict(zip(unresolved, combo))
        # A constraint can already be satisfied by a card that resolved
        # outside the unresolved set entirely (not just by one of this
        # combo's picks) -- check the true holder for those too.
        if not all(
            any(
                assignment.get(c, mask.holder_of(c)) == holder
                for c in cards
            )
            for cards, holder in mask.or_constraints
        ):
            continue
        completions += 1
        for card, holder in assignment.items():
            if holder == ENVELOPE:
                counts[card] += 1
    if completions == 0:
        return None
    return {c: n / completions for c, n in counts.items()}, unresolved


def test_exact_enum_reports_which_path_produced_its_answer():
    bots = {p: RandomBot() for p in range(3)}
    state, _events = engine.run_game(3, bots, seed=2, max_turns=25)
    obs = clude_constraints.observe(state, 0)
    unresolved = [c for c in ALL_CARDS if obs.mask.holder_of(c) is None]
    assert len(unresolved) > 1

    exact = ExactEnumAgent()
    exact.reset(0)
    belief = exact.select_action(obs)
    assert belief.extra["method"] in {"exact", "sampled"}
    assert belief.extra["nodes"] > 0

    starved = ExactEnumAgent(node_budget=1, sample_budget=50)
    starved.reset(0)
    belief = starved.select_action(obs)
    assert belief.extra["method"] == "sampled"
    assert 0 < belief.extra["valid_samples"] <= 50


def test_exact_enum_matches_independent_brute_force():
    """FloorBot games converge, so their late states have the small
    unresolved sets the reference enumerator can afford to brute-force."""
    checked_any = False
    for seed in range(20):
        n_players = 3 + seed % 3
        bots = {p: clude_constraints.FloorBot() for p in range(n_players)}
        state, _events = engine.run_game(
            n_players, bots, seed=seed, max_turns=100, observer=clude_constraints.observe
        )
        for viewer in range(n_players):
            obs = clude_constraints.observe(state, viewer)
            mask = obs.mask
            unresolved = [c for c in ALL_CARDS if mask.holder_of(c) is None]
            if not (1 <= len(unresolved) <= 8):
                continue
            reference = _brute_force_envelope_marginal(obs, mask)
            if reference is None:
                continue
            expected, _unresolved = reference
            agent = ExactEnumAgent(node_budget=200_000, sample_budget=1)
            agent.reset(seed)
            got = agent.select_action(obs).probabilities
            for card, p in expected.items():
                assert got[card] == pytest.approx(p, abs=1e-9), (seed, viewer, card)
            checked_any = True
    assert checked_any, "no sampled game produced a small-enough unresolved set to check"


# ---------------------------------------------------------------------
# Peacock -- Dempster-Shafer
# ---------------------------------------------------------------------


def test_dempster_shafer_belief_never_exceeds_plausibility():
    from clude_agents.dempster_shafer import DempsterShaferAgent

    agent = DempsterShaferAgent()
    agent.reset(0)
    for seed in range(6):
        n_players = 3 + seed % 4
        bots = {p: RandomBot() for p in range(n_players)}
        state, _events = engine.run_game(n_players, bots, seed=seed, max_turns=60)
        for viewer in range(n_players):
            obs = clude_constraints.observe(state, viewer)
            belief = agent.select_action(obs)
            for card in ALL_CARDS:
                if card not in belief.extra["belief"]:
                    continue
                assert belief.extra["belief"][card] <= belief.extra["plausibility"][card] + 1e-9


# ---------------------------------------------------------------------
# White -- Markov model
# ---------------------------------------------------------------------


def test_stationary_repeat_probability_increases_with_more_repeats():
    """Direct test of the chain, not the end-to-end belief, so that the
    normalization against the floor prior can't mask the thing this
    checks: that P(repeat) itself rises with more repeats."""
    from clude_agents.markov import _stationary_repeat_probability

    never_repeats = _stationary_repeat_probability([0, 0])
    repeats_once = _stationary_repeat_probability([0, 1])
    repeats_and_stays = _stationary_repeat_probability([0, 1, 1])
    assert _stationary_repeat_probability([]) == pytest.approx(0.5)
    assert repeats_once > never_repeats
    assert repeats_and_stays > repeats_once


def test_markov_unnamed_cards_are_unsuspicious_not_impossible():
    """Phase 5b: a still-possible card nobody has named keeps the floor's
    prior instead of a hard 0, and a re-named card sits above it."""
    repeated = [
        Suggestion(1, "Mustard", "Rope", "Kitchen", refuter=2, shown_to=1, card_shown=None),
        Suggestion(1, "Mustard", "Knife", "Kitchen", refuter=2, shown_to=1, card_shown=None),
    ]
    obs = make_obs(3, 0, set(), {0: 6, 1: 6, 2: 6}, repeated, turn=2)
    agent = MarkovAgent()
    agent.reset(0)
    belief = agent.select_action(obs)
    assert belief.probabilities["Green"] > 0.0  # never named, still possible
    assert belief.probabilities["Mustard"] > belief.probabilities["Green"]
    assert set(belief.extra["closeness"]) == {1, 2}
    assert 0.0 <= belief.extra["closeness"][1] < 1.0
    assert belief.extra["closeness"][1] > belief.extra["closeness"][2]  # 2 has suggested nothing
    assert belief.extra["repeat_probability"][1] > belief.extra["repeat_probability"][2]


# ---------------------------------------------------------------------
# Mustard -- decision tree (the tree mechanics in isolation; the shared
# soundness test above already covers the trained agent end to end)
# ---------------------------------------------------------------------


def test_decision_tree_recovers_a_perfectly_separable_split():
    rows = []
    for i in range(60):
        low = [0.0, 0.0]
        high = [1.0, 1.0]
        rows.append((tuple(low), 0))
        rows.append((tuple(high), 1))
    tree = _build_tree(rows, depth=0, max_depth=4, min_samples_leaf=5)
    assert _predict(tree, (0.0, 0.0)) < 0.5
    assert _predict(tree, (1.0, 1.0)) > 0.5


def test_tree_summary_and_render_agree_on_shape():
    from clude_agents.decision_tree import FEATURE_NAMES, render_tree, summarize_tree

    rows = [((0.0, 0.0), 0), ((1.0, 1.0), 1)] * 30
    tree = _build_tree(rows, depth=0, max_depth=4, min_samples_leaf=5)
    summary = summarize_tree(tree)
    assert summary.n_leaves >= 2
    assert summary.depth >= 1
    assert summary.n_nodes == summary.n_leaves + sum(summary.feature_use.values())
    assert set(summary.feature_use) <= set(FEATURE_NAMES)
    assert summary.leaf_predictions == tuple(sorted(summary.leaf_predictions))

    rendered = render_tree(tree)
    assert rendered.count("leaf p=") == summary.n_leaves
    assert "(n=60)" in rendered  # the root saw every row


def test_trained_mustard_exposes_its_tree():
    from clude_agents.decision_tree import DecisionTreeAgent, summarize_tree

    agent = DecisionTreeAgent(n_training_games=2, training_seed=5)
    summary = summarize_tree(agent.tree)
    assert summary.n_nodes >= 1
    assert agent.tree.n_samples > 0


def test_mustard_leaves_are_smoothed_away_from_hard_zeros():
    """Phase 5b: with m-estimate leaves no leaf predicts exactly 0 or 1;
    with m = 0 the same data can (a leaf with no positives)."""
    from clude_agents.decision_tree import DecisionTreeAgent, summarize_tree

    smoothed = DecisionTreeAgent(n_training_games=4, training_seed=5, smoothing_m=3.0)
    leaves = summarize_tree(smoothed.tree).leaf_predictions
    assert min(leaves) > 0.0 and max(leaves) < 1.0

    rows = [((0.0,), 0)] * 30 + [((1.0,), 1)] * 30
    plain = _build_tree(rows, depth=0, max_depth=2, min_samples_leaf=5, smoothing_m=0.0)
    assert _predict(plain, (0.0,)) == 0.0
    smooth = _build_tree(rows, depth=0, max_depth=2, min_samples_leaf=5, smoothing_m=3.0)
    assert 0.0 < _predict(smooth, (0.0,)) < 0.1
    assert 0.9 < _predict(smooth, (1.0,)) < 1.0


def test_mustard_features_include_the_phase5_additions():
    from clude_agents.decision_tree import FEATURE_NAMES, _features

    named_twice = [
        Suggestion(1, "Mustard", "Knife", "Kitchen", refuter=2, shown_to=1, card_shown=None),
        Suggestion(2, "Mustard", "Rope", "Study", refuter=0, shown_to=2, card_shown="Rope"),
    ]
    obs = make_obs(3, 0, {"Rope"}, {0: 1, 1: 9, 2: 8}, named_twice, turn=2)
    features = _features(obs, obs.mask, "Mustard", SUSPECTS)
    assert len(features) == len(FEATURE_NAMES)
    by_name = dict(zip(FEATURE_NAMES, features))
    assert by_name["distinct_namers"] == 2.0
    assert by_name["times_named_total"] == 2.0
    # Rope is located (own hand), so the second suggestion named Mustard
    # beside one located card; the first beside none.
    assert by_name["named_beside_located"] == pytest.approx(0.5)


# ---------------------------------------------------------------------
# Green -- bandit ensemble
# ---------------------------------------------------------------------


def test_bandit_updates_posteriors_toward_a_consistently_correct_arm():
    from clude_agents.base import ClueBelief
    from clude_agents.bandit import BanditAgent

    agent = BanditAgent()
    agent.reset(0)

    # Rig the situation: pretend "Scarlett" (naive Bayes) nailed it, every
    # other arm was clueless, across several rounds -- her posterior
    # should end up favored over the others.
    envelope = ("Scarlett", "Candlestick", "Kitchen")
    for _ in range(15):
        agent._last_predictions = {
            name: ClueBelief(probabilities={c: (1.0 if c in envelope else 0.0) for c in ALL_CARDS})
            if name == "Scarlett"
            else ClueBelief(probabilities={c: 0.0 for c in ALL_CARDS})
            for name in agent.arms
        }
        agent.observe(RevealedOutcome(envelope=envelope))

    scarlett_mean = agent.candidates["Scarlett"].alpha / (
        agent.candidates["Scarlett"].alpha + agent.candidates["Scarlett"].beta
    )
    for name, c in agent.candidates.items():
        if name == "Scarlett":
            continue
        other_mean = c.alpha / (c.alpha + c.beta)
        assert scarlett_mean > other_mean


def test_rank_rewards_are_linear_in_rank_with_shared_ties():
    from clude_agents.bandit import rank_rewards

    rewards = rank_rewards({"a": 0.1, "b": 0.5, "c": 0.3, "d": 0.9, "e": 0.7})
    assert rewards == {"a": 1.0, "c": 0.75, "b": 0.5, "e": 0.25, "d": 0.0}
    tied = rank_rewards({"a": 0.1, "b": 0.1, "c": 0.9})
    assert tied["a"] == tied["b"] == pytest.approx(0.75)
    assert tied["c"] == 0.0
    assert rank_rewards({"only": 2.0}) == {"only": 1.0}
    all_tied = rank_rewards({"a": 1.0, "b": 1.0})
    assert all_tied == {"a": 0.5, "b": 0.5}
