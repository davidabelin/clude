"""The app's own pages.

In step 2 this is the placeholder the login lands on. The lobby, the
replay screen and the watch screen fill it in over steps 3 to 5
(`docs/phase8.1-plan.md` 4).
"""
from __future__ import annotations

from flask import Blueprint, current_app, render_template

from .auth import current_user

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    """The landing page, and for now the whole of the app behind the
    login: who is signed in and which store is being read."""
    store = current_app.extensions["store"]
    return render_template(
        "index.html",
        user=current_user(),
        store=store.describe(),
        runs=len(store.list_runs()),
    )
