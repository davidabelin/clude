"""The app's own pages: the lobby, a run's games, the replay, Watch, and
the tables people play at (Phase 8.2).

`docs/phase8.1-plan.md` 3.2 has what the first screens are for and
`docs/phase8-plan.md` 3.2-3.4 the table; `docs/web.md` how to use them.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from markupsafe import Markup

from clude_agents import AGENT_SPECS
from clude_core import board, engine
from clude_core.domain import SUSPECTS
from clude_storage import GameRecord
from clude_training.table import TableError, TableSetup

from . import board_svg, replay_data, tables, users, watch
from .auth import current_style, current_user, public

bp = Blueprint("main", __name__)

DEFAULT_TABLE = 4
"""The Watch form's starting table size: the arena's usual table."""

DEFAULT_SEATS: dict = {
    "Scarlett": "me", "Mustard": "character", "White": "character", "Green": "character",
    "Peacock": "empty", "Plum": "empty",
}
"""The table form's starting occupants: you as Scarlett against three
characters, a four-seat game."""

CONTACT_URL = "https://github.com/davidabelin/clude/issues"
"""Where the footer's Contact goes: the repo's GitHub issues (D12)."""

LOBBY_FETCHES = 10
"""How many run summaries the lobby reads at once (`run_listing`): the
storage client's connection pool, which holds 10 per host. Measured from
Orbit, 10 threads read 39 summaries in 0.7 s where 16 took 1.2 s, the
extra threads opening and throwing away connections."""


def _board(positions: dict, title: str) -> str:
    """The board for this page in the viewer's look: dressed for an
    Engraved one (Phase 10f), as frozen for Legacy."""
    return board_svg.board_svg(positions, title=title, dressed=current_style().engraved)


def embed_json(payload: dict) -> Markup:
    """A dict as JSON safe to drop inside a `<script>` block.

    `<` becomes its `\\u003c` escape, which JSON parses identically and
    which stops a `</script>` inside the data from closing the tag early.
    A replay carries table talk written by a model, and a table what
    people type, so this is real text from outside the app, not a
    formality.
    """
    return Markup(json.dumps(payload).replace("<", "\\u003c"))


def _store():
    return current_app.extensions["store"]


def _registry() -> tables.TableRegistry:
    return current_app.extensions["tables"]


def _me() -> str:
    """The signed-in account's key: the label a human seat is recorded
    under, and what `SeatRecord.label` and a logbook are keyed by."""
    return users.normalise(current_user())


PRACTICE = "practice"
"""The Stored games folder of games played at clude's tables: the
store's ``web`` run (`tables.WEB_RUN`) under the name David gave it
(2026-09-29). The store's key is unchanged."""

DEVELOPMENT = "development"
"""The Stored games folder holding every other run: the arenas, the
sweeps, the ladders, the fixtures (David, 2026-09-29)."""


def folder_of(run_id: str) -> str:
    """The Stored games folder a run is shown under."""
    return PRACTICE if run_id == tables.WEB_RUN else DEVELOPMENT


def run_title(run_id: str) -> str:
    """A run's name as shown: the practice run by its folder's name."""
    return PRACTICE if run_id == tables.WEB_RUN else run_id


def folders(store) -> dict:
    """The lobby's two folders: how many games practice holds and what
    they spent with Claude, and how many runs are under development.
    Reads one summary, the practice run's; the development runs are
    only counted, and read when their folder is opened."""
    try:
        practice = store.get_run(tables.WEB_RUN)
    except KeyError:
        practice = {}
    games = practice.get("games", [])
    return {
        PRACTICE: {"n_games": practice.get("n_games", len(games)), "cost": run_cost(games)},
        DEVELOPMENT: {"n_runs": sum(1 for run_id in store.list_runs() if run_id != tables.WEB_RUN)},
    }


