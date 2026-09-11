# Phase Plan

Ordered so each phase is a testable system on its own; everything after
Phase 5 is presentation on top of a working game. Per `CLAUDE.md`: change
working systems one incremental step at a time, and confirm before moving
to the next phase.

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Headless rules engine, dumb random-legal-move bots, full game loop, structured event log | in progress |
| 2 | Finished `ConstraintPropagator` deduction floor; convergence tests | not started |
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
| `constraints.py` | `ConstraintPropagator` | Basis of the deduction floor once the 5 fixes in `docs/architecture.md` land (Phase 2) |
| `belief_tracker.py` | `BayesianBeliefTracker` | Demoted to Scarlett's naive-Bayes method (Phase 3) |
| `opponent_model.py` | `OpponentModel` | Starting point for White's Markov model (Phase 3) |
| `info_agent.py` | `InformationAgent` | Math is a placeholder; maybe reused for shared suggestion-choice logic once real, not a priority |
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

## Open questions

Ask before assuming; do not resolve unilaterally.

- May characters talk about their own cards, and may they lie?
- Should logbooks remember a human player's tells across games?
- What is the deployment target? (Cloud Run proposed, not confirmed.)

Resolved: environment is a Python 3.14 venv (`pythoncore-3.14-64` under
`C:\Users\David\AppData\Local\Python`), not conda — see `docs/architecture.md`.
