---
title: Accusation
short: A final claim that wins or eliminates its maker
categories: The game
redirects: Accuse, Accusations
---
An **accusation** names the suspect, weapon and room a player believes are in [[the envelope]]. In [[clude]] it is made at the end of the player's turn and may name any room. The engine checks the entire triple. A correct accusation wins immediately; an incorrect one ends that player's future turns.[^engine]

Waiting can let another player win, while accusing on uncertain evidence risks elimination. Numerical characters use an [[accusation threshold]] to govern this trade-off. Their confidence scores are estimates, not certificates of correctness.

## At the table

Suppose Plum has proved Peacock and Rope are in the envelope but has not distinguished Library from Study. He can accuse Peacock with Rope in Library from anywhere on the board. If Study is the solution room, the accusation is wrong despite the two correct cards. The engine's negative verdict rules out the triple; it does not identify which element failed.

By contrast, a [[suggestion]] asks other players for evidence and must name the room currently occupied. It may deliberately include the player's own cards. It has no elimination penalty, and a disproved suggestion does not remove its maker from play.

| Action | Room restriction | Answer | Consequence |
|---|---|---|---|
| Suggestion | Current room | A private matching card, or no disproof | More evidence |
| Accusation | Any room | Whole triple correct or incorrect | Win or elimination |

## Timing and elimination

The accusation decision follows movement and any suggestion's resolution. A player can use the answer just received, accuse without suggesting, or decline to accuse. There is at most one accusation that turn.[^engine]

After a wrong accusation, the player retains their hand and remains in the disproof order. They must show a matching card when required, including on the next player's turn. Their token also remains on the board and may be summoned by a suggestion. Being eliminated removes decisions on their own turns, not the information other players can obtain from their hand.

The last active player still needs a correct accusation to win. If nobody remains active or the turn cap is reached, the game ends without a winner and reveals the solution.

## The numerical decision

For five of the six characters, the score is the product of the largest card probability in each category. Let $p_s$, $p_w$ and $p_r$ be those suspect, weapon and room probabilities, and $t$ the threshold. The headless character accuses when

$$ p_s p_w p_r \geq t. $$

The product is an approximation to the triple's probability because card categories can be [[independence|dependent]] after evidence. It is not made exact merely by exact marginals. Ties for a category's best card are settled by the fixed card order.[^character]

[[Mrs. Peacock]] instead supplies her Dempster–Shafer belief bounds to the same product calculation. These numbers measure evidence committed to particular cards; their product is still not a guaranteed lower bound on the actual joint event. [[Floor player|The floor player]] takes a different approach and accuses only when its floor has proved all three cards.

## Model discretion

With a model-piloted character, the [[leash]] can make accusation available below the headless threshold and permit waiting above it. It offers only the character's selected triple or a pass, rather than an unrestricted menu of all triples. At zero leash the threshold answer is enforced; with positive leash, a model can exercise discretion.[^menu]

This means a high-confidence display does not ensure an immediate accusation by a model-piloted seat. A fallback returns to the headless threshold decision. [[Twin comparison]] measures how this discretion changes outcomes on paired games.


## See also

[[Suggestion]] · [[The envelope]] · [[Personality dials#Accusation threshold|Accusation threshold]] · [[Leash]]

## References

{{references}}

[^engine]: {{cite:clude_core/engine.py|`game_steps` and `resolve_accusation`}}
[^character]: {{cite:clude_agents/character.py|`best_triple`, `ds_belief_confidence` and `choose_accusation`}}
[^menu]: {{cite:clude_llm/menu.py|`accusation_menu`}}

{{navbox:clude}}
