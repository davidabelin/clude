---
title: The envelope
short: The three hidden cards that form the solution
categories: The game
redirects: Envelope, The solution, Solution
---
**The envelope** contains the solution to a game of [[Clue]]: one suspect, one weapon and one room selected before [[the deal]]. There are {{code:envelopes}} possible triples, from {{code:cards.suspects}} suspects, {{code:cards.weapons}} weapons and {{code:cards.rooms}} rooms. The other {{code:cards.dealt}} cards belong to players. A correct [[accusation]] identifies the whole triple and wins.[^setup]

Cards remain in their original locations throughout play. A suggestion does not change the envelope, and the suspect whose token is moved need not be its suspect card. The mystery is hidden information about a fixed deal.

## Finding a missing card

Every card located in a hand is excluded from the envelope. If five of the six weapons are located outside it, the remaining weapon is the solution weapon. Its owner is known by elimination even if no question ever named it.

The same rule applies independently to suspects and rooms. Finding the weapon does not automatically identify the other two categories. The [[deduction floor]] records proven envelope cards and uses them to simplify later questions.[^floor]

## An unanswered question

Suppose a player holds Peacock and Rope and suggests those cards in the Hall. If no other player can disprove, Hall must be in the envelope: it is the only named card not accounted for by the suggester's hand. Peacock and Rope remain in that hand. This is a legal use of [[bluffing]], not proof of the named triple.[^suggestion]

If the suggester holds none of the named cards and everyone else passes, all three are in the envelope. Observers who do not know the suggester's hand cannot generally draw that same conclusion. Publicly unanswered does not mean publicly solved.

## Probability of a card and of a triple

Before private evidence, each suspect has probability $1/{{code:cards.suspects}}$, each weapon $1/{{code:cards.weapons}}$ and each room $1/{{code:cards.rooms}}$ of being selected. The initial independent selection makes every full triple equally likely. Evidence from finite hands and hidden answers can make the categories dependent later.

Most characters choose their highest-confidence card in each category and multiply those three numbers for an accusation score. This is a shared approximation to the probability of the whole triple. Even exact individual card probabilities need not give an exact product: [[independence]] explains the difference.[^character]

## At the end of a game

The engine reveals the envelope when a correct accusation ends play, or when play ends without a winner through elimination or a turn cap. A [[The debrief|debrief]] can then compare the character's final estimates with the revealed cards. That post-game view includes information withheld during decisions and does not imply that the character saw the answer beforehand.

The benchmark also uses the true envelope to score earlier private observations. The truth is passed to the scoring code separately from the seat's observation; it is not supplied as input to the belief method.


## See also

[[The deal]] · [[Suggestion]] · [[Accusation]] · [[Belief]] · [[Independence]]

## References

{{references}}

[^setup]: {{cite:clude_core/engine.py|`setup` and `game_steps`}}
[^floor]: {{cite:clude_constraints/propagator.py|envelope category constraints}}
[^suggestion]: {{cite:clude_core/engine.py|`resolve_suggestion_steps`}}
[^character]: {{cite:clude_agents/character.py|`best_triple`}}

{{navbox:clude}}
