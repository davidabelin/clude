# Phase 9: a seat over MCP

Planned 2026-09-20. Status: **9a-9f all done** -- 9a the plan and the
renumbering (2026-09-20), 9b built and 9c deployed with the first live
game from the chat (2026-09-21), 9d the eight fixes after the second
live game and 9e David's follow-ups (2026-09-22), all deployed as
revision `clude-00010-knh` that evening; 9f the chat seat's report after
the third live game (2026-09-25), **to deploy**.

Section 8, "As implemented", is written as the work lands and **wins
over the plan sections above it wherever they differ** -- read it
first. Two things it overturns, so that nobody follows the plan text by
mistake: there is **no head** (sections 3-5 design one; David removed it
on 2026-09-21, and `SeatSpec.head` and `WebGame.head_reading` do not
exist), and a **stalled seat is handed over after three minutes**, not
ten.

## 1. Context

Phase 8 closed on 2026-09-19 with people and model seats playing at a
web table (`docs/phase8-plan.md` 12). On 2026-09-20, after a
conversation about clude with a chatbot at claude.ai, David decided to
let that Claude play a seat at the table itself, during a chat with it
there. Plain API endpoints were the first idea; an MCP server was
judged the better fit, since claude.ai reaches tools through MCP
connectors and the tool docstrings double as the only instructions the
player gets. The work is the new Phase 9; the in-depth UX moved to
Phase 10 and the clean-up and release to Phase 11 (`docs/phase-plan.md`).

David brought a draft from that conversation: a `clude_mcp.py` (six
tools over `TableRegistry`, a long-polling `turn`, and a combined
Flask-plus-MCP app) and a `webgame_reading.py` (a "head": the seat's
own character numbers, computed by a shadow agent). Both sit untracked
at the repo root under `TO DO MESH WITH REPO ...` names; this plan is
the mesh, and 9b consumes them. The draft's own constraint governs
everything here: **minimal disruption to the existing code**. Nothing
here is a new game. The chat seat is an ordinary account in an ordinary
human seat, answering the engine's `DecisionRequest`s through the same
registry the browser uses, and a game with one is indistinguishable in
the store from a game without.

The three properties the draft designs for, kept as written:

- **Forgetful.** A new conversation knows nothing, and even an old one
  may have lost the early turns. Every call returns a payload that
  fully reconstitutes the player: hand, position, notepad, a digest of
  the turns that fell off the end, and the decision on the table. No
  client-side state.
- **Slow and expensive.** Each tool call costs a model round trip and
  the person a spinner, so `turn` long-polls: it drives the bot seats
  itself and comes back with the chat seat's decision or with what
  happened while it waited. One call per decision.
- **Prone to retrying.** `answer` is guarded by `seq`, which
  `TableGame.answer` already refuses when stale. Kept.

## 2. What the code dictates

Checked against the code on 2026-09-20; the draft's four "wiring"
notes each resolve as follows.

1. **The view builder.** `clude_web.views._payload` is private and
   needs a Flask request context (it reads the signed-in user and
   builds a `url_for`). The MCP layer does not need it:
   `tables.view_payload(game, document, viewer, since, replay_url,
   waiting_for)` is public and takes the viewer as a seat index, which
   `tables.viewer_seat(setup, account)` gives. Nothing to rename.
2. **The store.** `clude_storage.open_store(uri)` exists and is what
   `create_app` and the CLI use. The draft's `try/except ImportError`
   goes.
3. **Who answered.** `TableGame.answer(seat, seq, data, by=...)`
   already records ``"human"``, ``"autopilot"`` or ``"llm"`` in the
   entry; `TableRegistry.answer` does not pass it through. A one-line
   change threads it, and the chat seat answers as ``by="mcp"``, not
   ``"llm"``: ``"llm"`` is the wrapper's own marker and means "an audit
   is attached", which a chat seat has none of. The record's `llm_log`
   and every rebuild path are untouched.
