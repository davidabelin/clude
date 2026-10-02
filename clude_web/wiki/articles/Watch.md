---
title: Watch
short: Stepping through a headless game while its cards stay hidden
categories: The app
redirects: Watch screen
---
**Watch** runs a game of [[clude]]'s headless characters and lets a viewer advance it a turn at a time. It uses the same engine and table driver as other games, with no language-model calls. Hands and the [[envelope]] stay hidden until the finish, so its displays describe reasoning progress without giving away the answer.[^watch]

## Following a game

The Watch form in [[the lobby]] chooses the characters, table size and optional seed. Next turn advances one game turn; Play to the end completes the game. The board shows positions and the record names suggestions and refuters. It does not identify a privately shown card.

Remembering is checked by default, and can be turned off. With it enabled, supported characters load [[method memory]] and save experience at the finish. Watch has no LLM seats, so it does not write model debriefs or provide the conversational personality of a model-piloted table.

## Reading the bars

For each seat, a count such as 9/21 means nine cards have proven locations from that seat's perspective. Its own hand contributes to that count. Category indicators show how many cards are placed and whether the category's envelope card is proven. The pale percentage is the method's confidence in its leading candidate; it can be high before proof.

Displaying all seats' exact known cards would reveal the answer at the deal: their hands together contain every card outside the envelope. Watch therefore shows counts and confidence rather than card identities. The [[certainty tag]] condenses the category confidences into the colour behind the seat's name.

## Restart and replay

A watched table can be rebuilt from its saved setup and progress. A seed suffices only alongside the same configuration, implementation and starting memory. Fresh agents provide the display's belief readings, keeping their random draws separate from the agents choosing moves.

After completion the game is stored in practice and Watch becomes its [[replay]]. Replay reveals the cards and allows event-by-event inspection. Its reconstructed belief trace has its own limits, especially for methods that accumulated state while playing; it is not necessarily the original internal state of every live agent.[^trace]


## See also

[[The lobby]] · [[Replay]] · [[Method memory]] · [[The certainty tag]]

## References

{{references}}

[^watch]: {{cite:docs/web.md|The Watch screen}}
[^trace]: {{cite:clude_web/replay_data.py|`TRACE_LIMITATION` and `belief_trace`}}

{{navbox:clude}}
