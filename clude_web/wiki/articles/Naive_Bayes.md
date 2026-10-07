---
title: Naive Bayes
short: Miss Scarlett's method of combining clues as independent evidence
categories: Methods
redirects: Naive Bayes classifier, Scarlett's method, Naive Bayes method
dyk: ... that [[Miss Scarlett]] updates her card scores using just two factors, {{code:scarlett.boost}} and {{code:scarlett.decay}}?
dyk: ... that the "naive" in [[Naive Bayes]] is a technical term, and that statisticians once called the method "idiot's Bayes"?
---
{{infobox
title: Naive Bayes
Played by | [[Miss Scarlett]]
In a phrase | Fixed-factor score updates from suggestions
Module | `naive_bayes.py`
Evidence used | Every [[suggestion]] and whether it was disproved
Assumes | Each suggestion contributes independent evidence about a card
Cost | About {{fact:bench.grid.Scarlett.ms}} ms a call at the Classic-board halfway checkpoint
= The two factors
Nobody could disprove | each named card × {{code:scarlett.boost}}
Disproved, card unseen | each named card × {{code:scarlett.decay}}
}}

**Naive Bayes** is a family of probability models that treat pieces of evidence as [[w:Conditional independence|conditionally independent]] once the proposed answer is known. In [[clude]], [[Miss Scarlett]] uses a simplified, heuristic version to estimate which [[Clue#The cards|cards]] are in [[the envelope]]. She assigns each of the {{code:cards.total}} cards a score and multiplies it by a fixed factor after each [[suggestion]]: an undisproved suggestion raises the named cards' scores, while an unseen [[suggestion#In the rules|disproof]] lowers them. The [[deduction floor]] excludes cards already known to be elsewhere before the scores become a [[belief]].[^module]

Suggestions at a Clue table often provide overlapping evidence. One card in one hand can disprove several suggestions, but Scarlett applies an adjustment for each of them. Repetition can therefore make her increasingly [[w:Overconfidence effect|confident]] without adding information. In the recorded ring-board and [[Classic board]] benchmarks, her [[log-loss]] was slightly worse than the [[uniform baseline]] at all four checkpoints. The method is fast, but its scores are unreliable estimates of how likely an answer is.[^ring]

Textbook [[w:Naive Bayes classifier|naive Bayes classifiers]] have applications such as [[w:Naive Bayes spam filtering|spam filtering]]. Their class rankings can be useful even when their probability estimates are inaccurate. Scarlett's hand-set update factors illustrate that distinction, but the measured weaknesses of her implementation should not be taken as a verdict on every naive Bayes model.[^domingos][^handyu] The word "naive" refers to the independence assumption; Hand and Yu's review uses "idiot's Bayes" in its title.[^idiot]

## At the table

The following example shows how repeated evidence affects the scores.

!!! example "Worked example: one fact, heard three times"
    {{figure:rope-bars|Scarlett's probability that Mrs. White is in the envelope, as the same fact reaches her once, twice and three times. The dashed line is the equal-weight count, unchanged by the repeated evidence.}}

    Late in a three-handed game Scarlett's [[detective notepad|notepad]] has every card placed except four. Of the suspects, either **Mrs. White** or **Mrs. Peacock** is in the envelope; of the weapons, either the **Rope** or the **Wrench**. The two that are not in the envelope are in [[Colonel Mustard]]'s hand. Before anything else is said, each is an [[w:Even money|even bet]].

    [[Mr. Green]] suggests *Mrs. Peacock, with the Rope, in the Hall*. The Hall is known to be in Green's hand. Scarlett cannot disprove the suggestion; Mustard can, and shows Green a card she does not see. Mustard must therefore hold Peacock or the Rope. Scarlett multiplies both cards' scores by {{code:scarlett.decay}} and normalises the scores within each category. Mrs. White's probability rises from 0.5 to **{{code:example.scarlett.1.White}}**.

    Green later repeats the same suggestion from the Hall, and Mustard disproves it again. This adds no constraint to the position: Mustard was already known to hold Peacock or the Rope. An [[exact posterior enumeration|exact count]] of the deals therefore leaves Mrs. White at {{code:example.plum.White}}. Scarlett applies another adjustment, raising her to **{{code:example.scarlett.2.White}}**. The calculation holds the rest of the position fixed to isolate repetition.

    After a third such disproof, Scarlett assigns Mrs. White **{{code:example.scarlett.3.White}}**. Her accusation estimate for White with the Wrench is {{code:example.scarlett.3.pair}}, above her [[accusation threshold]] of {{code:preset.Scarlett.accuse_threshold}}. This estimate multiplies two card probabilities; it is not the exact probability of that pair. One card in Mustard's hand could explain all three disproofs.

After the first disproof, Scarlett's estimate is below the exact {{code:example.plum.White}}; after the second, it is above it. The factors are chosen by hand rather than derived for this position. Repetition then increases the error, because the method treats each occurrence as fresh evidence.

## How it works

{{figure:scarlett-update|wide|Scarlett's whole method. Every suggestion in the game so far falls into one of three kinds; two of them move the scores.}}

Scarlett starts every card at a score of 1 and reads through the whole history of suggestions, from the first turn, each time she is asked for her belief.[^module] Each suggestion names three cards, a suspect, a weapon and a room, and falls into one of three kinds.

**Nobody could disprove it.**
:   Every other player was asked and none held any of the three cards. Each named card is either in the envelope or in the suggester's hand. If the suggester holds none of them, all three are in the envelope. Scarlett multiplies each of the three scores by {{code:scarlett.boost}}.

**Somebody disproved it, and Scarlett did not see the card.**
:   One of the three cards is in that player's hand, so each is a little less likely to be in the envelope. She multiplies each of the three scores by {{code:scarlett.decay}} (that is, she divides by {{code:scarlett.decay.divisor}}).

**Somebody disproved it, and Scarlett saw the card.**
:   She was the one who suggested, or the one who showed. This is no longer a matter of probability: the card is known to be in that hand, and the [[deduction floor]] records it as a fact. She changes nothing.

When the reading is done, the scores are turned into [[w:Probability|probabilities]] one category at a time. Any card the deduction floor has ruled out of the envelope is set to zero, whatever its score; a card the floor has proved to be in the envelope is set to 1; and the scores of the cards still in question are [[w:Normalizing constant|divided by their total]], so that the suspects sum to 1, the weapons sum to 1 and the rooms sum to 1.[^base] This last step is shared by all six methods. It ensures that Scarlett never assigns envelope probability to a card she is holding.

The scores are recomputed from the suggestion history on every call. There is no incremental state, cross-game method memory or training stage.

!!! algorithm "Scarlett's belief"
        Input: the suggestions so far; the deduction floor's mask
        score(c) ← 1 for every card c
        for each suggestion, naming three cards:
            if nobody could disprove it:  score(c) ← score(c) × boost   for each named c
            else if the card shown was not seen:  score(c) ← score(c) × decay   for each named c
            (a card shown to her is a fact; the mask settles it)
        within each category: zero the cards the floor rules out, fix the proven one,
            and divide the rest by their total
        return the scores as probabilities

## Formally

### Bayes' theorem and the naive assumption

[[w:Bayes' theorem|Bayes' theorem]] describes how a probability changes when evidence arrives. Let $H$ be a hypothesis, such as "the Rope is in the envelope", and $E$ the evidence. With $P$ denoting probability and $\neg H$ the hypothesis being false, the theorem can be written in terms of [[w:Odds|odds]]:

$$ \frac{P(H \mid E)}{P(\neg H \mid E)} = \frac{P(H)}{P(\neg H)} \times \frac{P(E \mid H)}{P(E \mid \neg H)} $$

The [[w:Posterior probability|posterior]] odds equal the [[w:Prior probability|prior]] odds multiplied by the likelihood ratio, $P(E \mid H)/P(E \mid \neg H)$. That ratio compares how likely the evidence is under the two hypotheses. Evidence twice as likely under $H$ doubles its odds.

For several pieces of evidence $E_1, \dots, E_n$, the required likelihood ratio concerns the whole collection: $P(E_1, \dots, E_n \mid H)/P(E_1, \dots, E_n \mid \neg H)$. The naive assumption makes the pieces [[w:Conditional independence|conditionally independent]] under both $H$ and $\neg H$: within either case, knowing one piece tells nothing about another. The joint likelihood ratio then becomes a product of individual ratios:

$$ \frac{P(H \mid E_1, \dots, E_n)}{P(\neg H \mid E_1, \dots, E_n)} = \frac{P(H)}{P(\neg H)} \times \prod_{j=1}^{n} \frac{P(E_j \mid H)}{P(E_j \mid \neg H)} $$

This is the naive Bayes update in odds form: begin with the prior odds and multiply once for each piece of evidence, in any order.[^aima]

### Scarlett's version

Scarlett's score for a card $c$ is such a product. Let $S_j$ be the set of three cards named by the $j$-th suggestion. Then

$$ s(c) = \prod_{j \,:\, c \in S_j} f_j \qquad f_j = \begin{cases} {{code:scarlett.boost}} & \text{nobody disproved it} \\ {{code:scarlett.decay}} & \text{disproved, card unseen} \\ 1 & \text{disproved, card seen} \end{cases} $$

and her probability that $c$ is the envelope's card in its category $K$ is its share of the scores the deduction floor still permits. With $m(c) = 1$ if the floor allows $c$ in the envelope and $0$ if not,

$$ P(c) = \frac{m(c)\, s(c)}{\sum_{k \in K} m(k)\, s(k)} $$

Scarlett's heuristic differs from a textbook naive Bayes [[w:Statistical classification|classifier]] in three respects. Every card starts with the same score. The factors $f_j$ are two hand-set constants, rather than likelihood ratios derived from the rules or [[w:Machine learning|learned from data]]. Finally, the scores are normalised within each category instead of converted separately into binary card probabilities. That normalisation, together with the floor's mask, makes one card's final probability depend on the other cards' scores.[^module]

### Where independence fails

{{figure:scarlett-net|wide|Three suggestions answered by the same player. Scarlett treats them as three independent witnesses; one card in that hand could have answered all three.}}

The textbook product requires [[w:Conditional independence|conditional independence]] and valid likelihood ratios. At a card table, repeated [[suggestion|suggestions]] can share a cause: the same card in the refuter's hand. Treating that [[w:Confounding|common cause]] as fresh evidence can push a score too far towards 0 or 1. Dependence does not always produce overconfidence, but this example shows how double-counting can do so.

Scarlett also discards information in an unseen disproof. She discounts the three named cards equally, although the evidence concerns them jointly: "at least one is in that hand". An [[exact posterior enumeration]], [[PlumOG]]'s method, retains that joint constraint. She does not use the identity or hand size of the disprover; [[Mrs. Peacock]]'s [[Dempster-Shafer theory|method]] uses both when weighting an open fact.

## In clude

The [[w:Python (programming language)|Python]] implementation is `clude_agents/naive_bayes.py`.[^module] It descends from an earlier tracker that kept probabilities for cards in every hand. That tracker could not represent joint evidence and could assign probabilities stronger than the evidence supported. The simplified envelope-only version retains this weakness as part of Scarlett's design.

Like every method, Scarlett's sits between two passes of the [[deduction floor]]: the floor's facts go in with the history of the game, and its mask comes down on the scores at the end. The methods "differ in how they reason under uncertainty, never in what is logically certain".[^architecture]

Her [[personality dials]] turn the belief into play. She [[accusation|accuses]] when the product of her best suspect, weapon and room probabilities reaches {{code:preset.Scarlett.accuse_threshold}}.[^presets] The low threshold encourages early accusations, while the method's overconfidence increases their risk. The project deliberately retains both traits.[^tuned]

## Measured

### The quality of her numbers

{{figure:scarlett-bench|Scarlett's [[log-loss]] through a game on the Classic board, against the [[uniform baseline]]: a little worse than knowing only what is certain, at every checkpoint. Lower is better.}}

The [[belief benchmark]] scores each method's probabilities against the truth at four points in a game, by [[log-loss]]: lower is better. The [[uniform baseline]] is the score of a player who believes exactly what the deduction floor has proved and spreads the rest evenly.

{{table:bench.grid|The six methods on the Classic board: log-loss at four checkpoints, {{fact:bench.grid.games}} games, 15 September 2026. Plum's row was measured before his sample was enlarged.}}

Scarlett's log-loss was slightly worse than the baseline at every checkpoint in this benchmark. Her score adjustments therefore reduced accuracy on average, compared with spreading probability evenly over the floor's remaining candidates. The earlier [[ring board]] benchmark showed the same pattern. The project notes attribute it to repeated, overlapping disproofs, which are more common than undisproved suggestions until late in a game.[^ring]

Two other metrics help interpret the result. At the end checkpoint, Scarlett's first choice in each category was correct with frequency {{fact:bench.grid.Scarlett.top1}}, compared with {{fact:bench.grid.uniform.top1}} for the baseline. Her ranking was therefore slightly better despite her worse log-loss; ranking and [[w:Calibration (statistics)|calibration]] measure different properties.[^domingos] She also answered in a fraction of a millisecond in this benchmark. [[Professor Plum]] and [[Mr. Green]], whose method consults Plum's, took about half a second per call.

### At the table

The [[arena]] measures how the method and its accusation threshold perform in complete games.

{{table:scarlett.threshold|Scarlett over three arenas of 24 games on the Classic board, with only her accusation threshold changed. Won and accused wrongly are percentages of the games she played.}}

In these threshold trials, Scarlett won three times as often at 0.3 as at 0.15, her earlier [[ring board]] setting. The longer Classic-board games gave her more evidence before she reached the threshold, and 0.3 was adopted.[^threshold] In the subsequent arena she won {{fact:arena.grid.Scarlett.win}}% of her games and accused wrongly in {{fact:arena.grid.Scarlett.wrong}}%, the highest wrong-accusation rate in that run.[^arena] Each percentage rests on about twenty games, with uncertainty of roughly ten percentage points.

## Why use it at all

Naive Bayes models are useful when computation must be inexpensive. Scarlett's version needs no [[w:Training, validation, and test data sets|training]] and only simple score updates. Textbook classifiers usually estimate parameters from data, but can still require relatively little training. Research shows that a naive Bayes classifier can choose the optimal class under some conditions even when its probability estimates are inaccurate.[^domingos][^handyu]

In clude, those estimates also control when Scarlett stakes the game on an [[accusation]]. Her method deliberately favours speed and confidence over calibrated probabilities. It illustrates why a useful ranking alone does not justify confidence in the top-ranked answer.

## See also

- [[Miss Scarlett]], the character who plays by this method
- [[Exact posterior enumeration]], which gets the worked example right
- [[Deduction floor]], which keeps even a naive method from believing the impossible
- [[Belief benchmark]] and [[Log-loss]]
- [[w:Naive Bayes classifier|Naive Bayes classifier]] and [[w:Bayes' theorem|Bayes' theorem]] on Wikipedia

## References

{{references}}

[^idiot]: The phrase "idiot's Bayes" appears in the title of Hand and Yu's review. {{cite:hand-yu}}
[^domingos]: {{cite:domingos-pazzani}}
[^handyu]: {{cite:hand-yu}}
[^module]: {{cite:clude_agents/naive_bayes.py|the module's opening note and `NaiveBayesAgent.select_action`}}
[^base]: {{cite:clude_agents/base.py|`mask_and_normalize`}}
[^aima]: {{cite:russell-norvig|Conditional independence and naive Bayes classification}}
[^architecture]: {{cite:CLAUDE.md|Architecture in brief}}
[^presets]: {{cite:clude_agents/personality.py|`PRESETS`}}
[^tuned]: {{cite:docs/strategy-glossary.md|Tuned presets}}
[^ring]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^threshold]: {{cite:docs/strategy-glossary.md|Scarlett's threshold on the grid (Stage 1d)}}
[^arena]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}

{{navbox:clude}}
