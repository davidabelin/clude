---
title: Replay
short: A finished game inspected event by event with all cards revealed
categories: The app
redirects: Replay screen, Replays
---
**Replay** is [[clude]]'s view of a saved game. It shows the board and events alongside each seat's reconstructed card estimates and deductions, with the true [[envelope]] marked. It is an omniscient post-game view: private hands and refutation cards are visible. The belief trace is rebuilt from each seat's permitted evidence, and is not a recording of every agent's live internal state.[^replay]

## Moving through the record

A game listed in practice or development opens at its run identifier and game index. The slider and step buttons move through the events; arrow keys step, and Home and End jump to the limits. Play or Space starts automatic stepping, with a slower–faster control. Using the scrubber pauses playback.

The page receives the game data once, and the browser redraws the board and panels from it. Stepping through a loaded replay makes no model calls. Its card revelations are for analysis; they were not available to the players at the corresponding point in the live game.

## Proof, estimates and truth

The card strips distinguish three states:

| Display | Meaning from that seat's evidence |
|---|---|
| Solid full-width strip | The deduction floor has proven this card belongs to the envelope |
| Greyed, struck-through card | The floor has proven a player holds it |
| Pale bar | The card is still open; its width shows the method's estimated probability |

A separate red mark identifies the true answer. Thus a large pale bar on the wrong card is a confident error, while a solid strip is a logical conclusion. [[Mrs. Peacock]] uses her conservative confidence convention, explained in [[Dempster-Shafer theory]]. The seat's [[certainty tag]] combines the three category confidences.

## How the trace is reconstructed

Board frames come directly from the [[game records|event record]]. At checkpoints the trace builds a masked observation for each seat and asks a fresh numerical agent for a reading. The enclosing replay can reveal the shown card to the viewer while still masking that card from seats that did not see it.[^trace]

The trace does not restore starting [[method memory]] or call the agents' learning hook, `observe`. It therefore omits remembered tree data, opponent priors and arm records, as well as Green's outcome-feedback updates. White still rebuilds her current-game suggestion chain from the masked history on each call; her learning hook is a no-op. These are reconstructed readings rather than a precise history of the original player's state.

The first request computes a trace and caches it beside the game. Later requests reuse a compatible cached version; an old cache version is rebuilt. This computation can delay the first opening, especially with Plum or Green. It does not retrain a character or replay paid model decisions.

## Using a replay

Replay connects an outcome to the decisions preceding it: a long journey between rooms, a question that reveals little, an early accusation or a repeated suggestion. [[Arena|Arena summaries]] show patterns across games; replay supplies the individual evidence behind a pattern. One interesting game can suggest a hypothesis, but cannot establish how often it occurs.


## See also

[[Game records]] · [[Arena]] · [[Belief benchmark]] · [[Watch]]

## References

{{references}}

[^replay]: {{cite:docs/web.md|The replay screen}}
[^trace]: {{cite:clude_web/replay_data.py|`belief_trace`, `cached_trace` and `TRACE_LIMITATION`}}

{{navbox:clude}}
