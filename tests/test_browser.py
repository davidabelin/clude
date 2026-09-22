"""The replay screen in a real browser.

Everything else in the suite tests markup and data. These tests drive
Chromium, which is the only thing that applies `style.css`, runs
`replay.js` and can say where a token actually ended up on screen --
`board_svg` sets no colour at all, so an SVG rasteriser would render a
blank and prove nothing.

Skipped unless ``CLUDE_WEB_BROWSER=1`` and Playwright is installed, in
the same way `CLUDE_LLM_LIVE` and `CLUDE_GCS_LIVE` gate the tests that
need credentials: the default suite stays fast and needs no browser.

    python -m pip install playwright
    python -m playwright install chromium
    $env:CLUDE_WEB_BROWSER = "1"; python -m pytest -q tests/test_browser.py
"""
from __future__ import annotations

import json
import os
import socket
import threading
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest

import clude_constraints
from clude_constraints import FloorBot
from clude_core import engine
from clude_llm import NullBackend
from clude_storage import GameRecord, SeatRecord, open_store
from clude_web import create_app, users

pytestmark = pytest.mark.skipif(
    os.environ.get("CLUDE_WEB_BROWSER") != "1",
    reason="set CLUDE_WEB_BROWSER=1 (and install playwright) to run browser tests",
)

NAME = "browser"
PASSWORD = "browser-password"
RUN = "browser-test"


class _Quiet(WSGIRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def served(tmp_path_factory):
    """The app on a spare port, with one real game and one account."""
    root = tmp_path_factory.mktemp("browser-store")
    store = open_store(str(root))

    n = 4
    state, events = engine.run_game(
        n, {p: FloorBot() for p in range(n)}, seed=11, max_turns=60,
        observer=clude_constraints.observe,
    )
    record = GameRecord.from_game(
        run_id=RUN, game_index=0, seed=11, state=state, events=events,
        seats=[
            SeatRecord(seat=p, suspect=state.suspects_in_play[p], label="floor", kind="floor")
            for p in range(n)
        ],
    )
    store.put_game(RUN, 0, record.to_dict())
    store.put_run(RUN, {"n_games": 1, "seed": 11, "roster": ["floor"], "per_player": {}})
    users.add_user(store, NAME, PASSWORD)
    users.mark_password_prompted(store, NAME)

    app = create_app({
        "STORE_URI": str(root), "SECRET_KEY": "browser-tests",
        "LLM_KEY": "browser-tests", "LLM_BACKEND": lambda model, key: NullBackend(),
    })
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = make_server("127.0.0.1", port, app, handler_class=_Quiet)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}", record
    server.shutdown()


@pytest.fixture
def page(served):
    """A signed-in page on the replay screen, with console errors
    collected so a broken script fails the test rather than passing
    quietly."""
    playwright = pytest.importorskip("playwright.sync_api")
    base, _record = served
    problems = []
    with playwright.sync_playwright() as play:
        browser = play.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.on(
            "console",
            lambda m: problems.append(m.text) if m.type == "error" else None,
        )
        page.on("pageerror", lambda e: problems.append(str(e)))

        page.goto(f"{base}/login")
        page.fill("#name", NAME)
        page.fill("#password", PASSWORD)
        page.click("button[type=submit]")
        page.wait_for_url(f"{base}/")
        page.goto(f"{base}/replay/{RUN}/0")
        page.wait_for_selector(".board-token")

        page.problems = problems
        page.base = base
        yield page

        browser.close()
    assert not problems, f"the page logged errors: {problems}"


def drawn_tokens(page) -> dict:
    """Suspect -> where its circle actually sits, read off the document."""
    return page.evaluate(
        """() => {
            const out = {};
            document.querySelectorAll('.board-token').forEach(c => {
                out[c.getAttribute('data-suspect')] =
                    [Number(c.getAttribute('cx')), Number(c.getAttribute('cy'))];
            });
            return out;
        }"""
    )


def payload(page) -> dict:
    return json.loads(page.inner_text("#replay-data"))


def scrub_to(page, index):
    page.evaluate(
        """(v) => {
            const el = document.getElementById('scrub');
            el.value = v;
            el.dispatchEvent(new Event('input'));
        }""",
        index,
    )


def test_the_screen_renders_with_no_script_errors(page):
    assert page.is_visible(".board")
    assert page.is_visible("#scrub")
    assert len(page.query_selector_all(".seat")) == 4


