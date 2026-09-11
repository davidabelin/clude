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
- Legacy basis: none; built fresh. Bootstrapped on `RandomBot` self-play
  via `clude_core.engine.run_game` (Phase 1) since `clude_training`
  doesn't exist yet -- a placeholder dataset, not Phase 4's real
  self-play pipeline; retraining against that later is expected to
  change his behavior, not just his accuracy.
- Summary: A hand-rolled CART-style regression tree (Gini-guided binary
  splits, leaf value = mean label), trained once and cached at module
  level, on six engineered per-card features (remaining possible-holder
  count, or-constraint involvement, times named [un]refuted, turn
  fraction, category size). Predicts each still-unresolved card's
  envelope probability from whatever pattern the training games
  happened to show -- confident, and wrong exactly when live play
  doesn't look like dumb-bot self-play.

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
  atypical play.

## Registry and factories

- Agent registration metadata: `clude_agents/__init__.py`.
- Build by suspect name: `build_agent(name)` (mirrors
  `rps_agents.heuristic.build_heuristic_agent`).
- Enumerate available specs: `list_agent_specs()`.
