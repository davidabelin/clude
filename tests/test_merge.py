"""`store merge` (`clude_storage.merge`): a downloaded store folded into a
local one, the download's names winning a clash."""
from __future__ import annotations

import json

import pytest

from clude_storage import GameRecord, LocalStore, Logbook, LogbookEntry
from clude_storage.merge import apply_merge, plan_merge
from tests.test_logbooks import _record

DECAY = 1.05


def _entry(identity, serial, record, date, read):
    entry = LogbookEntry.build(
        identity, serial, record, 0,
        {"title": f"{record.run_id} {record.game_index}", "standing_instructions": [f"Rule {date}"],
         "dossiers": [{"opponent": "Mustard", "read": read}]},
    )
    entry.date = date
    return entry


def _game(store, run_id, index, seed):
    record = _record(seed=seed, run_id=run_id, index=index)
    store.put_game(run_id, index, record.to_dict())
    store.put_run(run_id, {"run_id": run_id, "n_games": index + 1, "games": []})
    return record


@pytest.fixture
def stores(tmp_path):
    bucket, local = LocalStore(tmp_path / "bucket"), LocalStore(tmp_path / "local")

    # `web` clashes: game 0 differs. `arena` only has a gap the local copy fills.
    web = [_game(bucket, "web", i, seed=10 + i) for i in range(2)]
    mine = _game(local, "web", 0, seed=99)
    _game(bucket, "arena", 0, seed=3)
    _game(local, "arena", 1, seed=4)
    local.put_game("arena", 0, bucket.get_game("arena", 0))
    bucket.put_run("arena", {"run_id": "arena", "n_games": 2, "games": []})
    local.put_run("arena", {"run_id": "arena", "n_games": 2, "games": []})
    path = local.root / "games" / "arena" / "00000.json"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    local.put_doc("traces/arena/00000.json", {"cache": "local"})
    bucket.put_doc("traces/arena/00000.json", {"cache": "bucket"})

    plum = Logbook(bucket, "Plum")
    plum.add_entry(_entry("Plum", 1, web[0], "2026-09-01", "Bucket read 1."))
    plum.add_entry(_entry("Plum", 2, web[1], "2026-10-05", "Bucket read 2."))
    Logbook(local, "Plum").add_entry(_entry("Plum", 1, mine, "2026-10-01", "Local read."))
    Logbook(local, "Scarlett").add_entry(_entry("Scarlett", 1, mine, "2026-10-01", "Mine."))

    bucket.put_doc("logbooks/White/method.json", {
        "version": 1, "kind": "counts", "games": {"arena/00000": {"Plum": {"00": 1}}, "web/00001": {}},
    })
    local.put_doc("logbooks/White/method.json", {
        "version": 1, "kind": "counts", "games": {"arena/00000": {"Plum": {"00": 1}}, "web/00000": {"x": 1}},
    })
    bucket.put_doc("logbooks/Green/method.json", {
        "version": 1, "kind": "state", "games": 5, "arms": {"A": [4.0, 2.0], "B": [1.5, 3.0]},
    })
    # One local lesson from the prior: reward 1 for A, 0 for B, step 2.
    local.put_doc("logbooks/Green/method.json", {
        "version": 1, "kind": "state", "games": 1, "arms": {"A": [3.0, 1.0], "B": [1.0, 3.0]},
    })

    bucket.put_doc("spend/2026-10-01.json", {"date": "2026-10-01", "total": 1.0, "tables": {"t1": 1.0}})
    local.put_doc("spend/2026-10-01.json", {"date": "2026-10-01", "total": 0.5, "tables": {"t2": 0.5}})
    bucket.put_doc("users/david.json", {"key": "david", "password_hash": "bucket"})
    local.put_doc("users/david.json", {"key": "david", "password_hash": "local"})
    local.put_doc("tables/abc.json", {"record": {"run_id": "web", "index": 0}, "memory": {"White": {"games": ["web/00000"]}}})
    bucket.put_doc("notes/one.json", {"from": "bucket"})
    local.put_doc("notes/one.json", {"from": "local"})
    (local.root / "report.py").write_text("print('kept')\n", encoding="utf-8")
    return bucket, local


def _merge(bucket, local):
    plan = plan_merge(bucket.root, local.root, bandit_decay=DECAY)
    apply_merge(plan, local.root)
    return plan


