# The web app

`clude_web` serves browser pages and MCP over one TableRegistry. Read [architecture](architecture.md) for contracts and [CLI](cli.md) for store/account commands. This guide owns local configuration, viewer permissions, request-driven lifecycle and deployment.

## Running it locally

From the repo root, provide a stable `FLASK_SECRET_KEY` through the environment or ignored `.env`, then:

```powershell
& .venv\Scripts\python.exe scripts\clude_cli.py users add NAME --uri data/llm
& .venv\Scripts\python.exe -m flask --app clude_web run --debug
```

Open <http://127.0.0.1:5000/>. Flask alone serves browser pages; use the combined ASGI app below to add MCP. Missing session secrets refuse startup. `TESTING` permits an ephemeral key only when no configured secret exists; tests should pass explicit overrides to avoid ambient credentials.

| Variable | Default / purpose | Direct `.env` fallback in web config |
|---|---|---|
| `FLASK_SECRET_KEY` | Required stable session secret | Yes |
| `CLUDE_WEB_STORE` | `data/llm`, local path or `gs://` URI | No |
| `CLUDE_WEB_HTTPS` | Off locally; enable for HTTPS cookies/proxy handling | No |
| `ANTHROPIC_API_KEY` | Optional key enabling LLM seats | Yes |
| `CLUDE_LLM_MODEL` | `claude-opus-5`, configured model ID | No |
| `CLUDE_WEB_LLM_BUDGET` | $2 per table, adjustable at creation | No |
| `CLUDE_WEB_LLM_DAILY_CAP` | $10 per UTC day for the service | No |
| `CLUDE_MCP_SECRET` | Optional URL-safe secret path segment, 16-128 characters | Yes |
| `CLUDE_PUBLIC_URL` | Optional base URL for absolute replay links | Yes |

`config.read_env_file` reads selected values without exporting the file. Flask's CLI can additionally load `.env` through python-dotenv; direct Python/uvicorn scripts do not. The CLI's account commands require explicit `--uri` when the app store differs from `data/llm`.

## Accounts

