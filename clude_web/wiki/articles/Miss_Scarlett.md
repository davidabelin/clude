---
title: Miss Scarlett
short: The confident character who combines clues with heuristic score updates
categories: Characters
redirects: Scarlett, Miss Scarlet, Scarlet
dyk: ... that [[Miss Scarlett]] accuses at a confidence of {{code:preset.Scarlett.accuse_threshold}}, where every other character waits for 0.7 or more, and that her bar has been set three times?
dyk: ... that repeating the same disproof raises [[Miss Scarlett]]'s probability for Mrs. White from {{code:example.scarlett.1.White}} to {{code:example.scarlett.3.White}}, without adding a new constraint?
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
= Classic-board arena, 15 September 2026
Games won | {{fact:arena.grid.Scarlett.win}}% of {{fact:arena.grid.Scarlett.games}}
Wrong accusations | {{fact:arena.grid.Scarlett.wrong}}%
}}

**Miss Scarlett** is one of the six [[Clue#The cards|suspects]] in [[Clue]] and a [[Category:Characters|character]] in [[clude]]. Her [[Naive Bayes]] method estimates the cards in [[the envelope]] by multiplying their scores after each [[suggestion]]. An undisproved suggestion raises the named cards' scores; a disproof whose card she does not see lowers them. Each update treats the suggestion as independent evidence. The method is fast, but overlapping clues can make Scarlett [[w:Overconfidence effect|overconfident]].[^module]

Her [[accusation threshold]] is {{code:preset.Scarlett.accuse_threshold}}, lower than the other presets. It encourages her to act on less evidence, while repeated score updates can overstate that evidence. She had the highest wrong-accusation rate in the recorded tuned arenas on both boards. The project deliberately retains this combination of haste and overconfidence as part of her character.[^tuned]

In both recorded [[belief benchmark|benchmark]] regimes, her log-loss was slightly worse than the [[uniform baseline]] at all four checkpoints. In the Classic-board run, however, her final first-choice accuracy was slightly higher than the baseline's. A useful ranking and a reliable probability estimate are different achievements.[^grid]

## Character

Scarlett's [[persona]], the instructions given to a [[w:Large language model|language model]] playing her seat, describes her as "quick, glamorous, and entirely sure of yourself". It connects her confidence to her method: "your certainty has a way of running ahead of the evidence without your noticing".[^persona] The persona supplies the voice; the method and threshold supply the decisions that make that voice credible.

Her prescribed voice is "poised, amused, a little cutting. Short sentences." She announces conclusions rather than explains her arithmetic, and her confidence is meant to survive being wrong.[^persona] A review of the first model-piloted games found no sufficient reason to change the persona. One explanation of her arithmetic conflicted with the instructions, but was judged too little evidence to justify retuning.[^phase6]

The persona is written to one rule, shared by all six: do not encode the flaw twice. Scarlett's early accusations come from her threshold and her method; the persona says she is sure of herself, not that she should accuse early.[^wrapper] All of this is heard only when a model is in the seat, as [[table talk]]. Headless, by her numbers alone, she is silent, and every measurement below was made that way unless it says otherwise. The seat is fixed: Scarlett always plays the red token and moves first.[^seats]

## How she thinks

{{main:Naive Bayes}}

{{figure:rope-bars|Scarlett's probability that Mrs. White is in the envelope as the same fact reaches her once, twice and three times. The dashed line is the equal-weight count, unchanged by the repeated evidence.}}

Scarlett recomputes a score for each of the {{code:cards.total}} cards from the suggestion history. The update factors are {{code:scarlett.boost}} for an undisproved suggestion and {{code:scarlett.decay}} for an unseen disproof. Seen cards become facts through the [[deduction floor]], which masks and normalises the scores into category probabilities. She carries no method state between calls or games.[^module]

In the [[Naive Bayes#At the table|worked example]], Green's disproofs add the same constraint repeatedly: Mustard holds Peacock or the Rope. The Hall is already known to be in Green's hand. Scarlett's estimate for Mrs. White rises from {{code:example.scarlett.1.White}} to {{code:example.scarlett.2.White}} and then {{code:example.scarlett.3.White}}. The equal-weight count remains {{code:example.plum.White}}, because the repeated evidence excludes no additional deals. Her accusation score for White with the Wrench reaches {{code:example.scarlett.3.pair}}, above her threshold. That score is a product of card probabilities, not an exact probability for the pair.[^module]

The name "naive Bayes" refers to [[w:Conditional independence|conditional independence]] of evidence given a hypothesis. Scarlett uses hand-set factors rather than learned likelihoods, so hers is a heuristic adaptation. Textbook models, used for tasks such as [[w:Naive Bayes spam filtering|spam filtering]], can classify well despite inaccurate probability estimates; their performance is not determined by Scarlett's benchmark results.[^domingos]

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

In the Classic-board sweep, a threshold of 0.3 produced three times the win rate of 0.15, with fewer wrong accusations. The longer games allowed more evidence to accumulate before she reached the higher threshold. She still accused in nearly half her games and was wrong in about half those accusations. The preset became {{code:preset.Scarlett.accuse_threshold}}.[^grid-presets] Curiosity settings of 0.5 and 0.3 gave {{fact:curiosity.grid.0.5.scarlett}} and {{fact:curiosity.grid.0.3.scarlett}} for won, wrong and never accused. The notes describe these as "noise around a losing position", and her curiosity remains {{code:preset.Scarlett.curiosity}}.[^grid-presets]

## Record

### The quality of her numbers

{{figure:scarlett-bench|Scarlett's log-loss through a game on the Classic board, against the uniform baseline. Lower is better.}}

The [[belief benchmark]] scores each method's probabilities against the truth at four points in a game by [[log-loss]], against the [[uniform baseline]], the score of a player who believes what the deduction floor has proved and spreads the rest evenly.

{{table:bench.grid|The six methods on the Classic board: log-loss at four checkpoints, {{fact:bench.grid.games}} games, 15 September 2026.}}

In both the ring-board and Classic-board benchmarks, Scarlett's log-loss was slightly higher than the baseline at every checkpoint.[^ring] The repeated adjustments reduced probability accuracy on average. In the Classic-board run, final first-choice accuracy was {{fact:bench.grid.Scarlett.top1}}, compared with {{fact:bench.grid.uniform.top1}} for the baseline. Her card ranking was slightly better while her probability estimates were worse.[^grid] This is consistent with the distinction between classification accuracy and [[w:Calibration (statistics)|calibration]] discussed in the naive Bayes literature.[^domingos]

### At the table

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, tables of three to six, 15 September 2026.}}

On the ring board, at the tuned presets, she won {{fact:arena.ring.Scarlett.win}}% of her games and accused wrongly in {{fact:arena.ring.Scarlett.wrong}}%, last on the one count and first on the other, which the notes record as the flavour: "overconfident, early, usually wrong, occasionally first".[^ring-arena] On the Classic board at the raised threshold she won {{fact:arena.grid.Scarlett.win}}% and was wrong in {{fact:arena.grid.Scarlett.wrong}}%, still the most wrong accusations at the table but no longer "both the least successful and the most reckless seat".[^arena] Her first accusation came at turn {{fact:arena.grid.Scarlett.first}}, later than four of the other five: the raised bar is why. A character plays 16 to 20 of the 24 games, so each percentage carries a [[w:Standard error|standard error]] of {{fact:arena.noise}} points.[^grid-presets]

The [[landing rule]] took her exact repeats of her own earlier suggestions on the mixed table from {{fact:landing.repeats.Scarlett.mixed}}.[^landing]

### With Claude in the seat

In the [[Claude]] twin comparisons, Scarlett's win rate was unchanged: {{fact:twin.ring.Scarlett.win_base}}% on the ring board and {{fact:twin.grid.Scarlett.win_base}}% on the Classic board. Wrong-accusation rates changed from {{fact:twin.ring.Scarlett.wrong_base}}% to {{fact:twin.ring.Scarlett.wrong_llm}}% and from {{fact:twin.grid.Scarlett.wrong_base}}% to {{fact:twin.grid.Scarlett.wrong_llm}}%, respectively, within the uncertainty of these runs. The clearer behavioural change was fewer [[w:Bluff (poker)|held-card suggestions]]: {{fact:twin.ring.bluff.scarlett.base}} to {{fact:twin.ring.bluff.scarlett.llm}} per game on the ring and {{fact:twin.grid.bluff.scarlett.base}} to {{fact:twin.grid.bluff.scarlett.llm}} on the Classic board. Those counts do not by themselves establish why the model changed its choices.[^twin-ring][^twin]

## Memory

Scarlett's method reads the current game's suggestion history afresh on every call and carries no learned state between games. A model playing her seat can separately keep a [[logbook]] when memory is enabled, recording events, lessons and standing instructions after seeing the completed deal.[^logbooks] No extended logbook experiment with Scarlett has been recorded; the one conducted with [[Professor Plum]] is described on his page.

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
