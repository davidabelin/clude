---
title: DeepNash
short: Self-play reinforcement learning for the hidden-information game Stratego
categories: Classwork
redirects: Deep Nash
---
**DeepNash** is a learning system described by Perolat and colleagues in their 2022 paper on Stratego. It uses model-free multiagent reinforcement learning and self-play in a game with hidden piece identities. The paper is in [[clude]]'s [[classwork archive]] because it connects learning with imperfect information and strategic uncertainty. Since Phase 12 clude uses a variant of its training rule for [[Professor Plum]]: see [[regularised Nash dynamics]].[^paper][^clude]

## The strategic problem

Stratego players do not initially know the identities of their opponent's pieces. Moves and encounters reveal information, while deployment and deceptive play influence what an opponent can infer. The paper studies choosing actions in this setting rather than simply predicting a hidden label.

DeepNash uses **Regularised Nash Dynamics** (R-NaD), a learning approach aimed at approximate equilibrium behaviour in the studied two-player zero-sum game. Its self-play does not use the kind of explicit search common in perfect-information game systems. It is a different method from the [[deep Q-network|DQN]] described elsewhere in the archive.[^paper]

## Comparison with Clue

Both games involve private information, revealing events and choices that influence what another player learns. A player can have a useful estimate of hidden information yet make poor decisions about when to reveal, move or commit. This makes the paper relevant to the distinction between [[belief benchmark|belief quality]] and [[arena|playing strength]].

The correspondence has limits. The studied Stratego game has two opponents and a zero-sum outcome. Clue has three to six seats racing to identify an envelope, with turn order, private refutations and elimination after an incorrect accusation. A multi-seat Clue experiment needs its own objective, information model and opponent regime; a Stratego equilibrium result is not a guarantee for that setting.

## In clude

[[Professor Plum]]'s method since 5 October 2026 is an adaptation, described in [[regularised Nash dynamics]]. It keeps two of DeepNash's ingredients, the regularised reward that pulls each update back towards a recent copy of the policy and the NeuRD update on the policy's raw scores, and drops the third, the off-policy correction, because Plum's games are played by the policy being trained. It adds what Clue offers and Stratego does not: a [[deduction floor]] that settles everything certain before the network sees the position, and a belief head trained on the true envelope. The setting differs in the way the comparison above warns: three to six seats, no zero-sum outcome, so the convergence guarantee does not carry over.[^plan]

## The other characters

Clude gives the other five characters different numerical estimators under the same [[deduction floor]], then turns those estimates into actions with common scoring and [[personality dials]]. An optional [[LLM wrapper]] supplies leashed judgement and a voice. Supported numerical memory, narrative notes and preset tuning are described in [[character training]].

DeepNash provides an example of learning a broader strategy through repeated interaction. It does not establish that the present characters are equilibrium policies, that their card estimates are sufficient states, or that adding a language model reproduces its training procedure. Its role here is a reference for future design and evaluation.


## See also

[[Regularised Nash dynamics]] · [[Professor Plum]] · [[Self-play]] · [[Reinforcement learning]] · [[Character training]]

## References

{{references}}

[^paper]: {{cite:perolat-2022}}
[^clude]: {{cite:docs/strategy-glossary.md}}
[^plan]: {{cite:docs/deepnash-plan.md|3.1 The variant: Regularised Nash Dynamics over the floor}}

{{navbox:clude}}
