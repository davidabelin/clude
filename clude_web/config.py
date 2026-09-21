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

KEY_ENV = "ANTHROPIC_API_KEY"
"""The workspace-scoped key for LLM seats on the web (Phase 8.3a). On
Cloud Run it arrives from Secret Manager; locally the `.env` fallback
serves, as for the session secret. Without it the lobby disables LLM
seats and nothing reachable from the URL can spend."""

BUDGET_ENV = "CLUDE_WEB_LLM_BUDGET"
"""Dollars one table may spend with Claude, the lobby form's default."""

DAILY_CAP_ENV = "CLUDE_WEB_LLM_DAILY_CAP"
"""Dollars the whole service may spend with Claude in one UTC day."""

DEFAULT_BUDGET = 2.0
DEFAULT_DAILY_CAP = 10.0
"""David's 8.3 budgets (docs/phase8-plan.md 9)."""

MODEL_ENV = "CLUDE_LLM_MODEL"
DEFAULT_MODEL = "claude-opus-5"
"""The model every web table uses, as the CLI's default; the same
variable the live smoke test reads."""

MCP_SECRET_ENV = "CLUDE_MCP_SECRET"
"""The secret path segment the MCP endpoint is mounted under (Phase 9,
`clude_web.mcp.combined_app`): ``/mcp/<secret>``. The mount sits
outside the login gate, so the secret is the whole guard on it, the
same trade the login makes (`docs/web.md`, "Convenience over secrecy").
On Cloud Run it arrives from Secret Manager; locally the `.env`
fallback serves. Without it the endpoint is not mounted at all."""

MCP_ACCOUNT_ENV = "CLUDE_MCP_ACCOUNT"
DEFAULT_MCP_ACCOUNT = "claude"
"""The account the chat seat plays as: an ordinary one, made with
``users add claude``. Its label in every record."""


def mcp_secret():
    """The MCP endpoint's secret path segment, or None: the environment
    first, then `.env`."""
    return os.environ.get(MCP_SECRET_ENV) or read_env_file(MCP_SECRET_ENV)


def mcp_account() -> str:
    """The account key the chat seat sits as."""
    return (os.environ.get(MCP_ACCOUNT_ENV) or "").strip().lower() or DEFAULT_MCP_ACCOUNT


def read_env_file(name: str, path=None):
    """The value of `name` in a ``KEY=value`` file, or None.

    Nothing in clude loads `.env` automatically (CLAUDE.md), and this
    does not change that for any other package: it is a fallback used
    only by `secret_key`, so that running the app on Orbit does not need
    an export every time. A deployed service has the variable in its own
    environment and never reaches this.

    With `python-dotenv` installed, ``flask run`` loads `.env` into the
    environment before the app is even built, so this fallback does
    nothing on that path -- the environment is checked first and wins.
    It still covers the ways the app is made without Flask's CLI:
    gunicorn in 8.1b, the tests, and `create_app` called directly.
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


def anthropic_key():
    """The model key, or None: the environment first, then `.env`."""
    return os.environ.get(KEY_ENV) or read_env_file(KEY_ENV)


def _dollars(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default


def llm_budget() -> float:
    """The per-table default budget, in dollars."""
    return _dollars(BUDGET_ENV, DEFAULT_BUDGET)


def llm_daily_cap() -> float:
    """The service's daily cap, in dollars."""
    return _dollars(DAILY_CAP_ENV, DEFAULT_DAILY_CAP)


def llm_model() -> str:
    """The model id for web tables."""
    return (os.environ.get(MODEL_ENV) or "").strip() or DEFAULT_MODEL
