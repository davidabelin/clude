---
title: Bandit ensemble
short: Mr. Green's method: trust whichever of the other five has been doing best
categories: Methods
redirects: Bandit, Multi-armed bandit, Thompson sampling, Green's method, Ensemble, The ensemble
dyk: ... that [[Mr. Green]] has no method of his own, and that after sixty games on the ring board he trusted [[Professor Plum]] and [[Colonel Mustard]] twice as much as [[Miss Scarlett]]?
dyk: ... that the [[bandit ensemble]] learns from one lesson a game, and that the lesson is a ranking, not a mark?
---
{{infobox
title: Bandit ensemble
Played by | [[Mr. Green]]
In a phrase | Opportunistic; only as good as the method he is trusting
Module | `bandit.py`
Evidence used | The other five methods' beliefs, and how each has fared
Assumes | The method that has been closest to the truth lately will be again
Cost | About {{fact:bench.grid.Green.ms}} ms a call: everyone else's, added up
= The arms
How many | {{code:green.arms}}, one per other method
Each arm's record | A Beta distribution, from Beta(1, 1)
A lesson | A rank from 1 (closest to the truth) to 0, weighted {{code:green.step_size}}
Forgetting | The record decays towards the prior by {{code:green.decay}} a lesson
}}

The **bandit ensemble** is the method by which [[Mr. Green]] forms his [[belief]] about what is in [[the envelope]], or more exactly borrows it. Green has no way of reasoning of his own. On every turn he asks each of the other five [[Category:Methods|methods]] what it believes, and plays the belief of one of them, whole. Which one is decided by a record he keeps of how well each has done: after every game the five are ranked by how close they came to the truth, and the record of each is updated. Over many games the methods that are usually right are trusted most often, and the ones that are usually wrong are tried now and then in case they have improved.

Choosing among several options of unknown worth, each of which teaches you its worth only when you choose it, is the [[w:Multi-armed bandit|multi-armed bandit]] problem, named for a row of [[w:Slot machine|slot machines]] with different and unknown odds. Green's five arms are the five methods, and he solves the problem by [[w:Thompson sampling|Thompson sampling]], one of the oldest and simplest ways to do it: keep a probability distribution over each arm's worth, draw one number from each, and play the arm whose draw is highest. An arm with a good record draws high most of the time; an uncertain arm draws high sometimes. The balance between using what has worked and testing what might, between *exploitation* and *exploration*, is the oldest problem in [[w:Reinforcement learning|reinforcement learning]], and it is the first chapter of the textbook.[^sutton][^thompson]

The method is therefore as good as whichever arm it is trusting, and as slow as all five arms together: it inherits [[Professor Plum]]'s count and [[Colonel Mustard]]'s tree whether or not it ends up using them. Green is "exactly as good as the mind you are currently borrowing, and you know it", as his [[persona]] puts it.[^persona]

## At the table

