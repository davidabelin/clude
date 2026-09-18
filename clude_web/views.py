"""The app's own pages.

The replay screen (step 4) is here. The lobby and the watch screen land
in step 5 and replace `index`'s stopgap list of games
(`docs/phase8.1-plan.md` 4).
"""
from __future__ import annotations

import json

from flask import Blueprint, abort, current_app, render_template
from markupsafe import Markup

from clude_core import board
from clude_storage import GameRecord

from . import board_svg, replay_data
from .auth import current_user

bp = Blueprint("main", __name__)

LOBBY_PREVIEW = 12
"""How many runs `index` lists until the real lobby exists."""


def embed_json(payload: dict) -> Markup:
    """A dict as JSON safe to drop inside a `<script>` block.

    `<` becomes its `\\u003c` escape, which JSON parses identically and
    which stops a `</script>` inside the data from closing the tag early.
    A replay carries table talk written by a model, so this is real text
    from outside the app, not a formality.
    """
    return Markup(json.dumps(payload).replace("<", "\\u003c"))


@bp.get("/")
def index():
    """The landing page: who is signed in, and a way into a replay.

    The list here is a stopgap so the replay screen is reachable before
    the lobby exists; step 5 replaces it.
    """
    store = current_app.extensions["store"]
    runs = []
    for run_id in store.list_runs()[:LOBBY_PREVIEW]:
        games = store.list_games(run_id)
        if games:
            runs.append({"run_id": run_id, "games": games})
    return render_template(
        "index.html",
        user=current_user(),
        store=store.describe(),
        runs=runs,
        total_runs=len(store.list_runs()),
    )


@bp.get("/replay/<run_id>/<int:index_>")
def replay(run_id, index_):
    """One stored game, scrubbable event by event.

    The first open of a game computes its belief trace, which for a
    six-seat table takes about a minute (`replay_data`); every open after
    that reads the cached document and is immediate.
    """
    store = current_app.extensions["store"]
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
