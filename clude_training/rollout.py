"""Rollouts for training Plum's policy (Phase 12, N4;
`docs/deepnash-plan.md` 3.2).

A rollout is one real game through `clude_core.engine.run_game` with
some seats answered by the network under training and the rest by the
table he will actually face: the floor bot and the five other
characters, each at its own token. What comes back, a `GameTrace`, is
what `scripts/train_plum.py` learns from: every decision the network's
seats made (the encoded state, the options, the index drawn) and, once
the game is over, each seat's reward (+1 won, -1 out on a wrong
accusation, 0 otherwise) and the true envelope.

The network plays any token. `deep_nash.encode_state` reads the floor
relative to the seat, and a token is only a start square and a card, so
a self-play table seats the network several times. Seats are built here
directly rather than through the arena: per seat the draw is the
network, a floor bot, or that token's own character when the token is
not Plum (Plum's own character *is* the network).

`RecordingCharacter` is the one piece of play that differs from a
`Character` over `DeepNashAgent`: it draws the same numbers from the
same RNG, and writes down what it drew. Nothing here needs torch; the
numpy forward pass is the policy, which is what lets a worker pool play
with plain pickled weights.
"""
from __future__ import annotations

import multiprocessing
from dataclasses import dataclass, field
from random import Random
from typing import Optional

import numpy as np

import clude_constraints
from clude_agents import build_character
from clude_agents.bandit import RevealedOutcome
from clude_agents.character import Character
from clude_agents.deep_nash import DeepNashAgent, encode_choices, encode_state
from clude_agents.features import room_features, sample_softmax
from clude_agents.personality import PRESETS
from clude_constraints import ENVELOPE
from clude_core import engine
from clude_core.domain import ALL_CARDS, SUSPECTS
from clude_core.events import AccusationEvent, GameOverEvent
from clude_core.state import ClueObservation
from clude_training.arena import DEFAULT_ROSTER, fill_seed, lineup_for_game, seat_lineup

__all__ = [
    "DEFAULT_MAX_TURNS",
    "HEADS",
    "NET",
    "POPULATIONS",
    "TRAINING_PROFILE",
    "Decision",
    "GameTrace",
    "RecordingCharacter",
    "draw_table",
    "evaluate",
    "play_one",
    "rollout_batch",
]

DEFAULT_MAX_TURNS = 150
"""A rollout's turn cap: `self_play`'s, shorter than the arena's 200,
since an untrained table may never accuse."""

POPULATIONS = ("mixed", "self")
"""``"self"``: every seat is the network. ``"mixed"``: a coin per game
between that and a per-seat draw among the network, a floor bot and
the token's own character (David's call, 2026-10-05)."""

NET = "net"
"""The seat kind of a network seat in a trace."""

FLOOR = "floor"

HEADS = ("move", "suspect", "weapon")
"""The three decision heads a trace records, in the order their codes
run in `GameTrace.to_arrays`."""

TRAINING_PROFILE = PRESETS["Plum"].with_dials(temperature=1.0)
"""Plum's preset at temperature 1, so what is sampled is the policy
itself; the bluff coin, the accusation threshold and the secrecy are
the preset's."""

_SUSPECT_SET = frozenset(SUSPECTS)


# -- what a game leaves behind --------------------------------------------------


@dataclass
class Decision:
    """One decision by a network seat.

    Parameters
    ----------
    seat : int
    head : str
        ``"move"``, ``"suspect"`` or ``"weapon"``.
    state : np.ndarray
        `encode_state` of the observation, `STATE_SIZE` floats.
    possible : np.ndarray
        Per card in `ALL_CARDS` order, 1.0 where the floor still allows
        the envelope to hold it: the belief loss is taken over these.
    action : int
        The index drawn, into `choices` for a move and into `candidates`
        for a suggestion slot.
    choices : np.ndarray or None
        `encode_choices` of the legal moves, ``(k, CHOICE_SIZE)``; None
        for a suggestion.
    candidates : list[int] or None
        For a suggestion slot, the indices within the category of the
        honest candidates (the cards not in this hand); None for a move.
    """

    seat: int
    head: str
    state: np.ndarray
    possible: np.ndarray
    action: int
    choices: Optional[np.ndarray] = None
    candidates: Optional[list] = None


