# Phase 8 to completion: 8.0.4, 8.2 human players, 8.3 the rest of chat

Status: **closed 2026-09-19** (approved 2026-09-18; David's four
decisions are in section 9). Built on the 18th: 8.0.4, 8.2a, 8.2b and
8.2c; on the 19th: 8.2d, 8.3a, 8.3b and 8.3c, then the key deployed,
the live checks played and 8.3d's close (section 12). Section 12, "As
implemented", was written as each step landed; where it and the
sections above disagree, section 12 is what was built.

## 1. Context

Phase 8 is four parts (`docs/phase-plan.md`): 8.0 the re-measurement on
the Classic board, 8.1 the web scaffold and Cloud Run, 8.2 human players,
8.3 the rest of chat. 8.1 closed today; 8.0 is done except its one open
question. "Finish Phase 8" therefore means:

- **8.0.4, closing the parking question** (David, 2026-09-18: the scoring
  change, headless, first). `room_features` pays any room entered this
  turn `proximity = 1.0` whatever its envelope probability, so a secret
  passage into a cleared room scores 0.50 against 0.29 for walking toward
  a live one, the leash hides the walk, and Plum rides the loop (108 of
  148 wasted trips never put to the model; the headless character has
  the habit mildly; Mustard loops on the model too). Section 6.
