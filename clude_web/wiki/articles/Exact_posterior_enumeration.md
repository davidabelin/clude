---
title: Exact posterior enumeration
short: Counting consistent deals to estimate envelope probabilities
categories: Methods
redirects: Exact enumeration, Enumeration, Plum's method, Counting deals, Exact posterior
dyk: ... that [[exact posterior enumeration]] answered the Rope question in {{code:example.plum.nodes}} steps, and that a player at a six-seat table with one card of each kind in hand initially faces {{code:deals.6}} deals?
dyk: ... that the sample [[Professor Plum]] falls back on was raised from 2,000 to {{code:plum.sample_budget}} deals, and that in the recorded budget comparison, raising the sample budget helped more than raising the search budget?
---
{{infobox
title: Exact posterior enumeration
Played by | [[Professor Plum]]
In a phrase | Exhaustive when the search finishes; sampled otherwise
Module | `exact_enum.py`
Evidence used | Everything the [[deduction floor]] knows, joint facts included
Assumes | Every deal still possible is equally likely
Cost | About {{fact:bench.grid.Plum.ms}} ms a call at the Classic-board halfway checkpoint; Green also pays this cost
= The two budgets
Search steps | {{code:plum.node_budget}}
Random deals, after that | {{code:plum.sample_budget}}
}}

**Exact posterior enumeration** is [[Professor Plum]]'s method of estimating which [[Clue#The cards|cards]] are in [[the envelope]]. It lists every deal consistent with the [[deduction floor]] and calculates each card's [[w:Probability|probability]] as its share of the surviving deals. When the search finishes, this gives exact card probabilities under a model that treats consistent deals as equally likely. The model uses the logical consequences of suggestions and disproofs, but does not account for opponents' preferences when choosing suggestions or cards to show.[^module]

The search can be too large to finish between turns. It stops after {{code:plum.node_budget}} steps and falls back on up to {{code:plum.sample_budget}} [[w:Monte Carlo method|random draws]]. The accepted draws estimate the same card probabilities, with sampling noise and construction bias. In the original [[Classic board]] benchmark, the fallback was used in {{fact:plum.fallback.calls}} of {{fact:bench.grid.snapshots}} calls. That is a proportion of benchmark calls, not a measure of how much of each game was spent sampling.[^grid]

The counting principle is the ratio of favourable to possible cases associated with [[w:Pierre-Simon Laplace|Laplace]]. Plum implements it through [[w:Backtracking|backtracking]], a standard [[w:Artificial intelligence|artificial intelligence]] technique for searching a [[w:Constraint satisfaction problem|constraint satisfaction problem]]. The challenge is computational: even simple rules can permit a very large number of deals.[^aima]

## At the table

A small position makes it possible to check the count by hand.

