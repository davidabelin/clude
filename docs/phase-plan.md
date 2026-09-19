# Phase Plan

Ordered so each phase is a testable system on its own; everything after
Phase 5 is presentation on top of a working game. Per `CLAUDE.md`: change
working systems one incremental step at a time, and confirm before moving
to the next phase.

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Headless rules engine, dumb random-legal-move bots, full game loop, structured event log | done |
| 2 | Finished `ConstraintPropagator` deduction floor; convergence tests | done |
| 3 | Six strategy agents, each emitting a masked/renormalized belief vector; no action selection yet | done |
| 4 | Benchmark harness measuring the six methods' relative strength; `docs/strategy-glossary.md` filled in | done |
| 5 | Personality parameter profiles turning beliefs into actions; self-play checks that dials move win rate | done -- plan and David's decisions in `docs/phase5-plan.md`, results in `docs/strategy-glossary.md` |
| 6 | LLM wrapper: leashed menu of legal actions + persona -> structured action + remark; anything illegal, malformed or failed falls back to the character's own decision | done: built (6a-6d), tested on fake backends, and live-checked, persona-tuned and measured on Opus 5 on 2026-09-13, with per-character leash ladders the same day (presets stand) -- `docs/phase6-plan.md` |
| 7 | Logbooks: persistent, per-character, written after every game | done: built (7a-7c) on fake backends and live-checked and measured (7d) on Opus 5, all on 2026-09-14: three tiers of memory, a `memory` dial, the debrief, `--logbook-characters`, seat-locked characters; at leash 0.5 Plum's own notes cut his stalls by more than half at the price of two early accusations -- `docs/phase7-plan.md`, `docs/logbooks.md` |
| 8.0 | Re-measurement on the Classic board: every glossary number re-run on the grid, presets retuned, the LLM measurements repeated, method memory reset, the landing rule for the passage loop | done: 8.0.0-8.0.1 (2026-09-15), 8.0.2a-b and 8.0.3 (2026-09-16), 8.0.4 the landing rule (2026-09-18) -- `docs/phase8.0-plan.md`, `docs/phase8-plan.md` |
| 8.1 | 8.1a a basic UX scaffold as a local Flask app (login, lobby, replay, watching a headless game); 8.1b the same app on Cloud Run | done: 8.1a 2026-09-17, 8.1b deployed 2026-09-18 -- `docs/phase8.1-plan.md`, `docs/web.md` |
| 8.2 | Human players: human seats beside the cludebots, identity by login name | built 2026-09-18: the table driver and `play --human` (8.2a), the table on the web with open seats, autopilot, rebuild and "characters remember" (8.2b-c), deployed (8.2d) -- `docs/phase8-plan.md`, `docs/web.md` |
| 8.3 | The rest of chat: off-turn talk, staggered arrivals, capped concurrent speakers, chattiness-gated | not started |
| 9 | In-depth UX: the decorated board and logo, typography, motion, the six-seat layouts, the case-file styling | not started |
| 10 | Clean-up and close; then release to family and friends as version 1.0.0, planned in versions from then on | not started |

Design work on aesthetics/UX was meant to run in parallel with the
model phases (1-4). It did not, and became its own pass between Phase 7
and Phase 8 (David, 2026-09-14). On 2026-09-15, before that pass drew
the board, the engine's ring simplification was replaced by the Classic
grid and rules (`docs/board-plan.md`, `docs/board.md`); every
measurement before it was on the ring, and the re-measurement plan
scheduled the re-run.

On 2026-09-16 David renumbered what follows Phase 7. The re-measurement
became Phase 8.0 (its stages 8.0.0-8.0.3). Phase 8, which had been
"front end, then chat, then human seats", became 8.1 (the scaffold and
Cloud Run), 8.2 (human players) and 8.3 (chat): human players now come
before chat, since chat's hard parts are about people at the table and
bot table talk already exists headless. The UX pass splits into 8.1a's
scaffold and Phase 9's in-depth work. Phase 10 closes development; the
release after it is version 1.0.0, to family and friends (a public
release would first need the IP scrub in `CLAUDE.md`), and planning
continues in versions rather than phases.

## Legacy code disposition

