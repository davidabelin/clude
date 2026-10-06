"""Gather whole-game Episodes for Plum's policy/value/belief training.

RecordingPlum samples network policies through the real rules engine. Mixed
population games include self-play, other characters and FloorBot. Episodes
carry per-seat encoded states, candidates/actions, envelope, outcome reward
and deduction bits; reward belongs to the recorded seat. Shaping is optional
and defaults to zero because it can reward information without winning.

Workers use deterministic task seeds and return task order. This module uses
NumPy inference, not PyTorch; scripts/train_plum.py owns fitting/export.
See docs/deepnash-plan.md for losses, replay buffer and smoke limitations.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

import clude_constraints
from clude_agents import PRESETS, build_character
from clude_agents.character import N_TRIPLES, Character
from clude_agents.deep_nash import DeepNashAgent, encode_choices, move_scores
from clude_agents.features import room_features
from clude_agents.personality import Profile
from clude_constraints import ENVELOPE
from clude_core import engine
from clude_core.domain import ROOMS, SUSPECTS, WEAPONS
from clude_core.events import GameOverEvent
from clude_core.state import ClueObservation

from .arena import fill_seed, seat_lineup
from .self_play import DEFAULT_PLAYER_COUNTS

__all__ = [
    "CHARACTERS",
    "Episode",
    "KIND_BELIEF",
    "KIND_MOVE",
    "KIND_SUSPECT",
    "KIND_WEAPON",
    "KINDS",
    "NET_LABEL",
    "FLOOR_LABEL",
    "RecordingPlum",
    "RolloutConfig",
    "draw_lineup",
    "play_game",
    "play_games",
]

NET_LABEL = "net"
"""The roster label of a seat played by the network being trained."""
FLOOR_LABEL = "floor"
CHARACTERS: tuple = ("Scarlett", "Mustard", "White", "Green", "Peacock")
"""The other five characters, the rest of the population."""

KIND_MOVE, KIND_SUSPECT, KIND_WEAPON, KIND_BELIEF = 0, 1, 2, 3
KINDS: tuple = ("move", "suspect", "weapon", "belief")
"""What a recorded step is: a movement choice over the legal moves, a
suspect or a weapon drawn for a suggestion, or the observation the
accusation test read, which carries a belief target and no action."""

DEFAULT_MAX_TURNS = 150


@dataclass(frozen=True)
class RolloutConfig:
    """How games are drawn and played.

    Parameters
    ----------
    self_play : float
        Probability that every seat at a table is the network.
    policy_temperature : float
        The training seats' sampler: the softmax of the logits divided
        by this. 1 is the network's own distribution.
    player_counts : tuple[int, ...]
        Table sizes, cycled by game index.
    max_turns : int
        The engine's cap; a capped game rewards nobody.
    profile : Profile
        The dials the recording seat plays with for the decisions that
        stay the `Character`'s (`accuse_threshold`, `bluff_rate`,
        `secrecy`). Plum's preset by default.
    """

    self_play: float = 0.5
    policy_temperature: float = 1.0
    player_counts: tuple = DEFAULT_PLAYER_COUNTS
    max_turns: int = DEFAULT_MAX_TURNS
    profile: Profile = PRESETS["Plum"]


@dataclass
class Episode:
    """One network seat's record of one game.

    Parameters
    ----------
    seed, n_players, seat : int
    lineup : tuple[str, ...]
        Seat -> roster label (`NET_LABEL`, `FLOOR_LABEL` or a character).
    states : np.ndarray
        ``(T, STATE_SIZE)`` float32: the network's input at each step.
    kinds : np.ndarray
        ``(T,)`` int8, one of `KINDS` by index.
    actions : np.ndarray
        ``(T,)`` int16: the index of the option taken, -1 for a belief
        step.
    options : list
        Per step: for a move the ``(n, CHOICE_SIZE)`` float32 matrix of
        the legal moves' features; for a suspect or weapon the int array
        of the honest candidates' indices into `SUSPECTS` or `WEAPONS`;
        None for a belief step.
    gains : np.ndarray
        ``(T,)`` float32: at a belief step, the floor's bits gained
        since this seat's previous belief step, as a fraction of the
        bits in a deal (module docstring); 0 elsewhere.
    envelope : tuple[int, int, int]
        The true (suspect, weapon, room) as indices into their lists.
    reward : float
        +1 won, -1 put out, 0 otherwise.
    turns : int
    won, out : bool
    """

    seed: int
    n_players: int
    seat: int
    lineup: tuple
    states: np.ndarray
    kinds: np.ndarray
    actions: np.ndarray
    options: list
    gains: np.ndarray
    envelope: tuple
    reward: float
    turns: int
    won: bool
    out: bool

    def __len__(self) -> int:
        return len(self.kinds)


def floor_bits(obs: ClueObservation) -> float:
    """How far `obs`'s floor has come, 0 to 1: the bits it has ruled
    out of the 324 triples over the bits in a deal, the certainty tag's
    scale for a uniform belief over what the floor still allows."""
    possible = 1
    for category in (SUSPECTS, WEAPONS, ROOMS):
        possible *= sum(1 for c in category if obs.mask.is_possible(c, ENVELOPE))
    return 1.0 - math.log(possible) / math.log(N_TRIPLES)


def _softmax(logits: np.ndarray, temperature: float) -> np.ndarray:
    z = logits / temperature
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


class RecordingPlum(Character):
    """The training seat: Plum's `Character` over the given weights,
    sampling moves and suggestion cards from the network's distribution
    and recording every step (module docstring).

    Parameters
    ----------
    weights : dict
        The network (`clude_agents.deep_nash.WEIGHT_SHAPES`).
    profile : Profile
    policy_temperature : float
    """

    def __init__(self, weights: dict, profile: Profile, policy_temperature: float = 1.0) -> None:
        super().__init__(DeepNashAgent(weights), profile)
        self.agent: DeepNashAgent
        self.policy_temperature = policy_temperature
        self.steps: list = []
        self._bits = 0.0

    def _record(self, obs: ClueObservation, kind: int, options, action: int, gain: float = 0.0) -> None:
        self.steps.append((np.asarray(self.agent.heads(obs)["state"], dtype=np.float32), kind, options, action, gain))

    def choose_movement(self, obs: ClueObservation, choices: list, rng: random.Random) -> engine.MoveChoice:
        del rng
        features = room_features(obs, self.select_action(obs), choices)
        rows = encode_choices(features)
        logits = move_scores(self.agent.weights, self.agent.heads(obs)["hidden"], rows)
        probs = _softmax(logits, self.policy_temperature)
        action = self.rng.choices(range(len(choices)), weights=probs.tolist(), k=1)[0]
        self._record(obs, KIND_MOVE, rows.astype(np.float32), action)
        return features[action].choice

    def _pick_suggestion_card(self, obs: ClueObservation, belief, category: list) -> str:
        """As `Character._pick_suggestion_card`: the bluff coin flip
        first, then a draw over the honest candidates, here from the
        network's distribution rather than the sharpening sampler."""
        del belief
        own = [c for c in category if c in obs.own_hand]
        if own and self.rng.random() < self.profile.bluff_rate:
            return self.rng.choice(own)
        candidates = [c for c in category if c not in obs.own_hand]
        kind, head = (KIND_SUSPECT, "suspect") if list(category) == SUSPECTS else (KIND_WEAPON, "weapon")
        idx = np.asarray([list(category).index(c) for c in candidates], dtype=np.int16)
        probs = _softmax(self.agent.heads(obs)[head][idx], self.policy_temperature)
        action = self.rng.choices(range(len(candidates)), weights=probs.tolist(), k=1)[0]
        self._record(obs, kind, idx, action)
        return candidates[action]

    def choose_accusation(self, obs: ClueObservation, rng: random.Random) -> Optional[tuple]:
        bits = floor_bits(obs)
        self._record(obs, KIND_BELIEF, None, -1, gain=bits - self._bits)
        self._bits = bits
        return super().choose_accusation(obs, rng)


