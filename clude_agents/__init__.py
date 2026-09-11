"""Six strategy agents, one per suspect, plus the shared protocol and
registry. See docs/architecture.md for the method-to-suspect mapping and
docs/strategy-glossary.md for per-method write-ups.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .bandit import BanditAgent
from .base import AgentProtocol, ClueBelief, mask_and_normalize
from .decision_tree import DecisionTreeAgent
from .dempster_shafer import DempsterShaferAgent
from .exact_enum import ExactEnumAgent
from .markov import MarkovAgent
from .naive_bayes import NaiveBayesAgent

__all__ = [
    "AgentProtocol",
    "ClueBelief",
    "mask_and_normalize",
    "AgentSpec",
    "AGENT_SPECS",
    "list_agent_specs",
    "build_agent",
]


@dataclass(frozen=True)
class AgentSpec:
    """Metadata descriptor for one registered suspect agent."""

    name: str
    description: str
    factory: Callable[[], AgentProtocol]


def _build_specs() -> dict[str, AgentSpec]:
    return {
        "Scarlett": AgentSpec(
            "Scarlett", "Naive Bayes over suggestion evidence.", NaiveBayesAgent
        ),
        "Plum": AgentSpec(
            "Plum",
            "Exact posterior by enumeration over consistent deals (samples when too slow).",
            ExactEnumAgent,
        ),
        "Peacock": AgentSpec(
            "Peacock", "Dempster-Shafer belief/plausibility.", DempsterShaferAgent
        ),
        "Mustard": AgentSpec(
            "Mustard", "Decision tree trained on self-play game logs.", DecisionTreeAgent
        ),
        "Green": AgentSpec(
            "Green", "Thompson-sampling bandit ensemble over the other five.", BanditAgent
        ),
        "White": AgentSpec(
            "White", "Markov model over opponents' suggestion patterns.", MarkovAgent
        ),
    }


AGENT_SPECS = _build_specs()


def list_agent_specs() -> list[AgentSpec]:
    """Return all registered agent specs sorted by suspect name."""
    return [AGENT_SPECS[name] for name in sorted(AGENT_SPECS.keys())]


def build_agent(name: str) -> AgentProtocol:
    """Instantiate one suspect's agent by registry name."""
    if name not in AGENT_SPECS:
        raise KeyError(f"Unknown suspect agent: {name}")
    return AGENT_SPECS[name].factory()
