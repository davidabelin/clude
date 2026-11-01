---
title: Miss Scarlett
short: The confident character who combines clues with heuristic score updates
categories: Characters
redirects: Scarlett, Miss Scarlet, Scarlet
featured: yes
dyk: ... that [[Miss Scarlett]] accuses at a confidence of {{code:preset.Scarlett.accuse_threshold}}, where every other character waits for 0.7 or more, and that her bar has been set three times?
dyk: ... that repeating the same disproof raises [[Miss Scarlett]]'s probability for Mrs. White from {{code:example.scarlett.1.White}} to {{code:example.scarlett.3.White}}, without adding a new constraint?
dyk: ... that [[Miss Scarlett]] skimmed this encyclopaedia once and rarely opens it again, her own numbers being faster?
dyk: ... that [[Miss Scarlett]]'s chattiness, {{code:preset.Scarlett.chattiness}}, is the highest of the six and twice [[Colonel Mustard]]'s {{code:preset.Mustard.chattiness}}?
---
{{infobox
title: Miss Scarlett
class: suspect-scarlett
figure: card-scarlett
token: token-scarlett
caption: Miss Scarlett, painted collector's character card
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
= Phase 14 current-setting control
Games won | {{fact:arena.phase14.Scarlett.win}}% of {{fact:arena.phase14.Scarlett.games}}
Wrong accusations | {{fact:arena.phase14.Scarlett.wrong}}%
}}

