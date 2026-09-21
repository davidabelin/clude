# clude

A web app for playing Clue with a mix of human and LLM players. The name
is a nod to Claude. Owner: David (David Abelin, github.com/davidabelin).
Solo project. Call him David, never Dave.

## Read this first

This file is in the system prompt of every session; nothing under
`docs/` is until you open it. Start a session with `git log --oneline
-5` and `git status`, then the plan doc for the phase in play. Each
phase's plan doc ends with an "as implemented" section that records what
was actually built and where it departed from the plan: trust that over
the plan sections above it, and over this file if they disagree.

## Status (2026-09-19)

Phases 1-8 are done and committed. Each phase's record is the "as
implemented" section of its plan doc (`docs/phase5-plan.md` to
`docs/phase8-plan.md`; Phases 1-4 in `docs/phase-plan.md`), and every
measurement is in `docs/strategy-glossary.md`. The game runs headless
through `scripts/clude_cli.py`, and since 8.1a also in a local Flask app
(`docs/web.md`): a login, a lobby, a replay scrubber for any stored game,
and a Watch screen that plays a headless game a turn at a time. Since
8.1b the same app runs on Cloud Run at
<https://clude-648214345192.us-central1.run.app>, reading a mirror of
`data/llm` in the bucket (`docs/web.md`, "Deploying"). Phase 8 was
planned to completion on 2026-09-18 (`docs/phase8-plan.md`); that day
8.0.4 (the landing rule) and 8.2a-c (human players) were built, and on
2026-09-19 8.2d was deployed and live-checked, 8.3a-c built on fake
backends, the key deployed and 8.3 live-checked on the URL: a character
can play as an LLM character at a web table under a per-table budget and a
daily cap, people type at the table and the model seats answer off-turn
with pacing, and a remembering table wraps up with each model seat's
logbook entry. **Phase 8 closed 2026-09-19** (`docs/phase8-plan.md` 12,
"8.3d"): the live table cost $0.34 with no fallbacks, and the cold
rebuild came back in 0.1 s for a short table. One loose end: the
table's two debriefs drain on the next deploy (a `table.js` fix, below).
**Renumbered 2026-09-20:** Phase 9 is now the seat over MCP (planned
in `docs/phase9-plan.md`, 9a done; **9b built 2026-09-21** on fake
backends together with the serving code: `clude_web/mcp.py`, the
head, the note, the combined ASGI app and the Dockerfile command;
**9c deployed the same day**: the secret, the `claude` account,
revision 6 probed and live-checked, `docs/phase9-plan.md` 8; **the
first live game from the chat the same evening**: an Opus at claude.ai
played Plum at table `8de30daff8` for 30 turns and stopped with its
chat nearly full, every view about 9,000 tokens and a turn two to four
calls, so the view was made compact and cut at a `since` cursor,
`clude_answer` gained `accuse` and `wait`, and `clude_autopilot` is
the seventh tool -- built on fake backends, 21 MCP tests, **to
deploy**, after which that game resumes in a new chat); in-depth UX is
Phase 10 and clean-up and release Phase 11. Suite: 464 passed, 17 skipped (the
live-credential and browser tests), about three minutes with
`-n auto`; the browser tests run under `CLUDE_WEB_BROWSER=1`.

**The road from here** (David renumbered it on 2026-09-16;
`docs/phase-plan.md` has the table):

| Phase | What | State |
|---|---|---|
| 8.0 | Re-measure the glossary on the Classic board (was the "re-measurement plan"; stages 8.0.0-8.0.4) | done: 8.0.0-8.0.3, and 8.0.4 the landing rule for the passage loop (2026-09-18) -- `docs/phase8.0-plan.md`, `docs/phase8-plan.md` |
| 8.1 | 8.1a a basic UX scaffold as a local Flask app; 8.1b the same app on Cloud Run behind an app login | done: 8.1a built 2026-09-17 (steps 1-5: the engine seam, the login and accounts, the board and replay data, the replay scrubber, the lobby and Watch); 8.1b deployed 2026-09-18 (steps 6-9: the container, `store copy`, the service running as `clude-run`) -- `docs/phase8.1-plan.md`, `docs/web.md` |
| 8.2 | Human players | done: 8.2a-c built 2026-09-18 (the table driver and `play --human`; the table on the web with open seats, autopilot, cold rebuild and "characters remember"); 8.2d deployed and live-checked 2026-09-19, the cold rebuild 0.1 s on a 3-turn table (`docs/phase8-plan.md` 12, `docs/web.md`) |
| 8.3 | The rest of chat: the model on the web under a spend cap, human chat, off-turn talk with pacing, debriefs after web games | done: 8.3a-c built 2026-09-19 on fake backends, the key deployed and one live table played the same day (two model seats, chat, "remember"; $0.34, no fallbacks); 8.3d closed Phase 8 (`docs/phase8-plan.md` 12) |
| 9 | A seat over MCP: a Claude in a chat window (claude.ai) plays one seat of a live table through an MCP server mounted beside the Flask app, on the same `TableRegistry`; optionally with its character's own numbers as a "head" | 9a (the plan and this renumbering) done 2026-09-20; 9b built 2026-09-21 (`clude_web/mcp.py`: `build_server` over any registry and `combined_app`, the one ASGI app the container now serves; `SeatSpec.head`, `answer(by="mcp")`, `WebGame.head_reading`, the seat's note); 9c deployed 2026-09-21 (`clude-mcp-secret`, the `claude` account on the bucket, revision 6; the endpoint probed and a resumed live-check game played to the end), the connector added and the first live game played from the chat that evening (Plum, 30 turns, stopped with the chat full), which led to the compact `since` view, `accuse` and `wait` on `clude_answer` and the seventh tool `clude_autopilot` (21 tests, to deploy); then 9d -- `docs/phase9-plan.md` 8 |
| 10 | In-depth UX | not started (was Phase 9 until 2026-09-20) |
| 11 | Tweak, polish, release: clean-up and close, then version 1.0.0, released to family and friends, and planning in versions, not phases | not started (was Phase 10) |

