---
title: Q-learning
short: Updating action values towards reward plus the best estimated continuation
categories: Classwork
redirects: Q learning
---
**Q-learning** is a reinforcement-learning method that estimates the value of taking each action in a state. After an observed transition, it updates the chosen state–action pair towards the received reward plus the best estimated value at the next state. It is an **off-policy** method: its target follows a greedy policy even when the actions gathering experience are exploratory.[^q]

Q-learning is part of the [[classwork archive]], rather than the current action-selection algorithm of clude's six characters. Their common scorer ranks immediate legal options from card beliefs and personality settings; it does not maintain a learned table of long-term action returns.[^code]

## An update by example

Suppose a toy navigation task gives reward 1 for a transition. The current estimate for the chosen action is 2, and the best estimate at the next state is 4. With discount factor 0.9, the target is $1+0.9\times4=4.6$. With learning rate 0.5, the new estimate moves halfway towards that target: $2+0.5(4.6-2)=3.3$.

These are illustrative values, not clude measurements. The update need not have seen the eventual finish: it uses the next state's estimate as a stand-in for later reward. This **bootstrapping** is useful, but an inaccurate continuation estimate can also make the present update inaccurate.

## The rule

For a state $S_t$, action $A_t$, next state $S_{t+1}$ and reward $R_{t+1}$, the tabular update is

$$ Q(S_t,A_t)\leftarrow Q(S_t,A_t)+\alpha\left[R_{t+1}+\gamma\max_a Q(S_{t+1},a)-Q(S_t,A_t)\right]. $$

$Q$ stores the action-value estimates, $\alpha$ is the learning rate and $\gamma$ is the discount factor. The maximum ranges over legal next actions. At a terminal state the continuation value is zero. The bracketed quantity is the **temporal-difference error**: target minus present estimate.[^q]

The notation assumes that the state representation supports the [[Markov decision process|MDP]] model. In a hidden-card game, a player's observation is not necessarily a sufficient state. An unqualified application of the formula cannot restore information discarded by a poor representation.

## Behaviour and target policies

A common behaviour policy is **epsilon-greedy**: usually take an action with the highest estimated value, but sometimes explore. The Q-learning target uses a maximum regardless of which next action this behaviour policy actually takes. That is why it is off-policy. Sarsa, by comparison, uses the value of the next action sampled by the behaviour policy.[^sarsa]

Exploration must cover the relevant state–action pairs if a tabular learner is to discover their values. The classical convergence result also assumes a finite stationary MDP, bounded rewards and a suitable diminishing learning-rate schedule. It is not a general guarantee for a neural network, a partially observed game or continuously changing opponents.[^q]

## From a table to a network

A table is practical when the state–action space is small enough to store and visit. A [[deep Q-network]] replaces it with a neural approximation. This can generalise between inputs, but updating one example can change estimates elsewhere. Experience replay and target networks address parts of that training difficulty; they do not retain the tabular guarantee automatically.

For clude, a future Q-learning experiment would need a defined state or history representation, legal-action interface, reward and opponent regime. [[Character training]] separates such possible experiments from supervised tree fitting, method memory and preset tuning already in the project.


## See also

[[Reinforcement learning]] · [[Deep Q-network]] · [[Character training]] · [[Classwork archive]]

## References

{{references}}

[^q]: {{cite:sutton-barto|Section 6.5}}
[^sarsa]: {{cite:sutton-barto|Section 6.4}}
[^code]: {{cite:clude_agents/character.py|`score_actions`}}

{{navbox:clude}}
