---
title: Belief
short: A player's estimated probability that each card is in the envelope
categories: Methods
redirects: Beliefs, ClueBelief, Belief (clude), Certainty tag, Certainty, P(correct)
dyk: ... that the same overheard answer gives [[Mrs. White]] in the envelope a probability of {{code:example.white.White}} by one method and {{code:example.peacock.White}} by another, while the equal-weight count gives {{code:example.plum.White}}?
dyk: ... that at their accusation thresholds, [[Miss Scarlett]]'s certainty tag reads {{code:certainty.scarlett}} and [[Professor Plum]]'s reads {{code:certainty.plum}}?
---
{{infobox
title: Belief
Produced by | A [[Category:Methods|method]], once for each position it is shown
Shape | {{code:cards.total}} probabilities, summing to 1 in each of three categories
Masked by | The [[deduction floor]], before it is used
Used by | The [[personality dials]], the [[accusation]] test, the certainty tag
Scored by | [[Log-loss]], in the [[belief benchmark]]
= In the code
Type | `ClueBelief`, in `base.py`
Extras | A method's own notes beside the numbers: Plum's value estimate, Peacock's bounds, Green's arm
}}

A **belief** in [[clude]] is a player's set of estimated [[w:Probability|probabilities]] for the cards in [[the envelope]]. It contains one number for each of the {{code:cards.total}} [[Clue#The cards|cards]]. The numbers sum to 1 separately across the {{code:cards.suspects}} suspects, the {{code:cards.weapons}} weapons and the {{code:cards.rooms}} rooms: exactly one card of each kind is in the envelope. Each of the six [[Category:Characters|characters]] uses a different [[Category:Methods|method]] to produce these numbers. Shared [[personality dials]] then govern how the character uses them to move, [[suggestion|suggest]] and [[accusation|accuse]].[^base][^character]

The [[deduction floor]] constrains every belief. A card known to be outside the envelope receives probability 0; a card proven to be inside receives 1. The remaining scores are rescaled within their category. The characters therefore agree on the floor's deductions, while differing about unresolved cards. The [[uniform baseline]] assigns equal probability to each remaining candidate.[^base]

The [[belief benchmark]] measures these estimates independently of the decisions they lead to. It scores them against the actual envelope at four checkpoints using [[log-loss]]. A belief with low benchmark loss need not produce a high game win rate: movement, accusation timing and opponents also affect the outcome.[^benchmark]

## At the table

In this constructed example, every method evaluates the same observer's view. Its usual character name identifies the algorithm, rather than a separate seat with different private information. The probabilities are computed by the real agents.

!!! example "Worked example: one question, six answers"
    {{figure:belief-six|Every method's probability that Mrs. White is in the envelope after the same overheard answer, beside the floor's own.}}

    Late in a three-handed game every card is placed except four: of the suspects, **Mrs. White** or **Mrs. Peacock** is in the envelope; of the weapons, the **Rope** or the **Wrench**; the other two are in [[Colonel Mustard]]'s hand. [[Mr. Green]] suggests *Mrs. Peacock, with the Rope, in the Hall*. The viewer is passed over; Mustard shows Green a card the viewer does not see. Since the Hall is Green's own, the floor records that Mustard holds Peacock or the Rope, and leaves the rest to the methods.

    | Method | P(Mrs. White is in the envelope) | How it got there |
    |---|---|---|
    | The floor alone ([[uniform baseline]]) | {{code:example.uniform.White.dec}} | Two suspects still possible, an even share each |
    | [[Naive Bayes]] ([[Miss Scarlett]]) | {{code:example.scarlett.1.White}} | Marked Peacock and the Rope down by {{code:scarlett.decay}} and rescaled |
    | [[Exact posterior enumeration]] ([[PlumOG]]) | {{code:example.plum.White.dec}} (exactly {{code:example.plum.White}}) | Counted the deals: {{code:example.deals}} survive, White in the envelope in two |
    | [[Dempster-Shafer theory]] ([[Mrs. Peacock]]) | {{code:example.peacock.White}} | Belief {{code:example.peacock.White.bel}}, plausibility {{code:example.peacock.White.pl}}, split down the middle |
    | [[Decision tree]] ([[Colonel Mustard]]) | {{code:example.mustard.White}} | All four open cards reached the same leaf |
    | [[Markov chain]] ([[Mrs. White]]) | {{code:example.white.White}} | Green named Peacock and the Rope, so their scores rise |
    | [[Regularised Nash dynamics]] ([[Professor Plum]]) | {{code:example.policy.White}} | A trained network; it reads Green's naming of Peacock as evidence for her |
    | [[Bandit ensemble]] ([[Mr. Green]]) | one of the above | Whichever arm his record favours |

    The estimates differ because the methods use the evidence differently. The equal-weight count gives {{code:example.plum.White}}. Scarlett starts below it and exceeds it after repeated disproofs. Peacock assigns a higher decision probability but uses a lower evidential bound when accusing. Mustard's tree sends the unresolved cards to the same leaf. White raises the scores of cards Green has named, even though the disproof favours the alternatives. Green selects one of these methods, so his answer depends on the arm selected; there are not necessarily six distinct numbers.

