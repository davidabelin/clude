"""Backend protocol and offline/recorded implementations for LLMCharacter.

complete(request) returns LLMResult. NullBackend always fails; ScriptedBackend
serves test replies; RecordingBackend saves exchanges; ReplayBackend looks
up request digests and raises ReplayMiss for missing keys. Persona/rules,
menu or state changes can invalidate recordings. open_backend resolves CLI
backend specifications; only the real adapter imports the SDK lazily.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional, Protocol, Sequence

DEFAULT_MODEL = "claude-opus-5"
"""The model an `LLMCharacter` uses unless told otherwise (decision 3)."""

RECORD_FORMAT_VERSION = 1


@dataclass(frozen=True)
class LLMRequest:
    """One call: the cached `system` prefix, the per-turn `user` text, the
    fixed response `schema`, and the decision `kind` it is for.

    `memory` is the character's logbook block, sent as a cached system
    block after the persona; empty when the character has nothing to
    read back. `canon` is the index of the canon (`clude_llm.canon`),
    another cached system block, between the persona and the memory;
    `tools` are the canon's tool definitions, `lookup` answers one of
    their calls, and `max_lookups` is how many rounds of them the
    backend may run before the model must answer. With all of these
    empty the request, its `key` and the API call are exactly the Phase
    6 ones. `effort`, `max_tokens` and `timeout` override the backend's
    defaults for one call (the debrief asks for more of all three) and,
    like `lookup` and `max_lookups`, are not part of the key.
    """

    system: str
    user: str
    schema: dict
    kind: str
    memory: str = ""
    effort: Optional[str] = None
    max_tokens: Optional[int] = None
    timeout: Optional[float] = None
    canon: str = ""
    tools: tuple = ()
    lookup: Optional[Callable] = field(default=None, compare=False, repr=False)
    max_lookups: int = 0

    def key(self) -> str:
        """A stable digest of everything the model is sent: system, user
        and schema, plus the memory block, the canon block and the tools
        only when there are any, so every recording made before each
        existed still replays."""
        payload: dict = {"system": self.system, "user": self.user, "schema": self.schema}
        if self.memory:
            payload["memory"] = self.memory
        if self.canon:
            payload["canon"] = self.canon
        if self.tools:
            payload["tools"] = list(self.tools)
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


@dataclass
class LLMResult:
    """What came back. `ok` is the wrapper's go/no-go: some text, no
    error, and no refusal stop. `lookups` are the canon calls the
    backend answered on the way, oldest first, each ``{"tool", "input",
    "found", "error"}``; the token counts cover every round."""

    text: Optional[str] = None
    error: Optional[str] = None
    stop_reason: Optional[str] = None
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    seconds: float = 0.0
    lookups: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.text is not None and self.error is None and self.stop_reason != "refusal"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LLMResult":
        defaults = asdict(cls())
        return cls(**{key: data.get(key, value) for key, value in defaults.items()})


class LLMBackend(Protocol):
    name: str

    def complete(self, request: LLMRequest) -> LLMResult: ...


class NullBackend:
    """Never answers. An `LLMCharacter` on it is its headless twin."""

    name = "null"

    def complete(self, request: LLMRequest) -> LLMResult:
        del request
        return LLMResult(error="null backend: no model configured")


class ScriptedBackend:
    """Canned replies for tests.

    Parameters
    ----------
    responses : Sequence
        Served in order. A `str` is the reply text; a `dict` is JSON-dumped;
        an `LLMResult` is returned as is; an `Exception` instance is
        raised. When exhausted, the last item repeats (`repeat_last`) or
        an error result is returned.
    """

    name = "scripted"

    def __init__(self, responses: Sequence, repeat_last: bool = True) -> None:
        self.responses = list(responses)
        self.repeat_last = repeat_last
        self.requests: list = []
        self.calls = 0

    def complete(self, request: LLMRequest) -> LLMResult:
        self.requests.append(request)
        index = self.calls
        self.calls += 1
        if index >= len(self.responses):
            if not self.responses or not self.repeat_last:
                return LLMResult(error="scripted backend: script exhausted")
            index = len(self.responses) - 1
        item = self.responses[index]
        if isinstance(item, BaseException):
            raise item
        if isinstance(item, LLMResult):
            return item
        text = json.dumps(item) if isinstance(item, dict) else str(item)
        return LLMResult(text=text, stop_reason="end_turn", model=self.name)


class ReplayMiss(KeyError):
    """A replayed request was not in the recording: the prompt changed."""


def _load_recording(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"version": RECORD_FORMAT_VERSION, "systems": {}, "entries": {}}


class RecordingBackend:
    """Pass every request to `inner` and write the exchange to `path`
    (JSON; system prompts stored once, by digest). Appends to an existing
    file, so several games can share one recording."""

    name = "record"

    def __init__(self, inner: LLMBackend, path) -> None:
        self.inner = inner
        self.path = Path(path)
        self.data = _load_recording(self.path)

    def complete(self, request: LLMRequest) -> LLMResult:
        result = self.inner.complete(request)
        system_key = hashlib.sha256(request.system.encode("utf-8")).hexdigest()
        self.data["systems"][system_key] = request.system
        entry = {
            "kind": request.kind,
            "system": system_key,
            "user": request.user,
            "result": result.to_dict(),
        }
        for name in ("memory", "canon"):
            block = getattr(request, name)
            if block:
                # The block repeats on every call of a game; store it once, by digest.
                block_key = hashlib.sha256(block.encode("utf-8")).hexdigest()
                self.data["systems"][block_key] = block
                entry[name] = block_key
        if request.tools:
            entry["tools"] = [tool["name"] for tool in request.tools]
        self.data["entries"][request.key()] = entry
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=1), encoding="utf-8")
        return result

    def __len__(self) -> int:
        return len(self.data["entries"])


class ReplayBackend:
    """Serve a `RecordingBackend` file back, keyed by request digest.

    Parameters
    ----------
    path : str or Path
    strict : bool
        Raise `ReplayMiss` on an unknown request (default), else return
        an error result so the wrapper falls back.
    """

    name = "replay"

    def __init__(self, path, strict: bool = True) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"no recording at {self.path}")
        self.data = _load_recording(self.path)
        self.strict = strict
        self.hits = 0
        self.misses = 0

    def complete(self, request: LLMRequest) -> LLMResult:
        entry = self.data["entries"].get(request.key())
        if entry is None:
            self.misses += 1
            if self.strict:
                raise ReplayMiss(f"request not in recording {self.path} (kind={request.kind})")
            return LLMResult(error="replay: request not in recording")
        self.hits += 1
        result = LLMResult.from_dict(entry["result"])
        result.seconds = 0.0
        return result

    def __len__(self) -> int:
        return len(self.data["entries"])


def _anthropic(model: str, **kwargs):
    from .anthropic_backend import AnthropicBackend  # lazy: the SDK is optional

    return AnthropicBackend(model=model, **kwargs)


def open_backend(spec: str, model: str = DEFAULT_MODEL, **kwargs) -> LLMBackend:
    """Resolve a ``--llm-backend`` value.

    Parameters
    ----------
    spec : str
        ``anthropic`` (the real API), ``null``, ``record:PATH`` (the real
        API, recorded to PATH) or ``replay:PATH``.
    model : str
        Passed to the Anthropic backend.
    **kwargs
        Passed to the Anthropic backend (timeout, effort, ...).

    Raises
    ------
    ValueError
        On any other spec.
    """
    spec = spec.strip()
    if spec == "null":
        return NullBackend()
    if spec == "anthropic":
        return _anthropic(model, **kwargs)
    if spec.startswith("replay:"):
        return ReplayBackend(spec[len("replay:"):])
    if spec.startswith("record:"):
        return RecordingBackend(_anthropic(model, **kwargs), spec[len("record:"):])
    raise ValueError(
        f"unknown LLM backend {spec!r}; expected anthropic, null, record:PATH or replay:PATH"
    )
