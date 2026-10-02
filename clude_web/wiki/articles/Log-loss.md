---
title: Log-loss
short: A scoring rule penalising low probability assigned to the true outcome
categories: Mathematics
redirects: Log loss, Logloss, Logarithmic loss, Cross-entropy
---
**Log-loss** scores a prediction by taking the negative logarithm of the probability assigned to the outcome that actually occurred. A confident correct prediction has low loss; a confident wrong one has high loss. [[clude]] uses it to compare envelope-card estimates in the [[belief benchmark]] and to rank Green's arms.[^benchmark]

The benchmark averages the loss over the three card categories and across observations. It is a probability-quality measure, not a win rate. A character can have useful estimates yet lose through movement or accusation timing.

## A checkable example

Suppose the actual envelope weapon is Rope. A prediction assigning Rope probability 0.5 receives $-\ln(0.5)$, about 0.69. Assigning it 0.1 receives about 2.30. Assigning it 0.9 receives about 0.11. The unused probabilities matter through normalisation: giving too much to another weapon leaves less for Rope.

| Probability of the true card | Loss, using the natural logarithm |
|---|---|
| 1 | 0 |
| 1/2 | {{code:loss.half}} |
| 1/6 | {{code:loss.sixth}} |
| 1/10 | {{code:loss.tenth}} |
| 0 | Infinite before clipping |

These are computed examples, not measured benchmark results. The logarithm's base sets the unit: natural logarithms give **nats**, while base-two logarithms give **bits**. Lower is better in either unit.

## Formally

For an observed category outcome $y$ and predicted category probabilities $p$, the loss is

$$ L(p,y)=-\ln p(y). $$

$p(y)$ is the probability assigned to the true card. In a Clue observation, let $s$, $w$ and $r$ be the true suspect, weapon and room. The unclipped per-category mean is

$$ L=-\frac{\ln p(s)+\ln p(w)+\ln p(r)}{3}. $$

This averages three marginal scores. It is not an evaluation of the exact joint posterior of the full envelope. Multiplying marginals for an accusation makes an additional [[independence]] approximation.

Log-loss is a [[w:Scoring rule#Strictly proper scoring rules|strictly proper scoring rule]]: under a fixed true distribution, its expected value is minimised by reporting that distribution. This concerns repeated prediction under a distribution, not a promise that the lowest-loss method wins every finite sample.[^scoring]

## Clipping in clude

The implementation replaces the true-card probability by at least {{code:benchmark.epsilon}} before taking its logarithm. A hard zero therefore incurs about {{fact:bench.zero_cost}} for that category instead of infinity. The cap is numerical handling of an impossible prediction, not a claim that such a zero was reasonable.[^benchmark]

The [[deduction floor]] can set legitimate zeros on excluded cards. A sound floor cannot exclude the true envelope card from a valid observation. Zeros on unresolved true cards can instead come from a method's raw scores or insufficient sampling before masking and normalisation.

Clipping prevents one zero from making the whole run unusable, but repeated near-zero predictions can still dominate an average. The historical random-bot regime exposed that failure for some methods; later smoothing and floor-player evidence changed the results.

## Other scores and Green's reward

The benchmark also reports **Brier score**, the mean squared error over all {{code:cards.total}} card-membership probabilities, and **top-1 accuracy**, the fraction of categories whose highest-scoring card is correct. Brier weights rooms more heavily in its per-card average because there are more room cards; log-loss averages one contribution per category.[^benchmark]

Top-1 ignores how much probability the winner received. Two methods can choose the same top card yet have very different log-loss. A confident wrong answer may cost little top-1 detail beyond the error itself but receives a large logarithmic penalty.

Green ranks his five arms by their loss against the revealed envelope and converts rank into a fractional reward. That reward is not the loss itself or a binary game win. It updates decayed [[beta distribution|Beta]] records, as described in [[bandit ensemble]].[^green]


## See also

[[Belief benchmark]] · [[Uniform baseline]] · [[Entropy and bits]] · [[Bandit ensemble]]

## References

{{references}}

[^benchmark]: {{cite:clude_training/benchmark.py|`_Accumulator.update`}}
[^scoring]: {{cite:gneiting-raftery-2007|Section 3, categorical variables and the logarithmic score}}
[^green]: {{cite:clude_agents/bandit.py|`log_loss`, `rank_rewards` and `observe`}}

{{navbox:clude}}
