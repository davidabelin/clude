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

## Status (2026-09-13)

Phases 1-6 of `docs/phase-plan.md` are done and committed. Phase 7
(logbooks) is next and not started; Phase 8 (Flask/Cloud Run front end,
then chat, then human seats) follows. There is no UI and no chat yet:
everything runs headless through `scripts/clude_cli.py`. The suite is
211 tests passing and 2 skipped (the two live-credential tests), ~22 s.

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
- **Retracted:** the twin arena's "the leash rescues Mustard" reading.
  Alone on the model his win rate does not move at any leash and his
  wrong% at the preset is worse than headless; the twin improvement was
  the LLM table around him.
- Live spend to date is about $50 at list prices ($23 through the twin
  run and pooled sweep, $27 for the ladders). An LLM seat-game costs
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
  (per-seat belief replay), the arena and dial sweeps.
- `clude_storage` -- `GameRecord`/`SeatRecord`, `LocalStore`, `GcsStore`.
- `clude_llm` -- menus, schemas, prompts, personas (`personas/*.md` and
  `rules.md`), backends (`NullBackend`, `ScriptedBackend`,
  `RecordingBackend`/`ReplayBackend`, `AnthropicBackend`), `LLMCharacter`.
- `scripts/clude_cli.py` -- the maintainer CLI; `tests/` -- pytest.

Invariants to keep:

- The floor masks every belief before it is used. Agents differ in how
  they reason under uncertainty, never in what is logically certain.
- One `ClueObservation` contract; the event log is rich enough to replay
  every character's belief after the fact (`trace`).
- Every game is deterministic per seed. `tests/test_character.py` holds
  golden fingerprints of seeded character games; a scoring change that
  moves a game must update them on purpose, never by accident.
- The LLM wrapper chooses only within the leash of the character's own
  scores and falls back to the character on anything illegal, malformed
  or failed. `NullBackend` reproduces the headless game byte for byte;
  that twin is what every LLM measurement is paired against.
- Mustard trains in-process on 25 FloorBot self-play games (seed 2026,
  `decision_tree.py`); nothing feeds stored records into him yet, and
  White's Markov model sees only the current game. Both are Phase 7's
  business. The first 56 LLM games were run without `--store` and are
  lost; every live run since goes to `data/llm`.

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
- **Seats and player identity.** Each suspect is a Seat, occupied by a
  human or a seat-locked cludebot. Human identity is a chosen display
  name independent of seat. Logbooks split into an immutable per-game
  entry and a mutable per-opponent dossier that carries tells forward.
  Rationale in `docs/architecture.md`, "Seats and player identity".

## Open questions (ask, don't assume)

- **Leash presets versus distinctness.** The pooled sweep favours leash
  0.5 table-wide (shortest games, no wrong accusations), but more rope
  moves every character toward the model's judgment and costs Plum most.
  How distinct must the six methods stay? Wait for the per-character
  ladders, then put the numbers to David.
- **The tie-break fixed point** (Status, above): fix in the wrapper, in
  `movement_scores`, or both? It changes behaviour at every leash, so it
  needs a re-measure and re-recorded fixtures.
- **`docs/zenbot_memories.json`** is a per-session memory-entry template
  from David's zenbot project, tracked here. Its purpose in clude is
  unconfirmed; it may be a model for Phase 7 logbook entries.

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
  `benchmark`, `train-mustard`, `snapshots`, `arena`, `sweep` or
  `store`. Every command is deterministic per `--seed`. `docs/cli.md`
  explains each and how to read its output.
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
  Status); `store --store data/llm` lists them.

## Docs map

- `README.md` -- public-facing overview, quick start, layout.
- `docs/architecture.md` -- package layout, the floor, `ClueObservation`,
  the engine seam, `AgentProtocol`, personality layer, LLM wrapper,
  storage, credentials, deployment cost, Seats proposal.
- `docs/phase-plan.md` -- the eight phases with status, legacy
  disposition, scope of each built phase.
- `docs/phase5-plan.md`, `docs/phase6-plan.md` -- plan, David's
  decisions, and "as implemented".
- `docs/strategy-glossary.md` -- each method in plain language; the
  benchmark, dial sweeps, tuned presets, and the Phase 6 measurements.
- `docs/llm-wrapper.md` -- how a model pilots a character; credentials;
  measured costs.
- `docs/cli.md` -- every subcommand. `docs/board.md` -- board topology.
- `docs/docstring-guidelines.md` -- docstring conventions.
- `docs/pre_stage_5.md` -- the "Fab4" review that reworked Phase 5
  against the code as it was; historical.
- `docs/commit_msg_correction.md` -- the commit-message shape David
  wants, as a WRONG/RIGHT pair. Local only: it is gitignored, so it may
  be absent on a fresh clone; the rule itself is stated above.
- `docs/clude_floorplan_wikimedia.svg` -- board floorplan reference from
  Wikimedia; check its licence before any publishing.
- `docs/zenbot_memories.json` -- see Open questions.
- `legacy/README.md` -- what the legacy code is and what is wrong with it.
