"""Phase 5d: game records and the local / Cloud Storage record stores.
The GCS backend is exercised against an in-memory double; a live test
runs only when ``CLUDE_GCS_LIVE`` is set."""
from __future__ import annotations

import json
import os

import pytest

from clude_core import engine
from clude_core.bots import RandomBot
from clude_core.events import GameOverEvent, MoveEvent, RemarkEvent
from clude_storage import (
    GameRecord,
    GcsStore,
    LocalStore,
    SeatRecord,
    event_from_json,
    event_to_json,
    node_from_json,
    node_to_json,
    open_store,
    split_gcs_uri,
)
from clude_storage.records import RECORD_VERSION
from clude_storage.stores import game_key, run_key, validate_key, validate_prefix, validate_run_id


def _finished_game(seed=4, n_players=4):
    bots = {p: RandomBot() for p in range(n_players)}
    return engine.run_game(n_players, bots, seed=seed, max_turns=80)


def _seats(state):
    return [
        SeatRecord(seat=p, suspect=state.suspects_in_play[p], label="random", kind="random")
        for p in range(state.n_players)
    ]


def test_events_round_trip_through_json():
    state, events = _finished_game()
    kinds = {type(e).__name__ for e in events}
    assert {"MoveEvent", "SuggestionEvent", "GameOverEvent"} <= kinds
    for event in events:
        data = event_to_json(event)
        json.dumps(data)
        assert event_from_json(data) == event
    square = engine.board.Square(7, 4)
    assert node_to_json(square) == {"row": 7, "col": 4}
    assert node_from_json(node_to_json(square)) == square
    legacy = engine.board.HallwayCell("Kitchen", "Ballroom", 2)  # a ring-era record still loads
    assert node_from_json(node_to_json(legacy)) == legacy
    assert node_from_json(node_to_json("Study")) == "Study"
    with pytest.raises(TypeError):
        event_to_json("not an event")
    with pytest.raises(ValueError):
        event_from_json({"type": "teleport", "turn": 1})


def test_remarks_round_trip_and_version_one_records_still_load():
    remark = RemarkEvent(3, 1, "I have my suspicions.", "suggest")
    data = event_to_json(remark)
    assert data["type"] == "remark"
    assert event_from_json(json.loads(json.dumps(data))) == remark

    state, events = _finished_game()
    with_talk = [*events[:-1], remark, events[-1]]
    record = GameRecord.from_game("run-b", 0, 4, state, with_talk, _seats(state))
    assert record.version == RECORD_VERSION == 3
    back = GameRecord.from_dict(json.loads(json.dumps(record.to_dict())))
    assert back.events == with_talk
    assert back.winner == record.winner

    # A document written before remarks existed loads unchanged.
    old = GameRecord.from_game("run-c", 0, 4, state, events, _seats(state)).to_dict()
    old["version"] = 1
    assert all(e["type"] != "remark" for e in old["events"])
    assert GameRecord.from_dict(old).version == 1


def test_game_record_round_trips_and_is_json_serializable():
    state, events = _finished_game()
    record = GameRecord.from_game("run-a", 3, 4, state, events, _seats(state))
    assert record.n_suggestions == len(state.suggestion_log)
    assert record.envelope == state.envelope
    assert isinstance(record.events[-1], GameOverEvent)
    data = record.to_dict()
    json.dumps(data)
    back = GameRecord.from_dict(json.loads(json.dumps(data)))
    assert back.events == record.events
    assert back.hands == record.hands
    assert back.seats == record.seats
    assert back.envelope == record.envelope
    assert back.winner == record.winner


def test_keys_and_run_ids():
    assert run_key("arena-1") == "runs/arena-1.json"
    assert game_key("arena-1", 7) == "games/arena-1/00007.json"
    for bad in ("", "../x", "a/b", "-lead", "sp ace"):
        with pytest.raises(ValueError):
            validate_run_id(bad)
    with pytest.raises(ValueError):
        game_key("ok", -1)
    assert validate_key("logbooks/Plum/entries/0001.json") == "logbooks/Plum/entries/0001.json"
    assert validate_prefix("logbooks/Plum/") == "logbooks/Plum"
    assert validate_prefix("") == ""
    for bad in ("logbooks/Plum", "logbooks/../x.json", "/abs.json", "a//b.json", "sp ace.json"):
        with pytest.raises(ValueError):
            validate_key(bad)


def _exercise_documents(store):
    """The generic document surface (Phase 7) on either backend."""
    assert store.list_docs("logbooks") == [] and store.list_folders("logbooks") == []
    assert store.delete_doc("logbooks/Plum/head.json") is False
    store.put_doc("logbooks/Plum/head.json", {"serial": 2})
    store.put_doc("logbooks/Plum/entries/0002.json", {"serial": 2})
    store.put_doc("logbooks/Plum/entries/0001.json", {"serial": 1})
    store.put_doc("logbooks/White/head.json", {"serial": 0})
    assert store.get_doc("logbooks/Plum/head.json") == {"serial": 2}
    assert store.list_folders("logbooks") == ["Plum", "White"]
    assert store.list_docs("logbooks/Plum") == ["head"]
    assert store.list_folders("logbooks/Plum") == ["entries"]
    assert store.list_docs("logbooks/Plum/entries") == ["0001", "0002"]
    assert store.list_docs("logbooks/Plum/entries/") == ["0001", "0002"]
    assert store.delete_doc("logbooks/Plum/entries/0001.json") is True
    assert store.list_docs("logbooks/Plum/entries") == ["0002"]
    with pytest.raises(KeyError):
        store.get_doc("logbooks/Plum/entries/0001.json")
    with pytest.raises(ValueError):
        store.put_doc("logbooks/Plum/entries/0003", {})
    # The run/game documents are visible through the same surface.
    store.put_run("r1", {"n_games": 0})
    assert store.list_docs("runs") == ["r1"]
    assert "logbooks" in store.list_folders("") and "runs" in store.list_folders("")