The method articles use this same small position, called the Rope question, so that their outputs can be compared directly. The arithmetic involves four unresolved cards and one open fact. Full games involve more cards and a longer history of evidence.

## How it works

### The pipeline

A character receives its own view of the game: its hand, the seats and the suggestion history, with privately shown cards hidden where appropriate. The [[deduction floor]] produces a mask of possible holders and open constraints. The method uses this observation to compute scores, and the shared masking step converts them into probabilities consistent with the floor. Movement and suggestion decisions reuse the same belief; the accusation decision gets a fresh observation after the suggestion is answered. A character therefore computes at most two beliefs per turn.[^base][^character]

### What a belief is used for

The [[personality dials]] govern the decisions made from a belief. For a suggestion, the character normally favours suspect and weapon cards it does not hold, weighted by their probabilities; a [[bluff rate|bluff]] instead names a card from its own hand. For movement, it weighs reachable rooms by probability and distance, with [[curiosity]] controlling the balance. [[Secrecy]] governs which card to show and does not use the belief.[^character]

For an accusation, the character computes **P(correct)**, its estimate for the best suspect–weapon–room combination, and compares it with the [[accusation threshold]]. For five characters, this is the product of their three highest card probabilities. [[Mrs. Peacock]] instead multiplies her Dempster–Shafer lower bounds. Her threshold of {{code:preset.Peacock.accuse_threshold}} is consequently more conservative than the same value applied to her decision probabilities. Neither product generally gives an exact joint probability.[^character]

### The certainty tag

Every seat at a web table has a **certainty tag**, coloured from blue through white to red and visible to opponents as well as spectators. It expresses the seat's P(correct) on a logarithmic scale: 0 corresponds to an even guess over {{code:certainty.triples}} possible envelopes, 1 to an estimate of certainty, and 0.5 to about one chance in {{code:certainty.half.one_in}}. A person's tag uses the floor's uniform belief; a character's uses its accusation estimate. It shows the seat's estimate, not an independent measure of whether it is right.[^certainty][^tag]

The scale is shared and does not adjust for accusation thresholds. At her threshold of {{code:preset.Scarlett.accuse_threshold}}, [[Miss Scarlett]]'s tag reads {{code:certainty.scarlett}}. At his threshold of {{code:preset.Plum.accuse_threshold}}, [[Professor Plum]]'s reads {{code:certainty.plum}}. If two cards are certain and the third is an even chance, it reads {{code:certainty.even}}.[^certainty]

## Formally

### Three distributions, not one

