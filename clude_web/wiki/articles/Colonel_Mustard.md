---
title: Colonel Mustard
short: The character who reasons from the games he has seen
categories: Characters
redirects: Mustard, Col. Mustard, The Colonel
dyk: ... that [[Colonel Mustard]]'s method is a tree of {{code:mustard.tree.nodes}} questions grown from {{code:mustard.tree.games}} games he watched before the first one he played?
dyk: ... that on the ring board [[Colonel Mustard]]'s own method put him out of a third of his games, and that the dial that could have stopped it was left alone on purpose?
---
{{infobox
title: Colonel Mustard
class: suspect-mustard
figure: token-mustard
caption: Mustard's token, the second in the order of play
Method | [[Decision tree]]
In a phrase | Pattern-matches; confidently wrong on unusual deals
Module | `decision_tree.py`
Memory | Every game he has seen played, as training rows for his tree
= Personality dials
[[Accusation threshold]] | {{code:preset.Mustard.accuse_threshold}} (neutral)
[[Bluff rate]] | {{code:preset.Mustard.bluff_rate}}
[[Curiosity]] | {{code:preset.Mustard.curiosity}}
[[Secrecy]] | {{code:preset.Mustard.secrecy}}
[[Temperature]] | {{code:preset.Mustard.temperature}}
= Record on the Classic board
Games won | {{fact:arena.grid.Mustard.win}}% of {{fact:arena.grid.Mustard.games}}
Wrong accusations | {{fact:arena.grid.Mustard.wrong}}%
}}

