---
title: Markov chain
short: Mrs. White's method: what a player's questions give away
categories: Methods
redirects: Markov model, Markov chains, White's method, Markov, Two-state chain
dyk: ... that [[Mrs. White]] is the one character who reads the asking and not the answer, and that on the Rope question she comes out the opposite way from everyone else?
dyk: ... that a [[Markov chain]] with two states and four counts is the whole of Mrs. White's method, and the best belief of the six for most of a game?
---
{{infobox
title: Markov chain
Played by | [[Mrs. White]]
In a phrase | Reads people rather than cards
Module | `markov.py`
Evidence used | Each opponent's run of suggestions, as repeats and new questions
Assumes | A player who keeps naming a card has not been shown it
Cost | About {{fact:bench.grid.White.ms}} ms a call
= The chain
States | two: *new* and *repeat*
Fitted from | four transition counts per opponent, each starting at {{code:white.prior_cell}}
Read off | the long-run chance that the opponent repeats
}}

A **Markov chain** is the method by which [[Mrs. White]] forms her [[belief]] about what is in [[the envelope]]. It is the one method of the six that takes its evidence not from who could and could not answer a [[suggestion]] but from the suggestions themselves: which cards each opponent keeps asking about, and whether their questions are settling into a pattern. The reasoning behind it is a card-table commonplace. A player who names the same card turn after turn has not been shown it, and does not hold it; the card is still open for them, and that makes it a little more likely to be in the envelope. A player who has stopped asking about a card has found out where it is.

The chain is the machinery for "settling into a pattern". White reduces each opponent's history of suggestions to a string of two symbols, *repeat* (this suggestion names a card that player has named before) and *new* (every card in it is new to them), and fits to the string the simplest model of a sequence there is: one in which what comes next depends only on what came last. From the fitted model she reads the long-run chance that the opponent is repeating, and weights the cards they keep naming by it.[^glossary]

The method is named for the Russian mathematician [[w:Andrey Markov|Andrey Markov]], who first studied sequences with this one-step memory, and it is the first thing in [[w:Probability theory|probability]] that most people meet after independence.[^norris] In [[clude]] it produces a character who is, in her [[persona]]'s words, "better at knowing who is about to win than at knowing what they will say", and who, measured, has the best belief of the six for most of a game on the Classic board.[^persona][^grid]

## At the table

!!! example "Worked example: the Rope question"
    Late in a three-handed game White's [[detective notepad|notepad]] has every card placed except four: of the suspects, **Mrs. White** or **Mrs. Peacock** is in the envelope; of the weapons, the **Rope** or the **Wrench**; the other two are in [[Colonel Mustard]]'s hand. [[Mr. Green]] suggests *Mrs. Peacock, with the Rope, in the Hall*, and Mustard shows him a card she does not see.

    Every other method reads the showing. White reads the asking. Green has named Peacock and the Rope: they are cards he is still asking about, so cards he is less likely to hold, so cards a little more likely to be the envelope's. This is Green's first suggestion in her record, so his chain has nothing to go on and sits at its prior, a repeat probability of {{code:example.white.repeat}}. Each open card starts at a score of {{code:white.base_score}}; Peacock and the Rope gain one naming times {{code:example.white.repeat}}. Within the suspects that leaves Mrs. Peacock at **{{code:example.white.Peacock}}** and Mrs. White at **{{code:example.white.White}}**; within the weapons, the Rope at {{code:example.white.Rope}} and the Wrench at {{code:example.white.Wrench}}.

    It is the opposite of what [[Professor Plum]]'s count says, {{code:example.plum.White}} for Mrs. White, and of what every other method says. They have all used the fact that Mustard *showed* a card, which the floor gave them as "Mustard holds Peacock or the Rope". White's method does not read that fact at all; it is in the floor's mask, and the mask only ever rules cards out. What she has used instead is a fact about Green, and in this position it points the wrong way, because Green's asking about Peacock and the Rope was a guess like any other.

    Over a longer game the two readings converge: the cards an opponent keeps naming *are*, usually, the ones nobody has shown them, and by the middle of a game that is the best evidence at the table.

### The chain itself

