---
title: Mr. Green
short: The character who trusts whichever method has been doing best
categories: Characters
redirects: Green, Reverend Green, Rev. Green
dyk: ... that [[Mr. Green]] once won no games at all in an arena of sixteen and then {{fact:green.confirm.win}}% of the very same deals with nothing of his changed?
dyk: ... that [[Mr. Green]] is as slow as the other five methods put together, because he asks every one of them on every turn?
---
{{infobox
title: Mr. Green
class: suspect-green
figure: token-green
caption: Green's token, the fourth in the order of play
Method | [[Bandit ensemble]]
In a phrase | Opportunistic; only as good as the method he is trusting
Module | `bandit.py`
Memory | How well each of the other five methods has done
= Personality dials
[[Accusation threshold]] | {{code:preset.Green.accuse_threshold}}
[[Bluff rate]] | {{code:preset.Green.bluff_rate}}
[[Curiosity]] | {{code:preset.Green.curiosity}}
[[Secrecy]] | {{code:preset.Green.secrecy}}
[[Temperature]] | {{code:preset.Green.temperature}}
= Record on the Classic board
Games won | {{fact:arena.grid.Green.win}}% of {{fact:arena.grid.Green.games}}
Wrong accusations | {{fact:arena.grid.Green.wrong}}%
}}

