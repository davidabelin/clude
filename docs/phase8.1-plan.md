# Phase 8.1 Plan: a web scaffold, locally and on Cloud Run

Status: **proposed 2026-09-16, waiting on David's confirmation** of the
five points in section 6. Nothing in it is built.

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
- **Google Cloud as found on 2026-09-16:** Orbit's active gcloud
  configuration is zenbot's, but David's account reaches `clude-game`.
  The service account is `clude-sa@clude-game.iam.gserviceaccount.com`;
  the bucket `gs://clude-game-data` is in US-CENTRAL1 and holds `arena/`
  and `test/`, not the `data/llm` runs. Cloud Run, Cloud Build, Artifact
  Registry and Secret Manager are not enabled. Docker is not installed
  on Orbit; gcloud 563 is.

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
- **The service account is how the app reaches the store.** Locally
  from the key file, exactly as `clude_storage` finds it today. On
  Cloud Run the service runs *as* `clude-sa`, so it has the same
  identity and permissions while the key file never leaves Orbit and is
  never copied into an image.
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
grid-era runs from `data/llm` (a few megabytes) with a new `store copy`
subcommand, so the cloud's replay list matches Orbit's. A trace is
computed the first time its game is opened and saved as
`traces/<run_id>/<index>` beside the record.

### 3.6 Cloud Run (8.1b)

- **Container:** a `Dockerfile` on `python:3.14-slim` running gunicorn
  with one worker and a few threads and a 300 s timeout; `.gcloudignore`
  and `.dockerignore` exclude `.venv`, `data/`, `legacy/`, `tests/`,
  `docs/`, `.env` and `clude-game-sa.json`. With no Docker on Orbit,
  `gcloud run deploy --source .` builds it on Cloud Build.
- **Service:** `clude` in us-central1 (the bucket's region), running as
  `clude-sa`, `--min-instances 0` so idle time is free,
  `--max-instances 1` so the in-memory session cache and the login rate
  limit are simply correct, request-based CPU billing. Every gcloud
  command names `--account davidabelin96@gmail.com --project clude-game`,
  since the active configuration on Orbit belongs to zenbot.
- **Reachability:** the service is `--allow-unauthenticated` at the
  Cloud Run layer, because the app login is the gate. That is what
  choosing an app login means: anyone can load the login page, and
  nothing else.
- **No model on the web in 8.1.** The service gets no Anthropic key, so
  nothing reachable from the URL can spend API money. LLM seats on the
  web come with 8.2 or 8.3, with a per-game spend cap.
- **One-time project changes**, each listed and run only after David's
  yes: enable the Cloud Run, Cloud Build, Artifact Registry and Secret
  Manager APIs; create the session secret; grant `clude-sa` access to
  that secret and to the bucket's objects (if it lacks it); allow
  David's account to deploy as `clude-sa`. At family traffic the
  running service should stay inside Cloud Run's free tier
  (`docs/architecture.md`, "Deployment cost"); builds and stored images
  may cost cents.

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

6. `Dockerfile`, ignore files, gunicorn settings, `store copy`.
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

To confirm before code:

1. **The login as read in 3.4:** the app's own accounts made from the
   CLI, with the service account as the app's identity for the store
   and Cloud Run running as `clude-sa` rather than shipping the key.
2. **The engine seam as a generator (3.3)**, which changes
   `clude_core/engine.py` under the goldens' guard, and whether it is
   built in 8.1a or moved to 8.2.
3. **No LLM seats on the web in 8.1 (3.6).**
4. **The one-time Google Cloud changes (3.6)**, and the service being
   reachable with the app login as its only gate.
5. **Upload every grid-era run** for replay in the cloud (3.5), rather
   than a chosen few.

## 7. Out of scope

Human seats (8.2), though the seam is built for them; off-turn chat
(8.3); LLM seats on the web; the decorated board, logo, typography and
motion (Phase 9); fixing trace fidelity for the learning methods; any
change to a method, a dial or `movement_scores`.