There is no signup page. [CLI users](cli.md#users) creates/lists/changes/removes accounts. Keys are lower-case and case-insensitive; displayed names capitalize parts separated by `-`, `_` or `.`. Records and opponent dossiers retain the account key across token changes. Reserved suspect/bot names cannot be user identities.

### Convenience over secrecy

The private-game policy deliberately accepts any non-empty password, defaults new accounts to `password`, and displays/prints passwords in the UI/CLI. Only hashes reach storage. First login offers a change once; accepting or declining settles the offer. Later changes use `users passwd`. Removing an account leaves game records and logbooks.

## The gate

`auth.require_session` is an app-wide gate: new Flask routes are private unless marked `@auth.public`. Login, privacy and Wikiclude are public, as are assets required to display them. Spectating live games still requires an account. MCP is mounted outside Flask's gate and has its own secret-path/account-login checks.

Form POSTs require the session CSRF token, regenerated at login. Rate limits count attempts per name in memory; successful login clears them. Authentication uses a dummy hash for nonexistent accounts. Cookies are HttpOnly/SameSite=Lax, plus Secure under `CLUDE_WEB_HTTPS=1`; that setting also enables Cloud Run proxy handling. One worker/instance is part of the design, not a scaling suggestion.

## Layout

| Module / asset | Responsibility |
|---|---|
| `__init__.py`, `config.py`, `auth.py`, `users.py` | Factory, settings, gate and accounts |
| `tables.py` | Registry, persistence, work, timeouts, viewer payloads and memory |
| `watch.py` | All-bot Watch adapter over the same driver |
| `chat.py` | Off-turn reaction queue/pacing |
| `views.py`, `templates/` | Routes and Jinja pages |
| `mcp.py` | Tools, compact views, login tokens and combined ASGI factory |
| `board_svg.py`, `logo.py` | Geometry with stylesheet-controlled color |
| `replay_data.py` | Event frames, reconstructed beliefs and trace cache |
| `styles.py`, `static/styles/` | Look selection, tokens and shared chrome |
| `static/table.js`, `replay.js`, `lobby.js` | Browser polling, forms and rendering |
| `static/sound.js`, `static/sounds/` | Opt-in sound playback and six synthesized cues |
| `wiki/` | Separately maintained encyclopaedia |

## The board and the replay data

`board_svg(tokens)` generates geometry from the engine map; `dressed=True` adds decoration. Shapes carry classes rather than colors. Coordinate changes belong in the board, not copied UI maps.

`event_frames(record)` folds events into board/log frames. `cached_trace` computes beliefs once and stores `traces/<run>/<index>.json`; version/checkpoint changes rebuild it. These estimates use fresh agents/current weights, no restored method memory and no Green outcome feedback. White reconstructs her current-game chain from history. The payload's `limitation` explains why reconstructed traces can differ from what a live agent believed. Archived ring records remain readable.

## The lobby

- **Play:** six token rows, choices **empty**, **open**, **floorbot**, **me**, **X (LLM)**, **X (headless)**. Three to six occupied/reserved seats; empty omits a token, open reserves it. Named characters stay on their own tokens. LLM seats are disabled/refused without a key.
- **Tables:** unfinished games and games wrapping up, with occupants/status. Open seats must all fill before someone seated deals. A starter or seated player can end the table.
- **Watch:** an all-bot game, stepped from buttons; no model calls.
- **Stored games:** practice (`web`, `/practice`) and development (other runs, `/development`). Run summaries supply listings; records load when opened. Columns include seats, winner, turns, suggestions and wall time; Cost appears only in Developer. Older records/arena games may lack wall time.

New Play/Watch forms remember by default. Unchecking submits `remember=0`; missing form fields mean on. Saved setups keep their setting, and old documents missing `remember` load as false. Narrative depth is separate: a new lobby LLM seat starts at 1, while SeatSpec/CLI defaults remain 0.

## A table

`/tables/<id>` renders the board, current decision, own hand/notes, roster, Talk and Record. One decision form is active at a time: legal movement, optional suggestion, accusation/pass, or mandatory card show. Accuse is a persistent panel whose button activates only at the accusation question; confirmation protects accidental submission. Pass/No suggestion are also available above the board.

A player's hand includes marks for cards already shown, never removes them. Method one-liners and public hand sizes appear on the roster. Everyone sees certainty tags; **a seated viewer gets no `readings` key**, even in embedded page data. Private shown cards are named only to suggester/refuter. Spectators see board/log/Talk and compact readings, without hands, notes, decisions or chat controls. Readings can indirectly expose hand composition; that spectator-to-player social boundary was accepted explicitly.

### Request-driven lifecycle

Nothing advances between requests. Browser polls call `GET /tables/<id>/poll?since=N`; due work calls `POST /tables/<id>/work`. A work request performs one paced unit: a bot turn, model decision, reaction or debrief. The first caller takes a nonblocking lock; others return. Polls read published snapshots without waiting behind model calls.

Answers POST form data with CSRF and the pending **answer sequence** `seq`, not event/entry count. Stale/doubled/invalid answers are rejected before sending into the engine generator. The browser preserves form choices until the pending kind/sequence changes, so chat/polls cannot reset dropdowns.

Decisions allow 90 s, speed tables 30 s, card shows at most 30 s. The next work request after expiry has FloorBot finish that turn. Three consecutive timed-out turns hand the seat over; chat does not reset the timer. The deadline is in memory and restarts on cold rebuild. Autopilot belongs to the seat's owner, who may take it back. Eliminated seats use the stand-in for mandatory reveals.

`tables/<id>.json` persists setup, ordered answers/events, memory snapshot and status (`open`, `playing`, `finished`, `abandoned`). A cold registry rebuilds by replaying entries; single-flight rebuild prevents duplicate reconstruction. LLM answers/audits/remarks are stored, so restore makes no model calls. Numerical rebuild cost depends on game length and memory, not the old PlumOG timings alone.

### Memory, talk and cost

Remembering loads Mustard/White/Green method memory and attaches narrative logbooks to LLM seats before dealing. The table snapshots the memory inputs for deterministic rebuilds. Finish folds the record into method memory; remembering LLM seats then write one debrief per work request. No browser/MCP request means no further wrap-up work. [Logbooks](logbooks.md) owns schema and depth rules.

Human talk is capped at 240 characters. A line/suggestion/accusation can queue model reactions, paced and bounded by participation, reply depth, per-turn/game limits and budgets. Chat claims never affect formal refutation.

Each model backend is metered by table, seat and UTC day. The table budget persists across midnight. Caps/unpriced models cause numerical fallback; costs never reach character prompts or logbooks. Final costs include debriefs and are settled on table, record/seat and web summary after wrap-up. Ending during wrap-up records spend so far. Older totals can be backfilled with `tables costs --write`, without inventing missing seat splits.

Historical observation (2026-09-25): over the first nine web games with model seats, debriefs made up 38% of the bill ($1.69 of $4.40). Cost lines, bars and columns are now shown only in Developer, including MCP views according to the chatbot account's look.

End table removes an unfinished game from the lobby without recording it. Finished records remain. Stored practice games are omniscient in replay.

## The Watch screen

Watch uses the same registry/driver with no external people or models. Next turn advances once; Play to the end finishes and opens replay. Before finish it hides hands/envelope/private shown cards, but exposes compact readings. Remembering updates method memory; no narrative entry or API spend occurs.

## The replay screen

Replay is face up: board, event log, every hand, envelope and reconstructed beliefs. Slider/arrow keys select frames; Play/speed animate them, and manual stepping pauses playback. It is an analysis view, not evidence of the live method-memory state. It cannot advance or alter the finished game.

## Looks

Case-file light (default), Gaslight dark and Developer are account choices. Old keys are read through `styles.RENAMED`; accounts without an explicit choice get the current default. Developer uses frozen `legacy.css`; the other looks use `engraved.css`, self-hosted fonts and motion/color tokens. `chrome.css` supplies shared header/footer. Costs are gated by `Style.costs`. Keep the legacy stylesheet unchanged.

## Wikiclude

The encyclopaedia of clude (D20; `docs/wikiclude-plan.md` has the plan
and what was built): Wikipedia-style articles on the characters, their
methods, the game and what the measurements found, each written for
every reader at once. It is under `/wiki`, **public** like the privacy
page (David, 2026-10-01), and reached from the header bar's wooden
question mark and the footer. The same wooden question mark is every
wiki page's logo (David, 2026-10-02): the side panel's home link, beside
the wordmark, and the Main Page's welcome.

W1–W5 now supply 52 full articles and one remaining project stub
(*clude*), with no wanted pages. The game guide covers a complete turn
and the local house rules; the later articles cover personality, the
model wrapper, memory, mathematics and measurement. The inventory and
local verification are recorded in the plan's section 12. W6 covers
the app and project, and W7 remains the final editorial pass.

**An article is a Markdown file** in `clude_web/wiki/articles/`, named
for its title (`Professor_Plum.md`), with a front-matter block (title,
a short description, categories, redirects, "Did you know" hooks,
`kind: stub` for a place-holder) and a body. Edit it in VS Code like
any file. On top of Markdown's own footnotes and tables, the markup
(`clude_web/wiki/render.py`, whose docstring lists it all) has:

| Written | Is |
|---|---|
| `[[Professor Plum]]`, `[[Professor Plum\|Plum]]`, `[[Suggestion#The answer\|disprove]]` | a link to another article, in the red thread |
| `[[w:Bayes' theorem\|Bayes' theorem]]` | a link out to Wikipedia: its own blue, a small W, a new tab |
| `[[Category:Methods\|methods]]` | a link to a category |
| `{{fact:bench.grid.Plum.50}}` | a measured number, from `facts.py`, checked against the doc it came from |
| `{{code:preset.Plum.accuse_threshold}}` | a constant or a computed example, read from the live modules |
| `{{table:budget.grid\|Caption}}` | a whole measured table |
| `{{figure:rope-deals\|Caption}}`, `{{figure:key\|wide\|Caption}}` | a figure in a thumb frame; indented inside a worked example it stays inside it |
| `$x^2$`, `$$ ... $$` | mathematics, LaTeX rendered to MathML on the server; a literal dollar is `\$` |
| `[^note]` and `[^note]: {{cite:docs/board.md\|Movement rules}}` | a reference; References is numbered in the order the text cites |
| `{{infobox` ... `}}`, `{{main:Title}}`, `{{hatnote:...}}`, `{{navbox:clude}}`, `{{references}}` | the furniture |
| `!!! example "Title"` and an indented block | a worked example |

**Everything is rendered once, when the app starts** (`wiki.load()`, in
`create_app`), so a page view is a dictionary lookup and a mistake in
an article (an unknown fact, a figure that does not exist, a note cited
and never defined) stops the app starting and fails the tests, where it
is seen, and never reaches a reader. A link to an article nobody has
written yet is not an error: it renders dotted and is listed at
`/wiki/Special:WantedPages`, and `tests/test_wiki.py` holds the count
to `WANTED_BUDGET`, which is 0 at a release.

**Numbers are never typed into an article.** A measured number is
`{{fact:...}}`, kept in `facts.py` with the doc and heading it came
from, and a test finds every one in that doc: re-measure something,
change the glossary, and the suite fails until `facts.py` follows.
(`docs/` is not in the image, which is why the values are copied and
not read.) A constant is `{{code:...}}`, read from the module when the
wiki is built, and the worked example the method articles share, the
Rope question, is run through every method's real agent
(`facts.rope_question`; `plum_search` traces PlumOG's search for its
figure, `chain_example` fits White's chain, `mustard_tree` reads the
trained tree). The questions Colonel Mustard's tree asks on it reach the
text as `{{code:example.mustard.step.N.threshold}}` and the like,
computed on demand, so prose narrating a path the regrown tree no
longer takes fails at load.

**The figures set no colour**, like the board and the logo: each shape
has a class and `static/styles/wiki.css` dresses it from the look's
tokens. The pawns, the worked examples and the charts are drawn by
`figures.py` when the wiki is built. The board figures reuse the real
`board_svg` map and carry plain and dressed variants selected by the
look, with larger room names and an enlarged doorway detail. Leash
scores come from the menu rule, and arena bars from the recorded fact
table. The method diagrams are the
`DIAGRAMS` registry of `docs/ux/diagrams/build_diagrams.py`, drawn by
the vendored Mermaid under Playwright and stripped of its colours by

```powershell
& .venv\Scripts\python.exe scripts\build_wiki_figures.py
```

which writes `clude_web/wiki/figures/*.svg`, committed. Run it after a
diagram or the code behind one changes, then look at the page.

**The pages**: `/wiki` (the Main Page: the featured article, "Did you
know" with eight hooks drawn at random from every article's on each
visit, the categories), `/wiki/<Title>`, `/wiki/Category:<Name>`,
`/wiki/Figure:<key>`, and `/wiki/Special:` `AllPages`, `Random`,
`WantedPages`, `WhatLinksHere/<Title>` and `Search?q=`. Titles ignore
case and treat an underscore as a space; a redirect shows its target
with a "Redirected from" line. From 900 px the contents sit in a rail
on the left and the infobox floats right; on a phone the infobox comes
after the first paragraph and the contents fold away.

**Checking the Wikipedia links** needs the network, so it is skipped
unless asked for:

```powershell
$env:CLUDE_WIKI_LIVE = "1"; & .venv\Scripts\python.exe -m pytest tests\test_wiki.py -k wikipedia
```


## Sound

Six short synthesized cues: tick, turn, refute, accent, door and passage. No music. Sound starts off; the header toggle and volume persist per device. Cues fire once for new visible events/decisions, never polling, reload, talk or manual replay scrubbing. `scripts/make_sounds.py` regenerates the deterministic WAV assets.

## Looking at it

Install Chromium for Playwright, then run screenshot tooling against a throwaway store:

```powershell
& .venv\Scripts\python.exe -m playwright install chromium
& .venv\Scripts\python.exe scripts\clude_shots.py --dark --phone
```

`--look KEY` narrows looks; `--out DIR`, `--store`, `--run` and `--game` select output/input. Inspect the PNGs: only a browser applies the board's CSS and scripts. Default screenshots include wiki pages; `--wiki` shoots those alone. Screenshot backends are fake and spend nothing.

## Deploying

The repository config targets service `clude`, project `clude-game`, region `us-central1`, URL <https://clude-648214345192.us-central1.run.app>. This pass did not audit live configuration or deploy. `scripts/deploy.bat` is the canonical command; do not copy old revisions/timings as current acceptance.

### What is out there

| Configured piece | Purpose |
|---|---|
| `clude-run@clude-game.iam.gserviceaccount.com` | Runtime identity; bucket Object Admin and Secret Accessor on the three required secrets |
| `gs://clude-game-data/llm` | Runtime records, accounts, tables, memory and spend |
| `clude-flask-secret` -> `FLASK_SECRET_KEY` | Session signing |
| `clude-anthropic-key` -> `ANTHROPIC_API_KEY` | Optional real LLM seats |
| `clude-mcp-secret` -> `CLUDE_MCP_SECRET` | Optional MCP transport path |
| Dockerfile / `requirements-web.txt` | Python 3.14 image, NumPy inference, no PyTorch training |

The command sets HTTPS, store, $2/table, $10/UTC day and public URL; maps the three secrets at `latest`; runs one gunicorn worker with Uvicorn on the combined ASGI factory, 300 s timeout, 1 CPU/1 GiB, concurrency 8, min instances 0/max 1. Changing workers/instances requires concurrency design work, because registries, locks and login limits are process-local.

### Deploying a new version

After separately authorizing deployment:

```powershell
scripts\deploy.bat
```

The script pins account `clude-sa@clude-game.iam.gserviceaccount.com` and project `clude-game`. Use those explicit flags on other cloud commands too. Source upload/build uses `.gcloudignore`/`.dockerignore`; secrets and data must remain excluded. `gcloud meta list-files-for-upload` can inspect the upload. Runtime uses its identity, not a key file in the image.

For initial provisioning, create the named Secret Manager secrets from files containing only their values, grant the runtime identity access to each, and grant bucket Object Admin. Never paste secrets into commands/chat or commit them. Configuration describes required grants, not a current IAM audit. Rotate with new secret versions and a deliberate redeploy.

### Checking a deploy with a game

```powershell
scripts\live_check.bat play
scripts\live_check.bat start
scripts\deploy.bat
scripts\live_check.bat resume TABLE_ID
scripts\live_check.bat cleanup
```

These are **live mutations**: temporary accounts, games and a redeploy. `start` leaves a pending table; `resume` verifies cold rebuild after the deploy; cleanup removes accounts, not records. `scripts/clude_live_check.py` is the direct JSON-route client and prints request timings. LLM validation/spend is a separate step.

### Accounts and records in the cloud

Use `users add NAME --uri gs://clude-game-data/llm`. `store copy --uri data/llm --to gs://clude-game-data/llm --dry-run` previews a copy; remove `--dry-run` to write. It overwrites matching record/logbook keys, not accounts or live tables. [CLI](cli.md#store-copy) documents filtering.

### Taking it down

`gcloud run services delete clude --region us-central1 --account=clude-sa@clude-game.iam.gserviceaccount.com --project=clude-game` removes the service, not bucket data, IAM identities or secrets. Treat teardown as a separate deliberate action.

### Historical deployment observations

On 2026-09-18, cold startup was 8-10 s, warm lobby 0.6 s and cached replay 0.4 s. The 2026-09-19 live check measured median poll/answer/work at 93/850/820 ms. The first combined-app deployment on 2026-09-21 measured 112/1,113/1,074 ms on one resumed game. These predate the new Plum; they are bounded historical observations, not current performance promises.

## A seat over MCP (Phase 9)

`combined_app()` mounts Flask at `/` and Streamable HTTP MCP at `/mcp/<secret>`, sharing **one registry**. Separate processes would race cached table state. Locally:

```powershell
$env:CLUDE_MCP_SECRET = 'a-local-secret-0123456789'
& .venv\Scripts\python.exe -m uvicorn 'clude_web.mcp:combined_app' --factory --port 5000
```

The endpoint is `http://127.0.0.1:5000/mcp/a-local-secret-0123456789`. Hosted clients need the deployed URL/secret, configured with no transport OAuth; game account login follows through the tools. Protect the URL as a credential. Wrong/invalid paths are refused; with MCP enabled, unsupported OAuth/OpenID discovery gets JSON 404 rather than Flask's login redirect. With no secret there is no mount and Flask routing remains unchanged.

Twelve tools are registered:

| Tools | Purpose |
|---|---|
| `clude_login`, `clude_logout` | Issue login token / invalidate account's issued logins |
| `clude_tables`, `clude_sit` | Find a table and take an open seat |
| `clude_turn`, `clude_answer` | Wait for a decision and submit it using its sequence |
| `clude_say`, `clude_note`, `clude_autopilot` | Talk, persist private notes, hand over/reclaim the seat |
| `clude_watch`, `clude_games`, `clude_replay` | Spectate or inspect finished games |

Every operation after login takes its token. Browser users deal after open seats fill; a chatbot cannot create/deal a table. MCP occupies an ordinary human seat, reasoning without any character persona/agent. `notepad` is `full`, `shown` or `none`, adjustable only before the deal; reduced modes omit the seat's own certainty as well.

Compact views use `since` as an event cursor; `since=0` reconstitutes a fresh conversation. Older events become a digest. Room-name movement options include legal targets/distances. `seq` protects answers from retries. Turn/answer waits share a deadline of at most 60 s while driving the same work as the browser. An advance pass is held back after an undisproved suggestion or proven solution. Notes persist on the table, not in the replay entry log.

MCP tool docstrings are model-facing instructions. Keep required arguments, waiting/cursor rules, legal choices, private information and recovery behavior explicit when editing them. Login tokens carry an account epoch; logout invalidates them without affecting browser sessions.

## Tests

```powershell
& .venv\Scripts\python.exe -m pytest -q -n auto
$env:CLUDE_WEB_BROWSER = '1'
& .venv\Scripts\python.exe -m pytest tests\test_browser.py -q
```

The default suite uses temporary stores, fake model backends and the MCP SDK's in-memory client. Web checks cover privacy, invalid/stale answers, rebuilds, memory, timeout/autopilot, chat/cost and account routing. Wiki tests also validate doc headings and measured facts, so documentation edits must preserve their evidence.

Opt-in environment flags: `CLUDE_WEB_BROWSER` (Chromium), `CLUDE_GCS_LIVE` (bucket round trip), `CLUDE_LLM_LIVE` (paid API smoke), `CLUDE_WIKI_LIVE` (Wikipedia links). Run only the selected flag/test in the same shell call. Live/API checks require explicit authorization. The two historical LLM replay fixtures are stale after Phase 11 prompt edits and explicitly skip pending a paid refresh; fake-backend tests remain active.
