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
four decisions behind it are in `docs/phase6-plan.md`. On fake backends,
a backend that never answers reproduces every character golden byte for
byte, and an adversarial one with full rope cannot move an event. Two
dials joined `Profile`: `leash` (0.25 for everyone) and `chattiness`
(0.5). The live measurements below, on Opus 5, left both where they
were.

### Twin comparison (2026-09-13)

`arena --seed 7007 --games 24 --players 4`, run twice on the same deals
and dice, once headless and once with `--llm`. The roster is the default
six rather than the `Scarlett,Plum,Peacock,floor` the plan first
sketched, so that every character is measured; each plays 16 of the 24
games. Every game in both runs ended in a correct accusation.

| | win% base | win% LLM | wrong% base | wrong% LLM | 1st_acc base | 1st_acc LLM |
|---|---|---|---|---|---|---|
| Scarlett | 12.5 | 12.5 | 37.5 | 31.2 | 23.4 | 19.3 |
| Mustard | 12.5 | **37.5** | 37.5 | **6.2** | 22.2 | 18.1 |
| White | 12.5 | 25.0 | 0.0 | 0.0 | 29.5 | 22.5 |
| Green | 25.0 | 31.2 | 6.2 | 6.2 | 30.0 | 17.3 |
| Peacock | 12.5 | 12.5 | 0.0 | 0.0 | 24.0 | 18.5 |
| Plum | **75.0** | **31.2** | 0.0 | 0.0 | 27.8 | 26.2 |

Binomial std is 6-12pp on 16 games, so read only the large moves. Plum's
-43.8 is about 3 sigma and Mustard's wrong% -31.2 about 2.3 sigma; his
win% +25.0 is 1.7 sigma and suggestive; White's and Green's gains sit
inside the noise.

| | decis | asked | fallb% | deviate% | talk/g | tok/g |
|---|---|---|---|---|---|---|
| Scarlett | 254 | 121 | 0.0 | 0.8 | 3.50 | 9760 |
| Mustard | 302 | 145 | 0.0 | 0.7 | 4.00 | 11691 |
| White | 302 | 143 | 0.0 | 5.6 | 3.88 | 11791 |
| Green | 326 | 131 | 0.0 | 0.8 | 3.50 | 11865 |
| Peacock | 328 | 142 | 0.0 | 2.1 | 3.75 | 12755 |
| Plum | 289 | 125 | 0.0 | 3.2 | 3.44 | 10752 |

24 games in 2054s, $6.98 at list prices. **No seat fell back once**, in
807 calls across 1801 decisions, so every number above is the model
choosing and not the API failing.

**Plum's collapse is the finding, and it is not about Plum's seat.** He
deviated from his own method on 3.2% of played choices; that cannot cost
44 points. What changed is the table. Mean game length fell from 26.8
turns to 20.3, and every opponent's first accusation came earlier --
Green 30.0 to 17.3, White 29.5 to 22.5, Mustard 22.2 to 18.1 -- while
Plum's own barely moved, 27.8 to 26.2. He is the slowest accuser in the
game, and exact enumeration's edge was always that the others flailed
long enough for him to finish counting. An LLM-piloted table stops
flailing and ends the game before he gets there. The method did not get
worse; the field got faster.

Mustard looked like the mirror image: wrong accusations down from
37.5% of games to 6.2%, win rate tripled. The first reading was that a
decision tree that pattern-matches into confident errors is exactly the
character an extra judgment layer can rescue. **The per-character ladder
below does not bear that out.** With only Mustard on the model, his
wrong% at the preset leash is 41.7% against 25% headless, and his win
rate does not move outside noise at any leash. Whatever improved him in
the twin run came from the table -- five other LLM-piloted seats ending
games sooner and cleaner -- not from the model improving his own
choices. Scarlett's smaller change (37.5 to 31.2) should be read the
same way.

One unplanned effect: LLM seats bluff markedly less. Suggestions naming
one of the seat's own cards fell across the board -- White 3.69 to 0.25,
Mustard 2.44 to 0.31, Scarlett 1.50 to 0.44 -- while cards actually
leaked barely moved. The model treats naming its own card as a wasted
question rather than a feint. Given that talking about your own hand is
a settled house decision and the characters are meant to learn what
over-sharing costs, this is a dial to revisit rather than a win: the
personas currently give them no reason to pay for a bluff.