def wall_time(seconds) -> str:
    """A game's wall time as the games table shows it: ``"42 s"``,
    ``"17 min"``, ``"1 h 05 min"``; empty when it was not recorded."""
    if seconds is None:
        return ""
    seconds = max(0, int(round(float(seconds))))
    if seconds < 60:
        return f"{seconds} s"
    minutes = int(round(seconds / 60))
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60} h {minutes % 60:02d} min"


def run_listing(store) -> list:
    """Every stored run as the lobby lists it, games played here first.

    Read from each run's summary, which already carries every game's
    seats, winner and length, so the lobby opens no game record at all.
    The summaries are fetched in parallel: on Cloud Run each is a round
    trip to the bucket, and one after another the lobby took 3.5 s for 38
    runs (`docs/phase8.1-plan.md`, section 8, step 8).
    """

    def fetch(run_id):
        try:
            return run_id, store.get_run(run_id)
        except KeyError:
            return run_id, None

    with ThreadPoolExecutor(max_workers=LOBBY_FETCHES) as pool:
        fetched = list(pool.map(fetch, store.list_runs()))

    runs = []
    for run_id, summary in fetched:
        if summary is None:
            continue
        runs.append(
            {
                "run_id": run_id,
                "n_games": summary.get("n_games", len(summary.get("games", []))),
                "roster": summary.get("roster", []),
                "player_counts": summary.get("player_counts", []),
                "cost": run_cost(summary.get("games", [])),
            }
        )
    runs.sort(key=lambda r: (r["run_id"] != tables.WEB_RUN, r["run_id"]))
    return runs


def run_cost(games: list):
    """What a run's games spent with Claude in all, from each game's
    ``cost`` in the summary (Phase 9g), or None when no game records
    one: a headless run, or one stored before costs were."""
    costs = [float(g["cost"]) for g in games if g.get("cost") is not None]
    return round(sum(costs), 6) if costs else None


def _table_listing(me: str) -> list:
    """Every unfinished table as the lobby lists it: who sits where,
    whether it waits for people, and whether the viewer is at it."""
    out = []
    for document in _registry().in_progress():
        try:
            setup = TableSetup.from_dict(document["setup"])
        except (KeyError, ValueError):
            continue
        humans = [spec for spec in setup.seats if spec.kind == "human"]
        endpoint = "main.table" if humans or setup.open_seats else "main.watch_game"
        out.append(
            {
                "id": document["id"],
                "url": url_for(endpoint, table_id=document["id"]),
                "status": document.get("status", "playing"),
                "seats": [
                    {"token": spec.token, "kind": spec.kind, "label": spec.label}
                    for spec in setup.seats
                ],
                "seed": setup.seed,
                "turns": document.get("turns", 0),
                "started_by": document.get("started_by"),
                "open": len(setup.open_seats),
                "mine": tables.viewer_seat(setup, me) is not None,
                "human": bool(humans),
                "remember": setup.remember,
                "speed": tables.timeout_for(document) <= tables.SPEED_TIMEOUT,
                "model": any(spec.kind == "llm" for spec in setup.seats),
                "wrapping_up": bool(tables.pending_debriefs(document)),
                "can_end": tables.viewer_seat(setup, me) is not None
                or (document.get("started_by") or "").lower() == me,
            }
        )
    return out


def _lobby(error=None, form=None, status=200, table_error=None, table_form=None):
    characters = [
        {"name": name, "method": replay_data.seat_method(name)}
        for name in sorted(AGENT_SPECS)
    ]
    form = form or {}
    table_form = table_form or {}
    me = _me()
    tokens = [
        {
            "token": token,
            "method": replay_data.seat_method(token),
            "value": table_form.get(f"seat-{token}", DEFAULT_SEATS.get(token, "empty")),
            "memory": table_form.get(f"memory-{token}", tables.DEFAULT_MEMORY),
        }
        for token in SUSPECTS
    ]
    return (
        render_template(
            "lobby.html",
            user=current_user(),
            me=me,
            store=_store().describe(),
            folders=folders(_store()),
            tables=_table_listing(me),
            characters=characters,
            chosen=set(form.get("characters", [])),
            n_players=form.get("n_players", DEFAULT_TABLE),
            seed=form.get("seed", ""),
            sizes=range(engine.MIN_PLAYERS, engine.MAX_PLAYERS + 1),
            error=error,
            tokens=tokens,
            table_seed=table_form.get("seed", ""),
            remember=tables.remember_from_form(table_form),
            speed=tables.speed_from_form(table_form),
            watch_remember=tables.remember_from_form(form),
            table_error=table_error,
            llm=_registry().llm,
            budget=table_form.get("budget", ""),
        ),
        status,
    )


