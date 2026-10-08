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

import json

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
    """An app whose one account has settled its password already, so the
    one-time offer is out of the way. The offer has its own tests."""
    users.add_user(store, NAME, PASSWORD)
    users.mark_password_prompted(store, NAME)
    return create_app({"TESTING": True, "STORE_URI": str(tmp_path)})


@pytest.fixture
def fresh_app(tmp_path, store):
    """An app whose one account has never been offered the change: what
    a player meets on their very first login."""
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
    instead. While the one-time password offer is pending, everything
    else redirects to it, so it is where the token is.
    """
    marker = 'name="csrf" value="'
    for path in ("/login", "/password", "/"):
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


def test_a_persons_name_is_shown_capitalised_and_a_bots_as_it_is():
    """Phase 9j: a lower-case key reads as a slip, so a person's name is
    capitalised wherever it is shown; the key itself never changes, and
    a bot's label is left alone."""
    assert users.display_name("zenbot") == "Zenbot"
    assert users.display_name("mary-jo") == "Mary-Jo"
    assert users.display_name("j.r_ewing") == "J.R_Ewing"
    assert users.display_name("DeeDee") == "DeeDee"
    assert users.display_name("7of9") == "7of9"
    for bot in ("floor", "random", "Plum", "envelope"):
        assert users.display_name(bot) == bot
    assert users.display_name(None) is None and users.display_name("") == ""


def test_authenticate_refuses_a_wrong_password_and_a_missing_account(store):
    users.add_user(store, NAME, PASSWORD)

    assert users.authenticate(store, NAME, "wrong") is None
    assert users.authenticate(store, "nobody", PASSWORD) is None
    assert users.authenticate(store, "../escape", PASSWORD) is None


def test_a_name_cannot_escape_its_folder(store):
    for bad in ["../outside", "with/slash", "", "  ", "-leading"]:
        with pytest.raises(ValueError):
            users.add_user(store, bad, PASSWORD)


def test_any_non_empty_password_is_accepted(store):
    """Convenience over secrecy, on purpose (CLAUDE.md). One character
    is fine; empty is not, since it would make the form's own `required`
    the only thing in the way."""
    users.add_user(store, "Ada", "x")
    assert users.authenticate(store, "Ada", "x") is not None

    with pytest.raises(ValueError, match="cannot be empty"):
        users.add_user(store, "Grace", "")


def test_a_new_account_gets_the_default_password(store):
    users.add_user(store, "Ada")

    assert users.authenticate(store, "Ada", users.DEFAULT_PASSWORD) is not None
    assert users.DEFAULT_PASSWORD == "password"


def test_a_name_is_not_taken_twice(store):
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


PUBLIC = {"static", "auth.login", "main.privacy", "main.wiki", "main.wiki_page"}
"""The routes anyone may load: the login, the privacy page (D12) and
Wikiclude (David, 2026-10-01), which shows no game's state."""


def test_every_route_but_login_and_privacy_redirects_without_a_session(app, client):
    """Written over the app's whole url map, so a route added in steps 3
    to 5 is covered the day it appears. Wikiclude joined the public
    routes on 2026-10-01 (`tests/test_wiki.py` has its own)."""
    checked = 0
    for rule in app.url_map.iter_rules():
        if rule.endpoint in PUBLIC or "GET" not in rule.methods:
            continue
        response = client.get(rule.rule)
        assert response.status_code == 302, f"{rule.rule} was reachable"
        assert "/login" in response.headers["Location"]
        checked += 1
    assert checked, "no private routes were checked"


