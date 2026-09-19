"""Model seats at a web table (Phase 8.3a, docs/phase8-plan.md 4.1).

Pinned, all on a scripted backend and never the API: that the lobby
offers no model seat and the form refuses one without a key; that with
a key a table with Plum on the model plays to the end through `work`,
one model decision per call, its remarks landing in the log; that the
answers are stored with their audit and the record carries `llm_log`
and ``kind="llm"`` with the model id; that a cold registry rebuilds the
table with zero backend calls and the same events; that the spend is
metered per table and a spent budget lets the character play on; and
that a headless twin -- the same table on a backend that never answers
-- is the game the characters play by themselves.
"""
from __future__ import annotations

import json

import pytest
from werkzeug.datastructures import MultiDict

from clude_core.events import RemarkEvent
from clude_llm import LLMResult
from clude_llm.metered import Ledger
from clude_storage import GameRecord, open_store
from clude_web import create_app, tables, users
from tests.test_web_tables import ANN, PASSWORD, csrf, login, new_table, play_out, poll, work

SEED = 11
SEATS = {"Scarlett": "me", "Plum": "llm", "White": "character", "Green": "floor"}


class KindBackend:
    """Answers every decision with option A and a line, and counts."""

    name = "kinds"
    model = "claude-opus-5"

    def __init__(self, tokens_out: int = 20) -> None:
        self.calls = 0
        self.tokens_out = tokens_out

    def complete(self, request):
        self.calls += 1
        if request.kind == "suggest":
            reply = {"suspect": "A", "weapon": "A", "say": "Let us see who flinches."}
        else:
            reply = {"choice": "A", "say": f"A {request.kind}, then."}
        return LLMResult(
            text=json.dumps(reply), stop_reason="end_turn", model=self.model,
            input_tokens=500, output_tokens=self.tokens_out,
        )


class Factory:
    def __init__(self, tokens_out: int = 20) -> None:
        self.backends: list = []
        self.tokens_out = tokens_out

    def __call__(self, model, key):
        backend = KindBackend(self.tokens_out)
        self.backends.append(backend)
        return backend

    @property
    def calls(self) -> int:
        return sum(b.calls for b in self.backends)


@pytest.fixture
def store(tmp_path):
    return open_store(str(tmp_path))


def make_app(tmp_path, store, factory=None, budget=2.0, daily_cap=10.0, key="test-key"):
    users.add_user(store, ANN, PASSWORD)
    users.mark_password_prompted(store, ANN)
    settings = {"TESTING": True, "STORE_URI": str(tmp_path)}
    if key is not None:
        settings.update({"LLM_KEY": key, "LLM_BUDGET": budget, "LLM_DAILY_CAP": daily_cap,
                         "LLM_BACKEND": factory or Factory()})
    return create_app(settings)


def test_without_a_key_the_lobby_offers_no_model_seat_and_the_form_refuses_one(tmp_path, store):
    app = make_app(tmp_path, store, key=None)
    ann = login(app, ANN)
    assert "on the model" not in ann.get("/").get_data(as_text=True)
    response = new_table(ann, SEATS, seed=SEED, expect=400)
    assert "no key" in response.get_data(as_text=True)


def test_with_a_key_the_lobby_offers_it_and_the_form_takes_a_budget(tmp_path, store):
    app = make_app(tmp_path, store)
    ann = login(app, ANN)
    page = ann.get("/").get_data(as_text=True)
    assert "Plum, on the model" in page and 'name="budget"' in page
    fields = [("csrf", csrf(ann)), ("seed", str(SEED)), ("budget", "0.75")]
    fields += [(f"seat-{t}", v) for t, v in SEATS.items()]
    response = ann.post("/tables", data=MultiDict(fields))
    assert response.status_code == 302
    table_id = response.headers["Location"].rstrip("/").split("/")[-1]
    document = app.extensions["tables"].document(table_id)
    assert document["llm"] == {"model": "claude-opus-5", "budget": 0.75, "spent": 0.0}
    bad = ann.post("/tables", data=MultiDict(fields[:2] + [("budget", "lots")] + fields[3:]))
    assert bad.status_code == 400 and "number of dollars" in bad.get_data(as_text=True)


def _play(app, ann, factory):
    table_id = new_table(ann, SEATS, seed=SEED)
    dids = []
    final = play_out(app, table_id, {ANN: ann}, on_payload=lambda p: dids.append(p.get("did")))
    return table_id, final, dids


