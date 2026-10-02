---
title: Beta distribution
short: A distribution over values between zero and one used for Green’s arms
categories: Mathematics
redirects: Beta, Beta distributions
---
The **Beta distribution** describes a continuous uncertain quantity between 0 and 1. Its two positive shape parameters can represent evidence about a success rate. [[Mr. Green]] uses Beta records to draw scores for the five methods in his [[bandit ensemble]], selecting the method with the largest draw.[^tutorial]

His implementation uses fractional rank rewards and decays old evidence. Its Beta parameters are therefore heuristic preference records, not a calibrated posterior probability that a method is best. The textbook binary-success interpretation helps explain the mechanism but needs additional assumptions to apply literally.

## A small example

The uniform Beta distribution has parameters $\alpha=1$ and $\beta=1$. Every equal-length interval inside 0 to 1 then has equal probability. Starting with this prior, three successes and one failure in a fixed-rate Bernoulli model give $\operatorname{Beta}(4,2)$.

The mean of that posterior is $4/(4+2)=2/3$, rather than the observed success fraction $3/4$. The starting prior contributes to the posterior. A larger record with the same parameter ratio is more concentrated around that mean.

{{figure:green-arms|wide|Green's arm records after the constructed Rope-question lesson. The displayed curves concern uncertain arm scores, not card locations.}}

This figure uses the real ensemble's parameters after one revealed fixture. Green first evaluates all five arms on the same private observation. Their loss ranking supplies the updates; an arm's Beta mean is not its probability for White, Rope or another envelope card.

## Density and parameters

For $0<x<1$, positive shape parameters $\alpha$ and $\beta$ give density

$$ f(x)=\frac{x^{\alpha-1}(1-x)^{\beta-1}}{B(\alpha,\beta)}. $$

$B(\alpha,\beta)$ is the normalising Beta function: the integral of the numerator from 0 to 1. A density describes relative probability per interval, not a probability at a single exact continuous value. It can exceed 1 while the total area remains 1.

The mean and variance are[^density]

$$ \mathbb E[X]=\frac{\alpha}{\alpha+\beta},\qquad
\operatorname{Var}(X)=\frac{\alpha\beta}{(\alpha+\beta)^2(\alpha+\beta+1)}. $$

$X$ is the uncertain quantity, $\mathbb E$ denotes its mean and variance measures its spread. Scaling both parameters up at a fixed ratio narrows that spread. Not every Beta curve is a bell: the uniform case is flat, and other parameter choices can concentrate density near either boundary.

## Binary feedback and Thompson sampling

For independent binary trials with a fixed unknown success rate, a Beta prior remains Beta after the observations. Each success adds one to $\alpha$ and each failure one to $\beta$. This is **conjugacy**: the posterior stays in the same distribution family.[^tutorial]

Textbook [[w:Thompson sampling|Thompson sampling]] draws a plausible success rate for each arm from its posterior and plays the arm with the highest draw. The draw concerns the uncertain rate, not the next binary outcome. An uncertain arm can occasionally draw high enough to be explored even if its mean is lower.

## Green's adaptation

Green begins each arm at Beta(1,1). At feedback, he moves its parameters towards that prior by dividing the excess above 1 by {{code:green.decay}}, then adds {{code:green.step_size}} times its rank reward to $\alpha$ and the complementary amount to $\beta$. All arms receive feedback because he computed all their predictions.[^green]

The reward is between 0 and 1 rather than a Bernoulli success, and decay makes older rankings fade. His update can resemble the textbook model under special settings and binary rewards, but the default interpretation is a recency-weighted ranking heuristic. The [[bandit ensemble]] article gives the complete equations and limitations.

## Memory and limits

Green can save and restore these arm records as [[method memory]]. Their influence changes with the evidence policy and board because a method that predicts one regime well can fare differently in another. A high Beta mean is not a universal endorsement of that method.

The ensemble also pays to compute all five arms before selecting one. Thompson-style selection does not make the unchosen computations free, and the use of full feedback distinguishes this implementation from the usual bandit setting where only the played arm's outcome is observed.


## See also

[[Bandit ensemble]] · [[Probability]] · [[Method memory]] · [[Log-loss]]

## References

{{references}}

[^tutorial]: {{cite:russo-2018|Section 3, Beta–Bernoulli bandit}}
[^density]: {{cite:nist-beta|Standard density, mean and standard deviation}}
[^green]: {{cite:clude_agents/bandit.py|`_Candidate`, `select_action` and `observe`}}

{{navbox:clude}}