def test_every_page_wears_the_account_s_look_and_the_bar_can_change_it(app, store, client):
    """Phase 9h. The chosen style is linked on every page and named on
    the html element; the header bar's form changes it for the account
    and sends the player back where they were; a bad key or a foreign
    `next` is refused. Three looks since 2026-09-29 (D17)."""
    from clude_web import styles, users

    # Case-file light is the default, its theme fixed on the html element.
    sign_in(client)
    page = client.get("/").get_data(as_text=True)
    assert 'data-style="casefile"' in page and 'data-theme="light"' in page and "styles/engraved.css" in page
    assert 'action="/style"' in page and '<option value="casefile" selected>Case-file light</option>' in page
    picker = page.split('<select id="style"')[1].split("</select>")[0]
    assert picker.count("<option value=") == 3
    assert "Engraved" not in picker and "Legacy" not in picker
    assert users.style_of(users.get_user(store, NAME)) == "casefile"
    assert users.chosen_style(users.get_user(store, NAME)) is None
    assert styles.style_named("no-such-look").key == styles.DEFAULT_STYLE == "casefile"
    assert client.get("/static/styles/engraved.css").status_code == 200
    assert client.get("/static/fonts/inter-normal-400-700.woff2").status_code == 200

    token = csrf_from(client)
    bad = client.post("/style", data={"csrf": token, "style": "brass", "next": "/"})
    assert bad.status_code == 400 and "style" not in users.get_user(store, NAME)
    old = client.post("/style", data={"csrf": token, "style": "legacy", "next": "/"})
    assert old.status_code == 400, "only the current keys are offered"

    ok = client.post("/style", data={"csrf": token, "style": "developer", "next": "/replay/web-test/0?x=1"})
    assert ok.status_code == 302 and ok.headers["Location"].endswith("/replay/web-test/0?x=1")
    assert users.get_user(store, NAME)["style"] == "developer"
    assert users.chosen_style(users.get_user(store, NAME)) == "developer", "chosen from the bar, it sticks"
    with client.session_transaction() as session:
        assert session["look"] == "developer"
    page = client.get("/").get_data(as_text=True)
    assert 'data-style="developer"' in page and "styles/legacy.css" in page and "data-theme=" not in page

    away = client.post("/style", data={"csrf": token, "style": "developer", "next": "https://example.com/"})
    assert away.status_code == 302 and away.headers["Location"].endswith("/")
    assert "example.com" not in away.headers["Location"]

    client.post("/style", data={"csrf": token, "style": "gaslight", "next": "/"})
    themed = client.get("/").get_data(as_text=True)
    assert 'data-style="gaslight"' in themed and 'data-theme="dark"' in themed
    assert "styles/engraved.css" in themed and "Gaslight dark" in themed

    # An account made before there was a choice, one whose stored key
    # has gone from the list, and one that version 3 gave `legacy`
    # without asking all read as the default.
    document = users.get_user(store, NAME)
    del document["style"]
    store.put_doc(users.user_key(NAME), document)
    assert users.style_of(users.get_user(store, NAME)) == "casefile"
    document["style"] = "gone"
    store.put_doc(users.user_key(NAME), document)
    assert users.style_of(users.get_user(store, NAME)) == "casefile"
    document["style"], document["version"] = "legacy", 3
    document.pop("style_chosen", None)
    store.put_doc(users.user_key(NAME), document)
    assert users.style_of(users.get_user(store, NAME)) == "casefile"
    # The old keys, chosen: Legacy is Developer, Engraved Gaslight dark.
    document["style_chosen"] = True
    store.put_doc(users.user_key(NAME), document)
    assert users.chosen_style(users.get_user(store, NAME)) == "developer"
    document["style"] = "engraved"
    store.put_doc(users.user_key(NAME), document)
    assert users.chosen_style(users.get_user(store, NAME)) == "gaslight"
    with client.session_transaction() as session:
        session["look"] = "legacy"  # a session from before the rename
    assert 'data-style="developer"' in client.get("/").get_data(as_text=True)
    with pytest.raises(ValueError):
        users.set_style(store, NAME, "gone")

    # Signed out, the login page still has a look, and no picker.
    out = app.test_client().get("/login").get_data(as_text=True)
    assert "styles/engraved.css" in out and 'action="/style"' not in out


