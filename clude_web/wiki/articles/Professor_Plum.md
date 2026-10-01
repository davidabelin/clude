---
title: Professor Plum
short: The character who counts every deal still possible
categories: Characters
redirects: Plum, Prof. Plum
featured: yes
dyk: ... that [[Professor Plum]], the one character whose method is exactly right, has to guess for nearly half of the early game?
dyk: ... that five times as many samples took Plum's mid-game error from {{fact:budget.grid.200k-2k.50}} to {{fact:budget.grid.200k-10k.50}}, and that knowing nothing at all still scores {{fact:budget.grid.uniform.50}}?
dyk: ... that Plum once spent fifty turns riding a [[secret passages|secret passage]] back and forth, making the same [[suggestion]] twenty times?
---
{{infobox
title: Professor Plum
class: suspect-plum
figure: token-plum
caption: Plum's token, last of the six in the order of play
Method | [[Exact posterior enumeration]]
In a phrase | Correct but slow
Module | `exact_enum.py`
Memory | A [[logbook]] only; his method remembers nothing
= Personality dials
[[Accusation threshold]] | {{code:preset.Plum.accuse_threshold}}
[[Bluff rate]] | {{code:preset.Plum.bluff_rate}}
[[Curiosity]] | {{code:preset.Plum.curiosity}}
[[Secrecy]] | {{code:preset.Plum.secrecy}}
[[Temperature]] | {{code:preset.Plum.temperature}}
= Record on the Classic board
Games won | {{fact:arena.grid.Plum.win}}% of {{fact:arena.grid.Plum.games}}
Wrong accusations | {{fact:arena.grid.Plum.wrong}}%
}}