| File | Contents | Fate |
|---|---|---|
| `domain.py` | Card lists, `Suggestion`, `GameState` | Reused, extended into `ClueObservation` (Phase 1) |
| `constraints.py` | `ConstraintPropagator` | Superseded by `clude_constraints/propagator.py` -- the 5 fixes in `docs/architecture.md` are done |
| `belief_tracker.py` | `BayesianBeliefTracker` | Demoted to Scarlett's naive-Bayes method (Phase 3) |
| `opponent_model.py` | `OpponentModel` | Starting point for White's Markov model (Phase 3) |
| `info_agent.py` | `InformationAgent` | Starting point for Phase 5's room/suggestion target-selection policy -- a separate problem from belief inference; see `docs/architecture.md` |
| `reward_shaping.py`, `dqn.py`, `gnn.py` | RL reward, Dueling DQN, card-player GNN | Deferred indefinitely; not one of the six methods |
| `ml_agent.py` | `ClueMLAgent` wiring | Reference only |

## Phase 1 scope

- `clude_core`: `Suggestion`, `GameState`/`ClueObservation` per
  `docs/architecture.md`, event log types rich enough to support later
  post-game replay of all six belief traces.
- Rules engine: legal-move generation, turn order, suggestion/refutation
  resolution, accusation resolution, win/loss detection.
- Dumb bots: uniform-random choice among legal moves. No inference.
- A full game loop runnable headlessly end to end, plus a CLI entry point
  (`scripts/`) to play/watch one game -- now `python scripts/clude_cli.py
  play`; see `docs/cli.md`.
- `tests/`: rules-engine correctness (legal moves, refutation order,
  accusation resolution, game termination).

Explicitly out of scope for Phase 1: any probability computation, any of
the six agents, any LLM call, any UI.

## Phase 2 scope

- `clude_constraints`: `propagate(obs) -> ConstraintResult`, a pure
  function run fresh from a `ClueObservation` every call -- own hand,
  per-suggestion elimination/OR-constraint/hard-reveal facts, then a
  fixpoint loop (OR-constraint collapse, the category rule, hand-size
  saturation). No agent-facing probability yet -- that starts Phase 3.
- `tests/test_constraints.py`: targeted unit tests per propagation rule
  (category rule, OR-constraint collapse, hand-size saturation,
  contradiction detection), a soundness property test across many random
  real games (the floor must never rule out the truth), and a convergence
  test (at least one player reaches full certainty given enough turns).

Explicitly out of scope for Phase 2: any of the six agents' own
probability methods, any action selection, any LLM call, any UI.

## Phase 3 scope

- `ClueObservation.mask`: the field docs/architecture.md always specced
  is now populated -- `clude_constraints.observe(state, viewer)` builds
  an observation and attaches a freshly computed `ConstraintResult`.
  Kept `Optional`/defaulted in `clude_core.state` purely to avoid a
  circular import (`clude_constraints` already depends on `clude_core`);
  `for_player` itself still never sets it.
- `clude_agents`: `AgentProtocol`, `ClueBelief`, and the shared
  `mask_and_normalize` helper (`base.py`), plus one module per method
  and the `AgentSpec` registry (`build_agent`, `list_agent_specs`),
  mirroring `rps_agents`.
- All six methods implemented per `docs/strategy-glossary.md`'s
  per-agent summaries. Mustard's tree bootstraps its own training data
  from Phase 1's `RandomBot` self-play, since `clude_training` doesn't
  exist yet -- a placeholder, not the real Phase 4 pipeline.
- `tests/test_agents.py`: the Phase-3 analogue of Phase 2's soundness
  test -- across real self-play games, no agent may assign nonzero
  probability to a card the floor eliminated, or anything but 1.0 to one
  it proved -- plus one or two targeted tests per agent's distinguishing
  behavior (Plum checked against an independent brute-force enumerator;
  Peacock's Belief <= Plausibility invariant; White's chain checked
  directly to dodge a normalization ceiling effect; and so on).
