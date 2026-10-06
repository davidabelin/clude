"""Plum's NumPy policy/value/belief network over the deduction floor.

A shared hidden state feeds masked envelope beliefs, legal-move scores,
honest suspect/weapon scores and a value estimate. Character retains
bluffing, accusation and card-show decisions; curiosity is inert for the
network movement hook. Training uses a DeepNash variant described in
docs/deepnash-plan.md, not an equilibrium guarantee for multiplayer Clue.

weights/plum.npz is loaded once and still holds seeded initial weights;
smoke checkpoints have not been exported. Determinism depends on this file,
seed and memory. Float64 inference rounds scores to SCORE_DECIMALS before
sampling/argmax to limit platform-dependent picks. Card/holder iteration
uses stable order. PyTorch is needed only by the separate trainer.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

import numpy as np

from clude_agents.base import CATEGORIES, ClueBelief, SeededAgentMixin, mask_and_normalize
from clude_agents.features import sample_softmax
from clude_agents.personality import Profile
from clude_constraints import ENVELOPE
from clude_core.domain import ALL_CARDS, ROOMS, SUSPECTS, WEAPONS
from clude_core.engine import MoveChoice
from clude_core.state import ClueObservation

__all__ = [
    "CHOICE_SIZE",
    "DeepNashAgent",
    "HIDDEN",
    "MOVE_HIDDEN",
    "SCORE_DECIMALS",
    "STATE_SIZE",
    "WEIGHTS_PATH",
    "WEIGHT_SHAPES",
    "default_weights",
    "encode_choices",
    "encode_state",
    "forward",
    "init_weights",
    "load_weights",
    "move_scores",
    "playing_with",
    "save_weights",
]

MAX_SEATS = 6
N_HOLDER_SLOTS = MAX_SEATS + 1
"""Per card: six seats counted from this one round the table, then the
envelope. A table smaller than six leaves the spare seat slots at 0."""
CARD_FEATURES = 16
SEAT_FEATURES = 3
GLOBAL_FEATURES = 2
STATE_SIZE = len(ALL_CARDS) * CARD_FEATURES + MAX_SEATS * SEAT_FEATURES + GLOBAL_FEATURES
"""356: what `encode_state` returns."""
CHOICE_SIZE = 3 + 1 + 3 + len(ROOMS) + len(ROOMS)
"""25 per legal move: information, proximity, steps; lands in a room;
the kind (stay, secret passage, move) one-hot; the target room one-hot;
the landing room one-hot (all zero on a corridor square)."""
HIDDEN = 128
MOVE_HIDDEN = 64
SCORE_DECIMALS = 9
"""Scores are rounded to this many places before any pick is made."""

MAX_TURN_FOR_NORMALIZATION = 50.0
COUNT_SCALE = 5.0
KINDS = ("stay", "secret_passage", "move")

WEIGHTS_PATH = Path(__file__).with_name("weights") / "plum.npz"
INIT_SEED = 2026
"""`init_weights`'s seed for the committed file before training."""

WEIGHT_SHAPES: dict = {
    "trunk1_w": (STATE_SIZE, HIDDEN), "trunk1_b": (HIDDEN,),
    "trunk2_w": (HIDDEN, HIDDEN), "trunk2_b": (HIDDEN,),
    "belief_w": (HIDDEN, len(ALL_CARDS)), "belief_b": (len(ALL_CARDS),),
    "suspect_w": (HIDDEN, len(SUSPECTS)), "suspect_b": (len(SUSPECTS),),
    "weapon_w": (HIDDEN, len(WEAPONS)), "weapon_b": (len(WEAPONS),),
    "value_w": (HIDDEN, 1), "value_b": (1,),
    "move1_w": (HIDDEN + CHOICE_SIZE, MOVE_HIDDEN), "move1_b": (MOVE_HIDDEN,),
    "move2_w": (MOVE_HIDDEN, 1), "move2_b": (1,),
}
"""Every array in the weights file and its shape: the one place the
network's layout is spelled out, which `scripts/train_plum.py` mirrors
in torch and `save_weights` checks."""

_HEAD_NAMES = ("belief", "suspect", "weapon", "value", "move2")