**Colonel Mustard** is one of the six [[Clue#The cards|suspects]] of [[Clue]] and, in [[clude]], the [[Category:Characters|character]] who reasons from experience. His method is a [[decision tree]] grown from the records of past games: for each card still in doubt it asks a short series of questions (how many players could still hold it, how often it has been named and by how many different players, how far the game has run) and answers with how such cards turned out before. A situation reminds him of the ones that came before it, and the [[w:Pattern recognition|resemblance]] gives him the answer at once, with the confidence that many games give. When a deal is unlike the ones he remembers he does not notice, because the pattern speaks with the same confidence either way.

Measured, that is exactly what happens. On the ring board his [[belief]] was the best of the six at the end of a game and one of the worst in the middle, where a pattern that usually holds was confidently wrong about the deal in front of him; on the [[Classic board]], with a tree grown from games on that board, he matches a purely logical player in the middle and is the best method at the end. His [[accusation threshold]] is the neutral {{code:preset.Mustard.accuse_threshold}} on purpose, so that when he accuses wrongly the fault is the tree's and not a dial's, and on the ring board the tree put him out of a quarter of his games. He is one of three characters whose method itself remembers from game to game.[^glossary]

## Character

Mustard is written as "hearty, bluff, decisive, a military man who has played a great many games of this and remembers most of them."[^persona] The description is addressed to him: it is the opening of his [[persona]], the page of prose a [[w:Large language model|language model]] is given when it plays his seat. The persona describes the method from the inside: "You think by experience. A situation reminds you of the ones that came before it: this many suggestions in, that card named by that many people, the floor closed this far, and you know how those games came out. The pattern gives you the answer, and it gives it to you at once." And it names the flaw as a trait and not an instruction: "when a deal is unlike the ones you remember you do not notice, because the pattern still speaks with the same confidence. You trust it anyway. It has been right before."[^persona]

His voice is "loud, warm, impatient with theory. 'Seen this before.' 'In my experience.' 'Mark my words.'" He calls people by their titles, slaps metaphorical backs, and has "no time for anyone counting on their fingers". The persona gives him one way of losing: "When you are wrong you are magnificently wrong and you take it like a soldier, then blame the weather."[^persona] In the first recorded games with a model in every seat his voice needed no change. He did volunteer, in [[table talk]], that he held the room he was standing in, which the notes record as "a real [[w:Tell (poker)|tell]], in bounds under the over-sharing decision, and exactly the kind of thing the logbooks should punish later".[^phase6] Characters may hint, bluff and give themselves away about their own cards; what they may not do is refuse to show one when the rules require it.[^integrity]

Headless, by his numbers alone, he is silent, and every measurement below was made that way unless it says otherwise. The seat is fixed: Mustard always plays the yellow token, second in the order of play.[^seats]

## How he thinks

{{main:Decision tree}}

{{figure:mustard-tree|wide|Mustard's tree as it is actually played with, grown from the live model. A leaf's colour is how sure it is.}}

Mustard's [[w:Decision tree learning|tree]] is grown, when it is first needed, from {{code:mustard.tree.games}} games played out between purely logical players: one row for every card not yet placed, in every player's view, at the halfway point and at the end of each game, {{code:mustard.tree.rows}} rows in all, labelled with whether the card turned out to be the envelope's. From them the grower finds the {{code:mustard.tree.nodes}} questions that best separate the envelope's cards from the rest, and the {{code:mustard.tree.leaves}} leaves at the ends hold the answers: the share of training cards like this one that were the envelope's, [[w:Additive smoothing|smoothed]] so that no leaf says exactly never.[^module] To form a belief he takes each unplaced card down the tree to its leaf, and the [[deduction floor]] then strikes out whatever it has ruled out.

The questions are about a card's situation and never its name, and on the worked example the method articles share, the Rope question, they fail to tell four open cards apart. One overheard answer has told [[Professor Plum]] that Mrs. White is in the envelope with probability {{code:example.plum.White}}; Mustard's tree, asking its {{code:example.mustard.questions}} questions, sends all four cards to the same leaf, and he puts each at {{code:example.mustard.White}}. The tree has a question that would have separated them, whether a card is in an open "one of these" fact, but on this path it never asks it.[^tree]

## How he plays

A character's belief says what it thinks; five [[personality dials]] say what it does about it. Mustard's are set to make him the blusterer.[^presets]

| Dial | Mustard | What it does |
|---|---|---|
| [[Accusation threshold]] | {{code:preset.Mustard.accuse_threshold}} | He accuses once his own estimate of being right reaches this. The neutral setting, kept on purpose: with the dial neutral, every wrong accusation of his is the tree's. |
| [[Bluff rate]] | {{code:preset.Mustard.bluff_rate}} | The chance that he names a card from his own hand in a suggestion. |
| [[Curiosity]] | {{code:preset.Mustard.curiosity}} | How far he will walk for the room he most suspects. The lowest of the six: he "blusters into the nearest room". |
| [[Secrecy]] | {{code:preset.Mustard.secrecy}} | When he must show a card, how strongly he prefers one that player has already seen. The lowest of the six: he "shows whatever". |
| [[Temperature]] | {{code:preset.Mustard.temperature}} | How much chance enters his choices. The highest at the table, shared with [[Mr. Green]]: the "noisy" flavour. |

The neutral threshold is a rule the project calls "don't encode the flaw twice". A character's flaw is meant to live in exactly one place, and Mustard's lives in his method; a lowered threshold would have given him a second reason to accuse wrongly and made the arena unable to say which was at work. [[Mrs. White]]'s threshold is neutral for the same reason.[^rule] None of his dials has moved since the first tuning: on the Classic board the grid's sweeps found curiosity worth lowering for the high-curiosity characters, and his was already the lowest.[^grid-presets]

## Record

### The quality of his numbers

{{table:bench.ring|The six methods on the ring board, Phase 5: log-loss at four checkpoints. Lower is better.}}

On the first benchmark of all, before the tree was regrown on better games and its leaves smoothed, his score at the end of a game was {{fact:mustard.phase4}} against the baseline's {{fact:uniform.phase4}}, and {{fact:mustard.phase4.zeros}} per cent of that came from the one category in fifteen or so where a leaf put exactly nothing on the true card. A hard zero costs a [[log-loss]] of {{fact:bench.zero_cost}}, and would have read to the accusation test as certainty.[^phase4] With the smoothing and the floor-bot games, on the ring board, he became the best method at the end ({{fact:bench.ring.Mustard.100}}) and stayed confidently wrong in the middle: {{fact:bench.ring.Mustard.50}} and {{fact:bench.ring.Mustard.75}} against the [[uniform baseline]]'s {{fact:bench.ring.uniform.50}} and {{fact:bench.ring.uniform.75}}, "which is the character".[^ring]

{{table:bench.grid|The same benchmark on the Classic board, {{fact:bench.grid.games}} games, 15 September 2026.}}

On the Classic board, with a tree grown from games on that board, he matches the baseline at the halfway mark ({{fact:bench.grid.Mustard.50}} to {{fact:bench.grid.uniform.50}}) and is the best method at the end, {{fact:bench.grid.Mustard.100}}, with the best first choice of the six, {{fact:bench.grid.Mustard.top1}}: "the same method on data that suits it better".[^grid] He answers in a fraction of a millisecond.

### At the table

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, 15 September 2026.}}

