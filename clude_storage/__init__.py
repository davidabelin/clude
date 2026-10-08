"""Public record, store and logbook persistence interfaces.

Use open_store for a local path or gs:// URI; both share document keys.
GameRecord is omniscient. Use masked replay for live-seat views.
See docs/architecture.md and docs/logbooks.md.
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
    DEVELOPMENT_PHASE,
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
    "DEVELOPMENT_PHASE",
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
