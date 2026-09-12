"""Mustard -- decision tree trained on self-play game logs.

Built fresh (no legacy basis); needed a headless engine plus self-play to
train on, which Phase 1 already provides. A hand-rolled CART-style
regression tree (Gini-guided binary splits, leaf value = mean label) is
trained once, per Mustard's character: pattern-matches what dumb-bot
self-play looks like, and can be confidently wrong on a deal that
doesn't resemble that training distribution -- e.g. once real LLM/human
play replaces random bots.

Notes
-----
Training data comes from `clude_training.self_play.generate_snapshots`
(Phase 4) -- still `RandomBot` self-play, not smarter opponents, so
Mustard's pattern-matching is bootstrapped on the same distribution
`clude_training.benchmark` measures everyone against. Retraining against
richer self-play later is expected to change his behavior, not just his
accuracy.

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
from clude_training.self_play import generate_snapshots

DEFAULT_N_TRAINING_GAMES = 25
DEFAULT_TRAINING_SEED = 2026
DEFAULT_CHECKPOINTS: tuple = (0.5, 1.0)
DEFAULT_MAX_DEPTH = 6
DEFAULT_MIN_SAMPLES_LEAF = 20
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
)

Row = tuple  # tuple[tuple[float, ...], int] -- (features, label)


def _features(obs: ClueObservation, mask, card: str, category: list) -> tuple:
    possible_holders_frac = len(mask.possible_holders[card]) / (obs.n_players + 1)
    or_constraint_involvement = sum(1 for cards, _h in mask.or_constraints if card in cards)
    times_named_unrefuted = sum(
        1 for s in obs.suggestion_log if card in s.cards() and s.refuter is None
    )
    times_named_total = sum(1 for s in obs.suggestion_log if card in s.cards())
    turn_fraction = min(obs.turn / MAX_TURN_FOR_NORMALIZATION, 1.0)
    category_size_frac = len(category) / 9.0
    return (
        possible_holders_frac,
        float(or_constraint_involvement),
        float(times_named_unrefuted),
        float(times_named_total),
        turn_fraction,
        category_size_frac,
    )


def _generate_training_rows(n_games: int, seed: int, checkpoints: tuple) -> list:
    rows: list = []
    for snap in generate_snapshots(n_games, seed, checkpoints=checkpoints):
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


def _build_tree(rows: list, depth: int, max_depth: int, min_samples_leaf: int) -> _TreeNode:
    labels = [y for _x, y in rows]
    mean = sum(labels) / len(labels) if labels else 0.5
    if (
        not rows
        or depth >= max_depth
        or len(rows) < 2 * min_samples_leaf
        or len(set(labels)) <= 1
    ):
        return _TreeNode(is_leaf=True, prediction=mean, n_samples=len(rows))

    split = _best_split(rows, n_features=len(rows[0][0]))
    if split is None:
        return _TreeNode(is_leaf=True, prediction=mean, n_samples=len(rows))

    _gain, fi, threshold = split
    left_rows = [(x, y) for x, y in rows if x[fi] <= threshold]
    right_rows = [(x, y) for x, y in rows if x[fi] > threshold]
    return _TreeNode(
        is_leaf=False,
        feature_index=fi,
        threshold=threshold,
        left=_build_tree(left_rows, depth + 1, max_depth, min_samples_leaf),
        right=_build_tree(right_rows, depth + 1, max_depth, min_samples_leaf),
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
        Every leaf's mean label, ascending -- how spread out the tree's
        possible outputs are.
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


def training_rows(n_training_games: int, training_seed: int, checkpoints: tuple) -> list:
    """The (features, label) rows Mustard trains on for these settings,
    generated once and cached at module level. Exposed so tooling can
    inspect the training set (size, label balance) without retraining."""
    rows_key = (n_training_games, training_seed, checkpoints)
    if rows_key not in _ROWS_CACHE:
        _ROWS_CACHE[rows_key] = _generate_training_rows(
            n_training_games, training_seed, checkpoints
        )
    return _ROWS_CACHE[rows_key]


def _cached_tree(
    n_training_games: int, training_seed: int, checkpoints: tuple,
    max_depth: int, min_samples_leaf: int,
) -> _TreeNode:
    rows = training_rows(n_training_games, training_seed, checkpoints)
    tree_key = (n_training_games, training_seed, checkpoints, max_depth, min_samples_leaf)
    if tree_key not in _TREE_CACHE:
        _TREE_CACHE[tree_key] = _build_tree(
            rows, depth=0, max_depth=max_depth, min_samples_leaf=min_samples_leaf
        )
    return _TREE_CACHE[tree_key]


class DecisionTreeAgent(SeededAgentMixin):
    """Pattern-matches self-play history; confident, even when the
    pattern doesn't apply."""

    name = "Mustard"

    def __init__(
        self,
        n_training_games: int = DEFAULT_N_TRAINING_GAMES,
        training_seed: int = DEFAULT_TRAINING_SEED,
        checkpoints: tuple = DEFAULT_CHECKPOINTS,
        max_depth: int = DEFAULT_MAX_DEPTH,
        min_samples_leaf: int = DEFAULT_MIN_SAMPLES_LEAF,
    ) -> None:
        super().__init__()
        self.n_training_games = n_training_games
        self.training_seed = training_seed
        self.checkpoints = checkpoints
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self._tree: "Optional[_TreeNode]" = None

    def _ensure_trained(self) -> _TreeNode:
        if self._tree is None:
            self._tree = _cached_tree(
                self.n_training_games,
                self.training_seed,
                self.checkpoints,
                self.max_depth,
                self.min_samples_leaf,
            )
        return self._tree

    @property
    def tree(self) -> _TreeNode:
        """The trained tree, training it first if needed -- for
        `summarize_tree`/`render_tree`."""
        return self._ensure_trained()

    def select_action(self, obs: ClueObservation) -> ClueBelief:
        """Score every still-unresolved card with the trained tree's
        leaf mean, then mask and renormalize."""
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
