---
title: Deduction floor
short: The logic all six characters share: what is certain, and nothing else
categories: Methods
redirects: Floor, The floor, The deduction floor, Constraint propagation
kind: stub
---
The **deduction floor** is the part of every character's reasoning that is not a matter of opinion. From a player's own hand and the history of [[suggestion|suggestions]] it works out everything that follows for certain: which cards are placed, which holders are still possible for the rest, and which "this player holds at least one of these" facts remain open. It repeats three rules until nothing changes: an open fact with one card left becomes a placed card; a category with one candidate left has found its envelope card; a full hand can hold nothing more.[^architecture]

Every [[Category:Methods|method]] reasons on top of the floor and has its result checked against it afterwards, so that the six characters "differ in how they reason under uncertainty, never in what is logically certain".[^invariant] The floor also plays a seat of its own as the *floor bot*, and it is what fills in a human player's [[detective notepad]].

{{figure:floor-then-method|wide|The floor comes before every method and after it.}}

## References

{{references}}

[^architecture]: {{cite:docs/architecture.md|The deduction floor (`clude_constraints`)}}
[^invariant]: {{cite:CLAUDE.md|Architecture in brief}}

{{navbox:clude}}
