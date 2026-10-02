---
title: Exact posterior enumeration
short: Professor Plum's method: count every deal still possible
categories: Methods
redirects: Exact enumeration, Enumeration, Plum's method, Counting deals, Exact posterior
dyk: ... that [[exact posterior enumeration]] answered the Rope question in {{code:example.plum.nodes}} steps, and that a player at a full table on the first turn faces {{code:deals.6}} deals?
dyk: ... that the sample [[Professor Plum]] falls back on was raised from 2,000 to {{code:plum.sample_budget}} deals, and that the search budget beside it turned out barely to matter?
---
{{infobox
title: Exact posterior enumeration
Played by | [[Professor Plum]]
In a phrase | Correct but slow
Module | `exact_enum.py`
Evidence used | Everything the [[deduction floor]] knows, joint facts included
Assumes | Every deal still possible is equally likely
Cost | About {{fact:bench.grid.Plum.ms}} ms a call at mid-game, the slowest of the six
= The two budgets
Search steps | {{code:plum.node_budget}}
Random deals, after that | {{code:plum.sample_budget}}
}}

**Exact posterior enumeration** is the method by which [[Professor Plum]] forms his [[belief]] about what is in [[the envelope]]. It is the only one of [[clude]]'s six [[Category:Methods|methods]] that is, in principle, exactly right. It lists every way the hidden [[Clue#The cards|cards]] could have been dealt that agrees with everything Plum has seen, and takes a card's [[w:Probability|probability]] to be the share of those deals that put it in the envelope. There is no estimate, no weighting and no assumption beyond one: that every deal still on the list was equally likely to begin with, which is what a shuffled pack guarantees. The list is the [[w:Posterior probability|posterior]] of the method's name, and counting it is the enumeration.

The difficulty is the length of the list. Early in a game the number of deals a player cannot tell apart runs to the hundreds of thousands at a small table and the hundreds of millions at a full one, far beyond what can be counted between turns. Plum allows his search a fixed number of steps, {{code:plum.node_budget}}, and when it runs out he falls back on [[w:Monte Carlo method|sampling]]: he deals the hidden cards at random {{code:plum.sample_budget}} times and counts the deals that happen to be consistent. The sampled answer is noisy and slightly biased, and on the [[Classic board]] it is what he plays with for nearly half of the game. The method is therefore two methods, an exact count late in a game and a rough one early, and the measurements below separate them.

Outside clude, counting the worlds consistent with the evidence is the oldest definition of probability there is, going back to [[w:Pierre-Simon Laplace|Laplace]]'s ratio of favourable cases to possible cases, and the search Plum uses to count them is a standard technique of [[w:Artificial intelligence|artificial intelligence]], [[w:Backtracking|backtracking]] over a [[w:Constraint satisfaction problem|constraint satisfaction problem]].[^aima]

## At the table

The clearest way to see the method is to watch it count.