{{figure:white-chain|One opponent's run of suggestions, each a repeat or all new, and the two-state chain fitted to it. In the long run this opponent repeats with probability {{code:example.chain.stationary.dec}}.}}

Suppose an opponent's eight suggestions so far read, in order, {{code:example.chain.sequence}}. There are {{code:example.chain.steps}} steps from one to the next, and White counts the four kinds: new to new {{code:example.chain.counts.00}}, new to repeat {{code:example.chain.counts.01}}, repeat to new {{code:example.chain.counts.10}}, repeat to repeat {{code:example.chain.counts.11}}. To each count she adds {{code:white.prior_cell}}, a phantom observation that keeps a short record from giving a certain answer, and divides: after a *new* suggestion the chance of a *repeat* next is {{code:example.chain.p01}}, and after a *repeat* the chance of a *new* is {{code:example.chain.p10}}. A chain that moves between its two states at those rates spends, in the long run, {{code:example.chain.stationary}} of its time repeating, about {{code:example.chain.stationary.dec}}. That is the number she reads off: this opponent is in a repeating regime, still fishing.

## How it works

### The symbols

For each opponent White keeps a tally of how many times they have named each card. Each suggestion of theirs becomes one symbol: *repeat* if any of its three cards had already been named by that opponent, *new* if none had. The card that made it a repeat is not recorded; the chain sees only the string of symbols. Alongside the tally she keeps a count of how much that opponent has been shown, one for each suggestion of theirs that was disproved and three for each that was not, squashed into a *closeness* between 0 and 1: how near the opponent is to solving. Nothing in clude consumes closeness yet; it is there for an *urgency* dial if one is ever added.[^module]

### Fitting the chain

A two-state chain is four numbers, the counts of each kind of step, and fitting it is counting. The counts start at {{code:white.prior_cell}} each, a [[w:Additive smoothing|Laplace prior]] of {{code:white.prior_mass}} phantom observations in all, so that an opponent who has made one suggestion, or none, reads as repeating half the time rather than as undefined. From the four counts come two transition probabilities, and from those the stationary distribution: the share of time the chain spends in each state once it has run long enough to forget where it started.[^module]

### The belief

Every card the [[deduction floor]] has not placed starts at a score of {{code:white.base_score}}, the floor's own flat prior. For each opponent, each card they have named gains their naming count times their stationary repeat probability. The scores then go through the step every method ends with: the floor sets to 0 any card it has ruled out and to 1 any it has proved, and what remains is scaled to sum to 1 within each category.[^base] A card nobody has named stays at its starting score and comes out merely unsuspicious. Before Phase 5 it came out at 0, impossible, and those zeros were {{fact:white.phase4.zeros}} per cent of White's error on the first benchmark.[^phase5]

## Formally

### A two-state chain

A [[w:Markov chain|Markov chain]] on states $\{0, 1\}$ ("new", "repeat") is a sequence $X_1, X_2, \dots$ in which $P(X_{t+1} = j \mid X_t = i, X_{t-1}, \dots) = P(X_{t+1} = j \mid X_t = i) = p_{ij}$: the next symbol depends on the present one and on nothing earlier. Its transition matrix is

$$ P = \begin{pmatrix} 1 - p_{01} & p_{01} \\ p_{10} & 1 - p_{10} \end{pmatrix} $$

and its stationary distribution, the $\pi$ with $\pi P = \pi$, is

$$ \pi_1 = \frac{p_{01}}{p_{01} + p_{10}}, \qquad \pi_0 = 1 - \pi_1 $$

whenever $p_{01} + p_{10} > 0$. For the chain in the figure, $p_{01} = {{code:example.chain.p01}}$ and $p_{10} = {{code:example.chain.p10}}$, so $\pi_1 = {{code:example.chain.stationary}}$.[^norris]

### The estimates

With $n_{ij}$ steps observed from $i$ to $j$ and a prior count $a$ on every cell,

$$ \hat p_{01} = \frac{n_{01} + a}{n_{00} + n_{01} + 2a}, \qquad \hat p_{10} = \frac{n_{10} + a}{n_{10} + n_{11} + 2a} $$

with $a = {{code:white.prior_cell}}$. This is the [[w:Maximum likelihood estimation|maximum-likelihood]] estimate of each row of $P$, smoothed. Nothing is said about how the chain started; White uses $\pi_1$, the long-run figure, rather than the probability of a repeat on the very next turn, which would be $p_{01}$ or $1 - p_{10}$ according to the last symbol.[^module]

### The score

For a card $c$ not yet placed, with $n_o(c)$ the number of times opponent $o$ has named it and $\pi_o$ that opponent's stationary repeat probability,

$$ s(c) = {{code:white.base_score}} + \sum_{o} n_o(c)\, \pi_o $$

and the belief is $s$ masked and normalised within each category. The direction of the heuristic, that a repeat raises a card's suspicion rather than lowering it, is a modelling choice the module states rather than a fact it derives.[^module]

## In clude

The module is `clude_agents/markov.py`. It descends from a heuristic in the project's earlier code, "a player who repeats a card probably doesn't hold it", whose documentation could not say whether a high number meant "knows where the card is" or "probably does not hold it". The rewrite settled on the second and replaced the heuristic with an actual chain.[^module][^legacy]

### Memory

White is one of the three characters whose method remembers from game to game, and hers remembers *people*. For each opponent she has met, the four transition counts from every stored game they played are summed and kept under that opponent's name. At a new table the Laplace prior for a known opponent is replaced by their own frequencies, spread over the same {{code:white.prior_mass}} phantom observations the prior had, so that the live sequence weighs exactly as before and only the starting shape of the chain is informed by the past. The choice is deliberate: a hundred games of history should not drown the regime she is watching now. Rebuilt from the stored games of one measurement run, her memory held {{fact:white.memory.green}} transitions for Green, {{fact:white.memory.mustard}} for Mustard and {{fact:white.memory.plum}} for Plum.[^memory][^phase7]

### What the model sees

When [[Claude]] plays her seat it is shown each opponent's repeat probability beside her belief, and the method was audible in the voice from the first recorded games: "Mustard's stopped fishing for the Candlestick and started asking about rooms".[^phase6]

## Measured

### The quality of her numbers

{{table:bench.ring|The six methods on the ring board, Phase 5: log-loss at four checkpoints. Lower is better.}}

On the ring board the chain had the best belief of the six at the halfway checkpoint, {{fact:bench.ring.White.50}} against the baseline's {{fact:bench.ring.uniform.50}}, and beat the baseline at every checkpoint; at the end it fell behind the three methods that read the floor's facts more closely, {{fact:bench.ring.White.100}} against Plum's {{fact:bench.ring.Plum.100}}. On the first benchmark of all, before the flat prior, it had been the worst belief of the six by a distance, {{fact:white.phase4}}, nearly all of it from unnamed cards read as impossible.[^ring][^phase4]

{{table:bench.grid|The same benchmark on the Classic board, {{fact:bench.grid.games}} games, 15 September 2026.}}

On the Classic board she is the best method at every checkpoint until the end, {{fact:bench.grid.White.25}}, {{fact:bench.grid.White.50}} and {{fact:bench.grid.White.75}}, and at the end second only to Mustard. The project's notes put the mid-game strength down to the floor-bot regime the benchmark is played in, where players do re-name what they have not resolved, which is exactly the behaviour the chain reads.[^grid][^glossary]

### At the table

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, 15 September 2026.}}

