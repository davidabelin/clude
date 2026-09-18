# Phase 8.1 Plan: a web scaffold, locally and on Cloud Run

Status: **confirmed 2026-09-17**; section 6 records what David decided.
**8.1a is built** (steps 1-5; section 8 records how). 8.1b, steps 6-9,
waits on a separate yes for the one-time Google Cloud changes (3.6).

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
- **Traces are too slow to compute per request.** Each game's trace is
  computed once and stored as a document beside its record.

  **Measured on 2026-09-17**, correcting this section's estimate, which
  was about five times pessimistic: a 4-seat, 28-suggestion grid game
  takes **8.7 s**, a 3-seat game with Plum in it **11.9 s**, and a
  3-seat game without him 0.8 s. Served end to end, the first open of a
  replay is 10.4 s and every open after it is 0.04 s. So the estimate
  of "about a minute for six seats" was wrong, but the conclusion was
  not: ten seconds a request is still far too slow, and the cache is
  what makes the screen usable. The old estimate read: Plum's belief is
  about 0.7 s a call mid-game, so one seat of a 30-suggestion game is
  about 20 s and a six-seat table about a minute.
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
-> 294 passed, 2 skipped, and 303 after the amendment below.

#### Step 2 amended, 2026-09-17: convenience over secrecy

David's call, after the gate was working, and a departure from 3.4 as
written: clude is a game for family and friends, and friction costs more
than secrecy buys (CLAUDE.md, "Settled decisions"; `docs/web.md`).

- A new account's password is `password`. `users add NAME` no longer
  prompts at all, though a password can still be given as a second
  argument.
- Any non-empty password is accepted, one character included. Empty is
  still refused: it would leave the login form's own `required` as the
  only thing in the way, which is a surprise rather than a choice.
- The CLI prints passwords instead of hiding them, and the app's change
  form shows the password as it is typed.
- A player is offered a change **once**, after their first login. The
  gate holds them on `/password` until they either type a new one or
  keep the one they have; either answer sets `password_prompted` on the
  account and is never asked again. After that only `users passwd`
  changes a password, which means asking David. Accounts made before
  this (document version 1) have no flag and so read as never offered,
  which is the right answer for them.
- Usernames were already case-insensitive -- `normalise` has lowercased
  the key since the first commit of step 2 -- so David's request there
  needed no change, only confirming.

Not traded away, and worth keeping in view: passwords are still stored
only as Werkzeug hashes, the login still gates every route, CSRF and the
per-name rate limit still stand, and 8.1b still runs the service as the
narrow `clude-run` identity rather than the owner `clude-sa`, so the
damage ceiling is the game store. The risk I raised and David knowingly
accepted is that the Cloud Run service is reachable by anyone and
`password` is guessable.

