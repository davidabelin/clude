"""Phase 8.1b: what the Cloud Run deploy depends on, checked without it.

The deploy itself cannot run in a test (it needs the project and Cloud
Build), and gunicorn does not run on Windows, so the first time the
container starts is on Cloud Run. What can be pinned here is everything
that decides whether that start is safe and correct: the upload keeps the
secrets out, the app behaves behind the proxy, it builds against a
``gs://`` store without touching the network, and `store copy` fills the
cloud store with exactly what the plan says (`docs/phase8.1-plan.md`).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from clude_storage import GcsStore, LocalStore
from clude_storage.mirror import copy_docs, plan_mirror, walk_docs
from tests.test_storage import _FakeClient

ROOT = Path(__file__).resolve().parents[1]
IGNORE_FILES = (".gcloudignore", ".dockerignore")
MUST_STAY_OUT = ("clude-game-sa.json", ".env", "data/", ".venv/", ".git/")


def _patterns(name: str) -> set:
    lines = (ROOT / name).read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


@pytest.mark.parametrize("name", IGNORE_FILES)
def test_the_upload_and_the_image_keep_the_secrets_out(name):
    patterns = _patterns(name)
    missing = [p for p in MUST_STAY_OUT if p not in patterns]
    assert not missing, f"{name} lets through {missing}"


def test_the_two_ignore_files_list_the_same_things():
    # Docker needs `**/` to match below the root; gcloud (gitignore rules)
    # matches at any depth already. Otherwise the lists are one list.
    def norm(name):
        return {p.removeprefix("**/") for p in _patterns(name)} - set(IGNORE_FILES) - {"Dockerfile"}

    assert norm(".gcloudignore") == norm(".dockerignore")


def test_the_image_installs_its_own_requirements_and_serves_the_factory():
    """Since Phase 9 the image serves the combined ASGI app (Flask and
    the MCP endpoint, one registry) under gunicorn's uvicorn worker."""
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "requirements-web.txt" in dockerfile
    assert '"clude_web.mcp:combined_app()"' in dockerfile
    assert "-k uvicorn.workers.UvicornWorker" in dockerfile
    assert "--workers 1" in dockerfile
    wanted = (ROOT / "requirements-web.txt").read_text(encoding="utf-8")
    for package in ("flask", "gunicorn", "google-cloud-storage", "anthropic", "mcp", "asgiref", "uvicorn"):
        assert package in wanted, f"{package} is not installed in the image"


def test_behind_https_the_cookie_is_secure_and_the_proxy_is_trusted(monkeypatch, tmp_path):
    from werkzeug.middleware.proxy_fix import ProxyFix

    from clude_web import create_app

    monkeypatch.setenv("CLUDE_WEB_HTTPS", "1")
    app = create_app({"TESTING": True, "STORE_URI": str(tmp_path)})
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert isinstance(app.wsgi_app, ProxyFix)

    # The proxy's scheme reaches the app: a redirect to the login page
    # stays on https rather than dropping to the proxy's plain http.
    response = app.test_client().get(
        "/", headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "clude.example"}
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert not response.headers["Location"].startswith("http://")


def test_locally_the_proxy_headers_are_not_trusted(monkeypatch, tmp_path):
    from werkzeug.middleware.proxy_fix import ProxyFix

    from clude_web import create_app

    monkeypatch.delenv("CLUDE_WEB_HTTPS", raising=False)
    app = create_app({"TESTING": True, "STORE_URI": str(tmp_path)})
    assert app.config["SESSION_COOKIE_SECURE"] is False
    assert not isinstance(app.wsgi_app, ProxyFix)


def test_the_app_builds_against_a_bucket_without_touching_the_network(monkeypatch):
    from clude_web import create_app

    # Building a GCS client is what would reach the network (or fail for
    # want of credentials); the store must not build one until a request.
    def refuse(*_args, **_kwargs):
        raise AssertionError("create_app built a storage client")

    monkeypatch.setattr("clude_storage.stores.make_gcs_client", refuse)
    app = create_app({"TESTING": True, "STORE_URI": "gs://clude-game-data/llm"})
    store = app.extensions["store"]
    assert isinstance(store, GcsStore)
    assert store.describe() == "gs://clude-game-data/llm"


# --- store copy -------------------------------------------------------


