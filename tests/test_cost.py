"""What a game cost (Phase 9g, docs/phase9-plan.md 8).

Pinned, on scripted backends that report tokens and never the API:

- a web table's view carries its spend split by seat, adding up to the
  total;
- the cost is recorded only once the last logbook entry is written, and
  includes those entries -- on the table document, the record, each model
  seat of the record and the web run's line for the game -- while the
  logbook entries themselves never mention it;
- a table that writes no entries records it at the finish;
- a game with no model seat records none, and reads exactly as before;
- a cold registry settles the same figures;
- a table ended while it was still writing its entries records what it
  spent;
- the lobby's list of games shows the cost, and the lobby its run total;
- an MCP player is told the split in one line, on every reply;
- an arena game's record and summary line carry what its LLM seats spent,
  the logbook entry included, and a headless run carries nothing;
- `tables costs` prices a game recorded before costs were from the daily
  ledgers, printing first and writing only with ``--write``.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from clude_llm import LOGBOOK_KIND, LLMResult
from clude_llm.anthropic_backend import estimate_cost
from clude_llm.metered import Ledger, today_utc
from clude_storage import GameRecord, Logbook, open_store
from clude_storage.logbooks import entry_key
from clude_training.table import SeatSpec, TableSetup
from clude_web import mcp, tables
from tests.test_debrief import DEBRIEF
from tests.test_web_llm import make_app
from tests.test_web_tables import ANN, login, new_table, play_out, poll, work

SEED = 11
MODEL = "claude-opus-5"
SEATS = {"Scarlett": "me", "Plum": "llm", "White": "llm", "Green": "floor"}
DECISION_TOKENS = (400, 30)
DEBRIEF_TOKENS = (6000, 900)
DEBRIEF_PRICE = estimate_cost(MODEL, *DEBRIEF_TOKENS)

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "clude_cli.py"


class Priced:
    """Answers every decision with option A and silence, and every
    logbook entry with `DEBRIEF`, at token counts that price the entry
    well apart from a decision."""

    name = "priced"
    model = MODEL

    def __init__(self) -> None:
        self.requests: list = []

    def complete(self, request):
        self.requests.append(request)
        tokens = DECISION_TOKENS
        if request.kind == LOGBOOK_KIND:
            reply = dict(DEBRIEF, dossiers=[{"opponent": "ann", "read": "Quiet."}])
            tokens = DEBRIEF_TOKENS
        elif request.kind == "suggest":
            reply = {"suspect": "A", "weapon": "A", "say": ""}
        elif request.kind == "remark":
            reply = {"say": ""}
        else:
            reply = {"choice": "A", "say": ""}
        return LLMResult(text=json.dumps(reply), stop_reason="end_turn", model=self.model,
                         input_tokens=tokens[0], output_tokens=tokens[1])


class Factory:
    def __init__(self) -> None:
        self.backends: list = []

    def __call__(self, model, key):
        backend = Priced()
        self.backends.append(backend)
        return backend


@pytest.fixture
def store(tmp_path):
    return open_store(str(tmp_path))


@pytest.fixture
def app(tmp_path, store):
    return make_app(tmp_path, store, Factory())


@pytest.fixture
def ann(app):
    return login(app, ANN)


def _record(store, document) -> GameRecord:
    ref = document["record"]
    return GameRecord.from_dict(store.get_game(ref["run_id"], ref["index"]))


def _line(store, document) -> dict:
    ref = document["record"]
    return next(g for g in store.get_run(ref["run_id"])["games"] if g["game_index"] == ref["index"])


def _finished(app, ann, seats=SEATS, remember=True):
    table_id = new_table(ann, seats, seed=SEED, remember=remember)
    final = play_out(app, table_id, {ANN: ann})
    assert final["finished"]
    return table_id, final


def test_the_cost_is_recorded_last_after_every_logbook_entry(app, store, ann):
    table_id, final = _finished(app, ann)
    registry = app.extensions["tables"]
    game = registry.game(table_id)
    plum, white = game.suspects.index("Plum"), game.suspects.index("White")

    # The view splits the spend by seat, and only model seats spend.
    llm = poll(ann, table_id)["llm"]
    assert set(llm["seats"]) <= {str(plum), str(white)} and llm["seats"]
    assert sum(llm["seats"].values()) == pytest.approx(llm["spent"], abs=1e-3)

    # Over, but its entries are still to write: nothing is recorded yet.
    document = registry.document(table_id)
    assert tables.pending_debriefs(document) == sorted([plum, white])
    assert _record(store, document).cost is None and "cost" not in _line(store, document)
    assert not document["llm"].get("final")
    before = Ledger(store).spent(table_id)
    assert work(ann, table_id)["did"] == "debrief"
    assert _record(store, document).cost is None, "recorded before the last entry was in"
    assert work(ann, table_id)["did"] == "debrief"

    ledger = Ledger(store)
    total = ledger.spent(table_id)
    assert total == pytest.approx(before + 2 * DEBRIEF_PRICE), "the entries are not in the cost"
    document = registry.document(table_id)
    record = _record(store, document)
    assert record.cost == pytest.approx(total)
    assert record.seats[plum].cost == pytest.approx(ledger.seat_spent(table_id, plum))
    assert record.seats[white].cost == pytest.approx(ledger.seat_spent(table_id, white))
    assert record.seats[plum].cost + record.seats[white].cost == pytest.approx(total)
    assert all(s.cost is None for s in record.seats if s.kind != "llm")
    assert _line(store, document)["cost"] == pytest.approx(total)
    assert document["llm"]["final"] and document["llm"]["spent"] == pytest.approx(total)
    assert poll(ann, table_id)["llm"]["spent"] == pytest.approx(total, abs=1e-4)

    # The characters were not told: their entries say nothing of it.
    for label in ("Plum", "White"):
        serial = Logbook(store, label).serials()[-1]
        assert "cost" not in store.get_doc(entry_key(label, serial))

    # The lobby's list of games shows it, and the lobby the run's total.
    page = ann.get("/runs/web").get_data(as_text=True)
    assert f"${total:.2f}" in page and "Spent with Claude in all" in page
    assert f"${total:.2f} with Claude" in ann.get("/").get_data(as_text=True)


def test_a_table_that_writes_no_entries_records_its_cost_at_the_finish(app, store, ann):
    table_id, _final = _finished(app, ann, remember=False)
    document = app.extensions["tables"].document(table_id)
    total = Ledger(store).spent(table_id)
    assert total > 0
    assert _record(store, document).cost == pytest.approx(total)
    assert _line(store, document)["cost"] == pytest.approx(total)
    assert document["llm"]["final"]


def test_a_game_with_no_model_seat_records_no_cost(app, store, ann):
    table_id, final = _finished(app, ann, seats={"Scarlett": "me", "White": "character", "Green": "floor"})
    assert final["llm"] is None
    document = app.extensions["tables"].document(table_id)
    ref = document["record"]
    raw = store.get_game(ref["run_id"], ref["index"])
    assert "cost" not in raw and all("cost" not in seat for seat in raw["seats"])
    assert "cost" not in _line(store, document)
    page = ann.get("/runs/web").get_data(as_text=True)
    assert "no LLM seat, or not recorded" in page and "Spent with Claude in all" not in page


def test_a_cold_registry_settles_the_same_figures(app, store, ann):
    table_id, _final = _finished(app, ann)
    cold = tables.TableRegistry(store, app.extensions["tables"].llm)
    game = cold.game(table_id)
    assert cold.work(table_id, game) == "debrief"
    assert cold.work(table_id, game) == "debrief"
    ledger = Ledger(store)
    document = cold.document(table_id)
    record = _record(store, document)
    assert record.cost == pytest.approx(ledger.spent(table_id))
    for seat in (game.suspects.index("Plum"), game.suspects.index("White")):
        assert record.seats[seat].cost == pytest.approx(ledger.seat_spent(table_id, seat))
    assert document["llm"]["final"]


def test_a_table_ended_while_writing_its_entries_records_what_it_spent(app, store, ann):
    table_id, _final = _finished(app, ann)
    registry = app.extensions["tables"]
    assert work(ann, table_id)["did"] == "debrief"
    registry.abandon(table_id)
    document = registry.document(table_id)
    assert document["status"] == "abandoned" and document["llm"]["final"]
    assert _record(store, document).cost == pytest.approx(Ledger(store).spent(table_id))
    assert _line(store, document)["cost"] == pytest.approx(Ledger(store).spent(table_id))


def test_an_mcp_player_is_told_the_split_in_one_line_on_every_reply(store, monkeypatch):
    monkeypatch.setattr(tables, "WORK_INTERVAL", 0.0)
    registry = tables.TableRegistry(store, tables.LLMConfig(key="k", make_backend=Factory()))
    seats = (SeatSpec("Scarlett", "human", "claude"), SeatSpec("Plum", "llm", "Plum"), SeatSpec("Green", "floor"))
    table_id = registry.create(TableSetup(seats, SEED), started_by="claude")
    game = registry.game(table_id)
    for _ in range(2000):
        if registry.ledger.spent(table_id) > 0 or game.finished:
            break
        if game.pending is not None and game.pending.seat == 0:
            registry.answer(table_id, game, 0, game.seq, game.stand_in_answer())
        else:
            registry.work(table_id, game)
    assert registry.ledger.spent(table_id) > 0, "Plum never asked the model"
    view = mcp.seat_view(registry, table_id, game, 0)
    assert view["cost"] == "Model spend ${:.2f} of $2.00: Plum 100%; everyone else 0%.".format(
        registry.ledger.spent(table_id)
    )
    quiet = mcp.seat_view(registry, table_id, game, 0, since=game.snapshot.n_events)
    assert quiet["seats"] == "unchanged" and quiet["cost"] == view["cost"]


def test_the_cost_line_in_words():
    seats = [{"seat": 0, "token": "Scarlett"}, {"seat": 1, "token": "Mustard"}, {"seat": 2, "token": "Peacock"}]
    view = {"llm": {"spent": 0.39, "budget": 2.0, "seats": {"0": 0.16, "2": 0.23}}, "seats": seats}
    assert mcp.cost_line(view) == "Model spend $0.39 of $2.00: Scarlett 41%, Peacock 59%; everyone else 0%."
    view["seats"] = [seats[0], seats[2]]
    assert mcp.cost_line(view) == "Model spend $0.39 of $2.00: Scarlett 41%, Peacock 59%."
    idle = {"llm": {"spent": 0.0, "budget": 2.0, "seats": {}}, "seats": seats}
    assert mcp.cost_line(idle) == "Model spend $0.00 of $2.00."
    assert mcp.cost_line({"llm": None, "seats": seats}) is None


def test_an_arena_game_records_what_its_llm_seats_spent(tmp_path):
    from clude_llm import LLMSettings
    from clude_training.arena import run_arena

    store = open_store(str(tmp_path))
    run_arena(
        n_games=2, seed=9, roster=("Scarlett", "floor"), player_counts=(3,), max_turns=60,
        llm_backend=Priced(), logbook_store=store, store=store, run_id="costly",
    )
    model = LLMSettings().model
    for line in store.get_run("costly")["games"]:
        record = GameRecord.from_dict(store.get_game("costly", line["game_index"]))
        (seat,) = [s for s in record.seats if s.kind == "llm"]
        audits = record.llm_log[seat.seat]
        played = estimate_cost(
            model, sum(a["input_tokens"] for a in audits), sum(a["output_tokens"] for a in audits)
        )
        assert seat.cost == pytest.approx(played + estimate_cost(model, *DEBRIEF_TOKENS)), "the entry is not in it"
        assert record.cost == pytest.approx(seat.cost) and line["cost"] == pytest.approx(record.cost)
        assert all(s.cost is None for s in record.seats if s.kind != "llm")

    run_arena(n_games=1, seed=9, roster=("Scarlett", "floor"), player_counts=(3,), max_turns=60,
              store=store, run_id="free")
    assert "cost" not in store.get_run("free")["games"][0]
    raw = store.get_game("free", 0)
    assert "cost" not in raw and all("cost" not in seat for seat in raw["seats"])


@pytest.fixture(scope="module")
def cli():
    spec = importlib.util.spec_from_file_location("clude_cli", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tables_costs_prices_an_older_game_from_the_daily_ledgers(app, store, ann, tmp_path, cli, capsys):
    table_id, _final = _finished(app, ann, remember=False)
    registry = app.extensions["tables"]
    total = Ledger(store).spent(table_id)

    # Make it a game recorded before 9g: no table ledger, no cost anywhere,
    # and its spend over two days' documents.
    store.delete_doc(Ledger.table_key(table_id))
    today = Ledger.key(today_utc())
    day = store.get_doc(today)
    day["tables"][table_id] = round(total - 0.01, 6)
    store.put_doc(today, day)
    store.put_doc(Ledger.key("2026-09-01"), {"date": "2026-09-01", "total": 0.01, "tables": {table_id: 0.01}})
    document = registry.document(table_id)
    document["llm"] = {"model": MODEL, "budget": 2.0, "spent": 0.0}
    store.put_doc(tables.table_key(table_id), document)
    ref = document["record"]
    raw = store.get_game(ref["run_id"], ref["index"])
    raw.pop("cost")
    for seat in raw["seats"]:
        seat.pop("cost", None)
    store.put_game(ref["run_id"], ref["index"], raw)
    summary = store.get_run(ref["run_id"])
    for line in summary["games"]:
        line.pop("cost", None)
    store.put_run(ref["run_id"], summary)

    assert cli.main(["tables", "costs", "--uri", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert table_id in out and f"${total:.4f}" in out and "not recorded; --write records it" in out
    assert "cost" not in store.get_game(ref["run_id"], ref["index"]), "a dry run wrote"

    assert cli.main(["tables", "costs", "--uri", str(tmp_path), "--write"]) == 0
    assert "recorded now" in capsys.readouterr().out
    record = _record(store, document)
    assert record.cost == pytest.approx(total)
    assert all(s.cost is None for s in record.seats), "the old ledgers had no split by seat"
    assert _line(store, document)["cost"] == pytest.approx(total)
    assert registry.document(table_id)["llm"]["final"]

    assert cli.main(["tables", "costs", "--uri", str(tmp_path)]) == 0
    assert "already recorded" in capsys.readouterr().out


def test_tables_costs_leaves_a_game_still_writing_its_entries(app, store, ann):
    table_id, _final = _finished(app, ann)
    row = tables.TableRegistry(store).backfill_cost(table_id, write=True)
    assert row["state"] == "writing"
    assert _record(store, app.extensions["tables"].document(table_id)).cost is None