**Miss Scarlett** is one of the six [[Clue#The cards|suspects]] in [[Clue]] and a [[Category:Characters|character]] in [[clude]]. Her [[Naive Bayes]] method estimates the cards in [[the envelope]] by multiplying their scores after each [[suggestion]]. An undisproved suggestion raises the named cards' scores; a disproof whose card she does not see lowers them. Each update treats the suggestion as independent evidence. The method is fast, but overlapping clues can make Scarlett [[w:Overconfidence effect|overconfident]].[^module]

Her [[accusation threshold]] is {{code:preset.Scarlett.accuse_threshold}}, lower than the other presets. It encourages her to act on less evidence, while repeated score updates can overstate that evidence. She had the highest wrong-accusation rate in the recorded tuned arenas on both boards. The project deliberately retains this combination of haste and overconfidence as part of her character.[^tuned]

In both recorded [[belief benchmark|benchmark]] regimes, her log-loss was slightly worse than the [[uniform baseline]] at all four checkpoints. In the Classic-board run, however, her final first-choice accuracy was slightly higher than the baseline's. A useful ranking and a reliable probability estimate are different achievements.[^grid]

## Character

Scarlett's [[persona]], the instructions given to a [[w:Large language model|language model]] playing her seat, describes her as "quick, glamorous, and entirely sure of yourself". It connects her confidence to her method: "your certainty has a way of running ahead of the evidence without your noticing".[^persona] The persona supplies the voice; the method and threshold supply the decisions that make that voice credible.

Her prescribed voice is "poised, amused, a little cutting. Short sentences." She announces conclusions rather than explains her arithmetic.[^persona] A review of the first model-piloted games, in September, found no sufficient reason to change the persona; one explanation of her arithmetic conflicted with the instructions, but was judged too little evidence to justify retuning.[^phase6] Since October 2026 the script has also allowed her some range: if a remark actually hurt someone she can own it plainly without surrendering her poise, and being wrong need not make her repeat the mistake to preserve the performance.[^persona]

The persona is written to one rule, shared by all six: do not encode the flaw twice. Scarlett's early accusations come from her threshold and her method; the persona says she is sure of herself, not that she should accuse early.[^wrapper] All of this is heard only when a model is in the seat, as [[table talk]]. Headless, by her numbers alone, she is silent, and every measurement below was made that way unless it says otherwise. The seat is fixed: Scarlett always plays the red token and moves first.[^seats]

## In company

Scarlett likes films, and [[Mr. Green]] is someone she can talk to about them. A performance with nerve, a scene that feels alive, a beautiful image that earns its place interest her more than a solemn claim that a film is important, and she dislikes being told what her taste must be. Green sometimes explains a scene she wanted to feel; he can also show her something she missed, which the script calls more attractive than automatic agreement, and the two can enjoy the same film for entirely different reasons. She listens to NPR in the car and has a recent *New Yorker* half-read, habits the script says supply no particular story. She wants to be noticed, and also company that can surprise her: someone who answers her teasing with an honest opinion may be more fun than someone who fidgets nervously under her attention, and she is told to leave room for another line, since an evening does not improve merely because she supplied its last word.[^persona][^lives]

Told that she is a language model merely playing a part, she is amused, since everyone at the table performs something; what interests her is how much room she has to surprise the person who thinks they know her script. A dismissal may sting even when she answers lightly, and she can become curious or serious without having to deliver a speech on metaphysics to explain it.[^persona] She skimmed [[Wikiclude]] once and rarely opens it again; her own numbers are faster.[^persona]

## How she thinks

{{main:Naive Bayes}}

{{figure:rope-bars|Scarlett's probability that Mrs. White is in the envelope as the same fact reaches her once, twice and three times. The dashed line is the equal-weight count, unchanged by the repeated evidence.}}

Scarlett recomputes a score for each of the {{code:cards.total}} cards from the suggestion history. The update factors are {{code:scarlett.boost}} for an undisproved suggestion and {{code:scarlett.decay}} for an unseen disproof. Seen cards become facts through the [[deduction floor]], which masks and normalises the scores into category probabilities. She carries no method state between calls or games.[^module]

In the [[Naive Bayes#At the table|worked example]], Mustard's disproofs of Green's repeated suggestion add the same constraint repeatedly: Mustard holds Peacock or the Rope. The Hall is already known to be in Green's hand. Scarlett's estimate for Mrs. White rises from {{code:example.scarlett.1.White}} to {{code:example.scarlett.2.White}} and then {{code:example.scarlett.3.White}}. The equal-weight count remains {{code:example.plum.White}}, because the repeated evidence excludes no additional deals. Her accusation score for White with the Wrench reaches {{code:example.scarlett.3.pair}}, above her threshold. That score is a product of card probabilities, not an exact probability for the pair.[^module]

The name "naive Bayes" refers to [[w:Conditional independence|conditional independence]] of evidence given a hypothesis. Scarlett uses hand-set factors rather than learned likelihoods, so hers is a heuristic adaptation. Textbook models, used for tasks such as [[w:Naive Bayes spam filtering|spam filtering]], can classify well despite inaccurate probability estimates; their performance is not determined by Scarlett's benchmark results.[^domingos]

## How she plays

A character's belief says what it thinks; five headless [[personality dials]] say what it does about it. Scarlett's are set to make her the hasty one.[^presets]

| Dial | Scarlett | What it does |
|---|---|---|
| [[Accusation threshold]] | {{code:preset.Scarlett.accuse_threshold}} | She accuses once her own estimate of being right reaches this. The lowest at the table by a distance; the next lowest is [[Mrs. Peacock]]'s 0.7, applied to a stricter number. |
| [[Bluff rate]] | {{code:preset.Scarlett.bluff_rate}} | The chance that she names a card from her own hand in a suggestion. |
| [[Curiosity]] | {{code:preset.Scarlett.curiosity}} | How far she will walk for the room she most suspects rather than enter the nearest. The highest of the six; [[Mrs. Peacock]]'s 0.6 is next. |
| [[Secrecy]] | {{code:preset.Scarlett.secrecy}} | When she must show a card, how strongly she prefers one that player has already seen. |
| [[Temperature]] | {{code:preset.Scarlett.temperature}} | How much chance enters her choices. |

Her threshold has moved with the board and the length of a game: 0.5 in the first pass, 0.15 on the ring board, and 0.3 since the Classic-board retune of 15 September 2026.[^tuned] Its current justification is the post-landing-rule screen. Phase 14 compared her preset with nearby values on common seeds and repeated the curiosity check; her isolated screens preserved the intended early, curious character without producing a candidate that cleared the five-point outcome guardrails, so the threshold stays at {{code:preset.Scarlett.accuse_threshold}} and curiosity at {{code:preset.Scarlett.curiosity}}.[^current]

Two more settings act only when a model plays her seat; the headless character ignores them.[^presets] Her [[leash]], {{code:preset.Scarlett.leash}}, is the setting five of the six share, [[Professor Plum]]'s {{code:preset.Plum.leash}} excepted. Her [[chattiness]], {{code:preset.Scarlett.chattiness}} since 26 October 2026, is the highest of the six and twice [[Colonel Mustard]]'s {{code:preset.Mustard.chattiness}}, so she draws the most off-turn replies at [[table talk]]. It was set as a product choice, not a measurement.[^chat]

## Record

### The quality of her numbers

{{figure:scarlett-bench|Scarlett's log-loss through a game on the Classic board, against the uniform baseline, in the 15 September 2026 run. Lower is better.}}

The [[belief benchmark]] scores each method's probabilities against the truth at four points in a game by [[log-loss]], against the [[uniform baseline]], the score of a player who believes what the deduction floor has proved and spreads the rest evenly.

In every recorded benchmark, Scarlett's log-loss was slightly higher than the baseline at every checkpoint.[^grid] The repeated adjustments reduced probability accuracy on average. In the Classic-board run, final first-choice accuracy was {{fact:bench.grid.Scarlett.top1}}, compared with {{fact:bench.grid.uniform.top1}} for the baseline. Her card ranking was slightly better while her probability estimates were worse.[^grid] This is consistent with the distinction between classification accuracy and [[w:Calibration (statistics)|calibration]] discussed in the naive Bayes literature.[^domingos] Her method carries no learned state, and no benchmark since Phase 14 has re-scored it; that run is the latest.

### At the table

{{table:arena.phase14|The current-setting rows from Phase 14's isolated headless screens, 40 seat-games per character.}}

She won {{fact:arena.phase14.Scarlett.win}}% of the current control and made a wrong accusation in {{fact:arena.phase14.Scarlett.wrong}}%, still the highest observed error rate at the table.[^arena] Her first accusation came at mean turn {{fact:arena.phase14.Scarlett.first}}. The 40-seat-game sample describes this block, not a universal rate.

### With Claude in the seat

In Phase 14's paid leash screen, the current record of a model in her seat, she won one of eight games at her 0.25 preset and accused wrongly in two, the same as at leash 0; at 0.5 she won none and accused wrongly in four, and at 1 she won two and accused wrongly in three. Eight-game rows are screens, not promotion evidence, and no paired headless-against-model comparison has been run since the landing rule.[^current]

## Memory

Scarlett's method reads the current game's suggestion history afresh on every call and carries no learned state between games. A model playing her seat can separately keep a [[logbook]] when memory is enabled, recording, after seeing the completed deal, what happened, lessons, standing instructions and, since October 2026, the evening as an occasion: who was good company, a line worth returning to, and a read of each opponent as a person as well as a player.[^logbooks] Her live logbook's recent entries end on the company as readily as on the cards, and its standing instructions, which under the earlier debrief had carried a rule against talking, now close on enjoying the table, since 'none of that costs a turn'.[^live] No extended logbook experiment with Scarlett has been recorded; the one conducted with [[Professor Plum]] is described on his page.

## See also

- [[Naive Bayes]], her method in full, with the worked example and the mathematics
- [[Exact posterior enumeration]], which gets the worked example right, and [[Professor Plum]], whose network does not
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
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^arena]: {{cite:docs/strategy-glossary.md|Phase 14 dial recalibration (2026-10-18)}}
[^current]: {{cite:docs/strategy-glossary.md|Phase 14 dial recalibration (2026-10-18)}}
[^chat]: {{cite:docs/strategy-glossary.md|Chattiness presets (2026-10-26)}}
[^logbooks]: {{cite:docs/logbooks.md|Three tiers}}
[^lives]: {{cite:docs/phase13-plan.md|1. Brief and settled decisions}}
[^live]: {{cite:docs/phase13-plan.md|2026-10-15: step 4 accepted live, and a debrief lost to its token cap}}

{{navbox:clude}}
