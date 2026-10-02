---
title: Suggestion
short: The question a player asks from a room, and what its answer gives away
categories: The game
redirects: Suggest, Disproof, Disprove, Refutation, Refute, Showing a card
dyk: ... that a [[suggestion]] nobody can disprove tells the whole table something, and the player who made it something more?
dyk: ... that in the ring-board bluff-rate sweep, setting the bluff rate to 1 cut the pooled character win rate to about a third of its value at 0?
---
{{hatnote:This article is about the question asked during a turn. For the guess that ends the game, see [[Accusation]].}}

{{infobox
title: Suggestion
Made | From a room, once in a turn
Names | The room itself, any suspect, any weapon
Answered by | The first player, in the order of play, who holds one of the three cards
Answer | One card, shown to the suggester alone
Costs nothing | A wrong suggestion has no penalty
= In clude
Recorded mean | {{fact:landing.suggestions.after}} per game in the mixed-seat landing-rule arena
Time to show a card | 30 seconds at a web table
}}

A **suggestion** in [[Clue]] names a suspect, a weapon and the room occupied by the player's token: for example, "Mrs. Peacock, with the Rope, in the Hall." The other players are asked in order whether they hold any of those [[Clue#The cards|cards]]. The first who does must show one matching card privately to the suggester. Showing a card **disproves** the suggestion; if nobody can show one, it is **undisproved**. An incorrect suggestion carries no penalty, unlike an [[accusation]].[^engine]

Suggestions are the main source of evidence for [[w:Deductive reasoning|deduction]]. Only the suggester sees the shown card, but everyone learns who disproved the suggestion and who was asked without being able to do so. Each player can therefore learn from other players' turns as well as their own. [[clude]]'s [[Category:Methods|methods]] combine those public observations with the evidence available to their own seat.

A suggestion may name cards from the player's own hand. This can isolate an unknown card or conceal which cards the player is investigating. Wikiclude calls this [[bluffing]], although it may be a straightforward information-gathering tactic rather than [[w:Deception|deception]].

## In the rules

A player may make one suggestion in a turn, and only from a room. The room named must be the one the player's token stands in; the suspect and the weapon are free, and may be cards the player holds.[^rules]

**The summons.**
:   The token of the suspect named is moved at once into the room. For an occupied suspect seat, this can undo several turns of walking. After being summoned, a player whose token has been summoned may, on their next turn only, stay where they are and suggest from that room without moving.[^board]

**The answer.**
:   Starting with the next player in the order of play (to the left, at a real table), each player is asked in turn. A player who holds none of the three cards is passed over. The first player who holds one or more of them must show exactly one, to the suggester only, and the asking stops there: players further round the table are not asked at all. A player who has been put out of the game by a wrong accusation keeps their cards and must still answer.[^engine]

**Undisproved.**
:   If every other player is passed over, nobody holds any of the three cards. Each of them is either in [[the envelope]] or in the suggester's own hand.

**Afterwards.**
:   The turn continues with the chance to make an [[accusation]]. A player may not walk back into the room they have just left, so the same suggestion cannot ordinarily be made on consecutive turns.[^board]

The [[w:Cluedo|printed game]] also moves the weapon's piece into the room. clude has no weapon pieces: a weapon is a card and a name.

## At the table