# -- encoding ------------------------------------------------------------------


def _relative_slot(seat: int, obs: ClueObservation) -> int:
    """Seat `seat`'s slot counted from this one round the table: 0 is
    this seat, 1 the next to play, and so on."""
    return (seat - obs.my_index) % obs.n_players


def encode_state(obs: ClueObservation) -> np.ndarray:
    """One observation as the trunk's input, `STATE_SIZE` floats.

    Per card, in `ALL_CARDS` order: which holders the floor still allows
    (the seats counted from this one, then the envelope); resolved at
    all, resolved to the envelope, resolved to another seat; how many
    open or-constraints name it; how often it has been named, named and
    gone unrefuted, by how many distinct suggesters, and how often
    beside cards already located (Mustard's features, scaled to [0, 1]);
    and whether it is in this hand. Per seat, from this one round: still
    in the game, hand size, and whether the slot is a seat at all. Then
    the turn and the table size.

    Raises
    ------
    ValueError
        Without a mask: this agent reads the floor.
    """
    mask = obs.mask
    if mask is None:
        raise ValueError("DeepNashAgent needs a masked observation (observer=clude_constraints.observe)")
    x = np.zeros(STATE_SIZE)
    named: dict = {c: [] for c in ALL_CARDS}
    for s in obs.suggestion_log:
        for card in (s.suspect, s.weapon, s.room):
            named[card].append(s)
    or_counts = {c: 0 for c in ALL_CARDS}
    for cards, _holder in mask.or_constraints:
        for card in cards:
            if card in or_counts:
                or_counts[card] += 1
    i = 0
    for card in ALL_CARDS:
        holders = mask.possible_holders[card]
        for seat in range(obs.n_players):
            if seat in holders:
                x[i + _relative_slot(seat, obs)] = 1.0
        if ENVELOPE in holders:
            x[i + MAX_SEATS] = 1.0
        resolved = mask.holder_of(card)
        x[i + 7] = 1.0 if resolved is not None else 0.0
        x[i + 8] = 1.0 if resolved == ENVELOPE else 0.0
        x[i + 9] = 1.0 if resolved is not None and resolved != ENVELOPE and resolved != obs.my_index else 0.0
        x[i + 10] = min(or_counts[card] / 3.0, 1.0)
        log = named[card]
        x[i + 11] = min(len(log) / COUNT_SCALE, 1.0)
        x[i + 12] = min(sum(1 for s in log if s.refuter is None) / COUNT_SCALE, 1.0)
        x[i + 13] = min(len({s.suggester for s in log}) / COUNT_SCALE, 1.0)
        if log:
            beside = [
                sum(1 for other in (s.suspect, s.weapon, s.room) if other != card and mask.holder_of(other) is not None)
                for s in log
            ]
            x[i + 14] = sum(beside) / (2.0 * len(beside))
        x[i + 15] = 1.0 if card in obs.own_hand else 0.0
        i += CARD_FEATURES
    for seat in range(obs.n_players):
        j = i + SEAT_FEATURES * _relative_slot(seat, obs)
        x[j] = 1.0 if obs.active_players[seat] else 0.0
        x[j + 1] = obs.hand_sizes.get(seat, 0) / 6.0
        x[j + 2] = 1.0
    i += MAX_SEATS * SEAT_FEATURES
    x[i] = min(obs.turn / MAX_TURN_FOR_NORMALIZATION, 1.0)
    x[i + 1] = obs.n_players / MAX_SEATS
    return x


def encode_choices(features: list) -> np.ndarray:
    """The legal moves as a ``(len(features), CHOICE_SIZE)`` matrix, one
    row per `ChoiceFeatures` in order: the shared information and
    proximity numbers, the steps to the target (scaled), whether the
    move lands in a room this turn, the kind, the target room and the
    landing room."""
    rows = np.zeros((len(features), CHOICE_SIZE))
    for r, f in enumerate(features):
        rows[r, 0] = f.information
        rows[r, 1] = f.proximity
        rows[r, 2] = min(f.steps_to_target / 10.0, 1.0)
        rows[r, 3] = 1.0 if f.room is not None else 0.0
        rows[r, 4 + KINDS.index(f.choice.kind)] = 1.0
        rows[r, 7 + ROOMS.index(f.target)] = 1.0
        if f.room is not None:
            rows[r, 7 + len(ROOMS) + ROOMS.index(f.room)] = 1.0
    return rows