@bp.get("/")
def index():
    """The lobby: sit at a table, start a game to watch, pick up one in
    progress, or open any stored game as a replay."""
    return _lobby()


@bp.get("/privacy")
@public
def privacy():
    """What clude keeps and where (D12): public, so it can be read
    before signing in. Drafted 2026-09-29, ahead of 10h."""
    return render_template("privacy.html")


@bp.get("/wiki")
def wiki():
    """Wikiclude's front door: a placeholder until the pages are written
    (David, 2026-09-29: "don't start this yet")."""
    return render_template("wiki.html")


@bp.get("/practice")
def practice():
    """The practice folder: every game played at clude's tables."""
    return run(tables.WEB_RUN)


@bp.get("/development")
def development():
    """The development folder: every other run, each a table of games."""
    runs = [r for r in run_listing(_store()) if r["run_id"] != tables.WEB_RUN]
    return render_template("development.html", runs=runs, store=_store().describe())


@bp.get("/runs/<run_id>")
def run(run_id):
    """One run's games, each a way into its replay."""
    try:
        summary = _store().get_run(run_id)
    except (KeyError, ValueError):
        abort(404)
    games = sorted(summary.get("games", []), key=lambda g: g["game_index"])
    return render_template(
        "run.html",
        run_id=run_id,
        title=run_title(run_id),
        folder=folder_of(run_id),
        summary=summary,
        games=games,
        cost=run_cost(games),
    )


@bp.get("/replay/<run_id>/<int:index_>")
def replay(run_id, index_):
    """One stored game, scrubbable event by event.

    The first open of a game computes its belief trace, about ten seconds
    for a four-seat table (`replay_data`); every open after that reads
    the cached document and is immediate.
    """
    store = _store()
    try:
        record = GameRecord.from_dict(store.get_game(run_id, index_))
    except (KeyError, ValueError):
        abort(404)

    trace = replay_data.cached_trace(store, record)
    payload = replay_data.screen_payload(record, trace)
    suspects = replay_data.seat_names(record)
    return render_template(
        "replay.html",
        record=record,
        trace=trace,
        payload=embed_json(payload),
        # Drawn at the start squares so every token circle exists in the
        # document; the scrubber moves them rather than redrawing the board.
        board=_board(
            {s: board.start_position(s) for s in suspects},
            f"{run_id} game {index_}",
        ),
        suspects=suspects,
        run_title=run_title(run_id),
        n_frames=len(payload["frames"]),
    )


# --- tables -------------------------------------------------------------


def _document(table_id: str) -> dict:
    document = _registry().document(table_id)
    if document is None:
        abort(404)
    return document


def _live(table_id: str):
    """The live game for a dealt table, or a 404."""
    game = _registry().game(table_id)
    if game is None:
        abort(404)
    return game


def _replay_url(document: dict):
    ref = document.get("record")
    if not ref:
        return None
    return url_for("main.replay", run_id=ref["run_id"], index_=ref["index"])


