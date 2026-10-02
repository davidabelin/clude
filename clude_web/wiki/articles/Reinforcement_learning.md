---
title: Reinforcement learning
short: Learning a policy from actions, rewards and subsequent experience
categories: Classwork
redirects: RL
---
**Reinforcement learning** is learning how to act from interaction with an environment. An agent chooses actions, receives rewards and observations, and seeks a policy that produces a high expected return over time. It differs from being given the correct action for each training example: actions can change what the agent will encounter, and a useful action may pay off much later.[^intro]

The [[classwork archive]] includes the standard textbook and several reinforcement-learning papers. In [[clude]], [[Mr. Green|Green's bandit]] provides a limited reward-based choice among estimators, while [[Colonel Mustard|Mustard's tree]] is supervised learning. Current characters do not learn a complete Clue policy through Q-learning or deep reinforcement learning.[^implementation]

## A delayed result

Consider a possible learning task for a Clue player. It can enter a nearby room and ask a useful question now, or walk towards a distant room it considers likely to be in the envelope. Neither move itself wins the game. The eventual correct accusation supplies an outcome, but the learner must determine how earlier choices contributed to it.

Rewarding only a win makes that judgement difficult when many choices precede the result. Adding rewards for entering rooms or reducing uncertainty can make feedback more frequent, but may encourage collecting those rewards while losing the race to accuse. This is a task-design example, rather than clude's current training rule.

## Agent, policy and value

{{figure:learning-loop|wide|An agent chooses an action; the environment returns reward and a new observation. What the agent observes can be less than the environment's complete state.}}

The **agent** is the decision-maker; the **environment** supplies the consequences of its actions. A **policy**, written $\pi(a\mid s)$, gives the probability of action $a$ in state $s$. A deterministic policy chooses one action; a stochastic policy assigns probabilities to several.

A **reward** is the feedback received at a step. The **return** combines rewards over the future. A **value function** estimates expected return: $v_\pi(s)$ for a state, or $q_\pi(s,a)$ for taking an action and then following the policy. Value is about future reward, not necessarily the probability that a hidden card is in the envelope. [[Belief]] estimates and action values answer different questions.[^elements]

## Return and discounting

For rewards $R_{t+1},R_{t+2},\ldots$, one common return is

$$ G_t=\sum_{k=0}^{\infty}\gamma^k R_{t+k+1}. $$

Here $t$ is the present step and $\gamma$ is the discount factor, between zero and one. A smaller factor weights distant rewards less. For a finite episode the sum ends at termination; an undiscounted episodic task can use $\gamma=1$ when its expected return is well defined. Discounting does not replace a clear definition of what earns reward.[^returns]

## Exploration and learning

An agent needs experience of alternatives to discover a useful policy. **Exploration** gathers that experience; **exploitation** uses what it already estimates to be best. A [[bandit ensemble|bandit]] models a narrower choice among arms, while a sequential task includes transitions through states and delayed consequences.

[[Q-learning]] updates action values from observed transitions, using a target based on the best estimated next action. A [[deep Q-network]] approximates values with a neural network. Other methods learn a policy directly or combine a policy with a value estimator. [[DeepNash]] uses a different self-play learning method for Stratego.

## Hidden information and opponents

The ordinary [[Markov decision process]] formulation assumes a sufficient state representation. A Clue seat sees a hand and a masked history, not the complete deal. A belief about possible deals can represent uncertainty, but discarding history without a sufficient summary can lose information needed for future decisions.

Other players also choose actions. Training against fixed opponents and training against opponents who are learning describe different environments. A policy that wins against one roster may fail against another. These issues make [[self-play]] and evaluation conditions part of the learning problem, rather than incidental setup details.


## See also

[[Markov decision process]] · [[Q-learning]] · [[Character training]] · [[Self-play]]

## References

{{references}}

[^intro]: {{cite:sutton-barto|Sections 1.1 and 1.2}}
[^elements]: {{cite:sutton-barto|Section 1.3 and Chapter 3}}
[^returns]: {{cite:sutton-barto|Section 3.3}}
[^implementation]: {{cite:docs/strategy-glossary.md|Phase 7: memory (2026-09-14)}}

{{navbox:clude}}
