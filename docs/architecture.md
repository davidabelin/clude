# Architecture

## Package layout

Mirrors the shape of `rps` (and `c4`, which already copies it): a protocol,
a name-keyed registry, one module per method, sibling packages by concern.

```
clude/
  clude_core/          # domain model, board, ClueObservation, event log, GameState, rules engine
  clude_constraints/   # the deduction floor (ConstraintPropagator) and FloorBot
  clude_agents/        # AgentProtocol + AgentSpec registry + one module per method
    base.py
    naive_bayes.py        # Scarlett
    exact_enum.py          # Plum
    dempster_shafer.py      # Peacock
    decision_tree.py         # Mustard
    bandit.py                  # Green
    markov.py                   # White
    personality.py     # Profile: the five dials, six presets
    features.py        # shared room-choice features and softmax sampling
    character.py       # Character(agent, profile): the four engine decisions
    explain.py         # plain-text views of a seat's knowledge: CLI, LLM prompt, later UI
  clude_llm/           # Phase 6: menus, personas, LLM backends, LLMCharacter; Phase 7: the debrief (logbook.py)
  clude_training/      # self-play snapshots, belief benchmark, trace, arena, sweeps; Phase 7: replay.py, memory.py
  clude_storage/       # game records and logbooks; local and Cloud Storage stores
  clude_web/           # Flask/Cloud Run app, chat, UI (phase 8+, not started)
  scripts/             # clude_cli.py
  tests/
  docs/
```

`legacy/` is not a dependency of any of the above. It is read, and its ideas
and fixes are ported in; nothing imports `legacy` directly once a package
supersedes it. See `legacy/README.md` for what came from where.

Import direction, which the tests rely on: `clude_core` imports nothing
else; `clude_constraints` imports `clude_core`; `clude_training.self_play`
imports both but never `clude_agents`; `clude_agents` imports all three;
`clude_training.benchmark/trace/arena/sweep` and `clude_storage` sit on
top. `clude_training/__init__.py` stays empty of submodule imports so
Mustard's tree can depend on `self_play` without a cycle. Phase 7
added `clude_training.replay` (imports `clude_storage`,
`clude_constraints`, `self_play`) and `clude_training.memory` (imports
the agents, `clude_storage` and `replay`); `clude_llm.logbook` imports
`clude_training.replay` for a seat's live view, and `clude_training.arena`
imports `clude_llm` and `memory` above them all.

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
machine's miniconda install being on `PATH`. The only non-test dependency
is `google-cloud-storage`, imported lazily and only by `gs://` record
stores (see "Cloud Storage" below); everything else is the standard
library.

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
    or_constraints: tuple[tuple[frozenset[str], int], ...]  # still-open joint constraints
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
`tests/test_constraints.py`: across many real bot games, replayed
through every player's `ClueObservation`, the floor never rules out the
true holder of any card, and at least one player reaches full certainty
given enough turns.

Phase 5 fix: an or-constraint that a located card already satisfies is now
dropped rather than kept as "open". Keeping it was harmless to the mask
(it could never eliminate anything) but Peacock read the surviving,
still-unlocated members as live evidence against those cards, and the
`floor` CLI printed satisfied constraints as open. Plum's search already
filtered them itself.

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
    accusation_log: tuple[Accusation, ...]
    turn: int
    mask: ConstraintResult | None   # recomputed fresh each call; no agent can go stale
