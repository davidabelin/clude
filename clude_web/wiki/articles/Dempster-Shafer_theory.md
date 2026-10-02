---
title: Dempster-Shafer theory
short: Mrs. Peacock's method: belief and plausibility, with the doubt left open
categories: Methods
redirects: Dempster-Shafer, Dempster–Shafer theory, DS, Peacock's method, Belief and plausibility, Dempster's rule, Evidence theory
dyk: ... that [[Mrs. Peacock]] keeps two numbers for every card, and that on the Rope question they are {{code:example.peacock.White.bel}} and {{code:example.peacock.White.pl}} for the same card?
dyk: ... that [[Dempster-Shafer theory]] lets a player hold the fact "one of these three" as exactly that, without sharing it out?
---
{{infobox
title: Dempster-Shafer theory
Played by | [[Mrs. Peacock]]
In a phrase | Cautious; will not commit until the alternatives collapse
Module | `dempster_shafer.py`
Evidence used | Every open "holds at least one of these" fact
Assumes | A fact about three cards weighs on each category in proportion to the cards it has there
Cost | About {{fact:bench.grid.Peacock.ms}} ms a call
= The two numbers
Belief | What the evidence has established
Plausibility | What the evidence has failed to rule out
Reported | The middle of the two, by the pignistic rule
}}

**Dempster-Shafer theory** is the method by which [[Mrs. Peacock]] forms her [[belief]] about what is in [[the envelope]]. Where every other [[Category:Methods|method]] gives a card one number, its [[w:Probability|probability]], the theory gives it two. The first is its **belief**, the weight of evidence that points to that card and no other. The second is its **plausibility**, the weight of evidence that does not rule it out. The gap between them is what the evidence has not settled, and the method leaves it open rather than guessing how to fill it. A card can be entirely plausible and have no belief behind it at all, which at a [[Clue]] table is the usual condition of a card nobody has yet named.

