"""Mustard -- decision tree trained on self-play game logs.

Built fresh (no legacy basis); needed a headless engine plus self-play to
train on, which Phase 1 already provides. A hand-rolled CART-style
regression tree (Gini-guided binary splits, smoothed leaf means) is
trained once, per Mustard's character: pattern-matches what self-play
looks like, and can be confidently wrong on a deal that doesn't
resemble that training distribution -- e.g. once real LLM/human play
replaces bots.

Notes
-----
Training data comes from `clude_training.self_play.generate_snapshots`
(Phase 4). Since Phase 5b the default regime is `FloorBot` self-play
(`training_bot="floor"`, docs/phase5-plan.md 4.1): games that end by
deduction and carry information throughout, instead of the `RandomBot`
plateau the Phase 4 tree learned. Two features were added at the same
time that only smarter play makes informative: how many distinct
suggesters have named a card, and how often it was named alongside
cards the floor has already located (a probe). Retraining on richer
play later (Phase 7's logbooks) is expected to change his behavior,
not just his accuracy.

Leaf values are m-estimates, ``(positives + m * base_rate) / (n + m)``
with `smoothing_m` rows of the training set's base rate mixed in, so a
leaf with no positive rows predicts a small number rather than exactly
0 (Phase 5b, docs/phase5-plan.md 4.2). Hard zeros accounted for 69% of
Mustard's Phase 4 log-loss and, once a character accuses on a product
of category maxima, would have read as certainty. He stays
miscalibrated -- that is the character -- but never *impossible*.

The tree is trained lazily on first use and cached at module level
(keyed by its hyperparameters), so repeated `DecisionTreeAgent()`
construction -- e.g. inside Green's ensemble, `clude_agents/bandit.py`
-- doesn't retrain from scratch each time.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from clude_agents.base import CATEGORIES, ClueBelief, SeededAgentMixin, mask_and_normalize
from clude_core.state import ClueObservation
from clude_training.self_play import DEFAULT_BOT, generate_snapshots

DEFAULT_N_TRAINING_GAMES = 25
DEFAULT_TRAINING_SEED = 2026
DEFAULT_CHECKPOINTS: tuple = (0.5, 1.0)
DEFAULT_MAX_DEPTH = 6
DEFAULT_MIN_SAMPLES_LEAF = 20
DEFAULT_TRAINING_BOT = DEFAULT_BOT
DEFAULT_SMOOTHING_M = 3.0
MAX_TURN_FOR_NORMALIZATION = 50.0

# Positional names for the tuple `_features` returns, in order -- the only
# place the feature layout is spelled out, so tree inspection tooling
# (`render_tree`, `summarize_tree`, the `train-mustard` CLI) stays in sync.
FEATURE_NAMES: tuple = (
    "possible_holders_frac",
    "or_constraint_involvement",
    "times_named_unrefuted",
    "times_named_total",
    "turn_fraction",
    "category_size_frac",
    "distinct_namers",
    "named_beside_located",
)

Row = tuple  # tuple[tuple[float, ...], int] -- (features, label)


def _features(obs: ClueObservation, mask, card: str, category: list) -> tuple:
    possible_holders_frac = len(mask.possible_holders[card]) / (obs.n_players + 1)
    or_constraint_involvement = sum(1 for cards, _h in mask.or_constraints if card in cards)
    naming = [s for s in obs.suggestion_log if card in s.cards()]
    times_named_unrefuted = sum(1 for s in naming if s.refuter is None)
    times_named_total = len(naming)
    turn_fraction = min(obs.turn / MAX_TURN_FOR_NORMALIZATION, 1.0)
    category_size_frac = len(category) / 9.0
    distinct_namers = len({s.suggester for s in naming})
    beside_located = [
        sum(1 for other in s.cards() if other != card and mask.holder_of(other) is not None)
        for s in naming
    ]
    named_beside_located = sum(beside_located) / len(beside_located) if beside_located else 0.0
    return (
        possible_holders_frac,
        float(or_constraint_involvement),
        float(times_named_unrefuted),
        float(times_named_total),
        turn_fraction,
        category_size_frac,
        float(distinct_namers),
        named_beside_located,
    )


def _generate_training_rows(n_games: int, seed: int, checkpoints: tuple, bot: str) -> list:
    rows: list = []
    for snap in generate_snapshots(n_games, seed, checkpoints=checkpoints, bot=bot):
        mask = snap.obs.mask
        for category in CATEGORIES:
            for card in category:
                if mask.holder_of(card) is not None:
                    continue
                label = 1 if card in snap.envelope else 0
                rows.append((_features(snap.obs, mask, card, category), label))
    return rows


@dataclass
class _TreeNode:
    is_leaf: bool
    prediction: float = 0.0
    feature_index: int = -1
    threshold: float = 0.0
    left: "Optional[_TreeNode]" = None
    right: "Optional[_TreeNode]" = None
    n_samples: int = 0


def _gini(labels: list) -> float:
    if not labels:
        return 0.0
    p = sum(labels) / len(labels)
    return 2 * p * (1 - p)


def _best_split(rows: list, n_features: int):
    parent_gini = _gini([y for _x, y in rows])
    n = len(rows)
    best = None
    for fi in range(n_features):
        values = sorted({x[fi] for x, _y in rows})
        for a, b in zip(values, values[1:]):
            threshold = (a + b) / 2
            left = [(x, y) for x, y in rows if x[fi] <= threshold]
            right = [(x, y) for x, y in rows if x[fi] > threshold]
            if not left or not right:
                continue
            weighted = (
                len(left) * _gini([y for _x, y in left])
                + len(right) * _gini([y for _x, y in right])
            ) / n
            gain = parent_gini - weighted
            if best is None or gain > best[0]:
                best = (gain, fi, threshold)
    return best


def _leaf_value(labels: list, base_rate: float, smoothing_m: float) -> float:
    """m-estimate of the leaf's positive rate: `smoothing_m` phantom rows
    at `base_rate` mixed into the observed labels. With m = 0 this is the
    plain mean (or `base_rate` for an empty leaf)."""
    n = len(labels)
    if n + smoothing_m <= 0:
        return base_rate
    return (sum(labels) + smoothing_m * base_rate) / (n + smoothing_m)


def _build_tree(
    rows: list,
    depth: int,
    max_depth: int,
    min_samples_leaf: int,
    smoothing_m: float = DEFAULT_SMOOTHING_M,
    base_rate: Optional[float] = None,
) -> _TreeNode:
    """Grow a tree. `base_rate` is the whole training set's positive
    rate, fixed at the root (computed from `rows` when None) and passed
    down unchanged so every leaf is smoothed toward the same prior."""
    labels = [y for _x, y in rows]
    if base_rate is None:
        base_rate = sum(labels) / len(labels) if labels else 0.5
    prediction = _leaf_value(labels, base_rate, smoothing_m)
    if (
        not rows
        or depth >= max_depth
        or len(rows) < 2 * min_samples_leaf
        or len(set(labels)) <= 1
    ):
        return _TreeNode(is_leaf=True, prediction=prediction, n_samples=len(rows))

    split = _best_split(rows, n_features=len(rows[0][0]))
    if split is None:
        return _TreeNode(is_leaf=True, prediction=prediction, n_samples=len(rows))

    _gain, fi, threshold = split
    left_rows = [(x, y) for x, y in rows if x[fi] <= threshold]
    right_rows = [(x, y) for x, y in rows if x[fi] > threshold]
    return _TreeNode(
        is_leaf=False,
        feature_index=fi,
        threshold=threshold,
        left=_build_tree(left_rows, depth + 1, max_depth, min_samples_leaf, smoothing_m, base_rate),
        right=_build_tree(right_rows, depth + 1, max_depth, min_samples_leaf, smoothing_m, base_rate),
        n_samples=len(rows),
    )


def _predict(node: _TreeNode, x: tuple) -> float:
    while not node.is_leaf:
        node = node.left if x[node.feature_index] <= node.threshold else node.right
    return node.prediction


@dataclass(frozen=True)
class TreeSummary:
    """Shape statistics for one trained tree, for inspection tooling.

    Parameters
    ----------
    n_nodes : int
        Internal nodes plus leaves.
    n_leaves : int
    depth : int
        Longest root-to-leaf path in edges; 0 for a single-leaf tree.
    feature_use : dict[str, int]
        How many internal nodes split on each feature, keyed by
        `FEATURE_NAMES`. A feature the tree never splits on is absent.
    leaf_predictions : tuple[float, ...]
        Every leaf's smoothed mean label, ascending -- how spread out
        the tree's possible outputs are.
    """

    n_nodes: int
    n_leaves: int
    depth: int
    feature_use: dict
    leaf_predictions: tuple


def summarize_tree(node: _TreeNode) -> TreeSummary:
    """Walk a tree and collect its `TreeSummary`."""
    feature_use: dict = {}
    leaves: list = []
    n_nodes = 0
    max_depth = 0

    def walk(n: _TreeNode, depth: int) -> None:
        nonlocal n_nodes, max_depth
        n_nodes += 1
        max_depth = max(max_depth, depth)
        if n.is_leaf:
            leaves.append(n.prediction)
            return
        name = FEATURE_NAMES[n.feature_index]
        feature_use[name] = feature_use.get(name, 0) + 1
        walk(n.left, depth + 1)
        walk(n.right, depth + 1)

    walk(node, 0)
    return TreeSummary(
        n_nodes=n_nodes,
        n_leaves=len(leaves),
        depth=max_depth,
        feature_use=feature_use,
        leaf_predictions=tuple(sorted(leaves)),
    )


def render_tree(node: _TreeNode, indent: str = "  ") -> str:
    """Render a tree as indented text, one node per line.

    Internal nodes print as ``feature <= threshold`` with the left (true)
    branch first; leaves print their prediction and how many training
    rows reached them.
    """
    lines: list = []

    def walk(n: _TreeNode, depth: int) -> None:
        pad = indent * depth
        if n.is_leaf:
            lines.append(f"{pad}leaf p={n.prediction:.3f} (n={n.n_samples})")
            return
        lines.append(
            f"{pad}{FEATURE_NAMES[n.feature_index]} <= {n.threshold:.3f} (n={n.n_samples})"
        )
        walk(n.left, depth + 1)
        walk(n.right, depth + 1)

    walk(node, 0)
    return "\n".join(lines)


_ROWS_CACHE: dict = {}
_TREE_CACHE: dict = {}


def training_rows(
    n_training_games: int, training_seed: int, checkpoints: tuple, bot: str = DEFAULT_TRAINING_BOT
) -> list:
    """The (features, label) rows Mustard trains on for these settings,
    generated once and cached at module level. Exposed so tooling can
    inspect the training set (size, label balance) without retraining."""
    rows_key = (n_training_games, training_seed, checkpoints, bot)
    if rows_key not in _ROWS_CACHE:
        _ROWS_CACHE[rows_key] = _generate_training_rows(
            n_training_games, training_seed, checkpoints, bot
        )
    return _ROWS_CACHE[rows_key]


def _cached_tree(
    n_training_games: int, training_seed: int, checkpoints: tuple,
    max_depth: int, min_samples_leaf: int, bot: str, smoothing_m: float,
) -> _TreeNode:
    rows = training_rows(n_training_games, training_seed, checkpoints, bot)
    tree_key = (
        n_training_games, training_seed, checkpoints, max_depth, min_samples_leaf, bot, smoothing_m,
    )
    if tree_key not in _TREE_CACHE:
        _TREE_CACHE[tree_key] = _build_tree(
            rows, depth=0, max_depth=max_depth, min_samples_leaf=min_samples_leaf,
            smoothing_m=smoothing_m,
        )
    return _TREE_CACHE[tree_key]


class DecisionTreeAgent(SeededAgentMixin):
    """Pattern-matches self-play history; confident, even when the
    pattern doesn't apply.

    Parameters
    ----------
    n_training_games, training_seed, checkpoints
        Passed to `generate_snapshots` to build the training rows.
    max_depth, min_samples_leaf
        Tree growth limits.
    training_bot : str
        Self-play regime the rows come from (`self_play.BOT_KINDS`).
    smoothing_m : float
        m-estimate weight for leaf values; 0 restores plain means (and
        hard zeros).
    """

    name = "Mustard"

    def __init__(
        self,
        n_training_games: int = DEFAULT_N_TRAINING_GAMES,
        training_seed: int = DEFAULT_TRAINING_SEED,
        checkpoints: tuple = DEFAULT_CHECKPOINTS,
        max_depth: int = DEFAULT_MAX_DEPTH,
        min_samples_leaf: int = DEFAULT_MIN_SAMPLES_LEAF,
        training_bot: str = DEFAULT_TRAINING_BOT,
        smoothing_m: float = DEFAULT_SMOOTHING_M,
    ) -> None:
        super().__init__()
        self.n_training_games = n_training_games
        self.training_seed = training_seed
        self.checkpoints = checkpoints
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.training_bot = training_bot
        self.smoothing_m = smoothing_m
        self._tree: "Optional[_TreeNode]" = None

    def _ensure_trained(self) -> _TreeNode:
        if self._tree is None:
            self._tree = _cached_tree(
                self.n_training_games,
                self.training_seed,
                self.checkpoints,
                self.max_depth,
                self.min_samples_leaf,
                self.training_bot,
                self.smoothing_m,
            )
        return self._tree

    @property
    def tree(self) -> _TreeNode:
        """The trained tree, training it first if needed -- for
        `summarize_tree`/`render_tree`."""
        return self._ensure_trained()

    def select_action(self, obs: ClueObservation) -> ClueBelief:
        """Score every still-unresolved card with the trained tree's
        leaf value, then mask and renormalize."""
        assert obs.mask is not None, (
            "select_action requires a masked observation (see clude_constraints.observe)"
        )
        mask = obs.mask
        tree = self._ensure_trained()
        raw: dict = {}
        for category in CATEGORIES:
            for card in category:
                if mask.holder_of(card) is not None:
                    continue
                raw[card] = _predict(tree, _features(obs, mask, card, category))
        return ClueBelief(probabilities=mask_and_normalize(raw, mask))

    def observe(self, transition: Any) -> None:
        """No-op -- trained once from self-play at construction time;
        there is no online retraining from live outcomes."""
        return None