def test_the_sound_cues_are_served_short_and_start_muted(client):
    """Phase 10g (plan 11.1). Six self-hosted cues (the door and the
    passage since 2026-10-01), each a short mono
    WAV; the shared player is served and remembers an off-by-default
    preference; the lobby has no sound control, since nothing there
    makes a sound. No music: nothing runs longer than a second and a half."""
    import io
    import wave

    sign_in(client)
    for name in ("tick", "turn", "refute", "accent", "door", "passage"):
        response = client.get(f"/static/sounds/{name}.wav")
        assert response.status_code == 200, name
        with wave.open(io.BytesIO(response.get_data())) as clip:
            assert (clip.getnchannels(), clip.getsampwidth(), clip.getframerate()) == (1, 2, 22050)
            assert 0.05 <= clip.getnframes() / clip.getframerate() <= 1.5, name
    script = client.get("/static/sound.js").get_data(as_text=True)
    assert 'read(KEY_ON) === "1"' in script, "sound is off until the viewer turns it on"
    for name in ("tick", "turn", "refute", "accent", "door", "passage"):
        assert f'"{name}"' in script
    assert 'id="sound-toggle"' not in client.get("/").get_data(as_text=True)


def test_the_header_bar_wears_the_keyhole_under_engraved_only(client):
    """Phase 10f (D5, E). An Engraved look puts the keyhole mark beside
    the wordmark; Developer keeps Legacy's plain word. Every look links
    the favicon, which is served."""
    sign_in(client)
    engraved = client.get("/").get_data(as_text=True)
    bar = engraved.split('<header class="bar">')[1].split("</header>")[0]
    assert '<svg class="logo"' in bar and "<span>clude</span>" in bar
    assert 'rel="icon"' in engraved
    assert client.get("/static/favicon.svg").status_code == 200
    token = csrf_from(client)
    client.post("/style", data={"csrf": token, "style": "developer", "next": "/"})
    legacy = client.get("/").get_data(as_text=True)
    bar = legacy.split('<header class="bar">')[1].split("</header>")[0]
    assert '<svg class="logo"' not in bar and ">clude</a>" in bar
    assert 'rel="icon"' in legacy


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


# --- the one-time password offer --------------------------------------


def test_a_first_login_is_met_by_the_offer(fresh_app):
    client = fresh_app.test_client()
    sign_in(client)

    landing = client.get("/", follow_redirects=True)
    assert "Want a different password?" in landing.get_data(as_text=True)


def test_keeping_the_password_answers_the_offer_for_good(fresh_app, store):
    client = fresh_app.test_client()
    sign_in(client)
    token = csrf_from(client)

    client.post("/password", data={"action": "keep", "csrf": token})

    assert client.get("/").status_code == 200, "the app should be open now"
    assert users.authenticate(store, NAME, PASSWORD) is not None
    assert users.needs_password_offer(users.get_user(store, NAME)) is False


def test_changing_the_password_answers_the_offer_and_takes_effect(fresh_app, store):
    client = fresh_app.test_client()
    sign_in(client)
    token = csrf_from(client)

    client.post(
        "/password", data={"action": "change", "password": "x", "csrf": token}
    )

    assert client.get("/").status_code == 200
    assert users.authenticate(store, NAME, "x") is not None
    assert users.authenticate(store, NAME, PASSWORD) is None
    assert users.needs_password_offer(users.get_user(store, NAME)) is False


def test_the_offer_is_never_made_a_second_time(fresh_app):
    client = fresh_app.test_client()
    sign_in(client)
    client.post("/password", data={"action": "keep", "csrf": csrf_from(client)})

    page = client.get("/password").get_data(as_text=True)
    assert "Want a different password?" not in page
    assert "Ask David" in page

    signed_in_again = fresh_app.test_client()
    sign_in(signed_in_again)
    assert signed_in_again.get("/").status_code == 200, "asked again on a later login"


def test_choosing_to_change_but_typing_nothing_is_refused(fresh_app):
    client = fresh_app.test_client()
    sign_in(client)

    response = client.post(
        "/password", data={"action": "change", "password": "", "csrf": csrf_from(client)}
    )

    assert response.status_code == 400
    assert "Type a password" in response.get_data(as_text=True)


def test_a_settled_account_goes_straight_in(client):
    sign_in(client)

    assert client.get("/").status_code == 200


def test_the_offer_still_needs_a_session(fresh_app):
    assert fresh_app.test_client().get("/password").status_code == 302


