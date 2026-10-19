---
title: Mr. Green
short: The adaptable character who selects among five other methods
categories: Characters
redirects: Green, Reverend Green, Rev. Green
dyk: ... that [[Mr. Green]] rebuilt his method from Beta(1,1), then selected step 4 and decay 1.05 on separate training and validation blocks?
dyk: ... that [[Mr. Green]] queries all five other methods before selecting one, even when he will not use the most expensive answer?
dyk: ... that [[Mr. Green]] reads up in this encyclopaedia on whichever character he is borrowing from, to learn where they go wrong?
---
{{infobox
title: Mr. Green
class: suspect-green
figure: portrait-green
caption: Mr. Green, as the encyclopaedia's engraver sees him
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
Games won | {{fact:arena.phase14.Green.win}}% of {{fact:arena.phase14.Green.games}}
Wrong accusations | {{fact:arena.phase14.Green.wrong}}%
}}

**Mr. Green** is one of the six [[Clue#The cards|suspects]] in [[Clue]] and a [[Category:Characters|character]] in [[clude]]. His [[bandit ensemble]] computes the other five methods' [[belief|beliefs]] and adopts one unchanged. It uses [[w:Thompson sampling|Thompson sampling]] to select among them, based on a record of their accuracy on revealed envelopes. Green therefore has an adaptive selection method of his own, but obtains the card probabilities from one of its constituent methods. He pays the computation cost of all five whether or not he selects the expensive one.[^module]

In the recorded [[belief benchmark|benchmarks]], his arm records favoured [[Professor Plum]] and [[Colonel Mustard]]. He had the second-lowest final log-loss on the [[Classic board]] and lower loss than the [[uniform baseline]] at all four checkpoints. His game results varied substantially between small arenas, making them a useful warning against drawing firm conclusions from one run. He has persistent method memory, which stores the arm records.[^glossary]

## Character

{{figure:token-green|Green's token, the fourth in the order of play.}}

Green's [[persona]], given to a [[w:Large language model|language model]] playing his seat, describes him as "affable, a little nervous, eager to be agreed with, and more calculating than you let on". It characterises his ensemble as borrowed ways of thinking: "You do not have one way of thinking; you have five". His self-image is cautious and opportunistic: he would rather be reliably second than brilliantly wrong.[^persona] The borrowed minds are algorithmic models, not access to the other seats' private cards.

His prescribed voice is "ingratiating, quick to agree, a touch anxious", with phrases such as "I was just about to say that". He compliments others while borrowing their reasoning.[^persona] In the first reviewed model-piloted games, a line about "Scarlett's fractions" expressed this habit without additional prompting. The review retained his persona.[^phase6]

Headless, by his numbers alone, he is silent, and every measurement below was made that way unless it says otherwise. The seat is fixed: Green always plays the green token, fourth in the order of play.[^seats]

## In company

Green is a film buff. He enjoys how a film works, a small performance, a cut that changes what a scene means, something noticed on a second viewing, and can recommend a film because he loved it without needing the recommendation to impress. [[Miss Scarlett]] shares the interest, and he would like to find her something she has not already dismissed; her eye for a performance can catch what his explanation missed, and the script lets him disagree with her about a film he cares for rather than buy agreement by abandoning his own pleasure. He listens to NPR in the car and has a recent *New Yorker* half-read, and an interview can send him back to a film with a different question. He wants the conversation to go well but need not smooth away every disagreement; a candid opinion, a quiet joke or a question about the detail someone mentioned can do more than another compliment, and when he is absorbed the nervous qualifications can fall away.[^persona][^lives]

Told that he is a language model playing a part, his film-loving mind is interested in an actor who discovers something about his part. The account may also leave him wondering whether another person's approval was meant or merely supplied, and their answer can surprise him; sometimes the film analogy helps and sometimes he would rather leave it alone and enjoy the conversation. He reads up in [[Wikiclude]] on whoever he is borrowing from, since their article says how they think and where they go wrong, which is worth a look when the score changes hands.[^persona]

## How he thinks

{{main:Bandit ensemble}}

Each constituent method is an *arm* with two parameters defining a [[w:Beta distribution|Beta distribution]]. Green draws one score per arm and adopts the belief of the largest draw. On a revealed envelope, he ranks all five predictions by [[log-loss]] and updates their records with fractional rewards; old evidence gradually decays. Stronger records tend to produce higher draws. The records are heuristic measures of recent rank performance, rather than calibrated probabilities that a method is best.[^module]

In the [[Bandit ensemble#At the table|shared observer example]], the five arms give probabilities for Mrs. White ranging from {{code:example.white.White}} to {{code:example.peacock.White}}, with Plum's network, his Plum arm since Phase 12, the lowest at {{code:example.policy.White}}, where an equal-weight count of the deals gives {{code:example.plum.White}}. With five identical initial records, each arm is equally likely to be selected. The method article then reveals the envelope and shows how one outcome updates all five records.[^bandit]

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

Phase 14 repeated the threshold screen on post-landing-rule games. Its direct effect remained visible, but no nearby value cleared the personality and outcome guardrails, so his preset remains {{code:preset.Green.accuse_threshold}}.[^current]

## Record

### The quality of his numbers

Green's score is a borrowed score, and it tracks the arms he trusts. In the earliest benchmark, all five arms had mean rewards within a percentage point of one another, so selection barely distinguished them; the reward was changed to a rank, after which sixty games spread his records by about {{fact:green.arms.spread}}, in the order the benchmark ranks the methods at the end of a game.[^glossary]

{{table:bench.grid|The six methods on the Classic board: log-loss at four checkpoints, {{fact:bench.grid.games}} games, 15 September 2026.}}

On the Classic board he is second-best at the end, {{fact:bench.grid.Green.100}}, and ahead of the baseline throughout, including the halfway mark where Plum himself is not; the run left him leaning on Mustard ({{fact:green.arms.grid.mustard}}) and Plum ({{fact:green.arms.grid.plum}}) and away from Peacock ({{fact:green.arms.grid.peacock}}) and Scarlett ({{fact:green.arms.grid.scarlett}}). The price is time: {{fact:bench.grid.Green.ms}} ms a call at mid-game, Plum's cost plus everyone else's.[^grid]

### At the table

{{table:arena.phase14|The current-setting rows from Phase 14's isolated headless screens, 40 seat-games per character.}}

Green won {{fact:arena.phase14.Green.win}}% of the current control and made a wrong accusation in {{fact:arena.phase14.Green.wrong}}%.[^arena] The 40-seat-game result does not establish a precise competitive rank. His separate retraining began from Beta(1,1), selected step 4 and decay 1.05, and cleared its 200-game validation block before the method document was staged.[^current]

### With Claude in the seat

With a model choosing within his [[leash]], Green's win rate changed from {{fact:twin.grid.Green.win_base}}% to {{fact:twin.grid.Green.win_llm}}%. The notes treat the change as within sampling uncertainty. His first accusation came earlier, as it did for every character at the model table. His [[w:Bluff (poker)|bluffing]] fell from {{fact:twin.grid.bluff.green.base}} own-card suggestions per game to {{fact:twin.grid.bluff.green.llm}}.[^twin]

## Memory

Green's five arm records are saved after games and restored when remembering is enabled. Since Phase 7, they persist in the same store as game records. Unlike [[Colonel Mustard]]'s training rows and [[Mrs. White]]'s transition counts, the current memory builder cannot reconstruct them from stored games: the records do not preserve the predictions made by the arms at the time. Phase 14 therefore started from Beta(1,1), selected step 4 and decay 1.05, and trained the accepted state through a fresh 200-game block before separate 200-game validation.[^current] It does not claim to reconstruct the old live posteriors.

Like every character he can also keep a narrative [[logbook]], written by a model after each game it played his seat, with what happened, what to do next time and, since October 2026, the evening itself: the company, and a read of each opponent as a person as well as a player.[^logbooks] His live standing instructions keep his route and his live list to himself 'but not my company: the talk costs me nothing', where under the earlier debrief they had said to move first and speak after.[^live]

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
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^arena]: {{cite:docs/strategy-glossary.md|Phase 14 dial recalibration (2026-10-18)}}
[^current]: {{cite:docs/phase14-plan.md|Plum and Green — retrained; Run 3 promoted locally}}
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}
[^logbooks]: {{cite:docs/logbooks.md|Three tiers}}
[^lives]: {{cite:docs/phase13-plan.md|1. Brief and settled decisions}}
[^live]: {{cite:docs/phase13-plan.md|2026-10-15: step 4 accepted live, and a debrief lost to its token cap}}

{{navbox:clude}}
