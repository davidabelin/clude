---
title: Belief
short: What a method produces: a probability for every card, and six ways of getting one
categories: Methods
redirects: Beliefs, ClueBelief, Belief (clude), Certainty tag, Certainty, P(correct)
dyk: ... that the same overheard answer gives [[Mrs. White]] in the envelope a probability of {{code:example.white.White}} by one method and {{code:example.peacock.White}} by another, and that only one of the six is right?
dyk: ... that a seat's certainty tag reads {{code:certainty.scarlett}} at the moment [[Miss Scarlett]] accuses and {{code:certainty.plum}} when [[Professor Plum]] does?
---
{{infobox
title: Belief
Produced by | A [[Category:Methods|method]], once for each position it is shown
Shape | {{code:cards.total}} probabilities, summing to 1 in each of three categories
Masked by | The [[deduction floor]], before it is used
Consumed by | The [[personality dials]], the [[accusation]] test, the certainty tag
Scored by | [[Log-loss]], in the [[belief benchmark]]
= In the code
Type | `ClueBelief`, in `base.py`
Extras | A method's own notes beside the numbers: Plum's exact or sampled, Peacock's bounds, Green's arm
}}

A **belief**, in [[clude]], is one player's set of [[w:Probability|probabilities]] for what is in [[the envelope]]: a number for each of the {{code:cards.total}} [[Clue#The cards|cards]], summing to 1 across the {{code:cards.suspects}} suspects, to 1 across the {{code:cards.weapons}} weapons and to 1 across the {{code:cards.rooms}} rooms. Producing one is all a [[Category:Methods|method]] does. Each of the six [[Category:Characters|characters]] has a method of its own, and the whole difference between them, as reasoners, is the belief each forms from the same position. Turning a belief into a move, a [[suggestion]] or an [[accusation]] is the work of the character's [[personality dials]], which are the same five for everyone.

Whatever a method computes, the [[deduction floor]] has the last word. Before a belief is used, a card the floor has ruled out of the envelope is set to 0 and a card it has proved is set to 1, and the rest is rescaled to sum to 1 within its category. So the six characters agree on everything that is certain and differ only about what is not; and the [[uniform baseline]], the belief of a player with no method at all, is what the floor leaves when every open card gets an equal share.

A belief is also what the project measures. The [[belief benchmark]] scores every method's beliefs against the truth at four points in a game by [[log-loss]], apart from how the character then plays, and that score is where most of what is known about the six methods comes from.

## At the table

!!! example "Worked example: one question, six answers"
    {{figure:belief-six|Every method's probability that Mrs. White is in the envelope after the same overheard answer, beside the floor's own.}}

    Late in a three-handed game every card is placed except four: of the suspects, **Mrs. White** or **Mrs. Peacock** is in the envelope; of the weapons, the **Rope** or the **Wrench**; the other two are in [[Colonel Mustard]]'s hand. [[Mr. Green]] suggests *Mrs. Peacock, with the Rope, in the Hall*. The viewer is passed over; Mustard shows Green a card the viewer does not see. Since the Hall is Green's own, the floor records that Mustard holds Peacock or the Rope, and leaves the rest to the methods.

    | Method | P(Mrs. White is in the envelope) | How it got there |
    |---|---|---|
    | The floor alone ([[uniform baseline]]) | {{code:example.uniform.White.dec}} | Two suspects still possible, an even share each |
    | [[Naive Bayes]] ([[Miss Scarlett]]) | {{code:example.scarlett.1.White}} | Marked Peacock and the Rope down by {{code:scarlett.decay}} and rescaled |
    | [[Exact posterior enumeration]] ([[Professor Plum]]) | {{code:example.plum.White.dec}} (exactly {{code:example.plum.White}}) | Counted the deals: {{code:example.deals}} survive, White in the envelope in two |
    | [[Dempster-Shafer theory]] ([[Mrs. Peacock]]) | {{code:example.peacock.White}} | Belief {{code:example.peacock.White.bel}}, plausibility {{code:example.peacock.White.pl}}, split down the middle |
    | [[Decision tree]] ([[Colonel Mustard]]) | {{code:example.mustard.White}} | All four open cards reached the same leaf |
    | [[Markov chain]] ([[Mrs. White]]) | {{code:example.white.White}} | Green keeps naming Peacock and the Rope, so they rise |
    | [[Bandit ensemble]] ([[Mr. Green]]) | one of the above | Whichever arm his record favours |

    Six methods, six numbers, from one piece of evidence. Only the count is right, and it is right because it is a count: the question has an exact answer and the method computes it. Every other number is the shape of a character. Scarlett is short of the mark after one hearing and will overshoot it after two. Peacock has overshot it from the other side and does not trust her own number enough to act on it. Mustard's tree never asked the question that would have told the cards apart. White has read the asking instead of the answer and gone the other way entirely.