- Bug fix surfaced along the way, not scoped to Phase 3 but blocking it:
  `board.reachable` returned a bare `set`, whose iteration order depends
  on Python's per-process string-hash randomization, so `RandomBot`'s
  seeded `rng.choice` over it produced a *different* game from the same
  `seed` on every process run -- reproducible within one pytest session
  (one process, one hash seed) but not across separate runs, which is
  what made a real self-play game safe to use as Mustard's training data
  in the first place. Fixed with `board.node_sort_key` (`clude_core/board.py`,
  `clude_core/engine.py`); verified stable across several `PYTHONHASHSEED`
  values.

Explicitly out of scope for Phase 3: action selection (`choose_destination`
stays a reserved, unimplemented slot), personality parameters, any LLM
call, any UI, and the real `clude_training` self-play pipeline.

## Phase 4 scope

- `clude_training/self_play.py`: `generate_snapshots(n_games, seed,
  checkpoints)`, the real self-play pipeline `clude_agents/decision_tree.py`
  was a placeholder for -- `RandomBot` games snapshotted at several
  checkpoints (25/50/75/100% of suggestions played by default), yielding
  masked observations paired with the eventual ground truth. Mustard's
  tree now trains against this instead of duplicating the game-running
  loop itself. Deliberately depends only on `clude_core`/`clude_constraints`,
  never `clude_agents`, so agents can depend on it without a cycle back
  through `clude_training.benchmark` (which depends on `clude_agents`).
