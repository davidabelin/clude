"""The web scaffold: the login gate, accounts, and the app factory.

Flask's test client against a `LocalStore` in a temp dir. Nothing here
touches the network, a real store, or the developer's `FLASK_SECRET_KEY`
-- `TESTING` makes the app sign its cookies with an ephemeral key
(`clude_web.config.secret_key`).

The gate is the whole security boundary of 8.1b: the Cloud Run service
is reachable by anyone, and the app login is what stands in front of it
(`docs/phase8.1-plan.md` 3.6). So "every route but login redirects" is
the test that matters most here, and it is written to cover routes that
do not exist yet.
"""
from __future__ import annotations

import pytest

from clude_storage import open_store
from clude_web import create_app, users
from clude_web.auth import RateLimit

NAME = "David"
PASSWORD = "a-good-enough-password"


@pytest.fixture
def store(tmp_path):
    return open_store(str(tmp_path))


@pytest.fixture
def app(tmp_path, store):
    users.add_user(store, NAME, PASSWORD)
    return create_app({"TESTING": True, "STORE_URI": str(tmp_path)})


@pytest.fixture
def client(app):
    return app.test_client()


def sign_in(client, name=NAME, password=PASSWORD):
    """POST the login form with the CSRF token the page hands out."""
    token = csrf_from(client)
    return client.post(
        "/login", data={"name": name, "password": password, "csrf": token}
    )


def csrf_from(client) -> str:
    """Pull this client's CSRF token out of a rendered form.

    The login page carries one before signing in; afterwards that page
    redirects away, so the sign-out form in the header carries it
    instead.
    """
    marker = 'name="csrf" value="'
    for path in ("/login", "/"):
        response = client.get(path)
        if response.status_code != 200:
            continue
        page = response.get_data(as_text=True)
        if marker in page:
            start = page.index(marker) + len(marker)
            return page[start : page.index('"', start)]
    raise AssertionError("no CSRF token on either the login page or the index")


# --- accounts ---------------------------------------------------------


def test_add_user_stores_a_hash_and_never_the_password(store):
    document = users.add_user(store, "Ada", PASSWORD)

    assert PASSWORD not in str(document)
    assert document["password_hash"] != PASSWORD
    assert document["name"] == "Ada"
    raw = store.get_doc("users/ada.json")
    assert PASSWORD not in str(raw)


def test_a_name_is_matched_whatever_its_case_but_shown_as_typed(store):
    users.add_user(store, "David", PASSWORD)

    assert users.authenticate(store, "david", PASSWORD)["name"] == "David"
    assert users.authenticate(store, "DAVID", PASSWORD)["name"] == "David"


def test_authenticate_refuses_a_wrong_password_and_a_missing_account(store):
    users.add_user(store, NAME, PASSWORD)

    assert users.authenticate(store, NAME, "wrong") is None
    assert users.authenticate(store, "nobody", PASSWORD) is None
    assert users.authenticate(store, "../escape", PASSWORD) is None


def test_a_name_cannot_escape_its_folder(store):
    for bad in ["../outside", "with/slash", "", "  ", "-leading"]:
        with pytest.raises(ValueError):
            users.add_user(store, bad, PASSWORD)


def test_a_short_password_is_refused_and_a_name_is_not_taken_twice(store):
    with pytest.raises(ValueError, match="at least"):
        users.add_user(store, "Ada", "short")
    users.add_user(store, "Ada", PASSWORD)
    with pytest.raises(ValueError, match="already exists"):
        users.add_user(store, "ADA", PASSWORD)


def test_list_and_remove(store):
    users.add_user(store, "Ada", PASSWORD)
    users.add_user(store, "Grace", PASSWORD)

    assert sorted(u["name"] for u in users.list_users(store)) == ["Ada", "Grace"]
    assert users.remove_user(store, "ada") is True
    assert users.remove_user(store, "ada") is False
    assert [u["name"] for u in users.list_users(store)] == ["Grace"]


def test_set_password_replaces_the_hash(store):
    users.add_user(store, NAME, PASSWORD)
    users.set_password(store, NAME, "another-good-password")

    assert users.authenticate(store, NAME, PASSWORD) is None
    assert users.authenticate(store, NAME, "another-good-password") is not None


# --- the gate ---------------------------------------------------------


def test_every_route_but_login_redirects_without_a_session(app, client):
    """Written over the app's whole url map, so a route added in steps 3
    to 5 is covered the day it appears."""
    checked = 0
    for rule in app.url_map.iter_rules():
        if rule.endpoint in {"static", "auth.login"} or "GET" not in rule.methods:
            continue
        response = client.get(rule.rule)
        assert response.status_code == 302, f"{rule.rule} was reachable"
        assert "/login" in response.headers["Location"]
        checked += 1
    assert checked, "no private routes were checked"


