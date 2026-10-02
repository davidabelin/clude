---
title: Conditional probability and Bayes' theorem
short: Updating a probability when new evidence is observed
categories: Mathematics
redirects: Conditional probability, Bayes' theorem, Bayes theorem, Posterior probability
---
**Conditional probability** is the probability of an event given some evidence. **Bayes' theorem** relates this updated probability to the event's prior probability and the likelihood of observing that evidence if the event were true. In [[Clue]], the evidence includes private cards, passes and disproofs; the events concern the hidden deal.[^textbook]

The theorem is a rule of probability, not a guarantee that a particular model is accurate. A useful update needs appropriate prior weights and likelihoods. Scarlett's [[naive Bayes]] implementation uses manually chosen multipliers rather than a fitted likelihood model, while Plum's completed enumeration counts deals under explicit assumptions.

## A small update

Consider the constructed Rope-question position. Study is the solution room, Green holds Hall, and White, Peacock, Rope and Wrench remain open between Mustard's two spare hand slots and the envelope. Before the question, the four suspect–weapon envelopes are equally weighted: White–Rope, White–Wrench, Peacock–Rope and Peacock–Wrench.[^example]

Green suggests Peacock, Rope and Hall. The observer passes and Mustard answers privately. Hall cannot be his because Green holds it, so the evidence is that Mustard has Peacock or Rope. The Peacock–Rope envelope is ruled out: it would leave Mustard with White and Wrench and no matching card. Three equally weighted deals remain, two with White in the envelope. White's probability rises from $1/2$ to $2/3$.

The answer did not show the observer a suspect card. It still changed the suspect probabilities by coupling them to Mustard's possible weapon card.

## Conditional probability

Let $A$ mean 'White is in the envelope' and $E$ the evidence that Mustard can answer. The vertical bar in $P(A\mid E)$ means 'given $E$'. The definition is

$$ P(A\mid E)=\frac{P(A\cap E)}{P(E)},\qquad P(E)>0. $$

$A\cap E$ means both events occur. Conditioning keeps the outcomes compatible with the evidence and renormalises their probability to sum to 1. In the fixture, $P(E)=3/4$ and $P(A\cap E)=1/2$, giving $(1/2)/(3/4)=2/3$.

The requirement $P(E)>0$ matters. If a model says observed evidence was impossible, this formula supplies no ordinary update. A contradiction can indicate a wrong input, mistaken assumptions or a model that excluded a possible event.

## Bayes' theorem

The same result can be written

$$ P(A\mid E)=\frac{P(E\mid A)P(A)}{P(E)}. $$

$P(A)$ is the **prior**, before this evidence. $P(E\mid A)$ is the **likelihood**: how likely the answer is if White is the envelope suspect. $P(A\mid E)$ is the **posterior**, after the evidence. The denominator weights all ways the evidence could occur.[^textbook]

In the fixture, $P(A)=1/2$ and $P(E\mid A)=1$: if White is the envelope suspect, Mustard necessarily holds Peacock and can answer. If Peacock is the envelope suspect, Mustard can answer only in the half of prior cases where he holds Rope. Thus

$$ P(E)=1\times\frac12+\frac12\times\frac12=\frac34. $$

Bayes' theorem gives the same $2/3$ as direct counting. The two calculations differ in presentation, not in the underlying uniform four-deal model.

## Likelihoods and repeated evidence

A formal disproof means that a holder has at least one named card. A behavioural model can also ask why the player chose that suggestion, or which matching card a refuter would prefer to show. The completed enumeration model does not assign likelihoods to these policies; it treats formally consistent deals equally.

Repeated evidence needs care. Hearing the same claim twice does not make it two independent observations. A single held card can explain several disproofs. [[Independence]] states the assumptions required to multiply likelihood factors, and [[naive Bayes]] distinguishes its textbook version from Scarlett's heuristic reuse of suggestions.

## In clude

All methods receive the same kind of private observation and floor constraints. They need not implement the same posterior. A tree's leaf score, White's behaviour-based score and Peacock's evidence mass have different origins before they are mapped into the shared [[belief]] format.[^methods]

Calling a number a probability therefore identifies the decision interface, not proof that every method followed Bayes' theorem with the true data-generating process. The [[belief benchmark]] measures how those estimates performed on recorded evidence.


## See also

[[Probability]] · [[Independence]] · [[Naive Bayes]] · [[Exact posterior enumeration]]

## References

{{references}}

[^textbook]: {{cite:russell-norvig|Chapter 12, Bayes’ rule}}
[^example]: {{cite:clude_web/wiki/facts.py|`rope_observation`}}
[^methods]: {{cite:docs/architecture.md|`AgentProtocol`}}

{{navbox:clude}}
