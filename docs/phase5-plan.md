# Phase 5 Plan (refined, 2026-09-11)

Status: **approved 2026-09-12 and implemented.** David's answers to the
six decisions are in section 6; what was actually built, and where it
departed from this plan, is in section 8 at the end. This reworks the
Phase 5 design in `docs/review_pre_stage_5.md` (the "Fab4 review"), read
as a set of suggestions, against the code as it stood and against
numbers from the maintainer CLI (`docs/cli.md`). Items marked **ASK**
were the ones that needed David's call before any code was written.

## 1. What the measurements say

Everything below is reproducible with the command shown.

**Call cost** (`benchmark --games 12 --checkpoints 0.5 1.0`):

| Agent | ms per `select_action` | Why |
|---|---|---|
| Plum | 12-28 | backtracking search, worse early in a game |
| Green | 12-33 | queries all five arms, so Plum's cost plus Mustard's |
| Scarlett, Peacock, Mustard, White | 0.0-0.2 | pure functions of the observation |

A 6-seat arena game of ~60 turns at one belief per character per turn
is therefore about 60 x (28 + 33) ms = ~4 s, and a 3-4 seat game about
1-2 s. Plum hit his node budget and fell back to sampling in 4 of 108
benchmark calls, and at k=0 of a 3-player game (`trace --players 3`).
The review's speed flag is real in direction but small in magnitude:
200 arena games is minutes, not hours.

**Hard zeros** (`docs/strategy-glossary.md`, calibration note): 69% of
Mustard's and 79% of White's log-loss comes from the 5-7% of categories
where they put *exactly* 0 on the true card. On every other category
they are calibrated as well as Plum. Mustard's zeros are leaves with no
positive training rows (`train-mustard` prints `leaf predictions: min
0.000`); White's are cards no opponent has named yet.

**Green does not learn** (`benchmark --show-green`): after 108
snapshots his five arms sit at mean 0.740-0.752 with identical
evidence. The reward is mean probability on the three true cards, which
the shared floor dominates; the arms differ by a percent or two, so
Thompson sampling picks among them essentially at random (watch
`[arm: ...]` flip in any `trace`). The Phase 4 test only checks that
the posteriors *moved*, which they do -- together.

**The training regime is the wrong regime** (`floor --convergence`,
`snapshots`): `RandomBot` games run 80-120 suggestions, and the floor
plateaus early -- seed 1 at 4 players makes no deduction after k=40 of
183, no viewer ever proves the envelope, and at 6 players the `solved`
fraction is 0.00 at every checkpoint. Random suggesters name their own
cards and re-name located ones, so late suggestions carry nothing.
Mustard's rows at checkpoints 0.5/1.0 come mostly from that plateau,
and the benchmark's snapshots do too. This is a bigger problem than the
review's "RandomBot vs characters" distribution shift: the informative
regime is barely in the data at all.

## 2. Where this agrees with the review

- **5a, the engine seam, first.** `run_game` drives
  `RandomBotProtocol`, which never sees a `ClueObservation`; every agent
  only ever gets one post hoc. Replace it with a `PlayerProtocol` whose
  four decisions take `obs` first, and inject `observer:
  Callable[[GameState, int], ClueObservation]` into `run_game`,
  defaulting to `ClueObservation.for_player`, so `clude_core` still
  never imports `clude_constraints` (review Q1: yes). `RandomBot` grows
  an ignored `obs`; adding the call consumes no RNG, so every seeded
  game stays byte-identical -- add a golden test for that.
- **Shared features, per-character decision.** Exactly what
  `docs/architecture.md` already requires for room choice: feature
  extraction is shared arithmetic, the pick is the character's.
- **Don't encode the flaw twice.** Mustard's and White's profiles stay
  neutral on `accuse_threshold` so any wrong accusation is attributable
  to the method. Extended below: fix the *artifacts* before tuning, or
  the dials end up compensating for them.
- **Metrics and the keep-a-dial rule.** Win rate, wrong-accusation
  rate, turn of first accusation, own cards leaked; a dial that doesn't
  move at least one of them monotonically in a sweep is cut.

## 3. Where this differs

