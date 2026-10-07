---
title: Dyna-Q
short: Learning from real steps and from steps replayed from a learnt model of the world
kind: stub
categories: Algorithms
redirects: Dyna, Dyna architecture
---
**Dyna-Q** combines learning with planning. Each real step updates the action values as [[Q-learning]] would, and also records what happened in a simple model of the world. Between real steps, the agent replays imagined steps drawn from that model and learns from them too. A few real experiences are thereby used many times, so the agent learns more from less play.[^book]

## The idea

The model remembers, for each state and action tried, the reward and next state that followed, $\text{Model}(s, a) = (r, s')$. Planning is the same update as learning, applied to remembered transitions:

$$ Q(s, a) \leftarrow Q(s, a) + \alpha\big[r + \gamma \max_{a'} Q(s', a') - Q(s, a)\big], \quad (r, s') = \text{Model}(s, a) $$

!!! algorithm "Tabular Dyna-Q"
        Parameters: step size α;  ε;  discount γ;  planning steps n
        Initialise Q(s, a) ← 0 and an empty Model
        Loop forever:
            S ← the current state;  A ← ε-greedy choice in S from Q
            take A;  observe R and S′
            Q(S, A) ← Q(S, A) + α [R + γ max_a Q(S′, a) − Q(S, A)]
            Model(S, A) ← (R, S′)
            repeat n times:
                (s, a) ← a state and action tried before, at random
                (r, s′) ← Model(s, a)
                Q(s, a) ← Q(s, a) + α [r + γ max_a′ Q(s′, a′) − Q(s, a)]

## Relation to clude

Replaying stored experience is also what [[Professor Plum]]'s belief head does: it trains on a buffer of states from the last ten iterations, the remedy for memorising a single batch. That buffer replays real states, not a learnt model's.

## See also

[[Q-learning]] · [[Prioritised experience replay]] · [[Monte Carlo tree search]]

## References

{{references}}

[^book]: {{cite:sutton-barto|sections 8.1 and 8.2}}

{{navbox:clude}}
