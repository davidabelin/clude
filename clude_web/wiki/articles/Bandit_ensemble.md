---
title: Bandit ensemble
short: Mr. Green's adaptive selection among the other five methods
categories: Methods
redirects: Bandit, Multi-armed bandit, Thompson sampling, Green's method, Ensemble, The ensemble
dyk: ... that [[Mr. Green]] selects from five other methods, and that after sixty ring-board benchmark games the mean arm scores for Plum and Mustard were about twice Scarlett's?
dyk: ... that in arena play the [[bandit ensemble]] updates once per completed game, using the methods' ranked log-loss scores?
---
{{infobox
title: Bandit ensemble
Played by | [[Mr. Green]]
In a phrase | Selects one of five methods using learned score records
Module | `bandit.py`
Evidence used | The other five methods' beliefs, and how each has fared
Assumes | The method that has been closest to the truth lately will be again
Cost | About {{fact:bench.grid.Green.ms}} ms a call at the Classic-board halfway checkpoint; queries all five arms
= The arms
How many | {{code:green.arms}}, one per other method
Each arm's record | A Beta distribution, from Beta(1, 1)
A lesson | A rank from 1 (closest to the truth) to 0, weighted {{code:green.step_size}}
Forgetting | The record decays towards the prior by {{code:green.decay}} a lesson
}}

The **bandit ensemble** is [[Mr. Green]]'s method for selecting a [[belief]] from the other five [[Category:Methods|methods]]. On each call it computes all five beliefs and adopts one without blending them. Its choice uses a record of how accurately each method has predicted revealed envelopes. After feedback, it ranks their predictions by [[log-loss]] and updates that record. Methods with stronger recent records tend to be selected more often, while random sampling allows alternatives to be tried.[^module]

The design draws on the [[w:Multi-armed bandit|multi-armed bandit]] problem: choosing among options with uncertain rewards, named after [[w:Slot machine|slot machines]]. Green uses [[w:Thompson sampling|Thompson sampling]], drawing a score from each arm's distribution and selecting the largest. This balances *exploitation*, using a method with a good record, against *exploration*, trying one whose value is less certain.[^sutton][^thompson] Unlike a classical bandit, Green receives feedback for all five arms when the envelope is revealed, rather than only for the selected arm.

Green's current belief is exactly the selected method's output, but the computation cost is that of all five methods together. In particular, he pays for [[Professor Plum]]'s enumeration or sampling even when he selects another arm. His [[persona]] turns this dependence into the character's opportunistic voice.[^persona]

## At the table

