---
title: Miss Scarlett
short: The character who reasons by tally, and accuses first
categories: Characters
redirects: Scarlett, Miss Scarlet, Scarlet
dyk: ... that [[Miss Scarlett]] accuses at a confidence of {{code:preset.Scarlett.accuse_threshold}}, where every other character waits for 0.7 or more, and that her bar has been set three times?
dyk: ... that [[Miss Scarlett]], told the same thing three times, believes it three times as much?
---
{{infobox
title: Miss Scarlett
class: suspect-scarlett
figure: token-scarlett
caption: Scarlett's token, the first in the order of play
Method | [[Naive Bayes]]
In a phrase | Overconfident, accuses early
Module | `naive_bayes.py`
Memory | A [[logbook]] only; her method remembers nothing
= Personality dials
[[Accusation threshold]] | {{code:preset.Scarlett.accuse_threshold}}
[[Bluff rate]] | {{code:preset.Scarlett.bluff_rate}}
[[Curiosity]] | {{code:preset.Scarlett.curiosity}}
[[Secrecy]] | {{code:preset.Scarlett.secrecy}}
[[Temperature]] | {{code:preset.Scarlett.temperature}}
= Record on the Classic board
Games won | {{fact:arena.grid.Scarlett.win}}% of {{fact:arena.grid.Scarlett.games}}
Wrong accusations | {{fact:arena.grid.Scarlett.wrong}}%
}}