# -- the network --------------------------------------------------------------


def _relu(z: np.ndarray) -> np.ndarray:
    return np.maximum(z, 0.0)


def _softmax(logits: np.ndarray) -> np.ndarray:
    z = logits - logits.max()
    e = np.exp(z)
    return e / e.sum()


def _rounded(values: np.ndarray) -> list:
    """Scores as plain floats, rounded so a pick never depends on the
    last bits of a platform's arithmetic."""
    return [round(float(v), SCORE_DECIMALS) for v in values]


def forward(weights: dict, x: np.ndarray) -> dict:
    """The trunk and the per-observation heads for one encoded state.

    Returns
    -------
    dict
        ``hidden`` (the trunk's output, what `move_scores` reads),
        ``belief`` (21 logits), ``suspect`` and ``weapon`` (6 logits
        each), ``value`` (a float in [-1, 1]).
    """
    h = _relu(x @ weights["trunk1_w"] + weights["trunk1_b"])
    h = _relu(h @ weights["trunk2_w"] + weights["trunk2_b"])
    return {
        "hidden": h,
        "belief": h @ weights["belief_w"] + weights["belief_b"],
        "suspect": h @ weights["suspect_w"] + weights["suspect_b"],
        "weapon": h @ weights["weapon_w"] + weights["weapon_b"],
        "value": float(np.tanh(h @ weights["value_w"] + weights["value_b"])[0]),
    }


def move_scores(weights: dict, hidden: np.ndarray, choices: np.ndarray) -> np.ndarray:
    """The move head over every row of `choices` (from `encode_choices`)
    given the trunk's `hidden`: one logit per legal move."""
    joined = np.concatenate([np.repeat(hidden[None, :], len(choices), axis=0), choices], axis=1)
    z = _relu(joined @ weights["move1_w"] + weights["move1_b"])
    return (z @ weights["move2_w"] + weights["move2_b"])[:, 0]


# -- the weights file ---------------------------------------------------------


def init_weights(seed: int = INIT_SEED, head_scale: float = 0.01) -> dict:
    """A fresh network: He-scaled normal draws for the trunk and the
    move scorer's first layer, the heads scaled down by `head_scale` so
    an untrained Plum's every distribution starts close to uniform.
    Deterministic in `seed`."""
    rng = np.random.default_rng(seed)
    weights = {}
    for name, shape in WEIGHT_SHAPES.items():
        if name.endswith("_b"):
            weights[name] = np.zeros(shape)
            continue
        scale = np.sqrt(2.0 / shape[0])
        if name.split("_")[0] in _HEAD_NAMES:
            scale *= head_scale
        weights[name] = rng.normal(0.0, scale, size=shape)
    return weights


def save_weights(weights: dict, path: Path = WEIGHTS_PATH) -> None:
    """Write `weights` as float32 arrays, checking every name and shape
    against `WEIGHT_SHAPES` first."""
    _check(weights)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **{name: np.asarray(weights[name], dtype=np.float32) for name in WEIGHT_SHAPES})


def load_weights(path: Path = WEIGHTS_PATH) -> dict:
    """Read a weights file back as float64 arrays, checked against
    `WEIGHT_SHAPES`."""
    with np.load(path) as data:
        weights = {name: np.asarray(data[name], dtype=np.float64) for name in data.files}
    _check(weights)
    return weights


def _check(weights: dict) -> None:
    missing = set(WEIGHT_SHAPES) - set(weights)
    extra = set(weights) - set(WEIGHT_SHAPES)
    if missing or extra:
        raise ValueError(f"weights file layout: missing {sorted(missing)}, unexpected {sorted(extra)}")
    for name, shape in WEIGHT_SHAPES.items():
        if tuple(np.shape(weights[name])) != shape:
            raise ValueError(f"{name}: shape {np.shape(weights[name])}, expected {shape}")