def draw_lineup(rng: random.Random, n_players: int, self_play: float) -> list:
    """The roster labels for one game's seats, before seating (module
    docstring): all `NET_LABEL` with probability `self_play`, otherwise
    a draw per seat from the network, the characters not yet drawn and
    the floor bot, with at least one network seat."""
    if rng.random() < self_play:
        return [NET_LABEL] * n_players
    pool = [NET_LABEL, FLOOR_LABEL] + list(CHARACTERS)
    lineup = []
    for _ in range(n_players):
        label = rng.choice(pool)
        if label in CHARACTERS:
            pool.remove(label)
        lineup.append(label)
    if NET_LABEL not in lineup:
        lineup[rng.randrange(n_players)] = NET_LABEL
    return lineup


def play_game(weights: dict, seed: int, game_index: int, config: RolloutConfig = RolloutConfig()) -> list:
    """Play one game and return an `Episode` per network seat.

    The table is drawn from ``random.Random(seed)`` (not the engine's
    RNG, which `seed` also seeds, so the deal and the dice are those of
    any other game at this seed), its size ``config.player_counts[
    game_index % len]``. Characters are built as the arena builds them,
    reset with `seed`; floor bots and network seats get private RNGs
    from `fill_seed`.
    """
    rng = random.Random(seed)
    n_players = config.player_counts[game_index % len(config.player_counts)]
    labels, suspects = seat_lineup(draw_lineup(rng, n_players, config.self_play))
    players: dict = {}
    recorders: dict = {}
    for seat, label in enumerate(labels):
        if label == NET_LABEL:
            plum = RecordingPlum(weights, config.profile, config.policy_temperature)
            plum.reset(fill_seed(seed, seat))
            players[seat] = recorders[seat] = plum
        elif label == FLOOR_LABEL:
            players[seat] = clude_constraints.FloorBot(rng=random.Random(fill_seed(seed, seat)))
        else:
            character = build_character(label)
            character.reset(seed)
            players[seat] = character
    for seat, player in players.items():
        if isinstance(player, Character):
            player.new_game(labels)
    state, events = engine.run_game(
        n_players, players, seed=seed, max_turns=config.max_turns,
        observer=clude_constraints.observe, suspects=suspects,
    )
    final = events[-1]
    winner = final.winner if isinstance(final, GameOverEvent) else None
    envelope = (
        SUSPECTS.index(state.envelope[0]), WEAPONS.index(state.envelope[1]), ROOMS.index(state.envelope[2]),
    )
    episodes = []
    for seat, plum in recorders.items():
        won = winner == seat
        out = not won and not state.active[seat]
        steps = plum.steps
        episodes.append(Episode(
            seed=seed,
            n_players=n_players,
            seat=seat,
            lineup=tuple(labels),
            states=np.stack([s[0] for s in steps]) if steps else np.zeros((0, 0), dtype=np.float32),
            kinds=np.asarray([s[1] for s in steps], dtype=np.int8),
            actions=np.asarray([s[3] for s in steps], dtype=np.int16),
            options=[s[2] for s in steps],
            gains=np.asarray([s[4] for s in steps], dtype=np.float32),
            envelope=envelope,
            reward=1.0 if won else -1.0 if out else 0.0,
            turns=state.turn,
            won=won,
            out=out,
        ))
    return episodes


