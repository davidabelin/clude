---
title: Softmax and temperature
short: Sampling scored choices with a controllable degree of randomness
categories: Mathematics
redirects: Softmax, Softmax function
---
**Softmax** converts scores into probabilities by exponentiating and normalising them. **Temperature** controls how strongly score differences affect the result. [[clude]] uses this combination to sample headless movement, suspect and weapon choices, and matching cards to show. Higher-scoring options remain more likely at positive temperature, but lower-scoring ones can be selected.[^sampler]

Near zero temperature, the implementation chooses a top-scoring option and breaks ties uniformly. At high temperature, choices approach uniform probabilities. Temperature does not change the method's card estimates, make illegal choices available or govern the accusation threshold test.

## Two options

Consider scores 0.8 and 0.6, a gap of 0.2. At temperature 0.1, the higher option is about {{code:softmax.0.1}} likely. At temperature 0.5, it is about {{code:softmax.0.5}} likely. A higher temperature makes the lower option more competitive while preserving their ordering.

These probabilities are computed from the formula for this constructed two-option menu. They are not measured game frequencies. With more alternatives, their probabilities also depend on the other scores.

If both scores are equal, each has probability one half at every positive temperature. The zero-temperature implementation also samples ties rather than selecting the first entry. Thus turning temperature to zero removes lower-score sampling, not every source of randomness.

## Formally

For scores $S_1,\ldots,S_k$ and positive temperature $T$, option $i$ has probability

$$ q_i=\frac{\exp(S_i/T)}{\sum_{j=1}^k\exp(S_j/T)}. $$

$\exp$ is the exponential function, $k$ is the option count, and the denominator sums all options' weights. The output probabilities $q_i$ sum to 1. They describe selecting an action, not the probability that its card is in the envelope.

For two scores separated by $\Delta$, the higher-score probability simplifies to

$$ q_{\rm high}=\frac{1}{1+\exp(-\Delta/T)}. $$

Adding the same constant to every score changes no probability. The implementation uses this fact to subtract the largest score before exponentiating, keeping the largest exponent at zero and reducing overflow risk.[^sampler]

## Score scale matters

Doubling every score while keeping temperature fixed sharpens the selection just as halving the temperature would. A temperature therefore has meaning relative to the score scale. The shared movement and disclosure scores lie between 0 and 1, as do the suspect and weapon probabilities used for ordinary selection.

[[Secrecy]] multiplies disclosure preferences by its dial, so its ratio to temperature affects the choice. With positive secrecy and zero temperature, the ranking remains the same as secrecy rises. A dial's numerical change need not alter a greedy decision.

## In the character

Movement samples the [[curiosity]] blend. An ordinary suspect or weapon pick samples envelope-card probabilities among cards outside the player's hand. [[Bluffing]] uses a separate coin flip and a uniform held-card choice before that ordinary path. Card-showing samples secrecy scores among the engine's matching candidates.[^character]

Accusation is different: the headless character compares its confidence product to its threshold and either accuses or waits. Increasing temperature does not directly randomise that test, although it can change the preceding moves and evidence and therefore when the threshold is reached.

The [[LLM wrapper]] uses the same scored menus but delegates accepted choices to the model within the leash. Its accepted replies are not guaranteed to follow this softmax. Fallback invokes the headless sampler where applicable.

## Evaluation and limits

[[Dial sweeps]] found that high temperatures could weaken play in the recorded regimes by flattening otherwise useful preferences. Their outcome depended on the roster, board and other settings, so the formula alone does not identify an optimal temperature.

Softmax is also distinct from [[Thompson sampling]]. Green draws a possible arm quality from each Beta record and chooses the largest draw; the character later uses softmax for game actions. One randomises method selection through uncertainty about quality, the other samples a fixed list of action scores.


## See also

[[Personality dials]] · [[Leash]] · [[Bandit ensemble]] · [[Dial sweeps]]

## References

{{references}}

[^sampler]: {{cite:clude_agents/features.py|`sample_softmax`}}
[^character]: {{cite:clude_agents/character.py|decision sampling}}

{{navbox:clude}}
