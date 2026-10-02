---
title: Mr. Green
short: The adaptable character who selects among five other methods
categories: Characters
redirects: Green, Reverend Green, Rev. Green
dyk: ... that [[Mr. Green]] won no games in one sixteen-game arena, then {{fact:green.confirm.win}}% on the same deals with his settings unchanged and different opposition?
dyk: ... that [[Mr. Green]] queries all five other methods before selecting one, even when he will not use the most expensive answer?
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
= Classic-board arena, 15 September 2026
Games won | {{fact:arena.grid.Green.win}}% of {{fact:arena.grid.Green.games}}
Wrong accusations | {{fact:arena.grid.Green.wrong}}%
}}

**Mr. Green** is one of the six [[Clue#The cards|suspects]] in [[Clue]] and a [[Category:Characters|character]] in [[clude]]. His [[bandit ensemble]] computes the other five methods' [[belief|beliefs]] and adopts one unchanged. It uses [[w:Thompson sampling|Thompson sampling]] to select among them, based on a record of their accuracy on revealed envelopes. Green therefore has an adaptive selection method of his own, but obtains the card probabilities from one of its constituent methods. He pays the computation cost of all five whether or not he selects the expensive one.[^module]

In the recorded [[belief benchmark|benchmarks]], his arm records favoured [[Professor Plum]] and [[Colonel Mustard]]. He had the second-lowest final log-loss on the [[Classic board]] and lower loss than the [[uniform baseline]] at all four checkpoints. His game results varied substantially between small arenas, making them a useful warning against drawing firm conclusions from one run. He has persistent method memory, which stores the arm records.[^glossary]

## Character

Green's [[persona]], given to a [[w:Large language model|language model]] playing his seat, describes him as "affable, a little nervous, eager to be agreed with, and more calculating than you let on". It characterises his ensemble as borrowed ways of thinking: "You do not have one way of thinking; you have five". His self-image is cautious and opportunistic: he would rather be reliably second than brilliantly wrong.[^persona] The borrowed minds are algorithmic models, not access to the other seats' private cards.

His prescribed voice is "ingratiating, quick to agree, a touch anxious", with phrases such as "I was just about to say that". He compliments others while borrowing their reasoning.[^persona] In the first reviewed model-piloted games, a line about "Scarlett's fractions" expressed this habit without additional prompting. The review retained his persona.[^phase6]

Headless, by his numbers alone, he is silent, and every measurement below was made that way unless it says otherwise. The seat is fixed: Green always plays the green token, fourth in the order of play.[^seats]

## How he thinks

{{main:Bandit ensemble}}

{{figure:green-trust|Whom Green came to trust: the mean of each arm's record after sixty benchmark games on the ring board, against the prior's 0.5.}}

Each constituent method is an *arm* with two parameters defining a [[w:Beta distribution|Beta distribution]]. Green draws one score per arm and adopts the belief of the largest draw. On a revealed envelope, he ranks all five predictions by [[log-loss]] and updates their records with fractional rewards; old evidence gradually decays. Stronger records tend to produce higher draws. The records are heuristic measures of recent rank performance, rather than calibrated probabilities that a method is best.[^module]

In the [[Bandit ensemble#At the table|shared observer example]], the five arms give probabilities for Mrs. White ranging from {{code:example.white.White}} to {{code:example.peacock.White}}, including Plum's equal-weight count of {{code:example.plum.White}}. With five identical initial records, each arm is equally likely to be selected. The method article then reveals the envelope and shows how one outcome updates all five records.[^bandit]

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

Lowering Green's threshold produced one win in sixteen games; at 0.5 he also made two wrong accusations. The sweep suggested that his borrowed confidence often rose too slowly to reach the threshold before another player won. His preset remained {{code:preset.Green.accuse_threshold}}.[^grid-presets]

## Record

### The quality of his numbers

{{table:bench.ring|The six methods on the ring board, Phase 5: log-loss at four checkpoints. Lower is better.}}

Green's score is a borrowed score, and it tracks the arms he trusts. On the ring board he was joint-best with Plum at the end of a game, {{fact:bench.ring.Green.100}}, with the best first choice of the six, {{fact:bench.ring.Green.top1}}, and ahead of the [[uniform baseline]] at every checkpoint. In the earliest benchmark, all five arms had mean rewards within a percentage point of one another, so selection barely distinguished them; the reward was changed to a rank, and after sixty games his records spread by {{fact:green.arms.spread}}: Plum at {{fact:green.arms.ring.plum}}, Mustard {{fact:green.arms.ring.mustard}}, White {{fact:green.arms.ring.white}}, Peacock {{fact:green.arms.ring.peacock}} and Scarlett {{fact:green.arms.ring.scarlett}}, which is the order the benchmark ranks the methods at the end of a game.[^ring][^glossary]

{{table:bench.grid|The same benchmark on the Classic board, {{fact:bench.grid.games}} games, 15 September 2026.}}

On the Classic board he is second-best at the end, {{fact:bench.grid.Green.100}}, and ahead of the baseline throughout, including the halfway mark where Plum himself is not; the run left him leaning on Mustard ({{fact:green.arms.grid.mustard}}) and Plum ({{fact:green.arms.grid.plum}}) and away from Peacock ({{fact:green.arms.grid.peacock}}) and Scarlett ({{fact:green.arms.grid.scarlett}}). The price is time: {{fact:bench.grid.Green.ms}} ms a call at mid-game, Plum's cost plus everyone else's.[^grid]

### At the table

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, tables of three to six, 15 September 2026.}}

Green won {{fact:arena.ring.Green.win}}% of his games in the tuned ring-board arena and accused wrongly in {{fact:arena.ring.Green.wrong}}%.[^ring-arena] In the first Classic-board arena he won none of sixteen games. Later trials showed that this was not a stable result: across nine arenas that day, with his dials changed in only two, his win rates spanned {{fact:green.swing}} per cent. A confirmation run using the same deals as the initial arena gave {{fact:green.confirm.win}}% wins with his settings unchanged. Opponents' settings had changed, so this was not an identical replay. Each character played only 16 to 20 games per arena, giving an estimated [[w:Standard error|standard error]] of {{fact:arena.noise}} percentage points. These results do not establish a precise competitive ranking.[^grid-presets][^arena]

### With Claude in the seat

With a model choosing within his [[leash]], Green's win rate changed from {{fact:twin.ring.Green.win_base}}% to {{fact:twin.ring.Green.win_llm}}% on the ring board and from {{fact:twin.grid.Green.win_base}}% to {{fact:twin.grid.Green.win_llm}}% on the Classic board. The notes treat these changes as within sampling uncertainty. His first accusation came earlier on both boards, as it did for every character at the model table. His [[w:Bluff (poker)|bluffing]] fell from {{fact:twin.grid.bluff.green.base}} own-card suggestions per game to {{fact:twin.grid.bluff.green.llm}}.[^twin-ring][^twin]

## Memory

Green's five arm records are saved after games and restored when remembering is enabled. Since Phase 7, they persist in the same store as game records. Unlike [[Colonel Mustard]]'s training rows and [[Mrs. White]]'s transition counts, the current memory builder does not reconstruct them from stored games: the records do not preserve the predictions made by the arms at the time. His method memory is accumulated during play.[^memory]

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
