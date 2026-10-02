---
title: Clue
short: The hidden-card deduction game played in clude
categories: The game
redirects: Cluedo, The game, Suspects weapons and rooms, The cards, Cards
---
**Clue**, also known as [[w:Cluedo|Cluedo]], is a board game in which players deduce a hidden suspect, weapon and room. The three solution cards are placed in [[the envelope]], and the others are dealt to the players. Questions called [[suggestion|suggestions]] reveal cards that cannot be the solution. The first correct [[accusation]] wins; a wrong one eliminates its maker from further turns.

[[clude]] plays with the classic set of {{code:cards.total}} cards, three to six seats and the [[Classic board]]. Its rules use one die and private disproofs. The six suspect tokens can be played by people, numerical characters or chat agents. The mystery's story supplies the names; the problem is to find the three cards missing from all the hands.[^domain]

## The cards

| Kind | Cards |
|---|---|
| Suspects ({{code:cards.suspects}}) | [[Miss Scarlett]], [[Colonel Mustard]], [[Mrs. White]], [[Mr. Green]], [[Mrs. Peacock]], [[Professor Plum]] |
| Weapons ({{code:cards.weapons}}) | Candlestick, Knife, Lead Pipe, Revolver, Rope, Wrench |
| Rooms ({{code:cards.rooms}}) | Kitchen, Ballroom, Conservatory, Billiard Room, Library, Study, Hall, Lounge, Dining Room |

Each card occurs once. Its location is either a player's hand or the envelope. A suspect card does not belong automatically to the player with the matching token. A weapon card is evidence rather than a piece moved around this implementation's board. All six suspect cards remain in play even when fewer than six tokens occupy seats.[^domain]

The engine abbreviates Billiard Room and Dining Room to Billiard and Dining and writes Lead Pipe as `Lead_Pipe` internally. These are names for the same cards, not extra cards.

## At the table

{{main:Rules of play}}

A player moves into a room and proposes a suspect and weapon there. Other players are asked in order until one can show a matching card. Only the person who asked sees which card was shown; everyone sees who answered and who could not. Thus a single question produces different information for different seats.[^engine]

Suppose Scarlett shows Plum the Knife. Plum now knows the Knife cannot be in the envelope. Green, who watched the exchange, knows Scarlett held something in Plum's three-card suggestion but may not know which card. Their [[detective notepad|notepads]] should differ. Later questions and hand-size constraints may let Green identify the Knife without seeing it himself.

## Movement and information

The [[Classic board]] has nine rooms separated by corridors. A suggestion must name the room the token currently occupies. A promising room can therefore be several turns away. [[Secret passages]] join opposite corners and let a player ask in the destination room immediately.

An [[accusation]] is different: it may name any room and is checked against the entire envelope. Being in the Hall does not prevent accusing a crime in the Study. This distinction makes movement a way to obtain evidence rather than a requirement for submitting the answer.

## Reasoning in clude

Every numerical character shares the [[deduction floor]], which tracks conclusions compelled by that seat's evidence. Their separate [[Category:Methods|methods]] estimate probabilities where the floor leaves uncertainty. [[Professor Plum]] counts consistent deals when his search completes; [[Miss Scarlett]] uses repeated heuristic updates; other characters model evidence, learned patterns or opponents' behaviour.

Two players can disagree because they have different private evidence, different reasoning methods, or both. An apparently confident character is not necessarily correct. [[Personality dials]] then turn a character's estimates into decisions about movement, questions, disclosure and accusation timing.

## Scope of these rules

Physical editions differ in their cards, dice and additional rules. The [[rules of play]] article describes clude's engine. It does not assume that every edition called Clue uses this board or the same movement rules.[^board]

The implementation enforces legal moves and matching-card disclosures. Conversation remains unchecked, and players may use [[bluffing]] or [[table talk]] to obscure their intentions. Such claims are not added to the deduction floor as facts.


## See also

[[Rules of play]] · [[The deal]] · [[The envelope]] · [[Classic board]] · [[Rooms]]

## References

{{references}}

[^domain]: {{cite:clude_core/domain.py|`SUSPECTS`, `WEAPONS` and `ROOMS`}}
[^engine]: {{cite:clude_core/engine.py|`resolve_suggestion_steps`}}
[^board]: {{cite:docs/board.md|Movement rules}}

{{navbox:clude}}