def test_every_token_lands_where_the_payload_says(page):
    """The check that matters: the picture and the data agreeing. These
    are read back off the rendered document, not from the markup the
    server sent."""
    data = payload(page)
    for index in (0, len(data["frames"]) // 3, len(data["frames"]) - 1):
        scrub_to(page, index)
        expected = data["frames"][index]["tokens"]
        for suspect, point in drawn_tokens(page).items():
            assert point == pytest.approx(expected[suspect], abs=0.01), (
                f"{suspect} was drawn in the wrong place at step {index}"
            )


def test_tokens_in_one_room_never_stack(page):
    """They did once: the drawing fanned them out and the payload did
    not, so two characters in a room sat exactly on top of each other as
    soon as the page went live."""
    data = payload(page)
    stacked = []
    for index, frame in enumerate(data["frames"]):
        points = [tuple(p) for p in frame["tokens"].values()]
        if len(set(points)) != len(points):
            stacked.append(index)
    assert not stacked, f"tokens shared a point at steps {stacked[:5]}"


def test_the_scrubber_moves_the_tokens(page):
    scrub_to(page, 0)
    start = drawn_tokens(page)
    scrub_to(page, len(payload(page)["frames"]) - 1)
    end = drawn_tokens(page)

    assert start != end, "the board never changed"


def test_the_arrow_keys_step_the_game(page):
    scrub_to(page, 5)
    before = page.inner_text("#counter")
    page.keyboard.press("ArrowRight")
    after = page.inner_text("#counter")
    page.keyboard.press("ArrowLeft")
    back = page.inner_text("#counter")

    assert before != after
    assert back == before


def test_home_and_end_reach_both_ends(page):
    total = len(payload(page)["frames"])
    page.keyboard.press("End")
    assert page.inner_text("#counter").startswith(str(total))
    page.keyboard.press("Home")
    assert page.inner_text("#counter").startswith("1 ")


def test_the_step_line_follows_the_scrubber(page):
    data = payload(page)
    for index in (0, 7, len(data["frames"]) - 1):
        scrub_to(page, index)
        assert page.inner_text("#step-line") == data["frames"][index]["text"]


def test_a_proven_envelope_card_is_drawn_solid(page):
    """By the end of a finished game a seat has usually proven the
    envelope; that row must be the full, solid one."""
    data = payload(page)
    scrub_to(page, len(data["frames"]) - 1)

    rows = page.evaluate(
        """() => {
            const out = [];
            document.querySelectorAll('.seat .row').forEach(r => {
                out.push({
                    card: r.getAttribute('data-card'),
                    cls: r.className,
                    width: r.querySelector('.fill').style.width
                });
            });
            return out;
        }"""
    )
    solved = [r for r in rows if "proven-envelope" in r["cls"]]
    assert solved, "nobody had proven an envelope card by the end"
    for row in solved:
        assert row["card"] in data["envelope"]
        assert row["width"] == "100%"


def test_every_suspect_pip_is_coloured(page):
    """The `.suspect-*` rules colour the board with `fill`, an SVG
    property an HTML span ignores, so every pip rendered transparent --
    and a markup test could not tell, because the class *had* a rule."""
    colours = page.evaluate(
        """() => Array.from(document.querySelectorAll('.pip')).map(
            p => getComputedStyle(p).backgroundColor)"""
    )
    assert colours, "no pips on the page"
    for colour in colours:
        assert colour not in ("rgba(0, 0, 0, 0)", "transparent"), "a pip is invisible"
    assert len(set(colours)) == len(colours), "two seats share a colour"


def test_a_watched_game_deals_steps_and_ends_in_a_replay(page):
    """The whole Watch loop in a browser: deal from the lobby, step, and
    play to the end, which must land on the finished game's replay."""
    base = page.base
    page.goto(f"{base}/")
    for name in ("Scarlett", "Mustard", "White"):
        page.check(f"input[name=characters][value={name}]")
    page.select_option("#n_players", "4")
    page.fill("#seed", "7")
    page.click("form[action$='/watch'] button[type=submit]")
    page.wait_for_selector("#next-turn")
    assert page.inner_text("h1") == "Turn 0"

    for expected in (1, 2, 3):
        page.click("#next-turn")
        page.wait_for_selector("#next-turn")
        assert page.inner_text("h1") == f"Turn {expected}"
        assert " showed " not in page.content(), "a shown card leaked onto the watch screen"

    page.click("#play-to-end")
    page.wait_for_selector("#scrub")
    assert "/replay/web/" in page.url
    data = payload(page)
    assert data["frames"][-1]["kind"] == "over"


def test_the_board_is_actually_painted(page):
    """`board_svg` sets no colour, so if the stylesheet ever stopped
    reaching it every shape would render transparent and this whole
    screen would be blank -- while every markup test still passed."""
    fills = page.evaluate(
        """() => {
            const pick = s => {
                const el = document.querySelector(s);
                return el ? getComputedStyle(el).fill : null;
            };
            return {
                room: pick('.board-room rect'),
                corridor: pick('.board-corridor rect'),
                token: pick('.board-token')
            };
        }"""
    )
    for what, colour in fills.items():
        assert colour and colour not in ("none", "rgba(0, 0, 0, 0)"), f"{what} unpainted"
    assert fills["room"] != fills["corridor"], "the corridor is invisible against the rooms"

# --- a table with a person at it (Phase 8.2) --------------------------------


def test_lobby_seat_modes_and_memory_dial(page):
    """Seat choices are explicit; opting out hides the LLM memory dial."""
    page.goto(f"{page.base}/")
    assert page.locator("#remember").is_checked()
    assert page.locator("#watch-remember").is_checked()
    assert not page.locator('.seat-pick:has(#seat-Scarlett) .method').is_visible()
    assert page.locator("#seat-Plum option").all_text_contents() == [
        "empty", "open", "floorbot", "me (browser)", "Plum (LLM)", "Plum (headless)",
    ]
    assert not page.locator("#memory-Plum").is_visible()
    page.select_option("#seat-Plum", "llm")
    assert page.locator("#memory-Plum").is_visible()
    page.locator("#memory-Plum").fill("0.75")
    assert page.locator('output[for="memory-Plum"]').inner_text() == "0.75"
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.uncheck("#remember")
    assert not page.locator("#memory-Plum").is_visible()
    page.check("#remember")
    assert page.locator("#memory-Plum").input_value() == "0.75"
    page.select_option("#seat-Plum", "character")
    assert not page.locator("#memory-Plum").is_visible()
    assert page.locator('.seat-pick:has(#seat-Plum) .method').is_visible()


def _deal_table(page, seats: dict, seed="7"):
    base = page.base
    page.goto(f"{base}/")
    for token, value in seats.items():
        page.select_option(f"#seat-{token}", value)
    page.fill("#table-seed", seed)
    page.click("#table-form button[type=submit]")


def test_a_table_shows_the_move_on_the_board_and_as_buttons(page):
    """The legal destinations of the person's move are drawn on the board
    at the server's coordinates and listed as buttons, one for one."""
    _deal_table(page, {"Scarlett": "me", "Mustard": "character", "White": "character",
                       "Green": "empty", "Peacock": "empty", "Plum": "empty"})
    page.wait_for_selector(".decision .options button", timeout=20000)
    assert page.inner_text("#status") == "Your move."
    buttons = page.locator(".decision .options button").count()
    targets = page.locator(".board-target").count()
    assert buttons == targets >= 1
    assert page.locator("#hand .card-chip").count() >= 5
    assert page.locator("#notepad tr").count() > 21
    assert page.locator(".seat.compact").count() == 3


def test_clicking_a_target_plays_the_move(page):
    _deal_table(page, {"Scarlett": "me", "Mustard": "character", "White": "character",
                       "Green": "empty", "Peacock": "empty", "Plum": "empty"})
    page.wait_for_selector(".board-target", timeout=20000)
    before = page.locator("#log li:not(.placeholder)").count()
    page.locator(".board-target").first.click()
    page.wait_for_function(
        "n => document.querySelectorAll('#log li:not(.placeholder)').length > n",
        arg=before, timeout=20000,
    )
    lines = page.locator("#log li:not(.placeholder)").all_inner_texts()
    assert any("Scarlett (browser) moves to" in line for line in lines)
    assert page.locator(".board-target").count() == 0 or page.inner_text("#status") != "Your move."


def test_a_render_mid_choice_leaves_the_decision_panel_alone(page):
    """Phase 9d, David's high-priority report: "the Suggest selection
    drop-downs revert back to default too quickly".

    `render` ran `renderDecision` on every poll, and `renderDecision` tore
    the panel down and rebuilt it, so anything half-chosen went back to
    the first option -- every 1.5 seconds while the characters had chat
    queued. The panel is now keyed on the decision itself, and `seq`
    counts answers rather than entries so table talk does not move it.
    Saying something forces a render, which is the cheapest way to make
    the old code rebuild.
    """
    _deal_table(page, {"Scarlett": "me", "Mustard": "character", "White": "character",
                       "Green": "empty", "Peacock": "empty", "Plum": "empty"})
    page.wait_for_selector(".decision .options button", timeout=20000)
    page.eval_on_selector(".decision .options button", "b => b.dataset.mark = 'kept'")

    page.fill("#say-text", "Nobody move.")
    page.click("#say-form button[type=submit]")
    page.wait_for_function(
        "() => document.querySelectorAll('#talk li:not(.placeholder)').length >= 1", timeout=20000
    )

    assert page.locator(".decision .options button[data-mark=kept]").count() == 1, (
        "the decision panel was rebuilt under the player"
    )


def test_the_accuse_panel_opens_closes_and_keeps_what_was_picked(page):
    """Phase 9d. Accuse is its own panel, shut by default, and its three
    dropdowns are built once and never rebuilt -- so an accusation set up
    on turn 3 is still there on turn 9. Under the rules you may only
    accuse at the accusation question, so the button is disabled until
    then.
    """
    _deal_table(page, {"Scarlett": "me", "Mustard": "character", "White": "character",
                       "Green": "empty", "Peacock": "empty", "Plum": "empty"})
    page.wait_for_selector("#accuse-toggle", timeout=20000)
    assert page.inner_text("#accuse-toggle").strip().startswith("Accuse")
    assert page.locator("#accuse-body").is_hidden()

    page.click("#accuse-toggle")
    assert page.locator("#accuse-body").is_visible()
    assert page.locator("#accuse-body .field select").count() == 3
    accuse = page.locator("#accuse-body button.warn")
    assert accuse.is_disabled(), "accusing was offered outside the accusation question"
    assert "end of your turn" in page.inner_text("#accuse-hint")

    page.select_option("#accuse-body select[name=suspect]", "Plum")
    page.select_option("#accuse-body select[name=weapon]", "Rope")
    page.select_option("#accuse-body select[name=room]", "Library")

    page.fill("#say-text", "Thinking about it.")
    page.click("#say-form button[type=submit]")
    page.wait_for_function(
        "() => document.querySelectorAll('#talk li:not(.placeholder)').length >= 1", timeout=20000
    )
    assert page.input_value("#accuse-body select[name=suspect]") == "Plum"
    assert page.input_value("#accuse-body select[name=room]") == "Library"

    page.click("#accuse-body button.quiet")
    assert page.locator("#accuse-body").is_hidden()


def test_table_talk_and_the_game_log_are_separate_panels(page):
    """Phase 9d: chat goes to Table Talk, the narration stays in "The
    game so far"."""
    _deal_table(page, {"Scarlett": "me", "Mustard": "character", "White": "character",
                       "Green": "empty", "Peacock": "empty", "Plum": "empty"})
    page.wait_for_selector("#talk", timeout=20000)
    page.fill("#say-text", "Anyone been in the Study?")
    page.click("#say-form button[type=submit]")
    page.wait_for_function(
        "() => document.querySelectorAll('#talk li:not(.placeholder)').length >= 1", timeout=20000
    )
    said = page.locator("#talk li").all_inner_texts()
    assert any("Anyone been in the Study?" in line for line in said)
    assert not any("Anyone been in the Study?" in line for line in page.locator("#log li").all_inner_texts())
    assert page.locator("#talk li.kind-remark.about-chat").count() >= 1

    page.locator(".board-target").first.click()
    page.wait_for_function(
        "() => document.querySelectorAll('#log li:not(.placeholder)').length >= 1", timeout=20000
    )
    assert page.locator("#log li.kind-remark").count() == 0, "a remark landed in the game log"


def test_the_table_page_never_names_a_card_shown_between_others(page):
    """Play a few turns on autopilot: the log a person sees names a shown
    card only when they were the suggester or the refuter."""
    _deal_table(page, {"Scarlett": "me", "Mustard": "character", "White": "character",
                       "Green": "empty", "Peacock": "empty", "Plum": "empty"})
    page.wait_for_selector("#autopilot", timeout=20000)
    page.click("#autopilot")
    page.wait_for_function(
        "() => document.querySelectorAll('#log li.kind-suggestion').length >= 4", timeout=60000
    )
    lines = page.locator("#log li.kind-suggestion").all_inner_texts()
    for line in lines:
        if " showed " in line:
            assert line.startswith("Scarlett (browser) suggests") or "(browser) showed" in line, line
