"""`Character`: one seat's decision layer (Phase 5c).

Each character's turn works in two steps (CLAUDE.md): it calls its own
strategy agent for numbers -- one `select_action` per distinct
observation -- then combines those numbers with its `Profile` to choose
an action. `Character` implements `clude_core.engine.PlayerProtocol`,
so it drops straight into `engine.run_game` (with
``observer=clude_constraints.observe``), and it also exposes
`select_action`, so the trace and benchmark tooling can treat it as an
agent.

The four decisions, and the dial each one answers to:

- **movement** -- shared per-choice features (`features.room_features`)
  handed to the agent's own `choose_destination`; `curiosity`,
  `temperature`.
- **suggestion** -- always suggests when in a room. Suspect and weapon
  are each an honest softmax over the belief (never a card in this
  seat's own hand) unless a `bluff_rate` coin flip names one of its own
  cards instead; `temperature`.
- **accusation** -- accuse the best triple once its confidence product
  reaches `accuse_threshold`. Confidence is `probabilities` for five
  characters and the Dempster-Shafer lower bound for Peacock
  (`ds_belief_confidence`), supplied per `AgentSpec` rather than as a
  dial. No temperature: a threshold test, not a sample.
- **card to show** -- prefer a card this player has already seen, then
  one anyone has seen; `secrecy`, `temperature`.

The character draws every random number from its own RNG, never the
engine's, so the dice sequence of a seeded game depends only on the
seed (see `PlayerProtocol`).

Phase 6a split each decision's *scoring* from its *sampling*:
`suggestion_candidates`, `cards_exposed` and `show_scores` at module
level, and `Character.movement_scores` / `accusation_test`, are pure
functions that draw nothing from the RNG. The LLM wrapper (`clude_llm`)
builds its menus from those same numbers and, when it falls back, calls
the sampled decision with the RNG stream exactly where the headless
character would have had it.
"""
from __future__ import annotations

import time
from random import Random
from typing import Any, Callable, Optional

from clude_core.domain import SUSPECTS, WEAPONS
from clude_core.engine import MoveChoice
from clude_core.state import ClueObservation

from .base import CATEGORIES, AgentProtocol, ClueBelief
from .features import room_features, sample_softmax, score_choices
from .personality import NEUTRAL, Profile

ConfidenceFn = Callable[[ClueBelief], dict]
"""Maps a belief to per-card confidence in [0, 1] for the accusation test."""


def probabilities_confidence(belief: ClueBelief) -> dict:
    """The default confidence: the belief's own masked probabilities."""
    return belief.probabilities


def ds_belief_confidence(belief: ClueBelief) -> dict:
    """Peacock's confidence: her Dempster-Shafer *belief* (lower bound)
    from `ClueBelief.extra`, which stays at 0 for a card until evidence
    actually singles it out -- so she does not commit on a merely
    probable card. Cards absent from `extra` count as 0."""
    return belief.extra.get("belief", {})


def best_triple(confidence: dict) -> tuple:
    """The highest-confidence card per category and the product of the
    three -- the character's P(correct) for accusing that triple.

    Returns
    -------
    ((suspect, weapon, room), float)
        Ties within a category go to the earlier card in category order.
    """
    picks = []
    product = 1.0
    for category in CATEGORIES:
        best = max(category, key=lambda c: confidence.get(c, 0.0))
        picks.append(best)
        product *= confidence.get(best, 0.0)
    return tuple(picks), product


# -- pure scoring helpers (Phase 6a) ------------------------------------------


def suggestion_candidates(obs: ClueObservation, belief: ClueBelief, category: list) -> tuple:
    """The honest candidates for one suggestion slot and their scores.

    Parameters
    ----------
    obs : ClueObservation
        The suggesting seat's view; only `own_hand` is read.
    belief : ClueBelief
        That seat's masked belief.
    category : list[str]
        `SUSPECTS` or `WEAPONS` (the room is the engine's to supply).

    Returns
    -------
    (candidates, scores)
        The cards of `category` not in this seat's hand, in category
        order, and each one's masked P(it is the envelope's). Never
        empty: a hand cannot contain a whole category, since the
        envelope holds one card of each.
    """
    candidates = [c for c in category if c not in obs.own_hand]
    return candidates, [belief.probabilities[c] for c in candidates]


def cards_exposed(obs: ClueObservation, shown_to: int) -> tuple:
    """Which of this seat's own cards it has already shown, per its
    observation: to `shown_to` specifically, and to anyone at all.

    Returns
    -------
    (shown_to_this, shown_to_anyone) : tuple[set[str], set[str]]
    """
    shown_to_this: set = set()
    shown_to_anyone: set = set()
    for s in obs.suggestion_log:
        if s.refuter == obs.my_index and s.card_shown is not None:
            shown_to_anyone.add(s.card_shown)
            if s.shown_to == shown_to:
                shown_to_this.add(s.card_shown)
    return shown_to_this, shown_to_anyone


def show_scores(candidates: list, shown_to_this: set, shown_to_anyone: set, secrecy: float) -> list:
    """The `secrecy`-weighted score of each card this seat could show:
    1.0 for a card `shown_to` has already seen, 0.5 for one anyone has
    seen, 0.0 for a fresh card, all scaled by `secrecy` -- so at
    `secrecy = 0` every candidate ties."""
    return [
        secrecy * (1.0 if c in shown_to_this else 0.5 if c in shown_to_anyone else 0.0)
        for c in candidates
    ]


