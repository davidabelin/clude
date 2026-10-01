---
title: Belief
short: What a method produces: a probability for every card
categories: Methods
redirects: Beliefs, ClueBelief
kind: stub
---
A **belief**, in [[clude]], is one player's set of probabilities for what is in [[the envelope]]: a number for each of the {{code:cards.total}} cards, summing to 1 across the {{code:cards.suspects}} suspects, to 1 across the {{code:cards.weapons}} weapons and to 1 across the {{code:cards.rooms}} rooms. Producing one is all a [[Category:Methods|method]] does. Turning it into a move, a [[suggestion]] or an [[accusation]] is the work of the character's [[personality dials]].[^base]

Whatever a method computes, the [[deduction floor]] has the last word: a card it has ruled out is set to 0 and a card it has proved is set to 1 before the belief is used.

## References

{{references}}

[^base]: {{cite:clude_agents/base.py|`ClueBelief` and `mask_and_normalize`}}

{{navbox:clude}}