The wrong accusations are his record. In the ring board's first arena the tree "eliminated him in a third of his games", {{fact:arena.ring.first.Mustard.wrong}}% wrong, which the notes mark as the character where [[Miss Scarlett]]'s failure to accuse at all was a dial; at the tuned presets, {{fact:arena.ring.Mustard.wrong}}%, with {{fact:arena.ring.Mustard.win}}% won.[^first][^ring-arena] On the Classic board the better-grown tree accuses wrongly in {{fact:arena.grid.Mustard.wrong}}% of his games and wins {{fact:arena.grid.Mustard.win}}%, his first accusation coming at turn {{fact:arena.grid.Mustard.first}}. A character plays 16 to 20 of the 24 games, so each percentage carries a [[w:Standard error|standard error]] of {{fact:arena.noise}} points.[^arena][^grid-presets]

### With Claude in the seat

When a model plays him, choosing among his own best-scoring options within the [[leash]], Mustard looked at first like the character the model rescues. At a four-seat table where every character played with [[Claude]], his wrong accusations fell from {{fact:twin.ring.Mustard.wrong_base}}% to {{fact:twin.ring.Mustard.wrong_llm}}% and his wins tripled, {{fact:twin.ring.Mustard.win_base}}% to {{fact:twin.ring.Mustard.win_llm}}%, on the ring board, and the same again on the Classic board, {{fact:twin.grid.Mustard.wrong_base}}% to {{fact:twin.grid.Mustard.wrong_llm}}% and {{fact:twin.grid.Mustard.win_base}}% to {{fact:twin.grid.Mustard.win_llm}}%. The first reading was that a decision tree that pattern-matches into confident errors is exactly the character an extra layer of judgement can save.[^twin-ring][^twin]

{{table:ladder.mustard|Mustard alone with Claude at four leashes on the ring board, 24 paired games each against the same two headless opponents, 13 September 2026. "Departures" counts the choices on which the model overrode his top option.}}

The ladder that tested it, Mustard alone with a model at a table of two headless characters, did not bear it out. At the preset leash his wrong rate was {{fact:ladder.mustard.0.25.wrong}}% against {{fact:ladder.mustard.headless.wrong}}% without the model, his wins did not move outside noise at any leash, and the model overrode his top option on {{fact:ladder.mustard.1.devs}} of {{fact:ladder.mustard.1.played}} choices even when allowed to play anything. What improved him in the twin run was the table: five other model-piloted seats ending games sooner and cleaner, before his tree had reached a wrong certainty. The notes retire the "rescue" reading in so many words.[^ladder][^glossary]

Two other things the model did in his seat are recorded. He came to repeat himself: {{fact:mustard.loop.claude.pct}}% of his suggestions with Claude were exact repeats of his own earlier ones, against {{fact:mustard.loop.alone.pct}}% headless, with {{fact:mustard.loop.trips}} wasted trips; a loop through a room whose card he held names his own card on every pass, which is why his [[w:Bluff (poker)|bluffing]] held steady ({{fact:twin.grid.bluff.mustard.base}} to {{fact:twin.grid.bluff.mustard.llm}} own-card suggestions a game) while every character that did not loop bluffed far less. The [[landing rule]] has since taken most of the looping away: on the mixed table his repeats went from {{fact:landing.repeats.Mustard.mixed}}.[^twin][^landing]

