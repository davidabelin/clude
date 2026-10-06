"""Copy selected records, summaries, traces and logbooks between stores.

Only runs whose records meet min_version are selected (default grid version
3). Accounts, live tables/watch state and ring archives are excluded. Matching
keys overwrite; destination-only objects are not deleted. Dry run previews
without writes. This is data copying, not deployment. See docs/cli.md.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from .records import GRID_RECORD_VERSION, RECORD_VERSION
from .stores import RecordStore, game_key, run_key

LOGBOOK_PREFIX = "logbooks"
TRACE_PREFIX = "traces"


@dataclass
class MirrorPlan:
    """What `plan_mirror` chose.

    Attributes
    ----------
    keys : list of str
        Every document key to copy, in a stable order.
    runs : list of str
        The run ids taken.
    skipped_runs : list of str
        Run ids left behind because a record was older than the minimum.
    """

    keys: list = field(default_factory=list)
    runs: list = field(default_factory=list)
    skipped_runs: list = field(default_factory=list)


def walk_docs(store: RecordStore, prefix: str) -> list:
    """Every document key at any depth under `prefix`, sorted."""
    keys = [f"{prefix}/{name}.json" for name in store.list_docs(prefix)]
    for folder in store.list_folders(prefix):
        keys.extend(walk_docs(store, f"{prefix}/{folder}"))
    return sorted(keys)


def plan_mirror(store: RecordStore, min_version: int = GRID_RECORD_VERSION) -> MirrorPlan:
    """Choose what to copy out of `store` (see the module docstring).

    A run is taken only if every one of its records is at least
    `min_version`, which means reading each record once; locally that is
    about a second for `data/llm`.
    """
    plan = MirrorPlan()
    for run_id in store.list_runs():
        indices = store.list_games(run_id)
        versions = [
            int(store.get_game(run_id, i).get("version", RECORD_VERSION)) for i in indices
        ]
        if any(v < min_version for v in versions):
            plan.skipped_runs.append(run_id)
            continue
        plan.runs.append(run_id)
        plan.keys.append(run_key(run_id))
        plan.keys.extend(game_key(run_id, i) for i in indices)
        plan.keys.extend(walk_docs(store, f"{TRACE_PREFIX}/{run_id}"))
    plan.keys.extend(walk_docs(store, LOGBOOK_PREFIX))
    return plan


def copy_docs(source: RecordStore, dest: RecordStore, keys, workers: int = 10) -> int:
    """Copy each key from `source` to `dest`, overwriting; returns the
    number copied.

    Parallel because a bucket write is a round trip and a mirror is
    about 1,300 of them; a store's client is shared across the threads,
    which `google-cloud-storage` allows. Ten matches that client's
    connection pool; more threads only churn connections.
    """
    keys = list(keys)

    def one(key: str) -> None:
        dest.put_doc(key, source.get_doc(key))

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for _ in pool.map(one, keys):
            pass
    return len(keys)