### Leash sweep (2026-09-13)

`sweep --dial leash --values 0 0.25 0.5 1 --llm --games 8 --players 3
--seed 7007`: all six characters swept together, 8 paired games per
value (24 seat-games), 3538s, $14.99. The run cost twice its estimate
because the leash-0 games ran 50 turns.

| leash | wrong% | +- | 1st_acc | never% | named | turns | deviate% | talk/g |
|---|---|---|---|---|---|---|---|---|
| 0 | 25.0 | 8.8 | 41.1 | 41.7 | 6.42 | 50.4 | 0.0 | 4.92 |
| 0.25 | 16.7 | 7.6 | 24.2 | 50.0 | 1.46 | 26.9 | 1.7 | 6.21 |
| 0.5 | 0.0 | 0.0 | 19.1 | 66.7 | 0.46 | 19.1 | 11.1 | 6.08 |
| 1.0 | 8.3 | 5.6 | 20.1 | 58.3 | 0.96 | 21.4 | 4.1 | 8.88 |

**win% is omitted because it carries no information here.** It reads 33.3
at every value by construction: every seat at every 3-player table is a
swept character, and each game has exactly one winner. A pooled sweep of
all six cannot show who gains from the rope. That takes sweeping one
character against the others at preset.

What the table does show:

- **The first quarter of rope buys the most.** From leash 0 to 0.25, games
  halve (50.4 to 26.9 turns), and own-card naming falls from 6.42 to
  1.46. At leash 0 the model may only break ties on the character's own
  score, and it breaks them slowly and bluffily.
- **wrong% falls to zero at 0.5** (16.7 to 0.0, about 2 sigma on 24 games)
  and games are shortest there, 19.1 turns. At 1.0 two wrong accusations
  come back. That is within noise, but not what "more judgment is
  better" predicts.
- **The keep-a-dial test fails as posed.** Plan 6d asked that
  `deviation_rate` rise monotonically with the rope. It goes 0.0, 1.7,
  11.1, then 4.1. The likely cause is the metric, not the dial. The rate
  divides by choices the model *played*, and a wider leash sends it more
  menus, including lopsided ones where it rightly takes the top option.
  The denominator swells with agreement, so the rate can fall while the
  count of deviations rises. `talk/g` jumping to 8.88 at 1.0 fits: more
  calls, more chances to speak. That is a hypothesis. This run did not
  save `--json`, which carries `llm_deviations` and `llm_played`. The
  monotone quantity to test next time is the count, or deviations per
  decision.
- Chattiness was not swept. `talk/g` sits at 3.4-4.0 per seat in the
  twin run and nothing in the transcripts reads as too much or too little,
  so there is no evidence to move it.

**Presets: unchanged, on purpose.** `leash` stays 0.25 and `chattiness`
0.5 for everyone. Table-wide, the sweep points at 0.5: shortest games, no
wrong accusations, cheapest per game. But three things argue against
acting on it yet. The evidence is pooled, so it cannot say whether 0.5
helps each character or just some. It is 8 games per value. And the twin
run already shows that a faster LLM table costs Plum 44 points, so more
rope probably costs him more. Whether that is acceptable is a design
question about how distinct the six methods should stay, not a tuning
question. The per-character ladders below settled it the same day:
neither character gains from more rope, and the presets stand.

### Per-character leash ladders (2026-09-13)

The pooled sweep could not see who gains from the rope, so this runs
one character on the model at a time. Fixed 3-seat table `Plum,Mustard,
Green`, seed 7007, 24 games per value, the swept character alone
LLM-piloted and the other two headless at preset. One headless run on
the same deals is the baseline for both (`ladder-headless` in
`data/llm`). Because every run shares deals and dice, games can be
paired: "lost / gained" counts games the character won headless but not
at that leash, and the reverse.

#### Mustard

`sweep --dial leash --values 0 0.25 0.5 1 --characters Mustard --llm
--llm-characters Mustard --roster Plum,Mustard,Green --players 3 --games
24 --seed 7007`: 3013 s, $8.94, no fallbacks in 1176 calls.

