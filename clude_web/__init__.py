"""clude's web app: the Flask scaffold in front of the headless game.

`clude_web` imports every other package and nothing imports it
(`docs/architecture.md`), so the engine, the agents and the store stay
exactly as testable headless as they were.

Run it locally with Flask's own loader, which finds `create_app`::

    & .venv\\Scripts\\python.exe -m flask --app clude_web run --debug

It needs a session secret in `FLASK_SECRET_KEY` (the environment, or the
gitignored `.env`; see `config.secret_key`) and at least one account,
made with ``clude_cli.py users add NAME``.

On Cloud Run the `Dockerfile` serves it with gunicorn's factory form,
``gunicorn "clude_web:create_app()"`` (`docs/web.md`, "Deploying").
"""
from __future__ import annotations

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from clude_storage import open_store

from . import auth, config, views, watch

__all__ = ["create_app"]


def create_app(settings=None) -> Flask:
    """Build the app.

    Parameters
    ----------
    settings : dict or None
        Overrides, for tests and for 8.1b. ``STORE_URI`` picks the record
        store, ``SECRET_KEY`` the session secret, ``TESTING`` relaxes the
        secret to an ephemeral one; anything else is passed straight to
        Flask's config, so `SESSION_COOKIE_SECURE` and friends can be set
        from outside.

    Notes
    -----
    Every route is private unless its view is marked `auth.public`: the
    gate is registered here, once, as an app-wide `before_request`, so a
    route added later cannot be left open by forgetting a decorator.
    """
    settings = dict(settings or {})
    app = Flask(__name__)
    testing = bool(settings.get("TESTING"))

    app.config["TESTING"] = testing
    app.config["SECRET_KEY"] = settings.pop("SECRET_KEY", None) or config.secret_key(
        testing
    )
    store_uri = settings.pop("STORE_URI", None) or config.store_uri()
    app.config["STORE_URI"] = store_uri
    # Assigned, not `setdefault`: Flask seeds these keys itself (SameSite
    # as None, Secure as False), so a default would never be applied.
    # `settings` still wins, because it is merged in afterwards.
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = config.https_only()
    app.config.update(settings)
    if config.https_only():
        # Behind Cloud Run's front end the app sees plain http from the
        # proxy; trust its one hop of X-Forwarded-Proto/-Host so the
        # scheme and host are the ones the browser used. Only here: a
        # local server has no proxy, and trusting the headers there would
        # let any client choose them.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    app.extensions["store"] = open_store(store_uri)
    app.extensions["rate_limit"] = auth.RateLimit()
    app.extensions["watch"] = watch.WatchRegistry(app.extensions["store"])

    app.jinja_env.globals["csrf_token"] = auth.csrf_token
    app.before_request(auth.require_session)
    app.register_blueprint(auth.bp)
    app.register_blueprint(views.bp)
    return app
