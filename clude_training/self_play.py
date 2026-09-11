"""Self-play data generation: many `RandomBot` games, snapshotted at
several points each. Shared by Mustard's tree (`clude_agents.decision_tree`,
which needs (features, label) rows) and the benchmark
(`clude_training.benchmark`, which needs full masked observations) --
the two consumers extract different things from the same underlying
snapshots, so the game-running and truncation logic lives here once.

Deliberately depends only on `clude_core` and `clude_constraints`, never
`clude_agents`, so agents can depend on this module without a cycle.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterator

import clude_constraints
from clude_core import engine
from clude_core.bots import RandomBot
from clude_core.state import ClueObservation, GameState

DEFAULT_MAX_TURNS = 150
DEFAULT_CHECKPOINTS: tuple = (0.25, 0.5, 0.75, 1.0)


@dataclass(frozen=True)
class Snapshot:
    """One masked observation from one viewer at one checkpoint of one
    finished self-play game, paired with that game's eventual truth.

    Parameters
    ----------
    obs : ClueObservation
        `viewer`'s masked view of the game truncated to `checkpoint`'s
        fraction of that game's suggestions.
    envelope : tuple[str, str, str]
        The game's true (suspect, weapon, room) -- known only because the
        game already finished; never visible to `obs` itself.
    game_index : int
        Which self-play game this came from (0-based), for grouping.
    viewer : int
        Whose perspective `obs` is built from.
    checkpoint : float
        Which requested checkpoint fraction (e.g. 0.5) this snapshot
        corresponds to -- the *requested* value, not `k / total`, so
        results group cleanly regardless of rounding.
    """

    obs: ClueObservation
    envelope: tuple
    game_index: int
    viewer: int
    checkpoint: float


def _truncate(state: GameState, k: int) -> GameState:
    """A copy of `state` as if only its first `k` suggestions had
    happened yet -- for sampling one finished game at varied amounts of
    revealed evidence. Accusations are cleared and everyone is marked
    active, since Phase 3/4 only care about suggestion-log evidence."""
    return replace(
        state,
        suggestion_log=state.suggestion_log[:k],
        accusation_log=[],
        active=[True] * state.n_players,
        turn=k,
    )


def generate_snapshots(
    n_games: int,
    seed: int,
    checkpoints: tuple = DEFAULT_CHECKPOINTS,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> Iterator[Snapshot]:
    """Play `n_games` headless `RandomBot` games and yield a `Snapshot`
    for every (game, viewer, checkpoint) combination.

    Player count cycles 3..6 across games so training/benchmark data
    isn't biased toward one table size. A game with zero suggestions
    (vanishingly rare, but possible within `max_turns`) contributes no
    snapshots rather than dividing by zero.
    """
    for g in range(n_games):
        n_players = 3 + (g % 4)
        bots = {p: RandomBot() for p in range(n_players)}
        state, _events = engine.run_game(n_players, bots, seed=seed + g, max_turns=max_turns)
        total = len(state.suggestion_log)
        if total == 0:
            continue
        for checkpoint in checkpoints:
            k = max(1, round(total * checkpoint))
            snap_state = _truncate(state, k)
            for viewer in range(n_players):
                obs = clude_constraints.observe(snap_state, viewer)
                yield Snapshot(
                    obs=obs,
                    envelope=state.envelope,
                    game_index=g,
                    viewer=viewer,
                    checkpoint=checkpoint,
                )
