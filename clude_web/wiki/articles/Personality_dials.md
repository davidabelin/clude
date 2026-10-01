---
title: Personality dials
short: Five numbers that turn a belief into a way of playing
categories: Personality
redirects: Dials, Personality, Presets, Accusation threshold, Accuse threshold, Bluff rate, Curiosity, Secrecy, Temperature
kind: stub
---
The **personality dials** are five numbers that decide what a character does with its [[belief]]. Two characters given identical probabilities will still play differently if their dials differ; the dials are the temperament and the [[Category:Methods|method]] is the mind.[^personality]

| Dial | Decides | Meaning |
|---|---|---|
| **Accusation threshold** | when to [[accusation|accuse]] | The character accuses once its own estimate of being right reaches this. |
| **Bluff rate** | what to [[suggestion|suggest]] | The chance of naming one of its own cards in a suggestion. |
| **Curiosity** | where to move | At 1 it heads for the room it most suspects; at 0 it enters the nearest. |
| **Secrecy** | which card to show | How strongly it prefers to show a card that has been seen before. |
| **Temperature** | all of its choices | How much chance enters a choice; at 0 it always takes its top-scoring option. |

| Character | Accusation threshold | Bluff rate | Curiosity | Secrecy | Temperature |
|---|---|---|---|---|---|
| [[Miss Scarlett]] | {{code:preset.Scarlett.accuse_threshold}} | {{code:preset.Scarlett.bluff_rate}} | {{code:preset.Scarlett.curiosity}} | {{code:preset.Scarlett.secrecy}} | {{code:preset.Scarlett.temperature}} |
| [[Colonel Mustard]] | {{code:preset.Mustard.accuse_threshold}} | {{code:preset.Mustard.bluff_rate}} | {{code:preset.Mustard.curiosity}} | {{code:preset.Mustard.secrecy}} | {{code:preset.Mustard.temperature}} |
| [[Mrs. White]] | {{code:preset.White.accuse_threshold}} | {{code:preset.White.bluff_rate}} | {{code:preset.White.curiosity}} | {{code:preset.White.secrecy}} | {{code:preset.White.temperature}} |
| [[Mr. Green]] | {{code:preset.Green.accuse_threshold}} | {{code:preset.Green.bluff_rate}} | {{code:preset.Green.curiosity}} | {{code:preset.Green.secrecy}} | {{code:preset.Green.temperature}} |
| [[Mrs. Peacock]] | {{code:preset.Peacock.accuse_threshold}} | {{code:preset.Peacock.bluff_rate}} | {{code:preset.Peacock.curiosity}} | {{code:preset.Peacock.secrecy}} | {{code:preset.Peacock.temperature}} |
| [[Professor Plum]] | {{code:preset.Plum.accuse_threshold}} | {{code:preset.Plum.bluff_rate}} | {{code:preset.Plum.curiosity}} | {{code:preset.Plum.secrecy}} | {{code:preset.Plum.temperature}} |

The settings in the second table are the characters' *presets*, read from the code as this page was built. Mrs. Peacock's threshold is applied to her lower bound, the Dempster-Shafer belief, and not to a probability. Each dial will have an article of its own.

## References

{{references}}

[^personality]: {{cite:clude_agents/personality.py|`Profile` and `PRESETS`}}

{{navbox:clude}}
