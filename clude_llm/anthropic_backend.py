"""Anthropic SDK adapter for structured choices, remarks and debriefs.

The SDK is imported lazily. Persona/rules, the optional canon index and
the optional memory are cached system blocks; the request supplies user
text/schema. A request with canon tools runs the tool loop here, up to
its `max_lookups` rounds, the last round sent with tool choice none so
the model must answer in schema. SDK errors become LLMResult errors so
the wrapper can fall back. The adapter may use one SDK retry; no live
call is needed at construction. See docs/llm-wrapper.md.
"""
from __future__ import annotations

import json
import time
from typing import Optional

from .backend import DEFAULT_MODEL, LLMRequest, LLMResult

FALLBACK_BETA = "server-side-fallback-2026-07-01"
"""The beta header for the API's server-side refusal fallbacks."""

DEFAULT_EFFORT = "low"
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 1

PRICES_PER_MTOK: dict = {
    # (input, output) in dollars per million tokens; cache reads bill at a
    # tenth of the input rate. From the API reference as of 2026-06.
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> Optional[float]:
    """Dollars for one run's token counts, or None for an unpriced model.
    `input_tokens` is the uncached count; `cached_tokens` the cache reads."""
    prices = PRICES_PER_MTOK.get(model)
    if prices is None:
        return None
    price_in, price_out = prices
    return (input_tokens * price_in + cached_tokens * price_in / 10 + output_tokens * price_out) / 1e6


class AnthropicBackend:
    """Claude via the `anthropic` SDK.

    Parameters
    ----------
    model : str
    effort : str
        `output_config.effort`; ``low`` by default (docs/phase6-plan.md).
    max_tokens : int
        Room for adaptive thinking plus the short JSON reply.
    timeout : float
        Seconds per request; a timeout is just a fallback.
    max_retries : int
        The SDK's own retries on 429/5xx/connection errors.
    server_fallbacks : bool
        Send the API's server-side refusal fallbacks (`FALLBACK_BETA`,
        ``fallbacks="default"``). Redundant with the wrapper's own
        fallback, on by default per the API guidance for Opus 5.
    api_key : str or None
        Explicit key; default the SDK's own resolution.
    client : object or None
        A ready client (or a test double with ``messages.create`` and
        ``beta.messages.create``); default a lazily built `anthropic.Anthropic`.
    """

    name = "anthropic"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        *,
        effort: str = DEFAULT_EFFORT,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        server_fallbacks: bool = True,
        api_key: Optional[str] = None,
        client=None,
    ) -> None:
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.server_fallbacks = server_fallbacks
        self._api_key = api_key
        self._client = client

    @property
    def client(self):
        """The SDK client, built on first use.

        Raises
        ------
        ImportError
            If the `anthropic` package is not installed.
        """
        if self._client is None:
            try:
                import anthropic
            except ImportError as exc:
                raise ImportError(
                    "the anthropic backend needs the `anthropic` package: "
                    "pip install -r requirements.txt"
                ) from exc
            self._client = anthropic.Anthropic(
                api_key=self._api_key, timeout=self.timeout, max_retries=self.max_retries
            )
        return self._client

    def params(self, request: LLMRequest) -> dict:
        """The keyword arguments of the one API call, minus the beta bits.
        The system prompt is up to three cached blocks: the persona, then
        the canon index (`request.canon`, the same all season), then the
        logbook (`request.memory`, the same all game), stable before
        volatile for the cache. The canon's `tools` go on the call only
        with a `lookup` to answer them and a round to run. The request's
        `effort` and `max_tokens` win over the backend's when set."""
        system = [{"type": "text", "text": request.system, "cache_control": {"type": "ephemeral"}}]
        for block in (request.canon, request.memory):
            if block:
                system.append({"type": "text", "text": block, "cache_control": {"type": "ephemeral"}})
        params = {
            "model": self.model,
            "max_tokens": request.max_tokens or self.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": request.user}],
            "output_config": {
                "format": {"type": "json_schema", "schema": request.schema},
                "effort": request.effort or self.effort,
            },
        }
        if request.tools and request.lookup is not None and request.max_lookups > 0:
            params["tools"] = [dict(tool) for tool in request.tools]
        return params

    def _create(self, params: dict, options: dict):
        if self.server_fallbacks:
            return self.client.beta.messages.create(
                betas=[FALLBACK_BETA], fallbacks="default", **params, **options
            )
        return self.client.messages.create(**params, **options)

    @staticmethod
    def _answer(request: LLMRequest, use, lookups: list) -> dict:
        """One `tool_result` block for the `tool_use` block `use`, through
        `request.lookup`; a failure is an error result the model can
        answer around, never an exception. The lookup is appended to
        `lookups` for the audit."""
        name = str(getattr(use, "name", "") or "")
        arguments = dict(getattr(use, "input", None) or {})
        try:
            found = dict(request.lookup(name, arguments))
            summary = str(found.pop("found", ""))
            text = json.dumps(found, ensure_ascii=False)
            error = False
        except Exception as exc:  # the canon's fault, reported to the model
            text, summary, error = f"{type(exc).__name__}: {exc}", f"{name} failed: {exc}", True
        lookups.append({"tool": name, "input": arguments, "found": summary, "error": error})
        block = {"type": "tool_result", "tool_use_id": getattr(use, "id", ""), "content": text}
        if error:
            block["is_error"] = True
        return block

    def complete(self, request: LLMRequest) -> LLMResult:
        """One decision, in one or more API rounds: a round that stops
        for tools has each answered (`_answer`) and the exchange, the
        model's content unchanged, appended for the next; the last
        permitted round carries ``tool_choice: none``. Tokens are summed
        over the rounds; `seconds` is the whole."""
        started = time.perf_counter()
        try:
            params = self.params(request)
            options = {"timeout": request.timeout} if request.timeout else {}
            rounds = request.max_lookups if "tools" in params else 0
            messages = list(params["messages"])
            usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
            lookups: list = []
            for round_ in range(rounds + 1):
                call = dict(params, messages=messages)
                if rounds and round_ == rounds:
                    call["tool_choice"] = {"type": "none"}
                response = self._create(call, options)
                result = self.to_result(response, 0.0)
                for name in usage:
                    usage[name] += getattr(result, name)
                content = list(getattr(response, "content", None) or [])
                uses = [block for block in content if getattr(block, "type", None) == "tool_use"]
                if result.stop_reason != "tool_use" or not uses:
                    break
                messages = messages + [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": [self._answer(request, use, lookups) for use in uses]},
                ]
        except Exception as exc:  # every SDK error class is a fallback here, none is retried
            return LLMResult(
                error=f"{type(exc).__name__}: {exc}",
                model=self.model,
                seconds=time.perf_counter() - started,
            )
        for name, count in usage.items():
            setattr(result, name, count)
        result.lookups = lookups
        result.seconds = time.perf_counter() - started
        return result

    @staticmethod
    def to_result(response, seconds: float) -> LLMResult:
        """Map an SDK `Message` (or a double with the same attributes) to
        an `LLMResult`: the first text block, the stop reason, the model
        that served it, and the token counts."""
        text = None
        for block in getattr(response, "content", None) or []:
            if getattr(block, "type", None) == "text":
                text = block.text
                break
        usage = getattr(response, "usage", None)

        def count(name: str) -> int:
            return int(getattr(usage, name, 0) or 0)

        return LLMResult(
            text=text,
            stop_reason=getattr(response, "stop_reason", None),
            model=str(getattr(response, "model", "") or ""),
            input_tokens=count("input_tokens"),
            output_tokens=count("output_tokens"),
            cached_tokens=count("cache_read_input_tokens"),
            seconds=seconds,
        )
