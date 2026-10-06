"""Analyze floor and method beliefs over a finished game's visible history.

Each requested viewer uses a redacted observation. Methods are queried at
suggestion checkpoints; this reconstructs estimates rather than recording
live memory/feedback or model choices. Rendering is shared with CLI/prompts.
See docs/cli.md and docs/web.md for trace limitations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import clude_constraints
from clude_core.domain import ALL_CARDS, Suggestion
from clude_core.state import ClueObservation, GameState
from clude_training.self_play import truncate_state

if TYPE_CHECKING:
    from clude_agents.base import AgentProtocol, ClueBelief


@dataclass(frozen=True)
class BeliefStep:
    """One viewer's view after `k` suggestions, and each agent's belief
    given exactly that view.

    Parameters
    ----------
    k : int
        How many suggestions have been revealed; 0 is the deal alone.
    suggestion : Suggestion or None
        The k-th suggestion as the viewer sees it (`card_shown` only if
        they were entitled to it), or None at k = 0.
    obs : ClueObservation
        The viewer's masked observation at this point.
    beliefs : dict[str, ClueBelief]
        Agent name -> that agent's `select_action(obs)`.
    """

    k: int
    suggestion: Optional[Suggestion]
    obs: ClueObservation
    beliefs: dict


def resolved_count(obs: ClueObservation) -> int:
    """How many of the 21 cards the floor has fully located from `obs`'s
    perspective (own hand included)."""
    assert obs.mask is not None, "resolved_count needs a masked observation"
    return sum(1 for c in ALL_CARDS if obs.mask.holder_of(c) is not None)


def belief_trace(
    state: GameState,
    viewer: int,
    agents: dict,
    every: int = 1,
) -> list[BeliefStep]:
    """Replay a finished game from one viewer's perspective.

    Parameters
    ----------
    state : GameState
        A finished game (from `engine.run_game`); read, never mutated.
    viewer : int
        Whose perspective to rebuild.
    agents : dict[str, AgentProtocol]
        Agents to query at each step, already `reset` by the caller.
        Their `observe` is never called -- a trace is read-only.
    every : int
        Sample after every `every`-th suggestion. k = 0 and the final k
        are always included, so a trace is never empty and always ends
        on the full game.

    Returns
    -------
    list[BeliefStep]
        In increasing `k`.

    Raises
    ------
    ValueError
        If `every` < 1.
    """
    if every < 1:
        raise ValueError("every must be >= 1")
    total = len(state.suggestion_log)
    ks = sorted({0, total} | {k for k in range(1, total) if k % every == 0})
    steps: list[BeliefStep] = []
    for k in ks:
        obs = clude_constraints.observe(truncate_state(state, k), viewer)
        suggestion = obs.suggestion_log[-1] if k > 0 else None
        beliefs = {name: agent.select_action(obs) for name, agent in agents.items()}
        steps.append(BeliefStep(k=k, suggestion=suggestion, obs=obs, beliefs=beliefs))
    return steps


@dataclass(frozen=True)
class ConvergencePoint:
    """The floor's progress for every viewer after `k` suggestions.

    Parameters
    ----------
    k : int
    resolved : dict[int, int]
        Viewer -> cards fully located (of 21).
    solved : dict[int, bool]
        Viewer -> whether the floor has proven all three envelope cards.
    """

    k: int
    resolved: dict
    solved: dict


def floor_convergence(state: GameState) -> list[ConvergencePoint]:
    """How fast the deduction floor closes in for every viewer at once:
    one point per suggestion count from 0 to the full game. `resolved`
    is non-decreasing in `k` for each viewer, since more evidence can
    only shrink a card's possible-holder set."""
    points: list[ConvergencePoint] = []
    for k in range(len(state.suggestion_log) + 1):
        snap = truncate_state(state, k)
        resolved: dict = {}
        solved: dict = {}
        for viewer in range(state.n_players):
            obs = clude_constraints.observe(snap, viewer)
            resolved[viewer] = resolved_count(obs)
            solved[viewer] = obs.mask.solution() is not None
        points.append(ConvergencePoint(k=k, resolved=resolved, solved=solved))
    return points
