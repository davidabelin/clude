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

## Status (2026-09-15)

**2026-09-15: the board was rebuilt.** The engine now plays the
Classic 24 x 25 grid with the real doors, passages and start squares,
under the Classic movement rules (whole roll unless a room is entered,
no re-entry, "stay" only after a suggestion dragged you in), measured
from `docs/ux/sample_board_A.png` into `docs/ux/board_map.txt` and
`clude_core/board.py`. Plan and record: `docs/board-plan.md`; guide:
`docs/board.md`. Every golden was re-captured on purpose; the two LLM
fixtures still need a paid re-recording (about $0.35), until which the
two replay tests fail (256 passed, 2 skipped otherwise, ~95 s). Every
number in the glossary predates the grid; `docs/remeasure-plan.md`
schedules the re-run, headless first (free), then paid steps each
needing a yes. The UX pass (below) is where things stood before that.

Phases 1-6 of `docs/phase-plan.md` are done and committed. Phase 7
(logbooks) was planned, built (7a-7c, on fake backends) and
live-checked (7d) on 2026-09-14; its record is `docs/phase7-plan.md`
section 8 and the working guide `docs/logbooks.md`. 7d found the
debrief timing out at the wrapper's 30 s (fixed: its own 180 s), tuned
the debrief prompt on six real entries, added `--logbook-characters`,
and, on David's instruction mid-run, locked every character to its
own token ("Seat-locked characters" under Settled decisions). The
paired leash-0.5 measurement then ran (Plum on the model, his logbook
on against off, 24 games each, `seated-plum-leash-0.5` and
`seated-plum-leash-0.5-logbook` in `data/llm`; glossary, "Plum's
logbook at leash 0.5"): his own notes cut his stalls by more than
half over the run (37 to 3 in the last quarter on the same deals) at
the price of two early accusations, so wins are a wash. Phase 7 is
complete. Next David wants a UX design pass before Phase 8 (Flask/Cloud Run front end, then chat, then
human seats). There is no UI and no chat yet: everything runs headless
through `scripts/clude_cli.py`. The suite was then 247 tests passing and
2 skipped (the two live-credential tests), ~47 s.

Phase 7 in short (the plan doc has the detail):

- **Three tiers of memory per identity** (a `SeatRecord.label`), in the
  record store under `logbooks/<identity>/`: the record (Tier 0, with
  `clude_training.replay` rebuilding any seat's view from it); method
  memory (Tier 1, `method.json`, `clude_training.memory`): Mustard's
  tree trains on rows from every stored game, White's chain starts
  from a known opponent's transition frequencies, Green's posteriors
  persist; and narrative memory (Tier 2): a zenbot-shaped entry per
  game the character's own model writes at a debrief that sees the
  deal face up, plus a rolling head (tally, standing instructions, a
  dossier per opponent, a flag index).
- **The `memory` dial** (eighth on `Profile`, default 0) sets what an
  LLM seat reads back: the head at 0, entries' summaries and flags up
  to 0.5, whole entries above, everything at 1. The block is a second
  cached system block; an empty logbook sends none, so every fixture
  and golden held.
- **Off by default.** `--logbook [URI]` on `play`/`arena` turns memory
  on; `--logbook-readonly` and `sweep --logbook` read only; `logbook
  list|show|reset|rebuild` inspects and resets it; `play --store`
  persists single games. Mustard's and White's memory was rebuilt from
  the 193 stored ladder games in 3 s; retraining Mustard on it takes
  2 s.
- **A limit worth remembering:** the logbook steers the model only
  among options the leash allows. Plum's escape from a cleared room is
  on his menu only at leash >= 0.34, so at the preset his notes cannot
  unpark him. At leash 0.5 they can and do (above), but the same rope
  lets the notes' push for tempo turn into accusations below his
  threshold (P 0.50 and 0.80, both wrong). The debrief is $0.09 and
  42 s per seat-game; it needs its own timeout (180 s), since a
  move's 30 s kills it.

Phase 6, the LLM wrapper (`clude_llm`), closed on 2026-09-13. The record
is `docs/phase6-plan.md` section 8; the numbers are in
`docs/strategy-glossary.md` under "Phase 6". In short:

- The live smoke test passes on Opus 5. Personas were tuned from two
  real games: `rules.md` gained a no-repetition rule, and `Plum.md` a
  line that stops him reading decimals aloud.
- Twin arena (24 games, 4 seats, all six characters): an LLM-piloted
  table costs Plum 44 points of win rate (75% to 31%), not because the
  model overrides him but because the table ends games before his exact
  count converges. Mustard's wrong accusations fall from 37.5% to 6.2%.
  No fallbacks in 807 calls.
- The pooled leash sweep could not see individual characters (every
  seat was swept, so pooled win% is 33.3 by construction). Presets are
  unchanged: `leash` 0.25, `chattiness` 0.5.
- Per-character leash ladders (done 2026-09-13; glossary,
  "Per-character leash ladders"): one character on the model at a time
  on the 3-seat table `Plum,Mustard,Green`, seed 7007, 24 paired games
  per value. Neither Mustard (0 / 0.25 / 0.5 / 1) nor Plum (0.25 / 0.5
  / 1) gains from more rope; presets stand. Records and JSONs in
  `data/llm` (`ladder-headless`, `ladder-mustard-leash-*`,
  `ladder-plum-leash-*`, the set-aside `ladder-plum-leash-0-aborted`).
- **The parking mechanism (glossary, "Per-character leash ladders").**
  The model plays the character's top-scored option as an instruction;
  the headless character *samples* the same scores (`sample_softmax`,
  Plum's temperature 0.05). Plum's `movement_scores` gives 0.20 to any
  room he can suggest in this turn regardless of its probability and
  ~0.13 to a hallway toward the room his count favours, so once he
  stands in a cleared room, "stay" is top and the model never leaves:
  at leash 0.5 he declined an allowed escape toward a live room on 103
  of 109 such calls, one game running 126 turns on one repeated
  suggestion. More rope only offers more escapes to decline. Ties are
  the special case (stable sort, "stay" listed first, always chosen).
  Fix candidates, neither done, both needing a re-measure and
  re-recorded fixtures: make `movement_scores` prefer a step toward a
  live room over a cleared one (changes headless Plum and the goldens
  too), and/or have the prompt present scores as preference, not order.
  Deferred behind Phase 7 by David: logbooks first.
- **Retracted:** the twin arena's "the leash rescues Mustard" reading.
  Alone on the model his win rate does not move at any leash and his
  wrong% at the preset is worse than headless; the twin improvement was
  the LLM table around him.
- Live spend to date is about $63 at list prices ($23 through the twin
  run and pooled sweep, $27 for the ladders, $12.60 for Phase 7d). An LLM seat-game costs
  $0.07-0.11 for most characters but about $0.25 for Plum, whose games
  run long and ask the model often; low-leash games run longer still.
  Estimates have come in under twice: quote a range, not a point, and
  get a yes before any live run.

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
  headless as `RemarkEvent`s; off-turn chat is Phase 8.)
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
  (`docs/remeasure-plan.md`).
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
  `GameState` or any seat's view), `memory` (Tier 1 method memory), the
  arena and dial sweeps.
- `clude_storage` -- `GameRecord`/`SeatRecord`, `LocalStore`, `GcsStore`
  (with generic document methods), `logbooks` (`LogbookEntry`,
  `LogbookHead`, `Logbook`, the memory-depth renderer).
- `clude_llm` -- menus, schemas (three, `LOGBOOK_SCHEMA` the third),
  prompts, personas (`personas/*.md` and `rules.md`), backends
  (`NullBackend`, `ScriptedBackend`, `RecordingBackend`/`ReplayBackend`,
  `AnthropicBackend`), `LLMCharacter` (with `attach_logbook`,
  `read_back`, `debrief`), `logbook` (the debrief prompt).
- `scripts/clude_cli.py` -- the maintainer CLI; `tests/` -- pytest.

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
- Memory is off by default and changes nothing when off: Mustard's
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
  and debugging tool. (Headless `trace` exists; the UI is Phase 8.)
- **Chat pacing.** Stagger arrivals, cap concurrent speakers at two; the
  chattiness dial gates participation, not just verbosity.
- **Logbook reset** control, for fairness.
- **Human seats and player identity.** Each suspect is a Seat, occupied
  by a human or its seat-locked cludebot (the cludebot half is built,
  above). Human identity is a chosen display name independent of
  seat, written into `SeatRecord.label` so the logbook follows it.
  Rationale in `docs/architecture.md`, "Seats and player identity".

## Open questions (ask, don't assume)

One, now for after the re-measurement: whether `movement_scores` still
needs changing. On the ring the logbook (David's first hypothesis)
halved Plum's stalls at leash 0.5 but could not act at the preset
0.25, and the scoring change was the only fix there. The Classic stay
rule (2026-09-15) removed the free "stay" the parking lived on, so the
question is open again until Plum is re-measured on the grid
(`docs/remeasure-plan.md`, step 2b). Resolved 2026-09-13: leash presets stand; the parking
fix waits behind logbooks; `docs/zenbot_memories.json` is the logbook
model; no writing into `commit_msg.md`. Resolved 2026-09-14: the three
Phase 7 decisions above; the UX design pass comes between Phase 7 and
Phase 8.

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
- Tests: `& .venv\Scripts\python.exe -m pytest -q`. `CLUDE_LLM_LIVE=1`
  enables the live API smoke test (`-k live`), `CLUDE_GCS_LIVE=1` the
  bucket test.
- CLI: `& .venv\Scripts\python.exe scripts\clude_cli.py <cmd> --help`,
  where `<cmd>` is `agents`, `play`, `prompt`, `trace`, `floor`,
  `benchmark`, `train-mustard`, `snapshots`, `arena`, `sweep`, `store`
  or `logbook`. Every command is deterministic per `--seed` (and, with
  `--logbook`, per logbook state). `docs/cli.md` explains each and how
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
- `docs/strategy-glossary.md` -- each method in plain language; the
  benchmark, dial sweeps, tuned presets, and the Phase 6 measurements.
- `docs/llm-wrapper.md` -- how a model pilots a character; credentials;
  measured costs.
- `docs/logbooks.md` -- playerbot memory: the three tiers, the `memory`
  dial, the debrief, the CLI, cost.
- `docs/cli.md` -- every subcommand.
- `docs/board.md` -- the Classic board as measured, the doors, the
  rules, what the module exposes, and the ring it replaced.
- `docs/board-plan.md` -- the board rebuild: plan, David's decisions,
  and "as implemented". `docs/remeasure-plan.md` -- the costed plan to
  re-run every glossary measurement on the grid.
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