**Mr. Green** is one of the six [[Clue#The cards|suspects]] of [[Clue]] and, in [[clude]], the [[Category:Characters|character]] with no method of his own. He consults the other five, and on each turn adopts the [[belief]] of whichever he currently trusts most, whole. Which to trust is a [[w:Multi-armed bandit|multi-armed bandit]] problem, and he solves it by [[w:Thompson sampling|Thompson sampling]]: each method is an "arm" with a running record, and after every game the arms are ranked by how close each came to the truth and their records updated. His method is called the [[bandit ensemble]], an [[w:Ensemble learning|ensemble]] in the machine-learning sense of several models consulted together. He is as good as the mind he is currently borrowing, and as slow as all five of them together.

Over many games he comes to trust the methods the [[belief benchmark]] also ranks highest, [[Professor Plum]]'s count and [[Colonel Mustard]]'s tree, and his belief tracks theirs: second-best of the six at the end of a game on the [[Classic board]], and ahead of a purely logical player throughout. At the table his results are the noisiest of the six, and his record is the project's standing warning about what twenty games can and cannot show. He is one of three characters whose method remembers from game to game, and what his remembers is whom to believe.[^glossary]

## Character

Green is written as "affable, a little nervous, eager to be agreed with, and more calculating than you let on."[^persona] The description is addressed to him: it is the opening of his [[persona]], the page of prose a [[w:Large language model|language model]] is given when it plays his seat. The persona describes the method from the inside, and it is the one persona whose self-image is of having no self: "You do not have one way of thinking; you have five, borrowed from the other five people at this table, and you keep score of which of them has been closest to right lately. Each turn you lean on whichever one is winning that score, and your numbers this turn are theirs." It names the temperament the method implies: "You hedge by nature: you would rather be reliably second than brilliantly wrong. You are exactly as good as the mind you are currently borrowing, and you know it, which is why you watch the others so closely."[^persona]

His voice is "ingratiating, quick to agree, a touch anxious. 'I was just about to say that.' 'Well, that's one way of looking at it.'" He disclaims confidence right up to the moment he acts, compliments people whose reasoning he has just stolen, and is "the last person at the table anyone suspects of playing to win, and the second-most likely to."[^persona] In the first recorded games with a model in every seat the method surfaced unprompted as borrowing other players' reasoning, "Scarlett's fractions were quite persuasive, so I'll poke somewhere she hasn't", which the notes record as the method audible in the voice. He needed no edit.[^phase6]

Headless, by his numbers alone, he is silent, and every measurement below was made that way unless it says otherwise. The seat is fixed: Green always plays the green token, fourth in the order of play.[^seats]

## How he thinks

{{main:Bandit ensemble}}

{{figure:green-trust|Whom Green came to trust: the mean of each arm's record after sixty benchmark games on the ring board, against the prior's 0.5.}}

Green keeps, for each of the other five methods, a record of two numbers that together make a [[w:Beta distribution|Beta distribution]]: a curve saying how likely that method is to be the best. On every turn he asks all five what they believe, draws one random number from each curve, and plays the belief of the method whose number is highest, exactly as it stands. A method with a good record wins the draw nearly always; one with a poor record wins it now and then, which is how he finds out if it has improved. When a game ends and the envelope is opened, the five beliefs are scored against it by [[log-loss]], ranked, and each record is nudged by its rank, the best by a full step and the worst by none.[^module]

On the worked example the method articles share, the Rope question, his five arms give five answers for Mrs. White being in the envelope, from {{code:example.white.White}} ([[Mrs. White]]'s chain) to {{code:example.peacock.White}} ([[Mrs. Peacock]]'s bounds), with Plum's exact {{code:example.plum.White}} among them; which he plays depends on his record, and in a first game, every record flat, it is a coin toss. The example on the method's page goes on to score the five against a revealed envelope and shows one lesson bending every record.[^bandit]

## How he plays

A character's belief says what it thinks; five [[personality dials]] say what it does about it. Green's are set to make him the middling one.[^presets]

| Dial | Green | What it does |
|---|---|---|
| [[Accusation threshold]] | {{code:preset.Green.accuse_threshold}} | He accuses once his own estimate of being right reaches this. |
| [[Bluff rate]] | {{code:preset.Green.bluff_rate}} | The chance that he names a card from his own hand in a suggestion. |
| [[Curiosity]] | {{code:preset.Green.curiosity}} | How far he will walk for the room he most suspects rather than enter the nearest. |
| [[Secrecy]] | {{code:preset.Green.secrecy}} | When he must show a card, how strongly he prefers one that player has already seen. |
| [[Temperature]] | {{code:preset.Green.temperature}} | How much chance enters his choices. The highest at the table, shared with [[Colonel Mustard]]: the "noisy" flavour. |

The preset's own note calls him "opportunistic: middling everything, a bit noisy", and none of his dials has moved since the first tuning.[^presets] His threshold was the one questioned, after the Classic board's first arena, in which he did not win a game and accused in only one of sixteen while his belief on the benchmark was as good as anyone's.

{{table:green.threshold|Green with only his accusation threshold moved, three arenas of 24 games on the Classic board, 15 September 2026.}}

Lowering the bar bought one win in sixteen and, at 0.5, two wrong accusations. What limits him is pace, not his dial: the confidence he borrows rarely reaches even 0.5 before somebody else ends the game. The preset stood at {{code:preset.Green.accuse_threshold}}.[^grid-presets]

## Record

### The quality of his numbers

{{table:bench.ring|The six methods on the ring board, Phase 5: log-loss at four checkpoints. Lower is better.}}

Green's score is a borrowed score, and it tracks the arms he trusts. On the ring board he was joint-best with Plum at the end of a game, {{fact:bench.ring.Green.100}}, with the best first choice of the six, {{fact:bench.ring.Green.top1}}, and ahead of the [[uniform baseline]] at every checkpoint. On the first benchmark of all his five arms had sat within a percent of one another on the reward then in use, so that he chose among them at random; the reward was changed to a rank, and after sixty games his records spread by {{fact:green.arms.spread}}: Plum at {{fact:green.arms.ring.plum}}, Mustard {{fact:green.arms.ring.mustard}}, White {{fact:green.arms.ring.white}}, Peacock {{fact:green.arms.ring.peacock}} and Scarlett {{fact:green.arms.ring.scarlett}}, which is the order the benchmark ranks the methods at the end of a game.[^ring][^glossary]

{{table:bench.grid|The same benchmark on the Classic board, {{fact:bench.grid.games}} games, 15 September 2026.}}

On the Classic board he is second-best at the end, {{fact:bench.grid.Green.100}}, and ahead of the baseline throughout, including the halfway mark where Plum himself is not; the run left him leaning on Mustard ({{fact:green.arms.grid.mustard}}) and Plum ({{fact:green.arms.grid.plum}}) and away from Peacock ({{fact:green.arms.grid.peacock}}) and Scarlett ({{fact:green.arms.grid.scarlett}}). The price is time: {{fact:bench.grid.Green.ms}} ms a call at mid-game, Plum's cost plus everyone else's.[^grid]

### At the table

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, tables of three to six, 15 September 2026.}}

