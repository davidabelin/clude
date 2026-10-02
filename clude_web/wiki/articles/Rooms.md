---
title: Rooms
short: The nine places where players can make suggestions
categories: The game
redirects: Room, Billiard Room, Dining Room
---
**Rooms** are the nine named destinations on the [[Classic board]] and one of the three categories of [[Clue#The cards|cards]]. Entering a room permits a [[suggestion]] there. The room card itself is either in someone's hand or in [[the envelope]]; the positions of tokens do not determine who holds it.

Each room is treated as a single position for play. Its drawn floor contains many cells, but a token does not spend a die roll crossing them. The central cellar is impassable and is not a tenth room.[^board]

## At the table

Suppose Plum suspects the Library but is standing in the Hall. He cannot ask about the Library until he gets there. He can, however, make a Hall suggestion to investigate its suspect and weapon. If he already holds the Hall card, nobody else can answer with it, so a disproof must concern one of those other two cards. An [[accusation]] naming Library can be made from either location.

The room that is easiest to enter may therefore be useful even when its own card is settled. By contrast, a room held by an opponent often produces another showing of that same card. The [[landing rule]] and the [[Personality dials#Curiosity|curiosity dial]] explain how numerical characters score this distinction.

## Kitchen

Kitchen occupies the upper-left corner. Its single door faces the corridor below it. Its [[secret passage]] leads to Study at the opposite corner. A token can leave through the door or take the passage, subject to the ordinary movement choices.[^doors]

## Ballroom

Ballroom lies along the upper edge between Kitchen and Conservatory. It has four doors, two facing the side corridors and two facing the corridor below. It has no passage. Multiple exits can make a blocked approach less restrictive than it is for a single-door room.

## Conservatory

Conservatory occupies the upper-right corner. Its single door opens downwards, even though another corridor square touches the left side of its door cell. Its passage leads to Lounge. The [[Classic board#Doors and routes|door detail]] shows why touching a room cell is not enough to enter it.

## Billiard Room

Billiard Room, named `Billiard` in the engine, lies on the right below Conservatory. It has two doors and no passage. Its card is a single room card under either spelling; records use the engine's shorter name.

## Library

Library lies on the right below Billiard and above Study. It has two doors, one opening upwards and one to the left. It has no passage. The shared movement scoring can favour it as a likely solution room or as a nearby place to ask about other cards.

## Study

Study occupies the lower-right corner. Its single door opens upwards. Its passage leads to Kitchen. A passage arrival permits an immediate Study suggestion, just as entering through the door does.

## Hall

Hall lies along the lower edge, between Lounge and Study. It has three doors and no passage. It is a room, distinct from the corridors or hallways through which tokens travel. A question naming Hall must be asked from Hall itself.

## Lounge

Lounge occupies the lower-left corner. Its single door opens upwards; the corridor beside the door cell does not provide a second entrance. Its passage leads to Conservatory. Several tokens can share Lounge even though the door's outside corridor square holds only one.

## Dining Room

Dining Room, named `Dining` in the engine, lies on the left between Kitchen and Lounge. It has two doors and no passage. Like Billiard Room, its shorter internal name does not denote a different card.

## Room knowledge and room movement

The [[detective notepad]] locates room cards independently of the board. A token in Kitchen may hold Library, and a suspect summoned into Study may already know Study is outside the envelope. Moving a suspect does not move a card or transfer ownership.[^engine]

For [[Floor player|the floor player]], an unresolved room is a movement target. Once all room cards are located, it targets rooms in its own hand or the envelope, where nobody else can disprove with the room card. The numerical characters use their room probabilities, travel distance and [[personality dials]]. None of these policies turns a room's geographical position into evidence about its card.


## See also

[[Classic board]] · [[Suggestion]] · [[The envelope]] · [[Floor player]]

## References

{{references}}

[^board]: {{cite:docs/board.md|Source and measurement}}
[^doors]: {{cite:docs/board.md|Doors}}
[^engine]: {{cite:clude_core/engine.py|`resolve_suggestion_steps`}}

{{navbox:clude}}
