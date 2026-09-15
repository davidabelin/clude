"""Record stores: one interface, a local-directory backend and a Google
Cloud Storage backend, and `open_store` to pick one from a path or a
``gs://`` URI.

Both backends use the same keys, so a run written locally and one
written to a bucket have the same layout::

    runs/<run_id>.json              the run's settings and metrics
    games/<run_id>/<index>.json     one GameRecord per game (index zero-padded)
    logbooks/<identity>/...         Phase 7's logbooks (`clude_storage.logbooks`)

The run and game methods are the Phase 5d surface. Phase 7 added the
generic document methods (`put_doc`, `get_doc`, `delete_doc`,
`list_docs`, `list_folders`) that the logbooks are built on; a key is
a ``/``-separated path of safe segments ending in ``.json``
(`validate_key`).

Credentials for `GcsStore`: an explicit ``credentials_path``, else the
``CLUDE_GCS_CREDENTIALS`` environment variable, else the service-account
key file `DEFAULT_CREDENTIALS_FILE` next to the repo root if it exists
(that file is gitignored; never commit it), else whatever
``google.cloud.storage.Client()`` finds on its own (application
default credentials). The key file is read only by the client library;
nothing here prints or copies it.

Mirrors the shape of ``rps_storage/object_store.py`` (``gs://``
detection, lazy client construction) but keyed by run and game rather
than by free-form path, since that is the only thing clude stores yet.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional, Protocol

DEFAULT_CREDENTIALS_FILE = "clude-game-sa.json"
CREDENTIALS_ENV = "CLUDE_GCS_CREDENTIALS"
_REPO_ROOT = Path(__file__).resolve().parents[1]
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def validate_run_id(run_id: str) -> str:
    """Return `run_id` if it is safe to use as a path segment.

    Raises
    ------
    ValueError
        If it is empty or contains anything but letters, digits, ``_``,
        ``.`` and ``-`` (or starts with a non-alphanumeric).
    """
    if not isinstance(run_id, str) or not _RUN_ID_PATTERN.match(run_id):
        raise ValueError(f"invalid run id {run_id!r}: use letters, digits, '_', '.', '-'")
    return run_id


def run_key(run_id: str) -> str:
    """Storage key for a run summary."""
    return f"runs/{validate_run_id(run_id)}.json"


def game_key(run_id: str, game_index: int) -> str:
    """Storage key for one game record."""
    if game_index < 0:
        raise ValueError("game_index must be >= 0")
    return f"games/{validate_run_id(run_id)}/{int(game_index):05d}.json"


def validate_prefix(prefix: str) -> str:
    """Return `prefix` (a folder path such as ``logbooks/Plum/entries``)
    if every ``/``-separated segment passes `validate_run_id`; the
    empty prefix is the store root.

    Raises
    ------
    ValueError
        On an empty segment or an unsafe one.
    """
    if not isinstance(prefix, str):
        raise ValueError(f"invalid prefix {prefix!r}")
    prefix = prefix.strip("/")
    if prefix:
        for segment in prefix.split("/"):
            validate_run_id(segment)
    return prefix


def validate_key(key: str) -> str:
    """Return `key` if it is a safe document key: a `validate_prefix`
    path whose last segment ends in ``.json``.

    Raises
    ------
    ValueError
        If it does not end in ``.json`` or any segment is unsafe.
    """
    if not isinstance(key, str) or not key.endswith(".json") or key.startswith("/"):
        raise ValueError(f"invalid document key {key!r}: expected segments/name.json")
    validate_prefix(key)
    return key


class RecordStore(Protocol):
    """What the arena and the logbooks need from a store. Documents are
    plain dicts (JSON objects) so the store never depends on the record
    types."""

    def put_game(self, run_id: str, game_index: int, record: dict) -> str:
        """Write one game record; returns where it went."""
        ...

    def get_game(self, run_id: str, game_index: int) -> dict: ...

    def list_games(self, run_id: str) -> list:
        """Game indices stored for `run_id`, ascending."""
        ...

    def put_run(self, run_id: str, summary: dict) -> str:
        """Write the run summary; returns where it went."""
        ...

    def get_run(self, run_id: str) -> dict: ...

    def list_runs(self) -> list:
        """Run ids with a summary, sorted."""
        ...

    def put_doc(self, key: str, document: dict) -> str:
        """Write one document at a `validate_key` key; returns where it went."""
        ...

    def get_doc(self, key: str) -> dict:
        """Read one document; `KeyError` if absent."""
        ...

    def delete_doc(self, key: str) -> bool:
        """Remove one document; True if it existed."""
        ...

    def list_docs(self, prefix: str) -> list:
        """Names (``.json`` stripped) of the documents directly under a
        folder, sorted; empty for a missing folder."""
        ...

    def list_folders(self, prefix: str) -> list:
        """Names of the sub-folders directly under a folder, sorted."""
        ...

    def describe(self) -> str:
        """Human-readable location, for CLI output."""
        ...


def _dumps(document: dict) -> str:
    return json.dumps(document, indent=2, sort_keys=False)


class LocalStore:
    """JSON files under `root` (created on first write).

    Parameters
    ----------
    root : str or Path
        Directory to hold ``runs/`` and ``games/``.
    """

    def __init__(self, root) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        return self.root / key

    def _write(self, key: str, document: dict) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_dumps(document), encoding="utf-8")
        return str(path)

    def _read(self, key: str) -> dict:
        path = self._path(key)
        if not path.exists():
            raise KeyError(f"no such document: {key} (under {self.root})")
        return json.loads(path.read_text(encoding="utf-8"))

    def put_game(self, run_id: str, game_index: int, record: dict) -> str:
        return self._write(game_key(run_id, game_index), record)

    def get_game(self, run_id: str, game_index: int) -> dict:
        return self._read(game_key(run_id, game_index))

    def list_games(self, run_id: str) -> list:
        folder = self.root / "games" / validate_run_id(run_id)
        if not folder.is_dir():
            return []
        return sorted(int(p.stem) for p in folder.glob("*.json") if p.stem.isdigit())

    def put_run(self, run_id: str, summary: dict) -> str:
        return self._write(run_key(run_id), summary)

    def get_run(self, run_id: str) -> dict:
        return self._read(run_key(run_id))

    def list_runs(self) -> list:
        folder = self.root / "runs"
        if not folder.is_dir():
            return []
        return sorted(p.stem for p in folder.glob("*.json"))

    def put_doc(self, key: str, document: dict) -> str:
        return self._write(validate_key(key), document)

    def get_doc(self, key: str) -> dict:
        return self._read(validate_key(key))

    def delete_doc(self, key: str) -> bool:
        path = self._path(validate_key(key))
        if not path.is_file():
            return False
        path.unlink()
        return True

    def list_docs(self, prefix: str) -> list:
        folder = self._path(validate_prefix(prefix))
        if not folder.is_dir():
            return []
        return sorted(p.stem for p in folder.iterdir() if p.is_file() and p.suffix == ".json")

    def list_folders(self, prefix: str) -> list:
        folder = self._path(validate_prefix(prefix))
        if not folder.is_dir():
            return []
        return sorted(p.name for p in folder.iterdir() if p.is_dir())

    def describe(self) -> str:
        return str(self.root)


def is_gcs_uri(uri: str) -> bool:
    """True for ``gs://...``."""
    return str(uri).startswith("gs://")


