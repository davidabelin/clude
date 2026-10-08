"""Structured reply schemas and validation for model requests.

Choice uses one letter, suggestion suspect/weapon letters, remark only say,
debrief the logbook fields and condense the digest's. Schemas constrain
shape; the wrapper still checks letters against allowed menu entries.
Failure leads to fallback or an unwritten debrief or digest, never an
unchecked engine answer.
"""
from __future__ import annotations

import json

LABELS: tuple = tuple("ABCDEFGHIJKL")
"""The option letters, best first; also the cap on options per menu."""

MAX_OPTIONS = len(LABELS)

LABEL_FIELDS: dict = {
    "move": ("choice",),
    "accuse": ("choice",),
    "show": ("choice",),
    "suggest": ("suspect", "weapon"),
}
"""Which fields of a response name an option, per decision kind."""

LOGBOOK_KIND = "logbook"
"""The request kind of the debrief call."""

REMARK_KIND = "remark"
"""The request kind of an off-turn line (Phase 8.3b)."""

CONDENSE_KIND = "condense"
"""The request kind of the call that condenses a logbook into its digest."""

REMARK_SCHEMA: dict = {
    "type": "object",
    "properties": {"say": {"type": "string"}},
    "required": ["say"],
    "additionalProperties": False,
}


def _schema(fields: tuple) -> dict:
    properties = {name: {"type": "string", "enum": list(LABELS)} for name in fields}
    properties["say"] = {"type": "string"}
    return {
        "type": "object",
        "properties": properties,
        "required": [*fields, "say"],
        "additionalProperties": False,
    }


CHOICE_SCHEMA: dict = _schema(("choice",))
SUGGEST_SCHEMA: dict = _schema(("suspect", "weapon"))


def _strings() -> dict:
    return {"type": "array", "items": {"type": "string"}}


def _objects(*fields: str) -> dict:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {name: {"type": "string"} for name in fields},
            "required": list(fields),
            "additionalProperties": False,
        },
    }


LOGBOOK_FIELDS: tuple = (
    "title", "summary", "flags", "what_happened", "evaluations", "key_insights",
    "lessons_learned", "final_outcome", "standing_instructions", "dossiers",
)
"""The model-written fields of a `LogbookEntry`, in the order the prompt lists them."""

LOGBOOK_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "flags": _strings(),
        "what_happened": {"type": "string"},
        "evaluations": _objects("opponent", "evaluation", "notes"),
        "key_insights": _strings(),
        "lessons_learned": _strings(),
        "final_outcome": {"type": "string"},
        "standing_instructions": _strings(),
        "dossiers": _objects("opponent", "read"),
    },
    "required": list(LOGBOOK_FIELDS),
    "additionalProperties": False,
}

CONDENSE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "overview": {"type": "string"},
        "flag_map": _objects("flag", "into"),
        "themes": _objects("flag", "lesson"),
    },
    "required": ["overview", "flag_map", "themes"],
    "additionalProperties": False,
}
"""The model-written fields of a `LogbookDigest`; `flag_map` lists the merges."""


def schema_for(kind: str) -> dict:
    """The one schema object used for every call of decision `kind`
    (or the debrief, `LOGBOOK_KIND`, or the condensing, `CONDENSE_KIND`).

    Raises
    ------
    KeyError
        For a kind other than ``move``, ``suggest``, ``accuse``, ``show``,
        ``logbook``, ``condense`` or ``remark``.
    """
    if kind == LOGBOOK_KIND:
        return LOGBOOK_SCHEMA
    if kind == CONDENSE_KIND:
        return CONDENSE_SCHEMA
    if kind == REMARK_KIND:
        return REMARK_SCHEMA
    fields = LABEL_FIELDS[kind]
    return SUGGEST_SCHEMA if fields == ("suspect", "weapon") else CHOICE_SCHEMA


def parse_response(kind: str, text: str) -> dict:
    """Validate the model's reply for decision `kind`.

    Parameters
    ----------
    kind : str
        One of `LABEL_FIELDS`' keys.
    text : str
        The model's text, expected to be a JSON object.

    Returns
    -------
    dict
        The label fields upper-cased (``"a"`` is accepted as ``"A"``) and
        ``say`` stripped, a missing or non-string ``say`` becoming ``""``.
        Extra keys are ignored. For `LOGBOOK_KIND` and `CONDENSE_KIND` the
        object as parsed: `LogbookEntry.build` and `LogbookDigest.build` do
        the normalising. For `REMARK_KIND`,
        ``say`` alone, stripped.

    Raises
    ------
    ValueError
        Not JSON, not an object, a label field missing, or a label that
        is not one of `LABELS`. The message says which.
    """
    try:
        data = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"not JSON ({exc})") from None
    if not isinstance(data, dict):
        raise ValueError("not a JSON object")
    if kind in (LOGBOOK_KIND, CONDENSE_KIND):
        return data
    if kind == REMARK_KIND:
        say = data.get("say", "")
        return {"say": say.strip() if isinstance(say, str) else ""}
    parsed: dict = {}
    for name in LABEL_FIELDS[kind]:
        value = data.get(name)
        label = value.strip().upper() if isinstance(value, str) else None
        if label not in LABELS:
            raise ValueError(f"{name} is not an option letter: {value!r}")
        parsed[name] = label
    say = data.get("say", "")
    parsed["say"] = say.strip() if isinstance(say, str) else ""
    return parsed