!!! example "Worked example: the Rope question"
    {{figure:rope-deals|The four ways the open cards could lie. One is struck out by the overheard answer; three survive, and Mrs. White is in the envelope in two of them.}}

    Late in a three-handed game Plum's [[detective notepad|notepad]] has every card placed except four. Of the suspects, either **Mrs. White** or **Mrs. Peacock** is in the envelope; of the weapons, either the **Rope** or the **Wrench**. Whichever of each pair is not in the envelope is in [[Colonel Mustard]]'s hand, which has exactly two cards unaccounted for. Four deals are possible, and with nothing else to go on each open card is an [[w:Even money|even chance]].

    [[Mr. Green]] suggests *Mrs. Peacock, with the Rope, in the Hall*. Plum cannot [[suggestion#The answer|disprove]] it; Mustard can, and shows Green a card Plum does not see. The Hall is Green's own, so Mustard showed Peacock or the Rope: he holds at least one of the two.

    That rules out one deal, the one in which the envelope holds Peacock and the Rope and Mustard is left holding neither. **{{code:example.deals}} deals survive.** Mrs. White is in the envelope in two of them, so her probability is {{code:example.plum.White}}; Mrs. Peacock's is {{code:example.plum.Peacock}}, the Wrench's {{code:example.plum.Wrench}} and the Rope's {{code:example.plum.Rope}}.

### The search, step by step

{{figure:plum-search|Plum's search on the Rope question. Each open card is tried in Mustard's hand and in the envelope; a branch is abandoned the moment it breaks a rule; every branch that reaches the bottom is one complete deal.}}

The count above was done by inspection. The method does it by [[w:Tree traversal|walking a tree]], and the figure shows the whole walk for the same position: {{code:example.plum.nodes}} steps. The search takes the open cards in turn, Mrs. White first, and tries each in each place it could be: Mustard's hand, then the envelope. Having placed one card it moves to the next, and so on down. Whenever a placing breaks a rule it stops and backs up: Mustard's hand is full (he has room for two open cards and no more); a category already has its envelope card (two suspects cannot both be in the envelope); or the card Mustard showed has nowhere left to be (both Peacock and the Rope have been put in the envelope). Three branches reach the bottom, and those are the three deals.

The same count, done by hand, took four deals and one crossing-out. Done by the search it takes {{code:example.plum.nodes}} steps, because the search does not know in advance which placings will work and has to try them. On a position with twelve open cards instead of four it would take millions.

## How it works

### What a deal is

A game of [[Clue]] begins with a *deal*: three cards go unseen into the envelope and the remaining {{code:cards.dealt}} are shuffled and dealt round the table. Everything a player wants to know is which deal happened. From one seat most of a deal is hidden, and the method's whole idea is to reason about the hidden part by listing every version of it that could be true.

What could be true is decided by the [[deduction floor]], the logic every character shares. For each card the floor keeps the set of places it could still be: a particular seat, or the envelope, or some of these. It also keeps the facts that fit no single card, the *open facts* of the form "this player holds at least one of these cards", which are what a [[suggestion#Disproof|disproof]] leaves behind when the card shown is not seen. And it knows how many cards each hand holds. A *consistent deal* is an assignment of every unplaced card to one of its possible places such that no hand is over-full, each category has exactly one card in the envelope, and every open fact is satisfied.[^module]

### Counting them

The search places the unplaced cards one at a time, trying the most constrained card first (the one with the fewest places it could be), and for each card every place it could go, in a fixed order: the seats in order, then the envelope. After each placing it checks the three rules. A hand that is now full takes nothing more; a category whose envelope card is placed takes no second; and each open fact must still be satisfiable, either already by a card placed with its holder or by some card still to be placed that could go there. If a check fails the placing is undone and the next place tried. If every card is placed, a complete deal has been found: it is counted, and for every card it puts in the envelope that card's tally goes up by one.[^module]

When the walk is finished, a card's probability of being in the envelope is its tally divided by the number of complete deals. That is the whole method. It uses every fact the floor has, including the joint ones that the other methods can only approximate, because a deal that violates an open fact is simply never counted.

### When the count is too long

The number of consistent deals [[w:Combinatorial explosion|grows explosively]] with the number of unplaced cards. On the first turn a player at a three-handed table, holding six cards, cannot tell {{code:deals.3}} deals apart; at a six-handed table, holding three, {{code:deals.6}}.[^count] No budget worth affording covers the early game, and the search is given {{code:plum.node_budget}} steps.

If it has not finished by then, the search is abandoned and the method draws random deals instead. Each draw takes the unplaced cards in a shuffled order and puts each in a randomly chosen place that the rules allow at that moment; a draw that paints itself into a corner, or that ends with an open fact unsatisfied, is thrown away. Up to {{code:plum.sample_budget}} draws are made, and the share of the kept draws with a card in the envelope stands in for the exact share.[^module]

This is [[w:Rejection sampling|rejection sampling]], and it has two faults the exact count does not. The first is [[w:Sampling error|noise]]: a share measured on a few thousand draws wobbles, and a wobble on a card that was truly an even chance reads as evidence for or against it. The second is [[w:Bias (statistics)|bias]]: deals that are easy to build by placing cards in a random order are drawn more often than deals that are hard to build, so the sample is not a fair sample of the consistent deals. The module's own comment calls the fallback "an honest approximation, not a fix".[^module]

## Formally

### The posterior as a ratio of counts

Write $D$ for the set of all deals and $E$ for everything the player has seen: their hand, every suggestion, who could disprove each and who could not, and the cards shown to them. Since the pack was shuffled, every deal had the same prior probability $1/|D|$, and by [[w:Bayes' theorem|Bayes' theorem]] the posterior probability of a deal $d$ is proportional to the probability of the evidence given that deal, $P(E \mid d)$. If the evidence is simply *true or false* of a deal, as a disproof or a passed-over player is, then $P(E \mid d)$ is 1 for a consistent deal and 0 for an inconsistent one, and the posterior is uniform over the consistent deals. For a card $c$,

$$ P(c \in \text{envelope} \mid E) = \frac{\left|\{\, d \in D : d \models E,\; c \in \text{env}(d) \,\}\right|}{\left|\{\, d \in D : d \models E \,\}\right|} $$

where $d \models E$ says that deal $d$ is consistent with the evidence and $\text{env}(d)$ is the deal's envelope. This is Laplace's "favourable cases over possible cases", and it is exact under the one assumption stated: that all the evidence is of the true-or-false kind.[^aima]

### Where the assumption bends

Not quite all of it is. When another player holds two of the three cards named in a suggestion, they [[suggestion#Showing a card|choose which to show]], and the choice is evidence of a weaker kind. A deal in which Mustard held both Peacock and the Rope explains "Mustard showed me the Rope" only as well as his habit of choosing the Rope allows, which may be half as well as a deal in which the Rope was his only option. The count treats the two deals alike, and is slightly off whenever a shown card had company in its hand. This is the same structure as the [[w:Monty Hall problem|Monty Hall problem]], where it matters that the host had a choice of door. Only a card shown to Plum himself is affected; a disproof he did not see is true-or-false evidence and counts correctly.

The count also reads nothing into *which* suggestions the other players choose to make, or how they talk. A player who names the Rope three times running is, to the count, three suggestions and their answers, no more. That evidence is the whole basis of [[Mrs. White]]'s [[Markov chain]].

### The accusation test

A character [[accusation|accuses]] when the product of its best suspect, weapon and room probabilities reaches its [[accusation threshold]], as if the three questions were [[w:Independence (probability theory)|independent]]. For the count they are not quite: a deal fixes all three cards at once. In the Rope question the product for accusing White with the Wrench is {{code:example.plum.White}} times {{code:example.plum.Wrench}}, about {{code:example.plum.pair}}, but only one of the three surviving deals has that pair in the envelope, so the true figure is 1/3. The shortcut is shared by all six characters and the deals themselves are available to correct it; Plum, who waits until the product is nearly 1, is the character it matters least to.[^character]

## In clude

The module is `clude_agents/exact_enum.py`. The search is a small class holding the cards still to place, each card's possible places (taken from the floor's mask and sorted into a fixed order), each seat's remaining capacity, which categories already have their envelope card, and the open facts not yet satisfied by a placed card; it places and unplaces cards along the current branch and counts completions. The sampler reuses the same class for each random draw. The agent itself is a few lines over the two: it runs the search with the step budget, and if the search did not finish it runs the sampler with the draw budget.[^module]

Two details are worth recording. The first is that the search is verified against an independent, slower enumerator in the test suite, which lists every assignment outright on positions small enough to afford it and checks that the two agree card for card.[^tests] The second is a bug that the fixed ordering of places repaired: the floor's sets of possible places mix seat numbers with the word *envelope*, and the order in which [[w:Python (programming language)|Python]] iterates such a set changes from one run of the program to the next. Before the order was fixed, a seeded game at a table of five or six, where the sampler is always in use early on, could come out differently each time it was run, which broke the determinism that every measurement in clude rests on.[^ordering]

The method returns, beside its probabilities, a note of which path produced them: *resolved* (nothing left to place), *exact* (the search finished) or *sampled*, with the number of steps and of complete deals or kept draws. The [[belief benchmark]] uses the note to count how often the count fell back, and a model playing Plum's seat is shown it, which is where the persona's "faintly humiliating" sampling comes from.[^wrapper]

The cost falls on everyone who consults him. [[Mr. Green]]'s [[bandit ensemble]] queries all five other methods every turn, so it pays Plum's price whether or not it ends up trusting him, and the seeded character games that seat either of them are most of the test suite's running time.[^budget]

## Measured

### The two boards

The [[belief benchmark]] scores each method's probabilities against the truth at four points in a game, by [[log-loss]] (lower is better), against the [[uniform baseline]]: the score of a player who believes what the deduction floor has proved and spreads the rest evenly.

{{table:bench.ring|The six methods on the ring board, the first the game was played on: log-loss at four checkpoints, {{fact:bench.ring.snapshots}} positions from 60 games. Each column is the share of the game's suggestions already made.}}

On the ring board the method was the best or joint-best of the six from three-quarters of the way through a game, and at the end its first choice in each category was right {{fact:bench.ring.Plum.top1}} of the time against the baseline's {{fact:bench.ring.uniform.top1}}. Already there the budget held only part of the time: on early positions the search fell back to sampling in nearly half of its calls, at about {{fact:plum.ring.ms}} ms a call.[^ring]

{{table:bench.grid|The same benchmark on the Classic board, {{fact:bench.grid.games}} games and {{fact:bench.grid.snapshots}} positions, 15 September 2026. Plum's row was measured at the old sample of 2,000.}}

The move to the [[Classic board]] made the early game more open. Its games have longer walks and fewer suggestions per turn, so more cards are unplaced at the same point in a game, and the search ran out of steps in {{fact:plum.fallback.calls}} of {{fact:bench.grid.snapshots}} calls. At the halfway checkpoint the exact reasoner scored {{fact:budget.grid.200k-2k.50}} against the baseline's {{fact:budget.grid.uniform.50}}, worse than ignorance, and the sampler's noise was the cause.[^grid]

### The budgets

{{figure:plum-budget|Plum's log-loss through a game on the Classic board at the old and the new sample, against the uniform baseline. Lower is better.}}

Four budgets were then run on the same {{fact:bench.grid.games}} games.

{{table:budget.grid|Log-loss at four budgets on the Classic board. "Calls that fell back" is how many of the {{fact:bench.grid.snapshots}} calls exhausted the search and sampled instead.}}

The sample is what matters and the search budget barely does. Five times the draws took the halfway score from {{fact:budget.grid.200k-2k.50}} to {{fact:budget.grid.200k-10k.50}} at about twice the time per call; five times the steps reduced the fallbacks from {{fact:budget.grid.200k-2k.fallback}} calls to {{fact:budget.grid.1M-2k.fallback}}, bought far less, and cost more; both together were no better than the larger sample alone by more than 0.03. The early game on this board is too open for any search worth affording, and the larger sample was adopted, with the node budget unchanged. The price was paid in the developer's time: the test suite went from about {{fact:plum.suite.before}} seconds to about {{fact:plum.suite.after}}.[^budget]

The repair is partial. At the halfway mark the method is still a little worse than the baseline, {{fact:budget.grid.200k-10k.50}} to {{fact:budget.grid.uniform.50}}; by three-quarters it has caught up, and at the end it is among the best. The project's notes are plain about it: "the sampled middle is where his method stops being his method", and making him exact there "is an algorithm change, not a budget".[^budget]

## Limitations

The method's limitations are the character's.

- **It is slow where the game is open.** At {{fact:bench.grid.Plum.ms}} ms a call on the Classic board it is some thousands of times slower than [[Naive Bayes]], [[Dempster-Shafer theory]], the [[decision tree]] or the [[Markov chain]], each of which answers in a fraction of a millisecond.[^grid]
- **Where it samples it is not itself.** For the first half of a Classic-board game the numbers are the sampler's, with its noise and its bias, and in that half the method is worse than knowing only what is certain.
- **It knows nothing about people.** A deal is a deal; who asked what, and how often, is not evidence to the count.
- **It is exactly right only about the envelope.** The accusation test multiplies three marginals that the deals themselves tie together, and a shown card with company in its hand is counted as if the showing had been forced.

None of these is a fault in the sense of a bug. The method is the character: correct where it can finish, humbled where it cannot, and slow everywhere.

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
