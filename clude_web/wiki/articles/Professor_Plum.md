---
title: Professor Plum
short: The pedantic character who plays by a network trained in self-play
categories: Characters
redirects: Plum, Prof. Plum
featured: yes
dyk: ... that [[Professor Plum]] was rebuilt in October 2026 on a network trained in {{fact:policy.run.games}}-game runs, and now answers in under a millisecond where his old count took {{fact:bench.policy.PlumOG.ms}} ms?
dyk: ... that Plum's network gets the Rope question backwards, giving Mrs. White {{code:example.policy.White}} where the count gives {{code:example.plum.White}}, yet has the best mid-game estimates of any method on real games?
dyk: ... that the old Plum, now PlumOG, once spent fifty turns riding a [[secret passages|secret passage]] back and forth, making the same [[suggestion]] twenty times?
---
{{infobox
title: Professor Plum
class: suspect-plum
figure: token-plum
caption: Plum's token, last of the six in the order of play
Method | [[Regularised Nash dynamics]], since 5 October 2026
Before that | [[Exact posterior enumeration]], kept as PlumOG
In a phrase | Careful, pedantic, and quick since Phase 12
Module | `deep_nash.py`
Memory | A [[logbook]]; his network's weights are fixed between games
= Personality dials
[[Accusation threshold]] | {{code:preset.Plum.accuse_threshold}}
[[Bluff rate]] | {{code:preset.Plum.bluff_rate}}
[[Curiosity]] | {{code:preset.Plum.curiosity}} (inert for his network)
[[Secrecy]] | {{code:preset.Plum.secrecy}}
[[Temperature]] | {{code:preset.Plum.temperature}}
= Headless, 7 October 2026
Won at his own table | {{fact:arena.policy.own.win}}% of 24
Wrong accusations | {{fact:arena.policy.own.wrong}}%
}}