!!! example "Worked example: the Rope question, and the lesson after it"
    {{figure:green-arms|Each arm's record after one lesson. Every arm began at Beta(1, 1), the flat line; one question, scored against its answer, has already bent each one.}}

    Late in a three-handed game, every card is placed except four: of the suspects, **Mrs. White** or **Mrs. Peacock** is in the envelope; of the weapons, the **Rope** or the **Wrench**; and [[Colonel Mustard]] has just shown [[Mr. Green]] a card after Green suggested *Mrs. Peacock, with the Rope, in the Hall*, so Mustard holds Peacock or the Rope.

    Green asks his five arms for the probability that Mrs. White is in the envelope and gets five answers: [[Miss Scarlett]]'s tally says {{code:example.scarlett.1.White}}, [[Professor Plum]]'s count {{code:example.plum.White}}, [[Mrs. Peacock]]'s bounds {{code:example.peacock.White}}, [[Colonel Mustard]]'s tree {{code:example.mustard.White}} and [[Mrs. White]]'s chain {{code:example.white.White}}. Which one he plays depends on his record. In a first game, with every arm at Beta(1, 1), the draws are coin tosses and he plays any of them; with the record the benchmark left him he would most likely play Mustard's or Plum's.

    Then the game ends and the envelope is revealed: White, the Wrench, the Study. Each arm's belief is scored by [[log-loss]] on the three true cards: Peacock {{code:example.green.loss.Peacock}}, Plum {{code:example.green.loss.Plum}}, Scarlett {{code:example.green.loss.Scarlett}}, Mustard {{code:example.green.loss.Mustard}}, White {{code:example.green.loss.White}} (lower is better). The arms are ranked: the best scores a reward of 1, the worst 0, the three between at even spacing. Each arm's record is a [[w:Beta distribution|Beta distribution]] with two counts, successes and failures, both starting at 1; the reward times {{code:green.step_size}} is added to the one and its shortfall times {{code:green.step_size}} to the other. After this single lesson Peacock's arm stands at Beta({{code:example.green.alpha.Peacock}}, {{code:example.green.beta.Peacock}}) with a mean of {{code:example.green.mean.Peacock}}, Plum's at mean {{code:example.green.mean.Plum}}, Scarlett's {{code:example.green.mean.Scarlett}}, Mustard's {{code:example.green.mean.Mustard}} and White's {{code:example.green.mean.White}}.

One lesson is not a verdict: on this one question Peacock's overshoot happened to land nearer the truth than Plum's exact count, and the rank rewards her for it. Over sixty games the order comes out quite differently (below). The example shows the mechanism, which is all it is meant to show: the arms answer, the truth arrives, the arms are ranked, and the ranking becomes the next game's bias.

## How it works

### Thompson sampling

Each arm has a record of two numbers, $\alpha$ and $\beta$, which together define a Beta distribution: a curve on the interval from 0 to 1 that says how likely the arm is to be the best. At the start both are 1 and the curve is flat, every value equally likely. On every turn Green draws one random number from each arm's curve and plays the arm whose number is highest. An arm whose curve is piled up near 1 draws high nearly always; an arm whose curve is piled up near 0 draws high rarely but not never; an arm whose curve is still flat, because it has not been tested, draws high about as often as not. This is Thompson sampling, and it has a property that makes it the right tool here: an arm is played with exactly the probability that it is the best, according to the record. An arm that might be best is tried; an arm that is surely worse is left alone.[^thompson][^sutton]

### The lesson

Thompson sampling needs a *reward* after each play, and the reward is where the method had to be designed. The obvious one, how much probability the arm gave to the three true cards, failed: the [[deduction floor]] that every method shares does most of the work in every belief, so all five arms scored within a percent of one another, their records moved together, and Green chose among them at random. The reward adopted instead is a **rank**. On each revealed envelope the arms are ordered by their log-loss; the best scores 1, the worst 0, and the others fall at even steps between, with ties sharing their mean position. A rank compares the arms against one another on the same position, which is the only thing Green needs to learn.[^phase5][^module]

Before the reward is added, each record decays a step towards the flat prior, so that old evidence fades and an arm that has recently improved can be rediscovered. Then the arm's successes rise by the reward times a step size and its failures by the shortfall times the same, so one lesson moves a fresh record a long way and a well-established one a little.[^module]

### When the lessons come

A lesson needs the truth, and the truth arrives once a game, when the envelope is opened. So in the [[arena]] Green learns once per game; in the [[belief benchmark]], where every position comes with its answer, once per position. The record is kept across games, which is what "learns across games" means for him, and since Phase 7 it is also kept across runs of the program.[^arena]

## Formally

### The Beta distribution and the update

An arm's record is $\text{Beta}(\alpha, \beta)$, with density proportional to $x^{\alpha - 1}(1 - x)^{\beta - 1}$ on $[0, 1]$ and mean $\alpha / (\alpha + \beta)$. $\text{Beta}(1, 1)$ is the uniform distribution. For a reward $r \in [0, 1]$, step size $s$ and decay $d$, the update is

$$ \alpha \leftarrow \frac{\alpha - 1}{d} + 1 + s\,r, \qquad \beta \leftarrow \frac{\beta - 1}{d} + 1 + s\,(1 - r) $$

with $s = {{code:green.step_size}}$ and $d = {{code:green.decay}}$: the excess over the prior shrinks by the decay, then the lesson is added. With $d = 1$ and whole-number rewards this would be the ordinary [[w:Bayesian inference|Bayesian update]] of a Beta prior on a coin's bias after one toss, the Beta being the [[w:Conjugate prior|conjugate prior]] of a coin; the decay turns it into a record with a memory of a few dozen lessons rather than all of them.[^module]

### The rank reward

For arms with losses $\ell_1 \le \ell_2 \le \dots \le \ell_n$, the arm in position $i$ (counting from 0) receives

$$ r_i = 1 - \frac{i}{n - 1} $$

and arms with equal losses share the mean of the positions they span. With five arms the rewards are 1, 3/4, 1/2, 1/4 and 0.[^module]

### Thompson sampling as probability matching

If $\theta_k$ is the unknown worth of arm $k$ and the record is a posterior over each $\theta_k$, then drawing $\tilde\theta_k$ from each posterior and playing $\arg\max_k \tilde\theta_k$ plays arm $k$ with probability $P(\theta_k = \max_j \theta_j)$ under the posterior. This is [[w:Thompson sampling|probability matching]], and it is why no separate rule for exploration is needed: the uncertainty in the record is the exploration.[^thompson]

## In clude

The module is `clude_agents/bandit.py`, and it is a port. David's earlier project, a [[w:Rock paper scissors|rock-paper-scissors]] tournament, had a Thompson-sampling bandit over move-predicting heuristics; here the structure is the same and the arms are literal instances of the other five agents, built fresh when Green is reset. The draws come from Python's own `betavariate`, so that the package needs no numerical library the rest of clude does without.[^module][^port]

Three things about the implementation are worth knowing. The arm's belief is played *outright*, not blended: Green's probabilities on a given turn are exactly one other method's, and his belief carries a note of whose. The record is saved after every game and restored before the next as his method memory, one of the three characters' Tier 1 memories; it cannot be rebuilt from stored game records, since no record holds what his arms predicted at the time, so it is only ever accumulated.[^memory] And every arm is consulted on every call, which is where his cost comes from: [[Professor Plum]]'s count alone is about {{fact:bench.grid.Plum.ms}} ms at mid-game on the Classic board, and Green's call is {{fact:bench.grid.Green.ms}}.[^grid]

## Measured

### Whom he comes to trust

{{figure:green-trust|The mean of each arm's record after the ring board's benchmark of sixty games. The dashed line is the prior's 0.5.}}

The rank reward separated the arms where the earlier reward had not. Over sixty benchmark games on the ring board the records spread by about {{fact:green.arms.spread}} in mean: Plum and Mustard at {{fact:green.arms.ring.plum}} and {{fact:green.arms.ring.mustard}}, White at {{fact:green.arms.ring.white}}, Peacock at {{fact:green.arms.ring.peacock}} and Scarlett at {{fact:green.arms.ring.scarlett}}, which is the order the benchmark itself ranks the methods at the end of a game.[^glossary] On the Classic board the same run left him leaning on Mustard ({{fact:green.arms.grid.mustard}}) and Plum ({{fact:green.arms.grid.plum}}) and away from Peacock ({{fact:green.arms.grid.peacock}}) and Scarlett ({{fact:green.arms.grid.scarlett}}).[^grid]

### The quality of his numbers

{{table:bench.grid|The six methods on the Classic board: log-loss at four checkpoints, {{fact:bench.grid.games}} games, 15 September 2026.}}

Because he plays a borrowed belief, Green's score tracks the arms he trusts. On the ring board he was joint-best with Plum at the end, {{fact:bench.ring.Green.100}}, with the best first choice of the six, {{fact:bench.ring.Green.top1}}; on the Classic board he is second-best at the end, {{fact:bench.grid.Green.100}}, and ahead of the baseline throughout, including the halfway checkpoint ({{fact:bench.grid.Green.50}} to {{fact:bench.grid.uniform.50}}) where Plum himself is not. The notes describe him as tracking "Plum's quality at a Plum-plus-everyone price".[^ring][^grid]

### At the table

{{table:green.threshold|Green with only his accusation threshold moved, three arenas of 24 games on the Classic board, 15 September 2026.}}

In the [[arena]] Green's results are the noisiest of the six. He won {{fact:arena.ring.Green.win}}% of his games at the tuned presets on the ring board, and on the Classic board's first arena no game at all, accusing in only one of sixteen. Lowering his threshold bought one win in sixteen and, at 0.5, two wrong accusations, so the preset stood; what limits him is pace, not his dial, since the belief he borrows rarely reaches even 0.5 before somebody else ends the game. Then, across nine arenas that day in which his own settings were touched in only two, he won {{fact:green.swing}} per cent of his games, and {{fact:green.confirm.win}}% of the very deals he had lost every one of, with nothing of his changed. The zero was the low draw of a noisy number, and the project's notes use his record as the standing warning about what twenty games can show.[^tuned]

With [[Claude]] in his seat he moved within the noise: {{fact:twin.ring.Green.win_base}}% to {{fact:twin.ring.Green.win_llm}}% on the ring, {{fact:twin.grid.Green.win_base}}% to {{fact:twin.grid.Green.win_llm}}% on the Classic board.[^twin]

## Limitations

- **He is only as good as his arms.** An ensemble that plays one belief whole cannot be better than its best arm on any turn, and is worse whenever it picks another.
- **He learns slowly.** One lesson a game is a thin diet for five records, and a game's lesson is one ranking on one position, the final one.
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
