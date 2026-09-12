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
| 5 | Personality parameter profiles turning beliefs into actions; self-play checks that dials move win rate | planned -- see `docs/phase5-plan.md` (for discussion) |
| 6 | LLM wrapper: menu of legal actions + persona -> structured action + dialogue, illegal/malformed falls back to top-scored action | not started |
| 7 | Logbooks: persistent, per-character, written after every game | not started |
| 8 | Flask/Cloud Run front end -> chat (staggered, capped concurrency, chattiness-gated) -> human seats | not started |

Design work on aesthetics/UX runs in parallel with the model phases (1-4),
not after them.

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

## Open questions

Ask before assuming; do not resolve unilaterally. None outstanding as of
2026-09-11.

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