# --- the replay screen ------------------------------------------------


def stored_game(store, run_id="web-test", index=0):
    """Play a short real game into `store`, as the arena would."""
    import clude_constraints
    from clude_constraints import FloorBot
    from clude_core import engine
    from clude_storage import GameRecord, SeatRecord

    n = 3
    state, events = engine.run_game(
        n, {p: FloorBot() for p in range(n)}, seed=5, max_turns=40,
        observer=clude_constraints.observe,
    )
    record = GameRecord.from_game(
        run_id=run_id, game_index=index, seed=5, state=state, events=events,
        seats=[
            SeatRecord(seat=p, suspect=state.suspects_in_play[p], label="floor", kind="floor")
            for p in range(n)
        ],
    )
    store.put_game(run_id, index, record.to_dict())
    store.put_run(run_id, {"n_games": 1, "seed": 5, "roster": ["floor"], "per_player": {}})
    return record


def test_a_replay_renders_its_board_seats_and_scrubber(app, store, client):
    stored_game(store)
    sign_in(client)

    page = client.get("/replay/web-test/0")
    text = page.get_data(as_text=True)

    assert page.status_code == 200
    assert text.count('class="board-room"') == 9
    assert text.count('class="seat"') == 3
    assert 'id="scrub"' in text
    assert 'id="play"' in text and 'id="speed"' in text, "Play and the speed slider (Phase 9h)"
    assert "replay.js" in text


def test_a_replay_needs_a_session(app, store):
    stored_game(store)

    response = app.test_client().get("/replay/web-test/0")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_a_missing_game_is_a_404_not_a_crash(client):
    sign_in(client)

    assert client.get("/replay/nope/0").status_code == 404
    assert client.get("/replay/web-test/99").status_code == 404


def test_the_replay_payload_is_valid_json_with_a_frame_per_event(app, store, client):
    record = stored_game(store)
    sign_in(client)
    text = client.get("/replay/web-test/0").get_data(as_text=True)

    raw = text.split('id="replay-data" type="application/json">')[1].split("</script>")[0]
    payload = json.loads(raw)

    assert len(payload["frames"]) == len(record.events)
    assert payload["envelope"] == list(record.envelope)
    assert all("tokens" in frame for frame in payload["frames"])


def test_the_payload_cannot_close_the_script_tag(app, store, client):
    """Table talk is written by a model, so it is text from outside the
    app. A `</script>` in a remark must not break out of the block."""
    from clude_core.events import RemarkEvent
    from clude_storage import GameRecord

    record = stored_game(store)
    hostile = "</script><script>window.pwned=1</script>"
    record.events.insert(1, RemarkEvent(turn=1, seat=0, text=hostile, about="move"))
    store.put_game("web-test", 0, record.to_dict())
    store.delete_doc("traces/web-test/00000.json")
    sign_in(client)

    text = client.get("/replay/web-test/0").get_data(as_text=True)

    assert "window.pwned" not in text or "\\u003c" in text
    raw = text.split('id="replay-data" type="application/json">')[1].split("</script>")[0]
    payload = json.loads(raw)  # the block is still one whole JSON document
    assert any(hostile in frame["text"] for frame in payload["frames"])
    del GameRecord


