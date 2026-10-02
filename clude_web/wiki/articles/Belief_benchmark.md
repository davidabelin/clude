---
title: Belief benchmark
short: How the six methods' probabilities are scored against the truth
categories: Measurement
redirects: Benchmark, The benchmark
kind: stub
---
The **belief benchmark** evaluates probability estimates separately from game decisions. In the recorded [[Classic board]] run, {{fact:bench.grid.games}} floor-bot games supplied {{fact:bench.grid.snapshots}} observations. Each method evaluated the same seat views at four checkpoints: after a quarter, half, three-quarters and all of each game's [[suggestion|suggestions]]. Its [[belief]] was scored against the actual envelope using [[log-loss]]. The checkpoints are fractions of suggestions, not elapsed time or turns.[^glossary]

The results on the [[Classic board]] are tabulated at [[Naive Bayes#Measured|Naive Bayes]] and discussed for one method at [[Professor Plum#Record|Professor Plum]].

## References

{{references}}

[^glossary]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}

{{navbox:clude}}