- **Speed is not a design driver yet.** No per-game budgets, no
  memoizing Plum on the observation hash. The arena reports `ms/call`
  like the benchmark does; revisit only if a sweep is actually slow.
- **Fewer dials to start** (review Q2). Five, each owning one engine
  decision and one metric: `accuse_threshold` (accusation),
  `bluff_rate` (suggestion), `curiosity` (room choice: information vs
  distance), `secrecy` (card to show), `temperature` (softmax over
  scores, shared by all four). `w_danger` and `urgency` come back with a
  concrete trigger: a measured danger or closeness signal that moves
  win rate. `confidence_source` is not a dial (review Q3): Peacock's
  spec supplies a `confidence_fn` that reads her DS lower bound from
  `ClueBelief.extra`; profiles stay all-numeric and slider-ready.
- **A smarter dumb bot before any tuning.** See 4.1.
- **Mustard's retraining is not a Phase 7 item.** The distribution
  problem is fixable now with better self-play; logbook data (Phase 7)
  is a later, additional source.

## 4. The training issues, and proposed approaches

### 4.1 The self-play regime: a `FloorBot`

A seventh, characterless player that uses only the shared floor -- no
belief method, no personality -- so it is still "dumb" in the
six-methods sense but generates games that carry information and end:

- movement: uniform over legal moves (unchanged);
- suggestion: uniform over suspects/weapons that are neither in its own
  hand nor located by the floor (falls back to any if none);
- accusation: exactly when `mask.solution()` is not None, never
  otherwise;
- card to show: uniform (unchanged).

Needs 5a (it consumes an observation). Expected effects, all checkable
with `snapshots` and `floor --convergence`: games end by deduction,
`solved` > 0 at every table size, far fewer suggestions per game, and
Mustard's rows sample the regime where deduction is actually happening.
It doubles as the benchmark's opponent pool, the arena's fill seat
(3-4 seat tables for fast sweeps), and the "does a character beat a
purely logical player" baseline, the way `uniform` is the belief
baseline. **ASK:** adopt `FloorBot` as the standard self-play opponent
and regenerate Mustard's default training data from it?

### 4.2 Mustard: calibration, then distribution

Two separable problems:

1. *Hard zeros from empty leaves.* Proposed: an m-estimate leaf value,
   `(positives + m * base_rate) / (n + m)` with m around 2-5 rows, so a
   leaf with no positives predicts a small number rather than 0.0. One
   line in `_build_tree`; `train-mustard --eval-games 30` shows the
   before/after. This keeps the tree, keeps the pattern-matching, and
   keeps "confidently wrong" as *miscalibration* rather than
   *impossibility*. It does reverse the 2026-09-11 "leave as-is" call,
   which was made before the split above was measured. **ASK.** The
   argument for reversing: in Phase 5, P(correct) for an accusation is a
   product of category maxima, and a category whose other cards are
   zeroed reads as certainty. Hard zeros will make him accuse on
   nothing, which is a bug wearing a character's clothes.
2. *Distribution.* Retrain the default tree on `FloorBot` self-play
   (4.1). Add features Mustard can only get from smarter play: whether
   the suggester named a card the floor has already located, how many
   distinct suggesters have named this card. Later (Phase 7), the
   logbooks' per-game entries become a third source with human and LLM
   play in it.

### 4.3 White: the same zero, a different cause

`raw[c] = sum(n * p_repeat)` is 0 for any card no opponent has named,
so early in every game most cards are impossible to White. Proposed:
start every still-possible card at the floor's uniform prior and *add*
the Markov evidence on top (`raw = 1 + sum(...)`), so an unnamed card is
merely unsuspicious rather than excluded. The method is unchanged; only
its absence-of-evidence case is. Measurable with `benchmark --agents
White`. **ASK** (same reversal as 4.2). Separately, White's actual
strength -- reading who is close to solving -- has no consumer until
Phase 5; his `extra` should expose a per-opponent closeness estimate so
an `urgency` dial has something to read if it is ever added.

### 4.4 Green: a reward with signal in it

The arm reward must compare arms *against each other on the same
snapshot*, not against the truth in absolute terms. Two candidates,
both cheap:

- *rank reward*: best arm on this snapshot (by log-loss) scores 1,
  worst 0, linear in between;