def _payload(table_id: str, game, since: int = 0) -> dict:
    """The viewer's view. Asking for one while holding no seat is what
    puts someone in the spectator gallery, so every route that builds a
    view keeps the gallery current without a heartbeat of its own."""
    registry = _registry()
    document = registry.document(table_id) or {"id": table_id}
    viewer = tables.viewer_seat(game.setup, _me())
    if viewer is None:
        registry.seen_watching(table_id, _me())
    return tables.view_payload(
        game,
        document,
        viewer,
        since=since,
        replay_url=_replay_url(document),
        waiting_for=registry.waiting_for(table_id, game),
        watching=registry.watching(table_id),
        spend=registry.spend(table_id, document),
        typing=registry.typing(table_id, game),
    )


def _finished(table_id: str, game):
    """Save a finished game and send the viewer to its replay, where the
    hands and the envelope are finally shown."""
    ref = _registry().finish(table_id, game)
    return redirect(url_for("main.replay", run_id=ref["run_id"], index_=ref["index"]))


def _table_page(table_id: str):
    """The screen for a table in any state: waiting for people, being
    played (Watch's page when nobody human is at it), or finished."""
    document = _document(table_id)
    try:
        setup = TableSetup.from_dict(document["setup"])
    except (KeyError, ValueError):
        abort(404)
    me = _me()
    if document.get("status") == "open":
        return render_template(
            "table.html",
            table_id=table_id,
            open_table=True,
            setup=setup,
            seats=[
                {"token": spec.token, "kind": spec.kind, "label": spec.label}
                for spec in setup.seats
            ],
            viewer=tables.viewer_seat(setup, me),
            me=me,
            user=current_user(),
            document=document,
            payload=None,
            payload_json=None,
            board=None,
        )
    game = _live(table_id)
    if game.finished and not tables.pending_debriefs(document):
        return _finished(table_id, game)
    if not setup.external:
        return _watch_page(table_id, game, document)
    payload = _payload(table_id, game)
    positions = {game.suspects[seat]: node for seat, node in game.state.positions.items()}
    return render_template(
        "table.html",
        table_id=table_id,
        open_table=False,
        setup=setup,
        seats=payload["seats"],
        viewer=tables.viewer_seat(setup, me),
        me=me,
        user=current_user(),
        document=document,
        payload=payload,
        payload_json=embed_json(
            dict(
                payload,
                urls={
                    "poll": url_for("main.table_poll", table_id=table_id),
                    "work": url_for("main.table_work", table_id=table_id),
                    "answer": url_for("main.table_answer", table_id=table_id),
                    "autopilot": url_for("main.table_autopilot", table_id=table_id),
                    "say": url_for("main.table_say", table_id=table_id),
                    "typing": url_for("main.table_typing", table_id=table_id),
                },
            )
        ),
        board=_board(positions, "The table"),
        limitation=replay_data.TRACE_LIMITATION,
    )


def _watch_page(table_id: str, game, document: dict):
    """Direction D's order -- the board first, the seats' compact bars
    under it, the latest suggestion spoken -- for a table with nobody
    human at it, advanced by its two buttons."""
    with game.lock:
        positions = {game.suspects[seat]: node for seat, node in game.state.positions.items()}
        return render_template(
            "watch.html",
            watch_id=table_id,
            game=game,
            setup=game.setup,
            document=document,
            board=_board(positions, "The game in progress"),
            readings=game.readings(),
            lines=game.turn_lines(),
            spoken=game.last_suggestion(),
            # The turn's loudest sound, played once by static/sound.js
            # when the page arrives from Next turn (Phase 10g).
            cue=replay_data.loudest_cue(replay_data.event_cue(e) for e in game.turn_events()),
            limitation=replay_data.TRACE_LIMITATION,
        )


@bp.post("/tables")
def table_new():
    """A new table from the lobby's seat form: dealt at once, or waiting
    for the people its open seats are for."""
    me = _me()
    try:
        setup = tables.parse_table_form(request.form, me, _registry().llm)
    except ValueError as exc:
        return _lobby(table_error=str(exc), table_form=request.form.to_dict(), status=400)
    try:
        budget = tables.parse_budget(request.form, _registry().llm)
        table_id = _registry().create(
            setup, current_user(), budget, speed=tables.speed_from_form(request.form)
        )
    except ValueError as exc:
        return _lobby(table_error=str(exc), table_form=request.form.to_dict(), status=400)
    return redirect(url_for("main.table", table_id=table_id))


