---
title: Log-loss
short: A probability score that penalises low confidence in the true outcome
categories: Mathematics
redirects: Log loss, Logloss, Logarithmic loss, Cross-entropy
kind: stub
---
**Log-loss** measures the probability assigned to the outcome that actually occurred. For each card category, the [[belief benchmark]] takes the probability $p$ assigned to the true envelope card and computes $-\ln p$, where $\ln$ is the natural logarithm. Probability 1 gives loss 0; probability 0.5 gives about 0.69; and one chance in six gives about 1.79. Probability 0 would give infinite loss, so the benchmark clips probabilities and caps this contribution at {{fact:bench.zero_cost}}. Lower loss is better.[^glossary]

Unclipped logarithmic loss is a proper scoring rule: reporting the true distribution minimises expected loss. It penalises confident mistakes heavily, but one realised outcome cannot establish whether a probability estimate was correct. For a one-hot true outcome, the loss is also [[w:Cross-entropy|cross-entropy]] with the predicted distribution.

## References

{{references}}

[^glossary]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}

{{navbox:clude}}