Files: `clude_web/users.py` (`DEFAULT_PASSWORD`, `needs_password_offer`,
`mark_password_prompted`, document version 2), `clude_web/auth.py` (the
`/password` route and the gate's redirect to it),
`clude_web/templates/password.html`, `scripts/clude_cli.py` (no prompt,
optional password argument), `tests/test_web.py` (34 tests now),
`docs/web.md`, `docs/cli.md`, `CLAUDE.md`.

### Step 3, the board and the replay data (2026-09-17)

Two pure modules, neither importing Flask, so both are testable and
renderable on their own.

**`clude_web/board_svg.py`** draws the Classic grid from
`clude_core.board` and nothing else: the rooms, corridor, cellar, doors
and start squares all come from `BOARD_MAP` and `DOORS`. That is the
drift worth designing out -- a replay showing a token where the rules
forbid is worse than no picture -- and the tests check the drawing
against the board rather than against a stored copy of itself.

- Room outlines are drawn as one line per cell edge that borders
  something else, minus the edges a door opens through. Cheaper than
  unioning cells into a polygon and it gives the same picture: a crisp
  wall with a gap at every doorway, and a test that asserts no door is
  also walled off.
- No colour is set anywhere in the module. Every shape carries a class
  and `static/style.css` colours it in both themes, which is what lets
  Phase 9 restyle the board without touching the generator. A test walks
  the generated markup and fails on any class with no rule.
- Tokens sharing a room are fanned out rather than stacked; a room's
  centre is the mean of its cells, and a test checks that point lands
  inside every one of the nine rooms.

**`clude_web/replay_data.py`** is split by cost, which is the only thing
that matters here:

- `event_frames` folds the event log once, giving the board after every
  event and the line describing it. Cheap, so it runs per request. It
  folds exactly as `state_from_record` does -- including dragging a
  named suspect's token into the room, which the engine does without a
  move event of its own -- and a test pins its last frame to
  `state_from_record`'s result so the scrubber's end and the stored game
  cannot disagree.
- `trace_document` asks each seat's own method what it believed after
  every suggestion, and is far too slow for a request, so `cached_trace`
  computes it once and writes it to `traces/<run_id>/<index>.json`
  beside the record. A document from an older `TRACE_VERSION`, or built
  with a different `every`, is rebuilt rather than trusted.
- Each frame carries what that seat's floor has **proven**, not what its
  method guesses: the solid part of the two-tone bar.

**Two things the code taught us, both now covered by tests.**

1. `mask.holder_of` returns a seat index *or* the string `"envelope"`.
   A card proven to be the envelope's is the strongest thing a seat can
   know and a different statement from "nobody has shown it", so the
   screen has to be able to draw it. My first test wrongly assumed every
   holder was a seat.
2. A suggestion can name a suspect with no token at the table -- at
   three seats, most of them. `event_frames` moves only suspects in
   play, and a test asserts the frames never invent a position for an
   absent one.

A limitation to show on the screen rather than hide, carried in the
document as `limitation`: a trace calls `select_action` on a fresh agent
and never `observe`, so White's and Green's bars are a stateless reading
of the evidence rather than what they believed live. Out of scope to fix
in 8.1 (section 7).

Files: `clude_web/board_svg.py` and `clude_web/replay_data.py` added,
`clude_web/static/style.css` gained the board block,
`tests/test_replay_screen.py` added (23 tests). Suite 303 -> 326 passed,
2 skipped.

### Step 4, the replay screen (2026-09-17)

Direction A ("Scrubber") as 3.2 describes it: the grid board with the
tokens where they stood, a block per seat with its method and cards, the
line for the current step, and a scrubber with buttons and the arrow
keys.

**The whole game goes to the page once.** The scrubber moves per event,
and a request per step would be both slow and pointless, so
`replay_data.screen_payload` builds one JSON object and
`static/replay.js` redraws from it. A real 4-seat game is 148 KB served,
which is nothing, and stepping is instant.

- Token positions are sent as SVG coordinates worked out server-side,
  not as rooms and squares. Mapping them in JavaScript would put the
  board's geometry in a second place, and keeping the drawing and the
  rules together is the whole reason the board is generated from
  `clude_core.board`. It is why `replay_data` imports `board_svg`.
- The board is rendered once with every token at its start square, so
  the circles exist in the document; a step moves them rather than
  redrawing 828 elements.

**Reading a bar.** Each seat gets three strips, and each row is in one
of three states, which is a little richer than the plan's two: a card
proven to be the **envelope's** is solid and full, the strongest thing a
seat can know; a card proven to sit in someone's **hand** is greyed and
struck through, settled and out; anything still **open** is a pale bar as
wide as that seat's own belief. A red mark shows the truth. The
three-way split follows from `holder_of` returning a seat *or*
`"envelope"` (step 3), and collapsing it to two would have thrown away
the distinction between "I have proved this is the answer" and "I think
this is likely".

**One hole found and closed.** The payload sits in a `<script>` block
and a replay carries table talk written by a model, which is text from
outside the app. A `</script>` in a remark would have closed the tag and
run whatever followed. `views.embed_json` escapes `<` as `<`, which
JSON parses identically, and a test feeds a hostile remark through the
whole screen to prove the block stays one document.

**Wording.** Suggestion lines are written here rather than reused from
`clude_agents.explain.describe_suggestion`: that renders
``White/Rope/Lounge -- Scarlett showed White``, which is right for a
terminal column and wrong under a board, where the rest of the lines are
prose. Same facts, different audience.

`index` grew a stopgap list of stored games so a replay is reachable
before the lobby exists; step 5 replaces it.

Verified by serving it: sign in, open a replay, 9 rooms, 17 doors, 4
tokens, 4 seat blocks, 84 bar rows, an 81-step scrubber, both static
files served. The payload has all four tokens ending somewhere new
across 56 distinct board positions, and at the last step Scarlett has
proven all 21 cards -- the three envelope cards among them, with belief
1.0 on the Study, which is the truth. **Not** verified: how it actually
looks. Orbit has no browser automation and no SVG rasteriser, so nobody
has seen it rendered yet.

Files: `clude_web/views.py` (the replay route, `embed_json`, the stopgap
index), `clude_web/templates/replay.html`, `clude_web/static/replay.js`,
`clude_web/replay_data.py` (`screen_payload`, `suggestion_line`),
`clude_web/templates/index.html` and `static/style.css`;
`tests/test_web.py` and `tests/test_replay_screen.py` grew to 40 and 24.
Suite 326 -> 333 passed, 2 skipped.

### Step 4 amended, 2026-09-17: the screen gets looked at

Step 4 shipped with "not verified: how it looks", because Orbit had no
way to render a page. David's answer was to fix that rather than accept
it, and it was the right call: **three real bugs were invisible to 333
passing tests and obvious in the first screenshot.**

**Playwright**, not an SVG rasteriser. `board_svg` deliberately sets no
colour, leaving all of it to `style.css`, so rasterising the SVG alone
gives an unstyled blank. Only a browser applies the stylesheet, runs
`replay.js`, and honours dark mode and a phone width. It is optional --
`scripts/clude_shots.py` and `tests/test_browser.py` are the only things
that need it, and the second is gated on `CLUDE_WEB_BROWSER=1` like the
tests that need credentials.

**What the screenshots showed.**

1. **The corridor was invisible.** `--board-corridor` sat within a
   hair's breadth of the panel white behind it, so the board read as
   nine islands floating in nothing, with no visible space to walk. The
   fix is a `board-void` rect behind everything, a corridor darker than
   the rooms rather than lighter, and a faint grid stroke so the squares
   are countable, as they are on the real board.
2. **The cellar was a near-black slab** dominating the middle of the
   board. It is now a muted block carrying the wordmark, which is where
   Phase 9's logo goes.
3. **Room labels sat under the tokens** that gather in the middle of a
   room -- "Dining" and "Lounge" were both unreadable. Labels now anchor
   above the centre (`label_anchor`), with a halo behind them as well.
4. **Start squares were drawn as discs**, so they read as extra tokens:
   a four-handed game looked like it had seven pieces. They are squares
   now -- a start square is a place, and tokens are the round things.
5. `Lead_Pipe` was showing its underscore.

**And one real bug, found by asking the browser where the tokens
actually were.** `_fan` spread tokens sharing a room so they do not
stack, but it lived inside the drawing, and `screen_payload` computed
its own positions without it. So the server-rendered board fanned and
the live page did not: the moment the scrubber moved, two characters in
one room sat exactly on top of each other. Both now go through one
`board_svg.token_points`, which is the only thing that decides where a
token goes, and `test_tokens_in_one_room_never_stack` fails if they ever
diverge again.

**A false alarm worth recording.** A screenshot appeared to show a token
somewhere the step line contradicted, while the browser test read the
right coordinates. Both were true: a CSS `transition` on `cx`/`cy`,
added in passing, animates the *paint* while the attribute already
holds the new value, so the screenshot caught tokens mid-flight. The
transition is gone -- motion is Phase 9 (section 1) and it was never in
scope -- and `clude_shots.py` waits before each shot regardless.

`tests/test_browser.py` adds 9 tests that markup cannot reach: every
token where the payload says, no stacking, the arrow keys, Home and End,
the step line following the scrubber, a proven envelope row solid and
full, and the board being painted at all -- that last one because with
no colour in the SVG, a stylesheet that stopped reaching it would render
a blank screen while every other test still passed.

Files: `scripts/clude_shots.py` and `tests/test_browser.py` added;
`clude_web/board_svg.py` (`token_points`, `label_anchor`, the void rect,
the cellar wordmark, square start markers), `static/style.css` (the board
palette reworked), `templates/replay.html`, `clude_web/replay_data.py`,
`requirements.txt`, `CLAUDE.md` and `docs/web.md` updated.

### Step 5, the lobby and the Watch screen (2026-09-17)

This closes 8.1a. Built as 3.2 and 3.3 describe, with one design
question the plan did not see and several smaller departures.

**The plan asked for two things that contradict each other.** 3.2 says
Watch shows "the seats' bars" *and* that "hands and envelope stay hidden
until the game is over". The replay's per-card bars cannot do both:
every seat's own hand is proven to that seat from the first turn, and
all the hands together are exactly the eighteen cards that are not the
answer. Show each seat card by card and the envelope is on screen before
anyone moves. Direction D, which 3.2 names for Watch, had already drawn
the way out: compact bars -- "9/21" cards placed, three segments, "tap a
seat to open it". So a seat's block on Watch is cards placed (as a count
and as filled cells per category, which name no card) and how sure its
own method is of its best guess in each category. The hidden-hands rule
is the stronger requirement, so it won; "tap a seat to open it" is
deferred to Phase 9, where it would need its own answer to the same leak.

