---
title: Bandit ensemble
short: Mr. Green's method: trust whichever of the other five has been doing best
categories: Methods
redirects: Bandit, Multi-armed bandit, Thompson sampling, Green's method
kind: stub
---
The **bandit ensemble** is the method by which [[Mr. Green]] forms his [[belief]], or more exactly borrows it. The other five methods are the "arms" of a [[w:Multi-armed bandit|multi-armed bandit]]. For each he keeps a [[w:Beta distribution|Beta distribution]] summarising how well it has done; each turn he draws one number from every arm's distribution and plays the belief of the arm that drew highest, whole. This is [[w:Thompson sampling|Thompson sampling]]: arms with a good record are chosen most often, and uncertain ones still get tried.[^glossary][^sb]

After each game the arms are ranked by how close each came to the truth and their records updated. The balance he strikes, between using what has worked and testing what might, is the oldest problem in [[w:Reinforcement learning|reinforcement learning]].

## References

{{references}}

[^glossary]: {{cite:docs/strategy-glossary.md|Green -- Bandit ensemble over the other five}}
[^sb]: {{cite:sutton-barto|Chapter 2, "Multi-armed Bandits", sets out the problem of balancing exploration and exploitation}}

{{navbox:clude}}