4. **The head.** Neither `SeatSpec.head` nor `WebGame.head_reading`
   exists. But `WebGame.readings()` already computes exactly the
   sealed, rebuild-safe number the draft wants: a fresh agent for the
   seat's token, reset with the game seed, given
   `clude_constraints.observe(state, seat)` (the same door the engine's
   own bot sees through) and asked `select_action`. Its `ClueBelief`
   carries `probabilities` and the method's own `extra` (Peacock's
   belief/plausibility bounds, Green's arm). That is the head, in the
   method's own shape, with nothing new to persist. The draft's shadow
   agent (fed every event through `observe`) is the more faithful
   design for the learning methods, and it is exactly the trace
   fidelity question 8.1 deferred (`docs/phase8.1-plan.md`, "Out of
   scope"); it is not built here. Section 6 asks.

Other facts that shape the design:

- `TableRegistry.sit(table_id, me, token)` seats an account in an open
  seat before the deal (the draft has the arguments in another order);
  `deal` is a separate step the person who made the table takes in the
  browser. `in_progress()` lists open, playing and wrapping-up tables.
- `TableRegistry.say(table_id, game, seat, text)` is the person's line
  (240 characters, cleaned, an opportunity for the model seats); the
  draft's `registry.chat` and `game.remark(..., about="chat")` fallback
  become one call to `say`.
- There is no free-text notepad. `tables.notepad(game, viewer)` is the
  floor's auto-filled sheet: for every card, who is proven to hold it
  and who still might. The chat seat gets that in every payload, and a
  free-text note of its own is new: a string per seat in the table
  document (`document["notes"][str(seat)]`), never an entry, so a
  rebuild does not see it and the engine cannot.
- `TableRegistry.work(table_id, game)` returns ``"busy"``,
  ``"waiting"``, ``"turn"``, ``"autopilot"``, ``"model"``,
  ``"reaction"``, ``"debrief"``, ``"finished"`` or ``"nothing"``, never
  blocks on the lock, and paces bot turns by `WORK_INTERVAL`. The
  long-poll loops on it with a one-second sleep between units, exactly
  as `table.js` does from the browser, so a person and a chat seat at
  the same table drive the same work and neither starves the other.
- **One registry per process, or a race.** The registry caches games
  and writes the whole table document back; two processes over one
  store would each hold a table and the loser of a race drops an entry.
  The service already runs one gunicorn worker on at most one instance
  for this reason. So the MCP server runs *inside* the web service's
  process, sharing `app.extensions["tables"]`, not beside it.
- **The gate does not cover a mount.** `create_app` registers the
  login gate as a Flask `before_request`; an ASGI app mounted next to
  Flask is outside it. The MCP endpoint needs its own guard (section
  4.3).
- **Serving.** The Dockerfile runs `gunicorn ... "clude_web:create_app()"`
  with one worker and eight threads. FastMCP's streamable-HTTP app is
  ASGI, so the combined app is ASGI, served by gunicorn's uvicorn
  worker with Flask wrapped by `asgiref.wsgi.WsgiToAsgi` (Flask still
  runs its requests in a thread pool, so the game lock and the
  threading model do not change). Cloud Run's request timeout is
  300 s; `turn` holds a connection for 25 s.
- **The account.** The chat seat is an ordinary account made with
  `users add claude` and named to the server by `CLUDE_MCP_ACCOUNT`.
  `viewer_seat` then resolves its seat exactly as for a browser, and no
  permission code learns about MCP. Its label in `SeatRecord` is
  ``claude``, so a dossier about it accrues like a person's.
- `mcp` (the official SDK, with FastMCP) is not in the venv or in
  `requirements-web.txt`; 9b adds it, with `asgiref` and `uvicorn`.

## 3. Design

### 3.1 The server: `clude_web/mcp.py`

One module, importing `tables` and nothing that imports it. `FastMCP`
named ``clude``, the six tools of the draft with their docstrings kept
as the prompt they are (read them as written for the player, not the
maintainer), and the registry taken from the Flask app so there is one.

| Tool | Does | Calls |
|---|---|---|
| `clude_tables()` | Lists the tables the account could join or holds a seat at: id, status, turns, seats, open seats, `mine`. | `in_progress`, `viewer_seat` |
| `clude_sit(table_id, token)` | Takes an open seat as `token`. (The `head` argument of the first deploy is gone; 8.) | `sit`, then the listing |
| `clude_turn(table_id, since=0)` | Long-polls up to `POLL_SECONDS` (25): drives `work` until the decision is this seat's, the game ends, or time is up. Returns the view from `since`. | `game`, `work` |
| `clude_answer(table_id, seq, answer, accuse=None, since=0, wait=True)` | One decision, refused if `seq` is stale; a `TableError` comes back as `error` in the view rather than an exception, so the player reads it and calls `turn` again. `accuse` (false, or a triple) answers the accusation question that follows directly, in the same call; with `wait` the call then long-polls like `clude_turn`. (Both added after the first live game; 8.) | `answer(..., by="mcp")`, `work` |
| `clude_say(table_id, text)` | A line at the table, in the open. | `say` |
| `clude_note(table_id, text=None)` | Reads or wholly replaces the seat's free-text note. | the document |
| `clude_autopilot(table_id, on=True)` | Hands the seat to the floor bot, or takes it back: for a conversation about to run out. (Added after the first live game; 8.) | `set_autopilot` |

The view (`seat_view`) is `tables.view_payload` from the seat, then
reshaped for a reader that pays for every token (the shape below is
the one the first live game led to; the plan's was the screen's
payload lightly trimmed): `readings` and `tokens` dropped (every seat's
bars are Watch's and a player's business is its own), one string per
seat and per event, the events cut at a `since` cursor and capped at
`MAX_EVENTS` (60) with the rest folded into a `digest` (counts and the
last few unrefuted suggestions), the notepad one line per card in names
(`compact_notepad`, with the floor's `one_of` facts and its `solution`),
`note` only with ``since=0``. (Until the second 2026-09-21 build the
view carried a `head`; see 8.)

Errors a player can act on are messages, not stack traces: not seated
("use clude_tables to find one with an open seat"), a stale `seq`, a
finished table.

### 3.2 The driver and registry: what changes and what does not

- `clude_training/table.py`: `SeatSpec` gains `head: bool = False`,
  serialised in `to_dict`/`from_dict`, allowed only on a human seat
  (a character *is* its head; a bot has none). Nothing else in the
  driver changes: the entry log, `answer`, `rebuild` and every golden
  are untouched.
- `clude_web/tables.py`: `TableRegistry.answer` takes `by="human"` and
  passes it on; `sit` takes `head=False` and stores it on the spec;
  `WebGame.head_reading(seat)` returns
  ``{"method", "shape", "turn", "probabilities", "extra"}`` from a fresh
  agent as `readings` builds one (shared helper, cached per event-log
  length like `readings`), or ``None`` for a seat without a head; a
  `notes` dict on the document with `note(seat)` / `write_note(seat,
  text)` on the registry (a `_put`, no lock, since it touches no game).
- Nothing in the engine, the agents, the constraints, the store schema
  or the record changes. `RECORD_VERSION` stays 3.

### 3.3 Serving: `combined_app` and the container

`clude_web.mcp.combined_app()` builds the Flask app, hands its registry
to the MCP module, and returns a Starlette app with `/mcp` mounted on
`mcp.streamable_http_app()` and `/` on `WsgiToAsgi(flask_app)`. The
Dockerfile's command becomes

```
gunicorn -k uvicorn.workers.UvicornWorker --workers 1 --timeout 300 "clude_web.mcp:combined_app()"
```

with the same one-worker reasoning as before. Locally, the same app
runs under `uvicorn` for a check, and the plain Flask command in
`docs/web.md` keeps working for everything that is not MCP.

**The guard.** The mount is outside the login gate, and a claude.ai
custom connector can send an OAuth flow or nothing at all, but not a
static header. So the endpoint is a capability URL: it is mounted at
`/mcp/<CLUDE_MCP_SECRET>`, the secret living in Secret Manager beside
the Flask secret and the key, and any other path under `/mcp` is a 404.
That is the same trade `docs/web.md` ("Convenience over secrecy") made
knowingly for the login: the damage ceiling is the game store, and
what a stranger with the URL could do is play Clue as `claude`. Section
6 asks before it is built.

### 3.4 What a game looks like

David makes a table in the browser with one open seat and, if he
likes, LLM seats; remembering starts on, with an opt-out (2026-09-21).
In the chat he asks Claude to sit;
`clude_sit` seats the `claude` account; David deals; Claude calls
`clude_turn` and plays, `clude_say`ing as it goes; the game finishes
and, with "remember" on, the model seats debrief as they do now and a
dossier on `claude` accrues in the record like a person's. The replay
shows the game like any other, the chat seat labelled ``claude``.

### 3.5 Tests

`tests/test_mcp.py`, on the fake backends, with the MCP SDK's
in-memory client against the server object (no network, no HTTP):

- `clude_tables` lists an open table and `mine` flips after `clude_sit`.
- A whole short game through the tools with the other seats on
  autopilot and floor bots: every `turn` returns either a pending
  decision for this seat or a finished game; every answer is recorded
  with ``by="mcp"``; the record replays.
- A stale `seq` is refused and reported, not applied; a doubled answer
  is applied once.
- The view never carries `readings`, never another seat's hand, and
  `head` is ``null`` without a head and the method's own shape with one.
- `head_reading` at turn N equals the belief a fresh agent for that
  token holds at turn N (a pure function of seat, seed and view), on a
  rebuilt game as on the live one.
- The note survives a cold rebuild and never appears in an entry.
- `combined_app` serves the lobby at `/` behind the gate and 404s
  `/mcp` without the secret.
- `tests/test_deploy.py` gains the new packages in
  `requirements-web.txt` and the new command in the Dockerfile.

## 4. Sub-phases

| Step | What | Where |
|---|---|---|
| 9a | The plan and the renumbering, everywhere Phase 9 and 10 were named | this doc, `docs/phase-plan.md`, `CLAUDE.md`, `docs/phase8-plan.md`, `docs/phase8.1-plan.md`, `docs/web.md`, `clude_web/board_svg.py` |
| 9b | The driver and registry changes (3.2), `clude_web/mcp.py` (3.1) and its tests, all on fake backends and the in-memory client; the two draft files consumed and deleted | `clude_training/table.py`, `clude_web/tables.py`, `clude_web/mcp.py`, `tests/test_mcp.py`, `requirements-web.txt`, `requirements.txt` |
| 9c | Serving (3.3): the combined app, the Dockerfile, the secret, a deploy, the connector added at claude.ai, and one live game from the chat, costed and approved first | `Dockerfile`, `scripts/deploy.bat`, `docs/web.md` |
| 9d | The close: docs, the live numbers, "as implemented" | this doc, `CLAUDE.md`, `docs/phase-plan.md`, `docs/web.md` |

## 5. Decisions (David's)

Taken 2026-09-20:

1. **A Claude in a chat window plays a seat itself**, over an MCP
   server rather than API endpoints.
2. **Renumbered:** this is Phase 9; in-depth UX is Phase 10; tweak,
   polish and release is Phase 11.
3. **Minimal disruption:** the draft, or its idea some other way, on
   top of the existing registry and driver.

## 6. Open questions

Asked, not assumed; what I will do unless told otherwise is in
brackets.

1. **The guard on the public URL** (3.3): a secret path segment
   [yes], or nothing, or an OAuth server of our own [no: weeks of work
   for a family game].
2. **The account name** for the chat seat [`claude`]: it becomes the
   label in every record and the name at the table.
3. **The head** (2, item 4): the fresh reading `readings` already makes
   [yes], or the draft's shadow agent fed every event [later, together
   with the trace fidelity question, if the learning methods' heads
   turn out to matter].
4. **The serving change** (3.3): gunicorn's uvicorn worker over the
   combined ASGI app [yes]. The alternative, a second Cloud Run service
   for MCP, is the two-registries race and is not proposed.
5. **Whether `head` defaults off** [yes, as the draft says: the
   clueless arm is the cheaper and the more surprising one].

## 7. Out of scope

A chat seat making or dealing a table (the person does, in the
browser); a chat seat in the arena or the CLI; a chat seat that is also
a model seat (the wrapper's leash is the character's, and a chat
player has no character); OAuth; websockets; the shadow-agent head;
any change to a method, a dial, a preset, a persona or `rules.md`;
Phase 10's look.

## 8. As implemented

**9a (2026-09-20):** the renumbering above, and this plan.

**9b, and the code side of 9c (2026-09-21).** Built on the plan as
written, from the two drafts; where it departs, the departure is here.

- `clude_training/table.py`: `SeatSpec.head` (default False; only a
  human seat whose token has a character may take one), written to a
  setup only when set, so every stored setup and every golden reads as
  before; `answer`'s `by` documents ``"mcp"``. Nothing else in the
  driver changed.
- `clude_web/tables.py`: `TableRegistry.answer(..., by="human")` passes
  `by` through; `sit(..., head=False)`; `WebGame.fresh_belief(seat,
  label)` factored out of `readings` and shared with the new
  `WebGame.head_reading(seat)` -- method, `shape` (from `HEAD_SHAPES`),
  turn, probabilities rounded to four places, and the method's `extra`
  made JSON by `jsonable`; cached per event-log length like `readings`;
  None without a head -- and `note` / `write_note` on the registry,
  `document["notes"][seat]`, at most `MAX_NOTE` (8,000) characters, a
  `_put` with no lock.
- `clude_web/config.py`: `mcp_secret()` (`CLUDE_MCP_SECRET`, the
  environment then `.env`) and `mcp_account()` (`CLUDE_MCP_ACCOUNT`,
  default ``claude``).
- `clude_web/mcp.py`: `build_server(registry, account)` returns the
  server -- a factory over any registry rather than the draft's module
  singleton, so a test builds one over a temp store and `combined_app`
  one over the Flask app's own -- with the six tools as closures and
  their docstrings the prompt; `seat_view` and `digest` are module
  functions. The SDK installed is mcp 2.x, where the draft's `FastMCP`
  is `MCPServer` (`mcp.server.mcpserver`). A `ToolError` is what the
  model reads for "not seated", "no such table" and "not dealt yet"; a
  `TableError` on an answer comes back as `error` in the view, on a
  line or a note as `{"error": ...}`. `clude_turn` is a sync tool (the
  SDK runs it in a worker thread) looping on `registry.work` with
  `SLEEP_SECONDS` between idle units, and returns as soon as the game
  is finished: it does not drain debriefs, which stay the browser's
  `work`. `clude_sit` returns the listing entry and a message, since
  there is no game to view before the deal. The digest counts the
  dropped lines and names the suggestions nobody could disprove, read
  from the events themselves rather than the line text. `over.replay`
  is the path `/replay/web/N`, not a `url_for`.
- `combined_app(settings=None, secret=None, account=None)`: a Starlette
  app with `Mount("/mcp", <the SDK's streamable-HTTP app at
  "/<secret>">)` and `Mount("/", <Flask>)`, the outer lifespan running
  the SDK's session manager (a mounted app's own lifespan never runs).
  Three choices the plan did not make, each for a reason found in the
  code: the transport is **stateless with JSON responses**, so there is
  no session to lose when the instance scales to zero and a long-poll
  is an ordinary request; the SDK's localhost-only Host check is
  switched off, since it would reject Cloud Run's hostname and the
  secret is the guard; and the Flask bridge is asgiref's `WsgiToAsgi`
  with its thread-sensitive lane turned off, because asgiref's default
  runs every WSGI request on one thread one at a time, which would
  undo what `--threads 8` bought. Without a secret the endpoint is not
  mounted and the app is Flask under the bridge, so a deploy before
  the secret exists still serves the game. A secret must be 16 to 128
  URL-safe characters.