A refutation on Watch reads "Scarlett disproved it", never the card
shown -- all anyone but the two seats involved learns at a real table.
To make that impossible to get wrong in two places, the per-event
wording moved out of `event_frames` into `replay_data.describe_event`
with a `reveal` switch, and the replay and Watch both read from it.

**A watched game is `play`'s game.** Table-building lived in the CLI's
private `_play_game`, where the web app could not reach it, so it moved
to `clude_training.arena.headless_table` -- the CLI itself was left
untouched, and instead a test drives the CLI's own `_play_game` and pins
`headless_table`'s game to it for four rosters, one of them all six
characters at a six-seat table. A second test pins a game advanced one
turn at a time to the same event log. Both hold exactly.

**Surviving a cold start** is as 3.3 planned: `watch/<id>.json` holds
the setup and the turn count, and a game missing from memory is rebuilt
by replaying that many turns; a test rebuilds one in a fresh registry and
compares events, positions and readings. Belief readings come from fresh
agents reset with the game seed, never the agents playing, because a
reading consumes RNG in some methods and would otherwise change the rest
of the game; that also makes a reading a pure function of the seat, the
seed and its view, so the rebuilt game reads exactly as the live one.

**The turn that ends a game says so.** The generator only raises
`StopIteration` on the call *after* the last turn's marker, which would
have left one click that plays nothing. `WatchGame.advance` notices the
three endings (a correct accusation, the turn cap, everyone out) as the
marker arrives, and drains the generator, which in each case returns
without drawing a die or asking anyone anything.

