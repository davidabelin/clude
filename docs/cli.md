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
disk unless you pass `--json`.

| Subcommand | Question it answers | Phase it exercises |
|---|---|---|
| `agents` | What agents are registered? | 3 |
| `play` | What does one headless game look like? | 1 |
| `trace` | What did each agent believe after every suggestion, from one seat? | 2-3 |
| `floor` | What has the deduction floor proven, and how fast does it close in? | 2 |
| `benchmark` | How good is each method's belief, and what does a call cost? | 4 |
| `train-mustard` | What tree do these hyperparameters give, and does it help? | 3-4 |
| `snapshots` | What does the self-play training/benchmark data look like? | 4 |

The three one-game commands (`play`, `trace`, `floor`) share
`--players` (3-6, default 4), `--seed` (default 1) and `--max-turns`
(default 300) and always play the *same* game for the same values, so
you can `play` a game, then `trace` it, then `floor` it and be looking at
one deal throughout.

## `agents`

Lists the six registered suspects and their methods, straight from
`clude_agents.AGENT_SPECS`. The names it prints are the ones `--agents`
accepts elsewhere.

## `play`

```
python scripts/clude_cli.py play --players 4 --seed 1 --verbose --hands
```

Plays one game between `RandomBot`s (Phase 1's uniform-random bots) and
prints the outcome. `--verbose` prints the event log one line per
move/suggestion/accusation, with players labelled `P<index> <suspect>`
and hallway cells as `RoomA~RoomB[k]`; `--hands` appends the dealt hands
(omniscient -- no agent ever sees these).

```
turn 5: P0 Scarlett -> Lounge
turn 5: P0 Scarlett suggests Green/Rope/Lounge -- P1 Mustard showed Lounge
...
Envelope: Mustard/Rope/Ballroom
Turns played: 210; suggestions: 183; accusations: 4
No winner -- every player accused incorrectly.
```

The event log is omniscient too: it always names the card shown.
`trace` and `floor` show the redacted, per-seat view instead.

What to expect from `RandomBot`s: they suggest whatever, including cards
in their own hand, and accuse at random 3% of the time, so games are
long (100+ suggestions), nobody deduces anything on purpose, and most
end with every player eliminated. That is by design for Phase 1 -- and
exactly the distribution `snapshots` describes.

## `trace`

```
python scripts/clude_cli.py trace --seed 1 --players 3 --viewer 0 --every 4
python scripts/clude_cli.py trace --seed 1 --agents Plum,Scarlett --all-cards
```

The post-game belief replay in text form. Plays the game, then for the
chosen `--viewer`'s seat rebuilds their masked `ClueObservation` after
every `--every`-th suggestion (k=0 and the end are always shown) and
prints each selected agent's belief on it:

```
--- k=8: turn 12: P2 White suggests Plum/Rope/Study -- P0 Scarlett showed Plum
floor: 9/21 cards located; 2 open or-constraint(s)
Green     S: Mustard 0.43 Green 0.33 Peacock 0.23  |  W: Knife 0.44 ...  [arm: Plum]
Mustard   S: Mustard 0.33 Green 0.33 Peacock 0.33  |  W: Knife 0.25 ...
Peacock   S: Mustard 0.58 Green 0.21 Peacock 0.21  |  W: ...  [bel/pl of top: S 0.25/1.00 W 0.00/1.00 R 0.00/1.00]
Plum      S: Mustard 0.43 Green 0.33 Peacock 0.23  |  W: Knife 0.44 ...  [exact: 927 deals, 12003 nodes]
Scarlett  S: Mustard 0.43 Green 0.29 Peacock 0.29  |  W: ...
White     S: Green 0.50 Peacock 0.50 Mustard 0.00  |  W: ...
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
- The bracketed tail is whatever the method put in `ClueBelief.extra`:
  Plum's `[exact: N deals, M nodes]` or `[sampled: ...]` (he hit his
  node budget and fell back to rejection sampling), Green's chosen
  `[arm: ...]`, Peacock's Dempster-Shafer `[bel/pl ...]` bounds for her
  top card per category (the two-tone bar from the design notes).
- The header prints the truth so you can see who is right; no agent
  sees it.

Things worth noticing in a trace: how Plum and Green agree exactly
whenever Green picks Plum's arm; how White zeroes a card nobody has
named yet even when it is the answer; how Peacock's belief stays at 0.00
until something is *proven*, while her plausibility stays at 1.00.

Cost: roughly 1-2 s for a 3-player game with all six agents, more for
6 players (Plum's search and Green's five arms dominate; the trailer
line prints the total).

## `floor`

```
python scripts/clude_cli.py floor --seed 1 --players 3 --viewer 0 --at 6
python scripts/clude_cli.py floor --seed 1 --players 4 --convergence
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
  40    15    15    15    17
 183    15    15    15    17

first k with the envelope proven: P0=never, P1=never, P2=never, P3=never
```

That long final plateau is normal for `RandomBot` games: once the random
suggesters are re-naming located cards and their own hands, later
suggestions carry no new information. It is the clearest single picture
of why Phase 5 needs smarter self-play before anything trains on it.

## `benchmark`

```
python scripts/clude_cli.py benchmark
python scripts/clude_cli.py benchmark --games 12 --checkpoints 0.5 1.0 --show-green
python scripts/clude_cli.py benchmark --agents Plum,Scarlett --players 6 --json data/exports/bench.json
```

Phase 4's belief-quality benchmark (`clude_training.benchmark`): every
selected agent scores its belief on shared `RandomBot` self-play
snapshots against the eventual truth. Metrics per (agent, checkpoint):

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
Green              1.00    0.0456    0.9181     0.698     12.1
Mustard            1.00    0.0444    0.9254     0.673      0.2
Plum               1.00    0.0428    0.5738     0.679     11.6
...
uniform            1.00    0.0430    0.5748     0.673        -

12 games, seed 4004, table sizes [3, 4, 5, 6], 108 snapshots, 4.7s
Plum fell back to sampling in 4/108 calls
```

Flags: `--agents` benchmarks a subset (the `uniform` row is always
there); `--players N` fixes the table size instead of cycling 3..6 so
you can see how a method scales; `--show-green` prints Green's per-arm
Beta posteriors after the run (mean = how much he trusts that arm;
evidence = how many observations it has absorbed); `--json PATH` writes
everything `BenchmarkResult.to_dict()` knows.

The 60-game default takes about 50 s; nearly all of it is Plum and Green
(who calls Plum as an arm). See `docs/strategy-glossary.md` for the
reference results and what they mean.

## `train-mustard`

```
python scripts/clude_cli.py train-mustard
python scripts/clude_cli.py train-mustard --games 50 --max-depth 8 --min-samples-leaf 10 --render
python scripts/clude_cli.py train-mustard --eval-games 30 --eval-seed 9000
```

Trains Mustard's tree (`clude_agents.decision_tree`) with explicit
hyperparameters, describes it, and scores it on held-out self-play:

```
training set: 1443 rows from 25 RandomBot games (seeds 2026..2050) at checkpoints [0.5, 1.0]
  one row per (viewer, checkpoint, card the floor hadn't located); 275 positive = 0.191
trained in 0.2s
tree: 39 nodes, 20 leaves, depth 6 (--max-depth 6, --min-samples-leaf 20)
splits per feature:
  possible_holders_frac          5
  ...
leaf predictions: min 0.000, median 0.230, max 0.783

held-out evaluation: 8 games from seed 4004
agent        checkpoint     brier  log_loss  top1_acc  ms/call
Mustard            0.50    0.0684    2.3189     0.583      0.1
uniform            0.50    0.0559    0.7428     0.611        -
```

How to read it: the training set is one row per still-unlocated card
per snapshot, labelled 1 if that card was the envelope's; `label_rate`
is the base rate a smoothed tree would fall back to. `splits per
feature` says which of the six engineered features (`FEATURE_NAMES`)
the tree actually uses. `leaf predictions: min 0.000` means at least one
leaf predicts a hard zero -- see the calibration discussion in
`docs/strategy-glossary.md`. `--render` prints the whole tree, one node
per line, `feature <= threshold (n=rows)` with the true branch first.

The held-out block is `benchmark` restricted to this tree plus the
uniform baseline, so "does this setting help" is one command. It warns
if the evaluation seeds overlap the training seeds. Note that the
default `DecisionTreeAgent` (used by the registry and by Green's arm)
is trained with the defaults printed by `--help`; this command never
changes that, it only trains a separate instance.

## `snapshots`

```
python scripts/clude_cli.py snapshots --games 40
python scripts/clude_cli.py snapshots --games 20 --players 6 --checkpoints 0.25 0.5 0.75 1.0
```

Describes the self-play snapshot distribution `generate_snapshots`
produces -- Mustard's training data and the benchmark's test data:

```
games per table size, and suggestions per game at the last checkpoint:
  3 players: 6 games, suggestions min/mean/max 48/78.8/118
  ...
checkpoint players  snaps  mean_k unresolved label_rate  solved
      0.50       3     18    39.3        4.8      0.149    0.44
      0.50       6     36    58.0        7.0      0.207    0.00
```

- `mean_k` -- suggestions revealed at that checkpoint.
- `unresolved` -- cards the floor hasn't located, per snapshot; Mustard
  gets one training row per such card.
- `label_rate` -- fraction of those rows that are positive.
- `solved` -- fraction of snapshots whose viewer has the envelope fully
  proven. `0.00` at 6 players means no 6-player `RandomBot` game ever
  reaches a deduction, at any checkpoint.

## Adding a subcommand

Each subcommand is one `cmd_<name>(args) -> int` function plus a
`sub.add_parser(...)` block in `build_parser()`, with `set_defaults(fn=...)`
to dispatch. Put reusable logic in a package (`clude_training.trace` is
the pattern), keep the script to argument parsing and printing, and add
a smoke test to `tests/test_cli.py` that runs it on a tiny
configuration.