def _source(tmp_path) -> LocalStore:
    """A small `data/llm`: two grid runs (one with a cached trace), a
    ring run, a run with one ring record among grid ones, the rebuilt
    logbooks and a ring-era copy, an account, a watched game, and a loose
    report file at the root."""
    store = LocalStore(tmp_path / "source")
    for run_id, versions in {
        "grid-a": [3, 3],
        "grid-b": [3],
        "ring": [2, 2],
        "mixed": [3, 2],
    }.items():
        store.put_run(run_id, {"n_games": len(versions)})
        for i, version in enumerate(versions):
            store.put_game(run_id, i, {"game_index": i, "version": version})
    store.put_doc("traces/grid-a/00001.json", {"frames": [1]})
    store.put_doc("traces/ring/00000.json", {"frames": [0]})
    store.put_doc("logbooks/Mustard/head.json", {"tally": {}})
    store.put_doc("logbooks/Mustard/method.json", {"rows": [1, 2]})
    store.put_doc("logbooks/Plum/entries/00001.json", {"title": "t"})
    store.put_doc("logbooks-ring/Mustard/head.json", {"tally": {}})
    store.put_doc("users/david.json", {"hash": "x"})
    store.put_doc("watch/abc.json", {"turns": 3})
    store.put_doc("ladder_plum.json", {"report": True})
    return store


def test_the_mirror_takes_grid_runs_their_traces_and_the_logbooks(tmp_path):
    plan = plan_mirror(_source(tmp_path))
    assert plan.runs == ["grid-a", "grid-b"]
    assert sorted(plan.skipped_runs) == ["mixed", "ring"]
    assert plan.keys == [
        "runs/grid-a.json",
        "games/grid-a/00000.json",
        "games/grid-a/00001.json",
        "traces/grid-a/00001.json",
        "runs/grid-b.json",
        "games/grid-b/00000.json",
        "logbooks/Mustard/head.json",
        "logbooks/Mustard/method.json",
        "logbooks/Plum/entries/00001.json",
    ]


def test_the_minimum_version_is_a_dial(tmp_path):
    plan = plan_mirror(_source(tmp_path), min_version=2)
    assert plan.runs == ["grid-a", "grid-b", "mixed", "ring"]
    assert "traces/ring/00000.json" in plan.keys


@pytest.mark.parametrize("kind", ["local", "bucket"])
def test_a_copy_is_exact_and_can_be_run_twice(tmp_path, kind):
    source = _source(tmp_path)
    if kind == "local":
        dest = LocalStore(tmp_path / "dest")
    else:
        dest = GcsStore("clude-game-data", "llm", client=_FakeClient())
    plan = plan_mirror(source)
    assert copy_docs(source, dest, plan.keys, workers=4) == len(plan.keys)
    assert copy_docs(source, dest, plan.keys, workers=4) == len(plan.keys)

    for key in plan.keys:
        assert dest.get_doc(key) == source.get_doc(key)
    assert dest.list_runs() == ["grid-a", "grid-b"]
    assert dest.list_games("grid-a") == [0, 1]
    assert dest.list_folders("") == ["games", "logbooks", "runs", "traces"]
    assert walk_docs(dest, "logbooks") == [k for k in plan.keys if k.startswith("logbooks/")]


def test_the_cli_copies_and_its_dry_run_copies_nothing(tmp_path, capsys):
    spec = importlib.util.spec_from_file_location("clude_cli", ROOT / "scripts" / "clude_cli.py")
    clude_cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(clude_cli)
    source = _source(tmp_path)
    dest = tmp_path / "dest"

    argv = ["store", "copy", "--uri", str(source.root), "--to", str(dest)]
    assert clude_cli.main(argv + ["--dry-run"]) == 0
    assert not dest.exists()
    out = capsys.readouterr().out
    assert "2 runs (3 game records, 1 traces), 3 logbook documents: 9 documents" in out
    assert "2 runs (mixed, ring)" in out

    assert clude_cli.main(argv) == 0
    assert LocalStore(dest).list_runs() == ["grid-a", "grid-b"]
    assert clude_cli.main(["store", "copy", "--uri", str(dest), "--to", str(dest)]) == 2
    assert clude_cli.main(["store", "copy", "--uri", str(dest)]) == 2


def test_the_lobby_reads_summaries_in_parallel_and_keeps_its_order():
    from clude_web.views import run_listing

    class Store:
        """A bucket whose listing names a run that has since vanished."""

        def list_runs(self):
            return ["b-run", "web", "a-run", "gone"]

        def get_run(self, run_id):
            if run_id == "gone":
                raise KeyError(run_id)
            return {"n_games": 2, "roster": ["Plum"], "player_counts": [3]}

    listing = run_listing(Store())
    assert [r["run_id"] for r in listing] == ["web", "a-run", "b-run"]
    # No game line carries a cost, so the run has no total (Phase 9g).
    assert listing[0] == {"run_id": "web", "n_games": 2, "roster": ["Plum"], "player_counts": [3], "cost": None}