**Smaller departures.**

- `sessions.py` in section 5 is `watch.py`: "session" already means the
  login cookie here.
- The lobby reads run summaries, not records: every summary already
  carries each game's seats, winner, turns and suggestions, so the lobby
  opens no record at all (51 runs in 0.3 s on Orbit). No cache was
  needed, though GCS in 8.1b will be slower and may want one.
- A game played here is saved to one run, `web`, whose summary is kept
  in the arena's shape so the lobby, `/runs/web` and `clude_cli.py store
  --run web` all read it with no special case. Saving is idempotent and
  the next index is chosen under a lock.
- "Play to the end" is one request of about 20 s with Plum or Green at
  the table, under a second without. Fine locally and well inside Cloud
  Run's 300 s timeout.

**What the screenshots caught this time.** Every suspect pip in the app
-- the coloured dot by each name, on the replay since step 4 and now the
lobby and Watch -- had been invisible all along: the `.suspect-*` rules
colour the board with `fill`, an SVG property an HTML span ignores. The
existing "every class is styled" test could not see it, because the
class *had* a rule, just the wrong property for a span. A browser test
now checks each pip's computed background. Also fixed from the shots:
the two Watch buttons sitting at different heights, and the lobby's
labels floating away from their controls.

**Test cost.** The first draft of `tests/test_web_watch.py` took 138 s
in parallel, because it played whole games with Plum and Green (7 s and
12 s a game against 0.8 s for Scarlett, Mustard and White). The tests
now use the fast three, with one capped all-six case that still makes
every character take a turn: 25 s for the file, and the suite is 357
passed, 13 skipped in about 2 min 20 s.

Files: `clude_training/arena.py` (`Table`, `headless_table`,
`seat_kind`); `clude_web/watch.py`; `clude_web/views.py` rewritten
(lobby, `/runs/<run_id>`, the four Watch routes); `clude_web/replay_data.py`
(`describe_event`, `reveal`); templates `lobby.html`, `run.html`,
`watch.html`, with the stopgap `index.html` removed; `static/style.css`;
`scripts/clude_shots.py` shoots the lobby, a run and Watch too;
`tests/test_web_watch.py` added (23), `tests/test_browser.py` grew to 11,
`tests/test_web.py` adjusted.
