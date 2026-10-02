---
title: Rules of play
short: A complete guide to a game of Clue in clude
categories: The game
redirects: Rules, How to play
dyk: ...that an eliminated [[Clue]] player still has to show matching cards?
---
The **rules of play** in [[clude]] govern a game of [[Clue]] in which players try to identify three hidden cards: a suspect, a weapon and a room. Movement determines where a player can ask a question; the answers reveal which cards are in other hands. The first correct [[accusation]] wins. A wrong accusation ends that player's turns, so a plausible guess has a cost.[^engine]

This article covers the whole game. [[Suggestion]] explains how to read an answer, and [[Classic board]] explains the layout and movement in more detail. The house rules use the classic card set and one die; rules from other editions may differ.

## Before the first turn

The game has three to six players. Each occupies one seat and plays one suspect's token. A token's name identifies its position, not ownership of its suspect card: Scarlett can hold Mustard's card, and Scarlett's card can be the murderer.

The engine randomly selects one card from each category for [[the envelope]], then shuffles and deals the other {{code:cards.dealt}} cards round the table. Hands stay private. Everyone knows the number of cards in each hand. With four players, for example, the first two seats receive five cards each and the other two receive four. Each player can immediately rule out their own cards as the solution.[^setup]

Tokens begin on their marked start squares. Turns begin with the first occupied seat and proceed in seat order, skipping players eliminated by wrong accusations. The engine supplies the die roll; players choose from the legal destinations it offers.

## A turn

1. **Move.** Use the die roll to travel through corridors, enter a room, or take an available secret passage. A token summoned into a room since its last turn may stay there instead.
2. **Suggest, if in a room.** Name any suspect and weapon together with that room. Making a suggestion is optional; it is unavailable in a corridor.
3. **Resolve the suggestion.** The named suspect's occupied token moves into the room. Starting with the next seat, the first other player holding a named card must privately show one matching card. The search then stops.
4. **Accuse or wait.** At the end of the turn, name a suspect, weapon and any room as the proposed solution, or make no accusation. This decision can use the card just shown.[^engine]

A turn allows at most one suggestion and one accusation. An accusation does not require entering the room it names, and a player in a corridor can accuse. Movement and suggestion are separate decisions: entering a room permits a question but does not require one.

## Movement

Corridor steps are horizontal or vertical. Diagonal moves are unavailable. A route cannot visit the same square twice, pass through another token, or finish on an occupied corridor square. Several tokens can share a room.[^board]

The full roll must be used **unless the move enters a room**, which ends it immediately. With a roll of four, a room two steps away is a legal destination; an ordinary corridor square two steps away is not. A room counts as a destination rather than a collection of squares through which the token keeps walking.

A token leaving a room may use any unblocked door but cannot re-enter that same room during the move. The [[Classic board#Secret passages|secret passages]] connect Kitchen with Study and Conservatory with Lounge. Taking one uses the movement decision and places the token in the other room, where it can suggest immediately.

Staying in a room is normally unavailable. An exception applies when somebody else's suggestion has moved the token into that room since its last turn: it may stay and suggest on its next turn. That permission expires at the start of that turn, whether used or declined. Merely naming a suspect already in the room does not renew it. A token with no legal move stays where it is; if it is in a room, it can still suggest.[^board]

## Asking a question

{{figure:suggestion-round|wide|Plum asks about Peacock, Rope and Hall. Scarlett cannot answer, Mustard shows a card privately, and Green is not asked.}}

Suppose Plum is in the Hall and suggests Peacock with the Rope in the Hall. Scarlett sits next and holds none of those cards, so the question passes to Mustard. Mustard holds the Rope and shows it to Plum. The answer proves to Plum that the Rope is outside the envelope. Other players know only that Mustard holds **at least one** of the three named cards. They also know Scarlett holds none of them. Green was never asked, so his silence says nothing about his hand.

If a player holds two or three matching cards, that player chooses which one to show. Showing all of them would reveal more than the rules require. An eliminated player is still included in this process. The engine checks the actual hands: a player cannot refuse to answer, claim to have no matching card, or show an unrelated one.[^engine]

If nobody can answer, every named card not in the suggester's own hand must be in the envelope. The qualification matters: [[bluffing]] can put the suggester's own cards into the question. An unanswered suggestion containing two held cards proves only the third card, not all three.

## Keeping track

The [[detective notepad]] puts cards against possible holders, including the envelope. An exclusion means a holder cannot have a card; a location means its holder is known. A hidden disproof adds a separate fact: one of a set of cards belongs to the answering seat, even when none can yet be identified individually.

The automatic [[deduction floor]] applies these facts and hand sizes to each player's own view. It may narrow another holder without a new card being shown. For example, if Mustard must hold Rope or Hall and Hall is later located in Green's hand, Mustard must hold Rope. The floor's rules are sound but do not exhaust every possible argument, so an unresolved entry does not mean the card is impossible to deduce.[^floor]

[[Table talk]] is different evidence. A claim in conversation is not checked against the deal and may be a joke, bluff or mistake. It does not automatically alter the notepad.

## Winning and elimination

A correct [[accusation]] ends the game immediately and reveals the envelope. A wrong one eliminates its maker from moving, suggesting and accusing. Their cards remain in their hand, and they must still answer other players' suggestions. Their token also remains on the board, so elimination does not remove corridor obstructions.[^engine]

An incorrect triple rules out that combination, not necessarily each of its cards. Peacock, Rope and Hall could be wrong because just the room is wrong. No part of an incorrect accusation is individually certified by that verdict.

If everyone is eliminated, or the configured turn limit is reached, the engine ends the game without a winner and reveals the solution. A player does not win automatically by being the last active seat: a correct accusation is still required.

## Choices that matter

Questions can test cards the player genuinely suspects or use held cards to isolate an unknown one. Re-showing a card can avoid giving an opponent fresh information. Entering a nearby room permits an immediate question; walking towards a more promising one costs turns. These are choices within the rules, explored in [[bluffing]], [[secrecy]] and [[curiosity]].

The numerical characters use [[belief|probability estimates]] and an [[accusation threshold]] to decide when to commit. Their displayed confidence is a method's estimate, usually a product of three card probabilities. It can be wrong, even when it looks decisive. A human player can instead wait for deductions or accept a risk of elimination.


## See also

[[Clue]] · [[Classic board]] · [[Suggestion]] · [[Accusation]] · [[Detective notepad]]

## References

{{references}}

[^engine]: {{cite:clude_core/engine.py|`game_steps`, `resolve_suggestion_steps` and `resolve_accusation`}}
[^setup]: {{cite:clude_core/engine.py|`setup`}}
[^board]: {{cite:docs/board.md|Movement rules}}
[^floor]: {{cite:clude_constraints/propagator.py|`DeductionMask` and propagation rules}}

{{navbox:clude}}