| | win% | wrong% | 1st_acc | never% | named | turns | played | devs | dev/decision |
|---|---|---|---|---|---|---|---|---|---|
| headless | 25.0 | 25.0 | 16.9 | 50.0 | 2.08 | 24.0 | -- | -- | -- |
| leash 0 | 25.0 | 16.7 | 16.2 | 58.3 | 2.04 | 21.3 | 148 | 0 | 0.0% |
| leash 0.25 | 33.3 | 41.7 | 16.7 | 25.0 | 0.75 | 21.6 | 254 | 2 | 0.4% |
| leash 0.5 | 29.2 | 25.0 | 15.7 | 45.8 | 1.21 | 22.0 | 347 | 10 | 1.7% |
| leash 1 | 33.3 | 25.0 | 15.4 | 41.7 | 0.83 | 19.1 | 427 | 10 | 2.0% |

Paired against headless, games lost / gained: leash 0, 4 / 4; 0.25,
3 / 5; 0.5, 4 / 5; 1, 3 / 5. Opponents' win% headless then at each
leash: Plum 62.5, then 50.0, 50.0, 45.8, 54.2; Green 12.5, then 25.0,
16.7, 25.0, 12.5.

- **The leash does not move Mustard.** A net of 0 to +2 games out of 24
  at every value is inside the 9-point binomial std, and wrong% wanders
  (16.7, 41.7, 25.0, 25.0) with no direction. This is the run that
  retires the twin arena's "rescue" reading above.
- **The model barely uses the rope.** At leash 1 it may play anything
  legal on 427 decisions and departs from Mustard's top choice on 10.
  The persona and the "best first" menu make it deferential; the leash
  is an upper bound it never approaches.
- **Keep-a-dial passes on the right metric.** Deviations per *decision*
  rise monotonically, 0.0, 0.4, 1.7, 2.0%. The library's
  `deviation_rate` divides by choices played instead, and played grows
  from 148 to 427 with the leash while deviations plateau at 10, so it
  reads 0.0, 0.8, 2.9, 2.3 and fails. This confirms the denominator
  explanation offered for the pooled sweep; the metric should change.
- **`talk/g` rises with the leash** (2.75 to 7.62) and is the only
  metric the library calls monotone. It is not a chattiness effect: the
  gate is applied per call, and a wider leash means more calls. The two
  Phase 6 dials are coupled through the menu; a chattiness that meant
  "lines per game" would have to be gated per decision instead.
- **Even leash 0 is not the headless game.** With zero deviations,
  Plum's win rate on the same deals still falls from 62.5 to 50.0,
  because the model breaks Mustard's ties differently from his RNG and
  the trajectories diverge from there. The null-backend twin is exact;
  the leash-0 twin is not, and should not be used as a control.

#### Plum

`sweep --dial leash --values 0.25 0.5 1 --characters Plum --llm
--llm-characters Plum --roster Plum,Mustard,Green --players 3 --games
24 --seed 7007`. The leash-0 leg was started and cut after its first
game ran 90 turns (below); its one record is kept as
`ladder-plum-leash-0-aborted`.