- *margin vs uniform*: reward = clipped `(uniform_logloss -
  arm_logloss) / uniform_logloss`, so an arm is rewarded for beating the
  floor's own belief and punished for losing to it.

Rank is simpler and scale-free; margin is more informative when all
arms are bad. Proposed: rank first, and the Phase 4 test tightened from
"posteriors moved" to "posteriors separated" (max mean - min mean above
some threshold after N games), verifiable with `--show-green`. **ASK:**
rank or margin? Cadence stays as is -- one `observe` per revealed
envelope; in the arena that is once per game, which is what "learns
across games" means.

### 4.5 Sweeps are training too: sample sizes and held-out discipline

- Detecting a 5-point win-rate shift needs roughly 200 games per dial
  setting at 6 seats (binomial std ~2.6 points) and fewer at 3-4 seats.
  Report every arena metric with n and a binomial std, so a sweep's
  claim is honest.
- Rotate seats across games (Scarlett moves first) and cycle table size
  as `generate_snapshots` does.
- Keep training seeds (Mustard's 2026..) disjoint from evaluation seeds
  (4004..); `train-mustard` already warns on overlap.
- Cache self-play games on disk (`clude_storage/`, JSON event logs)
  once the arena exists, so a sweep replays the same deals for every
  dial setting rather than regenerating them -- a paired comparison,
  which needs far fewer games than independent ones.

## 5. Sub-phases

Each is a working system on its own, with the existing suite green
before moving on.

| | Deliverable | Check | CLI |
|---|---|---|---|
| 5a | `PlayerProtocol` (obs-first), `observer` injected into `run_game`, `RandomBot` adapted | all tests pass; golden test: seed-1 game unchanged | -- |
| 5b | `FloorBot`; Mustard retrained on it; leaf smoothing, White's prior, Green's rank reward (each **ASK**) | `snapshots` shows games end; benchmark before/after per change; Green's arms separate | `snapshots --bot floor`, `benchmark --bot floor` |
| 5c | `clude_agents/personality.py` (`Profile`, five dials, `to_dict`/`from_dict`, six presets), `features.py` (`room_features`, no danger yet), `character.py` (`Character(agent, profile)` implementing `PlayerProtocol`), `AGENT_SPECS` gains `profile` and Peacock's `confidence_fn`, `choose_destination` default | unit test per decision; a default character never accuses below its threshold; leaks only via bluffs | `trace` gains the chosen action per step |
| 5d | `clude_training/arena.py`: N games among characters and/or `FloorBot`s, seat rotation, table-size cycling, Green's `observe` at game end; metrics with n and std | a `accuse_threshold` sweep moves wrong-accusation rate monotonically | `arena`, `sweep` |
| 5e | Presets tuned so the arena reproduces the intended flavors; results in `docs/strategy-glossary.md`; dials that don't move a metric cut | the glossary table | -- |

5b's three calibration changes are independent of each other and of
`FloorBot`; any of them can be dropped without blocking the rest.

## 6. Decisions needed

1. `observer` injection into `run_game` (review Q1) -- recommended yes.
  * Yes.

2. `FloorBot` as the standard self-play opponent and Mustard's default
   training source (4.1) -- recommended yes.
  * Yes.

3. Remove the hard zeros: Mustard leaf smoothing (4.2) and White's
   floor prior (4.3), reversing the "leave as-is" call now that the
   cause is measured -- recommended yes, because Phase 5 will turn
   those zeros into accusations.
  * Yes.

4. Green's reward: rank or margin-vs-uniform (4.4) -- recommended rank.
  * Ok.

5. Five dials for the first pass, `confidence_source` as a per-spec
   function rather than a profile field (review Q2, Q3) -- recommended.
  * Ok, that's fine, I would rather have too many on first pass to prune down over time. I can't think of obvious additional dials right now, so we can just do your five, that's fine.

6. Whether to cache self-play games on disk in 5d (4.5), which starts
   `clude_storage/` a phase early.
  * We can start setting up Cloud Storage. Use the Service Account in the clude-game-sa.json.


## 7. Out of scope for Phase 5

Any LLM call, any UI, chat, logbooks (beyond noting what 5d's game
records should contain so Phase 7 can read them), danger/urgency dials
without a measured trigger, and any change to a method's core algorithm
beyond its absence-of-evidence case.

## 8. As implemented (2026-09-12)

Everything in section 5's table exists; `docs/phase-plan.md` lists the
modules and `docs/strategy-glossary.md` the results. Where the build
departed from the plan above, and why:

- **The measurements in section 1 were taken on a broken board.** The
  first FloorBot games plateaued exactly like the RandomBot games did,
  and tracing them showed why: `board.reachable` treated the *starting*
  room as terminal, so a token could only leave a room by secret
  passage. Every table piled into one room and re-suggested there. The
  "random suggesters re-name located cards" explanation in section 1
  was real but secondary; the plateau was mostly tokens that could not
  move. Fixed, along with a boxed-in hallway token having no legal move.
  The seam's golden fingerprints were regenerated once, after the fix.
- **FloorBot movement is not uniform** (4.1 said it would be). With
  uniform movement, even on the fixed board, tokens that get dragged into
  a located room by others' suggestions stay stuck there half the time.
  The bot now prefers a move landing in a room the floor hasn't located,
  else the move closest to one, and once every room is located, a room
  nobody else can refute. Still floor-only, no belief, no personality.
  Its exhausted-category fallback names the proven envelope card rather
  than a random one, for the same reason.
- **A floor fix fell out of the same trace**: or-constraints already
  satisfied by a located card were kept and printed as open, and Peacock
  read their unlocated members as evidence. Dropped now.
- **Cost.** Section 1's ms/call figures were measured on the plateaued
  regime, where the floor had already done Plum's work. On genuinely
  open mid-game FloorBot snapshots Plum costs about 200 ms per call and
  falls back to sampling in a third of them, so Green does too; a
  24-game arena at all table sizes takes about a minute. Sweeps ran at
  48 games per value with FloorBot control seats, not the 200 the
  sample-size arithmetic asks for, so the glossary reports them as
  direction-and-magnitude with their std, not as significance.
- **Mustard's two new features** are `distinct_namers` and
  `named_beside_located` (how often a card was named beside cards the
  viewer's floor has already located, a probe); the tree uses the first
  and not yet the second.
- **Green's `observe` cadence** is once per revealed envelope, as
  planned: every snapshot in the benchmark, once per game in the arena.
- **Storage went further than "cache on disk"**: one `RecordStore`
  interface with local and `gs://` backends, the `clude-game-data` bucket
  created under the service account once David enabled billing on the
  project, and `GameRecord` documented as Phase 7's input. The "replay
  the same deals" part of 4.5 turned out to need no cache at all: with
  every player drawing from its own RNG, a seed alone reproduces the deal
  and the dice, which is what the paired sweeps use.
- **`trace` gained the accusation test** (`[P(correct)=0.47 <0.50]`)
  rather than a chosen action per step, since the belief replay has no
  engine turn to choose in; `play --roster` shows the chosen actions
  of a live character game instead.
- **The `secrecy` dial survived its sweep on a technicality.** Its
  first sweep moved nothing, own cards leaked included. A re-show rate
  (`reshow%`: of the refutations with two or more matching cards, the
  share answered with an already-exposed card) was added to the arena
  as the dial's direct footprint, and that it does move monotonically;
  leaked stays flat because forced single-card refutations expose a
  hand anyway. Kept under David's "too many dials on the first pass,
  prune over time", and named in the glossary as the first to cut.
- **Seeded games were not reproducible across processes at 5-6
  players.** Found when the tuned arena, run twice with the same seed
  and dials, gave two different tables. Plum's search iterated
  `mask.possible_holders[c]` raw, a frozenset mixing seat ints with the
  string `ENVELOPE`, whose place in set order changes with each Python
  process's hash seed; on the sampling fallback (which a 6-player table
  always takes early on) that changed Plum's belief, hence Green's, and
  the game. Fixed with a fixed holder order (`_holder_order`), with a
  subprocess test under two `PYTHONHASHSEED`s. The sweeps each ran in
  one process, so their pairing across values was real; their absolute
  numbers cannot be regenerated bit-for-bit on the fixed code, and the
  glossary says so.
