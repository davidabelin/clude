---
title: Floor player
short: The bot that chooses using proven card locations alone
categories: Characters
---
The **floor player** is the `FloorBot` seat used for self-play and as a reference opponent in [[clude]]. It chooses questions and movement from the [[deduction floor]] and accuses only when that floor has proved all three envelope cards. It has no separate probability method, persona or cross-game memory.[^bot]

Its role differs from the [[uniform baseline]], which scores probabilities without playing a game. The floor player makes complete decisions. Its certainty-only accusation policy avoids speculative elimination but can lose to a character that correctly commits sooner.

## At the table

If the floor has located the Hall card in Mustard's hand but not located Library, the floor player targets an unresolved room such as Library. Asking repeatedly in Hall would allow Mustard to keep showing the same room card. Once all room cards are located, the floor player instead seeks a room in its own hand or the envelope, where nobody else can answer with the room card.

This lets it test unknown suspects and weapons even after the room is settled. It is a simple information-seeking policy, not a search for the question with the highest expected information gain.

## Four decisions

| Decision | Policy |
|---|---|
| Move | Enter a target room if possible; otherwise choose a move closest to one |
| Suggest | Randomly name unresolved suspect and weapon cards outside its own hand |
| Accuse | Return the proven envelope, or wait if any category is unresolved |
| Show | Choose uniformly among matching cards |

Movement ties are chosen uniformly. If a suggestion category has no unresolved cards, the bot uses its proven envelope card when available, so that slot cannot be disproved. It otherwise falls back to the category's cards. It always suggests when in a room.[^bot]

Board distances include passages and ignore temporary token obstructions for target ranking. The destinations themselves still come from the engine's legal-move list, so this estimate cannot authorise an illegal route.

## Why it replaced random self-play

[[Random bot|Random bots]] ask questions without pursuing unresolved cards. Their games can accumulate many redundant suggestions while the floor stops improving. The floor player was introduced to generate evidence throughout a game for [[decision tree|Mustard's training]] and the [[belief benchmark]].[^architecture]

Uniform movement was also insufficient: suggestions summon tokens into rooms, so a group could keep asking in a room whose card repeatedly answered them. The target-room policy addresses that feedback. It supplies a useful control, although evidence from its policy may not represent human or model-piloted play.

## Randomness and limitations

The bot can use the engine's random stream or an assigned private stream. Self-play uses the former; arena filler seats use the latter so their choices do not consume random draws reserved for the shared die sequence. These setups have different implications for [[determinism and seeds|paired comparisons]].[^bot]

The floor's inference is incomplete. Waiting for proof can therefore delay an accusation that another method would correctly make from uncertainty or exhaustive reasoning. The bot also lacks deliberate bluffing, disclosure preferences and opponent modelling. These limits make it a reference policy rather than a claim to optimal Clue play.


## See also

[[Deduction floor]] · [[Uniform baseline]] · [[Random bot]] · [[Self-play]]

## References

{{references}}

[^bot]: {{cite:clude_constraints/floor_bot.py|`FloorBot`}}
[^architecture]: {{cite:docs/architecture.md|Self-play regimes: `RandomBot` and `FloorBot` (Phase 5b)}}

{{navbox:clude}}