def test_local_store_generic_documents(tmp_path):
    _exercise_documents(LocalStore(tmp_path / "records"))


def test_local_store_round_trip(tmp_path):
    store = LocalStore(tmp_path / "records")
    assert store.list_runs() == []
    assert store.list_games("nope") == []
    store.put_game("r1", 1, {"game_index": 1})
    store.put_game("r1", 0, {"game_index": 0})
    store.put_run("r1", {"n_games": 2})
    assert store.list_games("r1") == [0, 1]
    assert store.get_game("r1", 1) == {"game_index": 1}
    assert store.get_run("r1") == {"n_games": 2}
    assert store.list_runs() == ["r1"]
    assert (tmp_path / "records" / "games" / "r1" / "00000.json").exists()
    with pytest.raises(KeyError):
        store.get_game("r1", 5)
    assert str(tmp_path) in store.describe()


class _FakeBlob:
    def __init__(self, bucket, name):
        self.bucket = bucket
        self.name = name

    def upload_from_string(self, payload, content_type=None):
        self.bucket.objects[self.name] = (payload, content_type)

    def exists(self):
        return self.name in self.bucket.objects

    def download_as_text(self):
        return self.bucket.objects[self.name][0]

    def delete(self):
        del self.bucket.objects[self.name]


class _FakeBucket:
    def __init__(self):
        self.objects = {}

    def blob(self, name):
        return _FakeBlob(self, name)


class _FakeClient:
    def __init__(self):
        self.buckets = {}

    def bucket(self, name):
        return self.buckets.setdefault(name, _FakeBucket())

    def list_blobs(self, name, prefix=""):
        bucket = self.bucket(name)
        return [_FakeBlob(bucket, key) for key in sorted(bucket.objects) if key.startswith(prefix)]


def test_gcs_store_uses_the_same_layout_under_a_prefix():
    client = _FakeClient()
    store = GcsStore("clude-game-data", "arena", client=client)
    where = store.put_game("r1", 2, {"game_index": 2})
    assert where == "gs://clude-game-data/arena/games/r1/00002.json"
    store.put_game("r1", 0, {"game_index": 0})
    store.put_run("r1", {"n_games": 2})
    store.put_run("r0", {"n_games": 0})
    assert store.list_games("r1") == [0, 2]
    assert store.list_runs() == ["r0", "r1"]
    assert store.get_game("r1", 2) == {"game_index": 2}
    assert store.get_run("r1") == {"n_games": 2}
    payload, content_type = client.buckets["clude-game-data"].objects["arena/runs/r1.json"]
    assert content_type == "application/json"
    assert json.loads(payload) == {"n_games": 2}
    with pytest.raises(KeyError):
        store.get_run("missing")
    assert store.describe() == "gs://clude-game-data/arena"
    assert GcsStore("b", client=client).describe() == "gs://b"


def test_gcs_store_generic_documents_with_and_without_a_prefix():
    _exercise_documents(GcsStore("clude-game-data", "arena", client=_FakeClient()))
    _exercise_documents(GcsStore("clude-game-data", client=_FakeClient()))


def test_open_store_dispatches_on_the_uri():
    local = open_store("data/records")
    assert isinstance(local, LocalStore)
    remote = open_store("gs://clude-game-data/arena/")
    assert isinstance(remote, GcsStore)
    assert (remote.bucket_name, remote.prefix) == ("clude-game-data", "arena")
    assert split_gcs_uri("gs://bucket") == ("bucket", "")
    with pytest.raises(ValueError):
        split_gcs_uri("gs://")
    with pytest.raises(ValueError):
        split_gcs_uri("s3://bucket/x")


@pytest.mark.skipif(not os.environ.get("CLUDE_GCS_LIVE"), reason="set CLUDE_GCS_LIVE=1 to hit the bucket")
def test_gcs_store_live_round_trip():
    store = open_store(os.environ.get("CLUDE_GCS_URI", "gs://clude-game-data/test"))
    store.put_run("live-smoke", {"ok": True})
    assert store.get_run("live-smoke") == {"ok": True}
    assert "live-smoke" in store.list_runs()


def test_records_from_a_character_game_keep_every_seat(tmp_path):
    from clude_training.arena import run_arena

    store = LocalStore(tmp_path)
    result = run_arena(
        n_games=2, seed=5, roster=("Scarlett", "floor"), player_counts=(3,), max_turns=60,
        store=store, run_id="smoke",
    )
    assert store.list_games("smoke") == [0, 1]
    record = GameRecord.from_dict(store.get_game("smoke", 1))
    assert [s.label for s in record.seats] == ["Scarlett", "floor", "floor"]  # seats are fixed by token
    assert record.seats[0].profile == result.profiles["Scarlett"]
    assert record.seats[1].profile is None
    assert isinstance(record.events[0], MoveEvent)
    summary = store.get_run("smoke")
    assert summary["n_games"] == 2
    assert set(summary["per_player"]) == {"Scarlett", "floor"}
