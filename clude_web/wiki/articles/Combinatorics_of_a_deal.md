---
title: Combinatorics of a deal
short: Counting complete card assignments from a player’s private view
categories: Mathematics
redirects: Combinatorics, Initial deal count
---
The **combinatorics of a deal** counts how many complete [[Clue]] deals are possible from a player's private view. Each deal specifies the envelope and every hand. Counting must preserve one card of each category in the envelope and the known hand sizes. These constraints make the count much larger than the number of possible solution triples.[^count]

[[Exact posterior enumeration]] searches this space after applying evidence. If the search completes, it can convert counts into exact card marginals under its uniform consistent-deal model. A large count helps explain why early-game search needs budgets and sampling, but it is not itself a measured running time.

## A three-player example

Suppose the observer's six-card hand contains two suspects, two weapons and two rooms. There are four suspects, four weapons and seven rooms still eligible for the envelope, giving $4\times4\times7=112$ triples.

For one chosen triple, twelve unseen dealt cards remain. Mustard receives six and Green receives the complementary six. The number of ways to choose Mustard's hand is

$$ \binom{12}{6}=\frac{12!}{6!6!}=924. $$

The exclamation mark denotes a **factorial**: for example, $4!=4\times3\times2\times1$. The binomial coefficient counts subsets, so the order within a hand does not matter. Choosing Green's hand afterwards adds no further factor because its cards are already determined.

The total is $112\times924=$ {{code:deals.3}} complete deals. It assumes this specific hand composition, no further evidence and two other six-card hands. A different six-card composition changes the number of allowed envelope triples.

## The general initial count

Let $s$, $w$ and $r$ be the numbers of suspect, weapon and room cards in the observer's hand. Let $h=s+w+r$ be its size, and let $h_1,\ldots,h_k$ be the other players' hand sizes. Then

$$ N=(6-s)(6-w)(9-r)\frac{(18-h)!}{h_1!\cdots h_k!}. $$

$N$ is the complete-deal count before additional evidence. The first factors count envelope choices excluding the observer's hand. The factorial ratio distributes the remaining unseen cards among the labelled other hands. The other sizes sum to $18-h$.[^count]

The recipients are labelled: moving a particular card from Mustard's hand to Green's creates a different deal. Order inside a hand does not: dealing the same cards in another order creates no new ownership assignment.

## Six players

With six players, each hand has three cards. If the observer holds one suspect, one weapon and one room, $5\times5\times8=200$ envelopes remain. For each, fifteen cards are split among five other three-card hands in

$$ \frac{15!}{(3!)^5} $$

ways: {{code:deals.6.hands}}. Multiplying by 200 gives {{code:deals.6}} complete deals. This count again fixes the observer's category composition; it is not the count for every possible three-card hand.

More seats leave smaller private hands, so more cards remain unseen and more labelled hands must be considered. This combinatorial growth is separate from how long a particular game lasts.

## What evidence removes

A shown card fixes one assignment. A pass excludes three assignments to the passing player. A hidden disproof demands at least one named card in the answering hand. Together with hand capacities, these constraints can remove entire combinations that remain individually possible in the notepad.[^enumeration]

{{figure:rope-deals|wide|In a late constructed position, four candidate deals shrink to three because Mustard must hold Peacock or Rope.}}

The fixture fixes Study as the room and all but four cards as placed. Mustard has two spare slots; one suspect and one weapon remain in the envelope. Green holds Hall and receives Mustard's hidden answer to Peacock–Rope–Hall. The Peacock–Rope envelope would leave Mustard without a matching card, so that deal is removed. Counting the surviving complete deals yields unequal card probabilities even though their remaining notepad cells look alike.

## Search and probability

An initial count describes the search problem before evidence. It does not say how many nodes the current search will visit: propagation and ordering can prune branches before a complete deal is reached. Nodes are partial assignments, while completions are full consistent deals.

Equal weighting also requires a modelling choice. Plum's completed enumeration treats deals satisfying the formal evidence equally and does not model question-selection or showing policies. Its fallback constructs random consistent deals with possible sampling bias and noise. [[Counting deals|The enumeration article]] explains these qualifications; the arithmetic here does not establish optimal play or an exact accusation product.


## See also

[[The deal]] · [[Exact posterior enumeration]] · [[Deduction floor]] · [[Probability]]

## References

{{references}}

[^count]: {{cite:clude_web/wiki/facts.py|`_deals`}}
[^enumeration]: {{cite:clude_agents/exact_enum.py|capacity constraints, pruning and search completion}}

{{navbox:clude}}
