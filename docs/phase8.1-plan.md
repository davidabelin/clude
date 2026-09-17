# Phase 8.1 Plan: a web scaffold, locally and on Cloud Run

Status: **confirmed 2026-09-17**; section 6 records what David decided.
8.1a is being built; 8.1b waits on a separate yes for the one-time
Google Cloud changes (3.6).

## 1. Context

Phases 1-7 built the game headless: the engine, six belief methods,
personalities, the LLM wrapper and logbooks, all driven from
`scripts/clude_cli.py`. Phase 8.0 re-measures the glossary on the
Classic board. Phase 8.1 puts the first screens in front of the game;
8.2 adds human players, 8.3 the rest of chat, Phase 9 the in-depth UX
work, Phase 10 the clean-up, and then clude is released to family and
friends as version 1.0.0 and planned in versions from then on.

8.1 has two halves (David, 2026-09-16):

- **8.1a, local:** a Flask app on Orbit with the scaffold screens,
  reading real records and running real (headless) games.
- **8.1b, cloud:** the same app on Cloud Run behind an app login.

"Scaffold" means the screens exist, work and read the real data, and
are plain. Typography, ornament, the decorated board with its logo,
motion and the six-seat layout polish are Phase 9.

## 2. What the code dictates

- **`engine.run_game` is one blocking call** that asks each seat's
  player object for four decisions: `choose_movement`,
  `choose_suggestion` and `choose_accusation` on its own turn, and
  `choose_card_to_show` from inside `resolve_suggestion`, on someone
  else's turn. A web request cannot hold a whole game, and a human seat
  (8.2) has to stop it at any of those four points, including the
  off-turn one.
- **Games are deterministic per seed**, and per model response, which
  `RecordingBackend` / `ReplayBackend` already capture. So a game in
  progress is fully described by its setup plus the answers that did
  not come from a headless character. That is its durable state; any
  live game object in memory is only a cache.
- **Replay has most of what it needs.** `clude_training.replay` rebuilds
  a `GameState` and any seat's masked view from a record;
  `trace.belief_trace` gives each agent's belief after every suggestion
  `k`; the floor mask gives what each seat has proven. Two gaps: beliefs
  are indexed by suggestion while tokens move per event, so positions
  per event need a small fold (`state_from_record` folds only to the
  end); and a trace calls `select_action` on a fresh agent and never
  `observe`, so for White and Green, who learn from what they see, the
  replayed bar is a stateless reading of the evidence rather than
  exactly what they believed live. That is a limitation to label on the
  screen, not one to fix in 8.1.
- **Traces are too slow to compute per request.** Plum's belief takes
  about 0.7 s a call mid-game (glossary, "Tuned presets on the grid");
  one seat of a 30-suggestion game is about 20 s, a whole six-seat table
  about a minute. Each game's trace is computed once and stored as a
  document beside its record.
- **The store already holds documents** (`LocalStore`, `GcsStore`, the
  logbooks use them), so users, sessions and trace caches need no new
  storage.
- **Google Cloud as found on 2026-09-17**, after David's changes (the
  2026-09-16 reading is below it, since four of its six points moved):
  Orbit's active gcloud configuration is now `clude-game`, with
  `clude-sa@clude-game.iam.gserviceaccount.com` as the active account,
  so commands no longer need to name `--account` and `--project`.
  `clude-sa` now holds **`roles/owner`** on the project, as does
  David's account, so no bucket or secret grant is outstanding. Cloud
  Run, Artifact Registry, Secret Manager and Container Registry are
  **enabled**; **Cloud Build is not**, and neither is the IAM API --
  the first blocks `gcloud run deploy --source .`, the second already
  fails `gcloud iam service-accounts list`. No Cloud Run service, no
  secret and no Artifact Registry repository exists yet. The bucket
  `gs://clude-game-data` is US-CENTRAL1 STANDARD with uniform
  bucket-level access on and public access prevention enforced; it
  holds 292 KB under `arena/` (the ring-era `arena-tuned-24`) and
  `test/`, not the `data/llm` runs. Docker is still not installed on
  Orbit; gcloud is 563.0.0.

  On 2026-09-16 the active configuration was zenbot's, `clude-sa` had
  no project role recorded here, and none of Cloud Run, Cloud Build,
  Artifact Registry or Secret Manager was enabled.