@dataclass
class GameTrace:
    """One rollout: the decisions of every network seat and the game's
    outcome.

    Parameters
    ----------
    seed : int
    n_players : int
    kinds : list[str]
        Per seat: ``"net"``, ``"floor"`` or a character's name.
    suspects : tuple[str, ...]
        The token in each seat.
    decisions : list[Decision]
    rewards : list[float]
        Per seat: +1 won, -1 out on a wrong accusation, 0 otherwise.
    envelope : tuple[str, str, str]
    turns : int
    winner : int or None
    capped : bool
        True when the game hit `max_turns` with seats still in.
    """

    seed: int
    n_players: int
    kinds: list
    suspects: tuple
    decisions: list = field(default_factory=list)
    rewards: list = field(default_factory=list)
    envelope: tuple = ()
    turns: int = 0
    winner: Optional[int] = None
    capped: bool = False

    @property
    def net_seats(self) -> list:
        return [seat for seat, kind in enumerate(self.kinds) if kind == NET]

    def to_arrays(self) -> dict:
        """The trace as flat arrays for a trainer.

        Returns
        -------
        dict
            ``states`` ``(N, STATE_SIZE)``; ``possible`` ``(N, 21)``;
            ``envelope`` ``(N, 21)`` one-hot of the three envelope cards;
            ``head`` ``(N,)`` codes into `HEADS`; ``action`` ``(N,)``;
            ``reward`` ``(N,)`` the deciding seat's; ``seat`` and
            ``game`` ``(N,)``; ``choices`` ``(M, CHOICE_SIZE)`` every
            move's rows end to end with ``choice_offsets`` ``(N + 1,)``
            (a suggestion's span is empty); ``candidates`` ``(C,)`` every
            suggestion's candidate indices end to end with
            ``candidate_offsets`` ``(N + 1,)`` (a move's span is empty).
        """
        n = len(self.decisions)
        env = np.zeros(len(ALL_CARDS))
        for card in self.envelope:
            env[ALL_CARDS.index(card)] = 1.0
        states = np.zeros((n, 0)) if n == 0 else np.stack([d.state for d in self.decisions])
        possible = np.zeros((n, 0)) if n == 0 else np.stack([d.possible for d in self.decisions])
        choice_rows: list = []
        choice_offsets = [0]
        candidate_rows: list = []
        candidate_offsets = [0]
        for d in self.decisions:
            if d.choices is not None:
                choice_rows.append(d.choices)
                choice_offsets.append(choice_offsets[-1] + len(d.choices))
                candidate_offsets.append(candidate_offsets[-1])
            else:
                candidate_rows.extend(d.candidates or [])
                candidate_offsets.append(candidate_offsets[-1] + len(d.candidates or []))
                choice_offsets.append(choice_offsets[-1])
        return {
            "states": states,
            "possible": possible,
            "envelope": np.repeat(env[None, :], n, axis=0),
            "head": np.array([HEADS.index(d.head) for d in self.decisions], dtype=np.int64),
            "action": np.array([d.action for d in self.decisions], dtype=np.int64),
            "reward": np.array([self.rewards[d.seat] for d in self.decisions]),
            "seat": np.array([d.seat for d in self.decisions], dtype=np.int64),
            "game": np.full(n, self.seed, dtype=np.int64),
            "choices": np.concatenate(choice_rows) if choice_rows else np.zeros((0, encode_choices([]).shape[1])),
            "choice_offsets": np.array(choice_offsets, dtype=np.int64),
            "candidates": np.array(candidate_rows, dtype=np.int64),
            "candidate_offsets": np.array(candidate_offsets, dtype=np.int64),
        }


# -- the recording seat ---------------------------------------------------------


def _possible(obs: ClueObservation) -> np.ndarray:
    return np.array([1.0 if obs.mask.is_possible(c, ENVELOPE) else 0.0 for c in ALL_CARDS])


