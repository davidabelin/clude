"""Fixed response schemas for the LLM wrapper (Phase 6b, 7c).

Two JSON schemas cover the four decisions: `CHOICE_SCHEMA` for movement,
accusation and card-to-show (`choice` + `say`) and `SUGGEST_SCHEMA` for
the suggestion (`suspect` + `weapon` + `say`). Every label field is an
enum over the fixed `LABELS`, so the schemas never change from call to
call -- the API compiles a new schema once and caches it for a day, and
a per-call schema would pay that cost every turn. The menu maps the
letters to options; a letter the menu does not have is caught client
side by the wrapper and falls back.

A third, `LOGBOOK_SCHEMA`, is the shape of a logbook entry's narrative
(Phase 7c): the fields the character's model writes at the debrief.
Its lists carry no length keywords -- structured outputs support only a
subset of JSON Schema -- so the bounds are stated in the prompt and
enforced by `clude_storage.logbooks.LogbookEntry.build`.

`parse_response` is the client-side half: it turns the model's text into
a validated dict or raises `ValueError` with the reason, which the
wrapper records as the fallback cause.
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


def schema_for(kind: str) -> dict:
    """The one schema object used for every call of decision `kind`
    (or the debrief, `LOGBOOK_KIND`).

    Raises
    ------
    KeyError
        For a kind other than ``move``, ``suggest``, ``accuse``, ``show``
        or ``logbook``.
    """
    if kind == LOGBOOK_KIND:
        return LOGBOOK_SCHEMA
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
        Extra keys are ignored. For `LOGBOOK_KIND` the object as parsed:
        `LogbookEntry.build` does the normalising.

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
    if kind == LOGBOOK_KIND:
        return data
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
