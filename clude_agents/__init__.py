"""Six strategy agents, one per suspect, plus the shared protocol, the
registry, and the Phase 5 personality layer (`Profile`, `Character`).
See docs/architecture.md for the method-to-suspect mapping and
docs/strategy-glossary.md for per-method write-ups.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .bandit import BanditAgent
from .base import AgentProtocol, ClueBelief, mask_and_normalize
from .character import (
    Character,
    ConfidenceFn,
    ds_belief_confidence,
    probabilities_confidence,
)
from .decision_tree import DecisionTreeAgent
from .dempster_shafer import DempsterShaferAgent
from .exact_enum import ExactEnumAgent
from .markov import MarkovAgent
from .naive_bayes import NaiveBayesAgent
from .personality import NEUTRAL, PRESETS, Profile

__all__ = [
    "AgentProtocol",
    "ClueBelief",
    "mask_and_normalize",
    "AgentSpec",
    "AGENT_SPECS",
    "list_agent_specs",
    "build_agent",
    "build_character",
    "Character",
    "Profile",
    "PRESETS",
    "NEUTRAL",
]


@dataclass(frozen=True)
class AgentSpec:
    """Metadata descriptor for one registered suspect agent.

    Parameters
    ----------
    name : str
        Suspect name; the registry key.
    description : str
    factory : Callable[[], AgentProtocol]
        Builds a fresh belief agent.
    profile : Profile
        The character's preset dials (`clude_agents.personality.PRESETS`).
    confidence_fn : ConfidenceFn
        What the character's `accuse_threshold` is tested against --
        the belief's probabilities for everyone but Peacock, whose
        caution comes from her Dempster-Shafer lower bound instead.
    """

    name: str
    description: str
    factory: Callable[[], AgentProtocol]
    profile: Profile = NEUTRAL
    confidence_fn: ConfidenceFn = probabilities_confidence


def _build_specs() -> dict[str, AgentSpec]:
    return {
        "Scarlett": AgentSpec(
            "Scarlett", "Naive Bayes over suggestion evidence.", NaiveBayesAgent,
            PRESETS["Scarlett"],
        ),
        "Plum": AgentSpec(
            "Plum",
            "Exact posterior by enumeration over consistent deals (samples when too slow).",
            ExactEnumAgent,
            PRESETS["Plum"],
        ),
        "Peacock": AgentSpec(
            "Peacock", "Dempster-Shafer belief/plausibility.", DempsterShaferAgent,
            PRESETS["Peacock"], ds_belief_confidence,
        ),
        "Mustard": AgentSpec(
            "Mustard", "Decision tree trained on self-play game logs.", DecisionTreeAgent,
            PRESETS["Mustard"],
        ),
        "Green": AgentSpec(
            "Green", "Thompson-sampling bandit ensemble over the other five.", BanditAgent,
            PRESETS["Green"],
        ),
        "White": AgentSpec(
            "White", "Markov model over opponents' suggestion patterns.", MarkovAgent,
            PRESETS["White"],
        ),
    }


AGENT_SPECS = _build_specs()


def list_agent_specs() -> list[AgentSpec]:
    """Return all registered agent specs sorted by suspect name."""
    return [AGENT_SPECS[name] for name in sorted(AGENT_SPECS.keys())]


def build_agent(name: str) -> AgentProtocol:
    """Instantiate one suspect's belief agent by registry name."""
    if name not in AGENT_SPECS:
        raise KeyError(f"Unknown suspect agent: {name}")
    return AGENT_SPECS[name].factory()


def build_character(name: str, profile: Optional[Profile] = None) -> Character:
    """Instantiate one suspect as a playable `Character`: its belief
    agent, its preset profile (or `profile` if given), and its spec's
    confidence function."""
    spec = AGENT_SPECS.get(name)
    if spec is None:
        raise KeyError(f"Unknown suspect agent: {name}")
    return Character(
        spec.factory(),
        profile=spec.profile if profile is None else profile,
        confidence_fn=spec.confidence_fn,
    )
