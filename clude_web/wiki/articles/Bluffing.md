---
title: Bluffing
short: Using held cards in suggestions to isolate or conceal information
categories: The game
redirects: Bluff, Bluffs
---
**Bluffing** in Wikiclude means making a [[suggestion]] that names a card from the suggester's own hand. This can conceal which cards are being investigated or isolate an unknown card. It need not involve a false statement: a suggestion asks for evidence rather than asserts a solution.

The headless characters' [[bluff rate]] controls the chance of selecting a held suspect or weapon. The room is fixed by the token's location and can be held even when that dial is zero. Conversational bluffing in [[table talk]] is a separate, unchecked activity.[^character]

## Isolating one card

Suppose Plum holds Peacock and Rope and reaches the Hall. He suggests Peacock with Rope in Hall. Nobody else can show the first two cards because Plum has them. A disproof therefore identifies Hall as outside the envelope, while no disproof proves Hall is the solution room.

This question tests one unknown cleanly. Its limitation is geographical: Plum needs to reach Hall before asking it. If he already knows Hall's owner, the same question is unlikely to add anything. Naming held cards does not automatically make a question useful.

## Concealing a question's purpose

An observer who does not know Plum's hand sees three candidates in the suggestion. They cannot tell immediately that Hall is the only card Plum is testing. When no one answers, they also cannot infer that all three cards are in the envelope: some may be in Plum's hand.[^engine]

Bluffing can thus make public patterns harder to interpret. It still produces ordinary formal evidence. Players who pass are known to hold none of the named cards, and the first answerer is known to hold at least one. The [[deduction floor]] uses these facts without judging Plum's intention.

## The numerical dial

The headless character chooses suspect and weapon separately. For a category with at least one held card, it flips a coin with probability $b$, the [[bluff rate]], and on success chooses a held card uniformly. Otherwise it samples a card outside its hand using its [[belief]] and [[softmax and temperature|temperature]].[^character]

At $b=1$, both selected slots use held cards whenever such cards exist. A category with no held cards cannot bluff and uses its ordinary candidate list. At $b=0$, the suspect and weapon choices never use held cards, but the mandatory room can still be held.

The [[arena]] counts suggestions naming **any** held card, including the room. That metric therefore need not be zero at bluff rate zero. It counts questions, not the number of held cards inside them.

## Model-piloted suggestions

The [[LLM wrapper]] exposes held suspect and weapon cards as labelled bluff options when both leash and bluff rate are positive. It does not force the model to use them with the dial's probability. The headless coin flip applies on fallback, while an accepted model reply reflects the model's own selection among allowed options.[^menu]

This difference is visible in [[twin comparison|twin comparisons]]. More verbal confidence or more conversation does not imply more held-card suggestions. A model can prefer apparently plausible candidates and use fewer bluff options than its headless counterpart.

## Recorded sweep

{{table:sweep.bluff|The historical ring-board sweep, pooled over the six characters, reported in Phase 5. Percentages concern complete seat-games; named counts are suggestions per seat-game.}}

The recorded sweep increased own-card naming as the dial rose but did not produce a matching increase in wins. At the extreme, questions often stopped testing new suspect or weapon candidates. The figures describe that board, roster and sweep, not an optimal setting for every player or opponent.[^sweep]


## See also

[[Suggestion]] · [[Personality dials#Bluff rate|Bluff rate]] · [[Table talk]] · [[Dial sweeps]]

## References

{{references}}

[^character]: {{cite:clude_agents/character.py|`_pick_suggestion_card`}}
[^engine]: {{cite:clude_core/engine.py|`resolve_suggestion_steps`}}
[^menu]: {{cite:clude_llm/menu.py|`suggestion_menu`}}
[^sweep]: {{cite:docs/strategy-glossary.md|Dial sweeps}}

{{navbox:clude}}