## Memory

Mustard's method remembers, and his memory is the plainest of the three that do: more rows. With a [[logbook]], rows built from every seat's view of every stored game, at the same two checkpoints his training games were sampled at, are added to the self-play base before his tree is grown, and the tree is grown afresh for him at each table. He learns from games he did not sit in, since a row is a row and the tree wants volume. Rebuilt from {{fact:mustard.memory.games}} stored games, {{fact:mustard.memory.rows}} rows joined the base; scored on {{fact:mustard.memory.held_out}} held-out games, a first and noisy look, his mid-game [[log-loss]] went from {{fact:mustard.memory.mid.before}} to {{fact:mustard.memory.mid.after}} (better) and his end-of-game score from {{fact:mustard.memory.end.before}} to {{fact:mustard.memory.end.after}} (worse). The tree with memory pattern-matches three-seat character games rather than floor-bot self-play, "which is the character"; the fair test, the notes add, is a benchmark on character games, which has not been run.[^memory]

Like every character he can also keep a narrative logbook, written by a model after each game it played his seat, with what happened and what to do next time.[^logbooks] The training rows are kept whether or not a model was ever in the seat.

## See also

- [[Decision tree]], his method in full, with the worked example and the mathematics
- [[Mrs. White]] and [[Mr. Green]], the other two characters whose methods remember
- [[Deduction floor]], whose floor bot played the games his tree was grown from
- [[Logbook]] and [[Leash]]
- [[Belief benchmark]] and [[Arena]]

## References

{{references}}

[^glossary]: {{cite:docs/strategy-glossary.md|Mustard -- Decision tree on game logs}}
[^persona]: {{cite:clude_llm/personas/Mustard.md|Mustard's persona, quoted throughout this section}}
[^phase6]: {{cite:docs/phase6-plan.md|6c, the real backend (2026-09-12; live checks done 2026-09-13)}}
[^integrity]: {{cite:docs/architecture.md|Reveal integrity and the lying/expulsion house rule}}
[^seats]: {{cite:CLAUDE.md|Settled decisions (David's)}} A character always plays its own suspect's token.
[^module]: {{cite:clude_agents/decision_tree.py|the defaults, `_features`, `_build_tree` and `_leaf_value`}}
[^tree]: Computed by walking the live tree with the Rope question's measurements; see [[Decision tree#At the table]].
[^presets]: {{cite:clude_agents/personality.py|`PRESETS`, Mustard's entry and its note}}
[^rule]: {{cite:docs/architecture.md|Personality layer (Phase 5c)}}
[^grid-presets]: {{cite:docs/strategy-glossary.md|Tuned presets on the grid (Stage 1e, 2026-09-15)}}
[^phase4]: {{cite:docs/strategy-glossary.md|Phase 4 benchmark results (RandomBot regime, historical)}}
[^ring]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^first]: {{cite:docs/strategy-glossary.md|Arena, first pass (untuned presets)}}
[^ring-arena]: {{cite:docs/strategy-glossary.md|Arena, tuned presets}}
[^arena]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}
[^twin-ring]: {{cite:docs/strategy-glossary.md|Twin comparison (2026-09-13)}}
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}
[^ladder]: {{cite:docs/strategy-glossary.md|Mustard}} The per-character leash ladder, 2026-09-13.
[^landing]: {{cite:docs/strategy-glossary.md|The landing rule (Phase 8.0.4, 2026-09-18)}}
[^memory]: {{cite:docs/strategy-glossary.md|Phase 7: memory (2026-09-14)}}
[^logbooks]: {{cite:docs/logbooks.md|Three tiers}}

{{navbox:clude}}