class RecordingCharacter(Character):
    """A `Character` over `DeepNashAgent` that writes down what it drew.

    The movement draw is the agent's own `movement_scores` sampled from
    the agent's RNG, exactly as `DeepNashAgent.choose_destination` does
    it; the suggestion draw is the Character's, bluff coin first, then
    `suggestion_scores` sampled from the Character's RNG. Only the
    honest path of a suggestion is recorded: a bluff is the dial's
    coin, not the policy's choice. The accusation and the card to show
    are the Character's and go unrecorded.
    """

    def __init__(self, weights: dict) -> None:
        super().__init__(DeepNashAgent(weights), TRAINING_PROFILE)
        self.decisions: list = []

    def choose_movement(self, obs: ClueObservation, choices: list, rng: Random):
        del rng
        features = room_features(obs, self.select_action(obs), choices)
        scores = self.agent.movement_scores(obs, choices, features, self.profile)
        index = sample_softmax(scores, self.profile.temperature, self.agent.rng)
        self.decisions.append(Decision(
            obs.my_index, "move", encode_state(obs), _possible(obs), index, choices=encode_choices(features),
        ))
        return choices[index]

    def _pick_suggestion_card(self, obs: ClueObservation, belief, category: list) -> str:
        del belief
        own = [c for c in category if c in obs.own_hand]
        if own and self.rng.random() < self.profile.bluff_rate:
            return self.rng.choice(own)
        candidates, scores = self.suggestion_scores(obs, category)
        index = sample_softmax(scores, self.profile.temperature, self.rng)
        head = "suspect" if list(category) == SUSPECTS else "weapon"
        self.decisions.append(Decision(
            obs.my_index, head, encode_state(obs), _possible(obs), index,
            candidates=[list(category).index(c) for c in candidates],
        ))
        return candidates[index]


# -- seating a rollout --------------------------------------------------------------


def draw_table(seed: int, n_players: int, population: str) -> tuple:
    """The tokens in play and the kind of each seat for one rollout,
    deterministic in `seed`.

    Returns
    -------
    (suspects, kinds) : tuple[tuple[str, ...], list[str]]
        `n_players` tokens in board order, and per seat ``"net"``,
        ``"floor"`` or the token's name (its own character); at least
        one seat is the network.

    Raises
    ------
    ValueError
        On an unknown population.
    """
    if population not in POPULATIONS:
        raise ValueError(f"population must be one of {POPULATIONS}, not {population!r}")
    draw = Random(seed * 7919 + 17)
    chosen = set(draw.sample(SUSPECTS, n_players))
    suspects = tuple(s for s in SUSPECTS if s in chosen)
    if population == "self" or draw.random() < 0.5:
        return suspects, [NET] * n_players
    kinds = []
    for token in suspects:
        options = [NET, FLOOR] + ([token] if token != "Plum" else [])
        kinds.append(draw.choice(options))
    if NET not in kinds:  # a table with nothing to learn from is no rollout
        kinds[draw.randrange(n_players)] = NET
    return suspects, kinds


def play_one(
    weights: dict,
    seed: int,
    n_players: int,
    population: str = "mixed",
    max_turns: int = DEFAULT_MAX_TURNS,
) -> GameTrace:
    """One rollout: a seeded game with the seats `draw_table` gives.

    Every network seat is its own `RecordingCharacter` reset with
    `seed`; a character seat is `build_character(token)` reset with
    `seed`; a floor seat draws from `fill_seed`. Characters get
    `new_game` with the seat kinds as labels and `observe` the envelope
    at the end, as the arena does.
    """
    suspects, kinds = draw_table(seed, n_players, population)
    players: dict = {}
    recorders: dict = {}
    characters: dict = {}
    for seat, kind in enumerate(kinds):
        if kind == NET:
            recorder = RecordingCharacter(weights)
            recorder.reset(seed)
            players[seat] = recorders[seat] = recorder
        elif kind == FLOOR:
            players[seat] = clude_constraints.FloorBot(rng=Random(fill_seed(seed, seat)))
        else:
            character = build_character(kind)
            character.reset(seed)
            players[seat] = characters[seat] = character
    for character in characters.values():
        character.new_game(kinds)
    state, events = engine.run_game(
        n_players, players, seed=seed, max_turns=max_turns,
        observer=clude_constraints.observe, suspects=suspects,
    )
    for character in characters.values():
        character.observe(RevealedOutcome(envelope=state.envelope))
    final = events[-1] if events and isinstance(events[-1], GameOverEvent) else None
    winner = final.winner if final is not None else None
    out = {e.accusation.accuser for e in events if isinstance(e, AccusationEvent) and not e.accusation.correct}
    rewards = [1.0 if seat == winner else -1.0 if seat in out else 0.0 for seat in range(n_players)]
    trace = GameTrace(
        seed=seed, n_players=n_players, kinds=kinds, suspects=suspects,
        rewards=rewards, envelope=tuple(state.envelope), turns=state.turn, winner=winner,
        capped=winner is None and any(state.active),
    )
    for seat in sorted(recorders):
        trace.decisions.extend(recorders[seat].decisions)
    return trace


