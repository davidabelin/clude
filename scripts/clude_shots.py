"""Screenshot the web app, so a UI change can actually be looked at.

An SVG rasteriser is no use for clude: `clude_web.board_svg` sets no
colour at all, leaving every shape to `static/style.css`, so rendering
the SVG on its own gives an unstyled blank. Only a real browser applies
the stylesheet, runs `replay.js` and honours dark mode and a phone
width. Hence Playwright.

This is a maintainer tool, not part of the app and not imported by it.
It boots the app on a spare port against a throwaway store seeded from
real records, signs in, and writes a PNG per screen: the login, the
lobby (including an LLM seat's memory dial), a run's games, a watched game as dealt and a few turns in, a
table with a person at it on their move and a few answers later, a
table with two model seats as a player and as a spectator sees it (each
seat's share of the spend), a table waiting for players, and a replay
at its start, middle and end.

The model here never answers, so it never spends: the spend on the model
table is seeded into the app's ledger, and the first game of the copied
run is given a cost, so the cost bars and the games' cost column have
something to show (Phase 9g).

Usage
-----
    python scripts/clude_shots.py
    python scripts/clude_shots.py --store data/llm --run grid-twin-base-24
    python scripts/clude_shots.py --out docs/ux/shots --dark --phone

Playwright and its browser are optional and not needed to run clude:

    python -m pip install playwright
    python -m playwright install chromium
"""
from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clude_storage import open_store  # noqa: E402
from clude_web import create_app, users  # noqa: E402

SHOT_USER = "shots"
SHOT_PASSWORD = "shots-password"

WIDE = {"width": 1440, "height": 1000}
PHONE = {"width": 390, "height": 844}


class _Quiet(WSGIRequestHandler):
    """The dev server's request log is noise here."""

    def log_message(self, *args):
        pass


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def seed_store(target: Path, source_uri: str, run: str, games: int) -> tuple:
    """Copy a few real games into a throwaway store and add an account.

    Real records, because a screenshot of made-up data proves nothing
    about how the screen handles a real game's length and crowding.
    """
    source = open_store(source_uri)
    store = open_store(str(target))
    runs = [run] if run else source.list_runs()
    picked = None
    for candidate in runs:
        indexes = source.list_games(candidate)
        if not indexes:
            continue
        picked = candidate
        for index in indexes[:games]:
            store.put_game(candidate, index, source.get_game(candidate, index))
        try:
            store.put_run(candidate, source.get_run(candidate))
        except KeyError:
            store.put_run(candidate, {"n_games": games, "seed": 0, "roster": [], "per_player": {}})
        break
    if picked is None:
        raise SystemExit(f"no games found in {source_uri}")
    users.add_user(store, SHOT_USER, SHOT_PASSWORD)
    users.mark_password_prompted(store, SHOT_USER)
    return store, picked, source.list_games(picked)[:games]


def seed_cost(store, run: str) -> None:
    """Give the throwaway copy's first game a cost, so the run page's
    cost column shows a figure beside the dashes."""
    summary = store.get_run(run)
    games = sorted(summary.get("games", []), key=lambda g: g["game_index"])
    if games:
        games[0]["cost"] = 0.34
        store.put_run(run, dict(summary, games=games))


def serve(store_uri: str):
    """Run the app on a spare port in a background thread. Returns the
    server, its address and the app."""
    from clude_llm import NullBackend  # noqa: PLC0415

    # A stand-in key so the lobby shows its model seats; the backend
    # never answers, so nothing here can spend even if a table were dealt.
    app = create_app({
        "STORE_URI": store_uri, "SECRET_KEY": "screenshots-only",
        "LLM_KEY": "screenshots-only", "LLM_BACKEND": lambda model, key: NullBackend(),
    })
    port = free_port()
    server = make_server("127.0.0.1", port, app, handler_class=_Quiet)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}", app


def spender(app):
    """``table_id -> None``: what the model table's two model seats
    (seats 1 and 3: White and Plum) would have spent, put in the app's
    own ledger so its screens read it as they would a real spend."""
    ledger = app.extensions["tables"].ledger

    def spend(table_id: str) -> None:
        if ledger.spent(table_id) == 0:
            ledger.add(table_id, 0.14, 1)
            ledger.add(table_id, 0.27, 3)

    return spend


