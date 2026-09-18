"""The app's own pages: the lobby, a run's games, the replay, and Watch.

`docs/phase8.1-plan.md` 3.2 has what each screen is for; `docs/web.md`
how to use them.
"""
from __future__ import annotations

import json

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)
from markupsafe import Markup

from clude_agents import AGENT_SPECS
from clude_core import board, engine
from clude_storage import GameRecord

from . import board_svg, replay_data, watch
from .auth import current_user

bp = Blueprint("main", __name__)

DEFAULT_TABLE = 4
"""The new-game form's starting table size: the arena's usual table."""


def embed_json(payload: dict) -> Markup:
    """A dict as JSON safe to drop inside a `<script>` block.

    `<` becomes its `\\u003c` escape, which JSON parses identically and
    which stops a `</script>` inside the data from closing the tag early.
    A replay carries table talk written by a model, so this is real text
    from outside the app, not a formality.
    """
    return Markup(json.dumps(payload).replace("<", "\\u003c"))


def _store():
    return current_app.extensions["store"]


def _registry() -> watch.WatchRegistry:
    return current_app.extensions["watch"]


def run_listing(store) -> list:
    """Every stored run as the lobby lists it, games played here first.

    Read from each run's summary, which already carries every game's
    seats, winner and length, so the lobby opens no game record at all.
    """
    runs = []
    for run_id in store.list_runs():
        try:
            summary = store.get_run(run_id)
        except KeyError:
            continue
        runs.append(
            {
                "run_id": run_id,
                "n_games": summary.get("n_games", len(summary.get("games", []))),
                "roster": summary.get("roster", []),
                "player_counts": summary.get("player_counts", []),
            }
        )
    runs.sort(key=lambda r: (r["run_id"] != watch.WEB_RUN, r["run_id"]))
    return runs


def _lobby(error=None, form=None, status=200):
    characters = [
        {"name": name, "method": replay_data.seat_method(name)}
        for name in sorted(AGENT_SPECS)
    ]
    form = form or {}
    return (
        render_template(
            "lobby.html",
            user=current_user(),
            store=_store().describe(),
            runs=run_listing(_store()),
            watching=_registry().in_progress(),
            characters=characters,
            chosen=set(form.get("characters", [])),
            n_players=form.get("n_players", DEFAULT_TABLE),
            seed=form.get("seed", ""),
            sizes=range(engine.MIN_PLAYERS, engine.MAX_PLAYERS + 1),
            error=error,
        ),
        status,
    )


@bp.get("/")
def index():
    """The lobby: start a game to watch, pick up one in progress, or open
    any stored game as a replay."""
    return _lobby()


@bp.get("/runs/<run_id>")
def run(run_id):
    """One run's games, each a way into its replay."""
    try:
        summary = _store().get_run(run_id)
    except (KeyError, ValueError):
        abort(404)
    return render_template(
        "run.html",
        run_id=run_id,
        summary=summary,
        games=sorted(summary.get("games", []), key=lambda g: g["game_index"]),
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
        board=board_svg.board_svg(
            {s: board.start_position(s) for s in suspects},
            title=f"{run_id} game {index_}",
        ),
        suspects=suspects,
        n_frames=len(payload["frames"]),
    )


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
        }
        return _lobby(error=str(exc), form=form, status=400)
    watch_id = _registry().create(setup, current_user())
    return redirect(url_for("main.watch_game", watch_id=watch_id))


def _watched(watch_id):
    game = _registry().game(watch_id)
    if game is None:
        abort(404)
    return game


def _finished(watch_id, game):
    """Save a finished game and send the viewer to its replay, where the
    hands and the envelope are finally shown."""
    ref = _registry().finish(watch_id, game)
    return redirect(url_for("main.replay", run_id=ref["run_id"], index_=ref["index"]))


@bp.get("/watch/<watch_id>")
def watch_game(watch_id):
    """A game being played: Direction D's order -- the board first, the
    seats' compact bars under it, the latest suggestion spoken."""
    game = _watched(watch_id)
    with game.lock:
        if game.finished:
            return _finished(watch_id, game)
        positions = {
            game.suspects[seat]: node for seat, node in game.state.positions.items()
        }
        return render_template(
            "watch.html",
            watch_id=watch_id,
            game=game,
            setup=game.setup,
            document=_registry().document(watch_id) or {},
            board=board_svg.board_svg(positions, title="The game in progress"),
            readings=game.readings(),
            lines=game.turn_lines(),
            spoken=game.last_suggestion(),
            limitation=replay_data.TRACE_LIMITATION,
        )


@bp.post("/watch/<watch_id>/next")
def watch_next(watch_id):
    """Play one more turn."""
    game = _watched(watch_id)
    with game.lock:
        game.advance(1)
        _registry().save(watch_id, game)
        if game.finished:
            return _finished(watch_id, game)
    return redirect(url_for("main.watch_game", watch_id=watch_id))


@bp.post("/watch/<watch_id>/end")
def watch_end(watch_id):
    """Play every remaining turn, then open the replay. A whole game is
    around twenty seconds for a table with Plum on it."""
    game = _watched(watch_id)
    with game.lock:
        game.play_to_end()
        _registry().save(watch_id, game)
        return _finished(watch_id, game)
