"""The spend caps (Phase 8.3a, docs/phase8-plan.md 4.1).

Pinned: a scripted result of a million output tokens trips the table's
budget and the next call is refused as an error result rather than an
exception; an unpriced model is refused before any call; the daily cap
counts every table; the ledger lives in the store as one document a
day; and an inner exception adds nothing to the ledger. Since Phase 9g,
also one document a table, split by seat, and a table's budget that
holds across midnight UTC, where it used to start again.
"""
from __future__ import annotations

import pytest

from clude_llm import LLMRequest, LLMResult, ScriptedBackend
from clude_llm.metered import Ledger, MeteredBackend
from clude_storage import open_store

REQUEST = LLMRequest(system="s", user="u", schema={}, kind="move")


def _result(output_tokens: int, model: str = "claude-opus-5") -> LLMResult:
    return LLMResult(text='{"choice": "A", "say": ""}', stop_reason="end_turn", model=model,
                     input_tokens=1000, output_tokens=output_tokens)


@pytest.fixture
def store(tmp_path):
    return open_store(str(tmp_path))


@pytest.fixture
def ledger(store):
    return Ledger(store, today=lambda: "2026-09-19")


def test_a_huge_reply_trips_the_table_budget_and_the_next_call_is_refused(store, ledger):
    inner = ScriptedBackend([_result(1_000_000), _result(10)])
    metered = MeteredBackend(inner, ledger, "t1", per_table_cap=2.0, daily_cap=10.0, model="claude-opus-5")
    first = metered.complete(REQUEST)
    assert first.ok and inner.calls == 1
    assert metered.spent() == pytest.approx(25.005, abs=1e-6)  # $25 out + $0.005 in
    second = metered.complete(REQUEST)
    assert not second.ok and second.error.startswith("budget: this table's $2.00 is spent")
    assert inner.calls == 1, "the refusal never reached the inner backend"
    assert metered.refused == 1 and metered.last_refusal == second.error
    document = store.get_doc(Ledger.key("2026-09-19"))
    assert document["tables"] == {"t1": pytest.approx(25.005)} and document["total"] == pytest.approx(25.005)


def test_an_unpriced_model_is_refused_before_any_call(ledger):
    inner = ScriptedBackend([_result(10)])
    metered = MeteredBackend(inner, ledger, "t1", 2.0, 10.0, model="claude-mystery-9")
    result = metered.complete(REQUEST)
    assert not result.ok and "no price" in result.error
    assert inner.calls == 0 and ledger.today() == 0.0


def test_the_daily_cap_counts_every_table(ledger):
    a = MeteredBackend(ScriptedBackend([_result(200_000)]), ledger, "a", 100.0, 8.0, model="claude-opus-5")
    b = MeteredBackend(ScriptedBackend([_result(10)]), ledger, "b", 100.0, 8.0, model="claude-opus-5")
    assert a.complete(REQUEST).ok  # $5.005 today
    assert b.complete(REQUEST).ok  # b's own table is fresh, the day is under $8
    assert b.complete(REQUEST).ok
    c = MeteredBackend(ScriptedBackend([_result(200_000)]), ledger, "c", 100.0, 8.0, model="claude-opus-5")
    assert c.complete(REQUEST).ok  # now past $8
    refused = b.complete(REQUEST)
    assert not refused.ok and refused.error.startswith("budget: today's $8.00 is spent")


def test_the_ledger_is_one_document_a_day_and_survives_a_fresh_ledger(store):
    first = Ledger(store, today=lambda: "2026-09-19")
    first.add("t1", 0.25)
    first.add("t2", 0.5)
    again = Ledger(store, today=lambda: "2026-09-19")
    assert again.spent("t1") == 0.25 and again.today() == 0.75
    assert Ledger(store, today=lambda: "2026-09-20").today() == 0.0
    assert store.list_docs("spend") == ["2026-09-19"]


def test_an_inner_exception_propagates_and_adds_nothing(ledger):
    metered = MeteredBackend(ScriptedBackend([RuntimeError("boom")]), ledger, "t1", 2.0, 10.0, model="claude-opus-5")
    with pytest.raises(RuntimeError):
        metered.complete(REQUEST)
    assert ledger.today() == 0.0 and metered.calls == 0


def test_the_price_follows_the_reply_model_when_it_is_priced(ledger):
    inner = ScriptedBackend([_result(1_000_000, model="claude-haiku-4-5")])
    metered = MeteredBackend(inner, ledger, "t1", 100.0, 100.0, model="claude-opus-5")
    assert metered.complete(REQUEST).ok
    assert metered.spent() == pytest.approx(5.001)


def test_the_table_document_splits_the_spend_by_seat(store, ledger):
    """Phase 9g: each seat's backend counts toward its own share of the
    table's spend as well as the table's and the day's totals."""
    a = MeteredBackend(ScriptedBackend([_result(1000)]), ledger, "t1", 100.0, 100.0, model="claude-opus-5", seat=0)
    b = MeteredBackend(ScriptedBackend([_result(3000)]), ledger, "t1", 100.0, 100.0, model="claude-opus-5", seat=2)
    assert a.complete(REQUEST).ok and b.complete(REQUEST).ok
    fresh = Ledger(store, today=lambda: "2026-09-19")  # read back from the store, not memory
    table = fresh.table("t1")
    assert table["seats"] == {"0": pytest.approx(0.03), "2": pytest.approx(0.08)}
    assert table["total"] == pytest.approx(0.11) == fresh.read()["tables"]["t1"]
    assert fresh.seat_spent("t1", 2) == pytest.approx(0.08) and fresh.seat_spent("t1", 1) == 0.0
    assert store.list_docs("spend") == ["2026-09-19"], "a table document is not a day"
    assert store.list_docs("spend/tables") == ["t1"]


def test_a_table_budget_holds_across_midnight(store):
    """Phase 9g: the budget is the table's, not the day's. Before, the
    third call here was allowed, since the new day's ledger had only
    $1.505 of this table's $3.01 on it."""
    day = ["2026-09-19"]
    ledger = Ledger(store, today=lambda: day[0])
    inner = ScriptedBackend([_result(60_000), _result(60_000), _result(10)])
    metered = MeteredBackend(inner, ledger, "t1", per_table_cap=2.0, daily_cap=10.0, model="claude-opus-5", seat=1)
    assert metered.complete(REQUEST).ok  # $1.505 on the 19th
    day[0] = "2026-09-20"
    assert metered.complete(REQUEST).ok  # $3.01 in all, $1.505 of it today
    assert ledger.spent("t1") == pytest.approx(3.01) and ledger.today() == pytest.approx(1.505)
    assert ledger.days_total("t1") == pytest.approx(3.01)
    refused = metered.complete(REQUEST)
    assert not refused.ok and refused.error.startswith("budget: this table's $2.00 is spent")
    assert inner.calls == 2


def test_the_daily_ledgers_price_a_table_that_has_no_document(store):
    """What the backfill reads for a game played before table documents:
    the daily documents, summed, whatever else they hold."""
    store.put_doc(Ledger.key("2026-09-18"), {"date": "2026-09-18", "total": 1.0, "tables": {"old": 0.25, "x": 0.75}})
    store.put_doc(Ledger.key("2026-09-19"), {"date": "2026-09-19", "total": 0.1, "tables": {"old": 0.1}})
    ledger = Ledger(store, today=lambda: "2026-09-19")
    assert ledger.days_total("old") == pytest.approx(0.35)
    assert ledger.table("old") == {"table": "old", "total": 0.0, "seats": {}}