def split_gcs_uri(uri: str) -> tuple:
    """``gs://bucket/some/prefix`` -> ``("bucket", "some/prefix")``; the
    prefix may be empty.

    Raises
    ------
    ValueError
        If `uri` is not a ``gs://`` URI or names no bucket.
    """
    if not is_gcs_uri(uri):
        raise ValueError(f"not a gs:// URI: {uri!r}")
    remainder = str(uri)[len("gs://"):]
    bucket, _, prefix = remainder.partition("/")
    if not bucket:
        raise ValueError(f"gs:// URI names no bucket: {uri!r}")
    return bucket, prefix.strip("/")


def default_credentials_path() -> Optional[str]:
    """The service-account key file to use when none is given: the
    `CREDENTIALS_ENV` variable if set, else `DEFAULT_CREDENTIALS_FILE`
    at the repo root if present, else None (application default
    credentials)."""
    from_env = os.environ.get(CREDENTIALS_ENV)
    if from_env:
        return from_env
    candidate = _REPO_ROOT / DEFAULT_CREDENTIALS_FILE
    return str(candidate) if candidate.exists() else None


def make_gcs_client(credentials_path: Optional[str] = None):
    """Build a ``google.cloud.storage.Client``, from a service-account
    key file when one is given or found (`default_credentials_path`).

    Raises
    ------
    RuntimeError
        If `google-cloud-storage` is not installed.
    """
    try:
        from google.cloud import storage
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-storage is required for gs:// stores: pip install google-cloud-storage"
        ) from exc
    path = credentials_path or default_credentials_path()
    if path:
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(path)
        return storage.Client(project=credentials.project_id, credentials=credentials)
    return storage.Client()