def test_plum_on_the_model_plays_to_the_end_one_decision_per_work(tmp_path, store):
    factory = Factory()
    app = make_app(tmp_path, store, factory)
    ann = login(app, ANN)
    table_id, final, dids = _play(app, ann, factory)
    assert final["finished"] and factory.calls > 0
    assert "model" in dids, "no work call answered for the model seat"
    game = app.extensions["tables"].game(table_id)
    seat = game.suspects.index("Plum")
    llm_entries = [e for e in game.entries if e.get("by") == "llm"]
    assert llm_entries and all(e["seat"] == seat and e.get("audit") for e in llm_entries)
    assert all(e["audit"]["called"] in (True, False) and e["audit"]["kind"] for e in llm_entries)
    # On-turn lines only: an off-turn reaction (8.3b) is its own entry.
    remarks = [e for e in game.events if isinstance(e, RemarkEvent) and e.seat == seat and e.about != "reaction"]
    assert remarks, "Plum said nothing all game"
    # A line is stored on whichever answer's resume drained it: Plum's own,
    # or the refuter's when a person showed him a card.
    said = [line for e in game.entries if e.get("kind") == "answer" for who, line in e.get("said", []) if who == seat]
    assert [r.text for r in remarks] == said
    # The log shows the line to the person at the table.
    page = poll(ann, table_id)
    texts = [e["text"] for e in page["events"] if e["kind"] == "remark"]
    assert any(remarks[0].text in t for t in texts)
    # The record carries the audit and the model.
    ref = app.extensions["tables"].document(table_id)["record"]
    record = GameRecord.from_dict(store.get_game(ref["run_id"], ref["index"]))
    assert record.seats[seat].kind == "llm" and record.seats[seat].model == "claude-opus-5"
    assert record.llm_log and set(record.llm_log) == {seat}
    assert len(record.llm_log[seat]) == len(llm_entries)
    # Spend was metered per table, in the ledger and on the document.
    assert Ledger(store).spent(table_id) > 0
    assert app.extensions["tables"].document(table_id)["llm"]["spent"] == pytest.approx(Ledger(store).spent(table_id), abs=1e-4)


def test_a_cold_registry_rebuilds_a_model_table_with_no_call(tmp_path, store, monkeypatch):
    # Off-turn talk is made certain and immediate, so the rebuild is proved
    # over a served reaction too (8.3d: the seat that said one must
    # remember it, and its decision, after a rebuild).
    from clude_web import chat
    monkeypatch.setattr(chat, "delay", lambda rng: 0.0)
    monkeypatch.setattr(chat, "joins", lambda rng, p: True)
    factory = Factory()
    app = make_app(tmp_path, store, factory)
    ann = login(app, ANN)
    table_id = new_table(ann, SEATS, seed=SEED)
    assert ann.post(f"/tables/{table_id}/say", data={"csrf": csrf(ann), "text": "Good evening, all."}).status_code == 200
    tables.WORK_INTERVAL, saved = 0.0, tables.WORK_INTERVAL
    try:
        payload = poll(ann, table_id)
        steps = 0
        while not payload["finished"] and steps < 400 and payload["turns"] < 8:
            steps += 1
            if payload["waiting"] is not None and payload["waiting"]["seat"] == 0:
                mine = poll(ann, table_id)
                from tests.test_web_tables import answer, simple_answer
                payload = answer(ann, table_id, mine["pending"]["seq"], simple_answer(mine["pending"]))
            else:
                payload = work(ann, table_id)
    finally:
        tables.WORK_INTERVAL = saved
    live = app.extensions["tables"].game(table_id)
    assert any(e.get("by") == "llm" for e in live.entries)
    reactions = [e for e in live.entries if e.get("kind") == "reaction"]
    assert reactions and all(e.get("audit") for e in reactions), "no reaction was served, or one without its audit"
    calls_before = factory.calls
    cold = tables.TableRegistry(store, app.extensions["tables"].llm)
    again = cold.game(table_id)
    assert factory.calls == calls_before, "the rebuild called the model"
    assert [repr(e) for e in again.events] == [repr(e) for e in live.events]
    def pause(game):
        return None if game.pending is None else (game.pending.seat, game.pending.kind)

    assert pause(again) == pause(live) and again.turns == live.turns
    plum = live.suspects.index("Plum")
    assert again.wrappers[plum].transcript == live.wrappers[plum].transcript
    assert len(again.wrappers[plum].decisions) == len(live.wrappers[plum].decisions)


def test_a_spent_budget_lets_the_character_play_on(tmp_path, store):
    factory = Factory(tokens_out=100_000)  # $2.50 a call
    app = make_app(tmp_path, store, factory, budget=2.0)
    ann = login(app, ANN)
    table_id, final, _dids = _play(app, ann, factory)
    assert final["finished"]
    assert factory.calls == 1, "the second call should have been refused by the budget"
    game = app.extensions["tables"].game(table_id)
    audits = [e["audit"] for e in game.entries if e.get("by") == "llm" and e.get("audit")]
    fallbacks = [a["fallback"] for a in audits if a["called"] or a["fallback"]]
    assert any(f and f.startswith("error: budget") for f in fallbacks)
    assert final["llm"]["refused"], final["llm"]


def test_the_null_twin_is_the_headless_game(tmp_path, store):
    """A model seat whose backend never answers plays the character's own
    game: the same table with Plum as a plain character."""
    from clude_llm import NullBackend
    from clude_training.table import SeatSpec, TableGame, TableSetup

    def seats(kind):
        return (SeatSpec("Scarlett", "floor"), SeatSpec("Plum", kind, "Plum"),
                SeatSpec("White", "character", "White"), SeatSpec("Green", "floor"))

    twin = TableGame(TableSetup(seats("llm"), SEED), llm_backend=lambda seat: NullBackend())
    while not twin.finished:
        if twin.pending is None:
            twin.run(1)
        else:
            twin.llm_answer()
    plain = TableGame(TableSetup(seats("character"), SEED))
    plain.play_to_end()
    assert [repr(e) for e in twin.events] == [repr(e) for e in plain.events]
