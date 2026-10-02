---
title: The table
short: A live game with private hands, legal choices and table talk
categories: The app
redirects: Table, Live table
---
**The table** is [[clude]]'s live game screen. It combines the board, the current legal decision, a player's private hand and [[detective notepad]], the public record and [[table talk]]. A signed-in person who holds no seat can watch the table. The views preserve hidden cards, while the public [[certainty tag]] gives a limited indication of each seat's confidence.[^table]

## A decision at a time

The engine supplies the legal options. A move offers corridor destinations, rooms, staying put and a secret passage where available. A [[suggestion]] chooses a suspect and weapon in the room occupied. When another person names cards in a player's hand, that player chooses which matching card to show. The accusation question allows a pass or an [[accusation]].

The Accuse panel keeps its selections while other activity arrives, but the accusation can be submitted only at the player's accusation decision and requires confirmation. Choosing a card to show can happen on someone else's turn. The decision form is keyed to the pending decision, so a new chat line does not reset selections in an unchanged question.

## Private and public information

A player's hand and shown cards are private. A refutation names its refuter publicly; only the refuter and suggester see the card. The automatic notes show deductions available from that seat's evidence. Typed table talk can be persuasive, mistaken or a [[bluffing|bluff]]; it does not alter the engine's evidence or the obligation to refute.

The roster shows who occupies each token and the certainty colour. Spectators see aggregate deduction progress and confidence, without card identities. Seated players receive their own notes and the public tags rather than the spectators' belief readings. A spectator cannot answer, speak as a seated player or switch that player's autopilot.

In Case-file light and Gaslight dark, the board and decision occupy a stage beside a rail. On a phone the rail uses Talk, Record, Hand and Notes tabs for a seated player. Developer retains the earlier panel layout. [[Looks|The appearance]] changes the presentation, while the engine supplies the same legal game.

## Waiting and autopilot

A human decision normally has {{code:table.timeout}} seconds, or {{code:table.speed_timeout}} in speed mode. Showing a card has at most {{code:table.show_timeout}} seconds. When the deadline is reached, a work request can let the floor stand-in answer; after {{code:table.strikes}} consecutive timed-out turns, autopilot takes over. The player can also switch it on and later take control back. An eliminated person still refutes, with that task handled automatically.[^driver]

These deadlines are advanced by app activity, rather than an independent timer that runs with every browser closed. A restarted process rebuilds the pending game; its waiting clock starts again. The clock is a convenience for keeping a shared table moving, not a tournament timing guarantee.

## Persistence and completion

The registry stores the setup, accepted decisions, chat and model audits. A rebuild deals the same setup and replays saved answers; accepted model answers do not incur a second call. Remembered games also preserve their starting numerical memory snapshot.

A completed game is saved in practice and can be opened in [[replay]]. Remembering model seats may still be writing their [[debrief|debriefs]], which the open table drives as further work. Their cost belongs to the finished game's bill. Ending an unfinished table removes it without creating a completed game record.[^finish]


## See also

[[The lobby]] · [[Detective notepad]] · [[The certainty tag]] · [[A seat over MCP]]

## References

{{references}}

[^table]: {{cite:docs/web.md|A table}}
[^driver]: {{cite:clude_web/tables.py|`decision_timeout`, `Registry.work` and timeout handling}}
[^finish]: {{cite:clude_web/tables.py|`Registry._finish` and debrief work}}

{{navbox:clude}}
