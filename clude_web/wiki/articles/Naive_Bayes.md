---
title: Naive Bayes
short: Miss Scarlett's method: every clue counted as if it stood alone
categories: Methods
redirects: Naive Bayes classifier, Scarlett's method, Naive Bayes method
dyk: ... that [[Miss Scarlett]]'s whole method is two multiplications, by {{code:scarlett.boost}} and by {{code:scarlett.decay}}, and that it runs a few thousand times faster than [[Professor Plum]]'s?
dyk: ... that the "naive" in [[Naive Bayes]] is a technical term, and that statisticians once called the method "idiot's Bayes"?
---
{{infobox
title: Naive Bayes
Played by | [[Miss Scarlett]]
In a phrase | Fast, decisive, overconfident
Module | `naive_bayes.py`
Evidence used | Every [[suggestion]] and whether it was disproved
Assumes | Every piece of evidence is independent of every other
Cost | About {{fact:bench.grid.Scarlett.ms}} ms a call, among the fastest of the six
= The two factors
Nobody could disprove | each named card × {{code:scarlett.boost}}
Disproved, card unseen | each named card × {{code:scarlett.decay}}
}}

**Naive Bayes** is the method by which [[Miss Scarlett]] forms her [[belief]] about what is in [[the envelope]]. She keeps a score for each of the {{code:cards.total}} [[Clue#The cards|cards]] and adjusts it once for every [[suggestion]] she hears: up, if nobody at the table could [[suggestion#Disproof|disprove]] the suggestion, and down, if somebody did. Each adjustment is a [[w:Multiplication|multiplication]], and every one is made as though no other had been: as though each suggestion were a fresh, separate witness. That assumption is what "naive" means. It is a technical term and not an insult, though it has been used as one.[^idiot]

The assumption is false at a Clue table, where the same card in the same hand can answer three different suggestions. Scarlett counts that one fact three times. The result is the character: she is quick, since her whole method is a few multiplications; she is decisive, since her numbers move a long way on little evidence; and she is [[w:Overconfidence effect|overconfident]] in exactly the places where her clues overlap. Measured against the truth, her [[w:Probability|probabilities]] are slightly worse than those of a player who knows only what is logically certain (the [[uniform baseline]]), at every stage of a game and on both [[Classic board|boards]] the game has been played on.

Outside clude, [[w:Naive Bayes classifier|naive Bayes]] is one of the oldest and most widely used methods in [[w:Machine learning|machine learning]], best known for [[w:Naive Bayes spam filtering|sorting spam from real mail]]. It is known there for the same pair of traits it has here: it is often surprisingly good at picking the right answer, and much less good at saying how sure it should be.[^domingos]

## At the table

The clearest way to see the method is to watch it hear the same thing more than once.

!!! example "Worked example: one fact, heard three times"
    {{figure:rope-bars|Scarlett's probability that Mrs. White is in the envelope, as the same fact reaches her once, twice and three times. The dashed line is the exact answer, which the second and third hearings do not change.}}

    Late in a three-handed game Scarlett's [[detective notepad|notepad]] has every card placed except four. Of the suspects, either **Mrs. White** or **Mrs. Peacock** is in the envelope; of the weapons, either the **Rope** or the **Wrench**. The two that are not in the envelope are in [[Colonel Mustard]]'s hand. Before anything else is said, each is an [[w:Even money|even bet]].

    [[Mr. Green]] suggests *Mrs. Peacock, with the Rope, in the Hall*. Scarlett cannot disprove it; Mustard can, and shows Green a card she does not see. Somebody holds one of those cards, so Scarlett marks Peacock and the Rope down, each to {{code:scarlett.decay}} of what it was, and shares out what is left among the cards still possible. Mrs. White rises from 0.5 to **{{code:example.scarlett.1.White}}**.

    Two turns later Green tries Peacock and the Rope again from another room, and Mustard shows him a card again. To [[Professor Plum]], who counts the [[exact posterior enumeration|deals still possible]], this is no news at all: he already knew Mustard held Peacock or the Rope, and his figure for Mrs. White stays where it was, at {{code:example.plum.White}}. Scarlett marks both cards down a second time. Mrs. White is now at **{{code:example.scarlett.2.White}}**.

    A third time, and she is at **{{code:example.scarlett.3.White}}**, ten points past the right answer and still climbing. Her figure for the pair, White with the Wrench, has reached {{code:example.scarlett.3.pair}}, twice her [[accusation threshold]] of {{code:preset.Scarlett.accuse_threshold}}. One card in Mustard's hand, perhaps the Rope alone, explains everything she has heard.

Two things are worth noticing. After the *first* hearing Scarlett was too cautious, not too bold: {{code:example.scarlett.1.White}} where the exact answer is {{code:example.plum.White}}. Her factors are round numbers chosen by hand, and nothing makes them right for any one situation. And the overshoot came from repetition alone. Each step was reasonable by itself; the error is in treating the steps as separate.

## How it works

{{figure:scarlett-update|wide|Scarlett's whole method. Every suggestion in the game so far falls into one of three kinds; two of them move the scores.}}

Scarlett starts every card at a score of 1 and reads through the whole history of suggestions, from the first turn, each time she is asked for her belief.[^module] Each suggestion names three cards, a suspect, a weapon and a room, and falls into one of three kinds.

**Nobody could disprove it.**
:   Every other player was asked and none held any of the three cards. Unless the player who suggested was [[bluffing]] with cards from their own hand, some of the three are in the envelope. Scarlett multiplies each of the three scores by {{code:scarlett.boost}}.

**Somebody disproved it, and Scarlett did not see the card.**
:   One of the three cards is in that player's hand, so each is a little less likely to be in the envelope. She multiplies each of the three scores by {{code:scarlett.decay}} (that is, she divides by {{code:scarlett.decay.divisor}}).

**Somebody disproved it, and Scarlett saw the card.**
:   She was the one who suggested, or the one who showed. This is no longer a matter of probability: the card is known to be in that hand, and the [[deduction floor]] records it as a fact. She changes nothing.

When the reading is done, the scores are turned into [[w:Probability|probabilities]] one category at a time. Any card the deduction floor has ruled out of the envelope is set to zero, whatever its score; a card the floor has proved to be in the envelope is set to 1; and the scores of the cards still in question are [[w:Normalizing constant|divided by their total]], so that the suspects sum to 1, the weapons sum to 1 and the rooms sum to 1.[^base] This last step is shared by all six methods. It is why Scarlett, however sloppy her arithmetic, can never suspect a card she is holding.

Nothing is carried from one call to the next and nothing from one game to the next. The method has no memory to go stale and nothing to train.

## Formally

### Bayes' theorem and the naive assumption

[[w:Bayes' theorem|Bayes' theorem]], named for the eighteenth-century clergyman [[w:Thomas Bayes|Thomas Bayes]], says how a probability should change when evidence arrives. Writing $H$ for a hypothesis ("the Rope is in the envelope") and $E$ for a piece of evidence, it is most easily used in terms of [[w:Odds|odds]]:

$$ \frac{P(H \mid E)}{P(\neg H \mid E)} = \frac{P(H)}{P(\neg H)} \times \frac{P(E \mid H)}{P(E \mid \neg H)} $$

The odds after the evidence (the [[w:Posterior probability|posterior]]) are the odds before it (the [[w:Prior probability|prior]]), multiplied by a single number, the [[w:Bayes factor|likelihood ratio]]: how much more often this evidence turns up when $H$ is true than when it is false. Evidence twice as common under $H$ doubles the odds.

With several pieces of evidence $E_1, \dots, E_n$ the theorem still holds, but the ratio needed is that of the whole collection at once, $P(E_1, \dots, E_n \mid H)$, which is rarely known. The naive assumption is that the pieces are [[w:Conditional independence|conditionally independent]]: that once it is settled whether $H$ is true, knowing one piece tells nothing about another. Then the joint ratio falls apart into a product, one factor for each piece:

$$ \frac{P(H \mid E_1, \dots, E_n)}{P(\neg H \mid E_1, \dots, E_n)} = \frac{P(H)}{P(\neg H)} \times \prod_{j=1}^{n} \frac{P(E_j \mid H)}{P(E_j \mid \neg H)} $$

This is the whole of naive Bayes: begin with the prior odds and multiply once for each piece of evidence, in any order.[^aima]

### Scarlett's version

Scarlett's score for a card $c$ is such a product. Let $S_j$ be the set of three cards named by the $j$-th suggestion. Then

$$ s(c) = \prod_{j \,:\, c \in S_j} f_j \qquad f_j = \begin{cases} 2 & \text{nobody disproved it} \\ 2/3 & \text{disproved, card unseen} \\ 1 & \text{disproved, card seen} \end{cases} $$

and her probability that $c$ is the envelope's card in its category $K$ is its share of the scores the deduction floor still permits. With $m(c) = 1$ if the floor allows $c$ in the envelope and $0$ if not,

$$ P(c) = \frac{m(c)\, s(c)}{\sum_{k \in K} m(k)\, s(k)} $$

Three things separate this from a textbook naive Bayes [[w:Statistical classification|classifier]]. The prior is flat: every card starts equal. The factors $f_j$ are not [[w:Machine learning|learned from data]] or derived from the rules; they are two constants set by hand, and they play the part of likelihood ratios without being calculated as such.[^module] And the result is normalised across a category instead of being computed card by card, which is the only place where one card's evidence touches another's.

### Where independence fails

{{figure:scarlett-net|wide|Three suggestions answered by the same player. Scarlett treats them as three independent witnesses; one card in that hand could have answered all three.}}

The product is correct only if the suggestions are [[w:Conditional independence|independent given the truth]], and at a card table they are not. A [[suggestion]] is [[suggestion#The answer|disproved]] *because of* a particular card in a particular hand, and that card is still there the next time one of its three is named. Evidence with a [[w:Confounding|common cause]] is the standard way for the naive assumption to fail, and its effect is always the same: the shared cause is counted once for every piece of evidence it produces, and the probability is pushed too far towards 0 or 1.

Scarlett's version has two further blind spots, both of which the other methods address. She discounts all three cards of a disproved suggestion equally, although the fact is about the three jointly ("at least one of these is in that hand"); [[Professor Plum]]'s [[exact posterior enumeration]] keeps the joint fact. And she takes no account of who did the disproving or how many cards they hold, where [[Mrs. Peacock]]'s [[Dempster-Shafer theory|Dempster-Shafer]] method weighs each such fact against the size of the hand it concerns.

## In clude

The [[w:Python (programming language)|Python]] module is some sixty lines, of which the method is a dozen.[^module] It descends from an earlier, more ambitious tracker that kept a probability for every card in every hand and adjusted the rows of that table as evidence arrived. That design could not express a fact about two cards at once, and could "drift past what the evidence actually supports"; it was wrong for a reasoner meant to be correct, and was kept, pared down to the envelope alone, for the one character whose flaw it describes.[^module]

Like every method, Scarlett's sits between two passes of the [[deduction floor]]: the floor's facts go in with the history of the game, and its mask comes down on the scores at the end. The methods "differ in how they reason under uncertainty, never in what is logically certain".[^architecture]

Her numbers reach the table through her [[personality dials]]. The one that matters is the [[accusation threshold]]. She [[accusation|accuses]] when the product of her best suspect, weapon and room probabilities reaches {{code:preset.Scarlett.accuse_threshold}}, where the other five wait for 0.7 to 0.9.[^presets] The low threshold makes her early; the method makes her wrong. As the project's notes put it, "the dial supplies 'early', the belief supplies 'wrong'", and repairing her arithmetic "would make her a different character".[^tuned]

## Measured

### The quality of her numbers

{{figure:scarlett-bench|Scarlett's [[log-loss]] through a game on the Classic board, against the [[uniform baseline]]: a little worse than knowing only what is certain, at every checkpoint. Lower is better.}}

The [[belief benchmark]] scores each method's probabilities against the truth at four points in a game, by [[log-loss]]: lower is better. The [[uniform baseline]] is the score of a player who believes exactly what the deduction floor has proved and spreads the rest evenly.

{{table:bench.grid|The six methods on the Classic board: log-loss at four checkpoints, {{fact:bench.grid.games}} games, 15 September 2026. Plum's row was measured before his sample was enlarged.}}

Scarlett is worse than the baseline at every checkpoint, by a little: every adjustment she makes to the floor's even spread costs her, on average, more than it gains. The same was true on the earlier [[ring board]].[^ring] The reason given in the project's notes is the mix of evidence in a real game. Most suggestions are disproved; one that nobody can disprove is rare until near the end. So for most of a game she is applying her weaker, cruder factor over and over to overlapping sets of cards.[^ring]

Two details qualify the picture. At the end of a game her *first choice* in each category is the right card with frequency {{fact:bench.grid.Scarlett.top1}}, against the baseline's {{fact:bench.grid.uniform.top1}}: her ranking of the cards is a little better than ignorance even while her probabilities are worse. That is the usual finding about naive Bayes, that it classifies well and is poorly [[w:Calibration (statistics)|calibrated]].[^domingos] And she is fast. Like three of the other methods she answers in a fraction of a millisecond, where [[Professor Plum]]'s count, and [[Mr. Green]]'s method, which consults it, take about half a second.

### At the table

In the [[arena]] the threshold decides how her flaw is spent.

{{table:scarlett.threshold|Scarlett over three arenas of 24 games on the Classic board, with only her accusation threshold changed. Won and accused wrongly are percentages of the games she played.}}

At 0.3 she won three times as often as at 0.15, the setting she had used on the smaller [[ring board]], where games were too short for a tally to come right. On the Classic board the longer game gives her count time to be correct before it reaches the bar, and 0.3 was adopted.[^threshold] At that setting, in the arena that followed, she won {{fact:arena.grid.Scarlett.win}}% of her games and accused wrongly in {{fact:arena.grid.Scarlett.wrong}}%, the highest rate of wrong accusations at the table.[^arena] Each of these figures rests on about twenty games and carries an uncertainty of some ten points.

## Why use it at all

Naive Bayes has outlived half a century of cleverer methods for good reasons, all of which apply here. It needs no [[w:Training, validation, and test data sets|training]] and almost no computation. It cannot be paralysed by a hard position, as an exact method can. And when the question is which of several answers is most likely, not how likely it is, the errors of the independence assumption often cancel: the method can be optimal as a classifier even when its probabilities are far from true.[^domingos][^handyu]

What it cannot be trusted with is the number itself. [[clude]] asks each character to stake the game on a probability, and for that purpose Scarlett's method is the wrong tool on purpose. Among the six she is the reminder that confidence and accuracy are different things.

## See also

- [[Miss Scarlett]], the character who plays by this method
- [[Exact posterior enumeration]], which gets the worked example right
- [[Deduction floor]], which keeps even a naive method from believing the impossible
- [[Belief benchmark]] and [[Log-loss]]
- [[w:Naive Bayes classifier|Naive Bayes classifier]] and [[w:Bayes' theorem|Bayes' theorem]] on Wikipedia

## References

{{references}}

[^idiot]: The name "idiot's Bayes" was once common in the statistical literature. {{cite:hand-yu}}
[^domingos]: {{cite:domingos-pazzani}}
[^handyu]: {{cite:hand-yu}}
[^module]: {{cite:clude_agents/naive_bayes.py|the module's opening note and `NaiveBayesAgent.select_action`}}
[^base]: {{cite:clude_agents/base.py|`mask_and_normalize`}}
[^aima]: {{cite:russell-norvig|The chapter on quantifying uncertainty introduces naive Bayes models}}
[^architecture]: {{cite:CLAUDE.md|Architecture in brief}}
[^presets]: {{cite:clude_agents/personality.py|`PRESETS`}}
[^tuned]: {{cite:docs/strategy-glossary.md|Tuned presets}}
[^ring]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^threshold]: {{cite:docs/strategy-glossary.md|Scarlett's threshold on the grid (Stage 1d)}}
[^arena]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}

{{navbox:clude}}
