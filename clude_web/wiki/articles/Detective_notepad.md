---
title: Detective notepad
short: The private grid of possible card locations
categories: The game
redirects: Notepad, Notes, Your notes, Detective notes
---
A **detective notepad** records what a [[Clue]] player knows about card locations. Cards form rows and possible holders form columns, including [[the envelope]]. Marks distinguish a known holder, an excluded holder and an unresolved possibility. In [[clude]], the automatic notepad is the [[deduction floor]] applied to that player's own hand and observed answers.[^floor]

The notepad reports deductions rather than a character's speculative [[belief]]. Its conclusions can differ between players because shown cards are private. Its unresolved cells can also contain possibilities that a more exhaustive argument would eliminate: the floor is sound but incomplete.

## Reading the grid

Suppose Plum asks about Peacock, Rope and Hall. Scarlett passes and Mustard shows Rope to Plum. Plum can mark all three cards excluded from Scarlett's hand and Rope located in Mustard's. Rope is then excluded from every other holder, including the envelope.

A spectator has the same three exclusions for Scarlett but cannot normally mark Rope as Mustard's. The spectator instead records that Mustard holds at least one of Peacock, Rope and Hall. The question never reaches the seats after Mustard, so their cells stay unresolved.[^view]

| Mark's meaning | Conclusion | Further use |
|---|---|---|
| Located | This holder has the card | Exclude every other holder |
| Excluded | This holder cannot have the card | Look for the last possible holder |
| Possible | Evidence has not ruled it out | Retain it for further reasoning |
| At least one of a set | This holder has some matching card | Narrow the set as other cards are placed |

Possible does not mean equally probable. A [[Category:Methods|method]] may assign different probabilities to cards whose notepad entries look alike.

## The automatic deductions

The floor starts with the private hand, public hand sizes, known shows, passes and hidden disproofs. It repeatedly applies ownership, category and capacity rules. Every card has exactly one holder, the envelope has exactly one card of each kind, and a hand contains exactly its dealt number of cards.[^floor]

If Mustard must hold Rope or Hall and Hall is placed in Green's hand, Mustard must hold Rope. If five suspect cards are excluded from the envelope, the sixth is proven there. If Green's whole hand is located, every other card is excluded from his column. Conclusions can therefore propagate through several rows without another suggestion.

## A worked position

{{figure:floor-notepad|wide|The computed Rope-question position. Most cards are placed; White, Peacock, Rope and Wrench remain unresolved between Mustard and the envelope.}}

In this constructed fixture, the observer has six cards, Green's six are known, and four cards remain open: White, Peacock, Rope and Wrench. Mustard has two hand slots left, the envelope still needs one suspect and one weapon, and Mustard must hold Peacock or Rope. Study is already proven as the room.[^example]

The individual open cells do not express that entire constraint. [[Exact posterior enumeration]] combines it with hand capacities and finds three consistent deals. The floor leaves the four card locations unresolved. This is the distinction between useful local deductions and exhaustive counting.

## Privacy and conversation

The notepad is built separately for each seat. A privately shown card appears in the entitled player's observation, while other players see a hidden disproof. There is no common omniscient grid used to advise everyone.[^view]

[[Table talk]] does not create a formal location or exclusion. A claim such as 'Green has the Hall' may guide a listener's choice, but the engine does not certify it and the floor does not accept it as a dealt-card fact. The [[LLM wrapper]] can show conversational history alongside the notepad while keeping the two kinds of evidence distinct.


## See also

[[Deduction floor]] · [[Belief]] · [[Suggestion]] · [[Uniform baseline]]

## References

{{references}}

[^floor]: {{cite:clude_constraints/propagator.py|`DeductionMask` and fixed-point propagation}}
[^view]: {{cite:clude_core/state.py|`ClueObservation.for_player`}}
[^example]: {{cite:clude_web/wiki/facts.py|`rope_observation`}}

{{navbox:clude}}
