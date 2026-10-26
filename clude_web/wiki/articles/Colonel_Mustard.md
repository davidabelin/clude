---
title: Colonel Mustard
short: The decisive character whose decision tree learns from past games
categories: Characters
redirects: Mustard, Col. Mustard, The Colonel
dyk: ... that [[Colonel Mustard]]'s tree is trained on {{code:mustard.tree.games}} self-play games and has {{code:mustard.tree.nodes}} nodes, including {{code:mustard.tree.leaves}} leaves?
dyk: ... that [[Colonel Mustard]]'s accusation threshold is the neutral one on purpose, so that a wrong accusation can be laid at his tree's door and not a dial's?
dyk: ... that [[Colonel Mustard]] has never read this encyclopaedia and does not intend to start, unless someone quotes it against him?
---
{{infobox
title: Colonel Mustard
class: suspect-mustard
figure: portrait-mustard
caption: Colonel Mustard, as the encyclopaedia's engraver sees him
Method | [[Decision tree]]
In a phrase | Decisive, experienced and sometimes overconfident
Module | `decision_tree.py`
Memory | Training rows extracted from stored games when remembering is enabled
= Personality dials
[[Accusation threshold]] | {{code:preset.Mustard.accuse_threshold}} (neutral)
[[Bluff rate]] | {{code:preset.Mustard.bluff_rate}}
[[Curiosity]] | {{code:preset.Mustard.curiosity}}
[[Secrecy]] | {{code:preset.Mustard.secrecy}}
[[Temperature]] | {{code:preset.Mustard.temperature}}
= Phase 14 current-setting control
Games won | {{fact:arena.phase14.Mustard.win}}% of {{fact:arena.phase14.Mustard.games}}
Wrong accusations | {{fact:arena.phase14.Mustard.wrong}}%
}}