class GcsStore:
    """Documents as JSON objects in one bucket under `prefix`.

    Parameters
    ----------
    bucket : str
        Bucket name (no ``gs://``).
    prefix : str
        Key prefix inside the bucket; empty for the bucket root.
    client : object or None
        A ``google.cloud.storage.Client`` (or a test double with the
        same ``bucket(name)``/``list_blobs(name, prefix=...)`` surface).
        Built lazily by `make_gcs_client` when None.
    credentials_path : str or None
        Passed to `make_gcs_client` when a client has to be built.
    """

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        client=None,
        credentials_path: Optional[str] = None,
    ) -> None:
        self.bucket_name = bucket
        self.prefix = prefix.strip("/")
        self._client = client
        self._credentials_path = credentials_path

    @property
    def client(self):
        if self._client is None:
            self._client = make_gcs_client(self._credentials_path)
        return self._client

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def _write(self, key: str, document: dict) -> str:
        blob = self.client.bucket(self.bucket_name).blob(self._full_key(key))
        blob.upload_from_string(_dumps(document), content_type="application/json")
        return f"gs://{self.bucket_name}/{self._full_key(key)}"

    def _read(self, key: str) -> dict:
        blob = self.client.bucket(self.bucket_name).blob(self._full_key(key))
        if not blob.exists():
            raise KeyError(f"no such object: gs://{self.bucket_name}/{self._full_key(key)}")
        return json.loads(blob.download_as_text())

    def _children(self, folder: str) -> tuple:
        """``(folders, docs)`` directly under `folder`: the distinct next
        path segments of every blob below it, split by whether anything
        follows the segment."""
        base = self._full_key(folder) if folder else self.prefix
        prefix = base.rstrip("/") + "/" if base else ""
        folders: set = set()
        docs: list = []
        for blob in self.client.list_blobs(self.bucket_name, prefix=prefix):
            rest = blob.name[len(prefix):]
            if not rest:
                continue
            head, sep, _tail = rest.partition("/")
            if sep:
                folders.add(head)
            else:
                docs.append(head)
        return sorted(folders), sorted(docs)

    def _names_under(self, folder: str) -> list:
        return self._children(folder)[1]

    def put_game(self, run_id: str, game_index: int, record: dict) -> str:
        return self._write(game_key(run_id, game_index), record)

    def get_game(self, run_id: str, game_index: int) -> dict:
        return self._read(game_key(run_id, game_index))

    def list_games(self, run_id: str) -> list:
        names = self._names_under(f"games/{validate_run_id(run_id)}")
        return sorted(int(n[:-5]) for n in names if n.endswith(".json") and n[:-5].isdigit())

    def put_run(self, run_id: str, summary: dict) -> str:
        return self._write(run_key(run_id), summary)

    def get_run(self, run_id: str) -> dict:
        return self._read(run_key(run_id))

    def list_runs(self) -> list:
        names = self._names_under("runs")
        return sorted(n[:-5] for n in names if n.endswith(".json"))

    def put_doc(self, key: str, document: dict) -> str:
        return self._write(validate_key(key), document)

    def get_doc(self, key: str) -> dict:
        return self._read(validate_key(key))

    def delete_doc(self, key: str) -> bool:
        blob = self.client.bucket(self.bucket_name).blob(self._full_key(validate_key(key)))
        if not blob.exists():
            return False
        blob.delete()
        return True

    def list_docs(self, prefix: str) -> list:
        names = self._names_under(validate_prefix(prefix))
        return sorted(n[:-5] for n in names if n.endswith(".json"))

    def list_folders(self, prefix: str) -> list:
        return self._children(validate_prefix(prefix))[0]

    def describe(self) -> str:
        return f"gs://{self.bucket_name}/{self.prefix}" if self.prefix else f"gs://{self.bucket_name}"


def open_store(uri: str, credentials_path: Optional[str] = None) -> RecordStore:
    """A `GcsStore` for a ``gs://bucket[/prefix]`` URI, else a
    `LocalStore` rooted at the path."""
    if is_gcs_uri(uri):
        bucket, prefix = split_gcs_uri(uri)
        return GcsStore(bucket, prefix, credentials_path=credentials_path)
    return LocalStore(uri)
