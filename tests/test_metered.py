"""The spend caps (Phase 8.3a, docs/phase8-plan.md 4.1).

Pinned: a scripted result of a million output tokens trips the table's
budget and the next call is refused as an error result rather than an
exception; an unpriced model is refused before any call; the daily cap
counts every table; the ledger lives in the store as one document a
day; and an inner exception adds nothing to the ledger.
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
