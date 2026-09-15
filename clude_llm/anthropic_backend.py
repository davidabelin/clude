"""The real backend: Claude, through Anthropic's Python SDK (Phase 6c).

One `messages.create` per decision: the persona + rules as a cached
system block, the per-turn text as the user message, the fixed JSON
schema as `output_config.format`, and a low effort setting, since a
Clue move is a short pick. A character's logbook block (Phase 7), when
it has one, goes as a second cached system block: stable for a whole
game, so it is written to the cache once and read cheaply after, while
the persona block stays the prefix every game shares. A request may
override effort and `max_tokens` (the debrief does). Credentials resolve exactly as the SDK does
(`ANTHROPIC_API_KEY`, or an `ant auth login` profile); an explicit
`api_key` wins, and a `client` double can be injected for tests, the way
`clude_storage.GcsStore` takes one. Nothing here prints or stores a key.

Every failure -- a rate limit, a timeout, a bad request, no credentials
-- comes back as an `LLMResult` with `error` set rather than raising:
the wrapper's answer to any failure is the character's own decision, and
nothing is retried at this layer beyond the SDK's own `max_retries`.
The SDK is imported lazily, so the rest of the package (and the test
suite) needs no network and no package unless this backend is opened.
"""
from __future__ import annotations

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
        With a `request.memory` the system prompt is two cached blocks,
        persona then logbook; the request's `effort` and `max_tokens`
        win over the backend's when set."""
        system = [{"type": "text", "text": request.system, "cache_control": {"type": "ephemeral"}}]
        if request.memory:
            system.append(
                {"type": "text", "text": request.memory, "cache_control": {"type": "ephemeral"}}
            )
        return {
            "model": self.model,
            "max_tokens": request.max_tokens or self.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": request.user}],
            "output_config": {
                "format": {"type": "json_schema", "schema": request.schema},
                "effort": request.effort or self.effort,
            },
        }

    def complete(self, request: LLMRequest) -> LLMResult:
        started = time.perf_counter()
        try:
            params = self.params(request)
            if self.server_fallbacks:
                response = self.client.beta.messages.create(
                    betas=[FALLBACK_BETA], fallbacks="default", **params
                )
            else:
                response = self.client.messages.create(**params)
        except Exception as exc:  # every SDK error class is a fallback here, none is retried
            return LLMResult(
                error=f"{type(exc).__name__}: {exc}",
                model=self.model,
                seconds=time.perf_counter() - started,
            )
        return self.to_result(response, time.perf_counter() - started)

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