## 3. Design

### 3.1 Package

`clude_web/`, the name `docs/architecture.md` has reserved since Phase
1: a Flask app factory `create_app(config)`, blueprints for auth,
replay and games, Jinja templates, one stylesheet with its colours as
CSS variables (light and dark), and a few small vanilla JavaScript
files. No front-end framework and no build step. `clude_web` imports
every other package; nothing imports it.

### 3.2 Screens (8.1a)

1. **Login.** Name and password; nothing else is reachable without it.
2. **Lobby.** The stored runs and their games (run id, table, winner,
   turns), and a form for a new game: roster from the six characters
   and `floor`, table size 3-6, seed. Headless seats only (section 3.6).
3. **Replay, Direction A ("Scrubber").** From `docs/ux/replay/`, the
   sketch already marked as leading, chosen because comparing the
   methods at the same moment is the point of the replay. The grid
   board with the tokens where they stood; one block per seat with its
   name, method and cards placed, and three strips (suspect, weapon,
   room) in which a proven card is solid, a still-plausible card is
   pale and as wide as that seat's belief, and a red mark shows the
   truth; the line for the current step (the move, the suggestion, who
   showed what, and any table talk); a scrubber with step buttons and
   the arrow keys. Board left and seats in two columns on a wide
   screen; everything stacked on a phone, as in the sketch. The sketch
   drew the ring; this uses the grid, generated as SVG from
   `clude_core.board`.
4. **Watch.** A headless game being played, in Direction D's order
   (the board leads, the seats' bars follow, the last suggestion
   spoken), with "next turn" and "play to the end". Hands and envelope
   stay hidden until the game is over; then the game opens as a replay.
   The same parts as the replay screen, so the two share their code.

### 3.3 The engine seam

The loop becomes resumable without threads:

- `clude_core.engine` gains a generator form of the game loop. Wherever
  it asks a seat for a decision it goes through one helper: a seat with
  a player object is asked directly, as now; a seat marked external
  makes the generator yield a `DecisionRequest` (seat, kind,
  observation, the choices) and wait for the answer to be sent in. The
  generator also yields a marker at the end of each turn.
  `resolve_suggestion` is split the same way so the refuter's choice
  can be external too, and keeps its current signature for its callers.
- `run_game` becomes a driver over that generator with no external
  seats, so it never pauses. Every golden in `tests/test_character.py`
  and every determinism test then proves the refactor changed nothing.
- A web game is a `GameSession`: setup, seed, and the list of external
  answers so far, saved to the store after every request. The live
  generator is kept in memory; on a cold instance the session is
  rebuilt by feeding a fresh generator the saved answers, which the
  determinism makes exact. In 8.1 there are no external seats, so a
  watched game's saved state is just its setup and how many turns it
  has played, and "next turn" runs to the next end-of-turn marker.

If the day runs short, this is the part to move to the start of 8.2:
Watch can instead run the whole game at once and reveal it turn by
turn, at the price of a 10-60 s wait before the first turn.

### 3.4 Login

David chose an app login and said to use the credentials in
`clude-game-sa.json`. My reading, to confirm:

- **Accounts are the app's own.** A name and a password hashed with
  Werkzeug's `generate_password_hash` (Flask's own dependency), stored
  as `users/<name>` documents in the store. Accounts are made from the
  CLI, never a sign-up page: `clude_cli.py users add NAME` prompts for
  the password (it is never on the command line), plus `users list` and
  `users remove`.
- **A service account is how the app reaches the store.** Locally from
  the `clude-sa` key file, exactly as `clude_storage` finds it today.
  On Cloud Run the service runs as its own identity, so no key file
  ever leaves Orbit or is copied into an image. That identity is
  **`clude-run@clude-game`**, not `clude-sa` (David, 2026-09-17, 3.6).
- **Sessions:** a signed Flask cookie (`Secure`, `HttpOnly`,
  `SameSite=Lax`) whose secret comes from Secret Manager in the cloud
  and from an environment variable locally; a CSRF token on every form;
  a few login attempts a minute per name. Every route except the login
  page requires a session.
- The login name is the player's identity. 8.2 writes it into
  `SeatRecord.label`, so a human's logbook follows the name
  (`docs/architecture.md`, "Seats and player identity").

### 3.5 Records in the cloud

