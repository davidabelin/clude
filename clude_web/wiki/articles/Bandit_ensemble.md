---
title: Bandit ensemble
short: Mr. Green's adaptive selection among the other five methods
categories: Methods
redirects: Bandit, Multi-armed bandit, Thompson sampling, Green's method, Ensemble, The ensemble
dyk: ... that [[Mr. Green]] selects from five other methods, and that after sixty benchmark games the mean arm scores for Plum and Mustard were about twice Scarlett's?
dyk: ... that in arena play the [[bandit ensemble]] updates once per completed game, using the methods' ranked log-loss scores?
---
{{infobox
title: Bandit ensemble
Played by | [[Mr. Green]]
In a phrase | Selects one of five methods using learned score records
Module | `bandit.py`
Evidence used | The other five methods' beliefs, and how each has fared
Assumes | The method that has been closest to the truth lately will be again
Cost | All five arms per call; the Plum arm is now a network rather than enumeration
= The arms
How many | {{code:green.arms}}, one per other method
Each arm's record | A Beta distribution, from Beta(1, 1)
A lesson | A rank from 1 (closest to the truth) to 0, weighted {{code:green.step_size}}
Forgetting | The record decays towards the prior by {{code:green.decay}} a lesson
}}

The **bandit ensemble** is [[Mr. Green]]'s method for selecting a [[belief]] from the other five [[Category:Methods|methods]]. On each call it computes all five beliefs and adopts one without blending them. Its choice uses a record of how accurately each method has predicted revealed envelopes. After feedback, it ranks their predictions by [[log-loss]] and updates that record. Methods with stronger recent records tend to be selected more often, while random sampling allows alternatives to be tried.[^module]

The design draws on the [[w:Multi-armed bandit|multi-armed bandit]] problem: choosing among options with uncertain rewards, named after [[w:Slot machine|slot machines]]. Green uses [[w:Thompson sampling|Thompson sampling]], drawing a score from each arm's distribution and selecting the largest. This balances *exploitation*, using a method with a good record, against *exploration*, trying one whose value is less certain.[^sutton][^thompson] Unlike a classical bandit, Green receives feedback for all five arms when the envelope is revealed, rather than only for the selected arm.

Green's current belief is exactly the selected method's output, but the computation cost is that of all five methods together. Until Phase 12 that included [[PlumOG]]'s enumeration, the slowest call in the game; his Plum arm is now [[Professor Plum]]'s network, which answers in under a millisecond. His [[persona]] turns this dependence into the character's opportunistic voice.[^persona]

## At the table