@bp.get("/tables/<table_id>")
def table(table_id):
    """A table: the play view if the viewer holds a seat, the spectator
    view otherwise."""
    return _table_page(table_id)


@bp.post("/tables/<table_id>/sit")
def table_sit(table_id):
    """Take an open seat before the deal."""
    try:
        _registry().sit(table_id, _me(), (request.form.get("token") or "").strip())
    except TableError as exc:
        return render_template("error.html", message=str(exc)), 400
    return redirect(url_for("main.table", table_id=table_id))


@bp.post("/tables/<table_id>/leave")
def table_leave(table_id):
    """Give up a seat before the deal."""
    try:
        _registry().leave(table_id, _me())
    except TableError as exc:
        return render_template("error.html", message=str(exc)), 400
    return redirect(url_for("main.index"))


@bp.post("/tables/<table_id>/deal")
def table_deal(table_id):
    """Deal a waiting table. Refused while an open seat is unfilled."""
    document = _document(table_id)
    try:
        setup = TableSetup.from_dict(document["setup"])
    except (KeyError, ValueError):
        abort(404)
    if tables.viewer_seat(setup, _me()) is None and document.get("started_by") != current_user():
        return render_template("error.html", message="Only someone at the table can deal it."), 403
    try:
        _registry().deal(table_id)
    except TableError as exc:
        return render_template("error.html", message=str(exc)), 400
    return redirect(url_for("main.table", table_id=table_id))


@bp.post("/tables/<table_id>/abandon")
def table_abandon(table_id):
    """End a table for good: anyone seated at it, or whoever started
    it. It leaves the lobby and nothing is recorded."""
    _document(table_id)
    try:
        _registry().abandon(table_id, _me())
    except TableError as exc:
        return render_template("error.html", message=str(exc)), 403
    return redirect(url_for("main.index"))


@bp.get("/tables/<table_id>/poll")
def table_poll(table_id):
    """The viewer's view of the table since an event cursor, as JSON.
    Never takes the game lock."""
    game = _live(table_id)
    try:
        since = int(request.args.get("since", 0) or 0)
    except ValueError:
        since = 0
    return jsonify(_payload(table_id, game, since))


@bp.post("/tables/<table_id>/work")
def table_work(table_id):
    """One unit of bot work if any is due, then the viewer's view."""
    game = _live(table_id)
    did = _registry().work(table_id, game)
    try:
        since = int(request.form.get("since", 0) or 0)
    except ValueError:
        since = 0
    payload = _payload(table_id, game, since)
    payload["did"] = did
    return jsonify(payload)


@bp.post("/tables/<table_id>/answer")
def table_answer(table_id):
    """One answer from the viewer's seat, as `data` (JSON) and `seq`."""
    game = _live(table_id)
    viewer = tables.viewer_seat(game.setup, _me())
    if viewer is None:
        return jsonify({"error": "You are not sitting at this table."}), 403
    try:
        seq = int(request.form.get("seq", ""))
        data = json.loads(request.form.get("data", "null"))
    except (TypeError, ValueError):
        return jsonify({"error": "That answer is not in the shape the decision needs."}), 400
    try:
        _registry().answer(table_id, game, viewer, seq, data)
    except TableError as exc:
        return jsonify({"error": str(exc)}), 400
    try:
        since = int(request.form.get("since", 0) or 0)
    except ValueError:
        since = 0
    return jsonify(_payload(table_id, game, since))