```

This is the most expensive object in the repo to change later, since all six
agents and the event log key off it — it was written once, in Phase 1,
before any agent code, and has not needed a field since. Positions are
deliberately not in it: nothing an agent decides today needs them (room
choice is driven by the legal-move list, which already encodes where the
mover is), and adding them is a one-line, defaulted change if a danger
feature ever needs them.

**As implemented (Phase 3):** `mask` is `Optional[ConstraintResult] = None`
in `clude_core.state`, not required as sketched above — `clude_constraints`
already depends on `clude_core`, so `clude_core` cannot import
`ConstraintResult` back at runtime without a cycle (the import there is
`TYPE_CHECKING`-only). `ClueObservation.for_player` never sets `mask`;
`clude_constraints.observe(state, viewer)` is the one place that builds an
observation and attaches a freshly computed mask, and every observation
reaching an agent's `select_action` is expected to have gone through it.

## The engine seam (Phase 5a)

`clude_core.engine.run_game` asks every seat four questions through
`PlayerProtocol`, each with that seat's `ClueObservation` first:

```python
class PlayerProtocol(Protocol):
    def choose_movement(self, obs, choices: list[MoveChoice], rng) -> MoveChoice: ...
    def choose_suggestion(self, obs, room: str, rng) -> tuple[str, str] | None: ...
    def choose_accusation(self, obs, rng) -> tuple[str, str, str] | None: ...
    def choose_card_to_show(self, obs, candidates: list[str], shown_to: int, rng) -> str: ...
```

The observation is built by an injectable `observer: Callable[[GameState,
int], ClueObservation]`, defaulting to `ClueObservation.for_player`, so
`clude_core` still never imports the deduction floor; anything that needs
a mask (`FloorBot`, every `Character`) is run with
`observer=clude_constraints.observe`. One observation serves a turn's
movement and suggestion decisions (nothing a `ClueObservation` carries
changes between them), a fresh one is built for the accusation once the
suggestion has resolved so its refutation is visible, and the refuter
gets its own observation -- from which the suggestion being refuted is
still absent, hence the explicit `shown_to`. Building an observation
consumes no RNG, so the seam left every seeded `RandomBot` game
byte-identical (`tests/test_engine.py` carries golden fingerprints).

Three implementations exist: `clude_core.bots.RandomBot` (ignores the
observation, draws from the engine RNG), `clude_constraints.FloorBot`
(below), and `clude_agents.character.Character` (below). A player with
its own RNG must leave the engine's alone, so that a seeded game's deal
*and* dice depend only on the seed -- the property the arena's paired
comparisons rest on.

Two rules bugs surfaced as soon as players with intent existed, both
fixed in Phase 5b: `board.reachable` treated the *starting* room as
terminal, so a token could only ever leave a room by secret passage
(every earlier self-play game piled up in one room for that reason); and
a hallway token boxed in by other tokens had no legal move at all, where
Clue simply has it stay put (`legal_moves` now offers ``stay`` in that
case). The golden fingerprints were regenerated once, after those fixes.

Phase 6a added one optional extension to the seam without touching
`PlayerProtocol`: a seat that also implements `SpeakingPlayer`
(`take_remarks() -> list[str]`, a `runtime_checkable` Protocol) has
whatever lines it buffered appended to the event log as `RemarkEvent`s
right after each decision -- the mover after its `MoveEvent`, the
suggester and then the refuter after the `SuggestionEvent`, and the
accuser after its accusation decision whether or not it accused. Players
without the method are never asked, so every golden fingerprint held.
Remarks are public and have no game effect; they exist so replay and
Phase 8's live view get dialogue interleaved with the actions it
accompanied, in one ordered log.

## `AgentProtocol`

Same shape as `rps_agents/base.py`. `select_action` returns numbers only,
never a chosen game action; the personality layer is what turns those
numbers plus a parameter profile into an actual move.

```python
class AgentProtocol(Protocol):
    name: str

    def reset(self, seed: int | None) -> None: ...

    def select_action(self, obs: ClueObservation) -> ClueBelief:
        """Return this agent's belief over the 21 cards, already masked and
        renormalized against obs.mask."""
        ...

    def choose_destination(
        self,
        obs: ClueObservation,
        legal_moves: list[MoveChoice],
        room_features: list[ChoiceFeatures],
        profile: Profile,
    ) -> MoveChoice:
        """Pick where to move this turn. `room_features` is shared
        arithmetic over the agent's own belief and the board; the pick is
        the agent's. The default (SeededAgentMixin) is a softmax over the
        profile's curiosity-weighted blend; any method may override it."""
        ...

    def observe(self, transition: RevealedOutcome) -> None: ...