!!! example "Worked example: the Rope question, and the lesson after it"
    {{figure:green-arms|Each arm's record after one lesson. Every arm began with the flat Beta(1, 1) distribution. The ranked scores from one revealed envelope have updated these selection records.}}

    In the shared comparison position, an observer has every card placed except four: **Mrs. White**, **Mrs. Peacock**, the **Rope** and the **Wrench**. One suspect and one weapon are in the envelope; the other two are in [[Colonel Mustard]]'s hand. The Hall is known to be in [[Mr. Green]]'s hand. Green suggests *Mrs. Peacock, with the Rope, in the Hall*, and Mustard shows him a card hidden from the observer. Green's ensemble is evaluated on the observer's view, not on the suggester's private knowledge, so it receives the same evidence as the other methods.

    Green asks his five arms for the probability that Mrs. White is in the envelope and gets five answers: [[Miss Scarlett]]'s tally says {{code:example.scarlett.1.White}}, [[Professor Plum]]'s network {{code:example.policy.White}}, [[Mrs. Peacock]]'s bounds {{code:example.peacock.White}}, [[Colonel Mustard]]'s tree {{code:example.mustard.White}} and [[Mrs. White]]'s chain {{code:example.white.White}}. Which one he plays depends on his record. In a first game, with every arm at Beta(1, 1), each draw is uniform on [0, 1] and each arm is equally likely to win; a saved method record can change those chances, but its ranking depends on the training history.

    Then the game ends and the envelope is revealed: White, the Wrench, the Study. Each arm's belief is scored by [[log-loss]] on the three true cards: Peacock {{code:example.green.loss.Peacock}}, Plum {{code:example.green.loss.Plum}}, Scarlett {{code:example.green.loss.Scarlett}}, Mustard {{code:example.green.loss.Mustard}}, White {{code:example.green.loss.White}} (lower is better). The arms are ranked: the best scores a reward of 1, the worst 0, the three between at even spacing. Each arm's record is a [[w:Beta distribution|Beta distribution]] with two counts, successes and failures, both starting at 1; the reward times {{code:green.step_size}} is added to the one and its shortfall times {{code:green.step_size}} to the other. After this single lesson Peacock's arm stands at Beta({{code:example.green.alpha.Peacock}}, {{code:example.green.beta.Peacock}}) with a mean of {{code:example.green.mean.Peacock}}, Plum's at mean {{code:example.green.mean.Plum}}, Scarlett's {{code:example.green.mean.Scarlett}}, Mustard's {{code:example.green.mean.Mustard}} and White's {{code:example.green.mean.White}}.

On this revealed envelope, Peacock's estimate gives the lowest loss and White's the highest; Plum's current network is second-highest. The network has read Green's naming of Peacock as evidence for her, and put Mrs. White at {{code:example.policy.White}} where counting the surviving deals gives {{code:example.plum.White}}. Even the exact count would not have won this lesson outright, since a probability estimate can be right without giving the most probability to the outcome of one particular deal. The reward reflects one realised outcome; it does not establish which method is best in expectation.[^policy]

## How it works

### Thompson sampling

Each arm has two parameters, $\alpha$ and $\beta$, defining a [[w:Beta distribution|Beta distribution]] over scores from 0 to 1. Both start at 1, giving a uniform distribution. On each call, Green draws one score per arm and selects the largest. Strong records tend to produce higher draws; uncertain records leave more opportunity for exploration. These distributions track decayed, fractional rank rewards, so they are heuristic records rather than calibrated probabilities that a method is best.[^module][^thompson][^sutton]

### The lesson

The update needs a reward that distinguishes the arms. The initial reward, based directly on probability assigned to the true cards, gave very similar values because the shared [[deduction floor]] supplied much of every belief. Phase 5 replaced it with a **rank reward**. At each reveal, methods are ordered by log-loss: the best receives 1, the worst 0, and the others evenly spaced values. Ties share their average rank. This compares methods on the same observation, while discarding the size of the loss differences.[^phase5][^module]

Before the reward is added, each record decays a step towards the flat prior, so that old evidence fades and an arm that has recently improved can be rediscovered. Then the arm's successes rise by the reward times a step size and its failures by the shortfall times the same, so one lesson moves a fresh record a long way and a well-established one a little.[^module]

### When the lessons come

Green can update only when the envelope is known. He therefore learns once per completed [[arena]] game, or once per scored position in the [[belief benchmark]]. His record persists across games and, since Phase 7, across program runs when memory is enabled.[^arena]

!!! algorithm "Green's choice, and his lesson"
        Input: the five other methods (arms), each with a record Beta(α, β)
        To decide:
            ask every arm for its belief
            for each arm: draw θ from Beta(α, β)
            use the belief of the arm with the largest θ
        When an envelope is revealed:
            score every arm's last belief by log-loss on the true cards
            rank the arms: best reward 1, worst 0, the rest evenly between
            for each arm with reward x:
                α ← 1 + (α − 1) / decay;   β ← 1 + (β − 1) / decay     (fade towards the prior)
                α ← α + step × x;          β ← β + step × (1 − x)

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

The chosen arm's probabilities are returned unchanged, with its name recorded in the belief's extras. Green's record is saved after each game and restored as Tier 1 method memory. The current memory builder does not reconstruct the arm counts from stored games, because those records do not preserve the predictions made by the arms at the time.[^memory] Phase 14 therefore began honestly from Beta(1,1), compared step sizes 1, 2 and 4 with decay rates 1.02, 1.05 and 1.10, then trained and validated on separate 200-game blocks. Step 4 and decay 1.05 cleared the held-out gates; the accepted state is fresh training, not a reconstruction of old live posteriors.[^phase14] Every call consults all five arms. Historical enumeration-era timings included PlumOG's search and do not describe the present network ensemble.

## Phase 14 validation

{{table:methods.phase14.green|Green's former comparison state and accepted rebuild on the same 19 validation deals and 264 private snapshots. Lower log-loss is better.}}

These are configuration-selection results, with the final state released on 18 October. The validation set helped choose the candidate, so it is not an independent confirmation set. The [[measurement record]] gives the separate arena outcomes and explains why passing a guardrail is not proof of improved winning.[^validation]

## Measured

### Whom he comes to trust

{{figure:green-trust|Historical ring-board mean arm records, with PlumOG, after sixty benchmark games. The dashed line is the prior's 0.5.}}

The rank reward separated the arms where the earlier reward had not. Over the earlier benchmark's sixty games the records spread by about {{fact:green.arms.spread}} in mean: Plum and Mustard at {{fact:green.arms.ring.plum}} and {{fact:green.arms.ring.mustard}}, White at {{fact:green.arms.ring.white}}, Peacock at {{fact:green.arms.ring.peacock}} and Scarlett at {{fact:green.arms.ring.scarlett}}, which is the order the benchmark itself ranks the methods at the end of a game.[^glossary] On the Classic board the same run left him leaning on Mustard ({{fact:green.arms.grid.mustard}}) and Plum ({{fact:green.arms.grid.plum}}) and away from Peacock ({{fact:green.arms.grid.peacock}}) and Scarlett ({{fact:green.arms.grid.scarlett}}).[^grid]

### The quality of his numbers

{{table:bench.grid|Historical comparison. The six methods on the Classic board: log-loss at four checkpoints, {{fact:bench.grid.games}} games, 15 September 2026.}}

Green's benchmark loss reflects which arms were selected. In the earlier run, his final loss was {{fact:bench.ring.Green.100}}, joint-lowest with Plum, and his final first-choice accuracy was {{fact:bench.ring.Green.top1}}, the highest of the six. In the Classic-board run, final loss was {{fact:bench.grid.Green.100}}, second-lowest. He beat the uniform baseline at all four checkpoints, including halfway: {{fact:bench.grid.Green.50}} versus {{fact:bench.grid.uniform.50}}. Computing all five arms made his runtime comparable to Plum's plus the other methods' costs.[^ring][^grid]

### At the table

{{table:arena.phase14|The current-setting rows from Phase 14's isolated headless screens, 40 seat-games per character.}}

Green won {{fact:arena.phase14.Green.win}}% of the current control and made a wrong accusation in {{fact:arena.phase14.Green.wrong}}%.[^current] Phase 14 also screened his threshold separately and retained 0.75 because no nearby value cleared the personality and outcome guardrails. A 40-seat-game row does not establish his competitive strength.

In the twin arena, adding [[Claude]] changed Green's win rate from {{fact:twin.grid.Green.win_base}}% to {{fact:twin.grid.Green.win_llm}}%. The difference was within the reported sampling uncertainty.[^twin]

## Limitations

- **Each prediction comes from one arm.** On an individual observation, Green returns one constituent belief unchanged. Adaptively selecting arms may outperform a fixed arm across a run, but selection does not improve that arm's current probabilities.
- **Game feedback is sparse.** An arena game supplies one update from the final predictions. This does not directly teach which method is best at each earlier stage.
- **He pays for every arm.** Selecting one estimate still requires computing all five. Replacing enumeration with the network removed the former dominant search cost; the current ensemble should not inherit PlumOG's timing.
- **The reward is a ranking, not a measure.** An arm that is a shade better than the rest scores the same 1 as one that is far better; the record knows the order of the arms and nothing of the gaps.

## See also

- [[Mr. Green]], the character who plays by this method
- [[Regularised Nash dynamics]], [[Decision tree]], [[Markov chain]], [[Dempster-Shafer theory]] and [[Naive Bayes]], the five arms ([[exact posterior enumeration]] until Phase 12)
- [[Belief]], where the five answers to the Rope question are set side by side
- [[Belief benchmark]], whose lessons his record was built on
- [[w:Multi-armed bandit|Multi-armed bandit]], [[w:Thompson sampling|Thompson sampling]] and [[w:Ensemble learning|ensemble learning]] on Wikipedia

## References

{{references}}

[^validation]: {{cite:docs/strategy-glossary.md|Phase 14 adaptive-method validation (2026-10-17)}}

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
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}
[^current]: {{cite:docs/strategy-glossary.md|Phase 14 dial recalibration (2026-10-18)}}
[^phase14]: {{cite:docs/phase14-plan.md|Plum and Green — retrained; Run 3 promoted locally}}
[^policy]: {{cite:clude_web/wiki/facts.py|`rope_observation` and `rope_question`}}

{{navbox:clude}}