@bp.post("/tables/<table_id>/say")
def table_say(table_id):
    """One line of chat from the viewer's seat (Phase 8.3b)."""
    game = _live(table_id)
    viewer = tables.viewer_seat(game.setup, _me())
    if viewer is None:
        return jsonify({"error": "You are not sitting at this table."}), 403
    try:
        _registry().say(table_id, game, viewer, request.form.get("text", ""))
    except TableError as exc:
        return jsonify({"error": str(exc)}), 400
    try:
        since = int(request.form.get("since", 0) or 0)
    except ValueError:
        since = 0
    return jsonify(_payload(table_id, game, since))


@bp.post("/tables/<table_id>/typing")
def table_typing(table_id):
    """The viewer's page says their chat box holds text (``on=1``) or
    was emptied (``on=0``), for "so-and-so is typing" at the other
    seats (Phase 9h). A heartbeat, not a view: the next poll carries
    the answer, so this returns nothing but an acknowledgement."""
    game = _live(table_id)
    viewer = tables.viewer_seat(game.setup, _me())
    if viewer is None:
        return jsonify({"error": "You are not sitting at this table."}), 403
    on = (request.form.get("on") or "").strip().lower() in ("1", "on", "true", "yes")
    _registry().seen_typing(table_id, viewer, on)
    return jsonify({"ok": True})


@bp.post("/tables/<table_id>/autopilot")
def table_autopilot(table_id):
    """Hand a seat to the stand-in or take it back: the seat's owner
    only. (Until Phase 9h anyone seated could hand over a seat that had
    stalled three minutes; the time-out plays a stalled turn itself now,
    so nobody needs to.)"""
    game = _live(table_id)
    registry = _registry()
    viewer = tables.viewer_seat(game.setup, _me())
    if viewer is None:
        return jsonify({"error": "You are not sitting at this table."}), 403
    try:
        seat = int(request.form.get("seat", viewer))
    except ValueError:
        return jsonify({"error": "No such seat."}), 400
    on = (request.form.get("on") or "").strip().lower() in ("1", "on", "true", "yes")
    if seat != viewer:
        return jsonify({"error": "Only the seat's owner can do that."}), 403
    if not (0 <= seat < game.setup.n_players) or game.kinds[seat] != "human":
        return jsonify({"error": "No such seat."}), 400
    try:
        registry.set_autopilot(table_id, game, seat, on)
    except TableError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_payload(table_id, game))


# --- Watch: a table with nobody human at it -----------------------------


@bp.post("/watch")
def watch_new():
    """Start a headless game to watch, from the lobby's form."""
    try:
        setup = watch.parse_setup(request.form)
    except ValueError as exc:
        form = {
            "characters": request.form.getlist("characters"),
            "n_players": request.form.get("n_players", DEFAULT_TABLE),
            "seed": request.form.get("seed", ""),
            "remember": request.form.get("remember", "1"),
        }
        return _lobby(error=str(exc), form=form, status=400)
    table_id = _registry().create(setup, current_user())
    return redirect(url_for("main.watch_game", table_id=table_id))


def _watched(table_id):
    """A dealt table with nobody human at it, or a 404 / 400."""
    game = _live(table_id)
    if game.setup.external:
        abort(400)
    return game


@bp.get("/watch/<table_id>")
def watch_game(table_id):
    """A game being watched; a table with people at it opens as a table."""
    return _table_page(table_id)


@bp.post("/watch/<table_id>/next")
def watch_next(table_id):
    """Play one more turn."""
    game = _watched(table_id)
    with game.lock:
        game.run(1)
        _registry().save(table_id, game)
        if game.finished:
            return _finished(table_id, game)
    return redirect(url_for("main.watch_game", table_id=table_id))


@bp.post("/watch/<table_id>/end")
def watch_end(table_id):
    """Play every remaining turn, then open the replay. A whole game is
    around twenty seconds for a table with Plum on it."""
    game = _watched(table_id)
    with game.lock:
        game.play_to_end()
        _registry().save(table_id, game)
        return _finished(table_id, game)