def shoot(base: str, run: str, index: int, out: Path, dark: bool, phone: bool, spend=None) -> list:
    """Drive the app and write a PNG per screen. Returns their paths."""
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    written = []
    problems = []

    with sync_playwright() as play:
        browser = play.chromium.launch()
        sizes = [("wide", WIDE)] + ([("phone", PHONE)] if phone else [])
        schemes = ["light"] + (["dark"] if dark else [])

        for scheme in schemes:
            for label, size in sizes:
                context = browser.new_context(viewport=size, color_scheme=scheme)
                page = context.new_page()
                page.on(
                    "console",
                    lambda message: problems.append(f"console {message.type}: {message.text}")
                    if message.type == "error"
                    else None,
                )
                page.on("pageerror", lambda error: problems.append(f"page error: {error}"))

                def save(name):
                    # Let anything animated settle first. A transition on
                    # a token once made every screenshot show it halfway
                    # to where the data already said it was.
                    page.wait_for_timeout(250)
                    path = out / f"{name}-{scheme}-{label}.png"
                    page.screenshot(path=str(path), full_page=True)
                    written.append(path)

                page.goto(f"{base}/login")
                save("login")

                page.fill("#name", SHOT_USER)
                page.fill("#password", SHOT_PASSWORD)
                page.click("button[type=submit]")
                page.wait_for_url(f"{base}/")
                save("lobby")
                page.select_option("#seat-Plum", "llm")
                page.locator("#memory-Plum").fill("0.75")
                save("lobby-llm-memory")

                page.goto(f"{base}/runs/{run}")
                save("run")

                # A watched game a few turns in: Scarlett, Plum and Green
                # at four seats, so one seat is a floor bot.
                page.goto(f"{base}/")
                for name in ("Scarlett", "Plum", "Green"):
                    page.check(f"input[name=characters][value={name}]")
                page.select_option("#n_players", "4")
                page.fill("#seed", "7")
                page.click("form[action$='/watch'] button[type=submit]")
                page.wait_for_selector("#next-turn")
                save("watch-dealt")
                for _ in range(9):
                    page.click("#next-turn")
                    page.wait_for_selector("#next-turn")
                save("watch-turn")

                # A table with a person at it (Phase 8.2): you as Scarlett
                # against Mustard, White and Green, then the same table
                # after the board has been answered a few times.
                page.goto(f"{base}/")
                page.select_option("#seat-Scarlett", "me")
                page.select_option("#seat-Mustard", "character")
                page.select_option("#seat-White", "character")
                page.select_option("#seat-Green", "character")
                page.select_option("#seat-Peacock", "empty")
                page.select_option("#seat-Plum", "empty")
                page.fill("#table-seed", "7")
                page.click("#table-form button[type=submit]")
                page.wait_for_selector(".decision .options button", timeout=20000)
                save("table-move")
                # Answer whatever is asked (the first button is always a
                # legal, harmless choice: a move, "Suggest", "Pass") until
                # the bots have had a turn and it is our move again.
                for _ in range(6):
                    before = page.inner_text("#status")
                    page.click(".decision .options button")
                    page.wait_for_function(
                        "s => document.querySelector('#status').textContent !== s",
                        arg=before, timeout=20000,
                    )
                    if page.inner_text("#status") == "Your move.":
                        break
                    page.wait_for_selector(".decision .options button", timeout=40000)
                page.wait_for_function(
                    "() => document.querySelectorAll('#log li:not(.placeholder)').length >= 4",
                    timeout=40000,
                )
                save("table-later")

                # A table with two model seats (Phase 9g): each seat's
                # tab has one bar, its share of what the table has spent.
                if spend is not None:
                    page.goto(f"{base}/")
                    for token, value in (("Scarlett", "me"), ("Mustard", "empty"), ("White", "llm"),
                                         ("Green", "floor"), ("Peacock", "empty"), ("Plum", "llm")):
                        page.select_option(f"#seat-{token}", value)
                    page.fill("#table-seed", "7")
                    page.click("#table-form button[type=submit]")
                    page.wait_for_selector(".seat.compact.roster", timeout=20000)
                    spend(page.url.rstrip("/").split("/")[-1])
                    page.reload()
                    page.wait_for_selector(".gauge.cost .pct", timeout=20000)
                    save("table-cost")

                    # And as a spectator: the same bar after the deduction bars.
                    page.goto(f"{base}/")
                    for token, value in (("Scarlett", "floor"), ("Mustard", "empty"), ("White", "llm"),
                                         ("Green", "floor"), ("Peacock", "empty"), ("Plum", "llm")):
                        page.select_option(f"#seat-{token}", value)
                    page.fill("#table-seed", "7")
                    page.click("#table-form button[type=submit]")
                    page.wait_for_selector(".seat.compact .gauge", timeout=20000)
                    spend(page.url.rstrip("/").split("/")[-1])
                    page.reload()
                    page.wait_for_selector(".gauge.cost .pct", timeout=20000)
                    save("table-cost-watching")

                # A table waiting for players.
                page.goto(f"{base}/")
                page.select_option("#seat-Scarlett", "me")
                page.select_option("#seat-Mustard", "character")
                page.select_option("#seat-White", "open")
                page.select_option("#seat-Green", "empty")
                page.click("#table-form button[type=submit]")
                page.wait_for_selector(".table-open")
                save("table-open")

                page.goto(f"{base}/replay/{run}/{index}")
                page.wait_for_selector(".board-token")
                save("replay-start")

                # Halfway, where the bars are interesting: some proven,
                # most still open.
                total = page.eval_on_selector("#scrub", "el => Number(el.max)")
                page.eval_on_selector(
                    "#scrub",
                    "(el, v) => { el.value = v; el.dispatchEvent(new Event('input')); }",
                    int(total // 2),
                )
                save("replay-middle")

                page.keyboard.press("End")
                save("replay-end")

                context.close()
        browser.close()

    for problem in problems:
        print(f"  ! {problem}")
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--store", default="data/llm", help="Store to copy real games from.")
    parser.add_argument("--run", default="", help="Which run (default: the first with games).")
    parser.add_argument("--game", type=int, default=0, help="Which game of that run.")
    parser.add_argument("--games", type=int, default=3, help="How many games to copy.")
    parser.add_argument("--out", default="", help="Where to write PNGs (default: a temp dir).")
    parser.add_argument("--dark", action="store_true", help="Also shoot in dark mode.")
    parser.add_argument("--phone", action="store_true", help="Also shoot at phone width.")
    args = parser.parse_args(argv)

    import tempfile

    with tempfile.TemporaryDirectory(prefix="clude-shots-") as scratch:
        store_dir = Path(scratch) / "store"
        store, run, indexes = seed_store(store_dir, args.store, args.run, args.games)
        seed_cost(store, run)
        index = args.game if args.game in indexes else indexes[0]
        server, base, app = serve(str(store_dir))
        print(f"serving {store_dir} at {base}; shooting {run} game {index}")
        try:
            time.sleep(0.2)
            out = Path(args.out) if args.out else Path(scratch).parent / "clude-shots"
            written = shoot(base, run, index, out, args.dark, args.phone, spend=spender(app))
        finally:
            server.shutdown()
    for path in written:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
