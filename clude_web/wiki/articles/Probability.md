---
title: Probability
short: A numerical description of uncertainty about the hidden deal
categories: Mathematics
redirects: Probabilities
---
**Probability** describes uncertainty by assigning numbers from 0 to 1 to possible events. At a [[Clue]] table, an event might be 'White is the envelope's suspect' or 'Mustard holds Rope'. A probability of 0 rules out an event under the model; 1 makes it certain under that model. Intermediate values express degrees of uncertainty.[^textbook]

In [[clude]], each method returns probabilities for the individual envelope cards, normalised separately among suspects, weapons and rooms. These are estimates conditioned on a seat's evidence. They need not be perfectly calibrated, and they do not by themselves specify the probability of a complete accusation.

## At the table

{{figure:rope-deals|wide|Three complete deals survive the constructed Rope question. White appears in two surviving envelopes, but White together with Wrench appears in only one.}}

In this fixture, Study is proven as the envelope room. Only White, Peacock, Rope and Wrench remain unplaced between Mustard's two remaining hand slots and the envelope. Green holds Hall and asks about Peacock, Rope and Hall. The observer passes; Mustard shows Green an unseen card. Because Hall is Green's, Mustard must hold Peacock or Rope.[^example]

Three deals survive. Under the model that gives those deals equal weight, White is in two envelopes, so its probability is $2/3$. Peacock is in the other, so its probability is $1/3$. The two suspect probabilities sum to 1. Wrench also occurs in two surviving envelopes, yet White and Wrench occur together in only one. The triple's probability cannot be recovered simply by multiplying the two marginals.

## Outcomes and events

A **sample space** is the set of possible outcomes under consideration. A complete deal specifies every hand and the envelope. An **event** is a subset of those outcomes, such as all deals placing White in the envelope. For equally weighted outcomes,

$$ P(A)=\frac{\text{number of outcomes in }A}{\text{total number of outcomes}}. $$

$P(A)$ means the probability of event $A$. The counting formula needs equal weights. If a model assigns different weights to deals, the probability is the sum of the weights belonging to the event instead. Merely listing possible deals does not establish that each is equally likely after all forms of evidence.

For the fixture, uniform weights mean one third per surviving deal. [[Exact posterior enumeration]] uses a uniform consistent-deal model based on ownership, hand sizes and formal evidence, without modelling the choices that caused each question or card show.

## Category probabilities

Exactly one suspect card is in the envelope, so the suspect events are mutually exclusive and collectively exhaustive. Their probabilities sum to 1. Weapons and rooms each form a separate such category. All {{code:cards.total}} envelope-card probabilities together therefore sum to 3, not 1.[^belief]

A card in the player's own hand has envelope probability 0. A proven envelope card has probability 1, and all other cards in its category receive 0. The [[deduction floor]] enforces these certainties around each method's estimates.

The [[uniform baseline]] divides a category's probability equally among remaining candidates. With four suspects still permitted it gives each one quarter. This is simple and useful, but it is not necessarily what counting consistent complete deals would produce.

## Conditional and joint probabilities

[[Conditional probability and Bayes' theorem|Conditional probability]] updates an event's probability in light of evidence. A **marginal** describes one part of an outcome, such as its suspect. A **joint probability** describes several parts together, such as White and Wrench being the suspect and weapon.[^textbook]

[[Independence]] is the condition that permits multiplication of marginals. The engine initially chooses envelope categories independently, but formal evidence can couple them later. Most characters nevertheless multiply their best three card probabilities for the [[accusation threshold]]. This is a shared decision approximation rather than an identity for every posterior.

## Estimates and calibration

A method that frequently assigns 0.8 to events which happen only half the time is overconfident. Calibration concerns this relationship across predictions, not whether one particular 0.8 event occurs. An unlikely event can occur without disproving a probability model on its own.

The [[belief benchmark]] evaluates estimates against completed games using [[log-loss]], squared error and top-choice accuracy. These scores answer different questions. Low loss supports better probability predictions in that evaluation, while an [[arena]] win also depends on movement, disclosure and accusation timing.


## See also

[[Conditional probability and Bayes' theorem]] · [[Independence]] · [[Belief]] · [[Combinatorics of a deal]]

## References

{{references}}

[^textbook]: {{cite:russell-norvig|Chapter 12, quantifying uncertainty}}
[^example]: {{cite:clude_web/wiki/facts.py|`rope_observation` and `rope_question`}}
[^belief]: {{cite:clude_agents/base.py|`ClueBelief` and `mask_and_normalize`}}

{{navbox:clude}}
