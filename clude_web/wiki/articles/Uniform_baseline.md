---
title: Uniform baseline
short: Equal envelope-card probabilities among candidates left by the floor
categories: Measurement
redirects: Uniform, Baseline, Uniform (baseline)
dyk: ... that the [[uniform baseline]] gives equal card probabilities, rather than counting equally likely complete deals?
---
The **uniform baseline** gives equal envelope probabilities to the cards the [[deduction floor]] still permits within each category. A proven solution card receives 1; excluded cards receive 0; the remaining candidates divide the category's probability equally. It is the reference estimate in the [[belief benchmark]].[^code]

Uniform here means equal **per-card** values, not uniform complete deals. Hidden disproofs and hand capacities can favour some cards when complete assignments are counted. The baseline deliberately does no such method-specific counting, making it useful for testing whether a more elaborate estimate improves prediction.

## At the table

If only White and Peacock remain possible envelope suspects, the baseline gives each $1/2$. If Study is proved as the room, it gives Study 1 and every other room 0. Those distributions are normalised separately; the card values across all categories sum to 3.

In the Rope-question fixture, White and Peacock, and Rope and Wrench, remain individually open. Mustard has two spare hand slots and must hold Peacock or Rope after a hidden answer to Green, who holds Hall. The baseline still splits each pair equally. Completed [[exact posterior enumeration|enumeration]] instead gives White and Wrench $2/3$ each because three consistent deals survive.[^example]

{{figure:rope-deals|wide|Counting complete deals gives unequal marginals even where the per-card baseline still divides each pair equally.}}

The difference is not that one player saw a private card and another did not. Both algorithms are evaluating the same observer's view. They use its joint constraints differently.

## Formally

For one category, let $C$ be the set of cards still possible in the envelope. When no card is already proved, the baseline assigns

$$ p(c)=\begin{cases}1/|C|&c\in C,\\0&c\notin C.\end{cases} $$

$|C|$ means the number of permitted cards. A proved card instead receives probability 1 and all other cards in that category 0. The floor should leave at least one permitted candidate for a valid game observation.

The implementation obtains this result by calling `mask_and_normalize` with no raw method scores. Its ordinary zero-total fallback divides equally over permitted candidates. Every method uses the same final masking mechanism, but can supply non-uniform scores before it.[^code]

## Recorded comparison

At the half-way checkpoint of the 15 September 2026 Classic-board benchmark, uniform loss was {{fact:bench.grid.uniform.50}}. White scored {{fact:bench.grid.White.50}}, Mustard {{fact:bench.grid.Mustard.50}}, Scarlett {{fact:bench.grid.Scarlett.50}} and Peacock {{fact:bench.grid.Peacock.50}}. Lower is better. The run used {{fact:bench.grid.games}} floor-player games and {{fact:bench.grid.snapshots}} private observations across four checkpoints.[^grid]

The comparison can therefore reveal that additional heuristic detail worsened average estimates in a particular regime. It does not imply that a uniform player would win more games: the baseline is a prediction row, while the [[floor player]] is an actual decision policy.

## Scope and limitations

The baseline depends on a seat's hand and deductions, so it is not an uninformed guess among all {{code:envelopes}} triples. It can become certain as the floor solves a category. It also ignores distinctions encoded only in joint constraints or behavioural evidence.

Equal remaining probabilities are a reference assumption rather than a proof of equal posterior weight. This makes the baseline easy to inspect and cheap to calculate, while leaving room for a valid complete-deal model to improve it. A method's improvement must be established on appropriate evidence rather than inferred from its greater complexity.


## See also

[[Deduction floor]] · [[Belief benchmark]] · [[Floor player]] · [[Exact posterior enumeration]]

## References

{{references}}

[^code]: {{cite:clude_training/benchmark.py|`_uniform_probabilities`}} and {{cite:clude_agents/base.py|`mask_and_normalize`}}
[^example]: {{cite:clude_web/wiki/facts.py|`rope_observation` and `rope_question`}}
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}

{{navbox:clude}}
