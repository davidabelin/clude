---
title: Log-loss
short: The score for a probability: the price of being surprised
categories: Mathematics
redirects: Log loss, Logloss, Logarithmic loss, Cross-entropy
kind: stub
---
**Log-loss** is the score the [[belief benchmark]] gives a [[belief]]. For each category it takes the probability $p$ the method gave to the card that was really in the envelope and charges $-\ln p$. A method that was certain and right pays nothing; one that gave the true card an even chance pays 0.69; one that gave it one chance in six pays 1.79; and one that had ruled it out pays without limit, which the benchmark caps at {{fact:bench.zero_cost}}.[^glossary] Lower is better.

The score rewards honesty about uncertainty. A method cannot improve it by sounding surer than it is: confidence in a wrong card costs far more than the same confidence in a right one earns. Outside clude the same quantity is called [[w:Cross-entropy|cross-entropy]].

## References

{{references}}

[^glossary]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}

{{navbox:clude}}