- **8.2, human players.** A person signs in, takes a token beside the
  cludebots and plays a whole game from the browser: moves, suggests,
  shows a card when another seat's suggestion names one of theirs,
  accuses. Several people can share a table. The login name is the
  identity written into `SeatRecord.label`, so a human's tells follow the
  name across whichever suspect they play (`CLAUDE.md`, "Human tells
  persist across games").
- **8.3, the rest of chat.** The characters talk on the web: the on-turn
  remarks that exist headless, off-turn talk, humans typing at the table,
  the pacing rules `CLAUDE.md` proposes ("stagger arrivals, cap
  concurrent speakers at two; the chattiness dial gates participation,
  not just verbosity"), and the debriefs that write a dossier on each
  human. This is where the model comes onto the web (8.1 gave the service
  no key on purpose), under a spend cap. David, 2026-09-18: after 8.2,
  not inside it.

Phase 9 (in-depth UX) and Phase 10 (clean-up, then 1.0.0) follow, so
everything here is built plain, as 8.1 was: the screens work and read the
real game; typography, ornament, motion and the decorated board wait.

## 2. What the code dictates

Established by reading the code today (three exploration passes and one
design review against the code); the detail is in the modules named.

- **The seam is ready, with one trap.** `engine.game_steps(...,
  external=frozenset)` yields `LiveGame` once, `DecisionRequest(seat,
  kind, obs, choices|room|candidates+shown_to)` for every decision of an
  external seat (answered with `steps.send`), and `TurnComplete` per
  turn; the off-turn `card_to_show` comes through
  `resolve_suggestion_steps`; `tests/test_engine_steps.py` proves a table
  rebuilt by replaying its answers matches the live one. The trap:
  `_ask` does `return _checked(request, (yield request))`
  (`clude_core/engine.py:345`), so an answer that fails `_checked`
  raises *inside* the generator and finishes it. One stale double submit
  would end the table for everyone. The driver must validate before it
  sends; the engine's check becomes a public function the driver calls
  first.
- **`WatchGame` is the driver to generalise.** `clude_web/watch.py`
  already has the shape: setup in a store document, the generator in
  memory as a cache, rebuild on a cold instance, a per-game lock,
  `finish` writing a `GameRecord` into run `web`. It cannot pause on a
  `DecisionRequest` (its loop sends `None`) and its document has nowhere
  for answers. Rebuild must become "replay the entries, then run to the
  stored turn count".
- **Remark ordering lives in the engine.** `_append_remarks` fires right
  after the `MoveEvent`, after the `SuggestionEvent` for the suggester
  then the refuter, and after the accusation (`engine.py:626-658`), and
  keys on `bots.get(seat)` being a `SpeakingPlayer`. A driver only
  regains control at the next yield, which for a suggestion is the
  refuter's request *before* the `SuggestionEvent` lands; remarks
  appended by a driver would precede the suggestion they answer. So an
  LLM seat driven from outside needs a `speakers` hook in the engine
  (three lines: `_append_remarks(events, {**bots, **speakers}, ...)`),
  which also gives it `hear` fan-out for free.
- **Identity needs one decision and two guards.** `SeatRecord.label` is
  the logbook key and the one every dossier, White's per-opponent
  priors (`markov.set_table`, `memory.white_counts`) and the debrief's
  `opponent_aliases` already use, so a human label flows through them
  unchanged; `replay_data.seat_method` and `trace_document` treat a
  non-agent label like `floor`; `watch.readings` gives it `confidence:
  None`. But the login name has two forms, `account["name"]` as typed
  and `account["key"]` lower-cased, and logbook paths and GCS keys are
  case-sensitive, so the label must be the key. And since `users.normalise`
  lower-cases, an account "mustard" would make `logbooks/mustard/`, which
  collides with `logbooks/Mustard/` on Windows: the reserved names
  (the six suspects, `floor`, `random`, `web`) must be refused
  case-insensitively.
- **A human label breaks three lookups today**: `arena.parse_roster`
  rejects it, `headless_table` would seat it as a `RandomBot`, and
  `seat_kind` would record the name itself as the kind. Nothing else
  branches on `SeatRecord.kind`.
- **No JavaScript talks to the server yet.** Every write is a form POST
  with a hidden `csrf` field; `auth.check_csrf` reads `request.form`
  only, so a `fetch` must post form-encoded, never JSON. `require_session`
  answers an expired session with a 302 and a CSRF miss with an HTML 400,
  which a `fetch` would follow to the login page with status 200, so the
  client must notice and reload. `SameSite=Lax` is fine for same-origin
  `fetch`.
- **Request-driven only, and CPU only during requests.** The service is
  `--max-instances 1`, request billed with CPU throttled between
  requests, scale to zero (`docs/web.md`). No background threads, no
  websockets: bot turns, model calls, reactions and debriefs all have to
  run *inside* someone's request. And `threading.Lock` is unfair: a 30 s
  model call holding the game lock while six browsers poll on 7 of 8
  gunicorn threads would starve the human's own answer. So polling reads
  a snapshot without the lock, and the work runs in its own request.
- **Memory on the web has two costs and one bug to avoid.** `play
  --logbook` semantics are `memory.load_into` after reset and
  `memory.update` after the game. Loading Mustard retrains his tree on
  116k rows: 30 s at the deal (`docs/phase8.0-plan.md`, Stage 3). Green's
  document is his live posteriors, overwritten wholesale by `update`
  (`clude_training/memory.py:232-234`), and `WatchGame.record` never
  calls `observe(RevealedOutcome)` as the arena does (`arena.py:772`), so
  a naive port would save unchanged arms and two tables finishing in
  either order would lose one's learning. A cold rebuild that re-loads a
  logbook changed since the deal would also change the bots' moves and
  could make a stored human answer illegal.
- **Remarks are events; `about` is the extension point.**
  `RemarkEvent(turn, seat, text, about)`; `about="chat"` needs no record
  version bump. `say` is welded to a decision in both schemas;
  `schema_for` has no branch for a kind without label fields. Any edit
  to `rules.md` or a persona re-keys both LLM fixtures ($0.26), so the
  off-turn prompt lives in the user block. `LLMRequest.key()` hashes the
  user text, which includes the transcript, so a `RecordingBackend`
  could not rebuild a table whose chat arrived on wall-clock ticks:
  answers must be stored as data.
- **Spend is counted in tokens, not dollars.** `LLMSettings` caps calls
  and tokens per game and the wrapper falls back on any error result
  (`player.py:423-426`); the debrief is ungated; `estimate_cost` returns
  `None` for an unpriced model; `AnthropicBackend(api_key=...)` takes an
  explicit key; `requirements-web.txt` has no `anthropic` and
  `tests/test_deploy.py:57` asserts so.
- **What the 8.1 tests pin.** `tests/test_web.py` walks the url map, so
  every new route is gate-checked the day it appears.
  `tests/test_web_watch.py` pins Watch's game to the CLI's and scans the
  Watch page for `" showed "`, `"Holds:"`, `"data-card="`; the play view
  must show a human's own hand, so those scans stay on the spectator
  view and the seated view gets its own checks.

## 3. Design: 8.2 human players

### 3.1 The driver, headless first: `clude_training/table.py`

Flask-free, beside `arena.headless_table`, so the CLI uses it without
Flask and the tests drive it without a browser.

- **`SeatSpec(token, kind, label)`**: kinds `character` (label is the
  token's own character, seat-locked), `floor`, `human` (label is the
  account key), `open` (a seat waiting for a person; `floor` when the
  table is dealt with it still empty), and in 8.3 `llm`.
- **`TableSetup(seats, seed, max_turns, remember=False)`**, seats in
  board order as `seat_lineup` orders them; `to_dict`/`from_dict`;
  validation: 3-6 seats, distinct tokens, a character only on its own
  token. `TableSetup.from_roster(roster, n_players, seed)` derives the
  specs through `parse_roster` / `lineup_for_game` / `seat_lineup`, and
  `headless_table` delegates to `build_table(from_roster(...))`, so the
  CLI's `play`, Watch and a no-human table are one code path and the
  existing pin in `tests/test_web_watch.py` covers all three.
- **`build_table(setup) -> (Table, external)`**: characters built,
  `reset(seed)` and `new_game(labels)` with the full seat-ordered labels
  (humans included, or White's seat indexing is off); floor bots on
  `fill_seed`; human seats absent from `players` and present in
  `external`. `Table` gains `kinds` so the record never derives a kind
  from a label.
- **`engine.check_answer(request, answer)`**: `_checked`'s body made
  public; `_checked` calls it. The driver validates every answer with it
  before `send`, so a bad answer is a 400 and the game goes on; if
  `send` still raises, the table is marked broken and rebuilt from its
  document. The goldens prove the engine unchanged.
- **The answer codec.** `encode_answer(kind, answer)` /
  `decode_answer(request, data)`: a movement as `{"move": "stay" |
  "secret_passage" | "move", "to": <node>}` with the node through
  `records.node_to_json` / `node_from_json` (a boxed-in "stay" has a
  `Square` destination), rebuilt as a `MoveChoice` and matched against
  `request.choices` by dataclass equality; a suggestion `{"suspect",
  "weapon"}` or null; an accusation the triple or null; a card
  `{"card"}`. A bad answer raises `ValueError` with a message fit for a
  400.
- **The entry log.** A table's document holds an ordered list of
  *entries*, not just answers: `{"kind": "answer", seat, decision, data,
  at}` for every external decision (human, stand-in, and in 8.3 LLM, the
  last with its `Decision` audit and the lines it said), and in 8.3
  `{"kind": "chat"|"reaction", seat, text, at}`. `at` is `len(events)`
  when the entry was applied. Every entry is applied while the generator
  is paused, and every pause is deterministic given the entries before
  it, so replaying the list in order rebuilds the game exactly.
- **`TableGame`.** Holds the generator, the `LiveGame` handle, `pending`
  (the `DecisionRequest` the game is stopped on, or None), the entries,
  `turns`, `finished`, `previous_mark`, a lock, and an immutable
  **snapshot** (events tuple, positions, pending summary, turns)
  republished after every advance so readers never take the lock.
  - `run(turns=1)`: advance until a request for an external seat (kept as
    `pending`), one `TurnComplete`, or the end (the three endings noticed
    eagerly, as `WatchGame.advance` does).
  - `answer(seat, seq, data)`: `seq` must equal the entry count (a double
    submit is refused), the seat must own `pending`; decode,
    `check_answer`, `send`, append, then run on to the next pause. A
    human's move is followed by their suggestion request in the same
    turn, so a turn is often several answers.
  - `rebuild(setup, entries, turns)`: build, then for each entry: an
    answer runs to the pending request (whose seat and kind must match,
    else the document is corrupt and the table is reported as such) and
    sends; a chat or reaction runs until `len(events) == at` and appends
    the `RemarkEvent`. Then run until `turns` turns are played or a
    request is pending. A test proves equality with the live game at
    every pause.
  - `stand_in(seat)`: the answer the floor bot for that seat
    (`FloorBot(rng=Random(fill_seed(seed, seat)))`, built once per game)
    gives to `pending`; used by autopilot (3.4), stored like any answer,
    so a rebuild never needs it.
  - `view(viewer_seat, since)`: everything a screen needs from the
    snapshot, JSON-ready (3.3), described from that seat's point of view.
- **`play --human TOKEN[,TOKEN]`** on the CLI: a terminal seat over
  `TableGame`, printing the rooms in reach and lettered choices per
  request and reading an answer, the rest of the table headless. The
  headless-first proof of the driver, a way for David to play from Orbit
  before the screens exist, and a Flask-free test of the off-turn show.

### 3.2 The registry and routes: `clude_web/tables.py`, `views.py`

`TableRegistry` generalises `WatchRegistry`; `watch.py` becomes a thin
compatibility layer (`WatchSetup` → `TableSetup.from_roster`, an all-bot
`TableGame`) so the `/watch` routes, `watch.html` and the 23 Watch tests
stand, and an all-bot table still advances by "Next turn" and "Play to
the end". Documents move to `tables/<id>.json`, version 2: `setup`,
`entries`, `turns`, `status` (`open`, `playing`, `finished`), the seat
owners, `autopilot` flags, `started_by`, `created`, `updated`,
`record`, and in 8.3 the spend and the pending debriefs. Cache in
memory, truth in the store, saved only when the entries or the turn
count changed (a GCS put is a round trip); rebuild by entries,
single-flight per id so two polls on a cold instance do not both replay
the game.

| Route | What |
|---|---|
| `POST /tables` | New table from the lobby form: six token rows, each *Empty*, *Me*, that token's character, *Floor bot* or *Open seat*; 3-6 non-empty; optional seed; "characters remember". Deals at once if no seat is open, else the table waits in the lobby. |
| `POST /tables/<id>/sit`, `/leave` | Take or give up an open seat before the deal. |
| `POST /tables/<id>/deal` | Anyone seated deals; open seats still empty become floor bots. |
| `GET /tables/<id>` | The table screen: the play view if the viewer holds a seat, the spectator view (Watch's) otherwise, with the initial payload embedded through `embed_json`. |
| `GET /tables/<id>/poll?since=N` | JSON: the viewer's view from the snapshot since an event cursor, plus `work: true` when bot work is due. Never takes the game lock. |
| `POST /tables/<id>/work` | One unit of work under the lock, `acquire(blocking=False)`: one bot turn (no sooner than 1.5 s after the last), and in 8.3 one model decision, one reaction or one debrief. Returns at once with `busy` if another request holds the lock. |
| `POST /tables/<id>/answer` | One answer; 400 with the message on anything the codec or `check_answer` refuses. |
| `POST /tables/<id>/autopilot` | A seat's owner hands their seat to the stand-in or takes it back; anyone seated may do it for a seat that has waited ten minutes (3.4). |

`poll`, `work` and `answer` are `fetch` calls, the writes form-encoded
with the CSRF token from a `<meta>` tag, and the client reloads on a
redirect or a 400 page (an expired session, a rotated token). The poll
loop runs every 2 s while the table is busy, every 5 s while waiting on
another person, every 10 s during the viewer's own turn, and stops while
the tab is hidden, so a tab left open overnight does not spend the
request quota. A client that sees `work: true` fires `/work`; the lock
makes the first the worker and the rest cheap no-ops, so with nobody at
the table the game simply waits, which is right when CPU exists only
during requests.

### 3.3 The play screen: `templates/table.html`, `static/table.js`

Watch's layout (board left, side panel right, stacked on a phone) plus
the human's own panel. All server text reaches the page as
`textContent` or DOM nodes, never `innerHTML`; JSON responses carry
`X-Content-Type-Options: nosniff`.

- **Status line.** "Your move: you rolled 4", "Waiting for Mustard",
  "Scarlett suggests White with the Rope in the Lounge. You must show a
  card", "Your token was called to the Lounge; you may stay and suggest
  there" (a drag has no `MoveEvent`, so the line is synthesised from the
  `SuggestionEvent`), "You are out; you still show cards", "Game over".
- **The decision, one form at a time**, from `pending`: for a movement,
  the legal destinations highlighted on the board as overlays at
  server-side coordinates (`board_svg.node_centre`, the way `replay.js`
  moves tokens; the geometry stays in one place) and the same choices as
  buttons ("Kitchen", "the corridor, 3 squares on", "Stay", "Secret
  passage to the Study"); for a suggestion two selects, the room fixed,
  "Suggest" or "No suggestion"; for an accusation three selects, "Accuse"
  behind a confirm, or "Pass"; for a card to show, one button per
  candidate. The human sees the engine's legal options, the same list a
  character scores (`menu.py`'s note).
- **My hand** and **my notepad**: the 21 cards with what the shared floor
  has proven from this seat's view (`clude_constraints.observe(state,
  my_seat).mask`: holder proven, or the seats still possible). Parity
  with the cludebots, who all get the floor (David, 2026-09-18).
- **The other seats, Watch's compact bars** (David, 2026-09-18): each
  bot seat's cards placed and its method's confidence per category, as
  the Watch screen draws them, and in or out. Readings are cached per
  event-log length, since a fresh Plum reading is 0.7 s.
- **The log** of this game as this seat saw it: `describe_event` gains a
  per-viewer reveal, so the card shown is named only to the suggester and
  the refuter (`ClueObservation.for_player`'s rule); spectators never see
  it. Table talk lands here too (8.3).
- **Game over**: the envelope, the winner, a link to the replay in run
  `web`, "Play again" (same seats, new seed).

### 3.4 Several people, and people who leave

- **Open seats.** A table with open seats waits under "Tables waiting for
  players" until someone sits and someone deals.
- **Autopilot.** A seat's owner can hand it to the stand-in and take it
  back; any seated player can put a seat on autopilot once it has waited
  ten minutes, so one person leaving cannot lock the table. The stand-in
  is the floor bot, the plain characterless player, so a human seat on
  autopilot never impersonates a character.
- **Resume anywhere.** The lobby lists every unfinished table the viewer
  sits at; the document holds everything; a cold instance rebuilds it.
  Rebuild replays every bot decision too: a six-seat, sixty-turn game
  with Plum and Green is an estimated 55-95 s on Cloud Run (their
  belief calls, at the measured 1.6x of Orbit) plus the 8-10 s cold
  start, and 30 s more with Mustard remembering. It is paid only after
  the instance has idled to zero or a redeploy, never while anyone
  polls; the screen says "restoring the table" meanwhile. `--min-instances
  1` would remove it at roughly $10-15 a month; not proposed.

### 3.5 Records, replay and memory

- A finished table is saved to run `web` as today, human seats
  `SeatRecord(kind="human", label=<account key>, profile=None)`; the
  lobby and `/runs/web` show the labels; the replay works unchanged (a
  human seat's block is the floor's proven cards and no belief, like
  `floor`).
- **"Characters remember"** (David, 2026-09-18: in 8.2, default off, the
  cost stated on the form). With it on, the deal does what `play
  --logbook` does against the web store's `logbooks/`, and the document
  snapshots what was loaded (Green's arms; the game ids Mustard's rows
  and White's counts came from) so a rebuild loads the same memory and
  not a logbook that has moved since. At the finish, under the save
  lock: reload Green from the latest document, `observe(RevealedOutcome)`
  as the arena does, then `update` for every remembering seat. With it
  off, nothing is read or written. White's per-opponent counts keyed by
  the human's label are what make "human tells persist" true before any
  model is involved.

### 3.6 Tests

- Driver (`tests/test_table.py`): a mixed table answered from a
  `Recorder` log reproduces `run_game`'s events (the `Fixed`/`Recorder`
  pattern of `tests/test_engine_steps.py`); the refuter is asked
  off-turn; a rebuilt table equals the live one after every entry; the
  codec round-trips every kind, a boxed-in stay on a square included; a
  double submit, a wrong seat, an illegal move and a card not held get a
  message and the game continues; `from_roster` plays `play`'s game for
  the four rosters `tests/test_web_watch.py` uses; autopilot answers are
  stored and rebuild needs no stand-in; `play --human` with a patched
  `input`.
- Web (`tests/test_web_tables.py`, reusing `client`, `csrf`, `deal`):
  two accounts play a three-seat table to the end (poll, work, answer)
  reading only what each may see, the spectator view through the
  secrecy asserts factored out of the Watch test, the seated view checked
  against `state.hands[me]` and `mask.holder_of`; a 400 leaves the game
  alive; a cold registry rebuilds identically, `pending` included, and
  single-flight; open seats, sit, deal, leave, autopilot; the record
  carries `kind="human"` and the key, its replay opens; reserved names
  refused in any case; memory off changes nothing, memory on moves
  Green's arms once and White's counts under the human's label, two
  tables finishing lose nothing, and a rebuild after the logbook moved
  still matches.
- Browser (`CLUDE_WEB_BROWSER=1`): highlighted squares where the board
  says; clicking one posts the move; the show-a-card prompt appears
  off-turn; a hostile line runs no script; `clude_shots.py` gains the new
  lobby form, an open table and the play screen in both themes and
  widths.

## 4. Design: 8.3 the rest of chat

### 4.1 The model on the web (8.3a)

- `anthropic` joins `requirements-web.txt` (`tests/test_deploy.py:57`
  flipped, the comment fixed); the key reaches the service as
  `ANTHROPIC_API_KEY` through `--set-secrets` from a new Secret Manager
  secret `clude-anthropic-key` with accessor granted to `clude-run`, a
  one-time change made only after David's yes, as 8.1b's were. No secret
  client in the app; the backend is built per table at the deal, not in
  `create_app`, so the deploy tests still build the app with no network.
  Without a key the lobby option does not appear.
- **`MeteredBackend(inner, ledger, per_game_cap)`** in `clude_llm`: one
  place for both caps. It prices every call with `estimate_cost` (an
  unpriced model is refused, not uncapped), keeps per-table spend, writes
  a daily ledger document (`spend/<date>.json`), and over either cap
  returns an error `LLMResult`, so the wrapper's existing fallback plays
  the headless character and the screen says "Plum's budget is spent".
  Covers decisions, reactions and debriefs without touching
  `LLMSettings`. Per-table budget on the lobby form (default
  `CLUDE_WEB_LLM_BUDGET`, proposed $2.00); daily cap
  `CLUDE_WEB_LLM_DAILY_CAP` (proposed $10).
- **LLM seats are external seats in the driver.** The driver calls
  `LLMCharacter.choose_*` on the `DecisionRequest` itself, passing
  `request.obs` (so `Character`'s per-observation belief cache still
  gives one Plum belief per turn), stores the answer with its `Decision`
  and the lines it said, and registers the wrapper with the engine's new
  `speakers` hook so its remarks land exactly where a headless seat's do
  and the other LLM seats `hear` them. On rebuild a scripted speaker
  returns the stored lines, `hear` is re-fed, and no backend is built:
  a cold instance never calls the model to catch up. Headless characters
  stay inside `bots`; `NullBackend` still reproduces the headless table,
  since the wrapper's fallback is the same character with the same RNG
  wherever it is called from. The stored `Decision`s become
  `GameRecord.llm_log` at the finish. The wrapper's chattiness RNG is not
  advanced on rebuild: the past is exact, the future may branch, which a
  game with people in it accepts.
- A bot turn on the model is two to four calls of 2-3 s each, one per
  `/work` request, so the table sees "Plum is thinking" for a few seconds
  rather than a frozen page; every request stays inside the 300 s
  timeout and the 30 s call timeout.

### 4.2 Humans talk (8.3b)

`POST /tables/<id>/say`: a seated human's line, capped at about 240
characters with control characters stripped (it lives in records for
ever and in every later prompt), becomes `RemarkEvent(turn, seat, text,
about="chat")`, appended by the driver as a `chat` entry, heard by every
LLM seat, shown to everyone in the log. Chat is never consulted by the
engine: the formal refutation stays `check_answer`ed against
`state.hands`, and a test says so ("I don't have it" changes nothing),
the regression test `docs/architecture.md` asks for.

### 4.3 Off-turn talk and pacing (8.3c)

- **Opportunities.** A suggestion resolving, an accusation, a human's
  line or another seat's remark opens one. Each LLM seat other than the
  actor **participates with probability `chattiness`** (the wrapper's own
  RNG): the dial gating participation, as `CLAUDE.md` proposes. The
  on-turn gate stays as it is, because moving that draw would change the
  later prompts of every recorded fixture.
- **Stagger and cap.** Of the seats that want to speak, at most **two**
  are queued, each with a random delay of 2-8 s; each `/work` serves at
  most one due item, so replies arrive one at a time, a few seconds
  apart. A queued reply is dropped once the game has moved on a turn. A
  reply to a reply decays (chattiness squared) so a conversation tails
  off; a per-turn and a per-game cap on off-turn lines and the dollar cap
  bound the rest. Every served line is a `reaction` entry.
- **The call.** `LLMCharacter.react(obs, trigger)`: a new request kind
  `"remark"` with a third fixed schema (`{"say": string}`, empty for
  silence; `schema_for` and `parse_response` get an explicit branch) and
  `prompt.remark_prompt(...)`: who you are, the compact state (hand,
  floor, top belief, the same formatters), recent table talk, the line
  that prompted this, and the instruction to say one short line in your
  voice or nothing, never a point already made. Low effort, small
  `max_tokens`, about a cent a call, audited as a `Decision` of kind
  `remark`. `rules.md` and the personas are not edited, so both fixtures
  stay valid and the cached system block still hits.
- **Bot turns keep the same beat**: one per `/work`, about two seconds
  apart, so the table reads at a human pace.

### 4.4 Debriefs, dossiers and read-back (8.3d)

After a table with LLM seats finishes, the document lists one pending
debrief per LLM seat with a logbook; the finishing screen ("wrapping
up") drives `/work` until they are done, one per request ("Plum is
writing up his notes", 42 s and $0.09 each), and the lobby drains one
pending debrief per visit as a fallback, since no request means no CPU.
Each entry writes its dossier on every opponent present, humans by
label: the narrative half of "human tells persist". With "characters
remember" on, LLM seats also read their logbook back at the `memory`
dial's depth (`attach_logbook`, `read_back`), so a character that has
met David before comes to the table with its read on him.

### 4.5 Tests

Every 8.3 test runs on `ScriptedBackend`/`NullBackend`, never the API
(the `_wrapped`/`PERSONA`/`RULES` helpers of `tests/test_llm.py`, the
`_KindBackend` of `tests/test_debrief.py`): a scripted LLM seat's choice
is played and its remarks land in the same order as the headless
`_llm_game` with the same script; a rebuild makes zero backend calls and
the record carries `llm_log`; the metered backend trips on a scripted
result of a million tokens and refuses an unpriced model; a human line
reaches every LLM seat's transcript and the next prompt; the
participation draw, the two-speaker cap, the stagger order, the
stale-drop and the decay on a fake clock; the remark schema is fixed and
its request keys stable; the reveal rule survives chat; the daily ledger
refuses over the cap; N `/work` ticks write N serials and the next
table's first request carries "From your logbook"; the two recorded
fixtures still replay with zero misses.

## 5. Order and sub-phases

Each step leaves the suite green and works on its own; I stop for a yes
before any step that spends.

| Step | Deliverable | Check |
|---|---|---|
| 8.0.4 | The `room_features` change (section 6), a paired 24-game arena against `arena-grid-tuned-24` at the presets, the loop report over both; goldens re-captured and both fixtures re-recorded on purpose ($0.26); glossary section, `CLAUDE.md` and `docs/phase8.0-plan.md` closed | repeats and wasted trips fall headless for Plum and Mustard; win rates within noise |
| 8.2a | `engine.check_answer`; `clude_training/table.py`; `headless_table` over `build_table`; `play --human`; `tests/test_table.py` | driver tests; goldens unchanged; `from_roster` pinned to `play` |
| 8.2b | `clude_web/tables.py`, `watch.py` as the shim, the lobby form, `table.html`/`table.js`, `poll`/`work`/`answer`, one human; reserved names; `kind="human"` | test-client game to the end; browser tests; screenshots looked at |
| 8.2c | Open seats, sit/deal/leave, autopilot, resume, single-flight rebuild; "characters remember" with the memory snapshot and Green's rebase | two-account tests; memory tests |
| 8.2d | Deploy; a scripted two-account check on the URL including a forced cold rebuild; `docs/web.md`, `docs/cli.md`, `docs/architecture.md` (Seats: the human half built), `README.md`, `CLAUDE.md`, "as implemented" | the live check passes; rebuild time and poll cost measured |
| 8.3a | `anthropic` in the image, the secret (after a yes), `MeteredBackend` and the ledger, the `speakers` hook, LLM seats external, the lobby option | cap and ordering tests; a live table on the URL ($1-2) |
| 8.3b | `/say`, the remark schema and prompt, `react`, the reaction queue with stagger, cap, decay and staleness | fake-clock tests; a live table ($1-2), transcript read for voice, repetition and pacing |
| 8.3c | Debriefs through `/work` and the wrapping-up page, read-back on the web | scripted debrief tests; a live table ($1-2) |
| 8.3d | `docs/llm-wrapper.md` (chat), `docs/web.md`, `docs/logbooks.md`, `CLAUDE.md` status and spend, `docs/phase-plan.md` rows; Phase 8 closed | suite green; screenshots looked at |

Rough size: 8.0.4 half a day of laptop time; 8.2 two days; 8.3 two days.
Live spend: $0.26 in 8.0.4, none in 8.2, $5-12 for 8.3's three live
checks, each quoted as a range and run only after a yes.

## 6. 8.0.4: the scoring change

The change is in `clude_agents/features.room_features`, the shared
feature arithmetic, not in any method (the "six distinct methods" rule
holds; `choose_destination` stays per agent). Today a landing in a room
gets `information = p[room]` and `proximity = 1.0`. The change: a landing
in a room whose card the floor has already located (`p[room] == 0`) gets
the corridor rule's proximity instead, `1 / (1 + steps from that room to
the nearest live room)`, since it is a place on the way rather than a
destination; a landing in a live room keeps 1.0; and when every room is
located, every landing keeps 1.0, since then any room serves for testing
suspects and weapons, which is FloorBot's rule. The corridor rule is
untouched, so the fallout is bounded to entering cleared rooms and the
"stay" a summons allows. Measured with a paired arena (same seeds as
`arena-grid-tuned-24`) and `loop_report.py` over both: kept if repeats
and wasted trips fall for Plum and Mustard without moving win rates
outside noise, else the plan's second form (proximity discounted by a
constant for a located room) is tried once, else the change is dropped
and the question closes as "measured, not helped". Either way the result
is a dated glossary section, the goldens re-captured, both fixtures
re-recorded ($0.26), and the open question removed from `CLAUDE.md`,
`docs/architecture.md` and `docs/phase8.0-plan.md`. No paid run.

## 7. Files

- **New:** `clude_training/table.py`, `clude_web/tables.py`,
  `clude_web/templates/table.html`, `clude_web/static/table.js`,
  `tests/test_table.py`, `tests/test_web_tables.py`; in 8.3
  `clude_llm/metered.py`, `clude_web/chat.py` (opportunities, queue,
  pacing), `tests/test_metered.py`, `tests/test_chat.py`;
  `docs/phase8-plan.md`.
- **Changed:** `clude_core/engine.py` (`check_answer`; in 8.3
  `speakers`), `clude_web/watch.py` (the shim), `clude_web/views.py`,
  `clude_web/__init__.py` (the registry, the `<meta>` token, `nosniff`),
  `clude_web/users.py` (reserved names), `clude_web/replay_data.py`
  (per-viewer reveal), `clude_web/templates/lobby.html`, `static/style.css`,
  `clude_training/arena.py` (`headless_table` over `build_table`,
  `Table.kinds`), `clude_training/memory.py` (load from a snapshot),
  `clude_storage/records.py` (the `kind` docstring),
  `scripts/clude_cli.py` (`play --human`, the `users add` guard),
  `scripts/clude_shots.py`, `tests/test_web_watch.py` (the secrecy
  helper); in 8.3 `clude_llm/player.py` (`react`, the `remark` decision
  kind), `clude_llm/schema.py` (`REMARK_SCHEMA`), `clude_llm/prompt.py`
  (`remark_prompt`), `requirements-web.txt`, `tests/test_deploy.py`,
  `docs/web.md`, `docs/cli.md`, `docs/architecture.md`,
  `docs/llm-wrapper.md`, `docs/logbooks.md`, `docs/phase-plan.md`,
  `README.md`, `CLAUDE.md`; in 8.0.4 `clude_agents/features.py`,
  `tests/test_character.py` goldens, `tests/fixtures/llm_seed*.json`,
  `docs/strategy-glossary.md`, `docs/phase8.0-plan.md`.
- **Reused as is:** `engine.game_steps` and `resolve_suggestion_steps`,
  `arena.seat_lineup` / `lineup_for_game` / `fill_seed` /
  `build_character`, `records.node_to_json` / `node_from_json`,
  `board_svg.token_points` / `node_centre`, `replay_data.suggestion_line`
  / `cached_trace` / `screen_payload`, `views.embed_json` /
  `run_listing`, `auth.csrf_token` / `current_user`, the `users` module,
  `clude_training.memory.load_into` / `update`, `LLMCharacter` and its
  fallback path, `estimate_cost`, `ScriptedBackend`, `LogbookEntry` /
  `Logbook`, `explain`'s formatters, the test helpers `Fixed` /
  `Recorder` / `replay` (`tests/test_engine_steps.py`) and `deal` /
  `csrf` (`tests/test_web_watch.py`).

## 8. Verification, end to end

- The whole suite with `-n auto` after every step; the browser tests
  under `CLUDE_WEB_BROWSER=1`; `clude_shots.py --dark --phone` after every
  screen change, and the PNGs looked at.
- 8.0.4: the paired arena and the loop report, numbers in the glossary.
- 8.2: `play --human Scarlett` from the terminal to the end of a game;
  locally two browsers signed in as two accounts through a three-seat
  table with Plum; then on the URL a scripted check with two throwaway
  accounts (as 8.1b did) covering sit, deal, every decision kind, the
  off-turn show, a forced cold rebuild (a deploy mid-game) and the
  replay; rebuild time and poll cost recorded in `docs/web.md`.
- 8.3: each live step is one table on the URL with a stated budget, its
  transcript read for voice, repetition and pacing, its spend compared
  with the quote, and the ledger and cap checked by trying to exceed
  them.

## 9. Decisions

Taken by David on 2026-09-18:

1. **8.0.4 first, the scoring change measured headless.** Not the paid
   ladders, not Phase 10.
2. **The model comes onto the web in 8.3a**, after human seats; 8.2's
   humans play the headless characters.
3. **A seated human sees the floor's notepad and Watch's compact bars
   for the bot seats**, beyond their own hand and the legal choices.
4. **"Characters remember" ships in 8.2**, default off, the cost stated
   on the form.

Still open, non-blocking, with what I will do unless told otherwise:

5. The stand-in for a seat on autopilot: the floor bot (assumed), or the
   token's own character.
6. Budgets for 8.3: the per-table default of $2 and the daily cap of $10
   (assumed), and a yes per live check when each step is ready.
7. `--min-instances 1` to remove the cold rebuild, at about $10-15 a
   month: not proposed; the cold rebuild is accepted and measured.

## 10. Assumptions

Login name as identity, the lower-cased key as the label and the typed
name on screen; no sign-up page; a human writes no logbook entries of
their own (dossiers are written *about* them); spectators see Watch's
view; the play screen is plain (Phase 9 dresses it); no websockets and no
background threads; one web run, `web`; the leash and chattiness presets
stand; no edit to `rules.md` or the personas; `RECORD_VERSION` stays 3;
nothing new in the Google Cloud project without a yes.

## 11. Out of scope

Phase 9's look (typography, the decorated board and logo, motion, the
six-seat layouts, "tap a seat to open it"); a manual notepad the human
ticks by hand; LLM seats in the arena or CLI beyond what exists; any
change to a method, a dial or a preset beyond 8.0.4; a cached trained
tree for Mustard (the 30 s stays honest on the form; revisit if it
hurts); a public release and the IP scrub.

## 12. As implemented

Written as the work lands. Where this section and the sections above
disagree, this section is what was built.

### 8.0.4, the landing rule (2026-09-18)

Built and measured as section 6 planned, with one departure the
measurement forced. The first form -- every placed room a place on the
way -- removed every exact repeat on all three tables but overshot: the
characters walked past rooms where a suggestion was still worth making,
suggestions per game fell by a third and the four-seat games ran 17
turns longer. The kept form is FloorBot's own rule brought into the
features: a placed room stays a destination when nobody else can refute
with it, because it is in the agent's own hand or proven to be the
envelope's, and only a room placed in another seat's hand becomes a
place on the way (`clude_agents/features._landing_proximity`, which now
reads the observation's mask; `room_features` no longer discards `obs`).
On every table games are shorter than the baseline (53.9 to 45.9 turns
at 3-6 seats, 41.9 to 35.6 at four, 31.9 to 30.1 on Plum's table),
exact repeats fall by two thirds or more for every character (Plum 43%
to 6%, 14% to 11% and 25% to 4%), secret passages halve, and win rates
move only within the noise floor. The numbers, both forms and all six
runs are in `docs/strategy-glossary.md`, "The landing rule". The four
goldens in `tests/test_character.py` were re-captured and both LLM
fixtures re-recorded ($0.22 against the $0.26 quoted; seed 1 now has
17 suggestions rather than 18). The open question in `CLAUDE.md`,
`docs/architecture.md` and `docs/phase8.0-plan.md` closes as answered;
2c and 2d were not run.

### 8.2a, the driver and the terminal seat (2026-09-18)

`clude_training/table.py` as 3.1 describes: `SeatSpec`, `TableSetup`
(seats sorted into the board's order whatever order they arrive in,
`from_roster` seating exactly as `seat_lineup` does, a test pins it),
`build_table`, the answer codec, `describe_request`, `TableSnapshot` and
`TableGame`. `engine.check_answer` is `_checked` made public and `_ask`
calls it, so the goldens prove the engine unchanged; `TableGame.answer`
runs it before `send`, so a bad answer is a `TableError` and the game
stays exactly as it was. Two things the plan did not name:

- **The turn slice.** `WatchGame` marked the previous turn as the event
  count before the `next()` that produced the marker, which is wrong
  once a turn spans several answers; `TableGame` keeps the count at the
  last `TurnComplete` instead, and `turn_events` is exact.
- **`arena.headless_table` builds through `build_table`** with a
  deferred import (`table` imports the arena's seating helpers), so
  `play`, Watch and a table with people are one code path; `Table`
  gained `kinds`, because a human seat's label is a person's name and
  the kind can no longer be read off it. `tests/test_web_watch.py`'s
  pin of Watch to `play` now covers all three.

`play --human TOKEN[,TOKEN] [--name NAME]` on the CLI: the same driver
from the keyboard, with distinct prompts per decision (`move>`,
`suggest>`, `accuse>`, `show>`) so a script can answer it, `?` printing
the floor's grid, and a card shown between two other seats hidden as
`ClueObservation.for_player` hides it. The event printer moved out of
`cmd_play`'s verbose block into `_event_line` so both use it.
`tests/test_table.py` (27 tests): the seating pins, every kind of
answer round-tripping (a boxed-in stay on a square included), a human
seat answered from a recorded game reproducing it with the off-turn
show, two humans refuting each other, a rebuild matching the live game
at every pause and stopping where the stored turn count says, a corrupt
log reported, refusals leaving the game alive, autopilot answers stored
so a rebuild needs no stand-in, remarks replayed in place (for 8.3),
and the terminal seat driven by a scripted `input`.

### 8.2b and 8.2c, the table on the web (2026-09-18)

`clude_web/tables.py` as 3.2-3.5 describe, with `watch.py` reduced to
the shim (`WatchSetup.to_table_setup`, `WatchGame` a `WebGame`,
`WatchRegistry` the one registry), so the 23 Watch tests stand
untouched except for the route parameter's name. Departures and
findings:

- **`work` answers for an autopilot seat in the same call.** The first
  draft played one turn and stopped, so a request landing on a seat on
  autopilot waited for the next call and the person saw a decision for
  a moment; the stand-in's whole turn is one unit of work.
- **The reveal test had to be per event.** A check that a viewer never
  saw "showed Plum" was wrong: the same card can be shown again in a
  refutation that viewer was part of. `tests/test_web_tables.py` keys
  each viewer's lines by event index and checks the one line.
- **`me` is the account key, `user` the name as typed.** The templates
  needed both (the open-table page says "(you)" by key and lets the
  starter deal by name), and the view functions pass both.
- **The lobby's web run sorts labels** (`sorted`, capitals first), so a
  human's key lists after the characters; the test expects `sorted`.
- Readings are cached per event-log length on the game (`WebGame`), the
  document is saved only when the entries or the turn count moved, the
  rebuild is single-flight, and `poll` reads the snapshot without the
  lock, all as the design review asked.
- **Memory** as 3.5: `clude_training.memory.snapshot` /
  `load_snapshot` (new), `TableGame(prepare=...)` to load it before the
  deal, Green reloaded from the latest document and shown the outcome
  before `update` at the finish, under the save lock. Tests: off reads
  and writes nothing; on writes White's counts under the person's key
  and Mustard's rows, the second table snapshots the first's game, and
  a rebuild after the logbook moved still matches; two tables with
  Green finishing keep both games.
- `users.RESERVED_NAMES` refuses the six suspects, `floor`, `random`,
  `web` and `envelope` in key form; `X-Content-Type-Options: nosniff` on
  every response; the CSRF token in a `<meta>` for the page's `fetch`.

`tests/test_web_tables.py` (16 tests) and three browser tests in
`tests/test_browser.py` (the legal squares drawn where the server says
and one button each, a click that plays the move, the reveal rule
holding in the log on autopilot). The screenshot script shoots the
table on the person's move, a few answers later, and waiting for
players.

### 8.2d, the deploy (2026-09-18 and 2026-09-19)

Everything up to the deploy was done on the 18th: the suite green,
every screen shot and looked at (the seat form's cards and the table's
empty log were fixed from the shots), the docs updated. The deploy
itself was refused by the session's permission check, as 8.1b's first
`gcloud services enable` was, so David ran it on the 19th (revision
`clude-00003-6nf`, 17:55 UTC) and played a four-seat table to the end
in the browser (replay `web/4`). The scripted check ran the same day
from the session: `play` (a four-seat game with two throwaway accounts,
63 turns, 186.7 s wall time, the replay opening after; poll median 94 ms,
work 764 ms, answer 806 ms over 97/84/95 requests) and `start` (table
`19ac4efe45` left three answers in). The redeploy between `start` and
`resume` was 8.3a's key deploy (revision `clude-00004-jl9`, 21:32 UTC),
and David ran `resume` after it: the first poll came back at the same
pending decision in 0.1 s (three answers in, no memory to load), and
the table finished (63 turns; poll median 93 ms, answer 849 ms, work
823 ms). The two
batch files David wrote for this became `scripts/deploy.bat` and
`scripts/live_check.bat`, runnable from any directory with the venv's
interpreter (the first draft used `#` for comments, which batch does
not have, and the global `python`); `docs/web.md` names them.

### 8.3a, the model on the web (2026-09-19)

As 4.1, with these pins and departures:

- **The engine's hook is a `speakers` mapping read at every drain**, not
  merged once: `game_steps(..., speakers=None)` wraps `bots` and
  `speakers` in `_Talkers`, whose `get` prefers the speaker, so the
  driver may install a replay speaker while the generator is paused.
  `run_game` is untouched and the goldens prove it.
- **`Table.wrappers` and `TableGame.speakers`.** `build_table(setup,
  llm_backend=None)` builds an `LLMCharacter` for each `llm` seat when a
  backend factory is given (`Table.wrappers`), reset and told the table
  like a character; without one the seat has no wrapper and only replays.
  Each `llm` seat's voice in the engine is a `Speaker` proxy: live, it
  drains the wrapper's line at the event it belongs to and records it;
  on a rebuild the stored lines are queued on it first and returned
  instead, so the events match with no call, and a wrapper present at
  the rebuild is reminded of its own lines and hears everyone else's.
- **Where a line is stored.** An answer entry gains `said: [[seat,
  text], ...]` for every line drained during *that answer's* resume,
  whoever said it: Plum's suggestion line lands on the refuter's answer
  when a person showed him a card, because that is when the
  `SuggestionEvent` lands. `rebuild` queues each entry's lines before
  sending it. `audit` on an `llm` entry is the `Decision.to_dict()`,
  replayed into the wrapper's audit on a warm rebuild and gathered into
  `GameRecord.llm_log` at the finish; `SeatRecord` gets `kind="llm"`
  and the model id.
- **One decision per `work`.** `TableGame.llm_answer` calls the
  wrapper's `choose_*` on the request's own observation with a per-seat
  RNG seeded like the stand-in's; `TableRegistry.work` answers a pending
  model seat that way (`did = "model"`) and returns, so the screen reads
  "Plum is thinking" between calls. `view_payload.work` is true while a
  model seat is pending, or the client would never fire `/work` for it.
  A `NullBackend` twin plays the headless characters' game exactly
  (`test_the_null_twin_is_the_headless_game`).
- **Metering** is `clude_llm.metered.MeteredBackend` over a `Ledger`
  (`spend/<date>.json`), one per seat sharing the table's budget and the
  day's cap; both refusals are error results the wrapper's fallback
  absorbs, and the audit says `error: budget: ...`. The backend keeps
  `known_spent` so a poll never reads the store. The web config is
  `LLMConfig(key, model, budget, daily_cap, make_backend)`, built by
  `create_app` from `ANTHROPIC_API_KEY` (or `.env` locally),
  `CLUDE_LLM_MODEL`, `CLUDE_WEB_LLM_BUDGET` and `CLUDE_WEB_LLM_DAILY_CAP`;
  under `TESTING` only what is passed in counts, so no test ever finds
  the developer's key. The screenshot app gets a stand-in key and a
  `NullBackend` factory so the lobby shows the option.
- The lobby's per-token select gains "Plum, on the model" and the form a
  budget field, only with a key; `anthropic` joins the image and the
  deploy test now asserts it is there.

### 8.3b, humans talk and the characters answer (2026-09-19)

As 4.2-4.3, with:

- `POST /tables/<id>/say`: `clean_line` strips control characters,
  collapses whitespace and caps at 240; `TableRegistry.say` takes the
  game lock, appends the `chat` remark (fanned to every speaker's
  `hear`, which `TableGame.remark` now does), scans for opportunities
  and saves. The engine never sees it: `test_chat_never_reaches_the_engine`.
- `LLMCharacter.react(obs, trigger, names)` with `REMARK_KIND`,
  `REMARK_SCHEMA` (`say` alone) and `prompt.remark_prompt`; the
  chattiness draw is the caller's, so the wrapper's RNG moves only where
  the caller says. `LLMSettings.remark_max_tokens` (200).
- `clude_web.chat.Reactions` on every `WebGame`: `scan` opens an
  opportunity per new chat line, on-turn remark, suggestion or
  accusation; each model seat but the actor joins with probability
  `chattiness ** (depth + 1)` on its own RNG, at most two queued in all,
  each due 2-8 s later; `work` serves one due reaction per call and,
  **departing from 4.3, holds bot and model turns while one is queued**
  (at a 1.5 s beat every reaction would have gone stale before it was
  due), while a person's own answer is never held. Caps: two lines a
  turn, forty a game. The queue is memory only.
- The chat form under the log, "The table is talking." on the status
  line, and `.log li.kind-remark` for the lines.

### 8.3c, debriefs and read-back on the web (2026-09-19)

As 4.4, with one departure: **the lobby never drains a debrief
synchronously** (42 s in a page load is worse than a late entry); it
lists a wrapping-up table with its link, the table page stays a table
rather than a redirect while a debrief pends, and whoever has it open
drives `/work`, which serves one pending debrief per call
(`TableRegistry.debrief_one`: the record read back face up, the entry
written with its dossiers on everyone present, people by account key;
the document marks `done` with the serial or `failed` with the reason).
With "characters remember" on, `_prepare` attaches a `Logbook` to every
model seat's wrapper at the deal (read-back at the `memory` dial's
depth) and loads its method memory from the snapshot like a character's;
`_remember` folds the game into a model seat's method memory too. The
finish schedules the debriefs only when "remember" is on. A cold
registry rebuilds the finished table with its wrappers and still writes
the entry.

Tests: `tests/test_metered.py` (6), `tests/test_web_llm.py` (6),
`tests/test_chat.py` (11), `tests/test_web_debrief.py` (3).

### 8.3d, the live checks and the close (2026-09-19)

The key went out as `clude-anthropic-key` (`docs/web.md`, "What is out
there") in David's deploy at 21:32 UTC, and the three 8.3 checks were
one table, played by David in the browser rather than the $1-2 scripted
runs section 5 quoted: table `1b31ccffd9`, David as Scarlett, White and
Peacock on the model, Mustard and Green as characters, the floor bot at
Plum, "characters remember" on. 58 turns; 55 model-seat decisions, 19
of which called the model (the rest had one legal option), 0 fallbacks,
1 deviation from the character; David said 6 lines, the model seats 8
on-turn lines and 28 off-turn reactions; $0.34 against the $2 budget
(`spend/2026-09-19.json`). Peacock's and White's lines read in voice and
answered what was said, which was 8.3b's question. The debriefs (8.3c)
were still `pending` when this was written: a debrief runs only while
someone has the finished table open to drive `/work`, and the page was
closed; David is opening it to drain them (about $0.20). Opening it
found the second bug of the pass: the page polled every 1.5 s and never
posted `/work`, because `table.js` only worked an *unfinished* table
(`current.work && !current.finished`), while the server marks a
finished, wrapping-up table as needing work. The test-client tests
call the route directly and so never saw it. Fixed in `table.js`
(`|| current.wrapping_up`); it reaches the service with the next
`scripts\deploy.bat`, after which reopening the table drains both
debriefs.

The other thing the pass found in the code: a served reaction was put back on
a rebuild through `TableGame.remark`, which fans a line to every *other*
speaker, so the seat that said it no longer remembered it, and the
reaction's `Decision` was never stored, so a finish after a cold rebuild
lost those calls from `llm_log`. Fixed: `remark` takes an `audit`,
`Reactions.serve` stores the reaction's decision with the entry, and
`rebuild` reminds the speaker's wrapper and gives the decision back. The
cold-rebuild test in `tests/test_web_llm.py` had been timing-dependent
(it saw the difference only when a reaction fell due during its loop,
hence under `-n auto` load); it now forces a reaction and asserts on it.

Docs closed: `CLAUDE.md` (status, spend, the suite at 440 passed and 16
skipped), `docs/phase-plan.md`, `docs/web.md` ("Deploying" gains the
live numbers), `README.md`, and this section. Phase 8 is closed; Phase 9
(in-depth UX) is next.
