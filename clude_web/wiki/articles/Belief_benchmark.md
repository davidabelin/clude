---
title: Belief benchmark
short: Evaluating envelope-card probabilities on shared private observations
categories: Measurement
redirects: Benchmark, The benchmark
---
The **belief benchmark** evaluates the six methods' probability estimates separately from their game decisions. It generates completed [[self-play]] games, constructs private observations at specified fractions of their [[suggestion|suggestion]] histories, and gives each method the same observations. Predictions are scored against the actual envelope using [[log-loss]], squared error and top-choice accuracy.[^code]

The recorded [[Classic board]] run used {{fact:bench.grid.games}} floor-player games and {{fact:bench.grid.snapshots}} observations. Its checkpoints measure fractions of suggestions, not time or turns. These results describe prediction quality under that evidence-generating policy; the [[arena]] tests complete playing behaviour instead.

## One observation

Consider a finished game containing twenty suggestions. At the half-way checkpoint, a viewer receives the first ten suggestions as that seat was entitled to see them, its own hand and the resulting floor deductions. Each method predicts the envelope cards from that same view. The scorer then compares the prediction with the actual envelope, which was withheld from the prediction input.[^snapshots]

The other viewers of that game contribute their own private observations. A card shown to one is hidden from another. Those observations are related, not independent games. Reporting {{fact:bench.grid.snapshots}} observations does not imply that many independently shuffled deals.

## Checkpoints and construction

The default checkpoints are {{code:benchmark.checkpoints}}. For a history of $m$ suggestions and fraction $f$, the prefix length is $\max(1,\operatorname{round}(mf))$. Thus the requested fraction groups observations even when rounding prevents exactly that fraction of the history.[^snapshots]

The helper copies a completed state with its suggestion log truncated, clears accusations and marks players active. Its turn field is set to the prefix length. It is a reconstruction of card evidence rather than a full replay of the actual board turn at that point. A method feature using that turn field receives a suggestion index, not elapsed game turns.

Table sizes cycle through three, four, five and six unless fixed by the run. Every viewer contributes each requested checkpoint; a game with no suggestions contributes no snapshots. The [[uniform baseline]] is computed from the same floor as the methods.

## Scores and denominators

| Score | Contribution | Denominator |
|---|---|---|
| [[Log-loss]] | Negative log probability of the true card | Three categories per observation |
| [[w:Brier score]] | Squared error against each card's envelope membership | {{code:cards.total}} cards per observation |
| Top-1 accuracy | Whether the category's highest-probability card is true | Three categories per observation |
| Milliseconds per call | Time spent computing one belief | Method calls |
| Sampled calls | Calls reporting a sampled result | Calls, not game duration |

Loss and Brier score are better when lower; top-1 is better when higher. Ties in top-1 follow the fixed card order. A method can rank the true card first but assign it little probability, so accuracy and log-loss need not agree.[^code]

## Recorded Classic-board results

{{table:bench.grid|Log-loss per category at four checkpoints, top-1 accuracy at completion, and mid-game milliseconds per call. Classic board, 60 floor-player games, seed 4004, recorded 15 September 2026.}}

White's method had lower loss than the uniform baseline at every checkpoint in this run. Mustard's tree was close to the baseline at half-way and had the lowest recorded final-checkpoint loss. Scarlett and Peacock had higher loss than the baseline throughout.[^grid]

Plum's half-way loss was {{fact:bench.grid.Plum.50}} against uniform's {{fact:bench.grid.uniform.50}}. The run reported {{fact:plum.fallback.calls}} sampled fallbacks among {{fact:bench.grid.snapshots}} calls. That is a fraction of benchmark calls, not the fraction of a typical game spent sampling. It also includes all checkpoints, not just half-way observations.

This table used the earlier sample budget. Subsequent budget comparisons increased the current fallback target to {{code:plum.sample_budget}} samples while retaining {{code:plum.node_budget}} search nodes. The dated table remains a record of the earlier configuration, not an automatic rerun of today's code.[^budgets]

## Adaptation and interpretation

Agents are constructed and reset once for a run, then reused. After each snapshot the benchmark sends its true envelope as feedback. Green updates his arm records from those predictions and carries them forward, including to later views and checkpoints of the same game. His column therefore describes this adaptive evaluation, not a cold-start prediction from an untouched estimator at every snapshot.[^code]

Mustard is trained separately on self-play features. The methods being compared did not choose the benchmark's movements or questions. A prediction score can therefore change when the generating policy changes, even if the method does not. Historical [[random bot]] and ring-board regimes are useful comparisons but different experiments.

## Limits

The benchmark does not measure how a method's own questions would change its evidence. It does not measure model conversation, the benefit of narrative memory, or the optimality of an accusation. Related observations from one deal also need care in uncertainty estimates.

The [[arena]] complements this test by letting beliefs, dials and opponents interact in complete games. Neither a benchmark rank nor a small arena rank is a universal ranking of Clue players.


## See also

[[Log-loss]] · [[Uniform baseline]] · [[Self-play]] · [[Arena]] · [[Exact posterior enumeration]]

## References

{{references}}

[^code]: {{cite:clude_training/benchmark.py|`run_benchmark` and `_Accumulator`}}
[^snapshots]: {{cite:clude_training/self_play.py|`generate_snapshots` and `truncate_state`}}
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^budgets]: {{cite:docs/strategy-glossary.md|Tuned presets on the grid (Stage 1e, 2026-09-15)}}

{{navbox:clude}}
