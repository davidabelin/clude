---
title: Markov decision process
short: A model of sequential decisions with state-dependent outcomes
categories: Classwork
redirects: MDP, Markov decision processes
---
A **Markov decision process** (MDP) models an agent choosing actions in states, with each action producing a next state and reward. The current state is assumed to contain the information needed to predict those outcomes: given the state and action, earlier history supplies no further predictive information. MDPs provide a framework for [[reinforcement learning]], but a player's partial view of a Clue deal is not automatically such a state.[^mdp]

## From a chain to a choice

A [[Markov chain]] specifies how a process moves between states. An MDP adds the agent's choice of action. A policy selects actions; fixing that policy induces a state-transition process. White's suggestion-sequence chain in clude is therefore not an MDP policy merely because both models use the word Markov.

In a simple movement example, a state might contain a token's square. An action chooses a legal destination, and a transition records where it arrives. That representation could suffice for a fixed navigation task. For Clue it omits the hand, evidence and opponents, which can change the value of going to the same room.

## A finite model

A finite MDP has a state set $\mathcal S$, available actions $\mathcal A(s)$, and a distribution

$$ p(s',r\mid s,a). $$

It gives the probability of next state $s'$ and reward $r$ when action $a$ is chosen in state $s$. The joint notation matters when next states and rewards are related. A policy $\pi(a\mid s)$ supplies action probabilities. Together with a discount factor $\gamma$, these define expected returns.[^interface]

The **Markov property** concerns sufficiency for predicting the next outcome. It does not require successive states to be independent, nor does it mean that a state must be a single square or number. A complete history can be sufficient where a short summary is not.

## Bellman's relation

The value under policy $\pi$ satisfies a recursive relation:

$$ v_\pi(s)=\sum_a\pi(a\mid s)\sum_{s',r}p(s',r\mid s,a)\bigl[r+\gamma v_\pi(s')\bigr]. $$

The value of the present state is the expected immediate reward plus discounted value of the next state. The equation averages over actions, next states and rewards. **Bellman equations** express this relation; they do not themselves specify how to obtain an unknown transition model.[^values]

An optimal action value replaces continuation under a fixed policy with the best available continuation. [[Q-learning]] estimates that relation from experience without requiring an explicit transition table.

## Clue as a partially observed game

The engine knows the envelope and all hands. A seat receives only its own hand, public events and the private refutations it saw. Two underlying deals can yield the same visible position and still call for different choices. Treating board position alone as the player's state loses this distinction.

A [[w:Partially observable Markov decision process|partially observable MDP]] explicitly separates hidden state from observations. A belief state can summarise the history as a distribution over hidden states when the model and update are appropriate. Clude's card marginals are useful estimates, but are not guaranteed to be a sufficient joint belief over deals and opponents.

With several strategic players, the transition also depends on their policies. The single-agent MDP formulation is useful when those policies are fixed parts of the environment; a changing self-play population needs a richer treatment. [[DeepNash]] provides one example in a different game, not a ready-made Clue model.


## See also

[[Markov chain]] · [[Reinforcement learning]] · [[Q-learning]] · [[Belief]]

## References

{{references}}

[^mdp]: {{cite:sutton-barto|Chapter 3}}
[^interface]: {{cite:sutton-barto|Section 3.1}}
[^values]: {{cite:sutton-barto|Sections 3.5 and 3.6}}

{{navbox:clude}}
