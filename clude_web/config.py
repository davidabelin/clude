"""Resolve web settings from environment and selected .env fallbacks.

Secrets/model key/MCP path/public URL have direct file fallbacks; store,
HTTPS, model and budgets read environment defaults. Flask's CLI may load
.env separately through python-dotenv; direct scripts do not export it.
Cloud Run uses environment/Secret Manager and runtime GCS identity.
See docs/web.md for the configuration table.
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
(see docs/web.md)."""

DEFAULT_STORE = "data/llm"
"""Default local record/logbook/account store."""

KEY_ENV = "ANTHROPIC_API_KEY"
"""Service key for LLM seats: environment first, then .env.
Without a key the lobby disables LLM seats. Cloud Run uses Secret Manager.
"""

BUDGET_ENV = "CLUDE_WEB_LLM_BUDGET"
"""Dollars one table may spend with Claude, the lobby form's default."""

DAILY_CAP_ENV = "CLUDE_WEB_LLM_DAILY_CAP"
"""Dollars the whole service may spend with Claude in one UTC day."""

DEFAULT_BUDGET = 2.0
DEFAULT_DAILY_CAP = 10.0
"""Approved table/day defaults; see docs/web.md for metering limits."""

MODEL_ENV = "CLUDE_LLM_MODEL"
DEFAULT_MODEL = "claude-opus-5"
"""The model every web table uses, as the CLI's default; the same
variable the live smoke test reads."""

MCP_SECRET_ENV = "CLUDE_MCP_SECRET"
"""Secret transport path, /mcp/<secret>, outside Flask's login gate.
Gameplay tools additionally require a game-account login. Environment
precedes .env; no secret means no mount. Cloud Run uses Secret Manager.
"""

PUBLIC_URL_ENV = "CLUDE_PUBLIC_URL"
"""The address people reach the app at, such as the Cloud Run URL. Set
by the deploy; unset locally, where a link stays a path."""

def mcp_secret():
    """The MCP endpoint's secret path segment, or None: the environment
    first, then `.env`."""
    return os.environ.get(MCP_SECRET_ENV) or read_env_file(MCP_SECRET_ENV)


def public_url():
    """Return configured public base URL without trailing slash, or None.

    Environment precedes .env; MCP uses it for absolute replay links.
    """
    found = (os.environ.get(PUBLIC_URL_ENV) or read_env_file(PUBLIC_URL_ENV) or "").strip().rstrip("/")
    return found or None


def read_env_file(name: str, path=None):
    """Read one value from a KEY=value file without exporting its contents.

    Web secret/key/MCP/public-URL accessors use this fallback after checking
    environment. Flask CLI loading through python-dotenv is separate. Missing
    files/empty values return None. This is not a general dotenv parser.
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
    """Resolve session secret from environment, then .env.

    If neither exists, testing permits an ephemeral key. A configured secret
    still wins under testing; callers needing isolation should override it.

    Raises
    ------
    RuntimeError
        If no secret is configured outside testing.
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