# -- batches, in a pool or not ---------------------------------------------------------


_WEIGHTS: Optional[dict] = None


def _init_worker(weights: dict) -> None:
    global _WEIGHTS
    _WEIGHTS = weights


def _play_in_worker(args: tuple) -> GameTrace:
    seed, n_players, population, max_turns = args
    return play_one(_WEIGHTS, seed, n_players, population, max_turns)


def rollout_batch(
    weights: dict,
    seeds: list,
    n_players_of,
    population: str = "mixed",
    workers: int = 1,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> list:
    """`play_one` over `seeds`, in this process or a pool of `workers`.

    Parameters
    ----------
    n_players_of : callable or int
        The table size for a seed (``n_players_of(seed)``), or one size
        for all.

    Notes
    -----
    The weights reach each worker once, through the pool's initializer,
    and the work items are module-level functions, so the pool starts
    under Windows' spawn as under fork. The result is the same list
    whatever `workers` is: a test pins serial against parallel.
    """
    size = (lambda seed: n_players_of) if isinstance(n_players_of, int) else n_players_of
    jobs = [(seed, size(seed), population, max_turns) for seed in seeds]
    if workers <= 1:
        _init_worker(weights)
        return [_play_in_worker(job) for job in jobs]
    with multiprocessing.Pool(workers, initializer=_init_worker, initargs=(weights,)) as pool:
        return pool.map(_play_in_worker, jobs, chunksize=max(1, len(jobs) // (4 * workers)))


# -- the two standard tables ------------------------------------------------------------


PLUM_TABLE = ("Plum", "Mustard", "Green")
"""The ladders' table (`docs/strategy-glossary.md`), three seats."""


def evaluate(weights: dict, n_games: int = 24, seed: int = 7007, max_turns: int = 200) -> dict:
    """Plum on `weights`, at his preset, on the two standard tables:
    `DEFAULT_ROSTER` cycling three to six seats and `PLUM_TABLE` at
    three, `n_games` paired games each from `seed`. The loop is the
    arena's per-game body with the agent injected.

    Returns
    -------
    dict
        Per table (``"tuned"`` and ``"plum"``): Plum's ``win_rate`` and
        ``wrong_rate``, the ``mean_turns`` and the ``capped`` fraction,
        and ``games``.
    """
    results = {}
    for name, roster, counts in (("tuned", DEFAULT_ROSTER, (3, 4, 5, 6)), ("plum", PLUM_TABLE, (3,))):
        characters = {label: build_character(label) for label in roster if label in _SUSPECT_SET}
        characters["Plum"] = Character(DeepNashAgent(weights), PRESETS["Plum"])
        for character in characters.values():
            character.reset(seed)
        wins = wrongs = capped = 0
        turns = 0
        for g in range(n_games):
            n_players = counts[g % len(counts)]
            lineup, suspects = seat_lineup(lineup_for_game(roster, g, n_players))
            game_seed = seed + g
            players = {}
            for seat, label in enumerate(lineup):
                if label in characters:
                    players[seat] = characters[label]
                else:
                    players[seat] = clude_constraints.FloorBot(rng=Random(fill_seed(game_seed, seat)))
            for label in set(lineup) & set(characters):
                characters[label].new_game(lineup)
            state, events = engine.run_game(
                n_players, players, seed=game_seed, max_turns=max_turns,
                observer=clude_constraints.observe, suspects=suspects,
            )
            for label in set(lineup) & set(characters):
                characters[label].observe(RevealedOutcome(envelope=state.envelope))
            plum = lineup.index("Plum") if "Plum" in lineup else None
            final = events[-1]
            winner = final.winner if isinstance(final, GameOverEvent) else None
            if plum is not None:
                wins += int(winner == plum)
                wrongs += int(any(
                    isinstance(e, AccusationEvent) and e.accusation.accuser == plum and not e.accusation.correct
                    for e in events
                ))
            capped += int(winner is None and any(state.active))
            turns += state.turn
        results[name] = {
            "games": n_games, "win_rate": wins / n_games, "wrong_rate": wrongs / n_games,
            "mean_turns": turns / n_games, "capped": capped / n_games,
        }
    return results
