# Maintainer CLI (`scripts/clude_cli.py`)

One entry point for running the headless pieces through their paces and
getting numbers back, in the shape of `rps/scripts/rps_cli.py`. Every
subcommand is deterministic for a given `--seed`, so any output here can
be reproduced exactly and pasted into a doc, a test, or a bug report.

```
python scripts/clude_cli.py --help
python scripts/clude_cli.py <subcommand> --help
```

Run from the repo root with the project venv active (see
`docs/architecture.md` for the environment). No subcommand writes to
disk unless you pass `--json` or `--store`.

| Subcommand | Question it answers | Phase it exercises |
|---|---|---|
| `agents` | What agents are registered, and what are their preset dials? | 3, 5 |
| `play` | What does one headless game look like, with or without LLM-piloted seats? | 1, 5, 6 |
| `prompt` | What exactly would this seat's LLM be sent, right now, for this decision? | 6 |
| `trace` | What did each character believe after every suggestion, and would it have accused? | 2-3, 5 |
| `floor` | What has the deduction floor proven, and how fast does it close in? | 2 |
| `benchmark` | How good is each method's belief, and what does a call cost? | 4 |
| `train-mustard` | What tree do these hyperparameters give, and does it help? | 3-4 |
| `snapshots` | What does the self-play training/benchmark data look like? | 4-5 |
| `arena` | Who wins, who accuses wrongly, who leaks, over N full games -- and, with `--llm`, what the model's rope cost each character? | 5, 6 |
| `sweep` | Does one dial move a metric monotonically? (`--llm` for the Phase 6 dials; `--logbook` for `memory`.) | 5, 6, 7 |
| `store` | What runs are in a record store, local or in the bucket? | 5 |
| `logbook` | What has a character remembered: its entries, its head, its method memory, and the block it would read at a given `memory` depth? | 7 |

The three one-game commands (`play`, `trace`, `floor`) share
`--players` (3-6, default 4), `--seed` (default 1), `--max-turns`
(default 300) and `--roster` (default `random`), and always play the
*same* game for the same values, so you can `play` a game, then `trace`
it, then `floor` it and be looking at one deal throughout.

