"""Phase 14's frozen corpus and method-only release guards."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from clude_agents import deep_nash
from clude_core import engine
from clude_storage import GameRecord, LocalStore, Logbook, SeatRecord
from clude_training import memory
from clude_training.recalibration import (
    CURRENT_PLUM,
    NO_PLUM,
    PLUM_OG,
    FrozenCorpus,
    build_method_candidates,
    document_hash,
    exclusion_reason,
    method_hashes,
    plum_generation,
    promote_methods,
    promote_plum_checkpoint,
    public_report,
    restore_methods,
    restore_plum_checkpoint,
    snapshot_narrative_logbooks,
    snapshot_corpus,
    verify_narrative_logbooks,
)
from clude_training.self_play import make_bots


def _record(run_id: str, index: int, seed: int, labels=("Plum", "White", "Mustard")) -> dict:
    bots, observer = make_bots("floor", len(labels))
    state, events = engine.run_game(len(labels), bots, seed=seed, max_turns=80, observer=observer)
    seats = [
        SeatRecord(p, state.suspects_in_play[p], labels[p], "character")
        for p in range(len(labels))
    ]
    record = GameRecord.from_game(run_id, index, seed, state, events, seats).to_dict()
    record["created_at"] = "2026-10-17T12:00:00+00:00"
    return record


def _source(tmp_path: Path) -> LocalStore:
    source = LocalStore(tmp_path / "source")
    for index in range(5):
        source.put_game("web", index, _record("web", index, 10 + index))
    # Seed 14 is deliberately shared with web/00004: the split must keep
    # the paid ladder/practice pair together.
    source.put_game("web-2", 0, _record("web-2", 0, 14))
    source.put_game("web-2", 1, _record("web-2", 1, 21))
    source.put_game("other", 0, _record("other", 0, 31, labels=("Alice", "White", "Mustard")))
    source.put_game("ring", 0, {**_record("ring", 0, 41), "version": 2})
    return source


def test_cutoff_version_and_generation_classification():
    current = _record("web-2", 0, 1)
    assert exclusion_reason(current) is None
    assert plum_generation(current) == CURRENT_PLUM
    assert plum_generation(_record("web", 4, 1)) == PLUM_OG
    assert plum_generation(_record("other", 0, 1, labels=("White", "Mustard", "Green"))) == NO_PLUM
    assert exclusion_reason({**current, "version": 2}) == "record_version"
    assert exclusion_reason({**current, "created_at": "2026-09-19T01:41:04Z"}) == "at_or_before_cutoff"
    assert exclusion_reason(_record("web", 3, 1)) == "web_00000_00003"
    with pytest.raises(ValueError, match="cannot classify"):
        plum_generation(_record("unknown", 0, 1))


def test_snapshot_is_reproducible_grouped_private_and_tamper_evident(tmp_path):
    source = _source(tmp_path)
    one = snapshot_corpus(source, tmp_path / "one")
    two = snapshot_corpus(source, tmp_path / "two")
    assert one == two
    assert one["inventory"]["scanned"] == 9
    assert one["inventory"]["eligible"] == 4
    assert one["inventory"]["plum_generations"] == {
        CURRENT_PLUM: 2, NO_PLUM: 1, PLUM_OG: 1,
    }
    shared = [row for row in one["records"] if row["seed"] == 14]
    assert len(shared) == 2 and len({row["split"] for row in shared}) == 1
    rendered = json.dumps(one)
    assert "Alice" not in rendered
    corpus = FrozenCorpus.open(tmp_path / "one" / "manifest.json")
    assert len(list(corpus.records())) == 4

    copied = LocalStore(tmp_path / "one")
    altered = copied.get_game("web", 4)
    altered["turns"] += 1
    copied.put_game("web", 4, altered)
    with pytest.raises(ValueError, match="record hash mismatch"):
        FrozenCorpus.open(tmp_path / "one" / "manifest.json")


def test_phase14_white_relabel_is_explicit_and_live_default_is_unchanged():
    record = GameRecord.from_dict(_record("web", 4, 4))
    original = memory.white_counts(record)
    relabelled = memory.white_counts(record, {"Plum": "PlumOG"})
    if "Plum" in original:  # a short game can leave a seat with no transition
        assert "Plum" not in relabelled
        assert relabelled["PlumOG"] == original["Plum"]
    assert memory.white_counts(record) == original


def test_stage_report_and_guarded_promotion_with_rollback(tmp_path):
    corpus_dir = tmp_path / "corpus"
    snapshot_corpus(_source(tmp_path), corpus_dir)
    corpus = FrozenCorpus.open(corpus_dir / "manifest.json")
    green = {"version": 1, "kind": "state", "games": 200, "arms": {"Plum": [10.0, 4.0]}}
    stage_dir = tmp_path / "stage"
    stage = build_method_candidates(corpus, stage_dir, green_state=green)
    assert stage["pending"] == [] and set(stage["documents"]) == {"Mustard", "White", "Green"}
    report = public_report(corpus, stage_dir)
    assert "private_identity_counts" in report["staged_methods"]
    assert "Alice" not in json.dumps(report)

    target = LocalStore(tmp_path / "target")
    old = {
        "Mustard": {"version": 1, "kind": "rows", "games": {}},
        "White": {"version": 1, "kind": "counts", "games": {}},
        "Green": {"version": 1, "kind": "state", "games": 3, "arms": {}},
    }
    for identity, document in old.items():
        Logbook(target, identity).save_method(document)
    expected = method_hashes(target)
    backup = tmp_path / "backup"

    dry = promote_methods(target, stage_dir, expected, backup)
    assert dry["apply"] is False and not backup.exists()
    assert method_hashes(target) == expected
    with pytest.raises(ValueError, match="source hash mismatch"):
        promote_methods(target, stage_dir, {**expected, "Green": "0" * 64}, backup)

    target.put_doc("tables/active.json", {"status": "playing"})
    with pytest.raises(RuntimeError, match="active tables"):
        promote_methods(target, stage_dir, expected, backup, apply=True)
    target.put_doc("tables/active.json", {"status": "finished"})

    promoted = promote_methods(target, stage_dir, expected, backup, apply=True)
    assert promoted["apply"] is True and (backup / "backup.json").exists()
    promoted_hashes = method_hashes(target)
    assert promoted_hashes == stage["documents"]
    assert Logbook(target, "Mustard").head().serial == 0
    assert Logbook(target, "Mustard").serials() == []

    restore_methods(target, backup, promoted_hashes, apply=True)
    assert method_hashes(target) == expected
    assert {identity: document_hash(document) for identity, document in old.items()} == expected


def test_snapshot_refuses_to_move_an_existing_freeze(tmp_path):
    source = _source(tmp_path)
    snapshot_corpus(source, tmp_path / "corpus")
    with pytest.raises(FileExistsError, match="already exists"):
        snapshot_corpus(source, tmp_path / "corpus")


def test_plum_checkpoint_promotion_is_explicit_hashed_and_reversible(tmp_path):
    target = tmp_path / "plum.npz"
    candidate = tmp_path / "checkpoint-000130.npz"
    backup = tmp_path / "backup" / "plum.npz"
    deep_nash.save_weights(deep_nash.init_weights(1), target)
    deep_nash.save_weights(deep_nash.init_weights(2), candidate)
    # The release guard uses exact file hashes, not hashes of parsed arrays.
    from clude_training.recalibration import file_hash

    old_hash = file_hash(target)
    dry = promote_plum_checkpoint(candidate, old_hash, backup, target=target)
    assert dry["apply"] is False and not backup.exists() and file_hash(target) == old_hash
    with pytest.raises(ValueError, match="target hash mismatch"):
        promote_plum_checkpoint(candidate, "0" * 64, backup, target=target)

    promoted = promote_plum_checkpoint(candidate, old_hash, backup, target=target, apply=True)
    assert file_hash(target) == promoted["candidate_sha256"] and file_hash(backup) == old_hash
    restore_plum_checkpoint(backup, promoted["candidate_sha256"], target=target, apply=True)
    assert file_hash(target) == old_hash


def test_method_searches_keep_personality_as_a_separate_gate(tmp_path, monkeypatch):
    from clude_training import recalibrate_methods as methods

    corpus_dir = tmp_path / "corpus"
    snapshot_corpus(_source(tmp_path), corpus_dir)
    corpus = FrozenCorpus.open(corpus_dir / "manifest.json")
    monkeypatch.setattr(methods, "MUSTARD_BASE_GAMES", (1,))
    monkeypatch.setattr(methods, "MUSTARD_DEPTHS", (2,))
    monkeypatch.setattr(methods, "MUSTARD_MIN_LEAVES", (2,))
    monkeypatch.setattr(methods, "MUSTARD_SMOOTHING", (1.0,))
    monkeypatch.setattr(methods, "WHITE_PRIOR_MASSES", (1.0,))
    monkeypatch.setattr(methods, "GREEN_STEP_SIZES", (1.0,))
    monkeypatch.setattr(methods, "GREEN_DECAY_RATES", (1.02,))

    mustard = methods.search_mustard(corpus, output=tmp_path / "mustard.json", arena_games=2)
    white = methods.search_white(corpus, output=tmp_path / "white.json", arena_games=2)
    green = methods.search_green(
        corpus, output=tmp_path / "green.json", training_games=2, validation_games=2,
    )
    for result in (mustard, white, green):
        assert result["complete"] is True
        assert result["personality_gate"] == "pending human review"
        assert result["ready_for_promotion"] is False
        assert len(result["candidates"]) == 1
    assert green["candidates"][0]["state"]["games"] == 2


def test_plum_evaluation_never_selects_a_checkpoint_automatically(tmp_path):
    from clude_training.recalibrate_plum import evaluate_plum_checkpoints

    candidate = tmp_path / "candidate.npz"
    deep_nash.save_weights(deep_nash.init_weights(99), candidate)
    report = evaluate_plum_checkpoints(
        [candidate], output=tmp_path / "evaluation.json", benchmark_games=2, arena_games=6,
    )
    assert report["complete"] is True and report["selected_checkpoint"] is None
    assert report["candidates"][0]["checkpoint"] == str(candidate)
    assert report["candidates"][0]["personality_gate"] == "pending human review"
    assert report["candidates"][0]["ready_for_promotion"] is False


def test_phase14_plum_commands_pin_and_record_the_training_device(tmp_path):
    from scripts import phase14_plum

    commands = phase14_plum._commands(tmp_path, workers=3, device="cuda")
    assert len(commands) == 6
    for row in commands:
        index = row["command"].index("--device")
        assert row["command"][index + 1] == "cuda"
        assert row["device"] == "cuda"


def test_narrative_memory_snapshot_excludes_method_documents(tmp_path):
    source = LocalStore(tmp_path / "source")
    source.put_doc("logbooks/White/head.json", {"version": 1, "identity": "White"})
    source.put_doc("logbooks/White/digest.json", {"version": 1, "identity": "White"})
    source.put_doc("logbooks/White/entries/0001.json", {"version": 1, "identity": "White"})
    source.put_doc("logbooks/White/method.json", {"kind": "counts", "games": {}})
    destination = tmp_path / "memory"
    manifest = snapshot_narrative_logbooks(source, destination, identities=("White",))
    assert len(manifest["documents"]) == 3
    assert all("method.json" not in row["key"] for row in manifest["documents"])
    assert verify_narrative_logbooks(destination) == manifest
    with pytest.raises(FileExistsError, match="already exists"):
        snapshot_narrative_logbooks(source, destination, identities=("White",))


def test_paid_preflight_sizes_prompts_without_paid_calls(tmp_path, monkeypatch):
    from clude_training import recalibrate_paid as paid

    corpus_dir = tmp_path / "corpus"
    snapshot_corpus(_source(tmp_path), corpus_dir)
    corpus = FrozenCorpus.open(corpus_dir / "manifest.json")
    stage_dir = tmp_path / "stage"
    build_method_candidates(
        corpus, stage_dir,
        green_state={"version": 1, "kind": "state", "games": 2, "arms": {}},
    )
    memory_dir = tmp_path / "narrative"
    snapshot_narrative_logbooks(
        LocalStore(tmp_path / "empty"), memory_dir,
        identities=("Scarlett", "Mustard", "White", "Green", "Peacock", "Plum"),
    )
    monkeypatch.setattr(paid, "LEASH_GAMES", 1)
    monkeypatch.setattr(paid, "MEMORY_GAMES", 1)
    monkeypatch.setattr(paid, "CHAT_GAMES", 1)
    report = paid.paid_preflight(
        corpus, stage_dir, memory_dir, tmp_path / "games", model="claude-opus-5",
    )
    assert report["paid_calls_made"] == 0 and report["approval_status"] == "required"
    assert report["quote"]["approval_ceiling"] > 0
    assert report["memory_snapshot_sha256"] == verify_narrative_logbooks(memory_dir)["snapshot_sha256"]
