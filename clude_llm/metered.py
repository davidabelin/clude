"""Spend caps for the model on the web (Phase 8.3a, docs/phase8-plan.md 4.1).

`MeteredBackend` wraps any backend and prices every call with
`estimate_cost`, keeping the running totals in a `Ledger`: one document a
day in the store (``spend/<date>.json``) with the day's total and each
table's share, and one document a table (``spend/tables/<id>.json``)
with the table's total and each seat's share (Phase 9g). Before a call it
refuses -- with an error `LLMResult`, never an exception -- when the
model is unpriced, when the table has spent its budget, or when the day
has spent its cap; the wrapper's own fallback then plays the headless
character, exactly as it does for a timeout, and the audit's `fallback`
says ``error: budget: ...``. After a call it adds the cost, so one call
may run a few cents past a cap and never more.

A table's budget is the table's, whatever the date: until Phase 9g it
was read from the day's document alone, so a game that crossed midnight
UTC (8 pm Eastern) started its budget again and its screen froze at the
figure it had reached before midnight.

The ledger is read-modify-write under a process lock: a store put per
call is a round trip on GCS, which is nothing beside a 2-3 s model call,
and the service runs one instance, so the lock is the whole story. For
the same reason a `Ledger` keeps the table documents it has read or
written in memory, so a screen polling every few seconds never reads
the store for them.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Callable, Optional

from .anthropic_backend import PRICES_PER_MTOK, estimate_cost
from .backend import DEFAULT_MODEL, LLMBackend, LLMRequest, LLMResult

SPEND_PREFIX = "spend"
"""Where the daily ledgers live in the store."""

TABLES_FOLDER = "tables"
"""The folder under `SPEND_PREFIX` holding one document a table."""


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class Ledger:
    """The store's spend documents: one a day, one a table.

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
        self._tables: dict = {}

    @staticmethod
    def key(date: str) -> str:
        return f"{SPEND_PREFIX}/{date}.json"

    @staticmethod
    def table_key(table_id: str) -> str:
        return f"{SPEND_PREFIX}/{TABLES_FOLDER}/{table_id}.json"

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

    def _read_table(self, table_id: str) -> dict:
        try:
            document = self.store.get_doc(self.table_key(table_id))
        except (KeyError, ValueError):
            document = {}
        document.setdefault("table", table_id)
        document.setdefault("total", 0.0)
        document.setdefault("seats", {})
        return document

    def table(self, table_id: str, fresh: bool = False) -> dict:
        """The table's document: ``{"table", "total", "seats": {"<seat>":
        dollars}}``, whatever the dates it was spent on; zeros for a table
        that has spent nothing. Kept in memory once read, so a screen
        polling every few seconds does not read the store; `fresh` reads
        it again. The copy returned is the caller's to keep."""
        with self._lock:
            if fresh or table_id not in self._tables:
                self._tables[table_id] = self._read_table(table_id)
            document = self._tables[table_id]
            return {"table": document["table"], "total": document["total"], "seats": dict(document["seats"])}

    def spent(self, table_id: str) -> float:
        """Dollars this table has spent, on every day it was played."""
        return float(self.table(table_id)["total"])

    def seat_spent(self, table_id: str, seat: int) -> float:
        """Dollars one seat of this table has spent."""
        return float(self.table(table_id)["seats"].get(str(seat), 0.0))

    def today(self) -> float:
        """Dollars spent today across every table."""
        return float(self.read()["total"])

    def days_total(self, table_id: str) -> float:
        """What this table spent, summed from the daily documents: the one
        place spend was recorded before the table documents (Phase 9g),
        so the way to price a game played before them. Reads every day's
        document, so it is for the CLI, never a request."""
        total = 0.0
        for date in self.store.list_docs(SPEND_PREFIX):
            total += float(self.read(date)["tables"].get(table_id, 0.0))
        return round(total, 6)

    def add(self, table_id: str, dollars: float, seat: Optional[int] = None) -> dict:
        """Add one call's cost to the day's totals and to the table's,
        and to `seat`'s share of the table's when a seat is given.
        Returns the table's document."""
        with self._lock:
            document = self.read()
            document["total"] = round(float(document["total"]) + dollars, 6)
            tables = document["tables"]
            tables[table_id] = round(float(tables.get(table_id, 0.0)) + dollars, 6)
            self.store.put_doc(self.key(document["date"]), document)

            table = self._tables.get(table_id) or self._read_table(table_id)
            table["total"] = round(float(table["total"]) + dollars, 6)
            if seat is not None:
                seats = table["seats"]
                seats[str(seat)] = round(float(seats.get(str(seat), 0.0)) + dollars, 6)
            self.store.put_doc(self.table_key(table_id), table)
            self._tables[table_id] = table
            return {"table": table["table"], "total": table["total"], "seats": dict(table["seats"])}


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
    seat : int or None
        The seat the calls are made for, whose share of the table's spend
        they count toward (Phase 9g); None counts them to the table alone.
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
        seat: Optional[int] = None,
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
        self.seat = seat

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
            self.ledger.add(self.table_id, cost, self.seat)
        return result


__all__ = ["Ledger", "MeteredBackend", "SPEND_PREFIX", "TABLES_FOLDER", "today_utc"]
