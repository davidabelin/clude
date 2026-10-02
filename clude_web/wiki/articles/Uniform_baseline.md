---
title: Uniform baseline
short: Equal probabilities among the deduction floor's remaining candidates
categories: Measurement
redirects: Uniform, Baseline, Uniform (baseline)
kind: stub
---
The **uniform baseline** is a [[belief]] formed directly from the [[deduction floor]]. Proven envelope cards receive probability 1, excluded cards receive 0, and remaining candidates share the probability equally within each category. The [[belief benchmark]] uses it as a reference: a method with lower [[log-loss]] improves on these estimates in that evaluation, while one with higher loss makes them less accurate on average.[^glossary]

In the recorded [[Classic board]] benchmark, [[Naive Bayes]] and [[Dempster-Shafer theory]] had higher log-loss than the baseline at all four checkpoints. Equal per-card probabilities are a simple reference, not necessarily the exact marginals of a uniform distribution over consistent deals; joint constraints can favour some cards.

## References

{{references}}

[^glossary]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}

{{navbox:clude}}
