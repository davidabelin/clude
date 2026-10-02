---
title: Deep Q-network
short: Neural approximation of action values with replay and a target network
categories: Classwork
redirects: DQN, Deep Q-networks, Dueling DQN, Prioritised experience replay, Prioritized experience replay
---
A **deep Q-network** (DQN) uses a neural network to estimate the expected return of actions. The influential 2015 DQN system combined Q-learning-style targets with stored experience and a separate target network, and evaluated the method on Atari games. The [[classwork archive]] holds that paper and two extensions, dueling networks and prioritised experience replay. Clude's current characters do not implement DQN.[^dqn][^clude]

## Values from inputs

Instead of storing a separate value for every state–action pair, a network takes a representation of the state and predicts action values $Q(s,a;\theta)$, where $\theta$ denotes its learned parameters. The original Atari system used image observations. A hidden-card game would require its own observation or history representation and action encoding.

These values estimate return under a reward scheme. They are not probabilities that particular cards are in the envelope. A useful card estimator and a useful action-value estimator can support each other, but they are different learning targets.

## Replay and the target network

**Experience replay** stores transitions and samples past experience for further updates. Sampling helps reuse observations and reduce the strong correlations between successive events of one trajectory. This is learning from stored transitions, distinct from [[replay|clude's replay screen]], which displays a completed game.

A separate target network holds parameters $\theta^-$ fixed between updates. For a non-terminal transition the target has the form

$$ y=r+\gamma\max_{a'}Q(s',a';\theta^-). $$

Here $r$ is the reward, $s'$ the next state, $a'$ a legal next action and $\gamma$ the discount factor. At termination $y=r$. The online network trains towards this target, and the target parameters are periodically refreshed. Replay and the delayed target stabilise parts of training; they do not guarantee convergence for every problem.[^dqn]

## Dueling architecture

The dueling-network paper separates a state-value stream, $V(s)$, from an action-advantage stream, $A(s,a)$. Value estimates how favourable the state is; advantage describes the relative benefit of an action. One aggregation is

$$ Q(s,a)=V(s)+A(s,a)-\frac{1}{|\mathcal A|}\sum_{b\in\mathcal A}A(s,b). $$

$\mathcal A$ is the action set, and $b$ indexes its actions. Subtracting mean advantage fixes the ambiguity in splitting one Q-value into value and advantage. This architecture can share learning about a state's value when many actions have similar effects. It changes the network representation and can be combined with an existing learning algorithm.[^duel]

## Prioritised experience replay

Uniform replay samples transitions equally. Prioritised replay instead samples more often from transitions assigned high priority, commonly from the magnitude of their temporal-difference error. With priority $p_i>0$ for stored transition $i$, one form is

$$ P(i)=\frac{p_i^{\alpha}}{\sum_j p_j^{\alpha}}. $$

The exponent $\alpha$ controls how strongly priority affects sampling; at zero the distribution is uniform. Repeatedly selecting surprising transitions can accelerate learning, but changes the training distribution. Importance-sampling weights compensate for this bias, with a separate exponent controlling the degree of correction. Stochastic sampling and a positive priority floor help preserve opportunities to revisit less surprising experience.[^priority]

## Relevance to clude

A Clue learner would need to address masked evidence, variable legal choices and strategic opponents. It could not train fairly from the omniscient replay view while claiming to play from a seat's information. The reward and evaluation roster would also determine which behaviour is encouraged.

[[DeepNash]] is another archive example of deep learning in a hidden-information game, using a different method. Neither paper establishes that DQN is the best next approach for clude; the archive supplies concepts and comparisons for future experiments.


## See also

[[Q-learning]] · [[Reinforcement learning]] · [[DeepNash]] · [[Character training]]

## References

{{references}}

[^dqn]: {{cite:mnih-2015}}
[^duel]: {{cite:wang-2016}}
[^priority]: {{cite:schaul-2016}}
[^clude]: {{cite:docs/strategy-glossary.md}}

{{navbox:clude}}
