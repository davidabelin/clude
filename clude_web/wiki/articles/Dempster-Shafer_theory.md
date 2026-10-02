---
title: Dempster-Shafer theory
short: Mrs. Peacock's method of assigning evidence to sets of possible cards
categories: Methods
redirects: Dempster-Shafer, Dempster–Shafer theory, DS, Peacock's method, Belief and plausibility, Dempster's rule, Evidence theory
dyk: ... that [[Mrs. Peacock]] keeps two numbers for every card, and that on the Rope question they are {{code:example.peacock.White.bel}} and {{code:example.peacock.White.pl}} for the same card?
dyk: ... that [[Dempster-Shafer theory]] lets a player hold the fact "one of these three" as exactly that, without sharing it out?
---
{{infobox
title: Dempster-Shafer theory
Played by | [[Mrs. Peacock]]
In a phrase | Assigns evidential support to sets of candidates
Module | `dempster_shafer.py`
Evidence used | Every open "holds at least one of these" fact
Assumes | A fact about three cards weighs on each category in proportion to the cards it has there
Cost | About {{fact:bench.grid.Peacock.ms}} ms a call at the Classic-board halfway checkpoint
= The two numbers
Belief | Mass supporting the card alone
Plausibility | Mass on sets that contain the card
Reported | Pignistic probability: each set's mass shared equally among its cards
}}

**Dempster-Shafer theory** represents evidence by assigning weight to [[w:Set (mathematics)|sets]] of possibilities. In [[clude]], [[Mrs. Peacock]] uses it to estimate which cards are in [[the envelope]]. For each card she keeps two values: **belief**, the mass supporting that card alone, and **plausibility**, the mass that does not exclude it. The gap represents unresolved support that could belong to that card or to another. These values depend on the chosen evidence model; they are not guarantees that a card is present or absent.[^shafer][^module]