!!! example "Worked example: the Rope question"
    {{figure:rope-deals|The four ways the open cards could lie. One is struck out by the overheard answer; three survive, and Mrs. White is in the envelope in two of them.}}

    Late in a three-handed game Plum's [[detective notepad|notepad]] has every card placed except four. Of the suspects, either **Mrs. White** or **Mrs. Peacock** is in the envelope; of the weapons, either the **Rope** or the **Wrench**. Whichever of each pair is not in the envelope is in [[Colonel Mustard]]'s hand, which has exactly two cards unaccounted for. Four deals are possible, and with nothing else to go on each open card is an [[w:Even money|even chance]].

    [[Mr. Green]] suggests *Mrs. Peacock, with the Rope, in the Hall*. Plum cannot [[suggestion#In the rules|disprove]] it; Mustard can, and shows Green a card Plum does not see. The Hall is Green's own, so Mustard showed Peacock or the Rope: he holds at least one of the two.

    That rules out one deal, the one in which the envelope holds Peacock and the Rope and Mustard is left holding neither. **{{code:example.deals}} deals survive.** Mrs. White is in the envelope in two of them, so her probability is {{code:example.plum.White}}; Mrs. Peacock's is {{code:example.plum.Peacock}}, the Wrench's {{code:example.plum.Wrench}} and the Rope's {{code:example.plum.Rope}}.

### The search, step by step

{{figure:plum-search|Plum's search on the Rope question. Each open card is tried in Mustard's hand and in the envelope; a branch is abandoned the moment it breaks a rule; every branch that reaches the bottom is one complete deal.}}

The example can be counted by inspection. The implementation instead [[w:Tree traversal|walks a search tree]], shown below in {{code:example.plum.nodes}} steps. It tries Mrs. White in Mustard's hand and then in the envelope, proceeding through the other open cards. A branch ends as soon as Mustard's hand is full, a category has a second envelope card, or both Peacock and the Rope are assigned to the envelope, leaving neither to explain Mustard's disproof. Three branches reach complete, valid deals.

By inspection, there are four initial deals and one to exclude. The search takes {{code:example.plum.nodes}} steps because it also visits partial assignments. Larger positions can require many more steps; the number depends on the remaining cards and how strongly the constraints restrict them.

## How it works

### What a deal is

A game of [[Clue]] begins with a *deal*: three cards go unseen into the envelope and the remaining {{code:cards.dealt}} are shuffled and dealt round the table. Everything a player wants to know is which deal happened. From one seat most of a deal is hidden, and the method's whole idea is to reason about the hidden part by listing every version of it that could be true.

What could be true is decided by the [[deduction floor]], the logic every character shares. For each card the floor keeps the set of places it could still be: a particular seat, or the envelope, or some of these. It also keeps the facts that fit no single card, the *open facts* of the form "this player holds at least one of these cards", which are what a [[suggestion#In the rules|disproof]] leaves behind when the card shown is not seen. And it knows how many cards each hand holds. A *consistent deal* is an assignment of every unplaced card to one of its possible places such that no hand is over-full, each category has exactly one card in the envelope, and every open fact is satisfied.[^module]

### Counting them

The search places the unplaced cards one at a time, trying the most constrained card first (the one with the fewest places it could be), and for each card every place it could go, in a fixed order: the seats in order, then the envelope. After each placing it checks the three rules. A hand that is now full takes nothing more; a category whose envelope card is placed takes no second; and each open fact must still be satisfiable, either already by a card placed with its holder or by some card still to be placed that could go there. If a check fails the placing is undone and the next place tried. If every card is placed, a complete deal has been found: it is counted, and for every card it puts in the envelope that card's tally goes up by one.[^module]

After a completed search, each card's probability is its envelope tally divided by the number of valid deals. The count respects every floor constraint, including joint facts: a deal that violates one is never counted.

### When the count is too long

The number of consistent deals [[w:Combinatorial explosion|grows explosively]] with the number of unplaced cards. For example, before further evidence, a player holding two cards of each kind at a three-seat table faces {{code:deals.3}} possible deals. At a six-seat table, a player holding one of each kind faces {{code:deals.6}}.[^count] No budget worth affording covers the early game, and the search is given {{code:plum.node_budget}} steps.

If it has not finished by then, the search is abandoned and the method draws random deals instead. Each draw takes the unplaced cards in a shuffled order and puts each in a randomly chosen place that the rules allow at that moment; a draw that paints itself into a corner, or that ends with an open fact unsatisfied, is thrown away. Up to {{code:plum.sample_budget}} draws are made, and the share of the kept draws with a card in the envelope stands in for the exact share.[^module]

The fallback rejects invalid draws, as in [[w:Rejection sampling|rejection sampling]], but its construction procedure does not sample all consistent deals equally. It has two sources of error. [[w:Sampling error|Sampling noise]] arises from using a finite number of accepted draws. [[w:Bias (statistics)|Construction bias]] arises because some deals are easier to build by placing cards in random order and are accepted more often. Increasing the number of draws reduces noise but does not necessarily remove that bias.[^module]

## Formally

### The posterior as a ratio of counts

Write $D$ for the set of all deals and $E$ for the logical constraints obtained from the player's observations, including their hand, passed-over players and known cards. Assume an unbiased shuffle and fixed hand sizes, so each deal has prior probability $1/|D|$, where $|D|$ is the number of deals. In the model, observing $E$ means conditioning on whether a deal satisfies these constraints. Its likelihood is 1 for a consistent deal and 0 otherwise. [[w:Bayes' theorem|Bayes' theorem]] then gives a uniform distribution over the consistent deals. For a card $c$,

$$ P(c \in \text{envelope} \mid E) = \frac{\left|\{\, d \in D : d \models E,\; c \in \text{env}(d) \,\}\right|}{\left|\{\, d \in D : d \models E \,\}\right|} $$

where $d \models E$ means that deal $d$ satisfies the constraints and $\text{env}(d)$ is its envelope. The result is exact for this constraint-based model when enumeration finishes. It is not a complete model of how other players' choices generate observations.[^aima]

### Where the assumption bends

Observed choices can carry evidence beyond their logical consequences. If Mustard holds both Peacock and the Rope, the probability that he shows the Rope depends on his [[suggestion#Showing a card|card-selection policy]]. If he chooses uniformly between them, seeing the Rope is half as likely as in a deal where it is his only matching card. The count treats both deals equally once the Rope is known to be in his hand. The size and direction of the resulting error depend on the policy. This resembles the [[w:Monty Hall problem|Monty Hall problem]], where the host's choice rule affects the posterior.

For an unseen disproof, the count retains the logical constraint that the refuter holds at least one matching card. It does not model why the suggester chose those cards, or any information conveyed by [[table talk]]. Repeated choices are the evidence used by [[Mrs. White]]'s [[Markov chain]], rather than by Plum's model.

### The accusation test

A character [[accusation|accuses]] when the product of its best suspect, weapon and room probabilities reaches its [[accusation threshold]]. This assumes [[w:Independence (probability theory)|independence]] between categories, which the consistent deals need not satisfy. In the Rope question, {{code:example.plum.White}} times {{code:example.plum.Wrench}} gives about {{code:example.plum.pair}}. Only one of the three surviving deals contains White with the Wrench, however, so the exact probability of that pair is 1/3. The shared accusation test uses the product rather than a joint probability, even when Plum's individual card probabilities are exact.[^character]

## In clude

The module is `clude_agents/exact_enum.py`. The search is a small class holding the cards still to place, each card's possible places (taken from the floor's mask and sorted into a fixed order), each seat's remaining capacity, which categories already have their envelope card, and the open facts not yet satisfied by a placed card; it places and unplaces cards along the current branch and counts completions. The sampler reuses the same class for each random draw. The agent itself is a few lines over the two: it runs the search with the step budget, and if the search did not finish it runs the sampler with the draw budget.[^module]

An independent, slower enumerator checks the search on small positions. It lists every assignment outright and verifies that the two methods agree card by card.[^tests] Fixed holder ordering also preserves reproducibility. Possible-holder sets mix seat numbers with the word *envelope*, and [[w:Python (programming language)|Python]] set iteration can change between processes. Before the ordering was fixed, this could change a sampler's choices and make the same seeded five- or six-seat game produce different results.[^ordering]

The method returns, beside its probabilities, a note of which path produced them: *resolved* (nothing left to place), *exact* (the search finished) or *sampled*, with the number of steps and of complete deals or kept draws. The [[belief benchmark]] uses the note to count how often the count fell back, and a model playing Plum's seat is shown it, which is where the persona's "faintly humiliating" sampling comes from.[^wrapper]

[[Mr. Green]]'s [[bandit ensemble]] queries all five constituent methods before choosing one, so it incurs Plum's computation cost even when it selects another arm. This also makes games involving either character relatively expensive to run in the test suite.[^budget]

## Measured

### The two boards

The [[belief benchmark]] scores each method's probabilities against the truth at four points in a game, by [[log-loss]] (lower is better), against the [[uniform baseline]]: the score of a player who believes what the deduction floor has proved and spreads the rest evenly.

{{table:bench.ring|The six methods on the ring board, the first the game was played on: log-loss at four checkpoints, {{fact:bench.ring.snapshots}} positions from 60 games. Each column is the share of the game's suggestions already made.}}

On the ring board the method was the best or joint-best of the six from three-quarters of the way through a game, and at the end its first choice in each category was right {{fact:bench.ring.Plum.top1}} of the time against the baseline's {{fact:bench.ring.uniform.top1}}. Already there the budget held only part of the time: on early positions the search fell back to sampling in nearly half of its calls, at about {{fact:plum.ring.ms}} ms a call.[^ring]

{{table:bench.grid|The same benchmark on the Classic board, {{fact:bench.grid.games}} games and {{fact:bench.grid.snapshots}} positions, 15 September 2026. Plum's row was measured at the old sample of 2,000.}}

The move to the [[Classic board]] made the early game more open. Its games have longer walks and fewer suggestions per turn, so more cards are unplaced at the same point in a game, and the search ran out of steps in {{fact:plum.fallback.calls}} of {{fact:bench.grid.snapshots}} calls. At the halfway checkpoint the exact reasoner scored {{fact:budget.grid.200k-2k.50}} against the baseline's {{fact:budget.grid.uniform.50}}, worse than the floor-only baseline, with sampling error contributing to the loss.[^grid]

### The budgets

{{figure:plum-budget|Plum's log-loss through a game on the Classic board at the old and the new sample, against the uniform baseline. Lower is better.}}

Four budgets were then run on the same {{fact:bench.grid.games}} games.

{{table:budget.grid|Log-loss at four budgets on the Classic board. "Calls that fell back" is how many of the {{fact:bench.grid.snapshots}} calls exhausted the search and sampled instead.}}

In this comparison, increasing the sample budget helped more than increasing the search budget. Five times the draws improved halfway log-loss from {{fact:budget.grid.200k-2k.50}} to {{fact:budget.grid.200k-10k.50}}, at about twice the time per call. Five times the search steps reduced fallbacks from {{fact:budget.grid.200k-2k.fallback}} to {{fact:budget.grid.1M-2k.fallback}}, but improved accuracy less and cost more. Raising both budgets improved the score by no more than 0.03 over raising the sample budget alone. The larger sample was adopted with the node budget unchanged. The measured test-suite runtime rose from about {{fact:plum.suite.before}} to {{fact:plum.suite.after}} seconds.[^budget]

The larger sample did not eliminate the deficit. At the halfway checkpoint, log-loss remained slightly worse than the baseline: {{fact:budget.grid.200k-10k.50}} versus {{fact:budget.grid.uniform.50}}. At the three-quarter checkpoint the method had caught up, and at the end it was among the lowest-loss methods. The tested budget increases therefore improved the approximation without making the early search exhaustive.[^budget]

## Limitations

The principal limitations concern computation, the evidence model and the use of its output.

- **It is slow where the game is open.** At {{fact:bench.grid.Plum.ms}} ms a call on the Classic board it is some thousands of times slower than [[Naive Bayes]], [[Dempster-Shafer theory]], the [[decision tree]] or the [[Markov chain]], each of which answers in a fraction of a millisecond.[^grid]
- **Sampling is approximate.** Early positions often exhaust the search budget. The recorded halfway scores remained worse than the uniform baseline even after the sample budget was increased.
- **Opponent choices are not modelled.** The count uses logical constraints rather than behavioural evidence about which questions players ask or which cards they prefer to show.
- **Exactness is conditional.** A completed search gives exact card probabilities under the equal-weight model. It neither corrects for card-selection policies nor supplies the joint probability used by an exact accusation test.

These are documented design trade-offs. Plum provides a useful exact calculation on small positions, while large positions require an approximation and all positions remain subject to the model's assumptions.

## See also

- [[Professor Plum]], the character who plays by this method
- [[Naive Bayes]], which reaches a different answer from the same evidence, and [[Belief]], where all six answers are compared
- [[Deduction floor]], which supplies the places each card could be and the open facts the count respects
- [[Belief benchmark]] and [[Log-loss]]
- [[w:Constraint satisfaction problem|Constraint satisfaction problem]], [[w:Backtracking|Backtracking]] and [[w:Rejection sampling|Rejection sampling]] on Wikipedia

## References

{{references}}

[^aima]: {{cite:russell-norvig|Chapter 6, "Constraint Satisfaction Problems", for the search; Chapter 12, "Quantifying Uncertainty", for probability as a ratio of consistent worlds}}
[^module]: {{cite:clude_agents/exact_enum.py|the search (`_Search.backtrack`), the sampler (`_sample_once`), the two budgets and the module's notes}}
[^count]: The envelopes a player's own hand leaves open, multiplied by the ways the cards they cannot see can fall into the other hands. For three players holding six cards each, two of each kind in hand: 4 × 4 × 7 envelopes and 924 ways to split the other twelve cards. For six players holding three each, one of each kind in hand: 5 × 5 × 8 envelopes and {{code:deals.6.hands}} ways to split the other fifteen.
[^character]: {{cite:clude_agents/character.py|`best_triple`: the product of the best probability in each category}}
[^tests]: {{cite:tests/test_agents.py|`test_exact_enum_matches_independent_brute_force`}}
[^ordering]: {{cite:docs/phase5-plan.md|8. As implemented (2026-09-12)}} The fix is `_holder_order` in the module.
[^wrapper]: {{cite:docs/llm-wrapper.md|What the model is shown, and what it is not}}
[^budget]: {{cite:docs/strategy-glossary.md|Tuned presets on the grid (Stage 1e, 2026-09-15)}}
[^ring]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}

{{navbox:clude}}