`--roster` says who sits at the table: `random` (Phase 1's `RandomBot`s),
`floor` (`FloorBot`s, the standard self-play opponent), or a
comma-separated lineup of suspect names and `floor` fill seats, seated
in that order and padded with `floor` up to `--players`. Seats print as
`P<index> <token>` with the occupant in parentheses when it differs:
`P1 Mustard (Plum)` is Plum's method piloting the Mustard token.

## `agents`

Lists the six registered suspects, their methods, their preset dials
(`accuse_threshold`, `bluff_rate`, `curiosity`, `secrecy`,
`temperature`) and what the accusation threshold is compared against
(`probabilities`, or `DS belief` for Peacock). The names it prints are
the ones `--agents` and `--roster` accept elsewhere.

## `play`

```
python scripts/clude_cli.py play --players 4 --seed 1 --verbose --hands
python scripts/clude_cli.py play --players 4 --seed 1 --roster floor
python scripts/clude_cli.py play --roster Plum,Scarlett,Peacock,floor --verbose
```

Plays one game and prints the outcome. `--verbose` prints the event log
one line per move/suggestion/accusation, with corridor squares as
`(row,col)` on the Classic grid (`docs/board.md`; records from before
2026-09-15 print their ring cells as `RoomA~RoomB[k]`); `--hands` appends the dealt hands (omniscient -- no
agent ever sees these).

```
seed=1 players=4 roster=floor
seats: P0 Scarlett (floor), P1 Mustard (floor), P2 White (floor), P3 Green (floor)

Envelope: Mustard/Rope/Ballroom
Turns played: 7; suggestions: 6; accusations: 1
Winner: P2 White (floor)
```

The same deal with `RandomBot`s runs 184 turns and 53 suggestions and
ends with every player eliminated: random bots suggest whatever,
including cards in their own hand, and accuse at random 3% of the time,
so nobody deduces anything on purpose. `FloorBot`s only name cards the
floor still leaves open, head for rooms it hasn't located, and accuse
exactly when it has proven the envelope, so their games end by deduction
-- occasionally, as above, because an early suggestion happened to name
the envelope and nobody could refute it. A character lineup shows the
personality layer choosing every move.

The event log is omniscient: it always names the card shown. `trace`
and `floor` show the redacted, per-seat view instead.

```
python scripts/clude_cli.py play --roster Plum,Scarlett,floor --llm --llm-backend null --verbose
python scripts/clude_cli.py play --roster Plum,Scarlett,floor --llm --llm-characters Scarlett
python scripts/clude_cli.py play --roster Plum,Scarlett,floor --llm --llm-backend replay:data/exports/llm-1.json
```

`--llm` (Phase 6) pilots the roster's character seats with an LLM
(`clude_llm.LLMCharacter`, docs/phase6-plan.md): each decision offers the
model the character's own leashed menu, and any reply that is not an
allowed option falls back to the character's own choice.
`--llm-backend` picks the model source: `anthropic` (the default; the
real API, 6c), `null` (never answers, so the game is the headless one
event for event -- the control), `record:PATH` (the real API, every
exchange saved) or `replay:PATH` (a saved recording, no spend).
`--llm-model` names the model and `--llm-characters` restricts wrapping
to a subset of the roster. With `--verbose`, remarks print inline as
`turn 7: P1 Mustard (Plum) says: "..."`; a trailer lists each LLM
seat's decisions, calls, fallbacks, deviations (a played option that
scored below the character's best), remarks, tokens and seconds.

```
python scripts/clude_cli.py play --roster Plum,Mustard,Green --players 3 --store data/llm
python scripts/clude_cli.py play --roster Plum,Mustard,Green --players 3 --store data/llm --logbook
python scripts/clude_cli.py play --roster Plum,Mustard,Green --players 3 --llm --llm-characters Plum --store data/llm --logbook
```

`--store URI` (Phase 7) writes the game's record as game 0 of a run
named by `--run-id` (default `play-<seed>-<timestamp>`), with a
one-game run summary so `store` lists it. `--logbook [URI]` gives every
character its logbook from that store (with no URI, the `--store`
location): method memory is loaded before the game and updated after
it, and an LLM-piloted seat reads its logbook back at its `memory`
dial's depth and writes an entry at the end (`docs/logbooks.md`). The
trailer says whose memory was updated and which entries were written.
`--logbook-readonly` reads and writes nothing. `--logbook-characters
Plum` gives only the named characters a logbook; the rest play exactly
as they do without memory.

## `prompt`

```
python scripts/clude_cli.py prompt --seed 1 --players 3 --roster Scarlett,Peacock --viewer 1 --at 2
python scripts/clude_cli.py prompt --seed 1 --roster Plum,Scarlett,floor --viewer 2 --agent Peacock --decision accuse
python scripts/clude_cli.py prompt --seed 1 --roster Plum,Scarlett,floor --decision move --roll 4
```

Prints the two prompts an LLM-piloted seat would be sent for one
decision at one point in a game (Phase 6): the system prompt (the
character's persona file plus `clude_llm/personas/rules.md`, the part
the API caches) and the user prompt (the seat's hand, what the floor has
proven, its method's top cards and accusation test, the suggestion log
as that seat saw it, and the leashed menu). No call is made. `--viewer`
picks the seat, `--at` the number of suggestions revealed (default the
whole game), `--decision` which menu to render, and `--agent` which
character's method and persona to use when the seat is a bot, or to try
another character in that seat. Positions are the finished game's, so
`--decision move` lists the legal moves from there for `--roll`.

This is the review tool for two things: reading what a character is
told before editing its persona file, and checking that nothing in the
user prompt is information the seat could not have.

`--logbook URI` (Phase 7) also prints the memory block the character
would read from its logbook in that store, as the third part (it
travels as a second cached system block); `--memory DEPTH` overrides
the character's `memory` dial for it. With nothing to read back the
command says so.

## `trace`

```
python scripts/clude_cli.py trace --seed 1 --players 3 --roster floor --viewer 0 --every 6
python scripts/clude_cli.py trace --seed 1 --agents Plum,Scarlett --all-cards
```

The post-game belief replay in text form. Plays the game, then for the
chosen `--viewer`'s seat rebuilds their masked `ClueObservation` after
every `--every`-th suggestion (k=0 and the end are always shown) and
prints each selected character's belief on it and its accusation test:

```
--- k=18: turn 25: P0 Scarlett (floor) suggests Mustard/Wrench/Ballroom -- P2 White (floor) showed Wrench
floor: 17/21 cards located
Scarlett  S: Mustard*  |  W: Rope*  |  R: Billiard 0.47 Study 0.47 Ballroom 0.06  [P(correct)=0.47 <0.50]
Peacock   S: Mustard*  |  W: Rope*  |  R: Ballroom 0.33 Billiard 0.33 Study 0.33  [bel/pl of top: S 1.00/1.00 W 1.00/1.00 R 0.00/1.00]  [P(correct)=0.00 <0.70]
Plum      S: Mustard*  |  W: Rope*  |  R: Ballroom 0.60 Billiard 0.20 Study 0.20  [exact: 5 deals, 30 nodes]  [P(correct)=0.60 <0.95]

--- k=19: turn 26: P1 Mustard (floor) suggests Scarlett/Rope/Ballroom -- P0 Scarlett (floor) showed Scarlett
floor: 18/21 cards located; envelope proven: Mustard/Rope/Ballroom
Scarlett  S: Mustard*  |  W: Rope*  |  R: Ballroom*  [P(correct)=1.00 >=0.50]
```

How to read it:

- The suggestion line is the viewer's view: it names the card shown only
  if the viewer was the suggester or the refuter; otherwise "showed a
  card (hidden)".
- `floor:` is the shared deduction floor's state (`clude_constraints`):
  how many of the 21 cards it has located, whether it has proven the
  envelope, and how many or-constraints ("this player holds at least one
  of these") are still open.
- `S/W/R` are the suspect/weapon/room categories. Each shows the
  `--top` (default 3) still-possible cards by that agent's probability;
  `Card*` means the floor has proven it, so every agent reports 1.0.
  `--all-cards` shows every still-possible card instead.
- The first bracketed tail is whatever the method put in
  `ClueBelief.extra`: Plum's `[exact: N deals, M nodes]` or `[sampled:
  ...]` (he hit his node budget and fell back to rejection sampling),
  Green's chosen `[arm: ...]`, Peacock's Dempster-Shafer `[bel/pl ...]`
  bounds for her top card per category (the two-tone bar from the design
  notes).
- The last tail is the Phase 5 accusation test: `P(correct)` is the
  character's confidence in its best triple (product of the three
  category maxima of its confidence source -- probabilities for five of
  them, the DS belief for Peacock, which is why hers reads 0.00 while
  her probabilities don't), against its preset `accuse_threshold`;
  `>=` means it would accuse here.
- The header prints the truth so you can see who is right; no agent
  sees it.

Things worth noticing in a trace: how Plum and Green agree exactly
whenever Green picks Plum's arm; how Scarlett's naive Bayes drifts off
the true room at k=18 above while Plum's exact posterior doesn't; how
Peacock's belief stays at 0.00 until something is *proven*, while her
plausibility stays at 1.00.

Cost: well under a second for a 3-player FloorBot game with three
agents, more for 6 players and all six (Plum's search and Green's five
arms dominate; the trailer line prints the total).

## `floor`

```
python scripts/clude_cli.py floor --seed 1 --players 3 --viewer 0 --at 6
python scripts/clude_cli.py floor --seed 1 --players 4 --roster floor --convergence
```

Two views of the deduction floor alone, no agents involved.

The default prints one viewer's card x holder grid after `--at` k
suggestions (default: the whole game):

```
card             P0   P1   P2  Env
Scarlett          #    .    .    .
Mustard           .    x    x    x
...
# = located holder, x = still possible, . = ruled out

open or-constraints (holder has at least one of):
  P2 White: Green, Rope

envelope proven: not yet (9/21 cards located)
truth: envelope = Mustard/Rope/Ballroom
```

`--convergence` prints every viewer's located-card count after each
suggestion, skipping rows where nothing changed, and then the first k
at which each viewer had the envelope proven:

```
   k    P0    P1    P2    P3
   0     5     5     4     4
   1     6     5     4     4
  ...
```

This is the view that found both Phase 5b rules bugs: a table of
`FloorBot`s plateaued at 15/21 for a hundred turns, and reading their
positions showed every token bouncing between Lounge and Conservatory
through the secret passage -- the only way a token could leave a room
at all until `board.reachable` was fixed.

## `benchmark`

```
python scripts/clude_cli.py benchmark
python scripts/clude_cli.py benchmark --games 12 --checkpoints 0.5 1.0 --show-green
python scripts/clude_cli.py benchmark --agents Plum,Scarlett --players 6 --bot random --json data/exports/bench.json
```

Phase 4's belief-quality benchmark (`clude_training.benchmark`): every
selected agent scores its belief on shared self-play snapshots against
the eventual truth. `--bot floor` (the default since Phase 5) snapshots
`FloorBot` games; `--bot random` the Phase 4 `RandomBot` regime. Metrics
per (agent, checkpoint):

- `brier` -- mean squared error over all 21 cards; lower is better.
- `log_loss` -- mean `-log P(true card)` per category; lower is better,
  and it punishes confident wrong answers hard (a hard 0 on the true
  card costs about 20.7).
- `top1_acc` -- fraction of categories whose highest-probability card
  is the true one.
- `ms/call` -- mean wall-clock per `select_action` call. The `uniform`
  baseline (the floor's own belief, no method) makes no call.

```
agent        checkpoint     brier  log_loss  top1_acc  ms/call
--------------------------------------------------------------
Green              0.50    0.0837    1.1501     0.568    226.1
Green              1.00    0.0085    0.1145     0.975     22.8
...
uniform            0.50    0.0971    1.3184     0.309        -
uniform            1.00    0.0252    0.3116     0.852        -

12 floor-bot games, seed 4004, table sizes [3, 4, 5, 6], 108 snapshots, 26.5s
Plum fell back to sampling in 33/108 calls
```

Flags: `--agents` benchmarks a subset (the `uniform` row is always
there); `--players N` fixes the table size instead of cycling 3..6 so
you can see how a method scales; `--show-green` prints Green's per-arm
Beta posteriors after the run (mean = how much he trusts that arm;
evidence = how many observations it has absorbed); `--json PATH` writes
everything `BenchmarkResult.to_dict()` knows.

FloorBot games are short and their mid-game snapshots are genuinely
open, which is where Plum's search is expensive: expect 200 ms per call
at the 0.5 checkpoint and a third of his calls falling back to sampling.
See `docs/strategy-glossary.md` for the reference results and what they
mean.

## `train-mustard`

```
python scripts/clude_cli.py train-mustard
python scripts/clude_cli.py train-mustard --games 50 --max-depth 8 --min-samples-leaf 10 --render
python scripts/clude_cli.py train-mustard --eval-games 30 --eval-seed 9000 --smoothing-m 0
```

Trains Mustard's tree (`clude_agents.decision_tree`) with explicit
hyperparameters, describes it, and scores it on held-out self-play:

```
training set: 2347 rows from 25 floor-bot games (seeds 2026..2050) at checkpoints [0.5, 1.0]
  one row per (viewer, checkpoint, card the floor hadn't located); 398 positive = 0.170
trained in 0.6s (rows and tree are cached per settings within a process)
tree: 45 nodes, 23 leaves, depth 6 (--max-depth 6, --min-samples-leaf 20, --smoothing-m 3.0)
splits per feature:
  possible_holders_frac          6
  ...
  turn_fraction                 10
  distinct_namers                2
  named_beside_located           0
leaf predictions: min 0.001, median 0.271, max 0.973

held-out evaluation: 8 floor-bot games from seed 4004
agent        checkpoint     brier  log_loss  top1_acc  ms/call
Mustard            0.50    0.0895    1.4965     0.546      0.1
Mustard            1.00    0.0075    0.1136     0.991      0.1
uniform            0.50    0.0977    1.3378     0.361        -
uniform            1.00    0.0292    0.3743     0.861        -
```

How to read it: the training set is one row per still-unlocated card
per snapshot, labelled 1 if that card was the envelope's; `label_rate`
is the base rate the m-estimate leaves are smoothed toward. `splits per
feature` says which of the eight engineered features (`FEATURE_NAMES`)
the tree actually uses. `leaf predictions: min 0.001` is the smoothing
at work -- with `--smoothing-m 0` the minimum is exactly 0.000 again.
`--render` prints the whole tree, one node per line, `feature <=
threshold (n=rows)` with the true branch first. `--bot` picks the
regime for both training and evaluation games.

The held-out block is `benchmark` restricted to this tree plus the
uniform baseline, so "does this setting help" is one command. It warns
if the evaluation seeds overlap the training seeds. Note that the
default `DecisionTreeAgent` (used by the registry and by Green's arm)
is trained with the defaults printed by `--help`; this command never
changes that, it only trains a separate instance.

`--logbook URI` (Phase 7) also trains on Mustard's method memory in
that store (`logbook rebuild --identity Mustard` builds it from every
stored game), and the training-set line says how many memory rows from
how many games joined the base. Run it with and without the flag to
see what memory changes.

## `snapshots`

```
python scripts/clude_cli.py snapshots --games 24
python scripts/clude_cli.py snapshots --games 24 --bot random
python scripts/clude_cli.py snapshots --games 20 --players 6 --checkpoints 0.25 0.5 0.75 1.0
```

Describes the self-play snapshot distribution `generate_snapshots`
produces -- Mustard's training data and the benchmark's test data:

```
24 floor-bot games, seed 2026, checkpoints [0.25, 0.5, 0.75, 1.0], table sizes [3, 4, 5, 6]: 108 snapshots in 2.6s

games per table size, and suggestions per game at the last checkpoint:
  3 players: 6 games, suggestions min/mean/max 15/18.5/22
  ...
checkpoint players  snaps  mean_k unresolved label_rate  solved
      1.00       3     18    18.5        4.3      0.182    0.39
      1.00       4     24    16.3        7.4      0.157    0.38
```

- `mean_k` -- suggestions revealed at that checkpoint.
- `unresolved` -- cards the floor hasn't located, per snapshot; Mustard
  gets one training row per such card.
- `label_rate` -- fraction of those rows that are positive.
- `solved` -- fraction of snapshots whose viewer has the envelope fully
  proven. About a third at the end of a FloorBot game (the winner, plus
  anyone else the last suggestions happened to settle it for); `--bot
  random` shows the Phase 4 regime for comparison.

## `arena`

```
python scripts/clude_cli.py arena
python scripts/clude_cli.py arena --games 48 --players 4 --roster Scarlett,Plum,Peacock,floor
python scripts/clude_cli.py arena --set Scarlett.accuse_threshold=0.3 --set Plum.temperature=0.5
python scripts/clude_cli.py arena --store data --run-id baseline --json data/exports/baseline.json
python scripts/clude_cli.py arena --store gs://clude-game-data/arena
```

Phase 5's arena (`clude_training.arena`): N whole games among characters
and/or bots, each character on its own suspect's token and every fill
on the lowest free one, seats in board order (so Mustard always moves
before Plum; since 2026-09-14, before which seats rotated), a roster
larger than the table rotating who sits out, table size cycling 3..6
unless `--players` fixes it, missing seats filled with `FloorBot`s. One row per roster label:

```
player     games   win%   +-  wrong%   +-  1st_acc  never%  leaked  named  reshow%  ms/call
-------------------------------------------------------------------------------------------
Scarlett      20   10.0  6.7    45.0 11.1     23.8    45.0    2.05   1.25     37.5      0.0
Mustard       16   25.0 10.8    25.0 10.8     20.1    50.0    2.81   1.31     33.3      3.3
White         20   30.0 10.2     0.0  0.0     31.0    70.0    2.25   3.05     23.1      0.1
Green         16   18.8  9.8    12.5  8.3     36.0    68.8    2.38   1.44     72.7    230.5
Peacock       20   15.0  8.0     0.0  0.0     21.7    85.0    2.40   1.65     42.9      0.1
Plum          16   37.5 12.1     0.0  0.0     26.7    62.5    2.44   0.81     12.5    229.8

24 games, seed 7007, table sizes [3, 4, 5, 6], 84.1s; mean 27.5 turns; 100% decided by a correct accusation
records: run arena-tuned-24 in gs://clude-game-data/arena
```

- `win%` and `wrong%` are per game (games won, games with a wrong
  accusation and elimination), each with its binomial standard
  deviation `+-` so a difference smaller than a couple of those is noise;
  200 games per setting is what a 5-point claim needs at 6 seats.
- `1st_acc` is the mean turn of the player's first accusation over the
  games it made one; `never%` the games it never accused in (somebody
  else won first).
- `leaked` is the number of distinct own cards shown to opponents over
  the game; `named` the number of the player's suggestions that named a
  card in its own hand (bluffs).
- `reshow%` is, over the refutations where the player held two or more
  matching cards and so had a choice, the share where it showed a card
  it had already exposed to somebody: the `secrecy` dial's footprint.
  `-` when it never had such a choice.
- `ms/call` is per belief call, as in `benchmark`; `-` for bots.

`--set LABEL.DIAL=VALUE` overrides one preset dial for one character
(repeatable). `--store PATH|gs://bucket/prefix` writes every game's
`GameRecord` and the run summary (see `store`); `--run-id` names the
run (default `arena-<seed>-<games>`). The table above is the tuned
baseline, whose records are in the bucket as `arena-tuned-24`; the
untuned first pass, the sweeps, and what changed are in
`docs/strategy-glossary.md`.

`--llm` (Phase 6) pilots the roster's characters with an LLM, with the
same `--llm-backend`, `--llm-model` and `--llm-characters` flags as
`play`; the default run id becomes `llm-<seed>-<games>`, the seats are
recorded as `kind="llm"` with the model and each game's decision audit,
and a second table follows the first:

```
LLM seats:
player     games  decis  asked  fallb%  deviate%  talk/g    tok/g  llm ms
-------------------------------------------------------------------------
Scarlett       2     38     11    100.0         -    0.00        0       0
```

- `decis` is every decision the seat made; `asked` those that were the
  model's to make (a menu with one allowed option is decided by the
  character, with no call).
- `fallb%` is, of the asked decisions, the share that fell back to the
  character (backend error, refusal, malformed reply, a letter not on
  the menu or not allowed, budget). On the `null` backend it is 100.
- `deviate%` is, of the choices the model actually played, the share
  that scored below the character's own best option (for the
  accusation, differed from its threshold answer); `-` when nothing
  was played.
