---
title: Temporal-difference learning
short: Learning a guess from a better guess: TD(0), n-step TD and TD(λ)
kind: stub
categories: Algorithms
redirects: TD learning, TD(0), TD(λ), TD lambda, n-step TD, Eligibility traces, Bootstrapping (reinforcement learning)
---
**Temporal-difference learning** (TD) updates a value estimate after every step, using the reward just received plus the current estimate of the next state's value, rather than waiting for the end of the episode as [[Monte Carlo methods]] do. Learning a guess from a guess is called *bootstrapping*. It makes TD faster to learn and less noisy, at the cost of some bias while the estimates are still wrong. Sutton and Barto call it the idea most central and novel to reinforcement learning.[^book]

## The idea

The *TD error* is the difference between what was expected and what one step of experience suggests:

$$ \delta_t = R_{t+1} + \gamma V(S_{t+1}) - V(S_t), \qquad V(S_t) \leftarrow V(S_t) + \alpha\, \delta_t $$

Between one step and a whole episode lies a range. *n-step TD* looks $n$ rewards ahead before bootstrapping. *TD(λ)* blends all the n-step targets, weighting each further step by $\lambda$, and does so efficiently with an *eligibility trace* that remembers how recently and how often each state was visited.[^book]

!!! algorithm "TD(0) prediction"
        Input: the policy π to evaluate;  step size α;  discount γ
        Initialise V(s) ← 0 for every state (0 for the terminal state)
        Loop for each episode:
            S ← the first state
            Loop until S is terminal:
                A ← the action π gives in S
                take A;  observe R and the next state S′
                V(S) ← V(S) + α [R + γ V(S′) − V(S)]
                S ← S′

## Relation to clude

clude's trainer for [[Professor Plum]] does not bootstrap: its targets are whole-game returns. A TD target would let its value head learn from a position without waiting for the game's end; the trainer described in [[regularised Nash dynamics]] does not use one.

## See also

[[Sarsa]] · [[Q-learning]] · [[Monte Carlo methods]] · [[Function approximation]]

## References

{{references}}

[^book]: {{cite:sutton-barto|sections 6.1 to 6.3, 7.1 and 12.1 to 12.2}}

{{navbox:clude}}