def test_merge_renames_a_clashing_run_and_fills_gaps(stores):
    bucket, local = stores
    plan = _merge(bucket, local)
    assert plan.renamed_runs == {"web": "web_local"}
    assert local.list_games("web") == [0, 1]
    assert local.get_game("web", 0) == bucket.get_game("web", 0)
    assert GameRecord.from_dict(local.get_game("web_local", 0)).run_id == "web_local"
    assert local.get_run("web_local")["run_id"] == "web_local"
    assert local.list_games("arena") == [0, 1]
    assert local.get_doc("traces/arena/00000.json") == {"cache": "bucket"}
    assert local.get_doc("tables/abc.json") == {
        "record": {"run_id": "web_local", "index": 0}, "memory": {"White": {"games": ["web_local/00000"]}},
    }
    assert (local.root / "report.py").read_text(encoding="utf-8") == "print('kept')\n"


def test_merge_appends_local_entries_to_the_downloaded_logbook(stores):
    bucket, local = stores
    _merge(bucket, local)
    plum = Logbook(local, "Plum")
    assert plum.serials() == [1, 2, 3]
    assert [e.game_id for e in plum.entries()] == ["web/00000", "web/00001", "web_local/00000"]
    head = plum.head()
    assert head.serial == 3 and head.tally["games"] == 3
    # The local entry is older than the download's newest: its rules and read do not win.
    assert head.standing_instructions == ["Rule 2026-10-05"]
    assert head.dossiers["Mustard"].read == "Bucket read 2."
    assert head.dossiers["Mustard"].games_together == 3
    assert head.tally["last_game_id"] == "web/00001"
    # A logbook only one side has is kept as it is.
    assert [e.game_id for e in Logbook(local, "Scarlett").entries()] == ["web_local/00000"]


def test_merge_combines_method_memory_spend_and_drops_live_documents(stores):
    bucket, local = stores
    plan = _merge(bucket, local)
    white = local.get_doc("logbooks/White/method.json")
    assert sorted(white["games"]) == ["arena/00000", "web/00001", "web_local/00000"]
    green = local.get_doc("logbooks/Green/method.json")
    assert green["games"] == 6
    # The same lesson applied to the download's arms: decay the excess, then add.
    assert green["arms"]["A"] == pytest.approx([3.0 / DECAY + 1 + 2, 1.0 / DECAY + 1])
    assert green["arms"]["B"] == pytest.approx([0.5 / DECAY + 1, 2.0 / DECAY + 1 + 2])
    spend = local.get_doc("spend/2026-10-01.json")
    assert spend["tables"] == {"t1": 1.0, "t2": 0.5} and spend["total"] == 1.5
    assert local.get_doc("users/david.json")["password_hash"] == "bucket"
    assert not (local.root / "users" / "david_local.json").exists()
    assert local.get_doc("notes/one.json") == {"from": "bucket"}
    assert local.get_doc("notes/one_local.json") == {"from": "local"}
    assert plan.moved == {"notes/one.json": "notes/one_local.json"}


def test_merge_leaves_the_download_alone_and_a_second_run_changes_nothing(stores):
    bucket, local = stores
    before = {p: p.read_bytes() for p in bucket.root.rglob("*") if p.is_file()}
    _merge(bucket, local)
    after_first = {p: p.read_bytes() for p in local.root.rglob("*") if p.is_file()}
    again = plan_merge(bucket.root, local.root, bandit_decay=DECAY)
    assert again.changes() == 0 and not again.renamed_runs
    apply_merge(again, local.root)
    assert {p: p.read_bytes() for p in local.root.rglob("*") if p.is_file()} == after_first
    assert {p: p.read_bytes() for p in bucket.root.rglob("*") if p.is_file()} == before


def test_merge_refuses_when_the_local_name_is_taken(stores):
    bucket, local = stores
    bucket.put_run("web_local", {"run_id": "web_local"})
    with pytest.raises(ValueError, match="web_local already exists"):
        plan_merge(bucket.root, local.root)


def test_store_merge_command_dry_run_then_merge(stores, capsys):
    from tests.test_cli import SCRIPT
    import importlib.util

    spec = importlib.util.spec_from_file_location("clude_cli", SCRIPT)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    bucket, local = stores
    argv = ["store", "merge", "--from", str(bucket.root), "--into", str(local.root)]
    assert cli.main(argv + ["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "run web: the local games differ; the local run becomes web_local" in out
    assert "logbook Plum: 1 local entries appended as #0003-#0003" in out
    assert "dry run: nothing changed" in out
    assert local.list_games("web_local") == []
    assert cli.main(argv) == 0
    assert local.list_games("web_local") == [0]
    assert cli.main(argv) == 0
    assert "changed 0 documents" in capsys.readouterr().out
    assert cli.main(["store", "merge", "--from", str(bucket.root), "--into", str(bucket.root)]) == 2