- `talk/g` is remarks per game, `tok/g` input plus output tokens per
  game, `llm ms` wall-clock per model call. A line after the footer
  estimates the run's cost at list prices.

The comparison that matters is paired: the same command with and
without `--llm` plays the same deals and dice, so the difference in
`win%` and `wrong%` is what the model's rope did to each character.
`--llm-backend null` reproduces the plain run exactly and is the
control. See `docs/llm-wrapper.md`.

`--logbook [URI]` and `--logbook-readonly` (Phase 7) work as for
`play`: every character's memory is loaded before each game and, unless
read-only, updated after it, with LLM seats debriefing; the LLM table
gains an `entries` column and the footer names the logbook store. With
memory on, a run is a learning curve rather than independent games, so
compare runs on one seed with the logbooks in the same state,
read-only. `--json` keeps the per-game lines for that.
`--logbook-characters Plum` restricts the logbook to the named
characters, so one character's memory can be measured against a
baseline with the rest of the table unchanged (the Phase 7d run).

## `sweep`

```
python scripts/clude_cli.py sweep --dial accuse_threshold --values 0.2 0.4 0.6 0.8 1.0
python scripts/clude_cli.py sweep --dial secrecy --values 0 0.5 1 --characters Plum --games 48
python scripts/clude_cli.py sweep --dial temperature --values 0 0.1 0.5 2 --roster Scarlett,floor,Plum,floor
```