def test_the_lobby_leads_to_a_stored_replay(app, store, client):
    """Lobby -> the run -> the game: the lobby lists runs, and a run's
    page lists its games as replay links."""
    record = stored_game(store)
    summary = store.get_run("web-test")
    summary["games"] = [
        {
            "game_index": 0, "seed": 5, "n_players": record.n_players,
            "labels": ["floor"] * record.n_players, "winner_label": None,
            "turns": record.turns, "n_suggestions": record.n_suggestions,
            "n_accusations": record.n_accusations, "hit_cap": False,
        }
    ]
    store.put_run("web-test", summary)
    sign_in(client)

    lobby = client.get("/").get_data(as_text=True)
    development = client.get("/development/1").get_data(as_text=True)
    run_page = client.get("/runs/web-test").get_data(as_text=True)

    # Practice in two sets, development in two phases (2026-10-07):
    # every run but practice is under development, by its phase.
    for href, name in (("/runs/web", "practice set one"), ("/runs/web-2", "practice set two"),
                       ("/development/1", "development phase one"), ("/development/2", "development phase two")):
        assert f'href="{href}">{name}</a>' in lobby
    assert "/runs/web-test" not in lobby
    assert "/runs/web-test" in development
    assert "/runs/web-test" not in client.get("/development/2").get_data(as_text=True)
    assert client.get("/development").headers["Location"].endswith("/development/1")
    assert client.get("/development/3").status_code == 404
    assert "/replay/web-test/0" in run_page
    assert 'href="/development/1">development phase one</a>' in run_page

    summary["phase"] = 2
    store.put_run("web-test", summary)
    assert "/runs/web-test" in client.get("/development/2").get_data(as_text=True)
    assert 'href="/development/2">development phase two</a>' in client.get("/runs/web-test").get_data(as_text=True)


def test_the_games_table_has_wall_time_and_shows_cost_to_the_developer_only(app, store, client):
    """David's columns (2026-09-29): Game, Seats, Winner, Turns,
    Suggestions, Wall time, and Cost only in the Developer look. Wall
    time is blank for a game stored before it was recorded."""
    from clude_web import views

    record = stored_game(store)
    line = {
        "seed": 5, "n_players": record.n_players, "labels": ["floor"] * record.n_players,
        "winner_label": None, "turns": record.turns, "n_suggestions": record.n_suggestions,
        "n_accusations": record.n_accusations, "hit_cap": False, "cost": 0.4321,
    }
    summary = store.get_run("web-test")
    summary["games"] = [{"game_index": 0, **line, "wall_seconds": 1234.5}, {"game_index": 1, **line}]
    store.put_run("web-test", summary)
    sign_in(client)

    page = client.get("/runs/web-test").get_data(as_text=True)
    head = page.split("<thead>")[1].split("</thead>")[0]
    assert [cell.split("</th>")[0] for cell in head.split("<th>")[1:]] == [
        "Game", "Seats", "Winner", "Turns", "Suggestions", "Wall time",
    ]
    walls = [cell.split("</td>")[0] for cell in page.split('<td class="wall">')[1:]]
    assert walls == ["21 min", ""]
    assert "$0.43" not in page

    client.post("/style", data={"csrf": csrf_from(client), "style": "developer", "next": "/"})
    page = client.get("/runs/web-test").get_data(as_text=True)
    assert "<th>Wall time</th><th>Cost</th>" in page and "$0.43" in page

    assert [views.wall_time(s) for s in (None, 42, 59.4, 61, 3569, 3600, 3900)] == [
        "", "42 s", "59 s", "1 min", "59 min", "1 h 00 min", "1 h 05 min",
    ]


def test_the_footer_links_privacy_contact_and_wikiclude_on_every_page(app, client):
    """2026-09-29. The footer is on every page, signed in or not; the
    privacy page is public (D12), and so since 2026-10-01 is Wikiclude,
    which the header bar's wooden question mark leads to."""
    anonymous = app.test_client()
    login = anonymous.get("/login").get_data(as_text=True)
    foot = login.split('<footer class="foot">')[1].split("</footer>")[0]
    assert 'href="/privacy"' in foot and 'href="/wiki"' in foot
    assert "github.com/davidabelin/clude/issues" in foot and "2026 AIX Protodyne" in foot
    privacy = anonymous.get("/privacy")
    assert privacy.status_code == 200 and "Anthropic" in privacy.get_data(as_text=True)
    assert anonymous.get("/wiki").status_code == 200
    for path in ("/static/copyleft.svg", "/static/questionmark-wood.png", "/static/styles/chrome.css"):
        assert anonymous.get(path).status_code == 200, path

    sign_in(client)
    lobby = client.get("/").get_data(as_text=True)
    bar = lobby.split('<header class="bar">')[1].split("</header>")[0]
    assert '<a class="wiki-button" href="/wiki"' in bar and "questionmark-wood.png" in bar
    assert "Wikiclude" in client.get("/wiki").get_data(as_text=True)


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