def test_the_login_page_itself_is_reachable(client):
    assert client.get("/login").status_code == 200


def test_a_wrong_password_does_not_sign_anyone_in(client):
    response = sign_in(client, password="not-the-password")

    assert response.status_code == 401
    assert client.get("/").status_code == 302


def test_a_wrong_name_and_a_wrong_password_look_the_same(client):
    wrong_name = sign_in(client, name="nobody").get_data(as_text=True)
    wrong_password = sign_in(client, password="nope").get_data(as_text=True)

    assert "Wrong name or password." in wrong_name
    assert wrong_name == wrong_password


def test_a_good_password_signs_in_and_opens_the_app(client):
    response = sign_in(client)

    assert response.status_code == 302
    page = client.get("/")
    assert page.status_code == 200
    assert NAME in page.get_data(as_text=True)


def test_signing_out_closes_the_app_again(client):
    sign_in(client)
    token = csrf_from(client)

    assert client.post("/logout", data={"csrf": token}).status_code == 302
    assert client.get("/").status_code == 302


def test_a_post_without_the_csrf_token_is_refused(client):
    response = client.post("/login", data={"name": NAME, "password": PASSWORD})

    assert response.status_code == 400
    assert client.get("/").status_code == 302


def test_a_post_with_another_sessions_csrf_token_is_refused(app, client):
    stolen = csrf_from(app.test_client())
    client.get("/login")  # this client now has a token of its own

    response = client.post(
        "/login", data={"name": NAME, "password": PASSWORD, "csrf": stolen}
    )

    assert response.status_code == 400


def test_the_csrf_token_changes_when_someone_signs_in(client):
    before = csrf_from(client)
    sign_in(client)

    assert csrf_from(client) != before


def test_repeated_wrong_passwords_are_rate_limited(client):
    codes = [sign_in(client, password="nope").status_code for _ in range(7)]

    assert 429 in codes, "guessing was never slowed down"
    assert codes.index(429) >= 5, "a handful of attempts should be allowed"


def test_the_rate_limit_forgets_after_its_window():
    limiter = RateLimit(limit=2, window=60.0)

    assert limiter.check("ada", now=0.0)
    assert limiter.check("ada", now=1.0)
    assert not limiter.check("ada", now=2.0)
    assert limiter.check("ada", now=100.0), "the window should have passed"
    assert limiter.check("grace", now=2.0), "one name must not block another"


def test_the_rate_limit_is_cleared_by_a_successful_login():
    limiter = RateLimit(limit=2, window=60.0)
    limiter.check("ada", now=0.0)
    limiter.check("ada", now=1.0)

    limiter.clear("ada")

    assert limiter.check("ada", now=2.0), "a good password should reset the count"


def test_a_good_password_still_works_after_a_few_wrong_ones(client):
    """Mistyping a password three times must not lock the account out."""
    for _ in range(3):
        assert sign_in(client, password="nope").status_code == 401

    assert sign_in(client).status_code == 302


# --- the factory ------------------------------------------------------


def test_the_session_cookie_is_locked_down(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_the_secure_cookie_flag_follows_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("CLUDE_WEB_HTTPS", "1")
    secure = create_app({"TESTING": True, "STORE_URI": str(tmp_path)})
    monkeypatch.setenv("CLUDE_WEB_HTTPS", "0")
    plain = create_app({"TESTING": True, "STORE_URI": str(tmp_path)})

    assert secure.config["SESSION_COOKIE_SECURE"] is True
    assert plain.config["SESSION_COOKIE_SECURE"] is False


def test_a_missing_secret_is_an_error_outside_testing(tmp_path, monkeypatch):
    """Falling back to a generated key would log everyone out on every
    restart and hide the mistake, so it is refused."""
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.setattr("clude_web.config.read_env_file", lambda *a, **k: None)

    with pytest.raises(RuntimeError, match="FLASK_SECRET_KEY"):
        create_app({"STORE_URI": str(tmp_path)})


def test_the_app_reads_the_store_it_was_given(app, tmp_path):
    assert app.extensions["store"].describe() == str(tmp_path)


def test_the_users_cli_writes_where_the_app_reads():
    """`clude_cli.py users` defaults to the web app's store, not the
    CLI's, or an account would land where the app never looks. The
    constant is duplicated so the CLI runs without Flask, so pin it."""
    import importlib.util
    import sys
    from pathlib import Path

    from clude_web import config as web_config

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "clude_cli_for_test", root / "scripts" / "clude_cli.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert module.WEB_STORE == web_config.DEFAULT_STORE