!!! example "Worked example: the Rope question, and the lesson after it"
    {{figure:green-arms|Each arm's record after one lesson. Every arm began with the flat Beta(1, 1) distribution. The ranked scores from one revealed envelope have updated these selection records.}}

    In the shared comparison position, an observer has every card placed except four: **Mrs. White**, **Mrs. Peacock**, the **Rope** and the **Wrench**. One suspect and one weapon are in the envelope; the other two are in [[Colonel Mustard]]'s hand. The Hall is known to be in [[Mr. Green]]'s hand. Green suggests *Mrs. Peacock, with the Rope, in the Hall*, and Mustard shows him a card hidden from the observer. Green's ensemble is evaluated on the observer's view, not on the suggester's private knowledge, so it receives the same evidence as the other methods.

    Green asks his five arms for the probability that Mrs. White is in the envelope and gets five answers: [[Miss Scarlett]]'s tally says {{code:example.scarlett.1.White}}, [[Professor Plum]]'s count {{code:example.plum.White}}, [[Mrs. Peacock]]'s bounds {{code:example.peacock.White}}, [[Colonel Mustard]]'s tree {{code:example.mustard.White}} and [[Mrs. White]]'s chain {{code:example.white.White}}. Which one he plays depends on his record. In a first game, with every arm at Beta(1, 1), each draw is uniform on [0, 1] and each arm is equally likely to win; with the record the benchmark left him he would most likely play Mustard's or Plum's.

    Then the game ends and the envelope is revealed: White, the Wrench, the Study. Each arm's belief is scored by [[log-loss]] on the three true cards: Peacock {{code:example.green.loss.Peacock}}, Plum {{code:example.green.loss.Plum}}, Scarlett {{code:example.green.loss.Scarlett}}, Mustard {{code:example.green.loss.Mustard}}, White {{code:example.green.loss.White}} (lower is better). The arms are ranked: the best scores a reward of 1, the worst 0, the three between at even spacing. Each arm's record is a [[w:Beta distribution|Beta distribution]] with two counts, successes and failures, both starting at 1; the reward times {{code:green.step_size}} is added to the one and its shortfall times {{code:green.step_size}} to the other. After this single lesson Peacock's arm stands at Beta({{code:example.green.alpha.Peacock}}, {{code:example.green.beta.Peacock}}) with a mean of {{code:example.green.mean.Peacock}}, Plum's at mean {{code:example.green.mean.Plum}}, Scarlett's {{code:example.green.mean.Scarlett}}, Mustard's {{code:example.green.mean.Mustard}} and White's {{code:example.green.mean.White}}.

On this revealed envelope, Peacock's estimate happens to give the lowest loss, although Plum's count gives the exact probabilities under the model. A probability estimate can be correct without giving the highest probability to the outcome of one particular deal. The reward therefore reflects one realised outcome; it does not establish which method is best in expectation.

## How it works

### Thompson sampling

Each arm has two parameters, $\alpha$ and $\beta$, defining a [[w:Beta distribution|Beta distribution]] over scores from 0 to 1. Both start at 1, giving a uniform distribution. On each call, Green draws one score per arm and selects the largest. Strong records tend to produce higher draws; uncertain records leave more opportunity for exploration. These distributions track decayed, fractional rank rewards, so they are heuristic records rather than calibrated probabilities that a method is best.[^module][^thompson][^sutton]

### The lesson

The update needs a reward that distinguishes the arms. The initial reward, based directly on probability assigned to the true cards, gave very similar values because the shared [[deduction floor]] supplied much of every belief. Phase 5 replaced it with a **rank reward**. At each reveal, methods are ordered by log-loss: the best receives 1, the worst 0, and the others evenly spaced values. Ties share their average rank. This compares methods on the same observation, while discarding the size of the loss differences.[^phase5][^module]

Before the reward is added, each record decays a step towards the flat prior, so that old evidence fades and an arm that has recently improved can be rediscovered. Then the arm's successes rise by the reward times a step size and its failures by the shortfall times the same, so one lesson moves a fresh record a long way and a well-established one a little.[^module]

### When the lessons come

Green can update only when the envelope is known. He therefore learns once per completed [[arena]] game, or once per scored position in the [[belief benchmark]]. His record persists across games and, since Phase 7, across program runs when memory is enabled.[^arena]

## Formally

### The Beta distribution and the update

An arm's record is $\text{Beta}(\alpha, \beta)$, with density proportional to $x^{\alpha - 1}(1 - x)^{\beta - 1}$ on $[0, 1]$ and mean $\alpha / (\alpha + \beta)$. $\text{Beta}(1, 1)$ is the uniform distribution. For a reward $r \in [0, 1]$, step size $s$ and decay $d$, the update is

$$ \alpha \leftarrow \frac{\alpha - 1}{d} + 1 + s\,r, \qquad \beta \leftarrow \frac{\beta - 1}{d} + 1 + s\,(1 - r) $$

with $s = {{code:green.step_size}}$ and $d = {{code:green.decay}}$: the excess over the prior shrinks by the decay, then the lesson is added. With $d = 1$, $s = 1$ and binary rewards this would be the ordinary [[w:Bayesian inference|Bayesian update]] of a Beta prior on a coin's bias after one toss, the Beta being the [[w:Conjugate prior|conjugate prior]] of a coin; the decay turns it into a record with a memory of a few dozen lessons rather than all of them.[^module]

### The rank reward

Order the $n$ arms by losses $\ell_1 \le \ell_2 \le \dots \le \ell_n$. A rank index $i$ runs from 0 for the best arm to $n-1$ for the worst. Its reward is

$$ r_i = 1 - \frac{i}{n - 1} $$

and arms with equal losses share the mean of the positions they span. With five arms the rewards are 1, 3/4, 1/2, 1/4 and 0.[^module]

### Thompson sampling as probability matching

For textbook Thompson sampling, let $\theta_k$ be arm $k$'s unknown expected reward. Drawing $\tilde\theta_k$ from each arm's posterior and selecting $\arg\max_k \tilde\theta_k$ chooses arm $k$ with the posterior probability that it is best. This is [[w:Thompson sampling|probability matching]]. Green uses the same sampling mechanism, but his decayed rank updates do not arise from that textbook reward model. The matching property describes his score distributions, not a guarantee that they represent the true relative merits of the methods.[^thompson][^module]

## In clude

The module is `clude_agents/bandit.py`, and it is a port. David's earlier project, a [[w:Rock paper scissors|rock-paper-scissors]] tournament, had a Thompson-sampling bandit over move-predicting heuristics; here the structure is the same and the arms are literal instances of the other five agents, built fresh when Green is reset. The draws come from Python's own `betavariate`, so that the package needs no numerical library the rest of clude does without.[^module][^port]

The chosen arm's probabilities are returned unchanged, with its name recorded in the belief's extras. Green's record is saved after each game and restored as Tier 1 method memory. The current memory builder does not reconstruct the arm counts from stored games, because those records do not preserve the predictions made by the arms at the time.[^memory] Every call consults all five arms. In the Classic-board benchmark, [[Professor Plum]] alone took about {{fact:bench.grid.Plum.ms}} ms per call at mid-game and Green took {{fact:bench.grid.Green.ms}} ms.[^grid]

## Measured

### Whom he comes to trust

{{figure:green-trust|The mean of each arm's record after the ring board's benchmark of sixty games. The dashed line is the prior's 0.5.}}

The rank reward separated the arms where the earlier reward had not. Over sixty benchmark games on the ring board the records spread by about {{fact:green.arms.spread}} in mean: Plum and Mustard at {{fact:green.arms.ring.plum}} and {{fact:green.arms.ring.mustard}}, White at {{fact:green.arms.ring.white}}, Peacock at {{fact:green.arms.ring.peacock}} and Scarlett at {{fact:green.arms.ring.scarlett}}, which is the order the benchmark itself ranks the methods at the end of a game.[^glossary] On the Classic board the same run left him leaning on Mustard ({{fact:green.arms.grid.mustard}}) and Plum ({{fact:green.arms.grid.plum}}) and away from Peacock ({{fact:green.arms.grid.peacock}}) and Scarlett ({{fact:green.arms.grid.scarlett}}).[^grid]

### The quality of his numbers

{{table:bench.grid|The six methods on the Classic board: log-loss at four checkpoints, {{fact:bench.grid.games}} games, 15 September 2026.}}

Green's benchmark loss reflects which arms were selected. In the ring-board run, his final loss was {{fact:bench.ring.Green.100}}, joint-lowest with Plum, and his final first-choice accuracy was {{fact:bench.ring.Green.top1}}, the highest of the six. In the Classic-board run, final loss was {{fact:bench.grid.Green.100}}, second-lowest. He beat the uniform baseline at all four checkpoints, including halfway: {{fact:bench.grid.Green.50}} versus {{fact:bench.grid.uniform.50}}. Computing all five arms made his runtime comparable to Plum's plus the other methods' costs.[^ring][^grid]

### At the table

{{table:green.threshold|Green with only his accusation threshold moved, three arenas of 24 games on the Classic board, 15 September 2026.}}

Green won {{fact:arena.ring.Green.win}}% of his games in the tuned ring-board arena and none of sixteen in the first Classic-board arena. Lowering the threshold produced only one win in sixteen, with two wrong accusations at 0.5, so the preset was retained. Across nine arenas that day, his win rates spanned {{fact:green.swing}} per cent. A confirmation run using the original 24 deals gave {{fact:green.confirm.win}}% wins with his settings unchanged but other characters retuned. The outcomes varied with the opposition as well as the sequence of play; a single small arena does not establish his competitive strength.[^tuned]

In the twin arenas, adding [[Claude]] changed Green's win rate from {{fact:twin.ring.Green.win_base}}% to {{fact:twin.ring.Green.win_llm}}% on the ring board and from {{fact:twin.grid.Green.win_base}}% to {{fact:twin.grid.Green.win_llm}}% on the Classic board. These differences were within the reported sampling uncertainty.[^twin]

## Limitations

- **Each prediction comes from one arm.** On an individual observation, Green returns one constituent belief unchanged. Adaptively selecting arms may outperform a fixed arm across a run, but selection does not improve that arm's current probabilities.
- **Game feedback is sparse.** An arena game supplies one update from the final predictions. This does not directly teach which method is best at each earlier stage.
- **He is slow.** Every call pays for every arm.
- **The reward is a ranking, not a measure.** An arm that is a shade better than the rest scores the same 1 as one that is far better; the record knows the order of the arms and nothing of the gaps.

## See also

- [[Mr. Green]], the character who plays by this method
- [[Exact posterior enumeration]], [[Decision tree]], [[Markov chain]], [[Dempster-Shafer theory]] and [[Naive Bayes]], the five arms
- [[Belief]], where the five answers to the Rope question are set side by side
- [[Belief benchmark]], whose lessons his record was built on
- [[w:Multi-armed bandit|Multi-armed bandit]], [[w:Thompson sampling|Thompson sampling]] and [[w:Ensemble learning|ensemble learning]] on Wikipedia

## References

{{references}}

[^sutton]: {{cite:sutton-barto|Chapter 2, "Multi-armed Bandits"}}
[^thompson]: {{cite:thompson-1933}}
[^persona]: {{cite:clude_llm/personas/Green.md|the character's persona}}
[^phase5]: {{cite:docs/phase5-plan.md|4.4 Green: a reward with signal in it}}
[^module]: {{cite:clude_agents/bandit.py|`BanditAgent.select_action` and `observe`, `rank_rewards`, `_Candidate`, and the module's notes}}
[^arena]: {{cite:docs/architecture.md|Arena, sweeps and game records (Phase 5d)}}
[^port]: {{cite:CLAUDE.md|Settled decisions (David's)}} The structure mirrors David's `rps` repository.
[^memory]: {{cite:docs/logbooks.md|Tier 1: method memory}}
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^glossary]: {{cite:docs/strategy-glossary.md|Green -- Bandit ensemble over the other five}}
[^ring]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^tuned]: {{cite:docs/strategy-glossary.md|Tuned presets on the grid (Stage 1e, 2026-09-15)}}
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}

{{navbox:clude}}