In the [[arena]] Green trails, "as an ensemble that is only as good as the arm it currently trusts and slower than everyone": {{fact:arena.ring.Green.win}}% of his games won on the ring board at the tuned presets, with {{fact:arena.ring.Green.wrong}}% wrong.[^ring-arena] The Classic board's first arena gave him no wins at all in sixteen games, and the notes called it a collapse until the arenas that followed said otherwise. Across the nine arenas run that day, in only two of which any dial of his was moved, he won {{fact:green.swing}} per cent of his games; and in the confirmation arena, played on the same 24 deals as the one he had lost every game of, he won {{fact:green.confirm.win}}% with nothing of his changed. The zero was "the low draw of a noisy number, not a collapse", and his line is the one the notes point to whenever a single arena seems to show something: a character plays 16 to 20 of the 24 games, so each percentage carries a [[w:Standard error|standard error]] of {{fact:arena.noise}} points, and "nothing smaller than that swing is evidence on its own".[^grid-presets][^arena]

### With Claude in the seat

When a model plays him, choosing among his own best-scoring options within the [[leash]], he moves within the noise: {{fact:twin.ring.Green.win_base}}% to {{fact:twin.ring.Green.win_llm}}% of games won on the ring board, {{fact:twin.grid.Green.win_base}}% to {{fact:twin.grid.Green.win_llm}}% on the Classic board, with his first accusation coming earlier in both, as everyone's did at a table where every seat had a model. His [[w:Bluff (poker)|bluffing]] fell, from {{fact:twin.grid.bluff.green.base}} own-card suggestions a game to {{fact:twin.grid.bluff.green.llm}}, as it did for every character that does not loop.[^twin-ring][^twin]

## Memory

Green's method remembers whom to trust. His five records are saved after every game and restored before the next, so that the trust he has built over a run of games is there at the start of the next one; since Phase 7 they survive the end of the program too, kept as his method memory in the same store as the game records. Unlike [[Colonel Mustard]]'s rows and [[Mrs. White]]'s counts, his memory cannot be rebuilt from stored games afterwards: a record depends on what his arms predicted at the time, which no game record holds, so it is only ever accumulated, never recomputed.[^memory]

Like every character he can also keep a narrative [[logbook]], written by a model after each game it played his seat, with what happened and what to do next time.[^logbooks]

## See also

- [[Bandit ensemble]], his method in full, with the worked example and the mathematics
- [[Professor Plum]] and [[Colonel Mustard]], the two arms he comes to trust
- [[Belief]], where the five arms' answers to one question are set side by side
- [[Belief benchmark]] and [[Arena]]
- [[Logbook]]

## References

{{references}}

[^glossary]: {{cite:docs/strategy-glossary.md|Green -- Bandit ensemble over the other five}}
[^persona]: {{cite:clude_llm/personas/Green.md|Green's persona, quoted throughout this section}}
[^phase6]: {{cite:docs/phase6-plan.md|6c, the real backend (2026-09-12; live checks done 2026-09-13)}}
[^seats]: {{cite:CLAUDE.md|Settled decisions (David's)}} A character always plays its own suspect's token.
[^module]: {{cite:clude_agents/bandit.py|`BanditAgent.select_action` and `observe`, `rank_rewards`}}
[^bandit]: Computed by the live modules on the Rope question; see [[Bandit ensemble#At the table]].
[^presets]: {{cite:clude_agents/personality.py|`PRESETS`, Green's entry and its note}}
[^grid-presets]: {{cite:docs/strategy-glossary.md|Tuned presets on the grid (Stage 1e, 2026-09-15)}}
[^ring]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^ring-arena]: {{cite:docs/strategy-glossary.md|Arena, tuned presets}}
[^arena]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}
[^twin-ring]: {{cite:docs/strategy-glossary.md|Twin comparison (2026-09-13)}}
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}
[^memory]: {{cite:docs/logbooks.md|Tier 1: method memory}}
[^logbooks]: {{cite:docs/logbooks.md|Three tiers}}

{{navbox:clude}}
