---
title: Suggestion
short: The question a player asks from a room, and what its answer gives away
categories: The game
redirects: Suggest, Disproof, Disprove, Refutation, Refute, Showing a card
dyk: ... that a [[suggestion]] nobody can disprove tells the whole table something, and the player who made it something more?
dyk: ... that a character who [[bluffing|bluffs]] in every suggestion wins a third as often as one who never does?
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
Per game | About {{fact:landing.suggestions.after}}, at a table of three to six
Time to show a card | 30 seconds at a web table
}}

A **suggestion** is the question at the heart of [[Clue]], a game of [[w:Deductive reasoning|deduction]]. A player whose token is in a room names that room, a suspect and a weapon, three of the game's [[Clue#The cards|cards]]: *"I suggest it was Mrs. Peacock, with the Rope, in the Hall."* The other players are then asked in turn whether they can **disprove** it. The first who holds one of the three cards named must show one of them, privately, to the player who asked; if nobody holds any, the suggestion stands undisproved. Unlike an [[accusation]], a suggestion risks nothing and may be wrong on purpose.

Almost everything a player learns in a game is learnt this way, and not only by the player who asks. The card that is shown is seen by one person, but who showed it, and who could not, is seen by everyone. A suggestion is therefore a small public [[w:Experiment|experiment]] with a private result, and the skill of the game lies in reading other people's experiments as closely as one's own. Each of [[clude]]'s six [[Category:Characters|characters]] reads them differently: that difference is the six [[Category:Methods|methods]].

Because the question is free, it is also the game's instrument of [[w:Deception|deceit]]. A player may name a card from their own hand, knowing that nobody else can show it, to narrow down the answer or to mislead the table. This is a [[bluffing|bluff]], and clude's characters do it at a measured rate.

## In the rules

A player may make one suggestion in a turn, and only from a room. The room named must be the one the player's token stands in; the suspect and the weapon are free, and may be cards the player holds.[^rules]

**The summons.**
:   The token of the suspect named is moved at once into the room. This is the only way a token moves outside its owner's turn, and it can undo several turns of walking. In compensation, a player whose token has been summoned may, on their next turn only, stay where they are and suggest from that room without moving.[^board]

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

    Four are playing. On his turn [[Professor Plum]] walks into the Hall and suggests *Mrs. Peacock, with the Rope, in the Hall*. Peacock's token, wherever it was, is moved into the Hall.

    [[Miss Scarlett]] is next in the order of play. She holds none of the three cards and says so. [[Colonel Mustard]] is next; he holds the Rope, and shows it to Plum, face down to the others. [[Mr. Green]] is not asked.

    **Plum** has learnt a fact: the Rope is Mustard's, and so is not in the envelope. **Scarlett and Green** have learnt something weaker, that Mustard holds Peacock, the Rope or the Hall. **Everyone**, Mustard included, has learnt that Scarlett holds none of the three. **Nobody** has learnt anything about Green's hand. And **Mustard** knows precisely what he has given away, and to whom.

## What a suggestion tells

The example generalises into four rules, which between them are the whole flow of information in the game.

| What happened | What every player learns | What only the suggester learns |
|---|---|---|
| A player was passed over | That player holds none of the three cards | |
| A player showed a card | That player holds at least one of the three | Which card it was |
| A player was never asked | Nothing about that player | |
| Nobody could disprove it | No other player holds any of the three: each is in the envelope or in the suggester's hand | Which of the three are in the envelope: all those not in the suggester's own hand |

Three consequences follow.

**Certainties accumulate.** Every "holds none of these" strikes three cards from one hand, and when enough have been struck a card has only one place left to be: the [[w:Process of elimination|process of elimination]]. Following these facts to their conclusions is mechanical, and in clude it is done for every character and every human player by the same piece of logic, the [[deduction floor]]. It is what fills in a player's [[detective notepad]].

**The middle case is where the methods differ.** "At least one of these three" (in logic, a [[w:Logical disjunction|disjunction]]) is not a fact about any single card, and no notepad has a box for it. What to believe meanwhile is a matter of judgement, and each character's method is a different judgement: [[Naive Bayes|Miss Scarlett]] marks all three cards down a little; [[Exact posterior enumeration|Professor Plum]] counts the deals in which the statement is true; [[Dempster-Shafer theory|Mrs. Peacock]] holds the statement as it stands and commits to nothing more; [[Decision tree|Colonel Mustard]] recalls how such cards turned out in past games; and [[Markov chain|Mrs. White]] attends less to the answer than to the question, on the principle that a player who keeps naming the same card has not yet been shown it.