!!! example "Worked example: one suggestion, four points of view"
    {{figure:suggestion-round|Professor Plum's suggestion goes round a table of four. Miss Scarlett is passed over; Colonel Mustard shows a card, which only Plum sees; Mr. Green is never asked.}}

    Four are playing: [[Miss Scarlett]], [[Colonel Mustard]], [[Mr. Green]] and [[Professor Plum]]. On his turn Plum enters the Hall and suggests *Mrs. Peacock, with the Rope, in the Hall*. Peacock's card can be suggested even though she has no seat in this game. In clude, only occupied suspect seats have movable tokens, so no Peacock token is summoned here.

    [[Miss Scarlett]] is next in the order of play. She holds none of the three cards and says so. [[Colonel Mustard]] is next; he holds the Rope, and shows it to Plum, face down to the others. [[Mr. Green]] is not asked.

    **Plum** has learnt a fact: the Rope is Mustard's, and so is not in the envelope. **Scarlett and Green** have learnt something weaker, that Mustard holds Peacock, the Rope or the Hall. **Everyone**, Mustard included, has learnt that Scarlett holds none of the three. **Nobody** has learnt anything about Green's hand. And **Mustard** knows precisely what he has given away, and to whom.

## What a suggestion tells

The answer supplies four kinds of information. The distinction between a player who was passed over and one who was never asked is essential.

| What happened | What every player learns | What only the suggester learns |
|---|---|---|
| A player was passed over | That player holds none of the three cards | |
| A player showed a card | That player holds at least one of the three | Which card it was |
| A player was never asked | Nothing about that player | |
| Nobody could disprove it | No other player holds any of the three: each is in the envelope or in the suggester's hand | Which of the three are in the envelope: all those not in the suggester's own hand |

Three consequences follow.

**Certainties accumulate.** Every "holds none of these" strikes three cards from one hand, and when enough have been struck a card has only one place left to be: the [[w:Process of elimination|process of elimination]]. Following these facts to their conclusions is mechanical, and in clude it is done for every character and every human player by the same piece of logic, the [[deduction floor]]. It is what fills in a player's [[detective notepad]].

**The middle case is where the methods differ.** "At least one of these three" (in logic, a [[w:Logical disjunction|disjunction]]) is not a fact about any single card, and a simple per-card grid does not express the joint constraint. What to believe meanwhile is a matter of judgement, and each character's method is a different judgement: [[Naive Bayes|Miss Scarlett]] marks all three cards down a little; [[Exact posterior enumeration|Professor Plum]] counts the deals in which the statement is true; [[Dempster-Shafer theory|Mrs. Peacock]] assigns evidential mass to the set of possibilities; [[Decision tree|Colonel Mustard]] recalls how such cards turned out in past games; and [[Markov chain|Mrs. White]] attends less to the answer than to the question, on the principle that a player who keeps naming the same card has not yet been shown it.

**An undisproved suggestion excludes every other hand.** Each named card must be in the envelope or the suggester's hand. The suggester knows which of those alternatives applies. Other players may not, especially if the suggestion names cards the suggester holds.

## Choosing what to ask

A suggestion can be used to find out, to confirm, or to mislead, and the same question seldom does all three.

A **non-bluffing** suggestion names a suspect and weapon the player does not hold. If it goes undisproved, the player can identify those cards as belonging to the envelope. Choosing high-probability candidates can help confirm an answer; choosing other unresolved cards may instead help eliminate alternatives. There is no universally best question independent of the position.

A **[[bluffing|bluff]]** names one or more cards from the player's own hand, much as a [[w:Bluff (poker)|bluff at poker]] represents cards the player does not have. Naming two of one's own cards with one unknown turns the suggestion into a precise test: anyone who shows a card can only be showing the third. Naming one narrows the answer to two. A bluff also hides the player's real interest, and if nobody can disprove it the others are left unsure how much has been found.

The room limits the question: a player can ask only about the room they occupy. Investigating the Conservatory therefore requires reaching it. The [[curiosity]] dial governs how a character balances a suspected room against travel distance.

clude's characters choose as follows. When a character is in a room it always suggests. For the suspect, and separately for the weapon, it first tosses a weighted coin, its [[bluff rate]]: on a bluff it names a card of that kind from its own hand, if it has one. Otherwise it picks among the cards it does not hold, favouring those its own [[belief]] rates most likely to be in the envelope, with a little [[w:Randomness|randomness]] set by its [[temperature]].[^character] A person at the table may choose anything, including not to suggest at all.

## Showing a card

A player who holds two or three of the cards named has a choice, and it is the only choice a player ever makes on somebody else's turn. Showing a card the suggester has already seen gives away nothing new; showing a fresh one gives away a card. Each character has a dial for this, [[secrecy]], which is how strongly it prefers a card that this player, or failing that any player, has seen before.[^character]

A player cannot decline to show a matching card. The engine finds the first hand with a match and asks its owner which matching card to show. It does not rely on a player's claim that no match exists. [[Table talk]] can include bluffing or misleading remarks, but the formal disproof is enforced by the engine.[^integrity]

At a web table a person has 30 seconds to choose the card, after which it is chosen for them: the turn belongs to somebody else, who is the one kept waiting.[^timeout]

## In clude

The [[w:Game engine|engine]] records the suggester, the three cards, the refuter if any and the shown card. Each seat's observation contains that history with privately shown cards hidden where appropriate, together with its own hand and the public game information. Methods reason from these seat observations rather than the full hidden deal.[^observation]

On the table screen a suggestion is narrated in a line above the board as it happens and kept in the Record; the card shown appears only to the two players concerned.

### How often

In the recorded [[Classic board]] arena after the landing-rule change, tables of three to six characters averaged {{fact:landing.turns.after}} turns and {{fact:landing.suggestions.after}} suggestions per game. Thus fewer than half the turns included a suggestion; many turns were spent travelling through corridors.[^landing]

Before the change, the corresponding mean was {{fact:landing.suggestions.before}} suggestions. The old movement score rewarded reaching any room, including one whose card was already resolved. [[Professor Plum]] often shuttled through secret passages and repeated answered questions: {{fact:plum.loop.before.pct}}% of his suggestions were exact repeats. The [[landing rule]] changed that incentive. Repeated suggestions became less common, games were shorter, and all games in the comparison ended with a correct accusation.[^landing]

### How much to bluff

The [[bluff rate]] was measured by setting it to the same value for all six characters and playing 48 games at each, on the earlier [[ring board]].

{{table:sweep.bluff|The six characters pooled, against purely logical opponents, with every character's bluff rate set to the same value. Won, accused wrongly and never accused are percentages of the games played.}}

In this sweep, a bluff rate of 0.25 did not reduce the pooled win rate. A rate of 1 reduced it to about a third of the rate at 0.[^sweeps] At 1, characters always attempted to name held suspects and weapons, using unresolved cards only when no held card of that category was available. Even at rate 0, a suggestion may include a held room card because its room is fixed by the token's location. The presets range from {{code:preset.Plum.bluff_rate}} for [[Professor Plum]] and [[Mrs. Peacock]] to {{code:preset.White.bluff_rate}} for [[Mrs. White]].

## See also

- [[Accusation]], the other thing a player can say
- [[Deduction floor]], what follows for certain from a suggestion
- [[Bluffing]]
- [[Detective notepad]]
- [[Naive Bayes]] and [[Exact posterior enumeration]], two readings of the same evidence
- [[w:Cluedo|Cluedo]] on Wikipedia, for the game's rules and history

## References

{{references}}

[^rules]: {{cite:clude_llm/personas/rules.md|the house rules every character is given}}
[^board]: {{cite:docs/board.md|Movement rules}}
[^engine]: {{cite:clude_core/engine.py|`resolve_suggestion`}}
[^character]: {{cite:clude_agents/character.py|the suggestion and card-to-show decisions}}
[^integrity]: {{cite:docs/architecture.md|Reveal integrity and the lying/expulsion house rule}}
[^timeout]: {{cite:clude_web/tables.py|`SHOW_TIMEOUT`}}
[^observation]: {{cite:clude_core/state.py|`ClueObservation`}}
[^landing]: {{cite:docs/strategy-glossary.md|The landing rule (Phase 8.0.4, 2026-09-18)}}
[^sweeps]: {{cite:docs/strategy-glossary.md|Dial sweeps}}

{{navbox:clude}}
