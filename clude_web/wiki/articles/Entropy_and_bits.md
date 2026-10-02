---
title: Entropy and bits
short: Measuring uncertainty and information on a logarithmic scale
categories: Mathematics
redirects: Entropy, Bits, Information gain
dyk: ... that four equally likely possibilities carry two [[entropy and bits|bits]] of uncertainty?
---
**Entropy** measures the average uncertainty of a probability distribution. A **bit** is the information unit obtained by using base-two logarithms. For equally likely possibilities, entropy is the logarithm of their count: four equally likely outcomes carry two bits of uncertainty.[^shannon]

These ideas help explain evidence gathering and [[clude]]'s certainty display. The display uses a logarithmic score based on the character's best accusation product. It is not the Shannon entropy of the full posterior, and the characters' movement 'information' feature is not an expected entropy reduction.

## Small examples

An equally likely choice between two envelope weapons has one bit of uncertainty. Ruling one out leaves a certain weapon and zero bits. An equally likely choice among four has two bits; reducing it to two leaves one bit. The examples count outcomes under an equal-weight model, not the number of questions needed in an actual game.

At the start, {{code:envelopes}} equally likely triples have about {{code:entropy.envelopes}} bits of uncertainty. A private hand already reduces that uncertainty for its holder. Public displays can use the common initial scale while players possess different private evidence.

## Shannon entropy

For finite outcomes indexed by $i$, with probabilities $p_i$, entropy in bits is

$$ H=-\sum_i p_i\log_2 p_i. $$

The sum runs over the outcomes, and a zero-probability term contributes zero by continuity. Equal probabilities over $N$ outcomes give $H=\log_2 N$. A certain outcome gives $H=0$.[^shannon]

Entropy uses the whole distribution rather than only its largest value. Two beliefs with the same top card can have different uncertainty in the remaining alternatives. A sum of separate suspect, weapon and room entropies equals joint entropy only under [[independence]].

## The certainty display

Let $P$ be the product of the character's highest confidence values and $N={{code:certainty.triples}}$ the initial triple count. The implementation displays the clipped value

$$ C=\frac{\ln(PN)}{\ln N}. $$

Here $\ln$ is the natural logarithm; using the same base above and below gives the same fraction. The result is limited to the interval from 0 to 1. A zero or negative product gives 0.[^certainty]

At $P=1/N$, the display is 0. At $P=1$, it is 1. Halfway corresponds to $P=1/\sqrt N$, or roughly one chance in {{code:certainty.half.one_in}}, rather than a 50% accusation score. The scale makes gains in confidence visible when the product is still relatively small.

This is a transformation of the method's score, not independent evidence of correctness. Peacock uses her belief-bound product, while other characters use their own probability product. A falsely confident method can therefore approach the high end without having found the true answer.

## Information gain and choices

Expected information gain compares current entropy with the average entropy after possible answers to a question. Computing it requires probabilities for those answers and their resulting beliefs. The shared [[curiosity]] score instead uses a target room's current envelope probability, discounted by distance.[^features]

That proxy is easier to calculate but need not choose the most informative suggestion. A room unlikely to be the answer can still permit a useful question about suspect and weapon cards, especially if nobody else holds its card. The [[landing rule]] partly recognises this distinction.

## Loss, surprise and limits

For an observed event of probability $p$, $-\log_2 p$ is its information or surprisal in bits. [[Log-loss]] uses the same form with natural logarithms to score predictions of the actual envelope cards. Entropy averages surprisal under a distribution; a realised loss concerns the event that occurred.

Neither measure counts social confidence, narrative detail or the physical difficulty of a move. More words in a [[logbook]] do not automatically mean more evidence about the next game's cards.


## See also

[[Probability]] · [[Log-loss]] · [[Belief]] · [[Curiosity]]

## References

{{references}}

[^shannon]: {{cite:shannon-1948|Part I, sections 1 and 6}}
[^certainty]: {{cite:clude_agents/character.py|`certainty`}}
[^features]: {{cite:clude_agents/features.py|`room_features`}}

{{navbox:clude}}
