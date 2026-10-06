# legacy/

Code from an earlier claude.ai chat, "Machine learning for Clue game in Python."
It aimed at one strong all-round agent; current packages use six distinct
methods over a shared floor. These files are reference material, never imported
by the application. Chat code is preserved; only module docstrings/imports were
added. Use [architecture](../docs/architecture.md) for current contracts.

Torch-free modules (`domain`, `belief_tracker`, `constraints`, `info_agent`,
`opponent_model`, `reward_shaping`) need only numpy and scipy. `dqn`, `gnn`, and
`ml_agent` need torch; `gnn` also needs torch-geometric.

## What each file is for now

| File | Contents | Current disposition |
|---|---|---|
| `domain.py` | Card lists, `Suggestion`, `GameState` | Informed `clude_core`; current contracts are separate |
| `constraints.py` | `ConstraintPropagator` (OR-constraints, propagation) | Informed `clude_constraints`; defects below belong to this legacy solver |
| `belief_tracker.py` | `BayesianBeliefTracker` (card × holder marginals) | Informed Scarlett's naive-Bayes method |
| `opponent_model.py` | `OpponentModel` (suggestion-history heuristics) | Informed White's Markov model |
| `info_agent.py` | `InformationAgent` (suggestion chooser) | Reference only; its information math is a placeholder |
| `reward_shaping.py`, `dqn.py`, `gnn.py` | RL reward, Dueling DQN, card-player GNN | Deferred; none is one of the six methods |
| `ml_agent.py` | `ClueMLAgent` wiring everything together | Reference only |

## Known issues

Items marked ✔ are reproduced by `python -m legacy.known_issues_check`.

These are legacy limitations, not defects in the current deduction floor.

**constraints.py.**
- ✔ `_possible_holders` doesn't track eliminations (its own comment says "track eliminations in production"), so `add_no_refutation` can never deduce anything.
- It has no category rule, meaning exactly one suspect, one weapon, and one room are in the envelope, and the last unlocated card of a category must be the envelope's.
- Hand sizes are stored but never used.
- Contradictions are silently skipped in `_propagate`, and `_set_known` doesn't check consistency when a card is reassigned.
- It labels the envelope `'envelope'` while the tracker uses holder index 0.

**belief_tracker.py.**
- ✔ When someone refutes, the players asked before them who passed are not zeroed out, so that information is lost.
- ✔ Envelope probabilities aren't constrained per category. They drift (sum 1.25 after one unrefuted suggestion), and the tracker can't conclude the last unlocated suspect is in the envelope (stays at 0.5).
- The refuter update is a fixed ×1.5 boost rather than a likelihood. That's arguably fine for Scarlett, whose flaw is sloppy independence, but it should be a deliberate choice.

**info_agent.py.** `_expected_info_gain` is a placeholder heuristic, not expected information gain. It computes the current entropy and never uses it. The `scipy` import is unused.

**opponent_model.py.** `safe_to_suggest` ignores its card arguments and `min_refutation_probability`. `estimated_knowledge` is documented as "knows where the card is," but the repeated-suggestion heuristic uses it to mean "probably doesn't hold it."

**ml_agent.py.** The no-refutation branch is a `pass`, so `add_no_refutation` is never called.

**domain.py.** `Suggestion` has no field for the card actually shown. The card names are the Classic originals, which is what clude uses (see CLAUDE.md).

**dqn.py / gnn.py** (deferred). `encode_state` omits the turn count its docstring promises, and `ACTION_ACCUSE` is unused. In the GNN, the holder type one-hot is never set, and edge weights are built but never passed to `GCNConv`.