A mass function can assign weight to "White or Peacock" without dividing it between the two cards. This differs from an ordinary [[w:Probability|probability]] distribution over single cards, although a joint probability model can also represent uncertain alternatives. Evidence is combined using [[w:Dempster–Shafer theory|Dempster's rule]], which assigns products of masses to intersecting sets and renormalises after excluding conflict. The theory draws on [[w:Arthur P. Dempster|Arthur Dempster]]'s 1967 work on [[w:Upper and lower probabilities|upper and lower probabilities]] and [[w:Glenn Shafer|Glenn Shafer]]'s 1976 account of evidence.[^dempster][^shafer]

Peacock reports a single decision probability by sharing each set's mass equally among its members. For an [[accusation]], she instead uses the product of the three selected cards' belief values. This encourages caution: she made no wrong accusations in the recorded headless arenas. Her decision probabilities had slightly higher [[log-loss]] than the [[uniform baseline]] in both recorded benchmark regimes. The project attributes that deficit to its heuristic division of cross-category evidence, rather than to the theory in general.[^glossary]

## At the table

!!! example "Worked example: the Rope question"
    {{figure:peacock-interval|Peacock's two numbers for each open card after the overheard answer. The solid bar ends at belief, the pale bar at plausibility; the diamond marks the pignistic probability used for decisions.}}

    Late in a three-handed game Peacock's [[detective notepad|notepad]] has every card placed except four: of the suspects, **Mrs. White** or **Mrs. Peacock** is in the envelope; of the weapons, the **Rope** or the **Wrench**; and the two that are not in the envelope are in [[Colonel Mustard]]'s hand. Before anything is said, her belief in every one of the four is 0 and her plausibility 1. The masses express no preference among the unresolved cards.

    [[Mr. Green]] suggests *Mrs. Peacock, with the Rope, in the Hall*. Mustard shows him a card she does not see. The Hall is Green's own, so Mustard holds Peacock or the Rope, or both: one open fact, about two cards in two categories.

    The fact weighs on the suspects and on the weapons alike, and the method splits its weight between them in proportion to the cards it names in each: one of two, so a half each way. Among the suspects, then, there is weight {{code:example.ds.share}} on "Mustard holds Peacock, so the envelope's suspect is White", and the remaining {{code:example.ds.share}} stays where it was, on "either of them". That gives Mrs. White a belief of **{{code:example.peacock.White.bel}}** (the weight on her alone) and a plausibility of **{{code:example.peacock.White.pl}}** (nothing rules her out); Mrs. Peacock a belief of {{code:example.peacock.Peacock.bel}} and a plausibility of {{code:example.peacock.Peacock.pl}}. The weapons come out the same way round: the Wrench {{code:example.peacock.Wrench.bel}} to {{code:example.peacock.Wrench.pl}}, the Rope {{code:example.peacock.Rope.bel}} to {{code:example.peacock.Rope.pl}}.

    To produce a decision probability, the mass on "either" is shared equally. Mrs. White receives **{{code:example.peacock.White}}** and Mrs. Peacock {{code:example.peacock.Peacock}}. The equal-weight count gives {{code:example.plum.White}} for White, so Peacock's estimate is higher. Her accusation score for White with the Wrench, however, is only {{code:example.peacock.pair}}: the product of their belief values. It falls below {{code:preset.Peacock.accuse_threshold}}, so she would not accuse. Neither this product nor the product of her decision probabilities is an exact joint probability.

The interval distinguishes support assigned to a card alone from support shared with alternatives. The decision probability allocates that unresolved mass, while the accusation test uses the more conservative belief value.

## How it works

### Mass, belief and plausibility

For each category, suspects, weapons and rooms, the method starts with the set of cards the [[deduction floor]] still allows in the envelope, and a **mass function** over that set's subsets: an allocation of a total weight of 1 among them. At the start the whole weight sits on the full set, which is the theory's way of saying "I know nothing beyond what is certain": the *vacuous* mass function.[^shafer]

Each open fact, "this player holds at least one of these cards", becomes a heuristic mass function for each affected category. Some mass supports cards outside the named set and the rest remains on the full set. The allocation rule is described below; it is not a deduction that every named card is absent from the envelope. Dempster's rule combines these functions. For an individual card, **belief** is the mass on its singleton set and **plausibility** is the total mass on sets containing it. Belief never exceeds plausibility, and both are 0 for cards excluded by the floor.[^module]

### Dempster's rule

Dempster's rule combines two mass functions by multiplying pairs of weights and assigning each product to the intersection of their sets. Evidence for "White or Peacock" and evidence for "White or Green", for example, support White at their intersection. Products for disjoint sets form the **conflict**. Provided it is less than 1, that conflict is removed and the remaining weights are rescaled to sum to 1. The rule therefore strengthens compatible support after discarding conflict; it does not average the two sources.

Peacock's single number is the **pignistic** probability, so called from the [[w:Latin|Latin]] for a bet: each set's weight is divided equally among its members, and a card's share is the sum of what it receives. It always lies between the card's belief and its plausibility, and it is the rule the [[w:Transferable belief model|transferable belief model]] prescribes for the moment a decision has to be made.[^smets]

## Formally

### The definitions

Let $\Theta$ be the *frame of discernment*, the set of cards a category could still have in the envelope. A mass function is a map $m : 2^{\Theta} \to [0, 1]$ from the [[w:Power set|subsets]] of the frame, with $m(\varnothing) = 0$ and $\sum_{A \subseteq \Theta} m(A) = 1$; a set with positive mass is a *focal set*. Belief and plausibility are

$$ \operatorname{Bel}(A) = \sum_{B \subseteq A} m(B), \qquad \operatorname{Pl}(A) = \sum_{B \cap A \neq \varnothing} m(B) = 1 - \operatorname{Bel}(\Theta \setminus A) $$

so that $\operatorname{Bel}(A) \le \operatorname{Pl}(A)$ always, with equality for every $A$ exactly when every focal set is a single card, in which case the two coincide with an ordinary probability. The theory contains probability as the special case in which nothing is left open.[^shafer]

### Dempster's rule, and an example with conflict

Two mass functions $m_1$ and $m_2$ combine to

$$ (m_1 \oplus m_2)(A) = \frac{1}{1 - K} \sum_{B \cap C = A} m_1(B)\, m_2(C), \qquad K = \sum_{B \cap C = \varnothing} m_1(B)\, m_2(C) $$

Here $A$ must be non-empty, the empty set is assigned mass 0, and $K < 1$ is required. $K$ is the conflict. The Rope question has one piece of evidence and no conflict. Suppose a second arrives: Green asks about *Mrs. White with the Wrench* from another room whose card is known to be in Green's hand, and Mustard shows him a card again, so Mustard holds White or the Wrench. Among the suspects the first fact was $m_1(\{\text{White}\}) = 1/2$, $m_1(\{\text{White}, \text{Peacock}\}) = 1/2$; the second is $m_2(\{\text{Peacock}\}) = 1/2$, $m_2(\{\text{White}, \text{Peacock}\}) = 1/2$. Multiplying out, the product of the two singletons has an empty intersection: $K = {{code:example.ds.two.conflict}}$. The rest, scaled by $1/(1-K)$, gives mass {{code:example.ds.two.white}} on White alone, {{code:example.ds.two.peacock}} on Peacock alone and {{code:example.ds.two.both}} on the pair. White's belief is {{code:example.ds.two.white}}, her plausibility {{code:example.ds.two.white.pl}}, and her reported probability {{code:example.ds.two.white.betp}}: two facts pulling opposite ways have left Peacock exactly where she started on the single number, with more of it now evidence and less of it doubt.[^combine]

### The pignistic transform

$$ \operatorname{BetP}(c) = \sum_{A \ni c} \frac{m(A)}{|A|} $$

Here $c$ is a card and $|A|$ is the number of cards in focal set $A$. The transform produces Peacock's decision probabilities. For two remaining cards it gives the midpoint of each card's belief and plausibility, as in the Rope question; that midpoint identity does not hold for larger focal sets in general.[^smets]

### The apportioning rule

clude keeps a separate mass function for each category, so it must translate a fact involving several categories into separate pieces of evidence. It assigns each category a share proportional to how many cards from that category the fact names. "Mustard holds Peacock or the Rope" therefore assigns {{code:example.ds.share}} to each relevant category's complement set. This is a heuristic modelling choice, not a consequence of Dempster–Shafer theory. The disjunction alone does not determine how its evidence should be apportioned. The project identifies this rule as a possible target for improvement.[^module][^glossary]

## In clude

The implementation is `clude_agents/dempster_shafer.py`. It builds a vacuous mass function per category, combines evidence from open constraints and computes belief, plausibility and decision probabilities. The decision probabilities pass through the shared masking step; the bounds are returned in the belief's `extra` field. If conflict leaves a normalising factor no greater than $10^{-12}$, `_combine` returns the second mass function rather than divide by a near-zero value. This is an implementation fallback, not Dempster's normalised combination rule.[^module]

Peacock's caution is wired at that point. Each character's [[accusation threshold]] is compared against a *confidence* that is, for five of them, the belief's probabilities; for Peacock it is her Dempster-Shafer belief, the lower bound. A threshold of {{code:preset.Peacock.accuse_threshold}} on a lower bound that stays at 0 until evidence singles a card out is, as the preset's note says, "far stricter than 0.7 would be for anyone else".[^presets] The choice is a function supplied with her registry entry, not a dial, so that her profile stays five plain numbers like everyone else's.[^phase5]

The method found one bug in the floor. Until Phase 5 an open fact that a located card had already satisfied was kept and reported as open, and Peacock read the fact's other, unlocated members as live evidence against those cards. Plum's search filtered such facts for itself; she did not, and the floor now drops them.[^phase5fix]

The two bounds are also the origin of a piece of the design: the "two-tone belief bar" of the project's early visual notes, solid for belief and pale for the unresolved gap to plausibility, is exactly this pair.[^module]

## Measured

### The quality of her numbers

The [[belief benchmark]] scores the pignistic probability, since that is the number the rest of the system uses, by [[log-loss]] against the [[uniform baseline]].

{{table:bench.ring|The six methods on the ring board, Phase 5: log-loss at four checkpoints. Lower is better.}}

In the recorded benchmarks on both boards, Peacock's log-loss was slightly worse than the baseline at every checkpoint. The Classic-board values were {{fact:bench.grid.Peacock.25}}, {{fact:bench.grid.Peacock.50}}, {{fact:bench.grid.Peacock.75}} and {{fact:bench.grid.Peacock.100}}, against {{fact:bench.grid.uniform.25}}, {{fact:bench.grid.uniform.50}}, {{fact:bench.grid.uniform.75}} and {{fact:bench.grid.uniform.100}}. Her final first-choice accuracy was {{fact:bench.grid.Peacock.top1}}, the same as the baseline's.[^glossary] In the Rope example, her {{code:example.peacock.White}} for White exceeds the equal-weight count's {{code:example.plum.White}}. The difference comes from the heuristic category split and the pignistic allocation of the remaining mass.

The accusation test uses the belief values rather than the decision probabilities. The benchmark does not directly evaluate those bounds, so its results alone cannot establish how well they express uncertainty.[^ring]

### At the table

The [[arena]] measures the complete character, including her lower-bound accusation test.

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, 15 September 2026.}}

Peacock made no wrong accusations in the recorded headless arenas on either board. In the tabulated Classic-board run, she won {{fact:arena.grid.Peacock.win}}% of her games, tied with [[Professor Plum]], and first accused at mean turn {{fact:arena.grid.Peacock.first}}, the latest of the six.[^arena] In the Classic-board curiosity sweep, three settings produced the same won, wrong and never-accused percentages: {{fact:curiosity.grid.preset.peacock}}.[^tuned] These small trials do not establish that the dial has no effect in other games.

With a model in her seat the picture changes. At a four-seat table where all six characters played with [[Claude]], her wins went from {{fact:twin.grid.Peacock.win_base}}% to {{fact:twin.grid.Peacock.win_llm}}% and her first accusation from turn {{fact:twin.grid.Peacock.first_base}} to {{fact:twin.grid.Peacock.first_llm}}. The [[leash]] lets a model accuse a little before the character's own threshold, and the recorded model-piloted seats accused earlier.[^twin]

## Limitations

- **The decision probability depends on the model.** The pignistic transform is not the posterior from counting consistent deals. In the recorded benchmarks, it had higher log-loss than the uniform baseline.
- **Cross-category evidence is apportioned heuristically.** The card-count rule is not derived from a generative model of deals.
- **Caution loses races.** A belief that waits for evidence to single out a card waits longer than a probability that will act on a likelihood, and a quicker player can end the game first. Her win rate is good because her threshold is set, by measurement, where patience pays on this board.
- **Evidence can overlap.** Dempster's rule assumes appropriately independent evidence sources. Repeated disproofs can share the same cause, and this implementation does not model that dependence.[^shafer]
- **Soft updates use only open facts.** Known cards and passed-over players affect the floor's constraints. Opponents' preferences for particular questions are not modelled.

## See also

- [[Mrs. Peacock]], the character who plays by this method
- [[Exact posterior enumeration]], which counts the deals the open facts allow, and [[Naive Bayes]], which shares a fact out instead of holding it
- [[Belief]], where the six methods' answers to the Rope question are compared
- [[Deduction floor]], whose open facts are her evidence
- [[w:Dempster–Shafer theory|Dempster-Shafer theory]] and [[w:Imprecise probability|imprecise probability]] on Wikipedia

## References

{{references}}

[^shafer]: {{cite:shafer-1976|Chapters 1 to 3 define mass functions, belief and plausibility, and Dempster's rule of combination}}
[^glossary]: {{cite:docs/strategy-glossary.md|Peacock -- Dempster-Shafer belief/plausibility}}
[^module]: {{cite:clude_agents/dempster_shafer.py|`_category_mass`, `_combine`, `_pignistic` and the module's notes on the apportioning rule}}
[^smets]: {{cite:smets-kennes-1994|the pignistic transformation}}
[^dempster]: {{cite:dempster-1967}}
[^combine]: Computed by the module's own `_combine` on the two mass functions given.
[^presets]: {{cite:clude_agents/personality.py|`PRESETS`, Peacock's entry and its note}}
[^phase5]: {{cite:docs/phase5-plan.md|3. Where this differs}}
[^phase5fix]: {{cite:docs/phase5-plan.md|8. As implemented (2026-09-12)}}
[^ring]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^arena]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}
[^tuned]: {{cite:docs/strategy-glossary.md|Tuned presets on the grid (Stage 1e, 2026-09-15)}}
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}

{{navbox:clude}}