**Miss Scarlett** is one of the six [[Clue#The cards|suspects]] of [[Clue]] and, in [[clude]], the [[Category:Characters|character]] who reasons by tally. Her method is [[Naive Bayes]]: every [[suggestion]] she hears nudges the three cards it names up, if nobody could [[suggestion#Disproof|disprove]] it, or down, if somebody did, and she adds up the nudges as though each had nothing to do with the others. It makes her the fastest thinker at the table, since her whole method is a few multiplications, and the most [[w:Overconfidence effect|overconfident]], since the same card in the same hand can answer three suggestions and she counts it three times.

She plays as she thinks. Her [[accusation threshold]] is {{code:preset.Scarlett.accuse_threshold}}, where the other five wait for 0.7 to 0.9, so she [[accusation|accuses]] on a third of the confidence anyone else would need; and because her numbers run ahead of the evidence, she makes more wrong accusations than any other character, on both [[Classic board|boards]] the game has been played on. The project's notes are careful about where that comes from: "the dial supplies 'early', the belief supplies 'wrong'". Repairing her arithmetic "would make her a different character".[^tuned]

Her [[belief]], measured against the truth, is a little worse than that of a player who knows only what is logically certain, at every stage of a game, and her first choice of card is nonetheless right a little more often than that player's. Among the six she is the reminder that confidence and accuracy are different things.

## Character

Scarlett is written as "quick, glamorous, and entirely sure of yourself. You came to win, and you would rather be first than careful."[^persona] The description is addressed to her: it is the opening of her [[persona]], the page of prose a [[w:Large language model|language model]] is given when it plays her seat. The persona describes the method from the inside, as a way of thinking rather than a rule: "You think in tallies. Every suggestion that nobody answers nudges its three cards up in your mind; every card someone shows nudges one down; and you add up the nudges as if each one had nothing to do with the others." And it names the flaw without instructing her to have it: "your certainty has a way of running ahead of the evidence without your noticing. When your numbers say a thing, you believe them."[^persona]

Her voice at the table is "poised, amused, a little cutting. Short sentences." She pays compliments with an edge on them, flirts with the table when she is winning and needles it when she is not, and "never explain[s] her arithmetic; you announce conclusions". She is given no sore point and no hedge: "if you are wrong you are wrong out loud, and you would do it again."[^persona] When the first recorded games with a model in every seat were read for how each voice had survived, hers needed no change; she had explained her arithmetic once in five lines, which her persona already forbids, and one line was judged too thin to tune on.[^phase6]

The persona is written to one rule, shared by all six: do not encode the flaw twice. Scarlett's early accusations come from her threshold and her method; the persona says she is sure of herself, not that she should accuse early.[^wrapper] All of this is heard only when a model is in the seat, as [[table talk]]. Headless, by her numbers alone, she is silent, and every measurement below was made that way unless it says otherwise. The seat is fixed: Scarlett always plays the red token and moves first.[^seats]

## How she thinks

{{main:Naive Bayes}}

{{figure:rope-bars|Scarlett's probability that Mrs. White is in the envelope as the same fact reaches her once, twice and three times. The dashed line is the exact answer, which the second and third hearings do not change.}}

Scarlett starts every one of the {{code:cards.total}} cards at a score of 1 and reads through every suggestion made so far. One that nobody could disprove multiplies the score of each card it named by {{code:scarlett.boost}}; one that somebody disproved with a card she did not see multiplies each by {{code:scarlett.decay}}; one whose shown card she saw changes nothing, because the [[deduction floor]] records that card as a fact. The scores are then turned into probabilities within each category, after the floor has struck out every card it has ruled out of the envelope. Nothing is carried from one call to the next and nothing from one game to the next.[^module]

The worked example at [[Naive Bayes#At the table|Naive Bayes]] shows the method hearing one fact three times. Late in a three-handed game, with Mrs. White or Mrs. Peacock in the envelope, Mr. Green suggests Peacock and the Rope and Colonel Mustard shows him a card. Scarlett marks Peacock and the Rope down and Mrs. White rises to {{code:example.scarlett.1.White}}. [[Professor Plum]], counting the deals still possible, puts her at {{code:example.plum.White}} and stays there however often the same question is asked. Scarlett does not: when Green asks again she is at {{code:example.scarlett.2.White}}, and a third time at {{code:example.scarlett.3.White}}, ten points past the right answer and still climbing, with her figure for the pair she would accuse at {{code:example.scarlett.3.pair}}, twice her threshold. One card in Mustard's hand explains everything she has heard.[^module]

The assumption behind the multiplication, that each piece of evidence is [[w:Conditional independence|independent]] of every other given the truth, is what the word "naive" means in the method's name, and it is false at a card table in exactly the way the example shows. Outside clude the same method [[w:Naive Bayes spam filtering|sorts spam from real mail]], and is known there for the same two traits: good at picking the right answer, poor at saying how sure to be.[^domingos]

## How she plays

A character's belief says what it thinks; five [[personality dials]] say what it does about it. Scarlett's are set to make her the hasty one.[^presets]

| Dial | Scarlett | What it does |
|---|---|---|
| [[Accusation threshold]] | {{code:preset.Scarlett.accuse_threshold}} | She accuses once her own estimate of being right reaches this. The lowest at the table by a distance; the next lowest is [[Mrs. Peacock]]'s 0.7, applied to a stricter number. |
| [[Bluff rate]] | {{code:preset.Scarlett.bluff_rate}} | The chance that she names a card from her own hand in a suggestion. |
| [[Curiosity]] | {{code:preset.Scarlett.curiosity}} | How far she will walk for the room she most suspects rather than enter the nearest. Second-highest of the six. |
| [[Secrecy]] | {{code:preset.Scarlett.secrecy}} | When she must show a card, how strongly she prefers one that player has already seen. |
| [[Temperature]] | {{code:preset.Scarlett.temperature}} | How much chance enters her choices. |

The threshold has been set three times, and its history is most of her record. The first pass gave her 0.5, meant to be low; on the ring board, where games were short, her tally reached even that so seldom that she accused in one game of twenty and never won. In the sweeps that moved every character's threshold together she reached a bar of 0.2 in only {{fact:scarlett.ring.accused_in}} games, the others ending the game before she got there, so she was given arenas of her own with only her dial moved: 0.3 won nothing, 0.2 and 0.15 were within noise of each other, and 0.15 was adopted as the lower bar, since the flavour asked for "early".[^tuned] On the Classic board, where games run forty turns and more, the question was asked again.

{{table:scarlett.threshold|Scarlett over three arenas of 24 games on the Classic board, with only her accusation threshold changed, 15 September 2026.}}

At 0.3 she won three times as often as at 0.15, at a lower wrong rate, because the longer game gives her tally time to be right before it reaches the bar. She still accuses in nearly half her games and is still wrong about half the times she does, just later. The threshold became {{code:preset.Scarlett.accuse_threshold}}.[^grid-presets] Her curiosity was tried at 0.5 and 0.3 the same day and the results, {{fact:curiosity.grid.0.5.scarlett}} and {{fact:curiosity.grid.0.3.scarlett}} for won, wrong and never accused, were "noise around a losing position"; it stands at {{code:preset.Scarlett.curiosity}}.[^grid-presets]

## Record

### The quality of her numbers

{{figure:scarlett-bench|Scarlett's log-loss through a game on the Classic board, against the uniform baseline. Lower is better.}}

The [[belief benchmark]] scores each method's probabilities against the truth at four points in a game by [[log-loss]], against the [[uniform baseline]], the score of a player who believes what the deduction floor has proved and spreads the rest evenly.

{{table:bench.grid|The six methods on the Classic board: log-loss at four checkpoints, {{fact:bench.grid.games}} games, 15 September 2026.}}

Scarlett trails the baseline at every checkpoint on the Classic board, by a little, as she did on the ring, where she was for a time the only method that did.[^ring] Every adjustment she makes to the floor's even spread costs her on average more than it gains, because most suggestions in a real game are disproved and her cruder factor is applied over and over to overlapping sets of cards. Her first choice in each category at the end of a game is nonetheless right {{fact:bench.grid.Scarlett.top1}} of the time against the baseline's {{fact:bench.grid.uniform.top1}}: her ranking of the cards is a little better than ignorance while her probabilities are worse, the usual finding about her method.[^grid][^domingos] And she is fast, answering in a fraction of a millisecond where [[Professor Plum]] takes half a second.

### At the table

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, tables of three to six, 15 September 2026.}}

On the ring board, at the tuned presets, she won {{fact:arena.ring.Scarlett.win}}% of her games and accused wrongly in {{fact:arena.ring.Scarlett.wrong}}%, last on the one count and first on the other, which the notes record as the flavour: "overconfident, early, usually wrong, occasionally first".[^ring-arena] On the Classic board at the raised threshold she won {{fact:arena.grid.Scarlett.win}}% and was wrong in {{fact:arena.grid.Scarlett.wrong}}%, still the most wrong accusations at the table but no longer "both the least successful and the most reckless seat".[^arena] Her first accusation came at turn {{fact:arena.grid.Scarlett.first}}, later than four of the other five: the raised bar is why. A character plays 16 to 20 of the 24 games, so each percentage carries a [[w:Standard error|standard error]] of {{fact:arena.noise}} points.[^grid-presets]

The [[landing rule]] took her exact repeats of her own earlier suggestions on the mixed table from {{fact:landing.repeats.Scarlett.mixed}}.[^landing]

### With Claude in the seat

When a model plays her, choosing among her own best-scoring options within the [[leash]], she is the character who changes least. At a four-seat table where every character played with [[Claude]], her wins were unchanged on both boards, {{fact:twin.ring.Scarlett.win_base}}% on the ring and {{fact:twin.grid.Scarlett.win_base}}% on the Classic board, and her wrong accusations moved within noise, {{fact:twin.ring.Scarlett.wrong_base}}% to {{fact:twin.ring.Scarlett.wrong_llm}}% and {{fact:twin.grid.Scarlett.wrong_base}}% to {{fact:twin.grid.Scarlett.wrong_llm}}%. The one thing the model did differently was [[w:Bluff (poker)|bluff]] less: her suggestions naming a card of her own fell from {{fact:twin.ring.bluff.scarlett.base}} a game to {{fact:twin.ring.bluff.scarlett.llm}} on the ring and from {{fact:twin.grid.bluff.scarlett.base}} to {{fact:twin.grid.bluff.scarlett.llm}} on the Classic board, which was true of every character that does not loop. The model treats naming its own card as a wasted question rather than a feint.[^twin-ring][^twin]

## Memory

Scarlett's method has nothing to remember: it starts every game from the deal in front of it and reads the whole history of suggestions afresh on every call. What she can carry from game to game is a [[logbook]], which only a model-piloted seat writes: after each game the model, shown the whole deal face up, writes an entry in her voice with what happened, what she learned, and a set of standing instructions for next time.[^logbooks] No long experiment with her logbook has been run; the one that has, with [[Professor Plum]]'s, is described on his page.

## See also

- [[Naive Bayes]], her method in full, with the worked example and the mathematics
- [[Professor Plum]] and [[Exact posterior enumeration]], which get the worked example right
- [[Mrs. Peacock]], the character at the other end of the caution scale
- [[Accusation]] and [[Accusation threshold]]
- [[Belief benchmark]] and [[Arena]]

## References

{{references}}

[^tuned]: {{cite:docs/strategy-glossary.md|Tuned presets}}
[^persona]: {{cite:clude_llm/personas/Scarlett.md|Scarlett's persona, quoted throughout this section}}
[^phase6]: {{cite:docs/phase6-plan.md|6c, the real backend (2026-09-12; live checks done 2026-09-13)}}
[^wrapper]: {{cite:docs/llm-wrapper.md|Personas}}
[^seats]: {{cite:CLAUDE.md|Settled decisions (David's)}} A character always plays its own suspect's token.
[^module]: {{cite:clude_agents/naive_bayes.py|the two factors and `NaiveBayesAgent.select_action`}}
[^domingos]: {{cite:domingos-pazzani}}
[^presets]: {{cite:clude_agents/personality.py|`PRESETS`}}
[^grid-presets]: {{cite:docs/strategy-glossary.md|Tuned presets on the grid (Stage 1e, 2026-09-15)}}
[^ring]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^ring-arena]: {{cite:docs/strategy-glossary.md|Arena, tuned presets}}
[^arena]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}
[^landing]: {{cite:docs/strategy-glossary.md|The landing rule (Phase 8.0.4, 2026-09-18)}}
[^twin-ring]: {{cite:docs/strategy-glossary.md|Twin comparison (2026-09-13)}}
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}
[^logbooks]: {{cite:docs/logbooks.md|Three tiers}}

{{navbox:clude}}