The example is the one every method article walks through from its own side, under the name of the Rope question, and it is deliberately small: four open cards, one fact, and arithmetic a reader can check. In a real game a method forms its belief over twenty-one cards from dozens of facts, and the same six characters emerge at scale.

## How it works

### The pipeline

Every turn, a character is shown its view of the game: its hand, who is at the table, and every suggestion so far with the cards it was not shown blanked out. The [[deduction floor]] is run over that view first, and the view goes to the method with the floor's mask attached. The method produces a raw score for every card it has an opinion about, by whatever reasoning it uses, and hands the scores to the masking step: ruled-out cards to 0, proven cards to 1, the rest rescaled within each category. What comes out is the belief, with the method's own notes beside it. A method is asked once per position, and the engine hands the same position to the movement and suggestion decisions of a turn and a fresh one to the accusation, so a character forms at most two beliefs a turn.[^base][^character]

### What a belief is used for

The five [[personality dials]] turn the belief into the four decisions the engine asks for. The suggestion names, for suspect and for weapon, a card the character does not hold, weighted by its belief, unless a [[bluff rate|bluff]] names one of its own instead. The move weighs each reachable room by its belief and its distance, at the character's [[curiosity]]. The card to show is chosen by [[secrecy]], and takes no notice of the belief at all.[^character]

The accusation is the belief's sharpest use. A character accuses when its **P(correct)**, the product of its best suspect, weapon and room probabilities, reaches its [[accusation threshold]]. Five of the six test their probabilities; [[Mrs. Peacock]] tests her Dempster-Shafer belief, the lower bound, which is why her threshold of {{code:preset.Peacock.accuse_threshold}} is the strictest at the table.[^character]

### The certainty tag

Since Phase 9h every seat at a web table carries a **certainty tag**, a colour from blue through white to red, shown to everyone including the seat's opponents: the one number that play-is-blind lets through, "the poker face". It is computed from the seat's P(correct), on a scale of bits gained: 0 for a guess spread evenly over the {{code:certainty.triples}} possible envelopes, 1 for a triple known for certain, and 0.5 at about one envelope in {{code:certainty.half.one_in}}. A person's tag is computed from the floor alone, an even spread over what it has not ruled out; a character's from its own belief, through whatever its accusation test reads. The scale is raw, not relative to any threshold: [[Miss Scarlett]] accuses at a P(correct) of {{code:preset.Scarlett.accuse_threshold}}, where the tag reads {{code:certainty.scarlett}}, and [[Professor Plum]] at {{code:preset.Plum.accuse_threshold}}, where it reads {{code:certainty.plum}}; at an even chance on one card with the other two certain it reads {{code:certainty.even}}.[^certainty][^tag]

## Formally

### Three distributions, not one

A belief is three probability distributions, one per category, and never one distribution over the {{code:cards.total}} cards. "The envelope's suspect" and "the envelope's weapon" are separate questions, and each distribution answers its own: for a category $K$ with cards $c \in K$, $\sum_{c \in K} P(c) = 1$. The categories are not independent in fact, since a deal fixes all three cards at once, but a belief carries no information about how they are joined.[^base]

### Masking

For a method's raw non-negative scores $s(c)$ and the floor's mask, write $m(c) = 1$ if the floor still allows $c$ in the envelope and $0$ if not. If some card $c^*$ in a category is proven the envelope's, $P(c^*) = 1$ and every other card in the category is 0. Otherwise

$$ P(c) = \frac{m(c)\, s(c)}{\sum_{k \in K} m(k)\, s(k)} $$

and if every permitted card has score 0, the permitted cards share the category evenly. A method may express evidence against a card only by giving it a low score; it may not give a negative one, and it may not raise a card the floor has struck.[^base]

### P(correct) and its shortcut

With $P_S$, $P_W$ and $P_R$ the three distributions, the triple a character would accuse is the best card of each, and its P(correct) is

$$ \max_{s} P_S(s) \cdot \max_{w} P_W(w) \cdot \max_{r} P_R(r) $$

as if the three questions were independent. They are not, and for a method that knows how they are joined the product is wrong. In the Rope question the count gives Mrs. White {{code:example.plum.White}} and the Wrench {{code:example.plum.Wrench}}, a product of about {{code:example.plum.pair}} for accusing the pair, but only one of the three surviving deals has that pair in the envelope: the true figure is 1/3. The shortcut is shared by all six characters and matters least to the patient ones, who wait for the product to approach 1.[^character]