White has not accused wrongly in any arena on either board, with her threshold at the neutral {{code:preset.White.accuse_threshold}} so that any wrong accusation would have been the method's. She names her own cards in suggestions more than anyone, {{fact:arena.grid.White.named}} a game on the Classic board, which is her [[bluff rate]] of {{code:preset.White.bluff_rate}}, the highest of the six; and she wins by patience, {{fact:arena.ring.White.win}}% on the ring board and {{fact:arena.grid.first.White.win}}% then {{fact:arena.grid.White.win}}% in two Classic-board arenas in which nothing of hers changed, a swing the notes record as the measurement's noise made visible.[^arena][^tuned]

With [[Claude]] in her seat at a four-seat table she won {{fact:twin.grid.White.win_llm}}% of her games, the most of anyone, as she had without it; what changed was her bluffing, which fell from {{fact:twin.grid.bluff.white.base}} own-card suggestions a game to {{fact:twin.grid.bluff.white.llm}}. The model treats naming its own card as a wasted question rather than a feint.[^twin]

## Limitations

- **The direction is assumed.** That repeating raises a card's suspicion is stated, not derived; a player who repeats a card they hold, to mislead, reads to her as fishing.
- **It ignores the showing.** The strongest fact a disproof leaves, "this player holds one of these", reaches her only through the floor's mask, which cannot raise a card's score. The Rope question shows the cost.
- **Unusual players break the pattern.** A chatty human, or a model that never repeats, gives her a chain fitted to nothing. Her strength is on who is close to solving; her weakness, as the notes say, "on the envelope itself if a player's pattern is atypical".
- **The symbol throws away the card.** A repeat is a repeat whichever card made it so, and the chain learns a player's habit of repeating, not which cards they repeat; the tally of namings carries the rest.

## See also

- [[Mrs. White]], the character who plays by this method
- [[Exact posterior enumeration]] and [[Naive Bayes]], which read the answer rather than the question
- [[Belief]], where the six methods' answers to the Rope question are compared
- [[Logbook]], where her memory of each opponent's habits is kept
- [[Bluffing]], the habit of hers that the method invites
- [[w:Markov chain|Markov chain]] and [[w:Stationary distribution|stationary distribution]] on Wikipedia

## References

{{references}}

[^glossary]: {{cite:docs/strategy-glossary.md|White -- Markov model over suggestion sequences}}
[^norris]: {{cite:norris-1997|Chapter 1, discrete-time Markov chains; the two-state chain's stationary distribution is its first worked example}}
[^persona]: {{cite:clude_llm/personas/White.md|the character's persona}}
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^module]: {{cite:clude_agents/markov.py|`suggestion_patterns`, `_stationary_repeat_probability`, `prior_cells`, `MarkovAgent.select_action` and the module's notes}}
[^base]: {{cite:clude_agents/base.py|`mask_and_normalize`}}
[^phase5]: {{cite:docs/phase5-plan.md|4.3 White: the same zero, a different cause}}
[^legacy]: {{cite:docs/architecture.md|Method-to-suspect mapping}}
[^memory]: {{cite:docs/logbooks.md|Tier 1: method memory}}
[^phase7]: {{cite:docs/strategy-glossary.md|Phase 7: memory (2026-09-14)}}
[^phase6]: {{cite:docs/phase6-plan.md|6c, the real backend (2026-09-12; live checks done 2026-09-13)}}
[^ring]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^phase4]: {{cite:docs/strategy-glossary.md|Phase 4 benchmark results (RandomBot regime, historical)}}
[^arena]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}
[^tuned]: {{cite:docs/strategy-glossary.md|Tuned presets on the grid (Stage 1e, 2026-09-15)}}
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}

{{navbox:clude}}
