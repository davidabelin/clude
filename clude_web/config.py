"""Where the web app gets its secret, its store and its cookie policy.

Nothing here reads a credential from the repo. The session secret comes
from the environment (and, locally, from the gitignored `.env` as a
convenience); the store is reached exactly as `clude_storage` reaches it
everywhere else, which on Cloud Run means the service's own identity and
no key file at all (`docs/phase8.1-plan.md` 3.4).
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SECRET_ENV = "FLASK_SECRET_KEY"
"""Environment variable holding the session secret."""

STORE_ENV = "CLUDE_WEB_STORE"
"""Environment variable holding the store URI; see `DEFAULT_STORE`."""

HTTPS_ENV = "CLUDE_WEB_HTTPS"
"""Set to 1 wherever the app is served over HTTPS, so the session cookie
is marked `Secure`. Left unset for a local http server, which would
otherwise never receive the cookie back. The Cloud Run deploy sets it
(`docs/phase8.1-plan.md` 3.6)."""

DEFAULT_STORE = "data/llm"
"""Every grid-era run lives here (CLAUDE.md, "Environment and how to
run"), so the replay list is the real one out of the box."""


def read_env_file(name: str, path=None):
    """The value of `name` in a ``KEY=value`` file, or None.

    Nothing in clude loads `.env` automatically (CLAUDE.md), and this
    does not change that for any other package: it is a fallback used
    only by `secret_key`, so that running the app on Orbit does not need
    an export every time. A deployed service has the variable in its own
    environment and never reaches this.
    """
    path = Path(path) if path else ROOT / ".env"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == name:
            return value.strip().strip('"').strip("'") or None
    return None


def secret_key(testing: bool = False):
    """The session secret: the environment first, then the local `.env`.

    Under `testing` an ephemeral random key is made instead, so a test
    never depends on the developer's environment and never signs a
    cookie with the real secret.

    Raises
    ------
    RuntimeError
        If there is no secret and this is not a test, with the command
        that sets one -- signing sessions with a generated key would log
        everyone out on every restart and hide the mistake.
    """
    found = os.environ.get(SECRET_ENV) or read_env_file(SECRET_ENV)
    if found:
        return found
    if testing:
        return secrets.token_hex(32)
    raise RuntimeError(
        f"no {SECRET_ENV} in the environment or .env. In PowerShell:\n"
        f'  $env:{SECRET_ENV} = (Get-Content .env | '
        f"Where-Object {{ $_ -match '^{SECRET_ENV}=' }}) "
        f"-replace '^{SECRET_ENV}=', ''"
    )


def store_uri() -> str:
    """The store the app reads and writes."""
    return os.environ.get(STORE_ENV) or DEFAULT_STORE


def https_only() -> bool:
    """Whether to mark the session cookie `Secure`."""
    return os.environ.get(HTTPS_ENV, "").strip().lower() in {"1", "true", "yes"}