### The certainty scale

For a P(correct) of $p$ over $N = {{code:certainty.triples}}$ possible envelopes,

$$ \text{certainty} = \frac{\ln(p N)}{\ln N} $$

clipped to $[0, 1]$: the share of the $\log_2 N$ bits of [[w:Information content|information]] the seat has gained, since $\ln(pN)/\ln N = 1 - \log_N(1/p)$. Linear in $p$, a seat would sit near 0 all game and jump at the end; on bits it rises steadily.[^certainty]

### Scoring a belief

The benchmark scores a belief by [[log-loss]]: for each category, $-\ln P(\text{true card})$, so that a certain and right method pays 0, an even chance pays $\ln 2 \approx 0.69$, and a card ruled out pays without limit, capped at {{fact:bench.zero_cost}}. It is a [[w:Scoring rule|proper scoring rule]]: a method cannot improve its expected score by reporting anything other than what it believes, and confidence in a wrong card costs far more than the same confidence in a right one earns.[^benchmark]

## In clude

The type is `ClueBelief` in `clude_agents/base.py`: the probabilities, and an `extra` dictionary for whatever a method wants to say beside them. [[Professor Plum]] records whether his answer was exact or sampled and how many deals or draws it rests on; [[Mrs. Peacock]] her belief and plausibility bounds; [[Mr. Green]] which arm he played; [[Mrs. White]] each opponent's repeat probability and closeness. The agent contract, shared with David's other projects, asks a method for a belief and nothing else: `select_action` returns probabilities, never a move, and the character turns them into play.[^base][^protocol]

A belief can be replayed. From a stored game's record, any seat's view at any point can be rebuilt and any method's belief recomputed, which is what the `trace` tool prints turn by turn and what the replay screen's belief trace draws; the event log is kept rich enough for exactly this.[^invariant]

What a belief shows on the web is governed by play-is-blind. A spectator, and anyone on the Watch screen, sees each seat's belief as bars by category; a player at the table sees a plain roster, since early in a game a seat's bars read as its hand. Everyone sees every seat's certainty tag. A person's own numbers are the floor's, and a [[Claude]] playing from a chat window gets the floor's notepad and no method's belief at all.[^web]

## Measured

{{table:bench.grid|The six methods on the Classic board: log-loss at four checkpoints, {{fact:bench.grid.games}} games and {{fact:bench.grid.snapshots}} positions, 15 September 2026. Plum's row is at the old sample of 2,000.}}

Read down the halfway column: [[Mrs. White]]'s chain is the best belief of the six there, {{fact:bench.grid.White.50}}; [[Colonel Mustard]]'s tree matches the floor, {{fact:bench.grid.Mustard.50}} to {{fact:bench.grid.uniform.50}}; [[Mr. Green]] tracks the arms he trusts; [[Professor Plum]], sampling, is worse than the floor until his sample was enlarged; and [[Miss Scarlett]] and [[Mrs. Peacock]] trail it by a little at every checkpoint. Read across the end column and the order changes: Mustard best at {{fact:bench.grid.Mustard.100}}, then Green, Plum and White within a few hundredths, the floor at {{fact:bench.grid.uniform.100}}, and the same two behind it. The last column is the price: four methods answer in a fraction of a millisecond, and the two that consult Plum's count take half a second.[^grid]

{{table:bench.ring|The same benchmark on the ring board, the first the game was played on, Phase 5.}}

The ring board's table tells the same story in a different order, and the two together are why the benchmark is re-run whenever the board or a method changes: a belief is only ever as good as it is on the games it is measured on.[^ring]

## Limitations

- **A belief is about the envelope only.** No method in clude keeps a belief about what is in another player's hand; the floor's placings are the whole of that knowledge.
- **The three categories are kept apart.** A belief cannot say "White with the Wrench" is likelier than its two halves suggest, and the accusation test pays for it.
- **Masking is the only guarantee.** Within what the floor allows, a method's numbers may be as badly calibrated as it likes, and two of the six are measured as worse than no method at all.
- **One number per card hides a lot.** Peacock's two bounds and Plum's exact-or-sampled note are carried in the extras because the probabilities alone cannot say how much of a belief is evidence.

## See also

- [[Deduction floor]], what every belief is masked by
- [[Naive Bayes]], [[Exact posterior enumeration]], [[Dempster-Shafer theory]], [[Decision tree]], [[Bandit ensemble]] and [[Markov chain]], the six ways of forming one
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

{{navbox:clude}}