The deployed app reads `gs://clude-game-data`. 8.1b uploads the
grid-era runs from `data/llm` with a new `store copy` subcommand, so
the cloud's replay list matches Orbit's, and the rebuilt logbooks with
them (David, 2026-09-17), so the cloud store is a full mirror rather
than records alone. A trace is computed the first time its game is
opened and saved as `traces/<run_id>/<index>` beside the record.

**Measured on 2026-09-17**, correcting this section's earlier "a few
megabytes": `data/llm` is 67 MB in all -- `games/` 47 MB, of which the
grid-era runs are **30 MB** across 51 runs, plus `logbooks/` at 18 MB
(Mustard's rebuilt tree is most of it) and `runs/` under 1 MB. So the
upload is about **48 MB**, negligible to store but several thousand
small JSON objects, which `store copy` must move in batches rather
than one blocking request each.

### 3.6 Cloud Run (8.1b)

- **Container:** a `Dockerfile` on `python:3.14-slim` running gunicorn
  with one worker and a few threads and a 300 s timeout; `.gcloudignore`
  and `.dockerignore` exclude `.venv`, `data/`, `legacy/`, `tests/`,
  `docs/`, `.env` and `clude-game-sa.json`. With no Docker on Orbit,
  `gcloud run deploy --source .` builds it on Cloud Build.
- **Service:** `clude` in us-central1 (the bucket's region),
  `--min-instances 0` so idle time is free, `--max-instances 1` so the
  in-memory session cache and the login rate limit are simply correct,
  request-based CPU billing. Orbit's active configuration is now
  `clude-game`'s, so gcloud commands no longer need `--account` and
  `--project` spelled out (3.2 of section 2).
- **A narrow identity for the service** (David, 2026-09-17). `clude-sa`
  now holds `roles/owner` on `clude-game`, and the service is
  deliberately reachable without Cloud Run authentication, so running
  the web app as `clude-sa` would put project-owner credentials behind
  an internet-facing login page, with BigQuery and Pub/Sub in reach of
  the same project. Instead 8.1b creates `clude-run@clude-game` holding
  only `roles/storage.objectAdmin` on `gs://clude-game-data` and
  `roles/secretmanager.secretAccessor` on the session secret, and the
  service runs as that. `clude-sa` stays the local and administrative
  identity.
- **Reachability:** the service is `--allow-unauthenticated` at the
  Cloud Run layer, because the app login is the gate. That is what
  choosing an app login means: anyone can load the login page, and
  nothing else.
- **No model on the web in 8.1.** The service gets no Anthropic key, so
  nothing reachable from the URL can spend API money. LLM seats on the
  web come with 8.2 or 8.3, with a per-game spend cap.
- **One-time project changes**, each listed and run only after David's
  yes, and narrowed on 2026-09-17 to what his own changes left
  outstanding: enable the **Cloud Build** and **IAM** APIs (Cloud Run,
  Artifact Registry and Secret Manager are already on); create
  `clude-run@clude-game` and grant it the two roles in the bullet
  above; create the session secret; allow David's account to deploy as
  `clude-run`. At family traffic the running service should stay inside
  Cloud Run's free tier (`docs/architecture.md`, "Deployment cost");
  builds and stored images may cost cents.

### 3.7 Tests

- **Engine:** every existing golden and determinism test runs through
  the new driver unchanged. New: answers recorded from a `run_game`
  fed back to a generator whose seats are all external reproduce its
  event log exactly, including a refutation on another seat's turn.
- **Web**, with Flask's test client and a `LocalStore` in a temp dir,
  no network: every route but login redirects without a session; a
  wrong password fails; `users add` hashes the password; the board SVG
  has nine rooms, 17 doors and six start squares; replay data for a
  short stored game has one position frame per event and one belief
  frame per suggestion; a watched session advances a turn at a time and
  a rebuilt session matches the live one.

## 4. Sub-phases

8.1a, local:

1. The engine seam (3.3); goldens unchanged; suite green.
2. `clude_web` skeleton: app factory, config, login and `users` CLI,
   base template, stylesheet.
3. The board as SVG from the map; replay data (positions per event,
   the trace cached per game, what each seat's floor has proven, the
   truth).
4. The replay screen.
5. The lobby and the watch screen.

8.1b, cloud:

6. `Dockerfile`, ignore files, gunicorn settings, `store copy`. The
   service must set `CLUDE_WEB_HTTPS=1`, or the session cookie is not
   marked `Secure` (step 2 of the "as implemented" section below).
7. The one-time Google Cloud changes, after a yes.
8. Upload the grid-era records; deploy; check on the URL that the login
   gates everything, a replay plays and a watched game finishes.
9. Documentation: `docs/web.md` (running locally, users, deploying),
   `docs/architecture.md`, `CLAUDE.md`, and this plan's "as implemented".

## 5. Files

- **New:** `clude_web/` (`__init__.py` with `create_app`, `auth.py`,
  `users.py`, `board_svg.py`, `replay_data.py`, `sessions.py`,
  `views.py`, `templates/`, `static/`), `Dockerfile`, `.gcloudignore`,
  `.dockerignore`, `docs/web.md`, `tests/test_engine_steps.py`,
  `tests/test_web.py`.
- **Changed:** `clude_core/engine.py`, `scripts/clude_cli.py` (`users`,
  `store copy`), `requirements.txt` (`flask`, `gunicorn`), `README.md`,
  `docs/architecture.md`, `docs/cli.md`, `CLAUDE.md`.

## 6. Decisions

Taken by David on 2026-09-16:

- 8.1a is the local Flask app and its screens; 8.1b is the deploy.
- An app login, not a Google-account allowlist.
- The replay direction is mine to choose: A for replay, D's order for
  watching (3.2).

Taken by David on 2026-09-17, closing the five points this section
asked:

1. **The login as read in 3.4:** the app's own accounts, made from the
   CLI only, passwords hashed with Werkzeug, stored as `users/<name>`
   documents. The login name is the player identity 8.2 writes into
   `SeatRecord.label`.
2. **The engine seam is built now**, as step 1 of 8.1a, not moved to
   8.2. It is the only change that touches a working system under the
   goldens' guard, human seats in 8.2 cannot be built without it, and
   the fallback in 3.3 would have had Watch rewritten in 8.2 anyway.
3. **No LLM seats on the web in 8.1 (3.6):** the service gets no
   Anthropic key, so nothing reachable from the URL can spend API
   money.
4. **The one-time Google Cloud changes (3.6)**, with the service
   reachable and the app login as its only gate -- but the service runs
   as a new, narrow `clude-run@clude-game` rather than as the
   now-`roles/owner` `clude-sa`. Each change is still run only after a
   separate yes when 8.1b starts.
5. **Upload the grid-era runs and the logbooks** (3.5), about 48 MB, so
   the cloud store mirrors Orbit's rather than holding records alone.

## 7. Out of scope

Human seats (8.2), though the seam is built for them; off-turn chat
(8.3); LLM seats on the web; the decorated board, logo, typography and
motion (Phase 9); fixing trace fidelity for the learning methods; any
change to a method, a dial or `movement_scores`.

## 8. As implemented

Written as the work lands. Where this section and the plan above
disagree, this section is what was built.

### Step 1, the engine seam (2026-09-17)

Built as designed in 3.3, with one addition the design missed.

`clude_core.engine.game_steps` is the turn loop as a generator, and
`run_game` is now a three-line driver over it (`_drive`) with no
external seats. `resolve_suggestion_steps` stands in the same relation
to `resolve_suggestion`. Both public functions keep their exact
signatures, so not one caller changed -- `arena`, `self_play`,
`clude_cli`, and the tests all call what they always did. The proof the
refactor changed nothing is the existing suite: every golden fingerprint
in `tests/test_character.py` and every determinism test passes
untouched, and the suite went from 257 passed / 2 skipped to **269
passed / 2 skipped** purely by adding `tests/test_engine_steps.py`.

One helper, `_ask`, is the single place a seat is asked anything. It is
a generator reached with `yield from`, so for a seat with a player
object it yields nothing at all -- which is exactly why `run_game` never
pauses.

**The addition: `LiveGame`.** The plan had the generator yield only
`DecisionRequest` and `TurnComplete`, and that is not enough: a driver
holding a paused generator had no way to see the board or the event log,
which even 8.1's Watch screen needs before any human seat exists.
`game_steps` now yields `LiveGame(state, events)` once before the first
turn, carrying the generator's own objects. Keeping it separate from
`DecisionRequest`, which carries only one seat's masked view, keeps the
referee's view and the player's view distinct -- worth the extra yield
type on a codebase whose reveal-integrity rule is a stated invariant.

**External answers are checked** before they touch the game
(`_checked`), which the plan did not specify: a movement must be one of
the choices offered and a refutation one of the cards that seat actually
holds, since a seat answering over a network is the first thing in the
project able to break reveal integrity by accident. Suggestions and
accusations need only name real cards.

**`TurnComplete` lands after the `GameOverEvent`** on the turn that ends
a game, so a driver slicing turns by marker never drops the ending.

**A note for whoever writes the Watch driver:** `RandomBot` draws its
choices from the engine RNG, so a table of external seats -- which never
calls a player object -- rolls different dice and diverges. This is not
a flaw in the seam; it is the `PlayerProtocol` rule that a player with
its own RNG must leave the engine's alone, which `Character` obeys and
`RandomBot` does not. `tests/test_engine_steps.py` therefore records its
sample games with a deterministic `Fixed` seat, and says so.

Files: `clude_core/engine.py` changed; `tests/test_engine_steps.py`
added (12 tests); `docs/architecture.md` gained "Resumable:
`game_steps`" under the engine seam.

### Step 2, the `clude_web` skeleton (2026-09-17)

The app factory, the login gate, accounts and their CLI, the base
template and the stylesheet. Built as 3.1 and 3.4 describe, with the
decisions below where the plan left a choice open.

**The gate is enforced once, not per route.** `auth.require_session` is
registered as an app-wide `before_request` in `create_app`, and a view is
reachable without a session only if it is marked `@auth.public` -- which
only the login page is. A route added in step 3 is therefore private the
day it appears rather than the day someone remembers a decorator, and
`tests/test_web.py` walks the app's whole url map asserting that every
route but the login redirects, so the test covers routes that do not
exist yet. This matters more here than in most apps: 3.6 makes the Cloud
Run service reachable by anyone on purpose, so this gate is the entire
security boundary.

**Accounts** are `users/<name>.json` documents holding a Werkzeug hash
(scrypt), made only by `clude_cli.py users add|list|passwd|remove`. The
password is prompted for twice and never taken as an argument, so it
stays out of shell history. `passwd` is not in the plan; without it a
forgotten password meant deleting and recreating an account, and
`set_password` was a few lines. A name is matched case-insensitively and
kept as typed, since it is the player identity 8.2 writes into
`SeatRecord.label`, and `authenticate` hashes against a dummy when there
is no such account so that a wrong name and a wrong password take the
same time -- the login page is not a way to find out who has an account.

**`users` defaults to `data/llm`, not the CLI's `data`.** They are
different stores, and an account written to the wrong one is invisible to
the app with no error to explain it. The constant is duplicated in
`clude_cli.py` rather than imported, so the CLI still runs without Flask
installed, and a test pins the two equal.

**The session secret** comes from `FLASK_SECRET_KEY` in the environment,
falling back to reading the gitignored `.env` for that one variable
(David, 2026-09-17: the key is already there). `clude_web.config` is the
only thing in clude that reads `.env`, and the rest of the project's "you
must export it first" rule is unchanged. With no secret anywhere the app
refuses to start rather than generating one, which would sign everyone
out on every restart and hide the mistake.

**One thing 8.1b must not forget:** the session cookie is `Secure` only
when `CLUDE_WEB_HTTPS=1`. It is off locally, because a `Secure` cookie
never comes back over plain http and the login would appear to silently
fail. The Cloud Run deploy has to set it, and step 6's checklist now
says so.

Verified beyond the suite by running the app and driving it over HTTP:
an unauthenticated `/` redirects to the login; a wrong password answers
401 with the same message a wrong name gets; a POST with no CSRF token
answers 400; the right password lands on the index reading the real
store; the cookie comes back `HttpOnly`; and sign-out returns to the
login page.

Files: `clude_web/` added (`__init__.py`, `config.py`, `auth.py`,
`users.py`, `views.py`, `templates/`, `static/style.css`);
`tests/test_web.py` added (25 tests); `scripts/clude_cli.py` gained
`users`; `requirements.txt` gained `flask`; `docs/web.md` added;
`docs/cli.md`, `docs/architecture.md` and `README.md` updated. Suite 269
-> 294 passed, 2 skipped.