The arena once per value of one dial, with the dial set on every swept
character (`--characters`, default all in the roster) and the others at
preset, on the *same* seeds each time -- so the same deals and dice --
and the swept characters' metrics pooled per value:

```
accuse_threshold   games   win%   +-  wrong%   +-  1st_acc  never%  leaked  named  turns
0.200 ...
1.000 ...

monotone: wrong_accusation_rate decreasing, mean_first_accusation_turn increasing
```

The `monotone:` line is the keep-a-dial rule from docs/phase5-plan.md:
a dial that moves no metric monotonically across its sweep gets cut. A
roster that interleaves characters with `floor` seats (the glossary's
sweeps use `Scarlett,floor,Mustard,floor,...`) makes the pooled `win%`
mean "characters versus purely logical players", with the FloorBot seats
as an untouched control group in each run's own table (`--json` keeps
every run).

`--llm` (with the same flags as `arena`) sweeps with the characters
LLM-piloted; `sweep --dial leash --llm` is the keep-a-dial test for the
leash, and the table gains `deviate%` and `talk/g` columns.
`--logbook [URI]` (Phase 7) reads every character's logbook from that
store at every value and writes nothing, so the sweep stays paired;
`sweep --dial memory --llm --logbook data/llm` is how the `memory` dial
is swept on one logbook state; `--logbook-characters` restricts it as
for `arena`.

