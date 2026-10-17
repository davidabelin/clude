"""Phase 14 corpus freezing and guarded method-memory promotion.

The frozen corpus is a local, read-only copy of eligible ``GameRecord``
documents plus a versioned manifest.  It is deliberately independent of
the live store after creation: training and reports read the copied records
and verify their hashes before use.

Method-memory candidates are staged as plain JSON documents.  Promotion is
separate, dry-run by default, checks the expected live hashes, refuses while
a web table is active, and backs up only ``method.json`` documents.  It never
touches logbook heads, digests or narrative entries.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional

from clude_agents import deep_nash
from clude_agents.deep_nash import WEIGHTS_PATH
from clude_agents.personality import PRESETS
from clude_storage import GameRecord, LocalStore, Logbook
from clude_storage.logbooks import method_key
from clude_storage.records import GRID_RECORD_VERSION
from clude_training import memory as method_memory

MANIFEST_VERSION = 1
STAGE_VERSION = 1
CUTOFF_COMMIT = "dda86f0"
CUTOFF = "2026-09-19T01:41:04+00:00"
EXCLUDED_WEB_INDICES = frozenset(range(4))
METHOD_IDENTITIES = ("Mustard", "White", "Green")
CHARACTER_IDENTITIES = ("Scarlett", "Mustard", "White", "Green", "Peacock", "Plum")
PLUM_OG = "plum_og"
CURRENT_PLUM = "current"
NO_PLUM = "not_present"


def canonical_bytes(value) -> bytes:
    """Stable UTF-8 JSON representation used by every Phase 14 hash."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def document_hash(value) -> str:
    """SHA-256 of :func:`canonical_bytes`, as lower-case hexadecimal."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_hash(path: Path) -> str:
    """SHA-256 of a file's exact bytes."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def promote_plum_checkpoint(
    checkpoint: Path,
    expected_target_hash: str,
    backup: Path,
    *,
    target: Path = WEIGHTS_PATH,
    apply: bool = False,
) -> dict:
    """Validate and deliberately promote one explicitly named checkpoint.

    The trainer never calls this function. A dry run validates the network
    layout and current target hash. ``apply`` writes a byte-for-byte backup,
    replaces through a temporary sibling, then verifies the resulting hash;
    a failed replacement restores the backup.
    """
    checkpoint = Path(checkpoint)
    target = Path(target)
    backup = Path(backup)
    deep_nash.load_weights(checkpoint)
    candidate_hash = file_hash(checkpoint)
    current_hash = file_hash(target)
    if current_hash != expected_target_hash:
        raise ValueError(
            f"Plum target hash mismatch: expected {expected_target_hash}, got {current_hash}"
        )
    if checkpoint.resolve() == target.resolve():
        raise ValueError("selected checkpoint is already the target weights file")
    result = {
        "apply": bool(apply),
        "checkpoint": str(checkpoint),
        "candidate_sha256": candidate_hash,
        "target": str(target),
        "target_sha256": current_hash,
        "backup": str(backup),
    }
    if not apply:
        return result
    if backup.exists():
        raise FileExistsError(f"Plum weights backup already exists: {backup}")
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup)
    temporary = target.with_name(target.name + ".phase14.tmp")
    try:
        shutil.copy2(checkpoint, temporary)
        temporary.replace(target)
        if file_hash(target) != candidate_hash:
            raise RuntimeError("promoted Plum weights failed their post-write hash check")
        deep_nash.load_weights(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        shutil.copy2(backup, target)
        raise
    return result


def restore_plum_checkpoint(
    backup: Path,
    expected_target_hash: str,
    *,
    target: Path = WEIGHTS_PATH,
    apply: bool = False,
) -> dict:
    """Hash-guarded restore of a Plum weights backup."""
    backup = Path(backup)
    target = Path(target)
    deep_nash.load_weights(backup)
    current_hash = file_hash(target)
    if current_hash != expected_target_hash:
        raise ValueError(
            f"Plum target hash mismatch before restore: expected {expected_target_hash}, got {current_hash}"
        )
    result = {
        "apply": bool(apply), "backup": str(backup), "backup_sha256": file_hash(backup),
        "target": str(target), "target_sha256": current_hash,
    }
    if apply:
        temporary = target.with_name(target.name + ".phase14.tmp")
        shutil.copy2(backup, temporary)
        temporary.replace(target)
        deep_nash.load_weights(target)
    return result


def _utc(value: str) -> datetime:
    """Parse an ISO timestamp and normalise it to UTC."""
    if not value:
        raise ValueError("record has no created_at timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"record timestamp is not timezone-aware: {value!r}")
    return parsed.astimezone(timezone.utc)


def exclusion_reason(data: dict) -> Optional[str]:
    """Why a source record is outside Phase 14, or ``None`` if eligible.

    Version 3 is the Classic-grid schema.  The timestamp is compared to
    the landing-rule commit's UTC author time, and the four known pre-change
    practice records are excluded explicitly as a second, auditable guard.
    """
    if int(data.get("version", 1)) != GRID_RECORD_VERSION:
        return "record_version"
    if data.get("run_id") == "web" and int(data.get("game_index", -1)) in EXCLUDED_WEB_INDICES:
        return "web_00000_00003"
    try:
        created = _utc(str(data.get("created_at", "")))
    except (TypeError, ValueError):
        return "missing_or_invalid_timestamp"
    if created <= _utc(CUTOFF):
        return "at_or_before_cutoff"
    return None


def plum_generation(data: dict) -> str:
    """Classify the Plum seat without publishing any other seat labels.

    The closed ``web`` practice set used PlumOG.  The policy ladder and
    ``web-2`` used the current network.  An unknown post-cutoff run with a
    Plum-labelled seat is rejected rather than silently assigned to either
    generation.
    """
    has_plum = any(seat.get("label") == "Plum" for seat in data.get("seats", []))
    if not has_plum:
        return NO_PLUM
    run_id = str(data.get("run_id", ""))
    if run_id == "web":
        return PLUM_OG
    if run_id == "web-2" or run_id.startswith("plum-policy-ladder-"):
        return CURRENT_PLUM
    raise ValueError(
        f"cannot classify Plum generation for {run_id}/{int(data.get('game_index', -1)):05d}"
    )


def _split_groups(groups: Iterable[str]) -> dict[str, str]:
    """Deterministic approximately 80/20 split of whole seed groups."""
    unique = sorted(set(groups))
    if not unique:
        return {}
    validation_n = max(1, round(len(unique) * 0.20)) if len(unique) > 1 else 0
    ranked = sorted(unique, key=lambda group: (hashlib.sha256(group.encode("utf-8")).hexdigest(), group))
    validation = set(ranked[:validation_n])
    return {group: ("validation" if group in validation else "train") for group in unique}


def _git_state(root: Path) -> dict:
    """Current commit and dirty marker; ``unknown`` outside a git checkout."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True
        ).stdout
        dirty = bool(
            status.strip()
        )
        names = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=root, check=True, capture_output=True, text=True,
        ).stdout.splitlines()
        digest = hashlib.sha256()
        for name in sorted(names):
            normal = name.replace("\\", "/")
            if not (
                normal.startswith("clude_")
                or normal.startswith("scripts/")
                or normal in ("requirements.txt", "requirements-web.txt", "pyproject.toml")
            ):
                continue
            path = root / name
            if not path.is_file():
                continue
            digest.update(normal.encode("utf-8") + b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
        return {"commit": commit, "dirty": dirty, "tree_sha256": digest.hexdigest()}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": "unknown", "dirty": None}


def experiment_context(corpus_manifest: Optional[Path] = None, root: Optional[Path] = None) -> dict:
    """Hashes attached to every Phase 14 sweep result."""
    root = Path(root or Path(__file__).resolve().parents[1])
    git = _git_state(root)
    corpus_hash = None
    if corpus_manifest is not None:
        corpus_hash = FrozenCorpus.open(corpus_manifest).sha256
    return {
        "corpus_sha256": corpus_hash,
        "code_sha256": git.get("tree_sha256"),
        "code_commit": git.get("commit"),
        "code_dirty": git.get("dirty"),
        "weights_sha256": file_hash(WEIGHTS_PATH),
    }


def baseline_state(source, root: Optional[Path] = None, method_documents: Optional[dict] = None) -> dict:
    """Hashes/configuration needed to reproduce the pre-training baseline.

    Human identities and method contents are not copied into the manifest;
    only the three adaptive characters' method-document hashes are included.
    Benchmark and arena result hashes are added later by ``report``.
    """
    root = Path(root or Path(__file__).resolve().parents[1])
    documents = method_documents or {
        identity: Logbook(source, identity).method() for identity in METHOD_IDENTITIES
    }
    methods = {}
    for identity in METHOD_IDENTITIES:
        document = documents.get(identity)
        methods[identity] = None if document is None else document_hash(document)
    return {
        "code": _git_state(root),
        "weights": {"path": str(WEIGHTS_PATH.relative_to(root)), "sha256": file_hash(WEIGHTS_PATH)},
        "presets": {name: PRESETS[name].to_dict() for name in sorted(PRESETS)},
        "method_sha256": methods,
        "measurements": {
            "status": "pending",
            "required": ["60-game belief benchmark", "192-game Plum table", "192-game six-character arena"],
        },
    }


def _corpus_hash(records: list[dict]) -> str:
    fields = [
        {
            key: row[key]
            for key in (
                "run_id", "game_index", "seed", "seed_group", "split", "record_sha256",
                "plum_generation", "created_at", "version",
            )
        }
        for row in records
    ]
    return document_hash(fields)


def snapshot_corpus(source, destination: Path, *, replace: bool = False) -> dict:
    """Freeze eligible source records below ``destination``.

    The destination must be new unless ``replace`` is explicit.  Replacement
    removes only known Phase 14 snapshot files (``manifest.json`` and copied
    ``games`` documents), never an arbitrary directory tree.
    """
    destination = Path(destination)
    manifest_path = destination / "manifest.json"
    copied = LocalStore(destination)
    if manifest_path.exists() and not replace:
        raise FileExistsError(f"snapshot already exists: {manifest_path}")

    accepted: list[tuple[dict, str]] = []
    excluded = Counter()
    scanned = 0
    inventory = [
        (run_id, index)
        for run_id in sorted(source.list_folders("games"))
        for index in source.list_games(run_id)
    ]
    baseline_documents = {
        identity: Logbook(source, identity).method() for identity in METHOD_IDENTITIES
    }
    for run_id, index in inventory:
        data = source.get_game(run_id, index)
        scanned += 1
        reason = exclusion_reason(data)
        if reason:
            excluded[reason] += 1
            continue
        generation = plum_generation(data)
        accepted.append((data, generation))

    accepted.sort(key=lambda pair: (str(pair[0]["run_id"]), int(pair[0]["game_index"])))
    split_by_group = _split_groups(str(data["seed"]) for data, _generation in accepted)
    rows = []
    for data, generation in accepted:
        run_id = str(data["run_id"])
        index = int(data["game_index"])
        seed_group = str(int(data["seed"]))
        digest = document_hash(data)
        copied.put_game(run_id, index, data)
        rows.append(
            {
                "run_id": run_id,
                "game_index": index,
                "seed": int(data["seed"]),
                "seed_group": seed_group,
                "split": split_by_group[seed_group],
                "record_sha256": digest,
                "plum_generation": generation,
                "created_at": data["created_at"],
                "version": int(data["version"]),
            }
        )

    counts = Counter(row["split"] for row in rows)
    generations = Counter(row["plum_generation"] for row in rows)
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "phase": 14,
        "source_uri": source.describe(),
        "cutoff_commit": CUTOFF_COMMIT,
        "cutoff": CUTOFF,
        "frozen_through": max((row["created_at"] for row in rows), default=None),
        "inventory": {
            "scanned": scanned,
            "eligible": len(rows),
            "excluded": dict(sorted(excluded.items())),
            "splits": dict(sorted(counts.items())),
            "plum_generations": dict(sorted(generations.items())),
            "seed_groups": len(split_by_group),
        },
        "corpus_sha256": _corpus_hash(rows),
        "baseline": baseline_state(source, method_documents=baseline_documents),
        "records": rows,
    }
    destination.mkdir(parents=True, exist_ok=True)
    methods_dir = destination / "baseline-methods"
    methods_dir.mkdir(parents=True, exist_ok=True)
    for identity, document in baseline_documents.items():
        if document is not None:
            (methods_dir / f"{identity}.json").write_text(
                json.dumps(document, indent=2) + "\n", encoding="utf-8"
            )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


@dataclass(frozen=True)
class FrozenCorpus:
    """Verified, read-only access to one Phase 14 snapshot."""

    root: Path
    manifest: dict

    @classmethod
    def open(cls, manifest_path: Path, *, verify: bool = True) -> "FrozenCorpus":
        manifest_path = Path(manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if int(manifest.get("manifest_version", 0)) != MANIFEST_VERSION:
            raise ValueError(
                f"unsupported Phase 14 manifest version {manifest.get('manifest_version')!r}"
            )
        corpus = cls(manifest_path.parent, manifest)
        if verify:
            corpus.verify()
        return corpus

    @property
    def sha256(self) -> str:
        return str(self.manifest["corpus_sha256"])

    def verify(self) -> None:
        rows = self.manifest.get("records", [])
        if _corpus_hash(rows) != self.sha256:
            raise ValueError("manifest corpus hash does not match its record index")
        store = LocalStore(self.root)
        for row in rows:
            data = store.get_game(row["run_id"], int(row["game_index"]))
            actual = document_hash(data)
            if actual != row["record_sha256"]:
                raise ValueError(
                    f"record hash mismatch for {row['run_id']}/{int(row['game_index']):05d}: "
                    f"expected {row['record_sha256']}, got {actual}"
                )

    def rows(self, split: Optional[str] = None) -> Iterator[dict]:
        """Manifest rows, optionally only ``train`` or ``validation``."""
        if split not in (None, "train", "validation"):
            raise ValueError("split must be train, validation or None")
        for row in self.manifest.get("records", []):
            if split is None or row["split"] == split:
                yield dict(row)

    def records(self, split: Optional[str] = None) -> Iterator[tuple[dict, GameRecord]]:
        """Manifest row and corresponding copied record, in manifest order."""
        store = LocalStore(self.root)
        for row in self.rows(split):
            data = store.get_game(row["run_id"], int(row["game_index"]))
            if document_hash(data) != row["record_sha256"]:
                raise ValueError(f"record changed after freeze: {row['run_id']}/{row['game_index']:05d}")
            yield row, GameRecord.from_dict(data)

    def baseline_method(self, identity: str) -> Optional[dict]:
        """Frozen pre-training method document, verified against the manifest."""
        if identity not in METHOD_IDENTITIES:
            raise ValueError(f"not a Phase 14 method identity: {identity!r}")
        expected = self.manifest["baseline"]["method_sha256"].get(identity)
        path = self.root / "baseline-methods" / f"{identity}.json"
        if expected is None:
            if path.exists():
                raise ValueError(f"unexpected baseline method document for {identity}")
            return None
        document = json.loads(path.read_text(encoding="utf-8"))
        actual = document_hash(document)
        if actual != expected:
            raise ValueError(f"baseline {identity} method hash mismatch: expected {expected}, got {actual}")
        return document


def build_method_candidates(corpus: FrozenCorpus, destination: Path, green_state: Optional[dict] = None) -> dict:
    """Build deterministic Mustard/White documents from the training split.

    ``web`` records relabel their Plum contribution to ``PlumOG`` for
    White's identity-conditioned chain.  Current-network records retain
    ``Plum``.  Green is accepted only as an explicit fresh-training state;
    old live posteriors are never reconstructed from records.
    """
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    mustard = method_memory.empty_memory("rows")
    white = method_memory.empty_memory("counts")
    for row, record in corpus.records("train"):
        method_memory.absorb(mustard, record)
        label_map = {"Plum": "PlumOG"} if row["plum_generation"] == PLUM_OG else None
        method_memory.absorb(white, record, white_label_map=label_map)

    candidates = {"Mustard": mustard, "White": white}
    if green_state is not None:
        if green_state.get("kind") != "state":
            raise ValueError("Green candidate must be a method-memory state document")
        candidates["Green"] = green_state
    for identity, document in candidates.items():
        (destination / f"{identity}.json").write_text(
            json.dumps(document, indent=2) + "\n", encoding="utf-8"
        )
    stage = {
        "stage_version": STAGE_VERSION,
        "corpus_sha256": corpus.sha256,
        "split": "train",
        "documents": {identity: document_hash(document) for identity, document in sorted(candidates.items())},
        "pending": [identity for identity in METHOD_IDENTITIES if identity not in candidates],
    }
    (destination / "stage.json").write_text(json.dumps(stage, indent=2) + "\n", encoding="utf-8")
    return stage


def load_staged_methods(stage_dir: Path) -> tuple[dict, dict]:
    """Read and hash-check a staged method set."""
    stage_dir = Path(stage_dir)
    stage = json.loads((stage_dir / "stage.json").read_text(encoding="utf-8"))
    if int(stage.get("stage_version", 0)) != STAGE_VERSION:
        raise ValueError(f"unsupported method stage version {stage.get('stage_version')!r}")
    documents = {}
    for identity, expected in stage.get("documents", {}).items():
        if identity not in METHOD_IDENTITIES:
            raise ValueError(f"unexpected staged method identity {identity!r}")
        document = json.loads((stage_dir / f"{identity}.json").read_text(encoding="utf-8"))
        actual = document_hash(document)
        if actual != expected:
            raise ValueError(f"staged {identity} hash mismatch: expected {expected}, got {actual}")
        if document.get("kind") != method_memory.kind_for(identity):
            raise ValueError(f"staged {identity} has method kind {document.get('kind')!r}")
        documents[identity] = document
    return stage, documents


def active_table_ids(store) -> list[str]:
    """Table ids that are neither finished nor abandoned."""
    active = []
    for table_id in store.list_docs("tables"):
        try:
            document = store.get_doc(f"tables/{table_id}.json")
        except KeyError:
            continue
        if document.get("status") not in ("finished", "abandoned"):
            active.append(table_id)
    return sorted(active)


def method_hashes(store, identities: Iterable[str] = METHOD_IDENTITIES) -> dict[str, Optional[str]]:
    """Current method hashes only; never returns method contents."""
    hashes = {}
    for identity in identities:
        document = Logbook(store, identity).method()
        hashes[identity] = None if document is None else document_hash(document)
    return hashes


def promote_methods(
    store,
    stage_dir: Path,
    expected_hashes: dict[str, Optional[str]],
    backup_dir: Path,
    *,
    apply: bool = False,
) -> dict:
    """Check or promote staged method documents, with rollback on failure.

    Every staged identity needs an expected current hash.  A real promotion
    requires all three method documents, no active tables and a new local
    backup directory.  Dry-run performs every read/hash check but writes
    neither the target nor the backup.
    """
    stage, candidates = load_staged_methods(stage_dir)
    if apply and set(candidates) != set(METHOD_IDENTITIES):
        raise ValueError(f"promotion requires all methods; stage still pending {stage.get('pending', [])}")
    current_documents = {identity: Logbook(store, identity).method() for identity in candidates}
    current_hashes = {
        identity: None if document is None else document_hash(document)
        for identity, document in current_documents.items()
    }
    missing_expectations = sorted(set(candidates) - set(expected_hashes))
    if missing_expectations:
        raise ValueError(f"missing expected source hashes for {missing_expectations}")
    mismatches = {
        identity: {"expected": expected_hashes[identity], "actual": current_hashes[identity]}
        for identity in candidates
        if expected_hashes[identity] != current_hashes[identity]
    }
    if mismatches:
        raise ValueError(f"method source hash mismatch: {mismatches}")
    active = active_table_ids(store)
    if active:
        raise RuntimeError(f"method promotion requires no active tables; found {len(active)}")

    result = {
        "apply": bool(apply),
        "target": store.describe(),
        "corpus_sha256": stage.get("corpus_sha256"),
        "current": current_hashes,
        "candidate": {identity: document_hash(document) for identity, document in candidates.items()},
        "backup": str(Path(backup_dir)),
    }
    if not apply:
        return result

    backup_dir = Path(backup_dir)
    if backup_dir.exists() and any(backup_dir.iterdir()):
        raise FileExistsError(f"backup directory is not empty: {backup_dir}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_manifest = {"target": store.describe(), "documents": current_hashes}
    for identity, document in current_documents.items():
        if document is not None:
            (backup_dir / f"{identity}.json").write_text(
                json.dumps(document, indent=2) + "\n", encoding="utf-8"
            )
    (backup_dir / "backup.json").write_text(json.dumps(backup_manifest, indent=2) + "\n", encoding="utf-8")

    written = []
    try:
        for identity in METHOD_IDENTITIES:
            Logbook(store, identity).save_method(candidates[identity])
            written.append(identity)
    except Exception:
        for identity in reversed(written):
            old = current_documents[identity]
            if old is None:
                store.delete_doc(method_key(identity))
            else:
                Logbook(store, identity).save_method(old)
        raise
    return result


def restore_methods(
    store,
    backup_dir: Path,
    expected_hashes: dict[str, Optional[str]],
    *,
    apply: bool = False,
) -> dict:
    """Hash-guarded restoration of a method-only backup."""
    backup_dir = Path(backup_dir)
    backup = json.loads((backup_dir / "backup.json").read_text(encoding="utf-8"))
    restored = {}
    for identity in METHOD_IDENTITIES:
        path = backup_dir / f"{identity}.json"
        restored[identity] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    current = method_hashes(store)
    if current != expected_hashes:
        raise ValueError(f"method source hash mismatch before restore: expected {expected_hashes}, got {current}")
    active = active_table_ids(store)
    if active:
        raise RuntimeError(f"method restore requires no active tables; found {len(active)}")
    result = {"apply": bool(apply), "target": store.describe(), "backup_target": backup.get("target")}
    if apply:
        for identity, document in restored.items():
            if document is None:
                store.delete_doc(method_key(identity))
            else:
                Logbook(store, identity).save_method(document)
    return result


def public_report(corpus: FrozenCorpus, stage_dir: Optional[Path] = None) -> dict:
    """Privacy-safe corpus/stage summary for maintainer reports."""
    report = {
        "manifest_version": corpus.manifest["manifest_version"],
        "corpus_sha256": corpus.sha256,
        "source_uri": corpus.manifest["source_uri"],
        "cutoff": corpus.manifest["cutoff"],
        "frozen_through": corpus.manifest["frozen_through"],
        "inventory": corpus.manifest["inventory"],
        "baseline": corpus.manifest["baseline"],
    }
    if stage_dir is not None:
        stage, documents = load_staged_methods(stage_dir)
        report["staged_methods"] = {
            "corpus_sha256": stage.get("corpus_sha256"),
            "hashes": stage.get("documents", {}),
            "pending": stage.get("pending", []),
            "games": {identity: method_memory.n_games(document) for identity, document in documents.items()},
            "private_identity_counts": {
                identity: len(method_memory.priors(document))
                for identity, document in documents.items()
                if document.get("kind") == "counts"
            },
        }
    return report


def snapshot_narrative_logbooks(
    source,
    destination: Path,
    *,
    identities: Iterable[str] = CHARACTER_IDENTITIES,
) -> dict:
    """Copy one immutable, character-only narrative-memory snapshot.

    Heads, digests and entries are copied; ``method.json`` is excluded so
    paid memory tests cannot accidentally load a different numerical method.
    """
    destination = Path(destination)
    manifest_path = destination / "manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"memory snapshot already exists: {manifest_path}")
    local = LocalStore(destination)
    keys = []
    for identity in identities:
        prefix = f"logbooks/{identity}"
        for name in ("head", "digest"):
            key = f"{prefix}/{name}.json"
            try:
                document = source.get_doc(key)
            except KeyError:
                continue
            local.put_doc(key, document)
            keys.append({"key": key, "sha256": document_hash(document)})
        entry_names = list(source.list_docs(f"{prefix}/entries"))
        for name in entry_names:
            key = f"{prefix}/entries/{name}.json"
            document = source.get_doc(key)
            local.put_doc(key, document)
            keys.append({"key": key, "sha256": document_hash(document)})
    keys.sort(key=lambda row: row["key"])
    manifest = {
        "version": 1,
        "source_uri": source.describe(),
        "identities": list(identities),
        "documents": keys,
        "snapshot_sha256": document_hash(keys),
        "readonly": True,
        "excluded": ["method.json"],
    }
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify_narrative_logbooks(destination: Path) -> dict:
    """Verify and return a narrative-memory snapshot manifest."""
    destination = Path(destination)
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    if int(manifest.get("version", 0)) != 1 or manifest.get("readonly") is not True:
        raise ValueError("not a Phase 14 read-only memory snapshot")
    store = LocalStore(destination)
    for row in manifest.get("documents", []):
        actual = document_hash(store.get_doc(row["key"]))
        if actual != row["sha256"]:
            raise ValueError(f"memory snapshot hash mismatch for {row['key']}")
    if document_hash(manifest.get("documents", [])) != manifest.get("snapshot_sha256"):
        raise ValueError("memory snapshot manifest hash mismatch")
    return manifest