def play_games(weights: dict, seeds: list, first_index: int = 0, config: RolloutConfig = RolloutConfig()) -> list:
    """`play_game` over `seeds` in order, game indices counting from
    `first_index` (for the table-size cycle); the episodes of every
    game in one list. The process pool's task."""
    episodes: list = []
    for offset, seed in enumerate(seeds):
        episodes.extend(play_game(weights, seed, first_index + offset, config))
    return episodes


def _play_task(args: tuple) -> list:
    """`play_games` unpacked, for `multiprocessing.Pool.imap_unordered`."""
    return play_games(*args)


def rollout_tasks(weights: dict, seeds: list, chunk: int, config: RolloutConfig) -> list:
    """Split `seeds` into tasks of `chunk` games for `_play_task`."""
    return [
        (weights, seeds[i:i + chunk], i, config)
        for i in range(0, len(seeds), chunk)
    ]


@dataclass
class RolloutStats:
    """What a batch of episodes says about the games behind it."""

    games: int = 0
    episodes: int = 0
    steps: int = 0
    turns: list = field(default_factory=list)
    net_wins: int = 0
    net_outs: int = 0
    mixed_episodes: int = 0
    mixed_wins: int = 0

    @classmethod
    def of(cls, episodes: list) -> "RolloutStats":
        """Tally `episodes`: games are counted once however many network
        seats they held, wins and outs per episode."""
        stats = cls()
        seen: set = set()
        for ep in episodes:
            stats.episodes += 1
            stats.steps += len(ep)
            stats.net_wins += int(ep.won)
            stats.net_outs += int(ep.out)
            if ep.seed not in seen:
                seen.add(ep.seed)
                stats.turns.append(ep.turns)
            if any(label != NET_LABEL for label in ep.lineup):
                stats.mixed_episodes += 1
                stats.mixed_wins += int(ep.won)
        stats.games = len(seen)
        return stats

    def to_dict(self) -> dict:
        """The tally as the curve file's ``rollout`` entry: counts, mean
        turns, the network's win and out rates, and its win rate in the
        mixed games alone (None when there were none)."""
        return {
            "games": self.games,
            "episodes": self.episodes,
            "steps": self.steps,
            "mean_turns": sum(self.turns) / len(self.turns) if self.turns else 0.0,
            "net_win_rate": self.net_wins / self.episodes if self.episodes else 0.0,
            "net_out_rate": self.net_outs / self.episodes if self.episodes else 0.0,
            "mixed_win_rate": self.mixed_wins / self.mixed_episodes if self.mixed_episodes else None,
            "mixed_episodes": self.mixed_episodes,
        }