_DEFAULT: Optional[dict] = None


def default_weights() -> dict:
    """The committed weights, read once per process (or the weights
    `playing_with` has installed for the duration of its block)."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = load_weights()
    return _DEFAULT


@contextmanager
def playing_with(weights: dict) -> Iterator[None]:
    """Make `weights` what every `DeepNashAgent` built without explicit
    weights plays with, for the duration of the block: the registry's
    Plum, and Green's Plum arm. The training script evaluates a
    checkpoint through the ordinary arena and benchmark this way. The
    previous weights (or the not-yet-loaded file) are restored on exit."""
    global _DEFAULT
    _check(weights)
    previous = _DEFAULT
    _DEFAULT = weights
    try:
        yield
    finally:
        _DEFAULT = previous


# -- the agent ----------------------------------------------------------------


class DeepNashAgent(SeededAgentMixin):
    """Plum: the network above as an `AgentProtocol` agent.

    Parameters
    ----------
    weights : dict or None
        The network to play with; the committed file by default. The
        training script passes checkpoints here to evaluate them.

    Notes
    -----
    The trunk runs once per observation object and its output is kept
    for the hooks, which the `Character` calls with the same
    observation it passed to `select_action`. The only random draw is
    `choose_destination`'s softmax over the move scores, from this
    agent's own RNG at the profile's temperature, so arenas stay paired.
    """

    name = "Plum"

    def __init__(self, weights: Optional[dict] = None) -> None:
        super().__init__()
        self.weights = default_weights() if weights is None else weights
        self._cached_obs: Optional[ClueObservation] = None
        self._cached: Optional[dict] = None

    def reset(self, seed: "int | None") -> None:
        super().reset(seed)
        self._cached_obs = None
        self._cached = None

    def heads(self, obs: ClueObservation) -> dict:
        """`forward` for `obs`, computed once per observation object and
        kept for the hooks; the dict also carries ``state``, the encoded
        input, which the training rollout records."""
        if obs is not self._cached_obs:
            x = encode_state(obs)
            self._cached = forward(self.weights, x)
            self._cached["state"] = x
            self._cached_obs = obs
        return self._cached

    def select_action(self, obs: ClueObservation) -> ClueBelief:
        """The belief head, masked and renormalised; `extra` carries
        ``method: "policy"`` and the value head."""
        heads = self.heads(obs)
        logits = heads["belief"]
        raw = {}
        for category in CATEGORIES:
            idx = [ALL_CARDS.index(c) for c in category]
            probs = _softmax(logits[idx])
            raw.update({c: round(float(p), SCORE_DECIMALS) for c, p in zip(category, probs)})
        return ClueBelief(
            probabilities=mask_and_normalize(raw, obs.mask),
            extra={"method": "policy", "value": round(heads["value"], 4)},
        )

    def movement_scores(self, obs: ClueObservation, choices: list, features: list, profile: Profile) -> list:
        """The move head as a distribution over `choices`, in order
        (the `AgentProtocol` hook; `profile` is unused, since the
        network learned its own curiosity)."""
        del choices, profile
        logits = move_scores(self.weights, self.heads(obs)["hidden"], encode_choices(features))
        return _rounded(_softmax(logits))

    def choose_destination(
        self, obs: ClueObservation, legal_moves: list, room_features: list, profile: Profile
    ) -> MoveChoice:
        """A softmax draw over `movement_scores` at the profile's
        temperature, from this agent's RNG."""
        scores = self.movement_scores(obs, legal_moves, room_features, profile)
        return room_features[sample_softmax(scores, profile.temperature, self.rng)].choice

    def suggestion_scores(self, obs: ClueObservation, candidates: list, category: list) -> list:
        """The suspect or weapon head as a distribution over the honest
        `candidates`, in order (the `AgentProtocol` hook)."""
        head = "suspect" if category is SUSPECTS or list(category) == SUSPECTS else "weapon"
        logits = self.heads(obs)[head]
        idx = [list(category).index(c) for c in candidates]
        return _rounded(_softmax(logits[idx]))

    def observe(self, transition: Any) -> None:
        """Nothing to learn at the table: training is offline."""
        del transition
