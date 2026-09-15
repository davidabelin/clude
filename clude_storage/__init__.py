"""Persistence: game records and the stores that hold them (Phase 5d).

Started a phase early (docs/phase5-plan.md, decision 6) so the arena's
self-play games are kept, not regenerated: each `GameRecord` is one
finished game with its seats, deal, and full event log, and each run
also stores its settings and metrics. Two stores share one interface:
`LocalStore` (JSON files under a directory, the default) and `GcsStore`
(the same keys as objects in a Google Cloud Storage bucket), picked by
`open_store` from a path or a ``gs://bucket/prefix`` URI. Nothing else
in the repo needs `google-cloud-storage`; it is imported only when a
`GcsStore` is actually built.

Phase 7's logbooks (`clude_storage.logbooks`) live in the same store
under ``logbooks/<identity>/``: one identity's entries, head and method
memory, built on the generic document methods every store has. A
seat's redacted view of a stored game is rebuilt by
`clude_training.replay`.
"""
from __future__ import annotations

from .logbooks import (
    Dossier,
    Logbook,
    LogbookEntry,
    LogbookHead,
    list_logbooks,
    memory_counts,
    render_entry,
    render_memory,
)
from .records import (
    GameRecord,
    SeatRecord,
    event_from_json,
    event_to_json,
    node_from_json,
    node_to_json,
)
from .stores import (
    DEFAULT_CREDENTIALS_FILE,
    GcsStore,
    LocalStore,
    RecordStore,
    default_credentials_path,
    is_gcs_uri,
    open_store,
    split_gcs_uri,
    validate_key,
)

__all__ = [
    "DEFAULT_CREDENTIALS_FILE",
    "Dossier",
    "GameRecord",
    "GcsStore",
    "LocalStore",
    "Logbook",
    "LogbookEntry",
    "LogbookHead",
    "RecordStore",
    "SeatRecord",
    "default_credentials_path",
    "event_from_json",
    "event_to_json",
    "is_gcs_uri",
    "list_logbooks",
    "memory_counts",
    "node_from_json",
    "node_to_json",
    "open_store",
    "render_entry",
    "render_memory",
    "split_gcs_uri",
    "validate_key",
]
