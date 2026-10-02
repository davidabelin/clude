---
title: Random bot
short: The uninformed player used in early self-play and engine tests
categories: Characters
redirects: RandomBot, The random bot
---
The **random bot** is an uninformed [[Clue]] player used in early self-play and engine tests. It chooses legal movements and matching cards randomly, usually makes a suggestion when in a room, and occasionally accuses a random triple. It ignores its private hand and the suggestion history when selecting questions or accusations.[^bot]

This makes it useful for exercising rules but a weak source of purposeful deduction. [[Floor player|The floor player]] replaced it as the default self-play policy for training and belief evaluation. Historical random-bot results remain a separate measurement regime.

## At the table

A random bot can hold Rope and still name Rope in a suggestion, or visit a room whose card has already been shown many times. Those actions are legal. Its selections do not identify what it suspects, because they are not based on evidence.

Its card disclosure is different: the engine gives it only matching cards, and it selects one of those. Random choice cannot let it deny a mandatory disproof or show a card it does not hold.

## The policy

| Decision | Random-bot choice |
|---|---|
| Movement | Uniform over offered legal destinations |
| Suggestion | With probability {{code:random.suggest}}, name a random suspect and weapon |
| Accusation | With probability {{code:random.accuse}}, name a random suspect, weapon and room |
| Card to show | Uniform over matching cards |

The suggestion probability applies only when the engine asks for a suggestion in a room. The accusation probability applies when asked at the end of its turn. Neither is confidence that a proposed triple is correct. The constants were chosen to exercise test behaviour, not tuned as a playing strategy.[^bot]

The bot samples from the full categories, including held cards and cards already ruled out by evidence. A random accusation can be correct by chance, but most are wrong and eliminate the bot. No knowledge of the envelope improves its choice.

## Measurement role

The early [[belief benchmark]] evaluated methods on random-bot histories. Later [[self-play]] used floor players, whose questions track unresolved cards and whose games end through deduction. Comparing these runs shows that the source of evidence can change a method's apparent quality.[^regime]

For example, [[Mrs. White]] reads patterns in opponents' repeated and changed suggestions. Random choices do not express the purposeful behaviour her interpretation assumes. A poor result in that regime does not by itself establish how she will perform against a more purposeful policy.

## Reproducibility

`RandomBot` draws from the engine's random stream. A seeded run is reproducible with the same policy and setup, but changing a policy can change how many random draws occur before a later die roll. Including a random-bot seat therefore breaks the arena's usual promise that changed profiles share the same dice sequence.[^arena]

That exception matters in a [[twin comparison]] or [[dial sweeps|dial sweep]]. The seed alone is insufficient to guarantee matched dice when a seat consumes the engine's stream for decisions.


## See also

[[Floor player]] · [[Self-play]] · [[Belief benchmark]] · [[Determinism and seeds]]

## References

{{references}}

[^bot]: {{cite:clude_core/bots.py|`RandomBot`}}
[^regime]: {{cite:docs/architecture.md|Self-play regimes: `RandomBot` and `FloorBot` (Phase 5b)}}
[^arena]: {{cite:clude_training/arena.py|random-stream separation}}

{{navbox:clude}}
