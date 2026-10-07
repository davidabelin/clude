---
title: Dueling network architecture
short: A Q-network split into how good the state is and how much better each action is
kind: stub
categories: Algorithms
redirects: Dueling DQN, Dueling network, Dueling architecture
---
The **dueling network architecture** is a change to the [[deep Q-network]]: instead of one stream of numbers estimating each action's value, the network splits into two streams, one estimating how good the state is, $V(s)$, and one estimating how much better or worse each action is than average, the *advantage* $A(s, a)$, and adds them back together. In many states most actions hardly matter, and learning the state's value once, rather than separately for every action, makes learning faster and steadier.[^paper]

## The idea

$$ Q(s, a) = V(s) + \Big(A(s, a) - \frac{1}{|\mathcal{A}|}\sum_{a'} A(s, a')\Big) $$

Subtracting the mean advantage makes the split unique: without it, any constant could move from $V$ to $A$ and back.

!!! algorithm "A dueling Q-network's forward pass"
        Input: a state s
        h ← the shared layers applied to s
        V ← the value stream applied to h                 (one number)
        A(a) ← the advantage stream applied to h          (one per action)
        Q(s, a) ← V + A(a) − mean over a′ of A(a′)        for every action a
        (train Q exactly as a deep Q-network is trained)

## Relation to clude

[[Professor Plum]]'s network shares the idea of one trunk read by several heads, a value head among them, but it learns a policy rather than action values, so it has no Q to decompose.

## See also

[[Deep Q-network]] · [[Prioritised experience replay]] · [[Actor-critic]]

## References

{{references}}

[^paper]: {{cite:wang-2016}}

{{navbox:clude}}