## `store`

```
python scripts/clude_cli.py store --uri data
python scripts/clude_cli.py store --uri data --run baseline
python scripts/clude_cli.py store --uri gs://clude-game-data/arena
```

Lists the runs in a record store and how many game records each has, or
prints one run's stored per-player summary. Local stores are directories
(`runs/<run_id>.json`, `games/<run_id>/<index>.json`, and since Phase 7
`logbooks/<identity>/...`); `gs://` stores use the same keys as objects
in the bucket, authenticated with the service-account key described in
`docs/architecture.md` ("Cloud Storage"). Records are omniscient (every
hand, every card shown) and are what the logbooks' method memory and
debriefs read.

### `store copy`

```
python scripts/clude_cli.py store copy --uri data/llm --to gs://clude-game-data/llm --dry-run
python scripts/clude_cli.py store copy --uri data/llm --to gs://clude-game-data/llm
```

Mirrors one store into another (`clude_storage.mirror`); it is how the
Cloud Run app's store is filled (`docs/web.md`, "Deploying"). It takes
every run whose records are all at least `--min-version` (default 3, the
grid era) with its summary, records and cached belief traces, plus
everything under `logbooks/`. It leaves out ring-era runs, `users/`
(accounts are made in each store with `users add --uri`), `watch/`,
`logbooks-ring` and loose files at the root. It prints what it chose and
which runs it left behind. `--dry-run` copies nothing, and `--workers`
(default 10, the storage client's connection pool) sets how many
writes run at once. It overwrites, so running
it again is safe. On `data/llm` it picks 38 runs, 1,322 records, 7
traces and 4 logbook documents, and leaves the 13 ring-era runs behind.

## `logbook`

```
python scripts/clude_cli.py logbook list --uri data/llm
python scripts/clude_cli.py logbook show --uri data/llm --identity Plum
python scripts/clude_cli.py logbook show --uri data/llm --identity Plum --entry 3
python scripts/clude_cli.py logbook show --uri data/llm --identity Plum --memory 0.75
python scripts/clude_cli.py logbook rebuild --uri data/llm --identity Mustard
python scripts/clude_cli.py logbook reset --uri data/llm --identity Plum --keep-entries
```

Phase 7's memory, per identity (`docs/logbooks.md`). `list` prints
every logbook in a store with its tally, dossier and flag counts and a
line on its method memory. `show` prints the head (tally, standing
instructions, every dossier) and an index of the entries; `--entry N`
one entry as text, with the standing instructions and dossiers it
wrote (`--raw` for its JSON); `--memory DEPTH` exactly the
block a character with that `memory` dial would read before a game.
`rebuild` recomputes the head from the entries and the method memory
from every game record in the store (`--from URI` for another store)
at or above `--min-version` (default 3: the Classic grid; ring-era
records, versions 1 and 2, are skipped and counted in the output):
the bootstrap for Mustard and White from the games already in
`data/llm`, and the recovery path; Green's posteriors are accumulated
live and cannot be rebuilt. `reset` is the fairness control: it forgets
the head and method memory, and the entries too unless
`--keep-entries`.

## `users`

The web app's accounts (Phase 8.1; `docs/web.md`, `docs/phase8.1-plan.md`
3.4). There is no sign-up page, so this is the only way an account comes
into being.

