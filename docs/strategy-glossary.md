# Strategy Glossary (Developer)

Links each suspect to their implementation module and documents the method
in plain language. Filled in during Phase 3, as each agent is built; the
table below is the skeleton.

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
  into overconfidence.

## Plum -- Exact posterior enumeration

- Module: `clude_agents/exact_enum.py`
- Legacy basis: none; built fresh.
- Summary: A real backtracking CSP search over every still-unresolved
  card, respecting hand-size capacity, the one-envelope-card-per-category
  rule, and `mask.or_constraints` jointly. Counts how many complete,
  consistent deals place each card in the envelope; that count, per
  card, is the exact marginal. Falls back to randomized-constructive
  rejection sampling once the search exceeds a 200,000-node budget
  (typically 5-6 players, early game) -- noisier, and biased toward
  whichever construction order happens to survive, which is an honest
  approximation rather than a fix. Verified against an independent
  brute-force enumerator in `tests/test_agents.py`.

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
  the visual design notes (`CLAUDE.md`).

## Mustard -- Decision tree on game logs

- Module: `clude_agents/decision_tree.py`
- Legacy basis: none; built fresh. Trained on `clude_training.self_play`
  snapshots (Phase 4) -- still `RandomBot` self-play, not smarter
  opponents, so his pattern-matching is bootstrapped on the same
  distribution the benchmark measures everyone against.
- Summary: A hand-rolled CART-style regression tree (Gini-guided binary
  splits, leaf value = mean label), trained once and cached at module
  level, on six engineered per-card features (remaining possible-holder
  count, or-constraint involvement, times named [un]refuted, turn
  fraction, category size). Predicts each still-unresolved card's
  envelope probability from whatever pattern the training games
  happened to show -- confident, and wrong exactly when live play
  doesn't look like dumb-bot self-play. Measured, not just asserted: see
  Phase 4 benchmark results below -- his log-loss runs roughly 2x worse
  than pure ignorance for the whole game.

## Green -- Bandit ensemble over the other five

- Module: `clude_agents/bandit.py`
- Legacy basis: ports from `rps_agents/heuristic/multi_armed_bandit.py`
  (Thompson sampling over predictor arms).
- Summary: A Beta(alpha, beta) posterior per arm -- the other five
  agents, queried every turn -- decayed toward its prior each `observe`
  call like `rps`'s bandit. Samples each arm's posterior and plays the
  single highest-sampled arm's belief outright (no blending). `observe`
  takes a `RevealedOutcome` (the solved envelope, a Phase-4-`ClueTransition`
  placeholder) and scores each arm by how much probability it put on the
  true three cards. Only as good as whichever arm currently looks best.

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
  without resolution. Reads suggestion behavior, not card content:
  strong on who's close to solving, weak on the envelope itself against
  atypical play. Measured, not just asserted: see Phase 4 benchmark
  results below -- his log-loss runs 3-4x worse than pure ignorance for
  the *entire* game, not just early on, the most extreme result of the
  six.

## Phase 4 benchmark results

`clude_training.benchmark.run_benchmark` (`python scripts/clude_cli.py benchmark`)
scores all six agents' belief against the eventual ground truth over
shared `RandomBot` self-play snapshots, at four checkpoints per game (25/
50/75/100% of that game's suggestions). Three metrics -- Brier score,
log-loss, and top-1 category accuracy -- against a `"uniform"` baseline
(the deduction floor's own belief with zero method-specific evidence).
Since Phase 5 (personality -> action) doesn't exist yet, this measures
*belief quality*, not win rate.

A run of 60 games (seed 4004) at game end (checkpoint 1.0):

| Agent | Brier | Log-loss | Top-1 acc |
|---|---|---|---|
| Plum | 0.033 | 0.45 | 0.79 |
| Scarlett | 0.036 | 0.49 | 0.77 |
| Peacock | 0.037 | 0.53 | 0.76 |
| uniform (baseline) | 0.034 | 0.47 | 0.77 |
| Green | 0.035 | 0.60 | 0.78 |
| Mustard | 0.036 | 0.91 | 0.77 |
| White | 0.044 | 1.73 | 0.76 |

Findings, and what they mean:

- **Plum, Scarlett, Peacock all sit at or just past the uniform
  baseline** on log-loss -- exactly what "correct" (Plum) or
  "reasonable, if sloppy" (Scarlett, Peacock) methods should do.
- **Green improves across checkpoints within a run** (log-loss 0.83 ->
  0.60 from the 25% to 100% checkpoint in the 60-game run) as his Beta
  posteriors accumulate real evidence about which of the other five to
  trust -- his posteriors are deliberately *not* reset between games
  (David's call, 2026-09-11; see `clude_training/benchmark.py`).
- **Mustard and White are both measurably worse than pure ignorance for
  the whole game**, not just early when there's little evidence yet --
  White dramatically so (3-4x worse throughout). Top-1 accuracy for both
  stays roughly in line with everyone else, so this is specifically a
  *calibration* problem (confident on the wrong card) rather than a
  ranking problem (picking the wrong card as most likely).
- **David's call (2026-09-11): leave this as-is rather than smoothing
  it away.** "Confidently wrong on unusual deals" (Mustard) and "weak on
  the envelope itself" (White) were the intended character flaws from
  the start (`CLAUDE.md`); the benchmark now gives real numbers for how
  bad that is, which is useful input to Phase 5's personality tuning --
  a character whose confidently-wrong beliefs actually cost it games is
  a stronger, more legible flaw than a softened one. Revisit if Phase 5
  self-play shows either of them losing so badly it stops being fun to
  play against.

### Calibration note (2026-09-11, measured with the CLI)

Where the bad log-loss actually comes from, over 20 games (seed 4004,
checkpoints 0.5 and 1.0, 540 scored categories per agent):

| Agent | Categories with a hard 0 on the true card | Share of total log-loss from those | Log-loss on the rest |
|---|---|---|---|
| Mustard | 27 (5.0%) | 69% | 0.50 |
| White | 40 (7.4%) | 79% | 0.45 |
| Scarlett | 0 | 0% | 0.59 |
| Plum | 0 | 0% | 0.53 |

So both flaws are, as currently measured, almost entirely a hard-zero
artifact, not a ranking or pattern-matching failure: away from those
cases Mustard and White are calibrated as well as Plum. The mechanisms
are mechanical -- a tree leaf with no positive training rows predicts
exactly 0.0 (`train-mustard` prints `leaf predictions: min 0.000`), and
White gives raw score 0 to any card no opponent has named yet (visible
in any `trace`: `S: ... Mustard 0.00` while Mustard is the murderer).
`mask_and_normalize` passes a raw 0 straight through as probability 0,
and `-log(0)` is clamped to about 20.7. Whether to keep this is a Phase
5 decision; see `docs/phase5-plan.md`.

## Registry and factories

- Agent registration metadata: `clude_agents/__init__.py`.
- Build by suspect name: `build_agent(name)` (mirrors
  `rps_agents.heuristic.build_heuristic_agent`).
- Enumerate available specs: `list_agent_specs()`.
