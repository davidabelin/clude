---
title: Sarsa
short: On-policy TD control, learning the value of the actions the agent actually takes
kind: stub
categories: Algorithms
redirects: Expected Sarsa, State-action-reward-state-action
---
**Sarsa** is [[temporal-difference learning]] for control: it learns the value $Q(s, a)$ of taking each action in each state, while choosing actions ε-greedily from those same values. Its name is the five things each update uses: the State, the Action, the Reward, the next State and the next Action. Because the next action is the one the agent will really take, exploration included, Sarsa learns the value of the policy it is following, which is called *on-policy* learning.[^book]

## The idea

$$ Q(S_t, A_t) \leftarrow Q(S_t, A_t) + \alpha\big[R_{t+1} + \gamma Q(S_{t+1}, A_{t+1}) - Q(S_t, A_t)\big] $$

*Expected Sarsa* replaces the sampled next action with the average over the policy's choices, $\sum_a \pi(a \mid S_{t+1}) Q(S_{t+1}, a)$, which removes the noise of that one draw. If the policy is greedy, Expected Sarsa becomes [[Q-learning]].[^book][^sheet]

!!! algorithm "Sarsa"
        Parameters: step size α;  ε > 0;  discount γ
        Initialise Q(s, a) ← 0 for every state and action
        Loop for each episode:
            S ← the first state;  A ← ε-greedy choice in S from Q
            Loop until S is terminal:
                take A;  observe R and S′
                A′ ← ε-greedy choice in S′ from Q
                Q(S, A) ← Q(S, A) + α [R + γ Q(S′, A′) − Q(S, A)]
                S ← S′;  A ← A′

## Relation to clude

The rps project's reinforcement-learning player is tabular [[Q-learning]], Sarsa's off-policy sibling. clude's own trained player, [[Professor Plum]], learns a policy directly rather than action values ([[policy gradient]]).

## See also

[[Q-learning]] · [[Temporal-difference learning]] · [[Bandit action selection]]

## References

{{references}}

[^book]: {{cite:sutton-barto|sections 6.4 and 6.6}}
[^sheet]: {{cite:drive-cheatsheet|Algorithms 13 and 15}}

{{navbox:clude}}
