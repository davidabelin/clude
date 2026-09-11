# Architecture

## Package layout

Mirrors the shape of `rps` (and `c4`, which already copies it): a protocol,
a name-keyed registry, one module per method, sibling packages by concern.

```
clude/
  clude_core/          # domain model, ClueObservation, event log, GameState
  clude_constraints/    # the deduction floor (finished ConstraintPropagator)
  clude_agents/          # AgentProtocol + AgentSpec registry + one module per method
    base.py
    naive_bayes.py        # Scarlett
    exact_enum.py          # Plum
    dempster_shafer.py      # Peacock
    decision_tree.py         # Mustard
    bandit.py                  # Green
    markov.py                   # White
  clude_training/       # self-play loop, decision-tree/bandit training, benchmarks
  clude_storage/         # logbooks, game logs, trained model artifacts
  clude_web/              # Flask/Cloud Run app, chat, UI (phase 8+)
  scripts/
  tests/
  docs/
```

`legacy/` is not a dependency of any of the above. It is read, and its ideas
and fixes are ported in; nothing imports `legacy` directly once a package
supersedes it. See `legacy/README.md` for what came from where.

## Environment

Python 3.14, from the `pythoncore-3.14-64` install under
`C:\Users\David\AppData\Local\Python` (newer than the 3.13 the system `python`
on PATH resolves to, and newer than the `rps` Cloud Run runtime, which stays
on 3.13 — clude doesn't need to match it). Managed with a standard venv
rather than conda:

```
C:\Users\David\AppData\Local\Python\pythoncore-3.14-64\python.exe -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

No conda environment is used for this project, so as not to depend on the
machine's miniconda install being on `PATH`.

## The deduction floor (`clude_constraints`)

A single shared constraint-propagation layer computes what is *logically*
still possible, and every agent's probabilities are masked and renormalized
over that surviving set before use. Agents differ in how they reason under
uncertainty; they never differ in what is logically certain. This is what
makes it safe for Scarlett's naive Bayes to be sloppy about soft evidence
without ever assigning nonzero probability to a card in her own hand.

Built by finishing `legacy/constraints.py`'s `ConstraintPropagator`. Per its
own known-issues list (`legacy/README.md`), five things need doing before it
can serve as the floor:

1. `_possible_holders` must actually track eliminations. Right now it
   returns "all holders" unless the card is fully known, which makes
   `add_no_refutation` a no-op — its own comment admits this
   ("simplified; track eliminations in production").
2. Add the category rule: exactly one suspect, one weapon, and one room
   are in the envelope, and once every other card in a category is
   located, the last unlocated one is the envelope's.
3. Enforce hand sizes (`self.hand_size` is stored but never read).
4. Make contradiction handling consistent: `_set_known` doesn't check
   consistency when a card is reassigned, and `_propagate` silently drops
   `or_constraints` that reduce to zero instead of raising.
5. Pick one envelope convention. `constraints.py` uses the string
   `'envelope'` as a holder; `belief_tracker.py` uses holder index `0`.
   Standardize on one (`'envelope'` is more readable and is what
   `constraints.py` already does; `clude_core` will use it too).

Output shape, consumed by every agent:

```python
@dataclass
class ConstraintResult:
    known: dict[str, str | int | None]      # card -> holder ('envelope', player index, or None)
    or_constraints: list[tuple[frozenset[str], int]]  # (candidate cards, holder) still undetermined
    hand_sizes: dict[int, int]

    def is_possible(self, card: str, holder: str | int) -> bool: ...
```

## `ClueObservation`

The one contract every agent consumes. Extends `legacy/domain.py`'s
`GameState`/`Suggestion`, closing the gap the legacy README flags (`Suggestion`
has no field for the card actually shown):

```python
@dataclass(frozen=True)
class Suggestion:
    suggester: int
    suspect: str
    weapon: str
    room: str
    refuter: int | None       # None if no one could refute
    shown_to: int              # who saw the card (usually == suggester)
    card_shown: str | None     # populated only when shown to the observing agent

@dataclass(frozen=True)
class ClueObservation:
    n_players: int
    my_index: int
    own_hand: frozenset[str]
    active_players: tuple[bool, ...]
    hand_sizes: dict[int, int]
    suggestion_log: tuple[Suggestion, ...]
    accusation_log: tuple[tuple[int, str, str, str, bool], ...]  # (player, s, w, r, correct)
    turn: int
    mask: ConstraintResult    # recomputed fresh each call; no agent can go stale
```

This is the most expensive object in the repo to change later, since all six
agents and the event log key off it — it is written once, in Phase 1, before
any agent code.

## `AgentProtocol`

Same shape as `rps_agents/base.py`, phase-scoped: through Phase 4 it returns
numbers only, not a chosen game action. The personality layer (Phase 5) is
what turns those numbers plus a parameter profile into an actual move.

```python
class AgentProtocol(Protocol):
    name: str

    def reset(self, seed: int | None) -> None: ...

    def select_action(self, obs: ClueObservation) -> ClueBelief:
        """Return this agent's belief over the 21 cards, already masked and
        renormalized against obs.mask. Phase 5+ callers additionally pass
        this through a personality profile to obtain a ClueAction."""
        ...

    def observe(self, transition: ClueTransition) -> None: ...
```

`AGENT_SPECS` is a name-keyed registry (`clude_agents/__init__.py`), same
pattern as `rps_agents.heuristic.AGENT_SPECS`, keyed by suspect name.

## Method-to-suspect mapping

| Character | Method | Legacy starting point | Failure mode as personality |
|---|---|---|---|
| Scarlett | Naive Bayes over reveal events | `belief_tracker.py`, demoted (see below) | Independence assumption is false here, so she's overconfident — accuses early, sometimes brilliantly, sometimes disastrously |
| Plum | Exact posterior by world enumeration | new | Correct and slow; needs sampling at 5-6 players to stay in budget, and gets noisy under it |
| Peacock | Dempster-Shafer belief/plausibility | new | Won't commit until plausibility collapses — cautious, sometimes too cautious to win the race |
| Mustard | Decision tree trained on game logs | new (needs `clude_training` self-play data first) | Pattern-matches past games rather than reasoning; confidently wrong on unusual deals |
| Green | Bandit ensemble over the other five | ports from `rps_agents/heuristic/multi_armed_bandit.py` | Opportunistic, hedges; only as good as his arms |
| White | Markov model over opponents' suggestion sequences | `opponent_model.py`, starting point | Reads people rather than cards; strong on who's close to solving, weak on the envelope itself |

Why `belief_tracker.py` is *demoted* rather than reused as-is: it stores
marginals (`belief[card, holder]`) and row-normalizes, which can't express
"these two cards are in the same hand" and doesn't enforce hand size, so it
drifts from the true posterior. That's wrong for Plum (who needs the real
posterior) but is exactly Scarlett's character flaw, so it becomes her
method once it's routed through the deduction floor.

## Per-turn data flow (Phases 1-3 scope)

```
GameState ──► ConstraintPropagator.propagate()
                     |
                     v
              ConstraintResult (known + or_constraints)
                     |
       +-------------+------+------+------+------+-------------+
       v             v      v      v      v      v             v
  NaiveBayes    ExactEnum  DShafer  DTree  Bandit  Markov
  (Scarlett)     (Plum)   (Peacock)(Mustard)(Green) (White)
       |             |      |      |      |      |             |
       +-------------+-- masked/renormalized against mask -----+
                                   |
                                   v
                     belief vector per agent (21 cards)
                [Phase 3 stops here -- logged for UI/benchmark]
                                   |
                        -- Phase 5 adds --
                                   v
                personality profile -> scored legal actions
                                   |
                        -- Phase 6 adds --
                                   v
              LLM: menu of legal actions + persona -> action + dialogue
              (invalid/malformed response falls back to top-scored action)
```

## Deferred legacy code

`legacy/dqn.py`, `legacy/gnn.py`, `legacy/ml_agent.py`, and
`legacy/reward_shaping.py` answered "one strong all-round agent," not "six
distinct ones." None is one of the six methods above, so none is on the
critical path. They stay in `legacy/` as reference, not ported.

## Open questions

Carried from `CLAUDE.md`; not yet decided:

- May characters talk about their own cards, and may they lie?
- Should logbooks remember a human player's tells across games?
- What is the deployment target? (Cloud Run is proposed but not confirmed.)
