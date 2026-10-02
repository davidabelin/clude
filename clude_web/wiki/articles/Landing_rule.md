---
title: Landing rule
short: A movement-score change reducing visits to routinely disproved rooms
categories: Measurement
redirects: The landing rule, Parking, The parking, Passage loop
---
The **landing rule** is a movement-score change adopted on 18 September 2026 to reduce repeated questions in rooms whose cards were already located in opponents' hands. Earlier scoring rewarded every room arrival as equally near a useful question. The revised rule distinguishes a useful destination from a room mainly valuable as a step towards somewhere else.[^record]

It changes the shared feature arithmetic, not the board's legal moves or any character's belief method. Paired headless arenas recorded fewer repeated suggestions and shorter games across three table configurations. Their win rates moved in different directions, so the evidence is stronger for reducing the loop than for improving every character's strength.

## The passage loop

Before the change, a secret passage into a resolved room could score {{fact:plum.landing.passage}} at curiosity 0.5, while a corridor move towards an unresolved room scored {{fact:plum.landing.walk}}. The [[leash]] could then exclude the corridor alternative. Plum repeatedly took a high-scoring passage and received the already known room card in reply.[^record]

A model's remembered instruction to leave the loop could not select an option outside the menu. The fix addressed the scoring incentive so headless as well as model-piloted characters could rank more useful movement differently.

## The revised score

A landing receives proximity 1 when the room remains possible in the method's envelope estimate, or when the floor locates its card in the player's own hand or the envelope. In the latter two cases, nobody else can disprove with the room card, so a suggestion can test the other categories cleanly.[^features]

If the room card is in another hand, the proximity becomes

$$ Q=\frac{1}{1+d}, $$

where $d$ is the distance from that room to the nearest room still given positive envelope probability. Passages count as one step in this distance estimate, and token obstructions are ignored. With no positive-probability room remaining, the implementation returns proximity 1.

The overall movement score still blends this proximity with the information proxy through [[curiosity]]. The rule does not ban a resolved room: it may remain useful as a route, a blocked-turn destination or a question about other cards. A known opponent can also choose a different matching card, so 'routinely disproved' describes an incentive problem rather than a rules certainty.

## Two forms tested

The first trial reduced the reward for every located room, including rooms in the player's own hand and the envelope. It removed repeats in the measured runs but also discouraged useful questions. The retained form restored full proximity for those two useful cases.[^record]

Each form was compared on three paired 24-game arenas, seed 7007: a mixed three-to-six-seat roster, a four-seat roster, and a three-seat `Plum,Mustard,Green` table. The runs used headless characters at the recorded presets. They tested the scoring change directly rather than assuming the model would fix it.

## Recorded results

{{table:landing.repeats|Exact repeats of a seat's own earlier suggestion, baseline to retained rule, across the three recorded Classic-board table configurations. Counts and percentages use suggestions, not games.}}

In the mixed-size comparison, Plum's repeats fell from {{fact:plum.loop.before}} ({{fact:plum.loop.before.pct}}%) to {{fact:plum.loop.after}} ({{fact:plum.loop.after.pct}}%). The denominator also changed because the games and his questions changed. This was not the same fixed set of suggestions scored twice.[^record]

Mean game length there fell from {{fact:landing.turns.before}} to {{fact:landing.turns.after}} turns, and mean suggestions from {{fact:landing.suggestions.before}} to {{fact:landing.suggestions.after}}. Repeats and game length fell in all three configurations; wins did not move consistently in one direction. Every recorded game still ended in a correct accusation.

## Implementation and limits

`_landing_proximity` in `clude_agents.features` supplies the new proximity; `room_features` combines it with each method's room probabilities. The characters' shared decision layer then scores legal moves. Tests and recorded character games were updated when the scoring change was adopted.[^features]

The feature called information is still a room-probability proxy rather than expected entropy reduction. The rule also does not explicitly remember every previous question. It removes a particular incentive for redundant travel without proving that the resulting movement policy is optimal or that no repeat can occur.


## See also

[[Curiosity]] · [[Classic board]] · [[Leash]] · [[Professor Plum#The parking|Plum’s passage behaviour]] · [[Arena]]

## References

{{references}}

[^record]: {{cite:docs/strategy-glossary.md|The landing rule (Phase 8.0.4, 2026-09-18)}}
[^features]: {{cite:clude_agents/features.py|`_landing_proximity` and `room_features`}}

{{navbox:clude}}
