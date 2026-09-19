"""The LLM wrapper (Phase 6): an LLM chooses, within a leash, among the
legal options a character's own method has scored, and adds a line of
table talk; anything else falls back to the character's own decision.
Design and David's decisions: docs/phase6-plan.md.
"""
from __future__ import annotations

from typing import Optional

from clude_agents import build_character
from clude_agents.personality import Profile

from .backend import (
    DEFAULT_MODEL,
    LLMBackend,
    LLMRequest,
    LLMResult,
    NullBackend,
    RecordingBackend,
    ReplayBackend,
    ReplayMiss,
    ScriptedBackend,
    open_backend,
)
from .menu import (
    Menu,
    Option,
    SuggestionMenu,
    accusation_menu,
    movement_menu,
    show_menu,
    suggestion_menu,
    within_leash,
)
from .logbook import debrief_prompt, resolve_opponents
from .persona import DISPLAY_NAMES, Persona, load_persona, load_rules
from .player import Decision, LLMCharacter, LLMSettings
from .prompt import remark_prompt, system_prompt, user_prompt
from .schema import (
    LABELS,
    LOGBOOK_KIND,
    LOGBOOK_SCHEMA,
    MAX_OPTIONS,
    REMARK_KIND,
    REMARK_SCHEMA,
    parse_response,
    schema_for,
)

__all__ = [
    "DEFAULT_MODEL",
    "DISPLAY_NAMES",
    "Decision",
    "LABELS",
    "LLMBackend",
    "LLMCharacter",
    "LLMRequest",
    "LLMResult",
    "LLMSettings",
    "LOGBOOK_KIND",
    "LOGBOOK_SCHEMA",
    "MAX_OPTIONS",
    "Menu",
    "REMARK_KIND",
    "REMARK_SCHEMA",
    "NullBackend",
    "Option",
    "Persona",
    "RecordingBackend",
    "ReplayBackend",
    "ReplayMiss",
    "ScriptedBackend",
    "SuggestionMenu",
    "accusation_menu",
    "build_llm_character",
    "debrief_prompt",
    "load_persona",
    "load_rules",
    "movement_menu",
    "open_backend",
    "parse_response",
    "remark_prompt",
    "resolve_opponents",
    "schema_for",
    "show_menu",
    "suggestion_menu",
    "system_prompt",
    "user_prompt",
    "within_leash",
]


def build_llm_character(
    name: str,
    backend: LLMBackend,
    profile: Optional[Profile] = None,
    settings: Optional[LLMSettings] = None,
) -> LLMCharacter:
    """One suspect as an LLM-piloted seat: `build_character(name, profile)`
    wrapped with its persona file and `backend`."""
    return LLMCharacter(build_character(name, profile), backend, settings=settings)
