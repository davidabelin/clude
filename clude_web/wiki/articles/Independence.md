---
title: Independence
short: When knowing one event does not change the probability of another
categories: Mathematics
redirects: Conditional independence, Independent events
---
**Independence** means that learning one event occurred does not change the probability of another. Independent events permit a product rule for their joint probability. At a [[Clue]] table, this matters both when combining repeated evidence and when estimating the chance that a three-card [[accusation]] is correct.[^textbook]

The envelope's suspect, weapon and room are selected independently before play. After evidence about finite hands and disproofs, those categories can become dependent. Exact individual card probabilities therefore do not necessarily make the characters' shared product accusation score exact.

## At the table

In the Rope-question fixture, Study is proven as the room. Green holds Hall and asks about Peacock, Rope and Hall; Mustard shows Green an unseen card after the observer passes. Four cards were open: White, Peacock, Rope and Wrench, with two slots left in Mustard's hand. His answer implies he holds Peacock or Rope.[^fixture]

The surviving envelopes and remaining hand cards are:

| Envelope's suspect and weapon | Mustard's two open cards |
|---|---|
| White and Rope | Peacock and Wrench |
| White and Wrench | Peacock and Rope |
| Peacock and Wrench | White and Rope |

With equal weights, White has probability $2/3$ and Wrench $2/3$. Their joint probability is $1/3$, because just the middle row contains both. Multiplication gives $4/9$, which is too high. If White is known as the suspect, Wrench's conditional probability drops to $1/2$. That change demonstrates dependence.

{{figure:rope-deals|wide|The surviving deals preserve dependencies that separate card probabilities do not show.}}

## The product rule

Two events $A$ and $B$ are independent when

$$ P(A\cap B)=P(A)P(B). $$

For $P(B)>0$, this is equivalent to $P(A\mid B)=P(A)$. Here $\cap$ means both events occur and the vertical bar means 'given'. Independence is a statement about a probability model and its evidence, not just about events having different names.[^textbook]

Different cards are not automatically independent. Two different suspect cards are mutually exclusive envelope events: both cannot be the suspect. A suspect and weapon can be independent initially, yet linked later by a holder's possible matching cards.

For three events, a product of all three marginals needs their **mutual independence**, a stronger condition than checking each pair alone. In general, the joint is instead obtained by successive conditioning:

$$ P(A,B,C)=P(A)P(B\mid A)P(C\mid A,B). $$

$P(A,B,C)$ denotes all three events together. Conditional factors can differ from the corresponding marginals.

## Conditional independence

Events can become independent when some condition is fixed, even if they are dependent overall. **Conditional independence given $H$** means that their joint probability under $H$ factors into their separate probabilities under $H$.

Textbook [[naive Bayes]] assumes feature observations are conditionally independent given the class hypothesis. A binary posterior also requires the appropriate model under the alternative hypothesis. These are assumptions about likelihoods; 'the updates use different suggestions' is not enough to justify them.

In [[Clue]], a single hidden card can explain several answers. Conditioning only on a proposed envelope card may still leave the answering player's hand as a common cause of those answers. Scarlett's manually chosen update factors can therefore compound correlated evidence, as illustrated in her method article.

## Decisions and limits

`best_triple` chooses the largest confidence in each category and multiplies the three. This shared approximation was used even when [[PlumOG]]'s enumeration completed exactly, and is used for the current Plum's network. It also need not identify the most probable complete triple under a dependent joint distribution.[^character]

Peacock substitutes evidence-based belief bounds, but multiplying them is not generally a guaranteed joint lower bound either. The numerical interface supplies per-card values and the decision layer uses a common rule; [[belief benchmark|benchmark]] scores of card estimates and [[arena]] outcomes should be read with that distinction intact.


## See also

[[Probability]] · [[Conditional probability and Bayes' theorem]] · [[Naive Bayes]] · [[Accusation]]

## References

{{references}}

[^textbook]: {{cite:russell-norvig|Chapter 12, independence and conditional independence}}
[^fixture]: {{cite:clude_web/wiki/facts.py|`rope_observation` and `rope_question`}}
[^character]: {{cite:clude_agents/character.py|`best_triple`}}

{{navbox:clude}}
