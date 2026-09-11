# Phase Plan

Ordered so each phase is a testable system on its own; everything after
Phase 5 is presentation on top of a working game. Per `CLAUDE.md`: change
working systems one incremental step at a time, and confirm before moving
to the next phase.

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Headless rules engine, dumb random-legal-move bots, full game loop, structured event log | done |
| 2 | Finished `ConstraintPropagator` deduction floor; convergence tests | done |
| 3 | Six strategy agents, each emitting a masked/renormalized belief vector; no action selection yet | not started |
| 4 | Benchmark harness measuring the six methods' relative strength; `docs/strategy-glossary.md` filled in | not started |
| 5 | Personality parameter profiles turning beliefs into actions; self-play checks that dials move win rate | not started |
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
  (`scripts/`) to play/watch one game.
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