The theory's distinctive move is to put weight on [[w:Set (mathematics)|sets]] of possibilities rather than on single ones. A [[suggestion]] that somebody disproved with a card the viewer did not see says "one of these three cards is in that hand". A probability has to share that fact out among the three somehow; a mass function, the theory's basic object, can hold it as a single weight on the set of three and be done. Pieces of evidence are then combined by [[w:Dempster–Shafer theory|Dempster's rule]], which multiplies the weights and discards the part of the product in which they contradict one another. The theory takes its name from [[w:Arthur P. Dempster|Arthur Dempster]], who introduced [[w:Upper and lower probabilities|upper and lower probabilities]] in 1967, and [[w:Glenn Shafer|Glenn Shafer]], whose book of 1976 made them a theory of evidence.[^dempster][^shafer]

In [[clude]] the character this produces is the careful one. Peacock reports a single probability when one is needed, by splitting each set's weight evenly among its members, but she [[accusation|accuses]] on the belief, the lower number, which stays at nothing for a card until evidence singles it out. She therefore accuses late and, in every arena tabulated below, never wrongly. Her single number is measured as slightly worse than knowing only what is certain, and the project's notes trace that to one modelling choice in how a fact about three cards is divided among the three categories.[^glossary]

## At the table

!!! example "Worked example: the Rope question"
    {{figure:peacock-interval|Peacock's two numbers for each open card after the overheard answer. The solid part is belief, the pale part plausibility, the diamond the one number she reports.}}

    Late in a three-handed game Peacock's [[detective notepad|notepad]] has every card placed except four: of the suspects, **Mrs. White** or **Mrs. Peacock** is in the envelope; of the weapons, the **Rope** or the **Wrench**; and the two that are not in the envelope are in [[Colonel Mustard]]'s hand. Before anything is said, her belief in every one of the four is 0 and her plausibility 1. She knows nothing, and says so.

    [[Mr. Green]] suggests *Mrs. Peacock, with the Rope, in the Hall*. Mustard shows him a card she does not see. The Hall is Green's own, so Mustard holds Peacock or the Rope, or both: one open fact, about two cards in two categories.

    The fact weighs on the suspects and on the weapons alike, and the method splits its weight between them in proportion to the cards it names in each: one of two, so a half each way. Among the suspects, then, there is weight {{code:example.ds.share}} on "Mustard holds Peacock, so the envelope's suspect is White", and the remaining {{code:example.ds.share}} stays where it was, on "either of them". That gives Mrs. White a belief of **{{code:example.peacock.White.bel}}** (the weight on her alone) and a plausibility of **{{code:example.peacock.White.pl}}** (nothing rules her out); Mrs. Peacock a belief of {{code:example.peacock.Peacock.bel}} and a plausibility of {{code:example.peacock.Peacock.pl}}. The weapons come out the same way round: the Wrench {{code:example.peacock.Wrench.bel}} to {{code:example.peacock.Wrench.pl}}, the Rope {{code:example.peacock.Rope.bel}} to {{code:example.peacock.Rope.pl}}.

    When a single number is wanted the weight on "either" is split evenly, and Mrs. White is reported at **{{code:example.peacock.White}}**, Mrs. Peacock at {{code:example.peacock.Peacock}}. The exact answer, counted by [[Professor Plum]], is {{code:example.plum.White}}: Peacock has overshot it a little, as [[Miss Scarlett]] does from the other side on the same evidence. But her *belief* in the pair she would have to accuse, White with the Wrench, is only {{code:example.peacock.pair}}, far below her threshold of {{code:preset.Peacock.accuse_threshold}}. She will not say it.

The example shows the two things the method is for. The interval says how much of her number is evidence and how much is the even split of a doubt; and the accusation test, read against the belief, is why a card that is merely probable never tempts her.

## How it works

### Mass, belief and plausibility

For each category, suspects, weapons and rooms, the method starts with the set of cards the [[deduction floor]] still allows in the envelope, and a **mass function** over that set's subsets: an allocation of a total weight of 1 among them. At the start the whole weight sits on the full set, which is the theory's way of saying "I know nothing beyond what is certain": the *vacuous* mass function.[^shafer]

Each open fact from the floor, "this player holds at least one of these cards", is one piece of evidence, and it becomes a mass function of its own: some weight on the cards it *does not* name (if the holder has one of the named cards, the envelope's card is one of the others) and the rest on the full set. The pieces are combined, one after another, by Dempster's rule, and from the result two numbers are read off for every card. Its **belief** is the weight on the set containing that card alone. Its **plausibility** is the total weight on every set that contains it. Belief never exceeds plausibility, and a card the floor has ruled out has both at 0.[^module]

### Dempster's rule

Combining two mass functions means multiplying every weight in the first by every weight in the second and giving each product to the intersection of the two sets it came from: evidence for "White or Peacock" and evidence for "White or Green" together support "White". Where two sets have nothing in common the product has nowhere to go; it is **conflict**, and it is thrown away, with everything that remains scaled up so the weights sum to 1 again. The scaling is what makes the rule interesting: contradictory evidence does not cancel out, it is removed, and what is left of each side is believed more strongly.

Peacock's single number is the **pignistic** probability, so called from the [[w:Latin|Latin]] for a bet: each set's weight is divided equally among its members, and a card's share is the sum of what it receives. It always lies between the card's belief and its plausibility, and it is the rule the [[w:Transferable belief model|transferable belief model]] prescribes for the moment a decision has to be made.[^smets]

## Formally

### The definitions

Let $\Theta$ be the *frame of discernment*, the set of cards a category could still have in the envelope. A mass function is a map $m : 2^{\Theta} \to [0, 1]$ from the [[w:Power set|subsets]] of the frame, with $m(\varnothing) = 0$ and $\sum_{A \subseteq \Theta} m(A) = 1$; a set with positive mass is a *focal set*. Belief and plausibility are

$$ \operatorname{Bel}(A) = \sum_{B \subseteq A} m(B), \qquad \operatorname{Pl}(A) = \sum_{B \cap A \neq \varnothing} m(B) = 1 - \operatorname{Bel}(\Theta \setminus A) $$

so that $\operatorname{Bel}(A) \le \operatorname{Pl}(A)$ always, with equality for every $A$ exactly when every focal set is a single card, in which case the two coincide with an ordinary probability. The theory contains probability as the special case in which nothing is left open.[^shafer]

### Dempster's rule, and an example with conflict

Two mass functions $m_1$ and $m_2$ combine to

$$ (m_1 \oplus m_2)(A) = \frac{1}{1 - K} \sum_{B \cap C = A} m_1(B)\, m_2(C), \qquad K = \sum_{B \cap C = \varnothing} m_1(B)\, m_2(C) $$

where $K$ is the conflict. The Rope question has one piece of evidence and no conflict. Suppose a second arrives: Green asks about *Mrs. White with the Wrench* from another room, and Mustard shows him a card again, so Mustard holds White or the Wrench. Among the suspects the first fact was $m_1(\{\text{White}\}) = 1/2$, $m_1(\{\text{White}, \text{Peacock}\}) = 1/2$; the second is $m_2(\{\text{Peacock}\}) = 1/2$, $m_2(\{\text{White}, \text{Peacock}\}) = 1/2$. Multiplying out, the product of the two singletons has an empty intersection: $K = {{code:example.ds.two.conflict}}$. The rest, scaled by $1/(1-K)$, gives mass {{code:example.ds.two.white}} on White alone, {{code:example.ds.two.peacock}} on Peacock alone and {{code:example.ds.two.both}} on the pair. White's belief is {{code:example.ds.two.white}}, her plausibility {{code:example.ds.two.white.pl}}, and her reported probability {{code:example.ds.two.white.betp}}: two facts pulling opposite ways have left Peacock exactly where she started on the single number, with more of it now evidence and less of it doubt.[^combine]

### The pignistic transform

$$ \operatorname{BetP}(c) = \sum_{A \ni c} \frac{m(A)}{|A|} $$

This is the probability Peacock reports, and the one every other part of clude treats as hers.[^smets]

### The apportioning rule

One choice in clude's version is not in the theory. An open fact names up to three cards in up to three categories, and the method keeps a separate mass function per category. The fact's weight is divided among the categories in proportion to how many of its cards fall in each: a fact about Peacock and the Rope, one suspect and one weapon, gives weight {{code:example.ds.share}} to each category's "the envelope's card is one of the others". The true division would need to know which card the holder actually has, which is the very thing hidden. The module's note calls the rule "a stated modeling choice, not a theorem", and the project's notes name it as the first thing to revisit if Peacock is ever meant to be a stronger reasoner.[^module][^glossary]

## In clude

The module is `clude_agents/dempster_shafer.py`, under a hundred and thirty lines. For each category it builds the vacuous mass function over the floor's permitted cards, folds in one mass function per open fact by Dempster's rule, and reads off belief, plausibility and the pignistic probability. The probabilities go through the same masking and renormalising step every method ends with; the two bounds travel beside them in the belief's `extra` field, where the [[accusation]] test and the Watch screen read them.[^module]

Peacock's caution is wired at that point. Each character's [[accusation threshold]] is compared against a *confidence* that is, for five of them, the belief's probabilities; for Peacock it is her Dempster-Shafer belief, the lower bound. A threshold of {{code:preset.Peacock.accuse_threshold}} on a lower bound that stays at 0 until evidence singles a card out is, as the preset's note says, "far stricter than 0.7 would be for anyone else".[^presets] The choice is a function supplied with her registry entry, not a dial, so that her profile stays five plain numbers like everyone else's.[^phase5]

The method found one bug in the floor. Until Phase 5 an open fact that a located card had already satisfied was kept and reported as open, and Peacock read the fact's other, unlocated members as live evidence against those cards. Plum's search filtered such facts for itself; she did not, and the floor now drops them.[^phase5fix]

The two bounds are also the origin of a piece of the design: the "two-tone belief bar" of the project's early visual notes, solid where a card is forced and pale where it is still only plausible, is exactly this pair.[^module]

## Measured

### The quality of her numbers

The [[belief benchmark]] scores the pignistic probability, since that is the number the rest of the system uses, by [[log-loss]] against the [[uniform baseline]].

{{table:bench.ring|The six methods on the ring board, Phase 5: log-loss at four checkpoints. Lower is better.}}

On both boards the method trails the baseline by a little at every checkpoint: on the Classic board {{fact:bench.grid.Peacock.25}}, {{fact:bench.grid.Peacock.50}}, {{fact:bench.grid.Peacock.75}} and {{fact:bench.grid.Peacock.100}} against {{fact:bench.grid.uniform.25}}, {{fact:bench.grid.uniform.50}}, {{fact:bench.grid.uniform.75}} and {{fact:bench.grid.uniform.100}}. Her first choice at the end is right {{fact:bench.grid.Peacock.top1}} of the time, the baseline's own figure. The project's notes attribute the shortfall to the apportioning rule and record that nothing depends on it yet.[^glossary] The Rope question shows the shape of the error in small: the overshoot to {{code:example.peacock.White}} where the exact answer is {{code:example.plum.White}} is the even split of the open weight, which treats "one of the others" as stronger evidence than it is.

The caution is unaffected by any of this, because it comes from the belief bound, which the benchmark does not score.[^ring]

### At the table

In the [[arena]] the lower bound decides everything.

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, 15 September 2026.}}

Peacock has not accused wrongly in any arena on either board, and on the Classic board she won {{fact:arena.grid.Peacock.win}}% of her games, level with [[Professor Plum]] at the top of the table, with her first accusation coming at turn {{fact:arena.grid.Peacock.first}}, the latest of the six.[^arena] On the ring board her [[curiosity]] was tried at three settings with every other dial fixed and her three results were identical, {{fact:curiosity.grid.preset.peacock}} for won, wrong and never accused, which the notes record as "its own answer".[^tuned]

With a model in her seat the picture changes. At a four-seat table where all six characters played with [[Claude]], her wins went from {{fact:twin.grid.Peacock.win_base}}% to {{fact:twin.grid.Peacock.win_llm}}% and her first accusation from turn {{fact:twin.grid.Peacock.first_base}} to {{fact:twin.grid.Peacock.first_llm}}. The [[leash]] lets a model accuse a little before the character's own threshold, and a model is less patient than a lower bound.[^twin]

## Limitations

- **The single number is approximate.** The pignistic split is a convention, not a posterior, and in clude it is measured as a little worse than ignorance throughout a game.
- **The apportioning is a guess.** Dividing a fact among categories by a head count is reasonable and unjustified; it is the method's one invented step.
- **Caution loses races.** A belief that waits for evidence to single out a card waits longer than a probability that will act on a likelihood, and a quicker player can end the game first. Her win rate is good because her threshold is set, by measurement, where patience pays on this board.
- **It uses only one kind of evidence.** The open facts. Who was passed over, who asked what, and how often, enter only through what the floor has already made of them.

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
