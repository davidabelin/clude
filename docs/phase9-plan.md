# Phase 9: a seat over MCP

Planned 2026-09-20. Status: 9a (this plan and the renumbering) done;
9b-9d not started. The "as implemented" section at the end is written
as the work lands and wins over the plan above it where they differ.

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
| `clude_sit(table_id, token, head=False)` | Takes an open seat as `token`; fixes the arm for the game. Returns the view. | `sit`, then the view |
| `clude_turn(table_id)` | Long-polls up to `POLL_SECONDS` (25): drives `work` until the decision is this seat's, the game ends, or time is up. Returns the view. | `game`, `work` |
| `clude_answer(table_id, seq, answer)` | One decision, refused if `seq` is stale; a `TableError` comes back as `error` in the view rather than an exception, so the player reads it and calls `turn` again. | `answer(..., by="mcp")` |
| `clude_say(table_id, text)` | A line at the table, in the open. | `say` |
| `clude_note(table_id, text=None)` | Reads or wholly replaces the seat's free-text note. | the document |

The view (`_view`) is `tables.view_payload` from the seat, then
trimmed: `readings` and `tokens` dropped (every seat's bars are Watch's
and a player's business is its own), the event lines capped at
`MAX_EVENTS` (60) with the rest folded into a `digest` (counts and the
last few unrefuted suggestions), plus `seat`, `note` and `head`. `head`
is ``null`` when the seat has none, and the docstrings say so, because
a seat that cannot tell which arm it is in narrates confidence it does
not have.

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
likes, model seats and "remember"; in the chat he asks Claude to sit;
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

Nothing yet beyond 9a (2026-09-20): the renumbering above, and this
plan.
