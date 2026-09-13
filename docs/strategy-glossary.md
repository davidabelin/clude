# Strategy Glossary (Developer)

Links each suspect to their implementation module and documents the method
in plain language, then the personality dials that turn each method's
belief into moves and what the arena measured (Phase 5).

Belief encoding used throughout: each agent returns a distribution over the
21 cards (6 suspects, 6 weapons, 9 rooms), already masked and renormalized
against the shared deduction floor (`clude_constraints`). Reading `belief[c]`
is "probability card `c` is in the envelope" unless noted otherwise.

## Scarlett -- Naive Bayes

- Module: `clude_agents/naive_bayes.py`
- Legacy basis: `legacy/belief_tracker.py`, demoted (see `docs/architecture.md`
  for why: row-normalized marginals can't express joint hand constraints,
  which is wrong for an exact posterior but is Scarlett's actual character).
- Summary: Starts every card at raw score 1, then applies a
  multiplicative, independence-assuming boost or decay per suggestion:
  an unrefuted suggestion boosts its three cards (`x2`, nobody could show
  them); a suggestion refuted by an unknown card decays them (`/1.5`,
  someone holds one, so each is individually less likely to be the
  envelope's). No joint accounting across suggestions -- that's the
  "naive" part, and it's what lets repeated unrefuted evidence compound
  into overconfidence. Measured: worse than the uniform baseline at every
  checkpoint of a FloorBot game (table below), the only method that is.

## Plum -- Exact posterior enumeration

- Module: `clude_agents/exact_enum.py`
- Legacy basis: none; built fresh.
- Summary: A real backtracking CSP search over every still-unresolved
  card, respecting hand-size capacity, the one-envelope-card-per-category
  rule, and `mask.or_constraints` jointly. Counts how many complete,
  consistent deals place each card in the envelope; that count, per
  card, is the exact marginal. Falls back to randomized-constructive
  rejection sampling once the search exceeds a 200,000-node budget --
  noisier, and biased toward whichever construction order happens to
  survive, which is an honest approximation rather than a fix. Verified
  against an independent brute-force enumerator in `tests/test_agents.py`.
  Measured: the best or joint-best belief at every checkpoint, and by far
  the most expensive -- about 450 ms per call on early FloorBot snapshots,
  where he falls back to sampling in nearly half of his calls.

## Peacock -- Dempster-Shafer belief/plausibility

- Module: `clude_agents/dempster_shafer.py`
- Legacy basis: none; built fresh.
- Summary: Per category, starts from a vacuous mass function over all
  still-possible envelope candidates and combines in one piece of
  evidence per `mask.or_constraint` via Dempster's rule -- each
  constraint's "this holder has at least one of these cards" burden is
  apportioned across the categories it touches, in proportion to how
  many of its cards fall in that category (a stated modeling choice, not
  a theorem -- see the module docstring). Reports the pignistic
  transform (BetP) as the probability, and raw Belief/Plausibility
  bounds in `ClueBelief.extra` -- literally the two-tone belief bar from
  the visual design notes (`CLAUDE.md`). Her *character* accuses on the
  Belief bound, not on BetP (see the dials below). Measured: on
  FloorBot snapshots her BetP is slightly worse than uniform at every
  checkpoint, so the apportioning rule is the first thing to revisit if
  she is ever meant to be a stronger reasoner; nothing depends on it yet.

## Mustard -- Decision tree on game logs

- Module: `clude_agents/decision_tree.py`
- Legacy basis: none; built fresh. Trained on `clude_training.self_play`
  snapshots -- since Phase 5, `FloorBot` self-play (games that end by
  deduction) rather than the `RandomBot` regime Phase 4 used.
- Summary: A hand-rolled CART-style regression tree (Gini-guided binary
  splits), trained once and cached at module level, on eight engineered
  per-card features (remaining possible-holder count, or-constraint
  involvement, times named [un]refuted, turn fraction, category size,
  distinct namers, named beside located cards). Leaf values are
  m-estimates -- three phantom rows at the training base rate mixed into
  each leaf -- so a leaf with no positive rows predicts about 0.001, not
  0.0 (Phase 5b; hard zeros were 69% of his Phase 4 log-loss and would
  have read as certainty to the accusation test). Predicts each
  still-unresolved card's envelope probability from whatever pattern the
  training games happened to show: measured, that means the best belief
  of all six at the end of a game and the worst mid-game, where he is
  confidently wrong (log-loss 1.50 against uniform's 1.36 at the halfway
  checkpoint). The tree splits ten times on `turn_fraction`, six on
  `possible_holders_frac`, twice on `distinct_namers`, and not yet on
  `named_beside_located`.

## Green -- Bandit ensemble over the other five

- Module: `clude_agents/bandit.py`
- Legacy basis: ports from `rps_agents/heuristic/multi_armed_bandit.py`
  (Thompson sampling over predictor arms).
- Summary: A Beta(alpha, beta) posterior per arm -- the other five
  agents, queried every turn -- decayed toward its prior each `observe`
  call like `rps`'s bandit. Samples each arm's posterior and plays the
  single highest-sampled arm's belief outright (no blending). `observe`
  takes a `RevealedOutcome` (the solved envelope) and, since Phase 5b,
  scores the arms by *rank* on that snapshot: lowest log-loss 1, highest
  0, linear in between. The Phase 4 reward (mean probability on the
  three true cards) was dominated by the shared floor, so all five arms
  sat within a percent of each other and he picked among them at
  random; with ranks his arms separate by about 0.4 in posterior mean
  over 60 games and he ends up trusting Plum and Mustard (0.71, 0.69)
  over White (0.46), Peacock (0.35) and Scarlett (0.29) -- the same
  order the benchmark ranks them at game end. Only as good as whichever
  arm currently looks best, and as slow as Plum plus everyone else.

## White -- Markov model over suggestion sequences

- Module: `clude_agents/markov.py`
- Legacy basis: `legacy/opponent_model.py`, starting point -- its
  documented ambiguity (does high `estimated_knowledge` mean "knows
  where it is" or "probably doesn't hold it"?) is resolved here: this
  module commits to the latter.
- Summary: Encodes each opponent's suggestion history as a repeat(1)/
  new(0) symbol sequence (did this suggestion re-name a card they'd
  already named?) and fits a two-state first-order Markov chain to it.
  A player currently in a high-P(repeat) regime is read as still
  fishing -- hasn't been shown those cards, doesn't hold them -- which
  raises suspicion toward the envelope for cards they keep re-naming
  without resolution. Since Phase 5b every still-unresolved card starts
  at the floor's prior and the Markov evidence is added on top, so a
  card nobody has named yet is merely unsuspicious rather than
  impossible (those hard zeros were 79% of his Phase 4 log-loss).
  Measured: the change plus the FloorBot regime, where players do
  re-name what they haven't resolved, turned him from the worst belief
  of the six into the second-best mid-game. `ClueBelief.extra` also
  carries per-opponent `repeat_probability` and a `closeness` proxy (how
  much each opponent has been shown), unconsumed until an `urgency` dial
  exists.

## Belief benchmark, FloorBot regime (Phase 5)

`python scripts/clude_cli.py benchmark --games 60 --show-green` (seed
4004, table sizes cycling 3..6, 1080 snapshots, 573 s). Every agent
scores its belief on shared `FloorBot` self-play snapshots against the
eventual truth, at four checkpoints per game (25/50/75/100% of that
game's suggestions), against the `uniform` baseline (the floor's own
belief with zero method-specific evidence). Log-loss per category
(lower is better; a hard 0 on the true card would cost 20.7):

| Agent | 25% | 50% | 75% | 100% | top-1 at 100% | ms/call at 50% |
|---|---|---|---|---|---|---|
| Plum | 1.55 | 1.49 | 0.95 | 0.23 | 0.93 | 375 |
| Green | 1.54 | 1.38 | 0.99 | 0.23 | 0.94 | 380 |
| Mustard | 1.52 | 1.50 | 1.19 | 0.22 | 0.93 | 0.1 |
| White | 1.53 | 1.28 | 0.94 | 0.32 | 0.88 | 0.1 |
| uniform (baseline) | 1.60 | 1.36 | 1.03 | 0.40 | 0.77 | - |
| Scarlett | 1.69 | 1.49 | 1.20 | 0.41 | 0.84 | 0.0 |
| Peacock | 1.68 | 1.45 | 1.10 | 0.41 | 0.78 | 0.2 |

Findings:

- **The hard zeros are gone, and both flaws survived it.** Mustard and
  White were 2-4x worse than ignorance for the whole game in Phase 4;
  now both beat the baseline at the start and the end. White beats it
  throughout. Mustard is still confidently wrong mid-game (1.50 and 1.19
  against 1.36 and 1.03), which is the character.
- **Scarlett is now the one method worse than ignorance everywhere**,
  by a small margin: the independence-assuming boosts compound in the
  wrong direction more often than the right one on FloorBot play, where
  refutations are the norm and unrefuted suggestions are rare until the
  end. That is her flaw, measured rather than asserted.
- **Peacock's BetP trails uniform** by a little at every checkpoint (see
  her section); her caution as a *character* comes from accusing on the
  Belief bound, which is unaffected.
- **Plum is exact when he can afford to be and best when it matters**,
  but half his calls on early snapshots hit the 200k-node budget and
  sample instead. Speed stays a non-issue for a 24-game arena (about a
  minute) and a real issue for a 60-game benchmark (ten minutes) or a
  200-game sweep.
- **Green learns which arm to trust** (his section) and tracks Plum's
  quality at a Plum-plus-everyone price.

### Phase 4 benchmark results (RandomBot regime, historical)

The Phase 4 table (60 `RandomBot` games, seed 4004, game end): Plum 0.45,
Scarlett 0.49, Peacock 0.53, uniform 0.47, Green 0.60, Mustard 0.91,
White 1.73 log-loss. Two things about it are now known to be artifacts.
The board was broken -- a token could not leave a room except by secret
passage (`docs/board.md`) -- so those games were tables piled into one
room re-suggesting the same cards, and the floor plateaued early; and
Mustard's and White's numbers were mostly hard zeros (69% and 79% of
their log-loss came from the 5-7% of categories where they put exactly
0 on the true card, measured 2026-09-11). David's 2026-09-11 call to
leave the zeros as-is was reversed in `docs/phase5-plan.md` once the
cause was measured, because Phase 5's accusation test would have turned
a zero on the true card into a confident wrong accusation. `--bot
random` still runs that regime on the fixed board for comparison.

## Personality dials and presets (Phase 5)

Each character plays through `clude_agents.character.Character`: one
belief per observation, then four decisions shaped by a `Profile` of
five dials (`clude_agents/personality.py`). The accusation test is a
threshold on P(correct), the product of the three category maxima of
the character's confidence source -- probabilities for five of them,
the Dempster-Shafer Belief bound for Peacock. Mustard and White keep the
neutral `accuse_threshold` so their wrong accusations stay attributable
to their beliefs.

| Dial | Decision | Meaning |
|---|---|---|
| `accuse_threshold` | accusation | accuse once P(correct) reaches this |
| `bluff_rate` | suggestion | P(naming one of my own cards instead of an honest pick) |
| `curiosity` | movement | 1 = chase the most probable room, 0 = enter the nearest room |
| `secrecy` | card to show | 1 = re-show what this player has already seen, 0 = indifferent |
| `temperature` | the three sampled decisions | softmax temperature over scores in [0, 1]; 0 = greedy |

### Arena, first pass (untuned presets)

`python scripts/clude_cli.py arena --games 24 --seed 7007` with the
first-pass presets, all six characters, seats rotating, table size
cycling 3..6, 64 s; every game decided by a correct accusation, mean 28
turns:

| Player | games | win% | wrong% | 1st accusation turn | never% | leaked | named |
|---|---|---|---|---|---|---|---|
| Scarlett (threshold 0.5) | 20 | 0 | 5 | 10.0 | 95 | 2.30 | 1.40 |
| Mustard (0.8) | 16 | 19 | 38 | 21.6 | 44 | 2.81 | 1.38 |
| White (0.8) | 20 | 30 | 0 | 31.8 | 70 | 2.65 | 3.50 |
| Green (0.75) | 16 | 13 | 13 | 20.8 | 75 | 2.62 | 1.62 |
| Peacock (0.7 on Belief) | 20 | 40 | 0 | 32.1 | 60 | 2.65 | 1.15 |
| Plum (0.95) | 16 | 31 | 6 | 19.8 | 63 | 2.31 | 0.31 |

(Binomial std on a 20-game rate is about 10 points; this is a first look,
not a ranking.) Two things were wrong with the presets on sight:
Scarlett, meant to accuse early, never reached 0.5 before somebody
proved the envelope, and Mustard's tree eliminated him in a third of his
games -- the latter is the character, the former is a dial. The sweeps
below are how the presets were then set.

### Dial sweeps

`python scripts/clude_cli.py sweep --dial <dial> --values ... --games 48
--seed 7100 --roster Scarlett,floor,Mustard,floor,White,floor,Green,floor,Peacock,floor,Plum,floor`:
all six characters interleaved with `FloorBot` control seats, the dial
set on every character, 48 paired games per value (same deals and dice
at every value), pooled over the characters. `win%` is therefore
"characters against purely logical players". Binomial std on 120 pooled
character-games is about 4 points; the sweeps show direction and rough
magnitude, not 5-point significance (that needs 200 games per setting,
docs/phase5-plan.md 4.5). One caveat on reruns: these tables were made
before the fix to Plum's holder order (docs/phase5-plan.md, section 8),
when a seeded game at 5-6 players depended on the process's string
hash seed. Each sweep ran in one process, so the pairing across values
within a table is real, but rerunning the command on the fixed code
gives slightly different absolute numbers; the tuned-preset tables
below were made after the fix and do reproduce.

**accuse_threshold** (0.2 / 0.4 / 0.6 / 0.8 / 1.0), 557 s:

| threshold | win% | wrong% | 1st accusation | never% | mean turns |
|---|---|---|---|---|---|
| 0.2 | 18.3 | 33.3 | 18.1 | 48 | 22.8 |
| 0.4 | 23.3 | 21.7 | 22.5 | 55 | 25.2 |
| 0.6 | 24.2 | 11.7 | 24.4 | 64 | 24.5 |
| 0.8 | 23.3 | 4.2 | 19.6 | 73 | 24.3 |
| 1.0 | 20.8 | 0.0 | 22.2 | 79 | 27.5 |

Monotone: wrong-accusation rate decreasing, never-accused rate
increasing. Win rate is a hump: a threshold of 0.2 throws a third of
games away on a guess, 1.0 waits for proof and loses races. Kept.

**bluff_rate** (0 / 0.25 / 0.5 / 1.0), 319 s:

| bluff_rate | win% | wrong% | never% | own cards named | mean turns |
|---|---|---|---|---|---|
| 0.0 | 19.2 | 8.3 | 73 | 0.62 | 26.8 |
| 0.25 | 20.0 | 7.5 | 73 | 1.91 | 26.0 |
| 0.5 | 17.5 | 5.0 | 78 | 2.90 | 25.4 |
| 1.0 | 6.7 | 12.5 | 81 | 4.77 | 31.2 |

Monotone: own cards named increasing (the dial's direct footprint; the
0.62 at zero is rooms -- the honest pick never names an own suspect or
weapon, but the room is wherever the character stands), never-accused
rate increasing. Bluffing a quarter of the time is free; always
bluffing means never testing the cards you are unsure of, and the win
rate collapses to 7%. Kept, with presets at or below 0.3.

**curiosity** (0 / 0.5 / 1.0), 266 s:

| curiosity | win% | wrong% | 1st accusation | never% | own cards named | mean turns |
|---|---|---|---|---|---|---|
| 0.0 | 23.3 | 6.7 | 22.8 | 70 | 1.86 | 24.0 |
| 0.5 | 25.8 | 4.2 | 23.5 | 70 | 1.51 | 23.9 |
| 1.0 | 18.3 | 4.2 | 26.5 | 78 | 0.88 | 28.6 |

Monotone: never-accused rate and first-accusation turn increasing,
own cards named decreasing (a character chasing the most probable room
is never standing in one of its own, whose envelope probability is 0),
wrong-accusation rate decreasing. Win rate is again a hump: full
curiosity walks past nearer rooms, makes fewer suggestions, and games
run five turns longer. Kept; the presets spread from 0.3 (Mustard) to
0.8 (Plum) so the flavors differ, and none sits at the losing extreme.

**secrecy** (0 / 0.5 / 1.0), 264 s:

| secrecy | win% | wrong% | never% | leaked | re-show% | mean turns |
|---|---|---|---|---|---|---|
| 0.0 | 29.2 | 6.7 | 64 | 2.64 | 30.4 | 24.1 |
| 0.5 | 20.0 | 8.3 | 72 | 2.90 | 38.1 | 26.6 |
| 1.0 | 25.0 | 6.7 | 68 | 2.68 | 40.8 | 24.4 |

Monotone: re-show rate increasing, and nothing else. `re-show%` is the
dial's direct footprint: of the refutations where the character held
two or more matching cards, the share where it showed one already
exposed (added to the arena for this sweep, because the first run of it
showed nothing moving). Its ceiling is well under 100% because a
re-show needs an already-exposed card among the candidates, and most
such choices come early. The metric the dial was meant to move, own
cards leaked, is flat within noise, and so is everything else: a hand
of three to six cards gets exposed by forced single-card refutations
whatever the character does with its rare choices. The win-rate wobble
(29 / 20 / 25) has no direction and is treated as noise pending a
200-game run. Kept for now under the rule of "too many dials on the
first pass, prune over time", but it is the one on the block: the
engine does what it is told, and it does not matter.

**temperature** (0 / 0.1 / 0.5 / 2.0), 366 s:

| temperature | win% | wrong% | 1st accusation | never% | leaked | named | re-show% | mean turns |
|---|---|---|---|---|---|---|---|---|
| 0.0 | 28.3 | 10.8 | 18.7 | 61 | 2.50 | 1.13 | 44.2 | 19.7 |
| 0.1 | 27.5 | 6.7 | 23.5 | 66 | 2.76 | 1.46 | 45.1 | 25.9 |
| 0.5 | 9.2 | 5.8 | 19.3 | 85 | 2.78 | 0.97 | 30.9 | 29.5 |
| 2.0 | 4.2 | 8.3 | 25.3 | 88 | 3.10 | 0.97 | 33.0 | 34.2 |

Monotone: win rate decreasing, never-accused rate and cards leaked
increasing. The strongest dial by far: between 0.1 and 0.5 the win rate
against the floor drops by two thirds, because a sampled suggestion
stops testing the cards the belief is unsure of and a sampled move
stops going anywhere in particular (games run ten turns longer at 2.0,
and the re-show rate falls as the card-to-show choice goes random too).
Greedy (0.0) is the fastest regime, 20 turns, and has the most wrong
accusations, 11%: the most informative suggestion every turn carries
every belief to its threshold sooner, the confidently wrong ones
included. Kept. The presets all sit at or below 0.2, on the flat part;
0.2 itself (Mustard, Green) lies in the unsampled gap between 0.1 and
0.5 and is left as the "noisy" flavor until a finer sweep says
otherwise.

### Tuned presets

All five dials survived, four on their intended metric and `secrecy` on
its footprint. Two characters moved:

| Character | accuse_threshold | bluff_rate | curiosity | secrecy | temperature | changed from the first pass |
|---|---|---|---|---|---|---|
| Scarlett | 0.15 | 0.2 | 0.7 | 0.4 | 0.15 | threshold 0.5 to 0.15 |
| Plum | 0.9 | 0.05 | 0.8 | 0.7 | 0.05 | threshold 0.95 to 0.9, curiosity 0.9 to 0.8 |
| Peacock | 0.7 (on Belief) | 0.05 | 0.6 | 0.9 | 0.1 | -- |
| Mustard | 0.8 (neutral) | 0.1 | 0.3 | 0.3 | 0.2 | -- |
| Green | 0.75 | 0.2 | 0.5 | 0.5 | 0.2 | -- |
| White | 0.8 (neutral) | 0.3 | 0.4 | 0.8 | 0.1 | -- |

Plum's two changes each step one notch in from the losing end of a
sweep (1.0 on the threshold waits for proof and loses races; 1.0 on
curiosity walks past rooms). Scarlett's needed its own runs: the pooled
sweep moves every character's threshold together, so at 0.2 the others
ended games before she reached hers and she accused in only 4 of 20.
Three 24-game arenas (seed 7007, everyone else at preset) with only her
dial moved:

| Scarlett threshold | win% | wrong% | accused in | 1st accusation turn |
|---|---|---|---|---|
| 0.3 | 0 | 30 | 30% | 28.8 |
| 0.2 | 20 | 40 | 60% | 24.3 |
| 0.15 | 10 | 45 | 55% | 23.8 |

Her Naive Bayes is worse than uniform on the benchmark above, so her
P(correct) climbs slowly, and when it does clear a bar it is over the
wrong triple more often than not: at 0.3 she reached it only in games
that had already run long, and never won. 0.2 and 0.15 are within
noise of each other (two games of wins, one of wrong accusations, half
a turn); 0.15 is the preset as the lower bar, since the flavor asks
for "early" and nothing separates them otherwise. That is the intended
flavor -- overconfident, early, usually wrong, occasionally first --
but note where it comes from: the dial supplies "early", the belief
supplies "wrong". Fixing her calibration would make her a different
character.

### Arena, tuned presets

`python scripts/clude_cli.py arena --games 24 --seed 7007 --store
gs://clude-game-data/arena --run-id arena-tuned-24`: the same 24 deals
as the first pass, tuned presets, 84 s including the upload; every game
decided by a correct accusation, mean 27.5 turns. The run's
`GameRecord`s are in the bucket under `arena-tuned-24`, and the run
reproduces exactly on the fixed code.

| Player | games | win% | wrong% | 1st accusation turn | never% | leaked | named | re-show% |
|---|---|---|---|---|---|---|---|---|
| Scarlett (threshold 0.15) | 20 | 10 | 45 | 23.8 | 45 | 2.05 | 1.25 | 37.5 |
| Mustard (0.8) | 16 | 25 | 25 | 20.1 | 50 | 2.81 | 1.31 | 33.3 |
| White (0.8) | 20 | 30 | 0 | 31.0 | 70 | 2.25 | 3.05 | 23.1 |
| Green (0.75) | 16 | 19 | 13 | 36.0 | 69 | 2.38 | 1.44 | 72.7 |
| Peacock (0.7 on Belief) | 20 | 15 | 0 | 21.7 | 85 | 2.40 | 1.65 | 42.9 |
| Plum (0.9) | 16 | 38 | 0 | 26.7 | 63 | 2.44 | 0.81 | 12.5 |

Against the first pass: Scarlett went from never accusing to accusing
in over half her games, wrong in most and first in two, which is the
flavor; Plum's one-notch threshold step made him the most frequent
winner with no wrong accusation; Mustard's tree still eliminates him in
a quarter of his games, which is the character rather than a dial;
White and Peacock never accuse wrongly and win by patience; Green
trails, as an ensemble that is only as good as the arm it currently
trusts and slower than everyone. The std on 16-20 games is 8-12 points,
so the order among the middle four is noise. What held across every
run of this seed, tuned or not: Scarlett last with the most wrong
accusations, and White, Peacock and Plum at zero.


## Phase 6: LLM-piloted characters

The wrapper (`docs/llm-wrapper.md`) lets a model choose within a leash
of each character's own scores and adds table talk; the design and the
four decisions behind it are in `docs/phase6-plan.md`. Everything is
built and tested on fake backends: a backend that never answers
reproduces every character golden byte for byte, and an adversarial one
with full rope cannot move an event. Two dials joined `Profile`,
`leash` (0.25 for everyone) and `chattiness` (0.5), pending the sweep
below.

**Results: not yet measured.** The machine this was built on has no API
credentials, so the numbers that belong here are still to be produced:

1. the twin comparison, `arena --games 24 --players 4 --roster
   Scarlett,Plum,Peacock,floor --seed 7007` with and without `--llm`
   (same deals and dice), reporting per character the change in `win%`
   and `wrong%` with their binomial std, plus the LLM table's
   `fallb%`, `deviate%`, `talk/g` and `tok/g`;
2. `sweep --dial leash --values 0 0.25 0.5 1 --llm`, the keep-a-dial
   test: `deviation_rate` should rise monotonically with the rope, and
   whatever `wrong%` does against the twin is the cost of decision 2's
   symmetric window;
3. the `leash` and `chattiness` presets those two runs suggest, per
   character, and a paragraph per character on whether the voice in its
   persona file survived contact with real play.

Until then the arena reports the `null` backend's control numbers only,
which by construction equal the Phase 5 tuned table above.