- `Dockerfile`: `gunicorn -k uvicorn.workers.UvicornWorker --workers 1
  --timeout 300 "clude_web.mcp:combined_app()"`; `requirements-web.txt`
  and `requirements.txt` gain `mcp>=2.0`, `asgiref>=3.8` and
  `uvicorn>=0.30`. `scripts/deploy.bat` is unchanged until the secret
  exists in Secret Manager (9c; the commands are in `docs/web.md`, "A
  seat over MCP").
- `tests/test_mcp.py` (14 tests on the SDK's in-memory `Client` against
  the server object, async under anyio): the listing and `mine`;
  sitting where one cannot; a whole game through the tools with Mustard
  and White as characters, every answer ``by="mcp"`` with no audit,
  recorded under `claude` with ``kind="human"``; the digest; the stale
  and the doubled answer; the view without `readings`, `tokens` or
  another seat's hand; Peacock's head equal to a fresh agent's belief
  live and on a cold rebuild, and the `SeatSpec` refusals; `head` null
  without one; the note across a cold rebuild and never in an entry; a
  line said and an empty one refused; the combined app (the lobby
  behind the gate, a wrong secret a 404, an `initialize` under the
  right one a 200 with Cloud Run's Host header), no secret no mount, a
  bad secret refused, and three overlapping Flask requests on three
  threads. `tests/test_deploy.py` pins the new command and packages.
- The two draft files at the repo root are consumed and deleted.
- Suite after: 454 passed, 16 skipped.

Not built, as planned: OAuth, the shadow-agent head, a chat seat that
makes or deals a table.

**9c up to the deploy (2026-09-21).** Done as `docs/web.md` ("A seat
over MCP") records: `clude-mcp-secret` made in Secret Manager (32
characters from `secrets.token_urlsafe(24)`, written from a file so no
newline rides along) with Secret Accessor for `clude-run`;
`CLUDE_MCP_SECRET=clude-mcp-secret:latest` added to the `--set-secrets`
list in `scripts/deploy.bat` and the docs; the `claude` account made on
the bucket; revision `clude-00006-mlg` deployed. Live probes: the login
page 200 (3.1 s, a cold start), a wrong secret a 404, `initialize` under
the right one 200 in 179 ms, `tools/list` the six tools; the SDK's own
streamable-HTTP client listed the tools in 0.7 s and `clude_tables`
answered as `claude` in 0.8 s, a missing table coming back as a
message. The documented live check (`live_check.bat play`) then tripped
mid-game: Cloud Run replaced the instance at 18:45:54 ("AUTOSCALING",
no error logged; the lobby page had taken 6.5 s just before), the poll
that met the fresh instance took 13.5 s (an 8 s worker boot plus the
rebuild), and the script's assumption that two consecutive polls see
one instance failed -- not the game. `live_check.bat resume` on the
same table found the cold rebuild in 0.1 s at the same pending
decision and played it to the end (63 turns, `runs/web/11`, the replay
opens). Timings on that resumed game: poll median 112 ms, answer
1,113 ms, a unit of bot work 1,074 ms (n = 67, 65, 53), against 93,
850 and 820 ms measured under the threaded worker on 2026-09-19 -- one
sample, about a quarter slower, worth watching rather than acting on.
The throwaway accounts were removed. Left: the connector at claude.ai
and one live game from the chat, then 9d.

**9c, the first live game from the chat (2026-09-21).** The connector
was added at claude.ai and an Opus there played Plum at table
`8de30daff8` through the tools: it sat, waited for the deal, played 30
turns, wrote its deductions to its note, and stopped on purpose with
the chat nearly full and the table waiting on it. Its report is the
finding of the test: every call came back with about 9,000 tokens (the
whole notepad as 21 objects with seat numbers, every event line, every
seat, the note) and a turn took two to four calls, so the conversation
would have run out around turn 30 to 40 of a 60-turn game. It also
asked for autopilot, which the browser has and the tools did not, and
raised the notepad not recording a pass (Peacock unable to disprove a
Knife) or a disjunction (Green holds Plum or the Wrench). Fixed the
same day, on the fake backends, in `clude_web/mcp.py` alone plus one
registry change:

- **The view is compact.** `seat_view(registry, table_id, game, seat,
  since=0)`: one string per seat (``"Plum: claude (you)"``, ``", on
  autopilot"``, ``", out (accused wrongly)"``), one string per event
  (``"12 (turn 5) Mustard moves to Hall."``), `waiting` a sentence, the
  movement options without the screen's coordinates, and everything the
  screen needs and a player does not (`llm`, `debriefs`, `work`,
  `chatter`, `offer_autopilot`, `remember`, `wrapping_up`) left out.
- **`since`** on `clude_turn` and `clude_answer`: the events from that
  index on (the `n_events` of the last view), the digest folding only
  what is cut between it and the `MAX_EVENTS` cap; and `note` comes
  only with ``since=0``, the call a fresh conversation makes, since a
  note of 8,000 characters in every view was the other half of the
  cost. Measured on a 6-seat table at turn 35 with a 2,000-character
  note (`json.dumps` length over four): the old view about 2,700
  tokens, the new since-0 view about 1,700, the new view from a cursor
  six events back about 430.
- **The notepad** is `compact_notepad`: per card the proven holder
  (``me``, a token, ``envelope``) or the holders still possible joined
  with "or", in names rather than seat numbers; `one_of`, the floor's
  open or-constraints ("Green holds at least one of: Plum, Wrench"),
  which `tables.notepad` never carried; and `solution` once all three
  are proven. The pass was never missing: `propagate` strikes every
  skipped seat from the three cards, and a test now pins that the
  compact lines show it. What Opus saw was the seat-number rows, and
  the disjunction, which the browser's rows do leave out.
- **`accuse`** on `clude_answer`: ``false`` passes the accusation
  question that follows this answer directly, a triple makes it, in the
  same call; checked before anything is applied (``true`` or a
  malformed triple refuses the whole call); given with a move into a
  room, where the suggestion question comes first, it is set aside and
  `notice` says so. And **`wait`** (default on): after answering, the
  call long-polls exactly as `clude_turn` does, so `pending` is usually
  set when it returns. A turn is then two calls (the move; the
  suggestion with the accusation folded in) rather than four, and
  `clude_turn` is for the first decision and for a call that came back
  with nothing pending.
- **`clude_autopilot(table_id, on=True)`** calls the registry's
  `set_autopilot`, which now drains every decision of the seat's in a
  row (it answered one and left the next to the following `work`);
  `clude_tables` shows `my_autopilot`. While on, `clude_turn` only
  watches.
- `tests/test_mcp.py`: 21 tests (from 14): the whole game now played
  the way a player would (`clude_turn` once, then `clude_answer`
  waiting), the view's shape, `since` and the note, an answer that
  waits, `accuse` folded through a whole game with no accusation ever
  put as a decision of its own, `accuse` too early or malformed, the
  pass and the `one_of` facts against the browser's rows, and the
  autopilot handover and return.

Not changed: the driver, the engine, the record, the browser's
notepad. The live game at `8de30daff8` has since finished (turn 47,
`runs/web/12`), with Opus's 757-character note still on its document.

**Later the same day: no head, stuck tables, the deal (2026-09-21).**
Four decisions of David's after the first live game, built at once:

1. **No head.** "MCP players get their numbers from floorbot, that's
   it. No heads! They're the head!" `SeatSpec.head`, `sit(head=)`,
   `WebGame.head_reading`, `HEAD_SHAPES`, `jsonable` and the `head`
   argument of `clude_sit` are removed; `SeatSpec.from_dict` ignores a
   stored ``head`` key, so a setup saved between the two deploys reads
   as a plain human seat. Open question 3 and 5 of section 6 are
   thereby closed the other way: not the fresh reading, nothing. The
   chat seat's numbers are the notepad, which is the floor.
2. **Killing a table.** `TableRegistry.abandon(table_id, me=None)`
   sets the document's status to ``abandoned``, drops the live game,
   and never records it; `me` must be seated or the starter, and None
   is the maintainer. `POST /tables/<id>/abandon` with an "End table"
   button (after a confirm) in the lobby and on a waiting table's page,
   for anyone seated or the starter; `clude_cli.py tables list |
   abandon ID --uri STORE` from outside the app, which is how the two
   tables David could not get out of are ended on the bucket before the
   deploy. `in_progress` skips abandoned tables, `game` returns None
   for one, and `clude_turn` says "was ended".
3. **A player who stops responding.** Two rules in `work`, whoever
   drives it: a human seat that has kept the table waiting
   `AUTOPILOT_AFTER` (180 s) is handed to the stand-in, its flag set as
   if the button had been pressed (so "Take my seat back" undoes it);
   and a human seat that is out (a wrong accusation) is the stand-in's
   without any flag, since all it has left is cards to show. A chat
   seat is a human seat for both. Before this, a table waited for
   ever, and the ten-minute mark only *offered* the handover to the
   others.
4. **The deal is held** until every open seat is taken: `deal` refuses
   with the seats still waiting named, the page's button is disabled
   and its note says so. `TableSetup.dealt` (open seats to floor bots)
   stays as the driver's operation but the registry no longer reaches
   it with an open seat. A table nobody comes to is ended instead.

Tests: `tests/test_mcp.py` 22 (the head tests replaced by "the floor's
numbers and nothing else" and "an ended table says so"),
`tests/test_web_tables.py` gains the deal rule, ending a table (by a
player, the starter, twice, and the maintainer), the ten-minute
handover and the out player answered by the stand-in.

### Eight fixes after game `7075f3ae29` (2026-09-22)

The second live game from the chat, with David at the browser and an
Opus at claude.ai on Scarlett's seat. Both came away with a list: four
about the table screen, four from the chat seat. Two of them turned out
to be one bug.

**The seq, which was the root of two reports.** `TableGame.seq` was
`len(self.entries)` and `remark()` appends an entry, so every line of
table talk invalidated the decision that was waiting. For the chat seat
that was "my answer comes back as out of date" -- four tries for one
suggestion while Scarlett and Peacock chatted. For the browser it was
half of the dropdown reset: with chatter queued a table polls every
1.5 s, not 10 s. `seq` now counts answers (`TableGame._answers`), and
the four internal callers that quoted `len(entries)` quote `self.seq`.
Remarks are still entries -- the rebuild needs them at their place in
the log -- they just no longer move the number an answer must match.
`seq` is never stored, so no document migrates.

**What was built, in the order it was done:**

1. **The seq fix** (`clude_training/table.py`). Above. Pinned by
   `test_table_talk_does_not_stale_the_decision_it_interrupts` and
   `test_table_talk_does_not_stale_the_decision_waiting_on_the_seat`,
   both of which fail on the old definition.
2. **`accuse` folded into a suggestion now lands** (`clude_web/mcp.py`).
   It was tested against whatever was pending the instant the answer
   landed, but a suggestion is refuted first, and a refuter who is a
   person or a model seat pauses the game in between. `clude_answer` now
   runs `await_turn` first and answers the accusation when it arrives.
   The test builds the case deliberately -- Mustard a person on
   autopilot, seated next after the chat seat, named from its own hand --
   because no seed in the suite produced it.
3. **The board, once** (`clude_core/board.py`, `clude_web/mcp.py`).
   `BOARD_LEGEND` joins `BOARD_MAP` as a constant and is appended to
   `docs/ux/board_map.txt` (`tests/test_board.py` now pins both halves);
   `mcp.BOARD_PICTURE` is the two together, ~1,200 characters, sent with
   `clude_sit` and with a `since=0` view and never on a turn. `me` gains
   `at`, the seat's own position, so the picture has an anchor.
4. **Distances on every move** (`clude_web/tables.py`). Each movement
   option carries `distances`, every room nearest-first, from
   `board.room_distances` -- already cached, already what the characters
   and the floor bot score moves with, so nothing new was written. The
   browser puts the same string in the button and board-target tooltips.
5. **A spent budget is announced** (`clude_web/mcp.py`). The chat seat
   reported that "every character falls back to the floor bot"; it does
   not. `MeteredBackend` returns an error result and the wrapper falls
   back to the agent's own method, the floor bot being only ever the
   autopilot stand-in. The seat guessed because `seat_view` strips
   `last_refusal`; a `models` line now says so when a wrapper is
   refusing, and the spent-budget test pins that no answer of that seat
   is ever entered `by="autopilot"`.
6. **The Accuse panel** (`table.html`, `table.js`, `style.css`). Its own
   panel, always shown, shut by default. Its three dropdowns are built
   once at startup and the render loop never touches them, so an
   accusation set up on turn 3 is still there on turn 9. The button is
   disabled until the accusation question is yours (David: disabled, not
   armed) and the panel takes a red border when live; the decision panel
   keeps Pass and points at it.
7. **The dropdowns stop resetting** (`table.js`), David's high-priority
   report. `renderDecision` tore the panel down on every poll;
   it is now keyed on `kind + "#" + seq` and returns early when the
   decision has not changed, which the seq fix makes exact. As a safety
   net `keptValues()` snapshots the selects by name before any rebuild
   and `select()` restores them.
8. **Table Talk, its own panel** (`tables.py`, `table.html`, `table.js`,
   `style.css`). Events carry `about`, and every remark -- a person's
   `chat`, an agent's on-turn aside, a model seat's off-turn `reaction`
   -- goes to a "Table Talk" panel above the log, with the say box; "The
   game so far" keeps the moves, suggestions and accusations. This also
   lit up `.log li.kind-remark.about-chat`, a rule that had never
   matched anything because `describe_event` dropped `about`.
9. **No deduction bars for a seated player** (`tables.py`, `table.js`,
   `table.html`). David's call on the fourth report, and he was right
   about the reason where I was wrong. I argued the bars were only
   deduction progress and that nothing in the payload had ever exposed
   a hand. Measured (seed 7, six seats), that is false: a seat begins
   having proven exactly one thing, its own hand, so `placed` per
   category *is* that seat's hand composition, for every seat, until
   other deductions dilute it --

   | turns | seats whose bars read exactly as their hand composition |
   |---|---|
   | 0-9 | 6 of 6 |
   | 12 | 5 |
   | 15 | 4 |
   | 18 | 3 |
   | 21 on | 0 |

   The real game does not mark card backs by category either: the three
   stacks are separated only to build the envelope, then the remaining
   18 are shuffled together and dealt, and the backs are identical. So
   dropping the bars for a seated player closes a real leak over roughly
   the first quarter of a game, not merely a fairness nicety.
   `renderSeats` draws a plain roster instead and the footnote
   explaining the bars goes with them; `view_payload` sends
   `readings: None` to a seated viewer, which also spares a fresh belief
   per poll -- most of a second for Plum. **A spectator and Watch still
   see the bars, and so still see that much** (David, 2026-09-22: a
   spectator whispering hands to a player is a social problem, not a
   software one).

Tests: 492 passed, 2 skipped (the live-credential ones) with browser
tests enabled; 474 and 20 skipped without. Ten new tests --
`tests/test_table.py` 1, `tests/test_mcp.py` 4, `tests/test_web_tables.py`
2, `tests/test_browser.py` 3 -- and each of the three behaviour fixes
was checked to fail with its fix reverted. Every screen was
re-screenshotted in both themes at both widths and looked at: that is
what caught the bars footnote still being shown to a player who no
longer has bars, and the placeholder lines being numbered "1.".

**Not deployed.** This stacks on the 9b/9c follow-up work already marked
"to deploy", so one deploy covers both. (It covered 9e too: revision
`clude-00010-knh`, the evening of 2026-09-22; see 9f.)

### Phase 9e: spectators, the memory default, folding logs (2026-09-22)

David's follow-ups to the eight fixes above, plus one bug they turned up.

1. **The spectator gallery.** Watching and being unable to act already
   worked -- the answer, say and autopilot routes have returned 403 to a
   seatless viewer since 8.2 -- so this adds presence only.
   `TableRegistry` gains `seen_watching` and `watching`: asking for a
   view of a table you do not sit at puts you in its gallery for
   `WATCHING_FOR` (45 s, outlasting a hidden tab's 15 s poll), so a
   closed tab leaves by itself. It is kept in memory, not on the
   document, since a poll arrives every few seconds from every open page
   and the fact is true only for the next few; a restarted process
   relearns it. `view_payload` carries `watching` to a seated viewer,
   and the screen shows the line only when somebody is there.
   **Signed-in accounts only** (David): the table id does not become a
   capability URL, and the MCP endpoint stays the only route outside the
   gate.
2. **The bars, corrected.** David was right and the note in item 9 above
   was wrong; it now carries the measurement. **Spectators and Watch
   keep the bars knowingly** (David, 2026-09-22): a spectator telling a
   player what is in them is a social problem, not a software one.
3. **The memory slider starts at 1.0**, the whole logbook, where it
   started at 0, the condensed head (`tables.DEFAULT_MEMORY`). Only the
   lobby form moved: `SeatSpec.memory` still defaults to 0 for the
   driver and the CLI, and a saved table keeps what it was made with.
   The memory block is a cached system block stable for a whole game, so
   the depth is written once and read at a tenth of the price on every
   call after; the cost grows with the logbook, which is worth watching
   as entries accumulate.
4. **"The game so far" and "Table Talk" fold away**, as `<details>`
   panels open by default, the heading being the handle. A list appended
   to while its panel was shut scrolls to the bottom when it reopens.
   The collapsed state is not remembered between page loads; nobody
   asked for that.
5. **A seat whose budget is spent is no longer queued to speak**
   (`clude_web/chat.py`, `refusing`). Turning the memory default up made
   the spent-budget test hang, which exposed a real defect rather than
   causing one: a refusing backend can never produce a line, since
   `react` needs a call and gets an error result, but
   `Reactions.opportunity` queued the seat anyway and `work` then
   answered "waiting" for the reaction's two to eight seconds before
   serving nothing. A table whose budget ran out both crawled and went
   quiet. Measured: it could not reach its end in 1,500 requests before,
   and finishes in 148 with no waiting step after. Probably part of what
   the chat seat meant in its fourth report.

Tests: 496 passed, 2 skipped with browser tests enabled (477 and 21
without). Three new --
the gallery (`tests/test_web_tables.py`), the refusing seat
(`tests/test_chat.py`), the slider default (`tests/test_web_llm.py`) --
and a browser test for the folding panels; the chat fix was checked to
fail with it reverted.

### Phase 9f: the chat seat's report after game `b089937cb8` (2026-09-25)

The third live game from the chat (2026-09-24): an Opus at claude.ai as
Plum, David as Green in the browser, Scarlett and Peacock as model seats;
Scarlett won at turn 41. Asked afterwards, the chat seat called the
notepad "genuinely good design -- it's doing the tedious part so I can
do the fun part", and named three things. The measurements below come
from rebuilding the table from the bucket.

**Deployed after all.** Revision `clude-00010-knh` went live on
2026-09-22 at 16:15 MDT, a minute after the documentation commit, so
9d and 9e were not waiting on a deploy as this doc and `CLAUDE.md` said.
This game ran on them: the distances it found heavy were 9d's.

1. **A move is one line per room** (`clude_web/mcp.py`). Plum's ten
   movement decisions averaged 9.7 legal moves and reached 26, each with
   the nine-room line 9d added: the block averaged 1,798 characters and
   reached 4,717, three quarters of the view at that point. What the
   seat wanted was the move heading for the room it had in mind, and it
   suggested either a per-room summary or naming the room. Both are
   built as one thing. A movement's `pending` carries `toward` instead
   of `options`: for each room, nearest first, what the best move toward
   it does ("enter it now", "enter it now, by the secret passage", "3
   steps short, ending at row 13, col 19", "1 step short, ending in the
   Conservatory"). `clude_answer` takes `{"toward": "Library"}` and
   `_resolve_toward` turns it into that move before the registry sees
   it, so the log, the record and the rebuild hold an ordinary
   `{"move", "to"}`; it does so only when the snapshot is this seat's
   movement at the quoted `seq`, and otherwise leaves the refusal to
   `TableGame.answer`. "Best" is `board.room_distances`, the cached
   proximity the characters and the floor bot already score moves with,
   ties to `board.node_sort_key` then the move's kind. A move named
   outright is still accepted. The block is now 512 characters on
   average and 545 at most, whatever the roll. The browser is unchanged:
   `tables.view_payload` still sends every option with its distances.
2. **Waiting is cheaper** (`clude_web/mcp.py`). The seat got four or
   five empty replies in a row while David thought, each a whole view,
   and asked for a longer hold or a sign that the wait would be long.
   - `POLL_SECONDS` 25 to 60. claude.ai documents about 300 s a tool
     call (one report shows 180 s), and Cloud Run and gunicorn allow
     300 s. A person holds the table at most `AUTOPILOT_AFTER` (180 s),
     so that is at most three idle replies a turn, down from seven.
   - One deadline per call. `clude_answer` with `accuse` waited twice
     -- for the accusation question, then for the next decision --
     each a whole poll, so a suggestion a person must disprove could
     hold 2 x `POLL_SECONDS`: at 60 s, two minutes. `await_turn` now
     takes the call's deadline.
   - A reply whose new lines are all moves or table talk
     (`QUIET_KINDS`), or that has none, sends `"unchanged"` for the
     notepad and the seats, which cannot have moved; `me`, `waiting` and
     `pending` always come. A cursor past the end of the log is taken as
     0. Measured over David's ten turns: an idle reply 1,527 characters
     before, 467 after.
   - `waiting` says when the floor bot takes a person's seat ("the
     floor bot takes the seat at 180 s"), and `clude_turn`'s docstring
     says an empty reply is normal while a person thinks, to call again
     with the same `since`, and that a reply with nothing new is short.
     It also corrects "up to half a minute" to a minute.
3. **A warning in `clude_say` against naming one's own hand: declined**
   (David, 2026-09-25). The seat said its hand aloud early on until
   David told it not to, and asked for one line in the tool's
   description. Talk and bluffing about one's own cards are allowed and
   players learn what over-sharing costs, so the description stands.
   The seat wrote the lesson into its note, which is kept per table, so
   it does not reach the next game.

Not built: folding the suggestion into the move call (one call rather
than two for a turn into a room; next if the number of calls still
matters), a note that outlives its table, and progress notifications
during a hold (the transport is stateless JSON).

Tests: `tests/test_mcp.py` 30 (from 25). `simple_answer` moves
`toward` the nearest room, and the whole-game test checks nine lines and
no `options`. New: every room's line against a brute force over the
offered moves, and the move a `toward` answer makes; an unknown room and
a stale `seq` refused, and a move named outright accepted; an idle reply
with Ann holding the table; the notepad resent exactly when a line since
the cursor could change it, checked from every cursor of a game; and
one call holding one poll at most, on a stand-in clock. That last test
was checked to fail with the old second deadline (20 s against a 10 s
poll). 482 passed, 21 skipped; 501 passed, 2 skipped with browser tests
enabled.

**Not deployed.**
