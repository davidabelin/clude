"""The app login: the gate in front of everything else.

The Cloud Run service is deliberately reachable without Google
authentication, because the app login *is* the gate
(`docs/phase8.1-plan.md` 3.6). So the rule here is the whole security
boundary: anyone can load the login page, and nothing else.

That rule is enforced once, in `require_session`, for every route the
app has rather than per view -- a route added later is private unless
someone marks it `@public` on purpose, which is the safer way round.
"""
from __future__ import annotations

import secrets
import time
from collections import defaultdict, deque

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from . import users

bp = Blueprint("auth", __name__)

SESSION_USER = "user"
"""Session key holding the logged-in account's display name."""

SESSION_CSRF = "csrf"
"""Session key holding this session's CSRF token."""

SESSION_OFFER = "password_offer"
"""Session key set when this player still owes an answer to the one-time
password offer. Held in the session rather than read from the store on
every request, and set from the account at login."""


def public(view):
    """Mark a view reachable without a session.

    Only the login page wears this. It is an explicit opt-out so that
    forgetting it leaves a new route private rather than open.
    """
    view.is_public = True
    return view


class RateLimit:
    """A few attempts per window, counted per key, in memory.

    In memory is correct here because the service runs with
    `--max-instances 1` (`docs/phase8.1-plan.md` 3.6); were that ever
    raised, each instance would count separately and the limit would
    loosen by that factor. It is a brake on guessing a password, not a
    defence against a distributed attacker, and it is deliberately keyed
    on the name so that one account being attacked cannot lock everyone
    else out.
    """

    def __init__(self, limit: int = 5, window: float = 60.0) -> None:
        self.limit = limit
        self.window = window
        self._hits = defaultdict(deque)

    def check(self, key: str, now=None) -> bool:
        """Record an attempt; False if `key` is over the limit."""
        now = time.monotonic() if now is None else now
        hits = self._hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True

    def clear(self, key: str) -> None:
        """Forget a key's attempts, as a successful login does."""
        self._hits.pop(key, None)


def csrf_token() -> str:
    """This session's CSRF token, made on first use.

    Exposed to every template as `csrf_token()`, so a form that forgets
    it simply fails `check_csrf` rather than quietly working.
    """
    token = session.get(SESSION_CSRF)
    if not token:
        token = secrets.token_urlsafe(32)
        session[SESSION_CSRF] = token
    return token


def check_csrf() -> bool:
    """Whether this POST carried the session's CSRF token."""
    sent = request.form.get("csrf", "")
    held = session.get(SESSION_CSRF, "")
    return bool(sent) and bool(held) and secrets.compare_digest(sent, held)


def current_user():
    """The logged-in account's display name, or None."""
    return session.get(SESSION_USER)


def require_session():
    """Before every request: check CSRF on writes, then the session.

    Registered as an app-wide `before_request` in `create_app`, so it
    covers every blueprint the app will grow.
    """
    if request.method == "POST" and not check_csrf():
        return render_template("error.html", message="Stale form. Try again."), 400
    if request.endpoint == "static":
        return None
    view = current_app.view_functions.get(request.endpoint)
    if view is not None and getattr(view, "is_public", False):
        return None
    if current_user() is None:
        return redirect(url_for("auth.login"))
    if session.get(SESSION_OFFER) and request.endpoint not in {
        "auth.password",
        "auth.logout",
    }:
        # The one-time offer, asked before the app opens so that it is
        # asked at all. Declining it is a click, and it never returns.
        return redirect(url_for("auth.password"))
    return None


@bp.route("/login", methods=["GET", "POST"])
@public
def login():
    """Name and password. Nothing else in the app is reachable without
    getting through here."""
    if current_user() is not None:
        return redirect(url_for("main.index"))
    if request.method == "GET":
        return render_template("login.html")

    name = request.form.get("name", "")
    password = request.form.get("password", "")
    limiter = current_app.extensions["rate_limit"]
    if not limiter.check(users.normalise(name) if name.strip() else "-"):
        return (
            render_template("login.html", error="Too many attempts. Wait a minute."),
            429,
        )

    account = users.authenticate(current_app.extensions["store"], name, password)
    if account is None:
        # One message for a wrong name and a wrong password alike: the
        # login page is not a way to find out who has an account.
        return render_template("login.html", error="Wrong name or password."), 401

    limiter.clear(account["key"])
    session.clear()  # a new session id and a new CSRF token on every login
    session[SESSION_USER] = account["name"]
    session[SESSION_OFFER] = users.needs_password_offer(account)
    csrf_token()
    return redirect(url_for("main.index"))


@bp.route("/password", methods=["GET", "POST"])
def password():
    """The one-time offer to change a password, after a first login.

    A player sees this once and answers it once, either way; after that
    the page only says who to ask. Passwords are shown as they are typed
    here, which is the same call as the default password itself: this is
    a family game, and being able to read what you typed is worth more
    than hiding it from someone already looking at your screen.
    """
    store = current_app.extensions["store"]
    name = current_user()
    if not session.get(SESSION_OFFER):
        return render_template("password.html", offered=False)
    if request.method == "GET":
        return render_template("password.html", offered=True)

    if request.form.get("action") == "change":
        chosen = request.form.get("password", "")
        if not chosen:
            return (
                render_template(
                    "password.html",
                    offered=True,
                    error="Type a password, or keep the one you have.",
                ),
                400,
            )
        users.set_password(store, name, chosen)
    users.mark_password_prompted(store, name)
    session[SESSION_OFFER] = False
    return redirect(url_for("main.index"))


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
