"""Spend caps for the model on the web (Phase 8.3a, docs/phase8-plan.md 4.1).

`MeteredBackend` wraps any backend and prices every call with
`estimate_cost`, keeping the running total in a `Ledger`: one document a
day in the store (``spend/<date>.json``) with the day's total and each
table's share. Before a call it refuses -- with an error `LLMResult`,
never an exception -- when the model is unpriced, when the table has
spent its budget, or when the day has spent its cap; the wrapper's own
fallback then plays the headless character, exactly as it does for a
timeout, and the audit's `fallback` says ``error: budget: ...``. After a
call it adds the cost, so one call may run a few cents past a cap and
never more.

The ledger is read-modify-write under a process lock: a store put per
call is a round trip on GCS, which is nothing beside a 2-3 s model call,
and the service runs one instance, so the lock is the whole story.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Callable, Optional

from .anthropic_backend import PRICES_PER_MTOK, estimate_cost
from .backend import DEFAULT_MODEL, LLMBackend, LLMRequest, LLMResult

SPEND_PREFIX = "spend"
"""Where the daily ledgers live in the store."""


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class Ledger:
    """The store's daily spend documents.

    Parameters
    ----------
    store : RecordStore
        Any store with the generic document methods.
    today : Callable[[], str] or None
        The date the ledger is for, as ``YYYY-MM-DD``; default UTC today.
        Injected by tests.
    """

    _lock = threading.Lock()

    def __init__(self, store, today: Optional[Callable[[], str]] = None) -> None:
        self.store = store
        self._today = today or today_utc

    @staticmethod
    def key(date: str) -> str:
        return f"{SPEND_PREFIX}/{date}.json"

    def read(self, date: Optional[str] = None) -> dict:
        """The day's document: ``{"date", "total", "tables": {id: dollars}}``,
        empty when nothing was spent."""
        date = date or self._today()
        try:
            document = self.store.get_doc(self.key(date))
        except KeyError:
            return {"date": date, "total": 0.0, "tables": {}}
        document.setdefault("date", date)
        document.setdefault("total", 0.0)
        document.setdefault("tables", {})
        return document

    def spent(self, table_id: str) -> float:
        """Dollars this table has spent today."""
        return float(self.read()["tables"].get(table_id, 0.0))

    def today(self) -> float:
        """Dollars spent today across every table."""
        return float(self.read()["total"])

    def add(self, table_id: str, dollars: float) -> dict:
        """Add one call's cost to the table's and the day's totals."""
        with self._lock:
            document = self.read()
            document["total"] = round(float(document["total"]) + dollars, 6)
            tables = document["tables"]
            tables[table_id] = round(float(tables.get(table_id, 0.0)) + dollars, 6)
            self.store.put_doc(self.key(document["date"]), document)
            return document


class MeteredBackend:
    """A backend under two caps: the table's budget and the day's.

    Parameters
    ----------
    inner : LLMBackend
        The backend that actually answers.
    ledger : Ledger
    table_id : str
        Whose budget the calls count against.
    per_table_cap, daily_cap : float
        Dollars; a call is refused once either total is at its cap.
    model : str or None
        The model id to price with; default `inner.model` if it has one,
        else `DEFAULT_MODEL`. An unpriced model is refused, not uncapped.
    """

    name = "metered"

    def __init__(
        self,
        inner: LLMBackend,
        ledger: Ledger,
        table_id: str,
        per_table_cap: float,
        daily_cap: float,
        model: Optional[str] = None,
    ) -> None:
        self.inner = inner
        self.ledger = ledger
        self.table_id = table_id
        self.per_table_cap = float(per_table_cap)
        self.daily_cap = float(daily_cap)
        self.model = model or getattr(inner, "model", None) or DEFAULT_MODEL
        self.calls = 0
        self.refused = 0
        self.last_refusal: Optional[str] = None
        self.known_spent = self.ledger.spent(table_id)
        """The table's spend as last read or added here, for a screen
        that must not read the store on every poll."""

    def refusal(self) -> Optional[str]:
        """Why the next call would be refused, or None."""
        if estimate_cost(self.model, 1, 1) is None:
            return f"budget: {self.model} has no price"
        if self.ledger.spent(self.table_id) >= self.per_table_cap:
            return f"budget: this table's ${self.per_table_cap:.2f} is spent"
        if self.ledger.today() >= self.daily_cap:
            return f"budget: today's ${self.daily_cap:.2f} is spent"
        return None

    def spent(self) -> float:
        return self.ledger.spent(self.table_id)

    def complete(self, request: LLMRequest) -> LLMResult:
        why = self.refusal()
        if why is not None:
            self.refused += 1
            self.last_refusal = why
            return LLMResult(error=why)
        self.last_refusal = None
        result = self.inner.complete(request)
        self.calls += 1
        priced = result.model if result.model in PRICES_PER_MTOK else self.model
        cost = estimate_cost(priced, result.input_tokens, result.output_tokens, result.cached_tokens)
        if cost:
            document = self.ledger.add(self.table_id, cost)
            self.known_spent = float(document["tables"].get(self.table_id, 0.0))
        return result


__all__ = ["Ledger", "MeteredBackend", "SPEND_PREFIX", "today_utc"]