A belief is three probability distributions, one per category, and never one distribution over the {{code:cards.total}} cards. "The envelope's suspect" and "the envelope's weapon" are separate questions, and each distribution answers its own: for a category $K$ with cards $c \in K$, $\sum_{c \in K} P(c) = 1$. The categories are not independent in fact, since conditioning on hand sizes and disproofs can link the categories, but a belief carries no information about how they are joined.[^base]

### Masking

For a method's raw non-negative scores $s(c)$ and the floor's mask, write $m(c) = 1$ if the floor still allows $c$ in the envelope and $0$ if not. If some card $c^*$ in a category is proven the envelope's, $P(c^*) = 1$ and every other card in the category is 0. Otherwise

$$ P(c) = \frac{m(c)\, s(c)}{\sum_{k \in K} m(k)\, s(k)} $$

If every permitted card has score 0, they share the probability evenly. Missing scores are treated as zero and negative scores are clamped to zero. No score can restore a card the floor has excluded.[^base]

### P(correct) and its shortcut

With $P_S$, $P_W$ and $P_R$ the three distributions, the triple a character would accuse is the best card of each, and its P(correct) is

$$ \max_{s} P_S(s) \cdot \max_{w} P_W(w) \cdot \max_{r} P_R(r) $$

The product is exact only if the relevant category events are independent. Evidence can make them dependent. In the Rope question, Mrs. White and the Wrench each have exact card probability {{code:example.plum.White}} and {{code:example.plum.Wrench}}, respectively. Their product is about {{code:example.plum.pair}}, but only one of the three surviving deals contains both, giving joint probability 1/3. Thus P(correct) is an accusation score, not a generally exact probability of success.[^character]

### The certainty scale

For a P(correct) of $p$ over $N = {{code:certainty.triples}}$ possible envelopes,

$$ \text{certainty} = \frac{\ln(p N)}{\ln N} $$

The value is clipped to $[0, 1]$. It can be interpreted as the fraction of $\log_2 N$ bits of uncertainty removed if $1/p$ is treated as an effective number of candidates. Since $p$ is an estimate for the top triple, this is a display scale rather than the [[w:Information content|information content]] or entropy of the full posterior. The logarithm makes changes at low probabilities more visible than a linear scale would.[^certainty]

### Scoring a belief

The benchmark uses [[log-loss]]: for each category, $-\ln P(\text{true card})$. A correct card assigned probability 1 costs 0; probability 0.5 costs $\ln 2 \approx 0.69$. Assigning 0 to the true card would give infinite loss, so the implementation clips probabilities and caps that contribution at {{fact:bench.zero_cost}}. Unclipped logarithmic loss is a [[w:Scoring rule|proper scoring rule]]: expected loss is minimised by reporting the true probability distribution. Clipping is a numerical safeguard.[^benchmark]

## In clude

The type is `ClueBelief` in `clude_agents/base.py`: the probabilities, and an `extra` dictionary for whatever a method wants to say beside them. [[Professor Plum]] records his network's estimate of how the game is going (PlumOG recorded whether his answer was exact or sampled); [[Mrs. Peacock]] her belief and plausibility bounds; [[Mr. Green]] which arm he played; [[Mrs. White]] each opponent's repeat probability and closeness. The agent contract, shared with David's other projects, asks a method for a belief and nothing else: `select_action` returns probabilities, never a move, and the character turns them into play.[^base][^protocol]

A stored game's event record allows any seat's view to be rebuilt at any recorded point. A method can then recompute its belief from that view. The `trace` tool prints these estimates turn by turn, and the replay screen draws them as a belief trace.[^invariant]

The web interface follows the project's "play-is-blind" rule. Spectators and Watch users see each seat's belief as bars by category. Players at the table see a plain roster, because another seat's early probabilities can reveal its hand. Everyone sees the certainty tags. A human player's own probabilities come from the floor; [[Claude]] playing from a chat window receives the floor's notepad, without a character method's belief.[^web]

## Measured

