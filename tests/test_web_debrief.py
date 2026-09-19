"""Debriefs and read-back on the web (Phase 8.3c, docs/phase8-plan.md 4.4).

Pinned, on a scripted backend: with "characters remember" on, a model
seat's finish lists a pending debrief; one `work` call writes it as a
logbook entry with its dossier on the person, by account key; the table
stays a table (not a redirect to the replay) and listed as wrapping up
until then; a cold registry still writes it; and the next table's first
request carries the logbook read back. With "remember" off nothing is
written and nothing pends.
"""
from __future__ import annotations

import json

from clude_llm import LOGBOOK_KIND, LLMResult
from clude_storage import Logbook, open_store
from clude_web import tables
from tests.test_debrief import DEBRIEF
from tests.test_web_llm import make_app
from tests.test_web_tables import ANN, login, new_table, play_out, poll, work

SEED = 11
SEATS = {"Scarlett": "me", "Plum": "llm", "White": "character", "Green": "floor"}


class Remembering:
    name = "kinds"
    model = "claude-opus-5"

    def __init__(self) -> None:
        self.requests: list = []

    def complete(self, request):
        self.requests.append(request)
        if request.kind == LOGBOOK_KIND:
            reply = dict(DEBRIEF, dossiers=[{"opponent": "ann", "read": "Bluffs about the Rope."}])
        elif request.kind == "suggest":
            reply = {"suspect": "A", "weapon": "A", "say": ""}
        elif request.kind == "remark":
            reply = {"say": ""}
        else:
            reply = {"choice": "A", "say": ""}
        return LLMResult(text=json.dumps(reply), stop_reason="end_turn", model=self.model,
                         input_tokens=400, output_tokens=30)


class Factory:
    def __init__(self) -> None:
        self.backends: list = []

    def __call__(self, model, key):
        backend = Remembering()
        self.backends.append(backend)
        return backend

    @property
    def requests(self):
        return [r for b in self.backends for r in b.requests]


def _finish(app, ann, remember):
    table_id = new_table(ann, SEATS, seed=SEED, remember=remember)
    final = play_out(app, table_id, {ANN: ann})
    assert final["finished"]
    return table_id, final


def test_a_remembering_model_seat_writes_its_entry_through_work(tmp_path):
    store = open_store(str(tmp_path))
    factory = Factory()
    app = make_app(tmp_path, store, factory)
    ann = login(app, ANN)
    table_id, final = _finish(app, ann, remember=True)
    registry = app.extensions["tables"]
    # play_out stops at the first finished payload; the debrief is scheduled by finish.
    document = registry.document(table_id)
    plum = registry.game(table_id).suspects.index("Plum")
    assert tables.pending_debriefs(document) == [plum]
    page = poll(ann, table_id)
    assert page["work"] and page["wrapping_up"] and page["debriefs"]["pending"] == ["Plum"]
    # The table keeps its page while wrapping up, and the lobby says so.
    assert ann.get(f"/tables/{table_id}").status_code == 200
    assert "writing up their notes" in ann.get("/").get_data(as_text=True)
    served = work(ann, table_id)
    assert served["did"] == "debrief"
    assert served["debriefs"] == {"pending": [], "done": ["Plum"], "failed": []} and not served["work"]
    logbook = Logbook(store, "Plum")
    assert logbook.serials() == [1]
    entry = logbook.entry(1)
    reads = entry.dossiers if isinstance(entry.dossiers, dict) else {
        d["opponent"]: d["read"] for d in entry.dossiers
    }
    assert reads.get("ann") == "Bluffs about the Rope."
    debriefs = [r for r in factory.requests if r.kind == LOGBOOK_KIND]
    assert len(debriefs) == 1 and "ann" in debriefs[0].user
    assert work(ann, table_id)["did"] == "finished"
    # Once wrapped up the table page goes to the replay, and the lobby drops it.
    assert ann.get(f"/tables/{table_id}").status_code == 302
    assert "writing up their notes" not in ann.get("/").get_data(as_text=True)
    # The next remembering table's first request carries the logbook.
    before = len(factory.requests)
    new_table(ann, SEATS, seed=SEED + 1, remember=True)
    second = registry.game(list(d["id"] for d in registry.in_progress())[0])
    plum2 = second.suspects.index("Plum")
    assert second.wrappers[plum2].memory_block, "nothing read back"
    assert "ann" in second.wrappers[plum2].memory_block


def test_a_cold_registry_still_writes_the_pending_debrief(tmp_path):
    store = open_store(str(tmp_path))
    factory = Factory()
    app = make_app(tmp_path, store, factory)
    ann = login(app, ANN)
    table_id, _final = _finish(app, ann, remember=True)
    cold = tables.TableRegistry(store, app.extensions["tables"].llm)
    game = cold.game(table_id)
    assert game.finished
    assert cold.work(table_id, game) == "debrief"
    assert Logbook(store, "Plum").serials() == [1]
    assert cold.work(table_id, game) == "finished"


def test_with_remember_off_nothing_pends_and_nothing_is_written(tmp_path):
    store = open_store(str(tmp_path))
    factory = Factory()
    app = make_app(tmp_path, store, factory)
    ann = login(app, ANN)
    table_id, final = _finish(app, ann, remember=False)
    assert not final["work"] and final.get("debriefs") is None
    assert not [r for r in factory.requests if r.kind == LOGBOOK_KIND]
    assert Logbook(store, "Plum").serials() == []
    assert ann.get(f"/tables/{table_id}").status_code == 302