4248 s, $18.13, no fallbacks in 1712 calls. Plum costs about 2.5 times
what Mustard does per game: his games run longer and he is asked more
(380 to 817 played decisions per leg against Mustard's 148 to 427).

| | win% | wrong% | 1st_acc | never% | named | turns | played | devs | dev/decision |
|---|---|---|---|---|---|---|---|---|---|
| headless | 62.5 | 0.0 | 25.9 | 37.5 | 0.88 | 24.0 | -- | -- | -- |
| leash 0.25 | 58.3 | 0.0 | 35.1 | 41.7 | 1.33 | 30.3 | 380 | 26 | 3.0% |
| leash 0.5 | 45.8 | 0.0 | 40.3 | 54.2 | 0.88 | 29.8 | 515 | 44 | 5.2% |
| leash 1 | 58.3 | 4.2 | 37.2 | 37.5 | 1.25 | 32.8 | 817 | 81 | 8.8% |

Paired against headless, games lost / gained: leash 0.25, 4 / 3; 0.5,
7 / 3; 1, 4 / 3. Opponents' win% headless then at each leash: Mustard
25.0, then 25.0, 25.0, 20.8; Green 12.5, then 16.7, 29.2, 20.8.
Deviations per decision rise monotonically (3.0, 5.2, 8.8%), as they
did for Mustard, and the model uses more of Plum's rope than Mustard's.

- **Win rate does not track the leash.** 58.3, 45.8, 58.3; a paired net
  of -1, -4, -1 games. The dip at 0.5 is 1.2 sigma. What every leash
  does cost him is time: his first accusation comes 10 to 15 turns
  later than headless at every value, and the table's games run 30 to
  33 turns instead of 24.
- **He parks, and on this table he gets away with it.** The next
  paragraphs show the mechanism; the count of games with five or more
  parked moves goes 0, 4, 8 across the three legs while his win rate
  does not fall with it, because Mustard and Green at preset do not
  punish a stall. Against the twin arena's LLM-piloted table they did:
  that is the 44-point collapse, read together with this run. Plum's
  loss there is his own parking plus opponents fast enough to make it
  fatal.
- **Full rope brings his first wrong accusation** in any run (4.2%, one
  game). Headless Plum never accuses wrongly.

**What the rope does to Plum is let him park.** The mechanism is visible
in every long game and is not the leash. Plum's `movement_scores`
gives 0.20 to any room he can enter and suggest in this turn, whatever
its probability, and about 0.13 to a hallway step toward the room his
count actually favours. Once he stands in a room the floor has already
cleared, "stay and suggest here" is his top-scored move, and the escape
hallway is only *allowed* at leash >= 0.34. Headless Plum has the same
scores but samples them (`sample_softmax`, temperature 0.05), so he
drifts out within a few turns. The model does not sample: it takes the
top-scored option as an instruction, even when the note beside it reads
`P(envelope room) 0.00` and an allowed option beside it reads 0.25.

Counting, per leg, the move calls where the model chose a
zero-probability room while an allowed option led toward a live one:

| leash | move calls | such calls | chose "stay" | games with 5+ |
|---|---|---|---|---|
| 0.25 | 141 | 12 | 10 (83%) | 0 |
| 0.5 | 253 | 109 | 103 (94%) | 4 |
| 1 | 274 | 110 | 101 (92%) | 8 |

At 0.25 the escape is rarely on the menu, so Plum plays almost his
headless game. At 0.5 and 1 it is on the menu and he declines it more
than nine times in ten. The worst case, game 7 at 0.5, is 126 turns: from turn 26 to 98
the model was offered "stay in the Ballroom (0.20, P 0.00)" against an
allowed "hallway toward the Study (0.13, P 0.25)" on 37 consecutive
calls and stayed on all 37, suggesting Scarlett/Candlestick/Ballroom 38
times with the suspect and weapon already right and the Billiard the
answer. He still won that game, at turn 126, because the two headless
seats learned nothing from a suggestion that was refuted the same way
every turn. The aborted leash-0 game is the same shape with ties
instead of a gap: three enterable rooms at 0.20, all cleared, "stay"
listed first, chosen eight times out of eight.

So more rope does not help Plum; it only offers him more chances to do
this. The fix is not a leash value. Two candidates, neither done:
`movement_scores` should not score a cleared room above a step toward
a live one (this is the target-selection problem `docs/architecture.md`
already separates from belief, and it would change headless Plum too,
with the goldens); and the wrapper could shuffle tied options or say in
the prompt that the scores are the character's preference, not an
order. Either changes behaviour at every leash and needs a re-measure
and re-recorded fixtures.

#### Verdict on the presets

`leash` stays at 0.25 and `chattiness` at 0.5 for everyone. Two
characters measured alone, 24 paired games per value each, and neither
gains from more rope: Mustard does not move, Plum loses time and, on a
faster table, games. 0.25 is also the value at which Plum's parking is
rarest, because the escape is seldom on the menu to be declined. The
pooled sweep's tilt toward 0.5 was a table effect of six LLM seats
ending games faster, not any character playing better. Chattiness was
not swept and is coupled to the leash through the per-call gate
(`talk/g` for Plum: 5.0, 7.2, 11.9 across the three legs).

The dial-keeping rule is met for `leash` on deviations per decision,
for both characters. The arena's `deviation_rate` should be redefined
with `llm_decisions` as its denominator before the next sweep.

The ladder JSONs (`ladder_headless.json`, `ladder_mustard.json`,
`ladder_plum.json`) sit beside their game records in `data/llm`.

Per-character notes on whether each persona's voice survived real play
are in `docs/phase6-plan.md`, section 8, under 6c.

## Phase 7: memory (2026-09-14)

Built and live-checked; the design is in `docs/phase7-plan.md` and the
working guide in `docs/logbooks.md`. What it changes about the methods
and the dials:

**Seating, first.** Every measurement above was made with characters
rotating through seats and tokens (Plum played the Scarlett token in
one game and White's in the next). Since 2026-09-14 a character is
locked to its own token (`CLAUDE.md`, "Seat-locked characters"):
`Plum,Mustard,Green` seats Mustard, Green, Plum in that turn order in
every game. Runs from that date on are not paired with the earlier
ones, however alike the flags; the paired leash-0.5 run below was
therefore played fresh on both legs.

- **A third LLM dial, `memory`** (default 0 for every preset), sets how
  much of its own logbook an LLM-piloted character reads before a
  game: the head (its standing instructions, its dossiers on the
  opponents present, its tally) at 0; plus every entry's summary and
  flags at 0.5; plus whole entries above that, all of them at 1. The
  keep-a-dial test for it is `sweep --dial memory --llm --logbook URI`,
  which reads one logbook state at every value and writes nothing;
  tokens per game rise with it trivially, and whether win rate or
  wrong accusations move with depth is the open measurement.
- **Mustard's tree can train on stored games.** With a logbook,
  `rows_from_view` rows from every seat's view of every game in the
  store join his 25-game self-play base. Rebuilt from the 193 stored
  ladder games (10,703 rows) and scored on 8 held-out FloorBot games,
  a noisy first look: mid-game log-loss 1.50 to 1.15 and Brier 0.0895
  to 0.0824 (better), the end checkpoint 0.11 to 0.15 log-loss and
  0.99 to 0.94 top-1 (worse). The tree now pattern-matches three-seat
  character games rather than FloorBot self-play, which is the
  character; a benchmark on character games is the fair test.
- **White's chain starts from a known opponent's habits.** A remembered
  opponent's repeat/new transition frequencies replace the Laplace
  prior at the prior's own mass (four pseudo-counts), so the live
  sequence weighs exactly as before and only the chain's starting
  shape is informed. Rebuilt from the same store: 902 / 985 / 1,211
  transitions for Green / Mustard / Plum.
- **Green's posteriors persist** across runs instead of dying with the
  process.
- **The narrative tier does not widen a menu.** Whatever a character's
  notes say, the model still picks among the options its leash allows,
  so Plum's parking (above) is unreachable by memory at the preset
  leash: his escape is on the menu only at leash >= 0.34. At leash
  0.5, where it is, his own notes cut his stalls by more than half
  over 24 games and bring two early accusations (next section).

### Plum's logbook at leash 0.5 (2026-09-14)

The Phase 7d measurement: does Plum's own logbook teach him out of the
parking? Fixed seating (Mustard, Green, Plum), seed 7007, 24 paired
games, Plum alone on the model at `leash` 0.5 and `memory` 0 (he reads
the head: tally, standing instructions, dossiers), the other two
headless at preset. The off leg has no logbook; the on leg gives one to
Plum only (`--logbook-characters Plum`), starting empty, so it is a
learning curve: game g is played on the entries of games 0 to g-1.

```
arena --games 24 --players 3 --roster Plum,Mustard,Green --seed 7007 --llm --llm-characters Plum --set Plum.leash=0.5 --store data/llm --run-id seated-plum-leash-0.5
arena ... --logbook data/llm --logbook-characters Plum --run-id seated-plum-leash-0.5-logbook
```

Off leg 1252 s, $4.63; on leg 2035 s, $5.56 ($3.32 of decisions and
$2.24 for the 24 debriefs: $0.093 and 42 s each). No fallbacks in 855
calls. `data/llm/pair_report.py` prints the comparison and
`parking_report.py` the counts.

| | win% | wrong% | 1st_acc | never% | turns | played | devs | dev/decision | talk/g | tok/g |
|---|---|---|---|---|---|---|---|---|---|---|
| logbook off | 54.2 | 0.0 | 20.5 | 45.8 | 25.6 | 478 | 40 | 5.2% | 6.54 | 31,689 |
| logbook on | 50.0 | 8.3 | 21.7 | 41.7 | 20.6 | 353 | 52 | 8.8% | 5.67 | 28,480 |

Paired by game, Plum lost 7 and gained 6 (net -1). Opponents' win%:
Mustard 33.3 to 25.0, Green 12.5 to 20.8.

Parking, as counted for the ladders (move calls where the model chose
a zero-probability room while an allowed option led toward a live one):

| | move calls | such calls | chose "stay" | games with 5+ stays |
|---|---|---|---|---|
| logbook off | 210 | 104 | 97 (93%) | 8 |
| logbook on | 169 | 48 | 40 (83%) | 2 |

By quarter of the run, stays on the same six deals: off 36, 11, 13, 37;
on 25, 6, 6, 3. Mean turns by quarter: off 36.0, 14.5, 22.5, 29.5; on
17.8, 20.2, 20.0, 24.3.

- **The notes do teach him out of the parking, mostly.** On the same
  deals his stalls fall from 97 to 40 over the run, and in the last
  quarter from 37 to 3; games with a long stall from 8 to 2; games run
  five turns shorter. The first entry lands before game 2, so even the
  first quarter differs. He names the fault himself: "room-anchoring",
  "redundant-testing" and "slow-tempo" are among his most-used flags
  (11, 10 and 10 of 24 entries), and by the end his standing
  instructions say to keep a list of the rooms nobody has named and to
  probe only from rooms his count still permits. What remains of the
  parking is deliberate: "once I occupy a room nobody can refute, stay
  in it and grind", which is a room he holds himself, used as ballast,
  and is sound.
- **The price is haste.** Two wrong accusations, at P(correct) 0.50
  (game 2, "had to flip a coin") and 0.80 (game 21, "accused the leader
  at four-fifths"), both below his 0.90 threshold and both inside the
  window leash 0.5 opens; the off leg never accused below 1.00, and
  headless Plum never accuses wrongly. The notes push tempo
  ("slow-tempo" and "tempo-discipline" on nineteen entries between
  them) and the model took the early-accusation rope it had always been
  offered. Entry #22's lesson adds the instruction not to accuse below
  threshold on a two-way room split, which is the logbook correcting
  its own excess, one game late.
- **Net, on this table, a wash in wins** (-1 of 24, well inside the
  10-point std): the stalls he sheds are repaid by the two eliminations.
  The ladders showed Mustard and Green at preset do not punish a stall,
  so the parking cost him little here; against a faster table (the twin
  arena) the same reduction should be worth more.
- **The model overrides the method more with memory:** deviations per
  decision 5.2% to 8.8%, and "off-method-pick" is a flag he uses nine
  times ("walked off-method to the one room nobody had named"). The
  logbook is a second voice beside the method's numbers, and the leash
  is what bounds it.
- **The entries and the head read well.** Titles are specific, summaries
  are precis, flags recur (ten flags on seven or more entries each),
  dossiers are verified against the face-up deal ("she held five weapons
  and named the sixth four times"), and the eight standing instructions
  are Clue strategy in Plum's voice. `logbook show --uri data/llm
  --identity Plum` has all of it.
- **Cost.** A debrief is $0.09 and 42 s; the read-back at `memory` 0
  is inside the decision cost, which fell ($4.63 to $3.32) because the
  games got shorter. The on leg is 63% longer in wall time, all of it
  debriefs.
- **Not measured:** the `memory` dial above 0 (a sweep on this logbook
  is `sweep --dial memory --llm --logbook data/llm --logbook-characters
  Plum`), the preset leash 0.25 (where the escape is not on the menu
  and the notes cannot act), and whether the head trained here helps
  on a different table.
