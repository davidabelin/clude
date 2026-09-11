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
own known-issues list (`legacy/README.md`), five things needed doing before
it could serve as the floor -- all five are done in
`clude_constraints/propagator.py`:

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

Implemented in `clude_constraints/propagator.py`. Output shape, consumed by
every agent:

```python
@dataclass(frozen=True)
class ConstraintResult:
    possible_holders: dict[str, frozenset[Holder]]  # Holder = int | 'envelope'
    or_constraints: tuple[tuple[frozenset[str], int], ...]  # still-unresolved joint constraints
    hand_sizes: dict[int, int]

    def holder_of(self, card: str) -> Holder | None: ...   # resolved holder, or None
    def is_possible(self, card: str, holder: Holder) -> bool: ...
    def solution(self) -> tuple[str, str, str] | None: ...
```

Two things worth noting about this shape, since it differs from the
original pseudocode above:

- `possible_holders` is exposed per card (not collapsed to known/unknown),
  because Peacock's Dempster-Shafer method wants exactly that
  mass-assignment-shaped structure.
- `or_constraints` is exposed too, separately, because per-card marginals
  lose the joint "this player holds at least one of these three" structure
  that Plum's exact enumeration needs to search the true joint posterior
  correctly -- a masked marginal alone isn't enough for him.

`propagate(obs: ClueObservation) -> ConstraintResult` recomputes from
scratch every call (own hand, then every suggestion's eliminations/OR
constraints/hard reveals, then a fixpoint loop over OR-constraint
collapse, the category rule, and hand-size saturation). Verified sound by
`tests/test_constraints.py`: across many real random-bot games, replayed
through every player's `ClueObservation`, the floor never rules out the
true holder of any card, and at least one player reaches full certainty
given enough turns.

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

    def choose_destination(
        self,
        obs: ClueObservation,
        legal_moves: list[MoveChoice],
        room_features: dict[str, RoomFeatures],
    ) -> MoveChoice:
        """Phase 5. Pick where to move this turn. `room_features` covers
        only the room-type entries in `legal_moves`; shared feature
        extraction, per-agent decision -- see the note above. A `HumanAgent`
        implements this by asking the UI instead of a model, through the
        same signature."""
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

## Room/suggestion target selection is not the same problem as belief

Flagged by David before Phase 2 started, and worth keeping explicit: an
agent's room-card belief (P(this room card is in the envelope), one of the
three masked sub-distributions in its belief vector) answers a different
question than "which room should I move toward this turn." Moving to a
room only buys you the room slot of your next suggestion -- suspect and
weapon are freely named regardless of position -- so a room's value isn't
its envelope probability, it's the best expected information gain from a
suggestion made there, discounted by reachability this turn (`legal_moves`)
and by opponent-danger (does refuting there teach a dangerous opponent too
much).

This is a **policy/action-selection** concern, not one of the six inference
methods, so it belongs in the Phase 5 personality layer, not `clude_agents`.

**Refined per David:** room choice must stay a genuine trainable input for
each character, not one shared analytic formula deciding for all six --
that would collapse the "six distinct methods" design exactly where it
matters most (an action every character actually takes, every turn). The
split:

- **Shared and deterministic -- feature extraction only.** For each room
  reachable this turn (the subset of `legal_moves()`'s output where
  `board.room_of(destination)` is not None), compute a numeric feature
  vector: this agent's own masked probability that the room card is the
  envelope's (already sitting in its belief vector -- no new computation),
  reachability/distance, opponent-danger, whether anything's even left to
  learn by suggesting there. Arithmetic over shared inputs, safe to share
  like `ConstraintResult` is.
- **Not shared -- the decision itself.** Turning that feature vector into
  a pick is per-agent: `choose_destination(obs, legal_moves, room_features)
  -> MoveChoice`, trainable/tunable per character like its belief method,
  not a fixed formula. A human player is presented the identical reachable-
  room menu and feature vector (surfaced in the UI) and picks directly
  through the same interface point -- real parity between LLM characters
  and human seats.

Starting point for the feature side: `legacy/info_agent.py`'s
`InformationAgent.best_suggestion(current_room)` already takes the room as
given and searches suspect/weapon only, with a placeholder expected-info-
gain calc to replace; `legacy/opponent_model.py`'s `danger_score`/
`safe_to_suggest` is the opponent-danger half.

Implementation is still Phase 5 (action selection), but `AgentProtocol`
should reserve the slot now so Phase 3 doesn't need a breaking change
later -- see the protocol sketch below.

## Deferred legacy code

`legacy/dqn.py`, `legacy/gnn.py`, `legacy/ml_agent.py`, and
`legacy/reward_shaping.py` answered "one strong all-round agent," not "six
distinct ones." None is one of the six methods above, so none is on the
critical path. They stay in `legacy/` as reference, not ported.

## Reveal integrity and the lying/expulsion house rule

David's ruling: characters may talk about, hint at, or bluff about their
own cards at their own discretion (including side-bets), and are meant to
learn the cost of over-sharing rather than have it designed away. The one
hard line: refusing a reveal you're actually required to make is
system-enforced expulsion.

That line is already close to unbreakable by construction. `resolve_suggestion`
(`clude_core/engine.py`) computes who must show a card straight from
`state.hands[p]` -- ground truth -- and calls `choose_card_to_show` only on
a player already known to hold a match. There is no code path today where a
player is asked "can you refute?" and allowed to answer untruthfully; the
question the engine actually asks is "which of these do you want to show,"
and only to someone who has no honest way to say "none."

This matters for every later phase that adds a decision point the current
engine doesn't have: once chat and human/LLM seats exist (Phase 8), nothing
should ever let a typed or spoken claim ("I don't have that") substitute
for this ground-truth check for the *formal* refutation step. Bluffing
stays legal everywhere else -- idle chat about your hand, claims outside a
suggestion you're party to, side-bets -- because none of that is the
system verifying a required reveal. Expulsion is therefore a backstop
invariant (a protocol violation should be unreachable if the UI/agent
layer is built correctly), not a mechanic that needs new state-machine
branches. Worth a regression test once Phase 6+ introduces any path where
a seat's own claim is consulted before the engine's ground truth is.

## Deployment cost

Cloud Run is confirmed as the target (see `CLAUDE.md`), but budget is
effectively zero, so cost needs to stay near zero too. Cloud Run scales to
zero between requests and the free tier (2M requests/month, generous
CPU-seconds) should cover a private game with a handful of family/friend
players -- likely $0/month at this traffic level even before optimizing
anything. Two things to watch once chat/websockets land (Phase 8): a
long-lived websocket connection keeps an instance warm (billed) for the
duration, so an idle lobby with a connection left open costs more than the
request-count math suggests; and `min-instances: 0` must stay set (no
always-warm instance) since that's what makes idle time free. If either of
those ever pushes real cost, cheaper always-on alternatives for this scale
are Fly.io's free allowance (small VM, no cold start, supports
websockets natively) or self-hosting on Orbit behind a tunnel (Tailscale
Funnel or Cloudflare Tunnel) -- free, but only reachable while the laptop
is on. Not needed yet; revisit if a Cloud Run bill ever shows up.

## Open questions

Carried from `CLAUDE.md`; not yet decided: none, as of 2026-09-11 (see
`CLAUDE.md` and `docs/phase-plan.md` for what was resolved). The Seat /
`PlayerIdentity` model for human seats and cross-game logbook identity is
under active discussion and not yet confirmed.
