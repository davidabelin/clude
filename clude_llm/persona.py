"""Personas: who each character is when it speaks (Phase 6).

A persona is prose, one Markdown file per suspect in `personas/`
(`Scarlett.md`, ...), plus `rules.md`, the standing rules every character
gets. The files are the source of truth so a voice can be tuned without
touching code; a suspect without a file gets a one-line default built
from its `AgentSpec.description`. Persona prose carries voice and
self-image; the numbers carry the behaviour ("don't encode the flaw
twice", docs/phase6-plan.md).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

PERSONA_DIR = Path(__file__).resolve().parent / "personas"
RULES_FILE = "rules.md"

DISPLAY_NAMES: dict = {
    "Scarlett": "Miss Scarlett",
    "Mustard": "Colonel Mustard",
    "White": "Mrs. White",
    "Green": "Mr. Green",
    "Peacock": "Mrs. Peacock",
    "Plum": "Professor Plum",
}


@dataclass(frozen=True)
class Persona:
    """`name` is the suspect (the registry key); `text` is the prose the
    system prompt opens with; `source` says where it came from."""

    name: str
    text: str
    source: str = "default"


def default_persona(name: str) -> Persona:
    """A minimal persona from the registry's one-line method description."""
    from clude_agents import AGENT_SPECS  # here, not at module top, so this module stays light

    display = DISPLAY_NAMES.get(name, name)
    spec = AGENT_SPECS.get(name)
    method = spec.description.rstrip(".") if spec is not None else "your own way of weighing the evidence"
    method = method[0].lower() + method[1:]
    text = (
        f"You are {display}, one of the six suspects at the table. "
        f"You reason by {method}. Speak briefly, in your own voice."
    )
    return Persona(name, text, "default")


def load_persona(name: str, directory: Optional[Path] = None) -> Persona:
    """The persona file for `name` if there is one, else `default_persona`."""
    folder = PERSONA_DIR if directory is None else Path(directory)
    path = folder / f"{name}.md"
    if path.exists():
        return Persona(name, path.read_text(encoding="utf-8"), str(path))
    return default_persona(name)


def load_rules(directory: Optional[Path] = None) -> str:
    """The standing rules text (`rules.md`).

    Raises
    ------
    FileNotFoundError
        If the file is missing; it ships with the package.
    """
    folder = PERSONA_DIR if directory is None else Path(directory)
    return (folder / RULES_FILE).read_text(encoding="utf-8")