- `clude_training/benchmark.py`: `run_benchmark(...)` scores all six
  agents' belief against ground truth on shared snapshots -- Brier
  score, log-loss, and top-1 category accuracy, per checkpoint, against
  a `"uniform"` (zero-evidence) baseline. Since Phase 5 doesn't exist
  yet, this measures belief quality, not win rate. Green's instance is
  built once and never reset mid-run (David's call, 2026-09-11), so his
  Beta posteriors accumulate real cross-game learning instead of
  cold-starting every game.
- CLI: `python scripts/clude_cli.py benchmark`. (The original
  `scripts/benchmark.py` and `scripts/play_game.py` were folded into the
  unified `scripts/clude_cli.py` alongside `trace`, `floor`,
  `train-mustard`, and `snapshots` -- see `docs/cli.md`.)
- `tests/test_training.py`: snapshot-generation shape and reproducibility,
  `_Accumulator` arithmetic checked against closed-form expectations on
  synthetic beliefs, an end-to-end run confirming at least one real
  method beats the uniform baseline, and a check that Green's posteriors
  actually move (not just that the run doesn't crash).
- Findings written up in `docs/strategy-glossary.md`'s new "Phase 4
  benchmark results" section: Plum/Scarlett/Peacock land at or better
  than the uniform baseline as expected; Mustard and White are both
  measurably *worse* than pure ignorance on log-loss for the whole game
  (White dramatically so, 3-4x) -- a calibration problem, not a ranking
  one, since top-1 accuracy stays in line with everyone else. David's
  call: leave it as-is rather than smoothing it away, since it's the
  intended "confidently wrong" character flaw, now quantified rather
  than asserted -- useful input to Phase 5's personality tuning.

Explicitly out of scope for Phase 4: any change to the six agents'
algorithms in response to their benchmark scores (see above), action
selection, personality parameters, any LLM call, any UI.

## Phase 5 scope

Planned in `docs/phase5-plan.md` (David's answers to its six decisions
are recorded there) and built in the five sub-phases it lays out:

- **5a, the engine seam.** `clude_core.engine.PlayerProtocol` replaces
  `RandomBotProtocol`: the four decisions take the seat's
  `ClueObservation` first, built by an `observer` injected into
  `run_game` (default `ClueObservation.for_player`, so `clude_core` still
  never imports the floor; `clude_constraints.observe` for anything that
  needs a mask). The refuter is told `shown_to`; the accusation sees
  this turn's refutation. Golden fingerprints of seeded `RandomBot`
  games proved the seam byte-identical before anything else changed.
- **5b, the self-play regime and calibration.** `clude_constraints.FloorBot`
  is the standard opponent (`--bot floor`, now the default for
  `generate_snapshots`, the benchmark, and Mustard's training); Mustard's
  leaves are m-estimates and his features gain `distinct_namers` and
  `named_beside_located`; White starts unresolved cards at the floor's
  prior and reports per-opponent `repeat_probability`/`closeness`;
  Green's arm reward is a rank per snapshot, and the Phase 4 test now
  demands his arms *separate*. Two Phase 1 rules bugs were found by the
  first games with intent and fixed: a token could not leave a room
  except by secret passage (`board.reachable` treated the start room as
  terminal), and a boxed-in hallway token had no legal move. One floor
  fix: satisfied or-constraints are dropped rather than kept as open.
- **5c, the personality layer.** `clude_agents.personality.Profile` (five
  dials, six presets, `to_dict`/`from_dict`), `features.py` (shared
  room-choice features, softmax sampling), `character.py`
  (`Character(agent, profile, confidence_fn)` implementing
  `PlayerProtocol`; Peacock's confidence is her DS lower bound),
  `AGENT_SPECS` gaining `profile` and `confidence_fn`, and
  `SeededAgentMixin.choose_destination` getting its real default. One
  unit test per decision.
- **5d, the arena and storage.** `clude_training.arena` (fixed seating by token since 2026-09-14, seat rotation before,
  table-size cycling, FloorBot fill, Green's `observe` per game, metrics
  with n and binomial std) and `clude_training.sweep` (paired runs per
  dial value, `monotone`). `clude_storage` started a phase early:
  `GameRecord` and `LocalStore`/`GcsStore` behind one interface, the
  `clude-game-data` bucket created, and the arena writing to either.
- **5e, tuning.** Sweeps of all five dials, the presets adjusted, and
  the results written up in `docs/strategy-glossary.md`.

Explicitly out of scope for Phase 5, and still not done: any LLM call,
any UI, chat, logbooks (beyond what `GameRecord` stores for Phase 7 to
read), danger/urgency dials, and any change to a method's core algorithm
beyond its absence-of-evidence case.

## Phase 6 scope

Planned in `docs/phase6-plan.md` (David's answers to its four decisions
are recorded there) and built in four sub-phases, each noted here as it
lands.

- **6a, the seam (done).** `Character`'s suggestion and card-to-show
  scoring split from their sampling into RNG-free helpers
  (`suggestion_candidates`, `cards_exposed`, `show_scores`) beside
  `Character.movement_scores` and `accusation_test`, with golden
  fingerprints of seeded character games proving no game moved;
  `clude_agents/explain.py` holding the belief, floor and suggestion
  text formatters lifted out of the CLI (its output diffed identical);
  `RemarkEvent` and the engine's `SpeakingPlayer` hook; `RECORD_VERSION`
  2 with the `remark` codec.
- **6b, the wrapper on fake backends (done).** `clude_llm`: `menu`,
  `schema`, `prompt`, `persona` (+ `personas/rules.md`), `backend`
  (`NullBackend`, `ScriptedBackend`, `RecordingBackend`/`ReplayBackend`,
  `open_backend`) and `player` (`LLMCharacter`, `LLMSettings`,
  `Decision`); the `leash` and `chattiness` dials on `Profile`;
  `SpeakingPlayer.hear`; `SeatRecord.model` and `GameRecord.llm_log`;
  `play --llm --llm-backend null|replay:PATH`. Tests pin the null and
  adversarial backends to the character goldens, every fallback path,
  reveal integrity under random letters, RNG-free menus, fixed schemas,
  the prompt's redaction, and record/replay.
- **6c, the real backend (done).**
  `clude_llm/anthropic_backend.py` (`AnthropicBackend`: cached system
  block, `output_config` format + effort, 30 s timeout, one SDK retry,
  server-side refusal fallbacks on by default, every error a fallback
  result; `estimate_cost`), six persona files, the `prompt` subcommand,
  `anthropic>=1.5` in `requirements.txt`, unit tests on a fake client and
  a `CLUDE_LLM_LIVE=1` smoke test. The live checks were done on
  2026-09-13. The smoke test passes. Two games were read for persona
  tuning, which led to a no-repetition rule in `rules.md` and a
  no-decimals line for Plum. Two recorded fixtures under
  `tests/fixtures/` replay offline.
- **6d, the arena (done).**
  `run_arena(llm_backend=..., llm_settings=..., llm_characters=...)` and
  `sweep_dial` likewise; `PlayerStats` gains the LLM counters and rates
  (`fallback_rate`, `deviation_rate`, `remarks_per_game`,
  `tokens_per_game`, `llm_ms_per_call`); an LLM table under the arena
  table; `kind="llm"` seats with their model and each game's `Decision`
  audit in the records; `arena --llm` and `sweep --llm` with a cost
  estimate; `docs/llm-wrapper.md`. Measured 2026-09-13: the twin run
  and the `leash` sweep, with results in `docs/strategy-glossary.md`.
  Presets were left unchanged; the per-character leash ladders followed
  the same day and left them standing (glossary, "Per-character leash
  ladders").

## Phase 7 scope

Planned in `docs/phase7-plan.md` (David's answers to its three
decisions are recorded there) and built in three sub-phases on
2026-09-14, all on fake backends; the working guide is
`docs/logbooks.md`.

- **7a, Tier 0 and the documents.** `clude_training/replay.py` (a
  stored record back into a `GameState`, any seat's masked view, the
  self-play `Snapshot`s); generic document methods on both stores;
  `clude_storage/logbooks.py` (`LogbookEntry`, `LogbookHead`,
  `Dossier`, `Logbook`, the memory-depth renderer); the `memory` dial;
  `play --store`; `logbook list | show | reset`.
- **7b, method memory.** `rows_from_view` and `extra_rows` for
  Mustard, per-identity transition priors and `set_table` for White,
  `state_dict` / `load_state` for Green; `Character.new_game(table)`;
  `clude_training/memory.py` (load, update, rebuild, describe);
  `--logbook` and `--logbook-readonly` on `play` and `arena`,
  read-only `--logbook` on `sweep`, `logbook rebuild`, `train-mustard
  --logbook`. Rebuilt from the 193 stored ladder games in 3 s.
- **7c, narrative memory.** `LOGBOOK_SCHEMA`; `LLMRequest.memory` as a
  second cached system block, with per-request effort and
  `max_tokens`; `clude_llm/logbook.py` (the debrief prompt, opponent
  resolution); `LLMCharacter.attach_logbook` / `read_back` / `debrief`;
  the arena debriefing LLM seats with an `entries` column; `prompt
  --logbook`.
- **7d, the live run (2026-09-14).** The debrief needed its own
  timeout (`LLMSettings.debrief_timeout`, 180 s: the wrapper's 30 s
  killed every debrief in the smoke run); the debrief prompt was
  tuned on six real entries; `--logbook-characters` gives only the
  named characters a logbook; and every character was locked to its
  own token (`seat_lineup`, `engine.run_game(..., suspects=...)`,
  goldens and fixtures re-captured). Measured on 24 paired games with
  Plum on the model at leash 0.5, his logbook on against off: stalls
  fall by more than half over the run (37 to 3 in the last quarter),
  two early accusations, wins a wash (`docs/strategy-glossary.md`,
  "Plum's logbook at leash 0.5"). About $12.60 of live spend.

Explicitly out of scope for Phase 7, and still not done: off-turn
chat, any UI, human seats, any change to `movement_scores` or the
presets, any change to a method's core algorithm beyond the memory
seams, the `memory` sweep itself, and any measurement run at ladder
scale.

## Open questions

Ask before assuming; do not resolve unilaterally. None outstanding as of
2026-09-18: the parking question (whether to change the movement
scoring for Plum's loop) was decided that day -- the landing rule,
measured headless and kept (`docs/phase8.0-plan.md` 8.0.4,
`docs/strategy-glossary.md` "The landing rule").

Resolved:

- Environment is a Python 3.14 venv (`pythoncore-3.14-64` under
  `C:\Users\David\AppData\Local\Python`), not conda — see `docs/architecture.md`.
- Characters may talk about and bluff about their own cards at their own
  discretion. House rule: refusing a reveal you're actually required to
  make is system-enforced expulsion — see `docs/architecture.md`.
- Logbooks must remember a human player's tells across games, independent
  of which seat/suspect they play next.
- Deployment target is Cloud Run, budget permitting — see
  `docs/architecture.md` for the cost caveat.