**Professor Plum** is one of the six [[Clue#The cards|suspects]] in [[Clue]] and the [[clude]] [[Category:Characters|character]] who plays by [[regularised Nash dynamics]]: a small neural network, trained by playing tens of thousands of games, that reads what the [[deduction floor]] has established and estimates which cards are in [[the envelope]], where to go and what to ask. He has played this way since 5 October 2026.[^module]

Until then he played by [[exact posterior enumeration]], counting every deal consistent with the evidence. That method, and the character as he was, are kept as **PlumOG**: not seatable, but preserved in the code, in his archived [[logbook]] and in this encyclopaedia's worked examples. The count was exact when it finished, but on the [[Classic board]] it rarely could mid-game, and it was the slowest and most expensive seat at the table. The network kept everything else about him: his token, his voice, his dials and his place in [[Mr. Green]]'s ensemble.[^plan]

The change made Plum the best reader of the cards from the start of a game to the halfway mark, by the [[belief benchmark]], and a thousand times quicker. It did not make him a better player than PlumOG: he wins a little less at his own table and noticeably less among all six characters. He has made no wrong accusation in any headless arena on record, before the change or since.[^bench][^arenas]

## Character

Plum is written as "an [[w:Academy|academic]], precise to the point of pedantry, and privately certain you are the cleverest person in the room".[^persona] The description is addressed to him: it is the opening of his [[persona]], the page of prose a [[w:Large language model|language model]] is given when it plays his seat. Its account of his thinking was rewritten for the network: "Your probabilities are estimates, not counts of every consistent deal", and he is told never to claim to know a probability's exact denominator, which the old persona had made his boast.[^persona]

His voice did not change. It is donnish and exact, with phrases such as "in point of fact" and "if one is being precise"; he is "courteous by habit and condescending by reflex, without noticing the second thing". The model is told to say what the evidence rules out and permits in words rather than recite decimals: "Showing every calculation at a card table is what undergraduates do, and you were brought up better."[^persona] These are writing instructions for a model playing his seat, not properties of the network.

All of this is heard only when a model is in the seat, as [[table talk]]. A character can also play *headless*, by its numbers alone and in silence; every measurement below was made that way unless it says otherwise. The seat itself is fixed: Plum always plays the purple token, last in the order of play.[^seats]

## How he thinks

{{main:Regularised Nash dynamics}}

{{figure:plum-network|Plum's network. The floor's state enters as numbers; a two-layer trunk feeds four heads (belief, suspect, weapon, value) and a scorer that rates each legal move.}}

On each of his turns the [[deduction floor]] settles what is certain, and Plum's network reads the result as {{code:net.state}} numbers: for every card, where it could still be and how often it has been named and by how many players; for every seat, its hand size; how far the game has run. One pass through the network gives him four answers: his [[belief]] about the envelope, scores for which suspect and which weapon to name, a score for each legal move, and an estimate of how the game is going for him.[^module]

The network learnt all of this. It played {{fact:policy.run.games}} games in each of two training runs, half against copies of itself and half among the other characters, and after every batch it was corrected towards the choices that had gone better than it expected and towards the envelopes that had turned out to be true.[^runs]

A learnt estimate has a learnt estimate's weakness. On the [[Belief#At the table|Rope question]], the small position every method article works through, the count says Mrs. White is in the envelope with probability {{code:example.plum.White}}; the network says {{code:example.policy.White}}. It has read Mr. Green's naming of Mrs. Peacock as evidence *for* her, a habit it seems to have learnt from its games, where the disproof that followed points the other way. On real positions it is the best estimator at the table; on a position that breaks its habits it can be confidently wrong in a way a count never is.

## How he plays

A character's [[belief]] says what it thinks; five [[personality dials]] say what it does about it. Plum's were set for PlumOG to make him the careful one, and kept for the network.[^presets]

| Dial | Plum | What it does |
|---|---|---|
| [[Accusation threshold]] | {{code:preset.Plum.accuse_threshold}} | He accuses once his chance of being right, by his own numbers, reaches this: the highest threshold of the six. |
| [[Bluff rate]] | {{code:preset.Plum.bluff_rate}} | The chance he names a card from his own hand in a suggestion. The lowest at the table, shared with [[Mrs. Peacock]]. |
| [[Curiosity]] | {{code:preset.Plum.curiosity}} | For the other characters, how far they will walk for the room they most suspect. Plum's network scores his moves itself, so for him this dial does nothing. |
| [[Secrecy]] | {{code:preset.Plum.secrecy}} | When he must show a card, how strongly he prefers one that player has already seen. |
| [[Temperature]] | {{code:preset.Plum.temperature}} | How much chance enters his choices. The lowest of the six: he very nearly always takes his top option. |

Two dials were measured again for the network. The threshold was kept because his estimates turned out well calibrated where it matters: whenever his best triple reached {{code:preset.Plum.accuse_threshold}}, it was right, in {{fact:policy.calibration.n}} of {{fact:policy.calibration.n}} positions. Lowering it won a few more games among six characters but brought back wrong accusations.[^dials]

{{table:sweep.policy.accuse|Plum's accusation threshold moved with every other dial and character at its preset, seed 7100: 128 games with Plum seated among six characters, 96 at his own table.}}

The temperature was kept for the same reason: 0.05 was the best or equal best at both tables. The [[leash]], which sets how far a model playing him may stray from his top option, had to change, because the network's scores are spread differently from the count's: at the old setting of 0.25 it would give the model less choice than PlumOG had. A leash of {{fact:policy.leash.match}} gives the same width of choice,[^leash] and a paid ladder with Claude kept it: at 0.25 the model made one wrong accusation in 24 games, at {{code:preset.Plum.leash}} none, with the same wins.[^n6]

## Record

### The quality of his numbers

{{figure:plum-policy-logloss|Plum's network against PlumOG's count and the uniform baseline, by [[log-loss]] at four points of a game. Lower is better.}}

The [[belief benchmark]] scores each method's probabilities against the truth at four points in a game, by [[log-loss]]: lower is better, and the [[uniform baseline]] is what a player scores who knows what the deduction floor has proved and nothing more. Halfway through a game Plum's network scores {{fact:bench.policy.Plum.50}}, against the baseline's {{fact:bench.policy.uniform.50}} and PlumOG's {{fact:bench.policy.PlumOG.50}}: the best of any method, where PlumOG had been worse than knowing nothing.[^bench]

### At the table

{{table:arena.policy|Plum at his own table and among all six characters, 24 games each at seed 7007, beside PlumOG on the same deals in September.}}

At his own table, against [[Colonel Mustard]] and [[Mr. Green]], he wins about half his games, a game fewer than PlumOG on the same deals. Among all six he wins less often: two of sixteen here, and {{fact:policy.six.96}}% over 96 games, against PlumOG's {{fact:arena.policy.og.six.win}}%. The estimated [[w:Standard error|standard error]] of a 24-game percentage is about ten points, so the gap at his own table is noise; the gap among six probably is not.[^arenas]

{{figure:plum-checkpoints|His win rate at his own table through the late stages of both training runs.}}

### With Claude

When [[Claude]] plays his seat at his own table, choosing within a leash of {{code:preset.Plum.leash}}, he wins as often as the network does alone, {{fact:ladder.policy.l35.win}}% of 24 games against the headless {{fact:ladder.policy.headless.win}}%. Paired game by game, the model lost {{fact:policy.llm.lost}} of the network's wins and won {{fact:policy.llm.lost}} others. It departs from the network's top option in {{fact:ladder.policy.l35.deviate}}% of the decisions it is asked to make, four to five times as often as it departed from PlumOG's, and talks about as much as PlumOG did, a median of six remarks a game. With PlumOG the model was worth seventeen points at this table, {{fact:plum.claude.base.win}}% to {{fact:plum.claude.llm.win}}%; the network already plays at that level.[^n6]

A typical game with Claude in his seat costs about \${{fact:cost.seat_game.plum}} at list prices. A long game costs more, because every call carries the game so far: one of the 24 ran {{fact:policy.llm.long.turns}} turns and stopped calling the model at the per-game cap, having spent \${{fact:policy.llm.long.cost}}.[^n6]

## PlumOG

The Plum who played from the first games until 5 October 2026 is kept as **PlumOG**. His method was [[exact posterior enumeration]]: he listed every deal of the cards consistent with what he knew and took each card's share of the surviving deals as its probability. Early positions were too large to list, so he searched for a limited number of steps and fell back on [[w:Monte Carlo method|random sampling]] when the search ran out.[^og]

### Counting deals

!!! example "Worked example: three deals"
    {{figure:rope-deals|Four ways the open cards could lie, one of them impossible. PlumOG's probability for a card was the share of the surviving deals that had it in the envelope.}}

    Late in a three-handed game every card is placed except four. Of the suspects, either **Mrs. White** or **Mrs. Peacock** is in the envelope; of the weapons, either the **Rope** or the **Wrench**. Whichever of each pair is not in the envelope is in [[Colonel Mustard]]'s hand. [[Mr. Green]] suggests *Mrs. Peacock, with the Rope, in the Hall*; Mustard shows him a card nobody else sees. The Hall is Green's own, so Mustard holds Peacock or the Rope.

    That rules out exactly one deal, the one in which the envelope holds Peacock and the Rope. **{{code:example.deals}} deals survive**, and Mrs. White is in the envelope in two of them: {{code:example.plum.White}}. The network, asked the same question, says {{code:example.policy.White}}.

### Why he was replaced

On the ring board he was the best or joint-best reader of the cards from three-quarters of the way through a game. The move to the [[Classic board]] on 15 September 2026 left more possibilities open at each point of a game, and his search ran out of steps in {{fact:plum.fallback.calls}} of {{fact:bench.grid.snapshots}} benchmark calls. Five times as many samples improved his halfway log-loss from {{fact:budget.grid.200k-2k.50}} to {{fact:budget.grid.200k-10k.50}}, but it stayed worse than the uniform baseline's {{fact:budget.grid.uniform.50}}, and a call took {{fact:budget.grid.200k-10k.ms}} ms. Mr. Green, who consults every method before choosing one, paid that cost on every turn.[^grid][^budget]

{{figure:plum-budget|PlumOG's log-loss through a game on the Classic board, before and after his sample was raised from 2,000 to 10,000, against the uniform baseline. Lower is better.}}

### With Claude in the seat

When a model played PlumOG, choosing among his own best options within the [[leash]], the result depended on the company. At a four-seat table where all six characters took turns to play with [[Claude]], his win rate fell from {{fact:twin.grid.Plum.win_base}}% to {{fact:twin.grid.Plum.win_llm}}%, the largest change any character showed, about {{fact:plum.twin.sigma}} [[w:Standard deviation|standard deviations]].[^twin] At a three-seat table where he alone had a model, it rose from {{fact:plum.claude.base.win}}% to {{fact:plum.claude.llm.win}}%.[^plumclaude]

### The parking

An early movement rule gave full marks to any room reachable that turn, whatever its card. From a corner room, a [[secret passages|secret passage]] to a room he had already ruled out could score above a walk towards an unresolved one: {{fact:plum.landing.passage}} against {{fact:plum.landing.walk}}.[^landing]

In one recorded game, with [[Claude]] in his seat, he was in the Kitchen with only the room left to find, the Conservatory or the Dining Room at even odds. He took the passage to the Study, a card he held himself, suggested a pair nobody could disprove, came back through the passage and was shown the Kitchen again. From turn {{fact:plum.loop.game.from}} to turn {{fact:plum.loop.game.to}} he did nothing else, and Green won on turn {{fact:plum.loop.game.won}}.[^plumclaude] Playing alone he repeated {{fact:plum.loop.alone.pct}}% of his own suggestions; with Claude, {{fact:plum.loop.claude.pct}}%. The [[landing rule]] of 18 September 2026 cut his repeats on the mixed table from {{fact:plum.loop.before.pct}}% to {{fact:plum.loop.after.pct}}%.[^landing]

### His logbook

A logbook experiment on the [[ring board]] gave PlumOG's model seat {{fact:plum.logbook.games}} paired games with the leash at 0.5. With logbooks, his stalls fell from {{fact:plum.logbook.stalls.off}} to {{fact:plum.logbook.stalls.on}}, and his entries kept naming "room-anchoring" and "slow-tempo"; he also made two wrong accusations below his threshold while trying to play faster. Win rates changed little: {{fact:plum.logbook.off.win}}% without logbooks and {{fact:plum.logbook.on.win}}% with them.[^logbook]

## Memory

Plum's network does not change between games: what it learnt, it learnt in training. A model playing him can keep a [[logbook]] when memory is enabled, writing an account in his voice, lessons and standing instructions after seeing the completed deal. PlumOG's logbook is archived under his name and the current Plum's starts empty, so the lessons of the old method are not read back by the new one; other characters' notes about "Plum" are about the token, and stay.[^logbooks]

## See also

- [[Regularised Nash dynamics]], his method in full, and [[exact posterior enumeration]], PlumOG's
- [[DeepNash]], the Stratego system his training is adapted from
- [[Naive Bayes]], [[Miss Scarlett]]'s method, which reads the Rope question differently again
- [[Deduction floor]], the logic all six characters share
- [[Belief benchmark]] and [[Arena]], the two ways the characters are measured
- [[Landing rule]]

## References

{{references}}

[^persona]: {{cite:clude_llm/personas/Plum.md|Plum's persona, quoted throughout this section}}
[^seats]: {{cite:CLAUDE.md|Settled decisions (David's)}} A character always plays its own suspect's token.
[^module]: {{cite:clude_agents/deep_nash.py|the encoding, the network and `DeepNashAgent`}}
[^plan]: {{cite:docs/deepnash-plan.md|1. Context}}
[^runs]: {{cite:docs/deepnash-plan.md|The second run, `run2`, and the export (2026-10-06)}}
[^presets]: {{cite:clude_agents/personality.py|`PRESETS` and `PLUM_OG`}}
[^dials]: {{cite:docs/strategy-glossary.md|Dial checks}}
[^leash]: {{cite:docs/strategy-glossary.md|Leash width (the equal-rope match)}}
[^n6]: {{cite:docs/strategy-glossary.md|Plum with Claude, the network (N6)}}
[^bench]: {{cite:docs/strategy-glossary.md|Belief benchmark, the network (N5)}}
[^arenas]: {{cite:docs/strategy-glossary.md|Arenas on the standard seeds}}
[^og]: {{cite:clude_agents/exact_enum.py|the search, the sampler and the two budgets}}
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^budget]: {{cite:docs/strategy-glossary.md|Tuned presets on the grid (Stage 1e, 2026-09-15)}}
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}
[^plumclaude]: {{cite:docs/strategy-glossary.md|Plum with Claude on the grid (Stage 2b, 2026-09-16)}}
[^landing]: {{cite:docs/strategy-glossary.md|The landing rule (Phase 8.0.4, 2026-09-18)}}
[^logbooks]: {{cite:docs/logbooks.md|Three tiers}}
[^logbook]: {{cite:docs/strategy-glossary.md|Plum's logbook at leash 0.5 (2026-09-14)}}

{{navbox:clude}}