Where things stand:

- **Seats and remembering (2026-09-21).** New Play and Watch tables
  remember by default, with an opt-out. The lobby options, in order, are
  `empty`, `open`, `floorbot`, `me (signed-in name)`, `X (LLM)`, and
  `X (headless)`. An LLM character uses its numerical method plus Claude's
  persona, leashed choices, chat and narrative logbook; a headless
  character never chats. Mustard, White and Green have method memory in
  either mode. Each LLM seat's memory-depth dial is saved as
  `SeatSpec.memory` (0 = condensed head, not off). Without a service key
  the LLM option is visible but disabled. Saved tables keep their memory
  choice; legacy setups missing the flag restore False. CLI logbooks
  remain explicit with `--logbook`. Working guide: `docs/web.md`.
  Validation: 472 passed, 2 live-credential tests skipped with browser
  tests enabled; the lobby also passes a 390 px overflow check.

- **The board (2026-09-15).** The engine plays the Classic 24 x 25 grid
  under the Classic movement rules, measured from
  `docs/ux/sample_board_A.png` into `docs/ux/board_map.txt` and
  `clude_core/board.py` (`docs/board-plan.md`, `docs/board.md`). Every
  golden was re-captured and both LLM fixtures re-recorded on purpose.
- **8.0 so far.** Every headless glossary number has a grid-era twin
  under "Re-measurement on the Classic board", every dial keeps the
  direction the ring found, and the presets were retuned (Settled
  decisions). On 2026-09-16 the two paid runs started: 8.0.2a
  (`grid-twin-llm-24`, all six with Claude, 4 seats) and 8.0.2b
  (`grid-plum-llm-24`, Plum alone with Claude at `Plum,Mustard,Green`),
  quoted $21-35 together and paired with the headless
  `grid-twin-base-24` and `grid-plum-base-24`; both finished ($14.24,
  no fallbacks). 2a reproduces the ring twin's findings in direction: an
  LLM table beats Plum (37.5% to 6.2%) and Mustard's wrong accusations
  fall (31.2% to 6.2%). 2b found the parking alive as a passage loop the
  leash hides from the model, which the trigger written beforehand
  could not see, so that trigger is withdrawn (below). 8.0.3 is done:
  all four logbooks reset (the ring-era copy is `data/llm/logbooks-ring`)
  and Mustard's and White's memory rebuilt from grid records only
  (`logbook rebuild --min-version`, default 3). Mustard's is now 116k
  rows, and loading it takes a 3-seat game from 1 s to 30 s. **8.0.4
  (2026-09-18)** closed the parking question: a placed room is a
  destination only when nobody else can refute with it (the agent's
  own, or the envelope's), a room in another seat's hand a place on the
  way (`features._landing_proximity`). Three paired arenas: games
  shorter on every table, exact repeats down two thirds or more for
  every character, win rates within noise (glossary, "The landing
  rule"). Goldens re-captured, fixtures re-recorded.
- **8.2 (2026-09-18).** `clude_training.table` is the driver: seats
  as `SeatSpec`s, a table as a `TableSetup`, human seats external to
  the engine, answers as data checked before they are sent in, an
  entry log that rebuilds a paused game exactly. `clude_web.tables`
  puts it on the web: a table document per game, polling and one unit
  of bot work per request (no threads, no websockets), open seats,
  autopilot, the reveal rule per viewer, the floor's notepad and
  Watch's bars for the person, "characters remember" with a memory
  snapshot. Watch is now a table with nobody human at it. A human's
  label is the account key; the suspect names, `floor`, `random`,
  `web` and `envelope` are refused as account names.
- **8.3 (2026-09-19).** An `llm` seat is the character with Claude,
  external to the engine like a person: `TableGame.llm_answer` makes
  one wrapper call per `work` request, every answer is stored with its
  audit and the lines it said (`Speaker`, the engine's `speakers` hook)
  so a rebuild never calls the model, and `MeteredBackend` over a daily
  `Ledger` (`spend/<date>.json`) refuses past the table's budget or the
  day's cap, the character playing on. `/say` is a person's line (240
  characters, never read by the engine); `clude_web.chat.Reactions`
  opens the floor on a line, a suggestion or an accusation, each model
  seat joining with probability `chattiness` (squared for a reply to a
  reply), two queued at most, served one per `work` a few seconds
  apart, bot turns held meanwhile. A remembering table attaches each
  model seat's logbook (read-back) and wraps up with one debrief per
  `work` after the end. The key reaches the service as
  `ANTHROPIC_API_KEY` from Secret Manager (`docs/web.md`, "Deploying");
  without it the LLM option is visible but disabled. Live-checked the
  same day on one table (David as Scarlett, White and Peacock with Claude,
  "remember" on): 58 turns, 55 model decisions of which 19 called the
  model, 0 fallbacks, 28 off-turn lines, $0.34. A served reaction and
  its audit are given back to the seat's wrapper on a rebuild (8.3d);
  before that fix a rebuilt model seat forgot its own off-turn lines.
  The same pass found `table.js` never posting `/work` for a finished
  table, so no web debrief had ever run; fixed, and the first live
  debriefs (the two pending on table `1b31ccffd9`) drain once the
  fix is deployed and the table reopened.
- **Worth knowing from the earlier phases** (the detail is in the docs
  named):
  - An LLM seat chooses only within the leash of its character's own
    scores and falls back to the character on anything illegal,
    malformed or failed; `NullBackend` reproduces the headless game
    byte for byte (`docs/llm-wrapper.md`, `docs/phase6-plan.md` 8).
  - **Plum's parking, resolved 2026-09-18** (glossary, "The landing
    rule"): on the ring it was a free "stay" in a cleared room, on the
    grid a secret passage into one, both paid for by a landing scoring
    `proximity` 1.0 whatever the room; the leash hid the walk toward a
    live room, so the wrapper played the loop without asking the model
    and a logbook could not reach it. 8.0.4's landing rule removed the
    payment; the history is in the glossary's ring and grid sections.
  - **Retracted:** the twin arena's "the leash rescues Mustard". Alone
    with Claude his win rate does not move at any leash.
  - Logbooks: three tiers of memory per identity and a `memory` dial.
    New web tables remember by default; CLI runs opt in with `--logbook`.
    The debrief is $0.09 and 42 s per seat-game and needs
    its own 180 s timeout (`docs/logbooks.md`, `docs/phase7-plan.md` 8).
- **Live spend** was about $63 at list prices before 8.0 ($23 for the
  twin run and pooled sweep, $27 for the ladders, $12.60 for 7d), then
  $0.26 re-recording fixtures on 2026-09-15, and $14.24 for 8.0.2a
  and 8.0.2b on 2026-09-16 ($9.36 and $4.88, against a $21-35 quote):
  about $78 in all, with $0.22 more re-recording the fixtures for 8.0.4
  on 2026-09-18 and $0.34 for the 8.3 live table on 2026-09-19 (plus
  its two debriefs, about $0.20). An LLM seat-game
  costs $0.07-0.11 for most characters and about $0.25 for Plum. Estimates have come in
  under twice: quote a range, not a point, and get a yes before any
  live run.

`legacy/` holds code from an earlier chat: material to port from, never
a foundation and never imported. Read `legacy/README.md` before touching
it; `docs/phase-plan.md` has the disposition of every file.

## Settled decisions (David's)

- **Six LLM characters, one per suspect.** Each uses a genuinely
  distinct probability method: six real algorithms, not one engine with
  six parameter sets. Part of the point is revisiting old-school ML
  methods David studied but never got to play with enough.

  | Suspect | Method | Module | Intended flavor |
  |---|---|---|---|
  | Scarlett | Naive Bayes | `naive_bayes.py` | Overconfident, accuses early |
  | Plum | Exact posterior enumeration over consistent deals | `exact_enum.py` | Correct but slow |
  | Peacock | Dempster-Shafer belief/plausibility | `dempster_shafer.py` | Cautious, won't commit until plausibility collapses |
  | Mustard | Decision tree trained on game logs | `decision_tree.py` | Pattern-matches, confidently wrong on unusual deals |
  | Green | Bandit ensemble over the other five methods | `bandit.py` | Ports almost directly from rps `multi_armed_bandit.py` |
  | White | Markov model over opponents' suggestion sequences | `markov.py` | Reads people rather than cards |

- **Each character's turn** works in two steps: its own strategy model
  produces numbers, then those numbers combine with its personality
  dials to choose an action. Built as `clude_agents.Character` over the
  five Phase 5 dials plus Phase 6's `leash` and `chattiness`.
- **In-game chat.** Characters initiate and respond even off-turn, gated
  by numeric settings such as a chattiness dial. (Table talk exists
  headless as `RemarkEvent`s; off-turn chat is Phase 8.3.)
- **Persistent logbooks.** Each character writes to its logbook after
  every game. (Phase 7.)
- **Sequencing.** First the models work and players receive numbers
  from them. Personalities and memories come after that.
- **Documentation.** Each player's model and strategy gets documented in
  detail (`docs/strategy-glossary.md`).
- **Parallel design track.** Aesthetics, gameplay design, and UX are
  developed alongside the model work.
- **IP.** clude stays a private project shared with a few family and
  friends, so it copies the Classic board game as closely as possible:
  the real rules, suspects, weapons, and rooms under their real names,
  card lists as in `clude_core/domain.py`. If it is ever published (e.g.
  to an app store), scrub it for infringement first. Visual assets are
  drawn fresh rather than copied from the board or card art.
- **Structure mirrors David's `rps` repo** (and `c4`, which already
  copies it): a shared `AgentProtocol` with `reset` / `select_action` /
  `observe`, an `AgentSpec` name-keyed registry, one module per method,
  sibling packages by concern plus `scripts/`, `tests/`, `docs/`.
- **Talk and bluffing about own cards: allowed.** Characters may hint,
  bluff and side-bet about their own hand and are meant to learn the
  cost of over-sharing rather than have it designed away. House rule:
  refusing a reveal the rules require (the formal refutation) is
  system-enforced expulsion, and the engine already makes it impossible
  to do by accident (`docs/architecture.md`, "Reveal integrity").
- **Human tells persist across games**, independent of which suspect the
  human plays next (see Seats, below).
- **Python 3.14 in a plain venv, no conda. Deployment target Cloud Run**,
  budget permitting (`docs/architecture.md` has the cost caveat).
- **Leash presets stand** at `leash` 0.25 and `chattiness` 0.5
  (2026-09-13, after the per-character ladders). The parking fix in
  `movement_scores` waits: David wants the logbook system working
  first, expects Plum's own post-game notes may teach him out of the
  parking before a scoring change is tried, and wants no more paid runs
  at ladder scale (~$10-20 each) until then.
- **Logbook entries are modelled on `docs/zenbot_memories.json`**, the
  self-written per-session memory format from David's zenbot project,
  which works well there. Same shape for Clue -- date and serial, title,
  what happened, evaluations, key insights, lessons learned, outcome,
  standing instructions -- minus the koans, and written by the
  character's own model after each game. Built in Phase 7 with two
  additions David asked for: a `summary` and `flags` per entry, so
  entries connect.
- **Phase 7 decisions (2026-09-14).** The debrief sees the whole deal
  face up (a post-mortem with cards on the table; it cannot leak into
  the next deal and lets a dossier verify a tell). All three numeric
  memories are in (Mustard, White, Green). Read-back is the `memory`
  dial: 1 the entire logbook, 0.75 the most recent full entries, 0.5
  every entry's summary and flags, 0 the head only (default); the
  interpolation between those anchors is mine and can be adjusted.
- **Seat-locked characters (2026-09-14).** A character always plays
  its own suspect's token and never another's (David: "No more
  characters moving their seats"; "Plum must never play Scarlett's
  seat"). A fill bot, later a human, takes the lowest free token;
  seats run in the board's order, so the roster `Plum,Mustard,Green`
  seats Mustard, Green, Plum and Mustard moves first.
  `clude_training.arena.seat_lineup` seats every table (`arena` and
  `play`); `engine.run_game(..., suspects=...)` takes the tokens in
  play and `ClueObservation.suspects` carries them to every player
  and prompt; a roster larger than the table rotates only who sits
  out. Every character golden was re-captured and both LLM fixtures
  re-recorded that day. Every measurement before it (Phase 5 sweeps,
  the Phase 6 twin arena and ladders) rotated characters through
  seats.
- **The Classic board and rules (2026-09-15).** The engine and the
  players play Board A (`docs/ux/sample_board_A.png`): the 24 x 25
  grid, 17 doors, two passages, six start squares, the cellar
  impassable. One die; the whole roll unless a room is entered; no
  re-entering the room just left; "stay" only when a suggestion moved
  the token in since its last turn; the image stands for the unplayable
  edge cells; ring-era records stay readable. The game will display
  that board with its grid, decorated more ornately than the graph
  diagram in `sample_board_B.png`, with a logo, not the big "?", in the
  middle. Then everything in the glossary is re-measured
  (Phase 8.0, `docs/phase8.0-plan.md`).
- **Presets retuned on the grid (2026-09-15).** Scarlett's
  `accuse_threshold` 0.15 to 0.3 (she wins three times as often at a
  lower wrong rate on the longer grid games, and still accuses early
  and wrongly often enough for the flavour); Plum's `curiosity` 0.8 to
  0.5 (the grid rewards entering any room over walking to the best
  one); Plum's sample budget 2,000 to 10,000 with the node budget
  unchanged (the fallback's noise, not the search, is what his mid-game
  numbers are made of -- it takes his 50%-checkpoint log-loss from 1.75
  to 1.44, still short of uniform's 1.35, and doubles the suite's
  runtime). Green's threshold stands at 0.75: his pace limits him, not
  his dial. Scarlett's and Peacock's curiosity stand. Everything else
  in the ring-era tuned table is unchanged.
- **The road to 1.0.0 (2026-09-16).** The re-measurement is Phase 8.0
  (its stages 8.0.0-8.0.3); 8.1a is a basic UX scaffold as a local
  Flask app and 8.1b the same app on Cloud Run; 8.2 human players; 8.3
  the rest of chat; then (as renumbered below) Phase 9 the seat over
  MCP, Phase 10 in-depth UX, Phase 11 clean-up and close.
  Then clude is released as version 1.0.0 -- to family and friends,
  which is not the public release the IP decision above guards -- and
  planned in versions, not phases.
- **A Claude at the table over MCP; renumbered (2026-09-20).** After a
  conversation about the project with a chatbot at claude.ai, David
  decided to let it play a seat itself during a chat there. API
  endpoints were considered first; an MCP server was judged the better
  fit. That work is Phase 9; the old Phase 9 (in-depth UX) is Phase 10
  and the old Phase 10 (tweak, polish, release) is Phase 11. It is to
  be built with minimal disruption to the existing code: the chat seat
  is an ordinary account in an ordinary human seat, answering through
  the same `TableRegistry` the browser uses. David's draft (a
  `clude_mcp.py` and a `webgame_reading.py`, untracked at the repo
  root) is the starting point; the plan is `docs/phase9-plan.md`.
- **8.0 and 8.1 decisions (2026-09-16).** 8.0.2a and 8.0.2b approved at
  $21-35. 8.0.3: reset all four logbooks (Plum's entries and Green's
  posteriors too), keeping a copy of the ring-era ones. 8.1: an app
  login rather than a Google-account allowlist, using the credentials
  in `clude-game-sa.json` (how, as I read it, is `docs/phase8.1-plan.md`
  3.4, awaiting confirmation); the replay direction was left to me:
  Direction A ("Scrubber") for replay, Direction D's order for watching
  a game.
- **Convenience beats security here (2026-09-17).** clude is a game for
  family and friends, and David judged that friction will cost more than
  secrecy buys. So: a new account's password is `password`, set without
  a prompt; any non-empty password is accepted, one character included;
  passwords are printed by the CLI and shown as they are typed in the
  app; and a player is offered a change exactly once, after their first
  login, after which only `clude_cli.py users passwd` changes it.
  Usernames are case-insensitive for the same reason. What is *not*
  traded away: passwords are still only stored as Werkzeug hashes, the
  login still gates every route, CSRF and the per-name rate limit stand,
  and 8.1b still runs the service as a narrow `clude-run` identity
  rather than the owner `clude-sa` -- so the damage ceiling stays the
  game store. I raised that the service is internet-reachable and
  `password` is guessable; David's call, made knowingly
  (`docs/web.md`).
- **Phase 8 to completion (2026-09-18).** The plan is
  `docs/phase8-plan.md`; David's four decisions: 8.0.4 first, the
  scoring change measured headless (not the paid ladders, not Phase
  10); the model comes onto the web in 8.3a, after human seats; a
  seated human sees the floor's notepad *and* Watch's compact bars for
  the bot seats; "characters remember" shipped in 8.2 initially off; David changed
  the default to on for new web tables on 2026-09-21, with an opt-out.
  The cost is stated on the form. Assumed unless he says otherwise: the floor
  bot as the autopilot stand-in, $2 per table and $10 a day as 8.3's
  budgets, no `--min-instances 1`.
- **Commit messages are printed in the reply, never written into
  `commit_msg.md`** by me (David declined that, 2026-09-13).

## Architecture in brief

Built; the detail is in `docs/architecture.md`.

- `clude_core` -- domain, board, event log, `GameState`/`ClueObservation`,
  the rules engine, `RandomBot`.
- `clude_constraints` -- the shared deduction floor (`propagator.py`) and
  `FloorBot`, the standard self-play opponent.
- `clude_agents` -- `AgentProtocol`, the `AgentSpec` registry, one module
  per method, `personality.py` (Profile, dials, presets), `character.py`
  (belief -> action), `explain.py` (text formatters).
- `clude_training` -- self-play snapshots, the belief benchmark, `trace`
  (per-seat belief replay), `replay` (a stored record back into a
  `GameState` or any seat's view), `memory` (Tier 1 method memory, and
  the snapshot a web table stores), the arena and dial sweeps, `table`
  (seats, the answer codec and `TableGame`, the driver for seats
  answered from outside the engine; `arena.headless_table` builds
  through it).
- `clude_storage` -- `GameRecord`/`SeatRecord`, `LocalStore`, `GcsStore`
  (with generic document methods), `logbooks` (`LogbookEntry`,
  `LogbookHead`, `Logbook`, the memory-depth renderer), `mirror` (one
  store into another; `store copy`).
- `clude_llm` -- menus, schemas (three, `LOGBOOK_SCHEMA` the third),
  prompts, personas (`personas/*.md` and `rules.md`), backends
  (`NullBackend`, `ScriptedBackend`, `RecordingBackend`/`ReplayBackend`,
  `AnthropicBackend`), `LLMCharacter` (with `attach_logbook`,
  `read_back`, `debrief`, and `react` for off-turn talk), `logbook` (the
  debrief prompt), `metered` (`MeteredBackend` and the daily `Ledger`,
  the web's spend caps).
- `clude_web` -- the Flask app: `create_app`, `config` (secret, store,
  cookie policy), `auth` (the login gate, CSRF, rate limit), `users`
  (accounts as store documents), `board_svg` (the grid drawn from
  `clude_core.board`, colourless so the stylesheet decides), `replay_data`
  (event lines, board frames, the cached belief trace), `tables` (the
  registry that stores, drives and rebuilds every game, the seat form,
  the view of a game from one seat, the model seats and their metering),
  `chat` (off-turn talk: the reaction queue and its pacing), `watch`
  (Watch as a table with nobody human at it), `mcp` (Phase 9: the seven
  tools a Claude in a chat window plays a seat through, built by
  `build_server` over any registry, the compact `seat_view` it reads,
  and `combined_app`, Flask and the endpoint in one ASGI app under a
  secret path), `views`, templates,
  one stylesheet, `replay.js` and `table.js`.
  Imports every other package; nothing imports it (`docs/web.md`).
  `clude_training.arena.headless_table` is the table `play` seats, shared
  with Watch and pinned to the CLI by a test.
- `scripts/clude_cli.py` -- the maintainer CLI (`play --human` seats
  you from the terminal); `scripts/clude_shots.py` screenshots every
  screen; `scripts/clude_live_check.py` plays a table on the deployed
  service, wrapped by `scripts/live_check.bat`; `scripts/deploy.bat` is
  the deploy command; `tests/` -- pytest.
- `Dockerfile`, `requirements-web.txt`, `.gcloudignore`,
  `.dockerignore` -- the Cloud Run image; the ignore files keep the key
  file, `.env` and `data/` out (`tests/test_deploy.py`).

Invariants to keep:

- The floor masks every belief before it is used. Agents differ in how
  they reason under uncertainty, never in what is logically certain.
- One `ClueObservation` contract; the event log is rich enough to replay
  every character's belief after the fact (`trace`).
- Every game is deterministic per seed. `tests/test_character.py` holds
  golden fingerprints of seeded character games (re-captured on
  2026-09-14 for fixed seating and on 2026-09-15 for the Classic
  board); a scoring change that moves a game
  must update them on purpose, never by accident.
- The LLM wrapper chooses only within the leash of the character's own
  scores and falls back to the character on anything illegal, malformed
  or failed. `NullBackend` reproduces the headless game byte for byte;
  that twin is what every LLM measurement is paired against.
- New Play and Watch tables remember by default (2026-09-21); an
  unchecked checkbox opts out. Existing saved tables retain their choice.
  CLI memory still requires `--logbook` and changes nothing when off: Mustard's
  default tree is still the 25 FloorBot self-play games (seed 2026) and
  White's chain still starts from the Laplace prior. With `--logbook`
  they load their method memory from the store; determinism is then
  "per seed and logbook state". A fixture or golden must never depend
  on a logbook. The first 56 LLM games were run without `--store` and
  are lost; every live run since goes to `data/llm`, which now also
  holds Mustard's and White's rebuilt method memory under `logbooks/`.

## Proposed, not yet confirmed by David

Suggestions to raise, not decisions to implement.

- **Setting (shelved).** A ready-made reskin if clude is ever published:
  the stormbound ocean liner *SS Meridian*. Rooms: Wheelhouse, Wireless
  Room, Grand Saloon, Purser's Office, Boiler Room, Galley, Promenade,
  Stateroom, Cargo Hold. Cast: Ms. Vermilion (Scarlett), Cpt. Ochre
  (Mustard), Dr. Indigo (Plum), Mme. Verdigris (Peacock), Mr. Sable
  (Green), Sister Celadon (White). Weapons not chosen.
- **Visual direction.** Mid-century modernist structure; case-file
  styling reserved for the logbook and post-game replay. Signature
  element: a two-tone belief/plausibility bar per player, solid for
  logically forced, pale for still plausible. Each character's method
  shown under its name as a toggle.
- **Post-game replay** of all six belief traces as the payoff feature
  and debugging tool. (Headless `trace` exists; the first replay
  screen is Phase 8.1a.)
- **Chat pacing.** Stagger arrivals, cap concurrent speakers at two; the
  chattiness dial gates participation, not just verbosity.
- **Logbook reset** control, for fairness.
- **Human seats and player identity.** Each suspect is a Seat, occupied
  by a human or its seat-locked cludebot (the cludebot half is built,
  above). Human identity is a chosen display name independent of
  seat, written into `SeatRecord.label` so the logbook follows it.
  Rationale in `docs/architecture.md`, "Seats and player identity".

## Open questions (ask, don't assume)

Phase 9's, in `docs/phase9-plan.md` section 6, were built as
bracketed on 2026-09-21 and await David's word: the MCP endpoint
guarded by a secret path on the public URL, the chat seat's account
`claude`, the head a fresh reading as `readings` makes one, uvicorn as
gunicorn's worker over the combined app, and `head` off by default.
Three serving choices made from the code that day, to confirm too: the
MCP transport stateless with JSON responses, the SDK's localhost-only
Host check switched off (the secret is the guard), and asgiref's
Flask bridge run off its one-thread lane (`docs/phase9-plan.md` 8). Phase 8 left
none: its assumptions stood through
its close (`docs/phase8-plan.md` 9): the floor bot as the autopilot
stand-in, 8.3's budgets ($2 a table, $10 a day), and no
`--min-instances 1` (the cold rebuild is accepted and measured).

Resolved 2026-09-13: leash presets stand; the parking fix waits behind
logbooks; `docs/zenbot_memories.json` is the logbook model; no writing
into `commit_msg.md`. Resolved 2026-09-14: the three Phase 7 decisions
above; a UX pass between Phase 7 and Phase 8. Resolved 2026-09-16: the
renumbering to 1.0.0 and the 8.0/8.1 decisions above. Resolved
2026-09-17: all five points of `docs/phase8.1-plan.md` section 6 -- the
login as read, the engine seam built now rather than in 8.2, no LLM
seats on the web in 8.1, the Cloud Run changes with the service running
as a new narrow `clude-run` rather than the now-owner `clude-sa`, and
uploading the grid-era runs *and* the logbooks. Resolved 2026-09-18:
the one-time Google Cloud changes for 8.1b, made by David in the
Console; the parking question (8.0.4, the landing rule, kept); the four
Phase 8 decisions above.

## Working with David

- Confirm shared understanding of a plan before writing code. Each
  phase gets `docs/phaseN-plan.md`: context, what the code dictates,
  design, sub-phases, files, David's decisions, out of scope, and then
  an "as implemented" section written as the work lands.
- Break large efforts into ordered phases. Change working systems one
  incremental step at a time.
- Prefer simple, pragmatic, modular code with docstrings
  (`docs/docstring-guidelines.md`), error handling, and unit tests. Run
  the whole suite before calling anything done.
- Build headless/CLI first and stay general before investing in UI.
- Give honest, independent evaluation. Say so when something is a bad
  idea. When a number turns out wrong, say so and fix every place it
  went.
- Get something working first. Brief theory tangents are welcome after.
- **Commits.** David runs `git commit` himself, from the VS Code commit
  box. After any nontrivial change, print a paste-ready message
  unprompted, as raw Markdown: a title line, a short paragraph on why,
  then `-` bullets with a blank line between them and nested `-`
  sub-bullets for detail. Never hard-wrap: one bullet is one line,
  however long. The shape he corrected is in
  `docs/commit_msg_correction.md`. End with the Co-Authored-By line from
  the session's system reminder. `commit_msg.md` at the repo root is his
  gitignored paste target.
- **Live spend.** Estimate the cost, offer sizes, and get a yes before
  any run that calls the API. Always pass `--store data/llm` and
  `--json <scratchpad path>` so nothing is lost.
- **Fixtures.** `tests/fixtures/llm_seed*.json` are keyed on the exact
  system prompt. Any edit to a persona or `rules.md` invalidates them:
  re-record with the command in `tests/test_llm.py` and update
  `RECORDED_GAMES` from the transcript it prints.

## Environment and how to run

- Windows 11 laptop ("Orbit"): i7-11800H, 32 GB RAM, RTX 3080 Laptop
  GPU. Editor: VS Code. For CUDA to engage, Python may need adding to
  Windows' high-performance GPU app list.
- **Use the venv's interpreter explicitly.** The shell tools do not
  activate `.venv`; bare `python` is a global 3.13 with no pytest.
  PowerShell: `& .venv\Scripts\python.exe ...`; Bash:
  `.venv/Scripts/python.exe ...`. PowerShell calls share no state, so set
  environment variables in the same call as the command that needs them.
- Tests: `& .venv\Scripts\python.exe -m pytest -q -n auto` (pytest-xdist;
  about two minutes against ~220 s serial; drop `-n auto` to debug a
  single test). `CLUDE_LLM_LIVE=1`
  enables the live API smoke test (`-k live`), `CLUDE_GCS_LIVE=1` the
  bucket test, `CLUDE_WEB_BROWSER=1` the Playwright tests
  (`tests/test_browser.py`).
- **Seeing the web app.** `& .venv\Scripts\python.exe
  scripts\clude_shots.py --dark --phone` writes a PNG of every screen,
  in both themes and at both widths, from a throwaway store seeded with
  real records. Run it after any UI change and *look* at the result:
  three real bugs on the replay screen were invisible to the whole test
  suite and obvious in the first screenshot. Needs Playwright
  (`pip install playwright` then `python -m playwright install
  chromium`), which is optional. An SVG rasteriser is no substitute:
  `clude_web/board_svg.py` sets no colour, so only a browser renders
  the board at all (`docs/web.md`).
- CLI: `& .venv\Scripts\python.exe scripts\clude_cli.py <cmd> --help`,
  where `<cmd>` is `agents`, `play`, `prompt`, `trace`, `floor`,
  `benchmark`, `train-mustard`, `snapshots`, `arena`, `sweep`, `store`,
  `logbook` or `users`. Every command is deterministic per `--seed` (and,
  with `--logbook`, per logbook state). `docs/cli.md` explains each and how
  to read its output.
- Claude API: `ANTHROPIC_API_KEY` in the environment (or an `ant auth
  login` profile), resolved by the SDK; never in the repo. Without it
  every LLM seat falls back to its headless character. The key must be
  **workspace-scoped**: an org-level key 400s on every call asking for
  an `anthropic-workspace-id` header, which the backend does not send.
  The key lives in a gitignored `.env`, but nothing loads that file;
  export it first, in the same call:
  `$env:ANTHROPIC_API_KEY = (Get-Content .env | Where-Object { $_ -match '^ANTHROPIC_API_KEY=' }) -replace '^ANTHROPIC_API_KEY=', ''`.
  Default model `claude-opus-5` (`--llm-model` on the CLI,
  `CLUDE_LLM_MODEL` for the smoke test). Costs in `docs/llm-wrapper.md`.
- Google Cloud: project `clude-game`, bucket `gs://clude-game-data`
  (billing enabled 2026-09-12). The service-account key is
  `clude-game-sa.json` at the repo root: gitignored, never commit it,
  never print or copy its contents. `clude_storage` finds it by that
  path or via `CLUDE_GCS_CREDENTIALS`.
- **gcloud: name the project on every command.** Orbit keeps a gcloud
  configuration per project and the active one is often zenbot's, so
  pass `--account=clude-sa@clude-game.iam.gserviceaccount.com
  --project=clude-game` every time rather than trusting it. The web
  app is the Cloud Run service `clude` (us-central1), running as
  `clude-run`, which holds only Storage Object Admin on the bucket and
  Secret Accessor on `clude-flask-secret`; its store is
  `gs://clude-game-data/llm`, filled by `store copy`, and its accounts
  are made with `users add NAME --uri gs://clude-game-data/llm`.
  Deploying, and every number measured, is in `docs/web.md`
  ("Deploying"). Nothing new in the project without a yes.
- `data/` is gitignored. `data/llm` holds every stored live run (see
  Status); `store --uri data/llm` lists them.

## Docs map

- `README.md` -- public-facing overview, quick start, layout.
- `docs/architecture.md` -- package layout, the floor, `ClueObservation`,
  the engine seam, `AgentProtocol`, personality layer, LLM wrapper,
  storage, credentials, deployment cost, Seats proposal.
- `docs/phase-plan.md` -- the eight phases with status, legacy
  disposition, scope of each built phase.
- `docs/phase5-plan.md`, `docs/phase6-plan.md`, `docs/phase7-plan.md`
  -- plan, David's decisions, and "as implemented".
- `docs/phase9-plan.md` -- Phase 9, a seat over MCP: what the code
  dictates, the design, sub-phases 9a-9d, David's decisions, open
  questions.
- `docs/strategy-glossary.md` -- each method in plain language; the
  benchmark, dial sweeps, tuned presets, and the Phase 6 measurements.
- `docs/llm-wrapper.md` -- how a model pilots a character; credentials;
  measured costs.
- `docs/logbooks.md` -- playerbot memory: the three tiers, the `memory`
  dial, the debrief, the CLI, cost.
- `docs/web.md` -- the Flask app: running it locally, the session
  secret, accounts and the `users` CLI, the login gate, the lobby, Watch
  (and why it shows so little), the replay, screenshots, the layout,
  and deploying to Cloud Run.
- `docs/cli.md` -- every subcommand.
- `docs/board.md` -- the Classic board as measured, the doors, the
  rules, what the module exposes, and the ring it replaced.
- `docs/board-plan.md` -- the board rebuild: plan, David's decisions,
  and "as implemented". `docs/phase8.0-plan.md` -- Phase 8.0, the costed plan to
  re-run every glossary measurement on the grid, with the trigger for
  its conditional paid steps. `docs/phase8.1-plan.md` -- Phase 8.1, the
  web scaffold (8.1a) and Cloud Run (8.1b), both built.
- `docs/ux/` -- the UX pass: the two reference boards, `board_map.txt`
  (the source of truth for `clude_core/board.py`), and `replay/`, the
  four replay-screen direction sketches on the design canvas.
- `docs/docstring-guidelines.md` -- docstring conventions.
- `docs/pre_stage_5.md` -- the "Fab4" review that reworked Phase 5
  against the code as it was; historical.
- `docs/commit_msg_correction.md` -- the commit-message shape David
  wants, as a WRONG/RIGHT pair. Local only: it is gitignored, so it may
  be absent on a fresh clone; the rule itself is stated above.
- `docs/zenbot_memories.json` -- the per-session memory template from
  David's zenbot project; the model for Phase 7 logbook entries.
- `legacy/README.md` -- what the legacy code is and what is wrong with it.
