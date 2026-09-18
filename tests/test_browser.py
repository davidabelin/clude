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

    app = create_app({"STORE_URI": str(root), "SECRET_KEY": "browser-tests"})
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