class Character:
    """A strategy agent for numbers plus a `Profile` for choices.

    Parameters
    ----------
    agent : AgentProtocol
        The belief method; `name` is taken from it.
    profile : Profile
        Dial settings. Default `NEUTRAL`.
    confidence_fn : ConfidenceFn
        What the accusation threshold is compared against; see
        `probabilities_confidence` and `ds_belief_confidence`.

    Notes
    -----
    `n_calls`/`seconds` count and time the agent's `select_action`
    calls, for the arena's ``ms/call`` column. `last_confidence` and
    `last_triple` are the most recent accusation test's numbers, for
    the trace.
    """

    def __init__(
        self,
        agent: AgentProtocol,
        profile: Profile = NEUTRAL,
        confidence_fn: ConfidenceFn = probabilities_confidence,
    ) -> None:
        self.agent = agent
        self.profile = profile
        self.confidence_fn = confidence_fn
        self.name = agent.name
        self.rng = Random()
        self._cached_obs: Optional[ClueObservation] = None
        self._cached_belief: Optional[ClueBelief] = None
        self.n_calls = 0
        self.seconds = 0.0
        self.last_confidence = 0.0
        self.last_triple: Optional[tuple] = None

    def reset(self, seed: "int | None") -> None:
        """Reset the agent and this character's own RNG."""
        self.agent.reset(seed)
        self.rng.seed(seed)
        self._cached_obs = None
        self._cached_belief = None

    def observe(self, transition: Any) -> None:
        """Forward the end-of-game outcome to the agent (Green learns)."""
        self.agent.observe(transition)

    def select_action(self, obs: ClueObservation) -> ClueBelief:
        """The agent's belief for `obs`, computed once per observation
        object: the engine hands the same observation to the movement
        and suggestion decisions of a turn, and a fresh one to the
        accusation, so this is at most two calls per turn."""
        if obs is not self._cached_obs:
            started = time.perf_counter()
            self._cached_belief = self.agent.select_action(obs)
            self.seconds += time.perf_counter() - started
            self.n_calls += 1
            self._cached_obs = obs
        return self._cached_belief

    # -- pure views of the numbers behind each decision (Phase 6a) --------

    def movement_scores(self, obs: ClueObservation, choices: list) -> tuple:
        """The shared room features for `choices` and the default
        curiosity-weighted score of each, both in `choices` order.

        Returns
        -------
        (features, scores) : tuple[list[ChoiceFeatures], list[float]]

        Notes
        -----
        Draws no random numbers. The scores are those of
        `SeededAgentMixin.choose_destination`'s default; an agent that
        overrides `choose_destination` may weigh the same features
        differently, so these describe the menu, not necessarily the
        agent's pick.
        """
        features = room_features(obs, self.select_action(obs), choices)
        return features, score_choices(features, self.profile)

    def accusation_test(self, obs: ClueObservation) -> tuple:
        """The best triple and this character's P(correct) for it,
        against which `choose_accusation` compares `accuse_threshold`.

        Returns
        -------
        ((suspect, weapon, room), float)
        """
        return best_triple(self.confidence_fn(self.select_action(obs)))

    # -- PlayerProtocol -------------------------------------------------

    def choose_movement(
        self, obs: ClueObservation, choices: list, rng: Random
    ) -> MoveChoice:
        del rng  # engine RNG deliberately unused (see module docstring)
        features = room_features(obs, self.select_action(obs), choices)
        return self.agent.choose_destination(obs, choices, features, self.profile)

    def choose_suggestion(
        self, obs: ClueObservation, room: str, rng: Random
    ) -> Optional[tuple]:
        del rng, room  # the engine supplies the room; the character only picks the other two
        belief = self.select_action(obs)
        return (
            self._pick_suggestion_card(obs, belief, SUSPECTS),
            self._pick_suggestion_card(obs, belief, WEAPONS),
        )

    def _pick_suggestion_card(self, obs: ClueObservation, belief: ClueBelief, category: list) -> str:
        """Bluff with one of my own cards at `bluff_rate`, else an honest
        softmax over the belief among cards I don't hold
        (`suggestion_candidates`). The coin flip comes first, so the RNG
        stream is unchanged from before the scoring was split out."""
        own = [c for c in category if c in obs.own_hand]
        if own and self.rng.random() < self.profile.bluff_rate:
            return self.rng.choice(own)
        candidates, scores = suggestion_candidates(obs, belief, category)
        return candidates[sample_softmax(scores, self.profile.temperature, self.rng)]

    def choose_accusation(self, obs: ClueObservation, rng: Random) -> Optional[tuple]:
        del rng
        triple, confidence = self.accusation_test(obs)
        self.last_triple, self.last_confidence = triple, confidence
        return triple if confidence >= self.profile.accuse_threshold else None

    def choose_card_to_show(
        self, obs: ClueObservation, candidates: list, shown_to: int, rng: Random
    ) -> str:
        del rng
        shown_to_this, shown_to_anyone = cards_exposed(obs, shown_to)
        scores = show_scores(candidates, shown_to_this, shown_to_anyone, self.profile.secrecy)
        return candidates[sample_softmax(scores, self.profile.temperature, self.rng)]
