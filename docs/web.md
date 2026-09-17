# The web app

`clude_web` is the Flask app in front of the headless game (Phase 8.1,
`docs/phase8.1-plan.md`). It imports every other package; nothing imports
it, so the engine, the agents and the store stay exactly as testable
headless as they were.

Built so far: the app factory, the login gate, accounts and their CLI, the
base template and the stylesheet (step 2 of 9). The lobby, the replay
scrubber and the watch screen are steps 3 to 5; the Cloud Run deploy is
8.1b.

## Running it locally

```powershell
& .venv\Scripts\python.exe -m flask --app clude_web run --debug
```

It needs two things.

**A session secret** in `FLASK_SECRET_KEY`. The app takes it from the
environment, and falls back to reading the gitignored `.env` at the repo
root for that one variable, so on Orbit there is nothing to export. This
fallback is `clude_web.config.read_env_file` and is used by nothing else:
the rest of clude still never loads `.env` (CLAUDE.md). A deployed service
has the variable in its own environment and never reaches the fallback.
With no secret anywhere the app refuses to start rather than generating
one, because a generated key would sign everybody out on every restart and
hide the mistake.

**At least one account.** There is no sign-up page; accounts are made from
the CLI only:

```powershell
& .venv\Scripts\python.exe scripts\clude_cli.py users add David
```

It prompts for the password twice and never takes it as an argument, where
it would land in shell history.

By default the app reads `data/llm`, the store holding every grid-era run,
and `users` writes there too. `CLUDE_WEB_STORE` points both somewhere else.

## Accounts

| Command | What it does |
|---|---|
| `users add NAME` | Create an account; prompts for the password. |
| `users list` | Every account and when it was made. No hash is printed. |
| `users passwd NAME` | Change a password. |
| `users remove NAME` | Delete an account. Records and logbooks are left alone. |

Each is `users <action> [--uri STORE]`.

A password is only ever stored as a Werkzeug hash (scrypt by default in
Werkzeug 3); the plaintext never reaches the store, a record or the event
log. The login name is matched case-insensitively but displayed as typed,
because it is the player's identity and not just a credential: Phase 8.2
writes it into `SeatRecord.label`, so a human's logbook follows the name
across whichever suspect they play (`docs/architecture.md`, "Seats and
player identity").

## The gate

The Cloud Run service will be reachable by anyone, deliberately: choosing
an app login means the login page is public and nothing else is
(`docs/phase8.1-plan.md` 3.6). So the gate is the whole security boundary,
and it is enforced in one place -- `auth.require_session`, registered as an
app-wide `before_request` in `create_app`. A route added later is private
unless someone marks it `@auth.public` on purpose, which is the safer way
round; `tests/test_web.py` walks the app's entire url map and asserts every
route but the login redirects, so a route added in step 3 is covered the
day it appears.

Alongside it:

- **CSRF.** Every form carries a token from the session, checked on every
  POST before anything else happens, including the login POST. The token
  is regenerated on login, so a token fixed before signing in is useless
  after.
- **Rate limiting.** A handful of attempts a minute per name, in memory.
  In memory is correct because the service runs `--max-instances 1`; were
  that raised, each instance would count separately. It is keyed on the
  name so that one account under attack cannot lock everyone else out, and
  cleared by a successful login.
- **The same answer for a wrong name and a wrong password**, in the same
  time -- `users.authenticate` hashes against a dummy when there is no such
  account -- so the login page is not a way to find out who has one.
- **The session cookie** is `HttpOnly` and `SameSite=Lax` always, and
  `Secure` when `CLUDE_WEB_HTTPS=1`. That variable is off locally, since a
  `Secure` cookie would never come back over plain http, and **the Cloud
  Run deploy must set it** (`docs/phase8.1-plan.md` 3.6).

## Layout

| File | What it holds |
|---|---|
| `clude_web/__init__.py` | `create_app`, the factory: config, store, blueprints, the gate. |
| `clude_web/config.py` | Secret, store URI and cookie policy. Imports no Flask. |
| `clude_web/auth.py` | The login blueprint, `require_session`, CSRF, `RateLimit`. |
| `clude_web/users.py` | Accounts as `users/<name>.json` documents. |
| `clude_web/views.py` | The app's own pages. A placeholder until step 5. |
| `clude_web/templates/` | Jinja templates; `base.html` is the shell. |
| `clude_web/static/style.css` | One stylesheet, every colour a variable. |

The stylesheet is plain on purpose. Typography, ornament, the decorated
board and its logo, and motion are Phase 9; what is there now is the colour
system those screens will inherit, declared once for light and once for
dark, so Phase 9 restyles the app by editing that block rather than hunting
through templates.

## Tests

`tests/test_web.py` runs Flask's test client against a `LocalStore` in a
temp dir, with no network and no real store. `TESTING` makes the app sign
its cookies with an ephemeral key, so a test never depends on the
developer's `FLASK_SECRET_KEY` and never signs anything with the real one.