{{table:bench.grid|The six methods on the Classic board: log-loss at four checkpoints, {{fact:bench.grid.games}} games and {{fact:bench.grid.snapshots}} positions, 15 September 2026. Plum's row is at the old sample of 2,000.}}

At the halfway checkpoint in this run, [[Mrs. White]] had the lowest log-loss, {{fact:bench.grid.White.50}}. [[Colonel Mustard]] scored {{fact:bench.grid.Mustard.50}}, compared with the baseline's {{fact:bench.grid.uniform.50}}. The Plum of that row is [[PlumOG]], at the smaller sampling budget that was later increased; the network that replaced him scores {{fact:bench.policy.Plum.50}} at halfway on the same positions, the best of any method.[^policy] [[Miss Scarlett]] and [[Mrs. Peacock]] scored slightly worse than the baseline at all four checkpoints. At the end, Mustard was lowest at {{fact:bench.grid.Mustard.100}}; Green, Plum and White followed within a few hundredths, ahead of the baseline at {{fact:bench.grid.uniform.100}}. Four methods took a fraction of a millisecond per call; PlumOG and Green, who consulted him, took about half a second.[^grid]

{{table:bench.ring|The same benchmark on the ring board, the first the game was played on, Phase 5.}}

The ring-board run produced a different ranking. These results describe the recorded games and configurations, rather than a universal order of methods. The benchmark is therefore rerun when the board or a method changes.[^ring]

## Limitations

- **The probability interface describes the envelope.** It contains no probability distribution over other players' hands. The floor supplies possible holders and joint constraints, and some methods reason over them internally.
- **Joint probabilities are absent.** Separate card probabilities cannot express how likely a particular suspect–weapon–room combination is, which limits the accusation test.
- **Masking does not guarantee calibration.** Scores can respect all floor deductions while remaining inaccurate. Scarlett and Peacock had higher log-loss than the floor-only baseline in both recorded benchmark regimes.
- **One number per card hides a lot.** Peacock's two bounds and Plum's value estimate are carried in the extras because the probabilities alone cannot say how much of a belief is evidence.

## See also

[[The certainty tag]] · [[Replay]]

- [[Deduction floor]], what every belief is masked by
- [[Naive Bayes]], [[Regularised Nash dynamics]], [[Dempster-Shafer theory]], [[Decision tree]], [[Bandit ensemble]] and [[Markov chain]], the six ways of forming one, and [[exact posterior enumeration]], PlumOG's archived seventh
- [[Personality dials]] and [[Accusation threshold]], what is done with one
- [[Belief benchmark]], [[Log-loss]] and [[Uniform baseline]], how one is scored
- [[w:Probability distribution|Probability distribution]], [[w:Calibration (statistics)|calibration]] and [[w:Bayesian probability|Bayesian probability]] on Wikipedia

## References

{{references}}

[^base]: {{cite:clude_agents/base.py|`ClueBelief`, `AgentProtocol` and `mask_and_normalize`}}
[^character]: {{cite:clude_agents/character.py|`Character.select_action`, the four decisions, `best_triple` and `ds_belief_confidence`}}
[^certainty]: {{cite:clude_agents/character.py|`certainty` and `N_TRIPLES`}}
[^tag]: {{cite:CLAUDE.md|Settled decisions (David's)}} "Phase 9h's four calls", 2026-09-26: the certainty tag is shown to everyone, on the bits-gained scale.
[^benchmark]: {{cite:clude_training/benchmark.py|the module's notes on the three metrics}}
[^protocol]: {{cite:docs/architecture.md|`AgentProtocol`}}
[^invariant]: {{cite:CLAUDE.md|Architecture in brief}}
[^web]: {{cite:CLAUDE.md|Settled decisions (David's)}} "Spectators, and what the seat bars give away", 2026-09-22, and "No persona advises a chat seat", 2026-09-21.
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^ring]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^policy]: {{cite:docs/strategy-glossary.md|Belief benchmark, the network (N5)}}

{{navbox:clude}}