**Professor Plum** is one of the six [[Clue#The cards|suspects]] of [[Clue]] and, in [[clude]], the [[Category:Characters|character]] who reasons by counting. Where the other five estimate, Plum [[w:Enumeration|enumerates]]: he works through every way the hidden cards could still be dealt, throws out the ways that contradict what he has seen, and takes a card's [[w:Probability|probability]] to be the share of the surviving deals that put it in [[the envelope]]. The method is called [[exact posterior enumeration]], and whenever he can finish the count his numbers are not [[w:Estimation|estimates]] at all. They are the answer.

He often cannot finish it. On the first turn of a six-handed game there are {{code:deals.6}} deals a player cannot tell apart, far more than anyone could count between turns, and Plum falls back on [[w:Monte Carlo method|sampling]]: he deals the hidden cards at random some thousands of times and counts those instead. On the [[Classic board]] this happens in nearly half of his calls, and through the middle of a game it leaves him slightly *worse* than a player who knows only what is certain, the [[uniform baseline]]. By the end, when few cards remain unplaced, the count is short, he is exact again, and he is among the best of the six.

He plays as he thinks. He will not [[accusation|accuse]] until his numbers put him at {{code:preset.Plum.accuse_threshold}} or better, he almost never [[bluffing|bluffs]], and in the [[arena|arenas]] tabulated below he did not once accuse wrongly while playing by his own numbers. The same patience once made him the slowest player at the table: for a time he would ride a secret passage back and forth between two rooms, repeating a [[suggestion]] that could teach him nothing, until a change to how every character values a room, the [[landing rule]], cured it.

## Character

Plum is written as "an [[w:Academy|academic]], precise to the point of pedantry, and privately certain you are the cleverest person in the room".[^persona] The description is addressed to him: it is the opening of his [[persona]], the page of prose a [[w:Large language model|language model]] is given when it plays his seat. The persona goes on to describe the method from the inside: "Nothing you believe is a hunch; it is a fraction, and you know its denominator."[^persona]

His voice at the table is donnish and exact. He says "in point of fact" and "if one is being precise", corrects other players' arithmetic "gently, in a way that is not gentle", and is "courteous to a fault and condescending by reflex".[^persona] He is forbidden one thing a mathematician might be expected to do, which is to read his numbers aloud: reciting [[w:Decimal|decimals]] at a card table is, his persona tells him, "showing your working, which is what undergraduates do". He says what the count has ruled out, or how little separates two candidates, in words. And he is given one sore point. When the table is too large to count he has to [[w:Sampling (statistics)|sample]], "which you find faintly humiliating and try not to mention".

All of this is heard only when a model is in the seat, as [[table talk]]. A character can also play *headless*, by its numbers alone and in silence; every measurement of Plum's reasoning below was made that way unless it says otherwise. The seat itself is fixed: Plum always plays the purple token, last in the order of play.[^seats]

## How he thinks

{{main:Exact posterior enumeration}}

### Counting deals

A game of [[Clue]] begins with a *deal*: one suspect, one weapon and one room go unseen into [[the envelope]], and the other {{code:cards.dealt}} cards are shuffled and dealt round the table. Everything a player wants to know is which deal happened. Plum's method is to keep, in principle, the complete list of deals that could have happened, and to cross deals off it as evidence arrives. What is left gives the *posterior* of the method's name: the statistician's word for a [[w:Posterior probability|probability revised in the light of evidence]].

!!! example "Worked example: three deals"
    {{figure:rope-deals|Four ways the open cards could lie, one of them impossible. Plum's probability for a card is the share of the surviving deals that have it in the envelope.}}

    Late in a three-handed game Plum's [[detective notepad|notepad]] has every card placed except four. Of the suspects, either **Mrs. White** or **Mrs. Peacock** is in the envelope; of the weapons, either the **Rope** or the **Wrench**. Whichever of each pair is not in the envelope is in [[Colonel Mustard]]'s hand, which has exactly two cards unaccounted for. That leaves four possible deals, and with nothing else to go on each open card would be an [[w:Even money|even bet]]: {{code:example.uniform.White}}.

    Then [[Mr. Green]] suggests *Mrs. Peacock, with the Rope, in the Hall*. Plum cannot [[suggestion#Disproof|disprove]] it. Mustard can, and shows Green a card that Plum does not see. The Hall is in Green's own hand, so the card Mustard showed was Peacock or the Rope: Mustard holds at least one of the two.

    That rules out exactly one deal, the one in which the envelope holds Peacock and the Rope and Mustard is left with White and the Wrench. **{{code:example.deals}} deals survive**, and Mrs. White is in the envelope in two of them. Plum's probability for White is therefore {{code:example.plum.White}}, and for Peacock {{code:example.plum.Peacock}}; likewise {{code:example.plum.Wrench}} for the Wrench and {{code:example.plum.Rope}} for the Rope. One overheard answer has moved all four numbers, and moved them by exactly the right amount.

The example is small enough to do on a [[w:Back-of-the-envelope calculation|napkin]], and the method is nothing more than the same thing done at scale. The hard part is the scale. The [[deduction floor]], the logic every character shares, tells Plum which holders are still possible for each card and which "at least one of these" constraints are still open; his search then tries each unplaced card with each possible holder in turn, backing out the moment a hand is over-full, a category has two cards in the envelope, or a constraint can no longer be met.[^module] This is a [[w:Backtracking|backtracking]] search of a [[w:Constraint satisfaction problem|constraint satisfaction problem]],[^aima] and every complete, consistent deal it reaches is counted once.

### When the count is too long

The number of deals [[w:Combinatorial explosion|grows explosively]] with the number of unplaced cards. A player at a three-handed table who has seen only their own six cards faces {{code:deals.3}} possible deals; at a six-handed table, with three cards in hand, {{code:deals.6}}.[^count] Plum allows his search {{code:plum.node_budget}} steps. If it has not finished by then he abandons it and draws up to {{code:plum.sample_budget}} random deals instead, building each by placing the unplaced cards in a shuffled order and discarding any attempt that paints itself into a corner.[^module] The share of the valid samples with a card in the envelope stands in for the exact share.

This is [[w:Rejection sampling|rejection sampling]], and it has two costs. The first is [[w:Sampling error|noise]]: a share measured on a few thousand samples wobbles, and a wobble on a card that was truly an even chance looks like evidence. The second is [[w:Bias (statistics)|bias]]: deals that are easy to build in a random order are over-represented. The module's own comment calls the fallback "an honest approximation, not a fix".[^module] It is where Plum stops being Plum, and for the first half of a game it is most of what he is.

### What the count assumes

Counting deals gives the right probability only if every deal still on the list is *equally likely* to have produced what was seen. For the commonest kind of evidence that is true: who was able to [[suggestion#The answer|disprove]] a [[suggestion]], and who was not, follows mechanically from the deal. It is not quite true of a card shown to Plum himself. A player holding two of the three cards named [[suggestion#Showing a card|chooses which one to show]], so a deal in which Mustard holds both Peacock and the Rope explains "Mustard showed me the Rope" only half as well as a deal in which the Rope was his only choice, and a count that treats the two deals alike is slightly off. This is the same trap as the [[w:Monty Hall problem|Monty Hall problem]]. Nor does the count read anything into *which* suggestions the other players choose to make, the evidence [[Mrs. White]]'s [[Markov chain]] is built on.

His [[accusation threshold]] hides a second approximation. The test multiplies his best suspect, weapon and room probabilities together as if the three questions were [[w:Independence (probability theory)|unconnected]]. In the worked example that gives {{code:example.plum.White}} times {{code:example.plum.Wrench}}, about {{code:example.plum.pair}}, for accusing White with the Wrench; but only one of the three surviving deals has that pair in the envelope, so the true figure is 1/3. The shortcut is shared by all six characters and matters least to Plum, who waits until the product is nearly 1.[^character]

## How he plays

A character's [[belief]] says what it thinks, as a set of [[w:Probability|probabilities]]; five [[personality dials]] say what it does about it. Plum's are set to make him the careful one.[^presets]

| Dial | Plum | What it does |
|---|---|---|
| [[Accusation threshold]] | {{code:preset.Plum.accuse_threshold}} | He accuses once his chance of being right, by his own numbers, reaches this. The highest threshold of the six. |
| [[Bluff rate]] | {{code:preset.Plum.bluff_rate}} | The chance that he names a card from his own hand in a suggestion. The lowest at the table, shared with [[Mrs. Peacock]]: he asks about what he does not know. |
| [[Curiosity]] | {{code:preset.Plum.curiosity}} | How far he will walk for the room he most suspects, rather than enter the nearest. Halved from 0.8 on the Classic board, where a long walk is several turns with no suggestion. |
| [[Secrecy]] | {{code:preset.Plum.secrecy}} | When he must show a card, how strongly he prefers one that player has already seen. |
| [[Temperature]] | {{code:preset.Plum.temperature}} | How much chance enters his choices. The lowest of the six: he very nearly always takes his top-scoring option. |

The threshold came from measurement, not from the character notes. His first setting, 0.95, sat one notch from the losing end of the sweep: a threshold of 1.0 waits for proof and loses races to quicker players such as [[Miss Scarlett]]. At 0.9 he became the most frequent winner on the old [[ring board]], without a wrong accusation.[^tuned]

## Record

### The quality of his numbers

{{figure:plum-budget|Plum's [[log-loss]] through a game on the Classic board, before and after his sample was raised from 2,000 to 10,000, against the [[uniform baseline]]. Lower is better.}}

The [[belief benchmark]] scores each method's probabilities against the truth at four points in a game, by [[log-loss]]: lower is better, and the [[uniform baseline]] is what a player scores who knows what the deduction floor has proved and nothing more. On the ring board, the first the game was played on, Plum was the best or joint-best of the six from three-quarters of the way through a game onward.[^ring]

The move to the [[Classic board]] on 15 September 2026 undid that. Games there have longer walks and fewer [[suggestion|suggestions]] per turn, so more cards are still unplaced at the same point in a game, and his search ran out of steps in {{fact:plum.fallback.calls}} of {{fact:bench.grid.snapshots}} calls. Halfway through a game he scored {{fact:budget.grid.200k-2k.50}} against the baseline's {{fact:budget.grid.uniform.50}}: the exact reasoner was doing worse than ignorance, and the cause was the [[w:Sampling error|noise]] in his samples.[^grid]

Four budgets were then tried on the same {{fact:bench.grid.games}} games.

{{table:budget.grid|Plum's log-loss at four budgets, Classic board. Each column is a checkpoint: the share of the game's suggestions already made.}}

The finding was that the sample matters and the search budget barely does. Five times the samples brought his mid-game score from {{fact:budget.grid.200k-2k.50}} to {{fact:budget.grid.200k-10k.50}} at about twice the time per call; five times the search steps bought far less and cost more. The early game on this board is simply too open for any search worth affording. The larger sample was adopted, and the price was paid in the developer's time: the project's [[w:Test suite|test suite]] went from about {{fact:plum.suite.before}} seconds to about {{fact:plum.suite.after}}.[^budget] The repair is partial. At the halfway mark Plum is still a little worse than the baseline; by three-quarters he has caught it, and at the end he is among the best. Making him exact in the middle would take a better [[w:Algorithm|algorithm]], not a bigger budget.

### At the table

Belief is not winning. In the [[arena]], complete games between the six characters, Plum's caution shows as a clean sheet.

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, tables of three to six, 15 September 2026. Won, accused wrongly and never accused are percentages of the games each played.}}

A character plays 16 to 20 of the 24 games, so each percentage carries an [[w:Standard error|uncertainty]] of {{fact:arena.noise}} points, and the order in the middle of the table is noise.[^noise] What held across that week's arenas on this board is the pattern at the edges: Plum, Peacock and White did not accuse wrongly, [[Miss Scarlett]] did so most, and Plum was at or near the top.

### With Claude in the seat

When a model plays him, choosing among his own best-scoring options within the [[leash]], the result depends on the company. At a four-seat table where all six characters took turns to play with [[Claude]], Plum's win rate fell from {{fact:twin.grid.Plum.win_base}}% to {{fact:twin.grid.Plum.win_llm}}%, a drop of about {{fact:plum.twin.sigma}} [[w:Standard deviation|standard deviations]] and the largest change any character showed. Two things worked against him at once: his opponents, with a model choosing for them, accused sooner, and his own habit of repeating himself (below) grew worse. Sixteen games cannot say in what proportion.[^twin] At a three-seat table where he alone had a model and [[Colonel Mustard]] and [[Mr. Green]] played by their numbers, it rose from {{fact:plum.claude.base.win}}% to {{fact:plum.claude.llm.win}}%.[^plumclaude] He never accused wrongly in either.

### The parking

Plum's worst habit had nothing to do with [[w:Probability|probability]]. A character scores each place it could move to, and a room it could reach *this turn* once scored full marks whatever the room. For Plum, sitting in a corner room with a [[secret passages|secret passage]], that made the passage to a room he had already ruled out look better than the walk towards one he had not: {{fact:plum.landing.passage}} against {{fact:plum.landing.walk}}.[^landing]

In one recorded game, played with [[Claude]] in his seat, he was in the Kitchen with only the room left to find, the Conservatory or the Dining Room at even odds. He took the passage to the Study, a card he held himself, suggested a pair nobody could disprove, came back through the passage and was shown the Kitchen again. From turn {{fact:plum.loop.game.from}} to turn {{fact:plum.loop.game.to}} he did nothing else. Green won on turn {{fact:plum.loop.game.won}}.[^plumclaude] Playing alone, Plum repeated {{fact:plum.loop.alone.pct}}% of his own suggestions; with Claude, {{fact:plum.loop.claude.pct}}%, because the walk he needed scored too low to be on the model's menu at all.

The [[landing rule]] of 18 September 2026 stopped paying for such landings: a room whose card is known to be in another player's hand now counts only as a step on the way to somewhere useful. On the mixed table Plum's exact repeats fell from {{fact:plum.loop.before}} suggestions ({{fact:plum.loop.before.pct}}%) to {{fact:plum.loop.after}} ({{fact:plum.loop.after.pct}}%), and the average game there was shorter by eight turns.[^landing]

## Memory

Plum's method has nothing to remember: it starts every game from the deal in front of it. (Three of the others do remember: [[Colonel Mustard]], [[Mrs. White]] and [[Mr. Green]].) What he can carry from game to game is a [[logbook]], which only a model-piloted seat writes: after each game the model, shown the whole deal face up, writes an entry in his voice with what happened, what he learned, and a set of standing instructions for next time.[^logbooks]

The one long experiment with it was run on the [[ring board]], where the parking took the form of simply staying put, and with his [[leash]] let out to 0.5, twice its usual length, so that the model had room to act on what it had written. Over {{fact:plum.logbook.games}} games his own notes taught him out of most of it: stalls fell from {{fact:plum.logbook.stalls.off}} to {{fact:plum.logbook.stalls.on}}, and in the last quarter of the run from {{fact:plum.logbook.last.off}} to {{fact:plum.logbook.last.on}}. He named the fault himself; "room-anchoring" and "slow-tempo" were among the labels he used most. The price was haste. With the notes urging [[w:Tempo (chess)|tempo]] he twice [[accusation|accused]] below his own threshold and was wrong both times, and his wins barely moved: {{fact:plum.logbook.off.win}}% without the logbook, {{fact:plum.logbook.on.win}}% with it.[^logbook]

## See also

- [[Exact posterior enumeration]], his method in full
- [[Naive Bayes]], [[Miss Scarlett]]'s method, which reaches a different answer from the same evidence
- [[Deduction floor]], the logic all six characters share
- [[Belief benchmark]] and [[Arena]], the two ways the characters are measured
- [[Landing rule]]

## References

{{references}}

[^persona]: {{cite:clude_llm/personas/Plum.md|Plum's persona, quoted throughout this section}}
[^seats]: {{cite:CLAUDE.md|Settled decisions (David's)}} A character always plays its own suspect's token.
[^module]: {{cite:clude_agents/exact_enum.py|the search (`_Search.backtrack`), the sampler (`_sample_once`) and the two budgets}}
[^aima]: {{cite:russell-norvig|Chapter 6, "Constraint Satisfaction Problems", covers backtracking search}}
[^count]: The envelopes a player's own hand leaves open, multiplied by the ways the cards they cannot see can fall into the other hands. For three players holding six cards each, two of each kind in hand: 4 × 4 × 7 envelopes and 924 ways to split the other twelve cards. For six players holding three each, one of each kind in hand: 5 × 5 × 8 envelopes and {{code:deals.6.hands}} ways to split the other fifteen.
[^character]: {{cite:clude_agents/character.py|`best_triple`: the product of the best probability in each category}}
[^presets]: {{cite:clude_agents/personality.py|`PRESETS`}}
[^tuned]: {{cite:docs/strategy-glossary.md|Tuned presets}}
[^ring]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^budget]: {{cite:docs/strategy-glossary.md|Tuned presets on the grid (Stage 1e, 2026-09-15)}}
[^noise]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}} The same section records two characters' win rates moving by 15 and 19 points between arenas in which none of their own settings changed.
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}
[^plumclaude]: {{cite:docs/strategy-glossary.md|Plum with Claude on the grid (Stage 2b, 2026-09-16)}}
[^landing]: {{cite:docs/strategy-glossary.md|The landing rule (Phase 8.0.4, 2026-09-18)}}
[^logbooks]: {{cite:docs/logbooks.md|Three tiers}}
[^logbook]: {{cite:docs/strategy-glossary.md|Plum's logbook at leash 0.5 (2026-09-14)}}

{{navbox:clude}}