**An undisproved suggestion is loud.** It tells the suggester the most, but it tells everybody a great deal: three cards, none of them in four hands. If the suggester has named a card of their own, the rest of the table cannot tell which of the three are the real discovery. If the suggester has not, they have just read out part of the answer.

## Choosing what to ask

A suggestion can be used to find out, to confirm, or to mislead, and the same question seldom does all three.

An **honest** suggestion names cards the player does not hold and thinks likely to be in the envelope. It has the best chance of going undisproved, and tells the player most when it does. It also tells the table what the player suspects.

A **[[bluffing|bluff]]** names one or more cards from the player's own hand, much as a [[w:Bluff (poker)|bluff at poker]] represents cards the player does not have. Naming two of one's own cards with one unknown turns the suggestion into a precise test: anyone who shows a card can only be showing the third. Naming one narrows the answer to two. A bluff also hides the player's real interest, and if nobody can disprove it the others are left unsure how much has been found.

The room is the constraint. A player can only ask about the room they are in, so a suspicion about the Conservatory has to be walked to; how far a character will walk for a room it suspects is its [[curiosity]].

clude's characters choose as follows. When a character is in a room it always suggests. For the suspect, and separately for the weapon, it first tosses a weighted coin, its [[bluff rate]]: on a bluff it names a card of that kind from its own hand, if it has one. Otherwise it picks among the cards it does not hold, favouring those its own [[belief]] rates most likely to be in the envelope, with a little [[w:Randomness|randomness]] set by its [[temperature]].[^character] A person at the table may choose anything, including not to suggest at all.

## Showing a card

A player who holds two or three of the cards named has a choice, and it is the only choice a player ever makes on somebody else's turn. Showing a card the suggester has already seen gives away nothing new; showing a fresh one gives away a card. Each character has a dial for this, [[secrecy]], which is how strongly it prefers a card that this player, or failing that any player, has seen before.[^character]

What a player may *not* do is decline. In clude the question is never put as "can you disprove this?" The engine looks at the hands, finds the first player who holds a matching card, and asks only "which of these will you show?" Characters and people may hint, tease and lie about their cards in [[table talk]] as much as they like; the formal answer to a suggestion is not theirs to falsify.[^integrity]

At a web table a person has 30 seconds to choose the card, after which it is chosen for them: the turn belongs to somebody else, who is the one kept waiting.[^timeout]

## In clude

The [[w:Game engine|engine]] records each suggestion with who made it, the three cards, who disproved it if anyone did, and the card shown. Each player's view of the game contains the whole list, with the card shown blanked out of every suggestion they were not party to. That list, and the player's own hand, is everything a method is given to reason from.[^observation]

On the table screen a suggestion is narrated in a line above the board as it happens and kept in the Record; the card shown appears only to the two players concerned.

### How often

On the [[Classic board]] at a mixed table of three to six characters, a game runs to about {{fact:landing.turns.after}} turns and {{fact:landing.suggestions.after}} suggestions: rather more than half of all turns end in a corridor with no question asked.[^landing]

The figure was once much higher, {{fact:landing.suggestions.before}} a game, and the difference was waste. Characters were being rewarded for reaching any room at all, and some, [[Professor Plum]] above all, took to shuttling between two rooms repeating a suggestion that had already been answered: {{fact:plum.loop.before.pct}}% of his suggestions were exact repeats of his own earlier ones. The [[landing rule]] removed the reward. The suggestions that disappeared were the ones that could teach nothing, and every game still ended in a correct accusation.[^landing]

### How much to bluff

The [[bluff rate]] was measured by setting it to the same value for all six characters and playing 48 games at each, on the earlier [[ring board]].

{{table:sweep.bluff|The six characters pooled, against purely logical opponents, with every character's bluff rate set to the same value. Won, accused wrongly and never accused are percentages of the games played.}}

[[Bluffing]] a quarter of the time cost nothing. Bluffing every time cut the win rate to a third of what it had been: a character that only ever names its own cards never tests the ones it is unsure of.[^sweeps] Even at a bluff rate of zero a character names one of its own cards now and then, since the room is wherever it happens to be standing. The characters' own rates run from {{code:preset.Plum.bluff_rate}} for [[Professor Plum]] and [[Mrs. Peacock]] to {{code:preset.White.bluff_rate}} for [[Mrs. White]].

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
