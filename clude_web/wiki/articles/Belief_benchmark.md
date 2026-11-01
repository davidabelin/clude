---
title: Belief benchmark
short: Evaluating envelope-card probabilities on shared private observations
categories: Measurement
redirects: Benchmark, The benchmark
---
The **belief benchmark** evaluates the six methods' probability estimates separately from their game decisions. It generates completed [[self-play]] games, constructs private observations at specified fractions of their [[suggestion|suggestion]] histories, and gives each method the same observations. Predictions are scored against the actual envelope using [[log-loss]], squared error and top-choice accuracy.[^code]

The current Phase 14 run used {{fact:phase14.bench.games}} floor-player games and {{fact:phase14.bench.snapshots}} observations. Its checkpoints measure fractions of suggestions, not time or turns. These results describe prediction quality under that evidence-generating policy; the [[arena]] tests complete playing behaviour instead.

## One observation

Consider a finished game containing twenty suggestions. At the half-way checkpoint, a viewer receives the first ten suggestions as that seat was entitled to see them, its own hand and the resulting floor deductions. Each method predicts the envelope cards from that same view. The scorer then compares the prediction with the actual envelope, which was withheld from the prediction input.[^snapshots]

The other viewers of that game contribute their own private observations. A card shown to one is hidden from another. Those observations are related, not independent games. Reporting {{fact:phase14.bench.snapshots}} observations does not imply that many independently shuffled deals.

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

## Current Phase 14 results

Phase 14 compared the former Plum checkpoint with the fresh networks on 120 floor-player games, seed 641600, and 2,160 private snapshots. There are 540 observations at each suggestion-history checkpoint, not 2,160 independent deals.[^phase14]

{{table:plum.phase14.benchmark|Current Run 3 and the former checkpoint on identical observations, with the same uniform floor baseline.}}

Run 3's loss was slightly higher at the first two checkpoints and slightly lower at the last two. All differences stayed inside the 0.02 acceptance margin, and both networks beat the uniform baseline at every checkpoint. This supports keeping belief quality while improving play in the separate balanced tournament; it does not show uniformly improved probability estimates.

Mustard, White and Green were selected on a different 19-game held-out corpus. Their paired before/after losses appear in [[measurement record]]. Those candidate-selection scores and Plum's benchmark have different evidence and starting states; they cannot be combined into a current six-method league table.

## What has not been measured

No benchmark since Phase 14 has scored all six methods on one set of snapshots. [[Miss Scarlett]]'s and [[Mrs. Peacock]]'s methods carry no learned state and were last benchmarked on 15 September 2026, in a Classic-board run that predates the [[landing rule]], the rebuilt methods and Plum's network; its table is kept in the maintainer glossary, not here. A fresh six-method run on current code, with the current Plum weights and the released method documents, is the measurement still to be collected before the methods can be ranked against one another again.[^grid]

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
[^phase14]: {{cite:docs/strategy-glossary.md|Phase 14 Run 3, the current Plum (2026-10-18)}}

{{navbox:clude}}