```

`AGENT_SPECS` is a name-keyed registry (`clude_agents/__init__.py`), same
pattern as `rps_agents.heuristic.AGENT_SPECS`, keyed by suspect name. Since
Phase 5 each spec also carries the character's preset `Profile` and its
`confidence_fn`, and `build_character(name)` returns a playable seat.

**As implemented (Phase 3):** `ClueBelief` is `{probabilities: dict[str,
float], extra: dict[str, Any]}` -- `extra` is where a method reports
whatever doesn't fit a flat per-card probability (Peacock's raw
Belief/Plausibility bounds, Green's selected arm, White's per-opponent
repeat probabilities and closeness proxy). Only Green's `observe` does
anything, against `RevealedOutcome` (just the solved envelope), which is
all any agent has needed so far.

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

## Per-turn data flow

```
GameState ──► observer (clude_constraints.observe) ──► ClueObservation + mask
                                   |
       +-------------+------+------+------+------+-------------+
       v             v      v      v      v      v             v
  NaiveBayes    ExactEnum  DShafer  DTree  Bandit  Markov
  (Scarlett)     (Plum)   (Peacock)(Mustard)(Green) (White)
       |             |      |      |      |      |             |
       +-------------+-- masked/renormalized against mask -----+
                                   |
                                   v
                     ClueBelief per agent (21 cards + extra)
                                   |
                        -- Phase 5 (Character + Profile) --
                                   v
          movement (features + curiosity/temperature) ─► MoveChoice
          suggestion (belief softmax, bluff_rate)      ─► (suspect, weapon)
          accusation (confidence_fn product >= threshold) ─► triple or None
          card to show (secrecy)                        ─► card
                                   |
                                   v
                        engine applies, appends events
                                   |
                        -- Phase 6 adds --
                                   v
              LLM: leashed menu of legal actions + persona -> action + remark
              (illegal/malformed/failed response falls back to the
               character's own decision above; docs/phase6-plan.md)
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
methods, so it belongs in the personality layer, not in the methods.

**Refined per David:** room choice must stay a genuine trainable input for
each character, not one shared analytic formula deciding for all six --
that would collapse the "six distinct methods" design exactly where it
matters most (an action every character actually takes, every turn). The
split:

- **Shared and deterministic -- feature extraction only.**
  `clude_agents.features.room_features(obs, belief, choices)` gives every
  legal move a `ChoiceFeatures`: the room it lands in this turn (if any),
  the room it is heading for, `information` (the agent's own masked
  P(that room card is the envelope's), discounted 0.7 per step still to
  go) and `proximity` (1 for a room this turn, else `1 / (1 + steps to
  the nearest room)`). Arithmetic over shared inputs, safe to share like
  `ConstraintResult` is. `board.room_distances` (breadth-first over
  hallways, rooms and secret passages) is the distance measure.
- **Not shared -- the decision itself.** `choose_destination(obs,
  legal_moves, room_features, profile) -> MoveChoice` is per-agent. The
  default on `SeededAgentMixin` scores each choice as
  `curiosity * information + (1 - curiosity) * proximity` and samples a
  softmax at the profile's `temperature` from the agent's own RNG; any
  method may override it. A human player is presented the identical
  reachable-room menu and feature vector (surfaced in the UI) and picks
  directly through the same interface point -- real parity between LLM
  characters and human seats.

Not yet in the features: opponent danger. docs/phase5-plan.md defers a
`w_danger` dial until there is a measured signal for it; White's
`closeness` proxy in `ClueBelief.extra` is the candidate input.

## Personality layer (Phase 5c)

`clude_agents.personality.Profile` is five floats, all-numeric and
slider-ready, each owning one engine decision and meant to move one arena
metric (the keep-a-dial rule: a dial that moves nothing monotonically in a
sweep is cut):

| Dial | Decision | Meaning | Metric it should move |
|---|---|---|---|
| `accuse_threshold` | accusation | accuse once P(correct) reaches this | wrong-accusation rate, turn of first accusation |
| `bluff_rate` | suggestion | P(naming one of my own cards instead of an honest pick) | own cards named |
| `curiosity` | movement | 1 = chase the most probable room, 0 = enter the nearest room | win rate |
| `secrecy` | card to show | 1 = re-show what this player has already seen, 0 = indifferent | own cards leaked |
| `temperature` | the three sampled decisions | softmax temperature over scores in [0, 1]; 0 = greedy | win rate |

`clude_agents.character.Character(agent, profile, confidence_fn)`
implements `PlayerProtocol`: one `select_action` per distinct observation
(so at most two per turn), then the four decisions off that belief. The
accusation is a threshold test, not a sample: P(correct) is the product
of the three category maxima of `confidence_fn(belief)`, which is the
belief's probabilities for five characters and the Dempster-Shafer
*belief* (lower bound) for Peacock -- her caution comes from her method,
not from a faked-up threshold, and `confidence_source` is therefore a
per-spec function rather than a profile field. The honest suggestion
never names a card in the character's own hand; only the `bluff_rate`
coin flip does. Everything random is drawn from the character's own RNG.

Since Phase 6a the scoring behind each decision is also available on its
own, RNG-free: `suggestion_candidates`, `cards_exposed` and `show_scores`
(module level in `character.py`) and `Character.movement_scores` /
`accusation_test`. The sampled decisions call these same helpers, with
the bluff coin still flipped first, so the split moved no seeded game
(`tests/test_character.py` carries golden fingerprints, captured on the
Phase 5 code, that prove it). `clude_agents.explain` renders a seat's
belief, the floor's grid and the suggestion log as text from an
observation and seat labels alone -- lifted from the CLI so the LLM
prompt and, later, a human's screen use the very same lines.

Presets live in `personality.PRESETS`, one per suspect; Mustard and White
sit at the neutral `accuse_threshold` on purpose, so that any wrong
accusation of theirs is attributable to the method (their calibration is
the flaw) rather than to a dial. How the presets were tuned, and what the
sweeps showed, is in `docs/strategy-glossary.md`.

## The LLM wrapper (Phase 6)

Planned in `docs/phase6-plan.md` (David's four decisions are recorded
there). `clude_llm.LLMCharacter` wraps a `Character` and implements both
`PlayerProtocol` and `SpeakingPlayer`; the arena and CLI treat it as a
character (`name`, `profile`, `select_action`, `reset`, `observe`,
`n_calls`, `seconds` all delegate).

One decision, every time:

1. **Menu.** `clude_llm.menu` builds the legal options from the
   character's own RNG-free scoring helpers: the engine's `MoveChoice`s
   scored by `movement_scores`; the honest suggestion candidates by
   belief, plus the character's own cards as labelled bluff options; the
   engine's ground-truth refutation candidates by `secrecy`; the
   accusation test. Best first, lettered `A`.., capped at twelve. Built
   from the seat's `ClueObservation` only, never `GameState`.
2. **Leash.** An option is allowed when its score is at least
   `(1 - leash)` of the best; `leash = 0` is the headless pick, `1` any
   legal option. Bluff options are allowed with any rope and a nonzero
   `bluff_rate`. The accusation menu (`[accuse, pass]`) applies the leash
   symmetrically: accusing is allowed once `P(correct) >= (1 - leash) *
   accuse_threshold`, passing whenever P is below the threshold or there
   is any rope. One allowed option means no call at all.
3. **Call.** `prompt.system_prompt` (persona file + `personas/rules.md`,
   byte-stable and cacheable) and `prompt.user_prompt` (hand, the floor's
   proven and located cards, the belief's top cards, the accusation test,
   the suggestion log as the seat saw it, recent table talk, the menu) go
   to an `LLMBackend` with a fixed JSON schema (`schema.py`: two schemas
   for the four decisions, so the API's schema cache always hits).
4. **Parse or fall back.** An allowed letter is played and its `say` line
   is buffered for the engine, published with probability `chattiness`
   from the wrapper's own RNG. Anything else -- budget, backend error or
   timeout, `refusal`, malformed JSON, an unknown or disallowed letter --
   calls the wrapped character's own method, which spends the
   character's RNG exactly as it would have headless. So `NullBackend`
   reproduces the headless game byte for byte, and an adversarial
   backend with `leash = 1` cannot move a single event
   (`tests/test_llm.py` pins both against the character goldens).
5. **Audit.** Every decision is a `Decision` (menu, letter, fallback
   reason, deviation from the top option, the line, tokens, seconds),
   stored per seat in `GameRecord.llm_log`; `SeatRecord.kind` is
   `"llm"` with the `model`.

Backends (`clude_llm.backend`): `AnthropicBackend` (6c, the SDK imported
lazily), `NullBackend`, `ScriptedBackend` for tests, and
`RecordingBackend`/`ReplayBackend`, which key every exchange by a digest
of the request so a recorded game replays with no spend and a changed
prompt surfaces as a `ReplayMiss`. `open_backend` resolves the CLI's
``--llm-backend``. Remarks reach the other LLM seats through
`SpeakingPlayer.hear`, called by the engine as it appends each
`RemarkEvent`, rather than through `ClueObservation`; if a belief method
ever wants to read table talk, that is the point to revisit.

## Memory: the logbooks (Phase 7)

Planned in `docs/phase7-plan.md` (David's three decisions are recorded
there); the working guide is `docs/logbooks.md`. One `Logbook` per
identity (a `SeatRecord.label`: a character name whichever token it
plays, later a human's display name), stored beside the records under
`logbooks/<identity>/` in the same local or `gs://` store, holding
three tiers of memory:

- **Tier 0, the record.** `GameRecord`, omniscient. `clude_training.replay`
  now does what `records.py` promised: `state_from_record` folds the
  event log back into the engine's `GameState` (a suggestion drags the
  named token into the room without a `MoveEvent`, so that step is
  applied too), `seat_view` gives any seat's masked view at any point,
  and `snapshots_from_record` the same `Snapshot`s self-play would have
  yielded. `play --store` writes a single game's record.
- **Tier 1, method memory** (`method.json`, `clude_training.memory`):
  numeric, headless, no model. Mustard's tree trains on
  `rows_from_view` rows from every seat's view of every stored game on
  top of his self-play base; White's chain for a known opponent starts
  from that opponent's transition frequencies at the Laplace prior's
  own mass (`prior_cells`), so only the chain's starting shape is
  informed; Green's Beta posteriors are saved after every game and
  restored after `reset`. Documents are keyed by game id, so an
  incremental `update` and a `rebuild` from a whole store agree.
  Scarlett, Plum and Peacock are memoryless by construction.
- **Tier 2, narrative memory** (`entries/NNNN.json`, `head.json`,
  `clude_storage.logbooks`, `clude_llm.logbook`): a zenbot-shaped entry
  per game, written by the character's own model at a debrief that
  sees the whole deal face up, plus a rolling head (tally, standing
  instructions, a dossier per opponent met, a flag index) that only the
  opponents present at a game have touched by its entry.

The `memory` dial on `Profile` (default 0) sets how much of its logbook
an LLM-piloted character reads before a game: the head at 0, plus an
index of entries (summary and flags) up to 0.5, plus whole entries
above that, every entry at 1. The block goes as a **second cached
system block** (`LLMRequest.memory`): stable for a game, so cached
after one write, while the persona block stays the cross-game prefix.
An empty logbook sends no block and leaves the request, its replay key
and the API call exactly Phase 6's, which keeps every recorded fixture
valid. The block only steers the model among the options its leash
allows; it never widens a menu.

Every character gets `new_game(table)` before a game (White's
`set_table` is how his priors find their seats) and, with a logbook
store, `clude_training.memory.load_into` after `reset`; after a game
`memory.update` and, for LLM seats, `LLMCharacter.debrief`. A read-only
mode reads and writes nothing, so a sweep (always read-only) compares
dial values on one logbook state. Determinism is "per seed and logbook
state": with no logbook nothing moves, and every golden holds.

## Self-play regimes: `RandomBot` and `FloorBot` (Phase 5b)

`clude_constraints.FloorBot` is the standard self-play opponent: a
seventh, characterless player that uses only the shared floor. Suspect
and weapon are uniform over cards neither in its hand nor located by the
floor (once a category is exhausted, its proven envelope card, which
nobody can refute, so the suggestion tests the others cleanly); it
accuses exactly when `mask.solution()` is not None; it shows a uniform
card. Movement deviates from docs/phase5-plan.md's "uniform over legal
moves", which was measured not to produce games that end: it prefers a
move landing in a room the floor has not located, else the move closest
to one, and once every room is located, a room nobody else can refute.
`RandomBot` is kept as the Phase 1 baseline (`--bot random`).

`clude_training.self_play.generate_snapshots(..., bot="floor")` is what
Mustard's tree trains on by default now, and what the benchmark scores
against. The `snapshots` CLI shows the difference: FloorBot games end in
about 12-23 suggestions with a third of viewers holding a proven
envelope at the end, where the old regime ran 80-180 suggestions with a
floor that plateaued early.

Three calibration changes landed with the regime, per the plan's
decision 3 and 4: Mustard's leaves are m-estimates (no hard zeros), White
starts every unresolved card at the floor's prior (an unnamed card is
unsuspicious, not impossible), and Green's arm reward is a rank on each
snapshot rather than an absolute score the floor dominated. Each is an
absence-of-evidence fix, not a change to the method.

## Arena, sweeps and game records (Phase 5d)

`clude_training.arena.run_arena` plays N whole games through the seam
with `clude_constraints.observe`, each character on its own suspect's
token and fills on the lowest free tokens, seats in board order
(`seat_lineup`; since 2026-09-14, before which seats rotated across
games), the table size cycling 3..6, missing seats filled with
`FloorBot`s. Per roster
label it reports win rate and wrong-accusation rate with binomial std,
mean turn of first accusation and the never-accused rate, distinct own
cards leaked, suggestions naming an own card, and ms per belief call.
Characters are built once per run and reset once, so Green's posteriors
persist and his `observe` at each game's end is what "learns across
games" means. Every game's deal and dice depend only on `seed + g`, so a
`sweep_dial` (the arena once per value of one dial, same seed) is a
paired comparison, and `SweepResult.monotone(metric)` is the keep-a-dial
test.

Since Phase 6d `run_arena(llm_backend=...)` wraps the roster's characters
(or `llm_characters`) in `LLMCharacter`s sharing one backend, calls
`new_game()` on each before every game, records `kind="llm"` seats with
their model and each game's `Decision` audit as `GameRecord.llm_log`,
and reports an LLM table (decisions, asked, fallback and deviation
rates, remarks and tokens per game, ms per call). The twin comparison
is two runs on one seed, with and without a backend; `NullBackend`
reproduces the headless run game for game.

Every game can be written as a `clude_storage.GameRecord`: seats (label,
suspect token, kind, profile dials), the deal, the full omniscient event
log, and the outcome; the run summary goes beside them. `RECORD_VERSION`
is 2 since Phase 6a, when `RemarkEvent`s joined the event log; version-1
documents load unchanged, and Phase 7 added no version: entries live in
the logbooks and reference a record by game id. Phase 7's logbooks read
these records -- a seat's own view is rebuilt from `events` by
`clude_training.replay` with `ClueObservation.for_player`'s redaction
rule -- and `SeatRecord.label` is the identity a logbook is keyed by,
which a human's display name is expected to join rather than replace.
`play --store` writes a single game as game 0 of a run with a one-game
summary, so `store` lists it.

## Cloud Storage

Decision 6 of docs/phase5-plan.md: game records can go to Google Cloud
Storage as well as a local directory, through one `RecordStore` interface
(`clude_storage.stores`). Facts, as set up on 2026-09-12:

- Project `clude-game`, bucket `gs://clude-game-data` (us-central1,
  Standard class, uniform bucket-level access, public access prevention
  enforced). Created with the service account after David enabled
  billing on the project; the free tier covers this usage.
- Credentials: the service-account key `clude-game-sa.json` at the repo
  root, which is gitignored and must never be committed or pasted
  anywhere. `GcsStore` finds it via the `CLUDE_GCS_CREDENTIALS`
  environment variable, else that default path, else application default
  credentials. Nothing in the repo reads the key except the client
  library.
- Layout is identical locally and remotely: `runs/<run_id>.json` and
  `games/<run_id>/<index>.json`. `python scripts/clude_cli.py arena
  --store gs://clude-game-data/arena` writes there; `store --uri
  gs://clude-game-data/arena` lists it. The default store is the local
  `data/` directory (gitignored).
- `tests/test_storage.py` exercises the GCS backend against an in-memory
  double; set `CLUDE_GCS_LIVE=1` to run one round trip against the real
  bucket.

## Claude API credentials (Phase 6c)

The `anthropic` SDK (`requirements.txt`) is imported lazily and only by
`clude_llm.anthropic_backend`; the test suite never needs it or the
network (`tests/test_llm.py` runs the backend against a fake client).
Credentials resolve exactly as the SDK does: `ANTHROPIC_API_KEY` in the
environment, else an `ant auth login` profile. Nothing is stored in the
repo and no key file joins `clude-game-sa.json`; the key never passes
through clude's code except as the backend's optional `api_key=`
argument. `CLUDE_LLM_LIVE=1` runs the one live smoke test (two calls, a
few cents); `CLUDE_LLM_MODEL` overrides its model. Spend is estimated at
list prices by `estimate_cost` and printed by `play --llm`.

In practice, as of 2026-09-13:

- The key must be scoped to a workspace. An organisation-level key gets
  a 400 on every call asking for an `anthropic-workspace-id` header, and
  the backend does not send one.
- The key sits in a gitignored `.env` at the repo root, but nothing
  loads that file. Export the variable into the environment before
  running. `docs/llm-wrapper.md` has measured per-game costs.

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
and only to someone who has no honest way to say "none". Phase 5's
`Character.choose_card_to_show` keeps that shape: it ranks the candidates
the engine hands it and never invents one.

This matters for every later phase that adds a decision point the current
engine doesn't have: once chat and human/LLM seats exist (Phase 8), nothing
should ever let a typed or spoken claim ("I don't have that") substitute
for this ground-truth check for the *formal* refutation step. Bluffing
stays legal everywhere else -- idle chat about your hand, claims outside a
suggestion you're party to, side-bets, and now the `bluff_rate` dial's
own-card suggestions -- because none of that is the system verifying a
required reveal. Expulsion is therefore a backstop invariant (a protocol
violation should be unreachable if the UI/agent layer is built correctly),
not a mechanic that needs new state-machine branches. Worth a regression
test once Phase 6+ introduces any path where a seat's own claim is
consulted before the engine's ground truth is.

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
is on. Not needed yet; revisit if a Cloud Run bill ever shows up. The
Cloud Storage bucket above is in the same boat: a few hundred kilobytes
per arena run, inside the always-free 5 GB-months for US regions.

## Seats and player identity (the cludebot half built; the human half proposed)

Answers "how do human players play, and how are they recognized across
games" (`CLAUDE.md`). The cludebot half was built on 2026-09-14 (a
character is locked to its own token; below); Phase 8 builds human
seats and Phase 7 built logbooks, and the identity model is recorded
here so neither needs a breaking change.

- **Seat** -- one of the six suspect slots for a single game. Exactly
  `suspects_in_play[i]` in `GameState`, now chosen by the caller
  (`engine.run_game(..., suspects=...)`) and carried to every player
  and prompt as `ClueObservation.suspects`. The arena's `SeatRecord`
  (seat index, suspect token, roster label, kind, profile) is the
  first persisted form of it.
- **`PlayerIdentity`** -- who's behind a seat, persistent *across* games.
  Deliberately kept out of `clude_core`/`clude_agents`: a `SeatAssignment
  {seat_index, suspect, identity}` map is built at table setup, before
  `engine.setup()` deals, and lives in `clude_web`/`clude_storage`. The
  engine and all six agents stay identity-agnostic and index-based, so
  none of Phases 1-5 needed to change for this.
  - LLM occupant: identity is intrinsic and seat-locked --
    `MissScarlettbot` is always naive Bayes, always Scarlett. No auth,
    no seat mobility. **Built 2026-09-14** (David: "Plum must never
    play Scarlett's seat"): `clude_training.arena.seat_lineup` puts
    each character on its own token, every other player on the
    lowest free token, and orders the seats as the board does; the
    arena and `play` seat every table with it, and a larger roster
    rotates only who sits out. Every character golden was re-captured
    and both LLM fixtures re-recorded that day; measurements before
    it (Phase 5's sweeps, Phase 6's twin arena and ladders) rotated
    characters through seats.
  - Human occupant: identity must be independent of seat, since
    remembering a human's tells across games only makes sense if the
    same person is recognized whether they're piloting Plum tonight and
    White next week. Given a small trusted circle and no budget for
    real auth: a human picks/enters a display name once; that name is
    the identity key. A `localStorage` token can pre-fill it by
    browser, but the name stays the source of truth, not the token.
- **Logbooks, two layers** (adapting `docs/zenbot_memories.json`'s
  shape -- structured + narrative + evaluative + lessons -- while
  splitting episodic record from durable fact, which that schema
  conflates):
  1. **Per-game entry**, keyed by `(identity, game_id)`, immutable.
     Zenbot-shaped: `title`, `key_insights`, `lessons_learned`,
     `final_outcome`, plus a `reads` list (zenbot's
     `session_evaluations` -- one per opponent faced that game:
     identity, evaluation, notes). Derivable from a `GameRecord`.
  2. **Per-opponent dossier**, keyed by identity alone, mutable, updated
     after every game -- zenbot's `user_instructions`, but rolling
     rather than per-session. This is what "remember tells across
     games" actually requires: without it, a tell would need
     re-deriving from full history on every lookup.

  Mustard's tree and White's Markov model train on layer 1; the
  personality/chat layer (Phase 8) reads layer 2 to recognize a known
  human by their established read.

  **As built (Phase 7):** the two layers are `entries/NNNN.json` and
  `head.json` under `logbooks/<identity>/`, keyed by `SeatRecord.label`
  as proposed, plus a third document, `method.json`, for the numeric
  memory. One departure: Mustard and White train on the game
  *records* (Tier 0), not on the entries, since the entry is narrative
  and the record is the data. A human's dossier will follow their
  label across seats with no further work; what Phase 8 must do is
  write the display name into `label`. See "Memory: the logbooks"
  above and `docs/logbooks.md`.

## Open questions

Carried from `CLAUDE.md`; not yet decided: none, as of 2026-09-12 (see
`CLAUDE.md` and `docs/phase-plan.md` for what was resolved).
