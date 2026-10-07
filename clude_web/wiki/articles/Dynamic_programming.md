---
title: Dynamic programming
short: Policy evaluation, policy iteration and value iteration, when the model of the world is known
kind: stub
categories: Algorithms
redirects: Policy iteration, Value iteration, Policy evaluation, Generalised policy iteration
---
In reinforcement learning, **dynamic programming** (DP) is the family of methods that compute the best policy for a [[Markov decision process]] whose rules are fully known: every state, every action, every probability of every outcome. They work by sweeping over the states, improving each state's value from its neighbours' until nothing changes. They need a perfect model and visit every state, so they are rarely used as they stand; but every later method in the textbook is, in Sutton and Barto's words, an attempt to achieve the same effect with less computation and without a perfect model.[^book]

## The idea

The value of a state under a policy $\pi$ satisfies the [[w:Bellman equation|Bellman equation]], which policy evaluation solves by repeated sweeps:

$$ v_\pi(s) = \sum_a \pi(a \mid s) \sum_{s', r} p(s', r \mid s, a)\big[r + \gamma\, v_\pi(s')\big] $$

*Policy iteration* alternates evaluating the policy and making it greedy with respect to the values; *value iteration* folds both into one sweep by taking the best action's value directly. The alternation of evaluation and improvement, in any proportion, is *generalised policy iteration*, the pattern most methods share.[^book][^sheet]

{{figure:gpi|Generalised policy iteration: evaluation and improvement, each making the other out of date, until both settle.}}

!!! algorithm "Value iteration"
        Input: a known model p(s′, r | s, a); discount γ; tolerance θ > 0
        Initialise V(s) ← 0 for every state s
        Loop:
            Δ ← 0
            for each state s:
                v ← V(s)
                V(s) ← max_a Σ_{s′, r} p(s′, r | s, a) [r + γ V(s′)]
                Δ ← max(Δ, |v − V(s)|)
        until Δ < θ
        return the policy π(s) = argmax_a Σ_{s′, r} p(s′, r | s, a) [r + γ V(s′)]

## Relation to clude

Clue is far too large for this: a state would have to include the hidden deal and every player's knowledge. clude's [[deduction floor]] is a kind of sweep to a fixed point, though over logical facts rather than values.

## See also

[[Markov decision process]] · [[Monte Carlo methods]] · [[Temporal-difference learning]] · [[Reinforcement learning]]

## References

{{references}}

[^book]: {{cite:sutton-barto|Chapter 4, sections 4.1 to 4.6}}
[^sheet]: {{cite:drive-cheatsheet|Algorithms 1 to 7}}

{{navbox:clude}}
