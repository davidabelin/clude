---
title: Monte Carlo methods
short: Learning values by averaging the returns of complete episodes
kind: stub
categories: Algorithms
redirects: Monte Carlo prediction, Monte Carlo control, First-visit Monte Carlo
---
**Monte Carlo methods** learn the value of a state, or of an action in a state, by playing whole episodes and averaging the returns that actually followed. They need no model of the world, only experience, and they wait until the end of an episode to learn anything. Control comes from making the policy greedy, with a little exploration, with respect to the averages as they improve.[^book]

## The idea

The return from step $t$ is the discounted sum of the rewards that follow, $G_t = R_{t+1} + \gamma R_{t+2} + \gamma^2 R_{t+3} + \dots$, and the value estimate is the average return over the visits to a state:

$$ V(s) \approx \frac{1}{N(s)} \sum_{\text{visits to } s} G $$

Each estimate is unbiased, since it is an average of real returns, but noisy, since one return carries the luck of the whole episode.[^book]

!!! algorithm "First-visit Monte Carlo control, ε-greedy"
        Parameters: ε > 0;  discount γ
        Initialise Q(s, a) ← 0 and N(s, a) ← 0;  π ← ε-greedy in Q
        Loop for each episode:
            play an episode S_0, A_0, R_1, …, S_T following π
            G ← 0
            Loop for t = T−1, T−2, …, 0:
                G ← γ G + R_(t+1)
                if (S_t, A_t) does not occur earlier in the episode:
                    N(S_t, A_t) ← N(S_t, A_t) + 1
                    Q(S_t, A_t) ← Q(S_t, A_t) + (G − Q(S_t, A_t)) / N(S_t, A_t)
            π ← ε-greedy in Q

## Relation to clude

[[Professor Plum]]'s training is a Monte Carlo method in this sense: each game is played to the end and every decision is credited with the regularised return that followed it, with the network's value head as the baseline ([[regularised Nash dynamics]]). The [[belief benchmark]] and [[arena]] are Monte Carlo measurements: averages over many complete games.

## See also

[[Temporal-difference learning]] · [[Dynamic programming]] · [[Monte Carlo tree search]] · [[Policy gradient]]

## References

{{references}}

[^book]: {{cite:sutton-barto|Chapter 5, sections 5.1 to 5.4}}

{{navbox:clude}}