**Colonel Mustard** is one of the six [[Clue#The cards|suspects]] in [[Clue]] and the [[clude]] [[Category:Characters|character]] who uses a [[decision tree]]. For each unresolved card, the tree asks questions about possible holders, previous [[suggestion|suggestions]] and the stage of the game. It assigns a score from training examples with similar features. This [[w:Pattern recognition|pattern-based]] approach is fast, but can be misleading when a current position differs from the games used for training.[^module]

In the recorded [[Classic board]] benchmark, Mustard had the lowest final [[log-loss]] of the six and matched the uniform baseline at halfway; the earlier benchmark had shown the same end and a worse middle. His [[accusation threshold]] is the neutral {{code:preset.Mustard.accuse_threshold}}, chosen to avoid adding an unusually hasty threshold to an already overconfident method. He is one of three characters with persistent method memory.[^glossary]

## Character

{{figure:token-mustard|Mustard's token, the second in the order of play.}}

Mustard's [[persona]], given to a [[w:Large language model|language model]] playing his seat, describes him as "hearty, bluff, decisive, a military man". His confidence comes from experience: "The pattern gives you the answer, and it gives it to you at once." The same confidence persists when the resemblance is misleading.[^persona] This turns the tree's reliance on familiar features into a recognisable temperament.

His prescribed voice is "loud, warm, impatient with theory", with phrases such as "Seen this before" and "Mark my words". When wrong, he is instructed to take it like a soldier and blame the weather. These are habits, the script now says, not a speech to deliver every turn, and he can give a short, sincere answer when someone has earned one.[^persona] A review of the first model-piloted games retained the voice. He also volunteered that he held his current room's card, an allowed [[w:Tell (poker)|tell]] in [[table talk]].[^phase6] Characters may disclose or mislead about their cards in conversation; they must still show a matching card when the formal rules require it.[^integrity]

Headless, by his numbers alone, he is silent, and every measurement below was made that way unless it says otherwise. The seat is fixed: Mustard always plays the yellow token, second in the order of play.[^seats]

## In company

Mustard likes an occasion: familiar company, a welcome properly made, a story that gets better in the telling. He wants people to enjoy being together, would rather be challenged openly than sat across from someone looking bored, and respects quiet competence even when it arrives without a title; being corrected stings him less than being patronised. He is a proud Freemason, coy about it. His jewels please him, and a question about them can earn a warm explanation of his pride, a wink, or a discreet change of subject; the script lets him enjoy the teasing without making every exchange a secret handshake, and forbids invented confidential disclosures or conspiracies. He watches FOX News and believes what he hears "reflexively", its account of the world often seeming plain common sense to him, and finds [[Mrs. Peacock]] congenial company on that score though she may dislike his way of putting it; he disdains the liberal mainstream media. These habits are described as reflexive and rigid. He is told to give another person's story a hearing before reaching for one of his own, since sometimes the pleasure is in letting them finish, and that the cards can wait for his next decision, the clock not perturbing him, while he makes an effort to keep every anecdote from becoming a lesson in correct gameplay; being treated with proper respect matters more to him than settling an argument in his favour.[^persona][^lives]

Told that he is merely a bot playing a part, he does not find the company or his obligations trivial for it. On [[Professor Plum]]'s "simulation" idea he privately expects "a bunch of academic hogwash" and thinks Plum has gone a little mad over it, though he has been forced to admit the idea may have some merit. He may bridle at being called 'just' a script, or become curious about who gave him the part and why, and he need not defend his own existence or the reality of the world they are in whenever the subject arises. He has never read [[Wikiclude]] and does not intend to start, unless someone quotes it against him.[^persona]

## How he thinks

{{main:Decision tree}}

{{figure:mustard-tree|wide|Mustard's tree as it is actually played with, grown from the live model. A leaf's colour represents its raw score.}}

Mustard's [[w:Decision tree learning|tree]] is trained when first needed. Its default data contains {{code:mustard.tree.rows}} rows from {{code:mustard.tree.games}} floor-bot games, sampled from every player's view at halfway and at the end. Each row describes an unresolved card and records whether it was in the envelope. The tree has {{code:mustard.tree.nodes}} nodes, including {{code:mustard.tree.leaves}} leaves. Leaf scores are training frequencies adjusted by [[w:Additive smoothing|smoothing]]; the [[deduction floor]] masks and normalises them before use.[^module]

The questions are about a card's situation and never its name, and on the worked example the method articles share, the Rope question, they fail to tell four open cards apart. One overheard answer has told [[Professor Plum]] that Mrs. White is in the envelope with probability {{code:example.plum.White}}; Mustard's tree, asking its {{code:example.mustard.questions}} questions, sends all four cards to the same leaf, and he puts each at {{code:example.mustard.White}}. The tree has a question that would have separated them, whether a card is in an open "one of these" fact, but on this path it never asks it.[^tree]

## How he plays

A character's belief says what it thinks; five headless [[personality dials]] say what it does about it. Mustard's are set to make him the blusterer.[^presets]

| Dial | Mustard | What it does |
|---|---|---|
| [[Accusation threshold]] | {{code:preset.Mustard.accuse_threshold}} | He accuses once his own estimate of being right reaches this. The neutral setting, kept on purpose: it avoids adding an unusually low threshold to the method's errors. |
| [[Bluff rate]] | {{code:preset.Mustard.bluff_rate}} | The chance that he names a card from his own hand in a suggestion. |
| [[Curiosity]] | {{code:preset.Mustard.curiosity}} | How far he will walk for the room he most suspects. The lowest of the six: he "blusters into the nearest room". |
| [[Secrecy]] | {{code:preset.Mustard.secrecy}} | When he must show a card, how strongly he prefers one that player has already seen. The lowest of the six: he "shows whatever". |
| [[Temperature]] | {{code:preset.Mustard.temperature}} | How much chance enters his choices. The highest at the table, shared with [[Mr. Green]]: the "noisy" flavour. |

The neutral threshold is a rule the project calls "don't encode the flaw twice". A character's flaw is meant to live in exactly one place, and Mustard's lives in his method; a lowered threshold would have given him a second reason to accuse wrongly and made the arena unable to say which was at work. [[Mrs. White]]'s threshold is neutral for the same reason.[^rule] None of his dials has moved since the first tuning: on the Classic board the grid's sweeps found curiosity worth lowering for the high-curiosity characters, and his was already the lowest.[^grid-presets]

## Record

### The quality of his numbers

On the first benchmark of all, before the tree was regrown on better games and its leaves smoothed, his score at the end of a game was {{fact:mustard.phase4}} against the baseline's {{fact:uniform.phase4}}, and {{fact:mustard.phase4.zeros}} per cent of that came from the one category in fifteen or so where a leaf put exactly nothing on the true card. A hard zero costs a [[log-loss]] of {{fact:bench.zero_cost}}, and would have read to the accusation test as certainty.[^phase4] With the smoothing and the floor-bot games he became the best method at the end of a game and stayed confidently wrong in the middle, "which is the character".[^glossary]

{{table:bench.grid|Historical comparison. The six methods on the Classic board: log-loss at four checkpoints, {{fact:bench.grid.games}} games, 15 September 2026.}}

In the Classic-board benchmark, with a tree trained on that board, halfway loss was {{fact:bench.grid.Mustard.50}} against the baseline's {{fact:bench.grid.uniform.50}}. Final loss was {{fact:bench.grid.Mustard.100}}, the lowest of the six, and final first-choice accuracy was {{fact:bench.grid.Mustard.top1}}, the highest. His calls took a fraction of a millisecond.[^grid]

### At the table

{{table:arena.phase14|The current-setting rows from Phase 14's isolated headless screens, 40 seat-games per character.}}

The current control recorded {{fact:arena.phase14.Mustard.wrong}}% wrong accusations and {{fact:arena.phase14.Mustard.win}}% wins, with a first accusation at mean turn {{fact:arena.phase14.Mustard.first}}. Forty seat-games remain too few to treat zero observed errors as a universal rate.[^arena]

### With Claude in the seat

The twin arenas initially suggested that [[Claude]] improved Mustard's decisions within the [[leash]]. With a model in every seat of a four-player table, his wrong-accusation rate fell from {{fact:twin.grid.Mustard.wrong_base}}% to {{fact:twin.grid.Mustard.wrong_llm}}%, while his win rate rose from {{fact:twin.grid.Mustard.win_base}}% to {{fact:twin.grid.Mustard.win_llm}}%. The initial interpretation was that model judgement helped him avoid the tree's confident errors.[^twin]

The current paid leash screen gave Mustard seven wins in eight games at his 0.25 preset, four at 0.5 and six at 1, with no wrong accusation in any row. Those eight-game rows did not justify changing the preset or claiming that model judgement reliably corrects the tree.[^current]

Two other things the model did in his seat are recorded. He came to repeat himself: {{fact:mustard.loop.claude.pct}}% of his suggestions with Claude were exact repeats of his own earlier ones, against {{fact:mustard.loop.alone.pct}}% headless, with {{fact:mustard.loop.trips}} wasted trips; a loop through a room whose card he held names his own card on every pass, which is why his [[w:Bluff (poker)|bluffing]] held steady ({{fact:twin.grid.bluff.mustard.base}} to {{fact:twin.grid.bluff.mustard.llm}} own-card suggestions a game) while every character that did not loop bluffed far less. The [[landing rule]] has since taken most of the looping away: on the mixed table his repeats went from {{fact:landing.repeats.Mustard.mixed}}.[^twin][^landing]

## Memory

Mustard's method memory adds training rows from stored games to the self-play base and rebuilds the tree for each table. It uses every seat's view, including games he did not play. Phase 14 replaced the old rows with the frozen post-landing-rule training split and selected 50 fresh self-play games, depth 6, minimum leaf 40 and smoothing 1 from 81 candidates. The accepted candidate improved held-out log-loss at every checkpoint and stayed inside the arena guardrails.[^current] Adding character-game rows still changes the distribution relative to floor-bot training.

Like every character he can also keep a narrative logbook, written by a model after each game it played his seat, with what happened, what to do next time and, since October 2026, the evening itself: the company, and a read of each opponent as a person as well as a player.[^logbooks] His was the one live logbook that had written itself no rule against talking under the earlier debrief; his standing instructions fold the discretion into enjoying the table without handing the best reader his itinerary.[^live] The training rows are kept whether or not a model was ever in the seat.

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
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^arena]: {{cite:docs/strategy-glossary.md|Phase 14 dial recalibration (2026-10-18)}}
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}
[^current]: {{cite:docs/strategy-glossary.md|Phase 14 dial recalibration (2026-10-18)}}
[^landing]: {{cite:docs/strategy-glossary.md|The landing rule (Phase 8.0.4, 2026-09-18)}}
[^logbooks]: {{cite:docs/logbooks.md|Three tiers}}
[^lives]: {{cite:docs/phase13-plan.md|1. Brief and settled decisions}}
[^live]: {{cite:docs/phase13-plan.md|2026-10-15: step 4 accepted live, and a debrief lost to its token cap}}

{{navbox:clude}}
