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
- Summary: TODO (Phase 3).

## Plum -- Exact posterior enumeration

- Module: `clude_agents/exact_enum.py`
- Legacy basis: none; built fresh.
- Summary: TODO (Phase 3). Needs a sampling fallback at 5-6 players to stay
  within a time budget -- track when that kicks in and how noisy it gets.

## Peacock -- Dempster-Shafer belief/plausibility

- Module: `clude_agents/dempster_shafer.py`
- Legacy basis: none; built fresh.
- Summary: TODO (Phase 3). This is the method most worth documenting
  carefully -- mass assignments over card subsets, and the belief/plausibility
  split that drives the two-tone UI bar.

## Mustard -- Decision tree on game logs

- Module: `clude_agents/decision_tree.py`
- Legacy basis: none; built fresh. Requires `clude_training` self-play data
  before there is anything to train on.
- Summary: TODO (Phase 3/4).

## Green -- Bandit ensemble over the other five

- Module: `clude_agents/bandit.py`
- Legacy basis: ports from `rps_agents/heuristic/multi_armed_bandit.py`
  (Thompson sampling over predictor arms).
- Summary: TODO (Phase 3).

## White -- Markov model over suggestion sequences

- Module: `clude_agents/markov.py`
- Legacy basis: `legacy/opponent_model.py`, starting point.
- Summary: TODO (Phase 3).

## Registry and factories

- Agent registration metadata: `clude_agents/__init__.py`.
- Build by suspect name: `build_agent(name)` (mirrors
  `rps_agents.heuristic.build_heuristic_agent`).
- Enumerate available specs: `list_agent_specs()`.
