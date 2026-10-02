---
title: The deal
short: How the hidden solution and private hands are selected
categories: The game
redirects: Deal, Dealing
---
**The deal** selects [[the envelope]] and distributes the remaining [[Clue#The cards|cards]] among the players. The engine chooses one suspect, one weapon and one room independently and uniformly, shuffles the other {{code:cards.dealt}} cards, and deals them round the table. Each player receives a private hand; its size is public.[^setup]

The deal fixes the solution and ownership for the whole game. Movement, suggestions and conversation reveal information about those locations without changing them. A [[determinism and seeds|seed]] can reproduce a deal, but a player is shown only their own hand and permitted evidence during play.

## Hand sizes

| Players | Cards in each hand, in seat order |
|---|---|
| 3 | {{code:deal.hands.3}} |
| 4 | {{code:deal.hands.4}} |
| 5 | {{code:deal.hands.5}} |
| 6 | {{code:deal.hands.6}} |

The first seats receive any extra cards because dealing begins at seat zero. A hand has no prescribed mixture of suspects, weapons and rooms: one player could receive several weapons and no suspect cards. The table lists total hand sizes, not category quotas.

## What a hand reveals

Suppose a three-player observer holds two suspects, two weapons and two rooms. Their hand excludes those six cards from the envelope, leaving four suspect candidates, four weapon candidates and seven room candidates. Before any answers, there are $4\times4\times7=112$ possible envelopes from this private view.

For each such envelope, twelve unseen dealt cards must be divided between the two other players, six apiece. The same observer therefore has {{code:deals.3}} possible complete deals before further evidence. [[Combinatorics of a deal]] derives the count and explains why another hand composition changes it.[^count]

The whole table's initial {{code:envelopes}} possible envelopes and one observer's 112 possible envelopes are different counts. The second includes private information. Showing the observer a card can reduce their count without giving every spectator the same reduction.

## Why hand sizes matter

If Mustard has six cards and all six are located, every other card is excluded from his hand. Conversely, if six cards are the only ones still permitted there, all six must be his. The [[deduction floor]] applies these capacity constraints together with suggestions and the rule that every card has exactly one holder.

A hidden answer such as 'Mustard holds Peacock or Rope' is also constrained by the space left in his hand. Treating each card as independently assignable would allow impossible hands. [[Exact posterior enumeration]] searches complete assignments with these capacities intact; the [[uniform baseline]] assigns equal probabilities to the remaining cards within each category without counting all those assignments.

## In the engine

`setup` uses one seeded random stream for choosing the envelope, shuffling and later die rolls. The chosen suspect tokens do not alter how the cards are dealt: the same seed and table size produce the same envelope and seat hands with a different token roster.[^setup]

Hands are fixed sets, so their order in a player's display has no rules meaning. The [[accusation]] verdict compares the proposed triple with the original envelope. Even an eliminated player retains their dealt cards and must show a matching one when asked.

## Limits of reproduction

A seed identifies a deal only together with the setup procedure and player count. Changing the number of seats changes how the shuffled cards are partitioned. Changing the random-number procedure can change the deal. For exact comparisons, [[arena]] records include the roster and settings as well as the seed; saved game records preserve the actual deal.


## See also

[[The envelope]] · [[Detective notepad]] · [[Combinatorics of a deal]] · [[Determinism and seeds]]

## References

{{references}}

[^setup]: {{cite:clude_core/engine.py|`setup`}}
[^count]: {{cite:clude_web/wiki/facts.py|`_deals`}}

{{navbox:clude}}