```
users add NAME [PASSWORD]      create an account; without a password it gets "password"
users list                     every account and when it was made
users passwd NAME [PASSWORD]   change a password; asks for one if left off
users remove NAME              delete an account
```

Each takes `--uri STORE`, defaulting to `data/llm` -- the store the web
app reads, not the CLI's usual `data`, so an account lands where the app
will look for it.

Passwords are printed, not hidden, and any non-empty one is accepted: a
family game where friction costs more than secrecy buys (CLAUDE.md,
"Settled decisions"). Only a Werkzeug hash reaches the store, and `list`
never prints it. A player is offered a change once in the app, after
their first login; after that `users passwd` is the only way, which is
the point -- they ask David.

A name is matched case-insensitively but kept as typed, because it is
the player's identity and Phase 8.2 writes it into `SeatRecord.label`.

Removing an account deletes only the account: its records and its logbook
stay where they are.

## Adding a subcommand

Each subcommand is one `cmd_<name>(args) -> int` function plus a
`sub.add_parser(...)` block in `build_parser()`, with `set_defaults(fn=...)`
to dispatch. Put reusable logic in a package (`clude_training.trace` and
`clude_training.arena` are the pattern), keep the script to argument
parsing and printing, and add a smoke test to `tests/test_cli.py` that
runs it on a tiny configuration.
