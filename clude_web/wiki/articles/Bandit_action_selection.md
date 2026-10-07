---
title: Bandit action selection
short: Epsilon-greedy, upper confidence bounds and gradient bandits: choosing among options of unknown worth
kind: stub
categories: Algorithms
redirects: Epsilon-greedy, ε-greedy, Upper confidence bound, UCB, Gradient bandit
---
**Bandit action selection** is the problem of choosing, again and again, among options whose rewards are uncertain, learning their worth from the choices themselves. The name comes from the [[w:Multi-armed bandit|multi-armed bandit]], a row of slot machines with unknown payouts. Every method balances *exploitation*, taking the option that looks best, against *exploration*, trying others in case they are better. Sutton and Barto's second chapter introduces three ways to strike the balance.[^book]

## The idea

Each option $a$ keeps an estimate $Q(a)$ of its average reward, updated incrementally after it is tried for the $n$-th time:

$$ Q(a) \leftarrow Q(a) + \frac{1}{n}\big(R - Q(a)\big) $$

- **ε-greedy**: take the best-looking option, except with small probability $\varepsilon$ take one at random.
- **Upper confidence bound** (UCB): take the option with the highest optimistic estimate, $Q(a) + c\sqrt{\ln t / N(a)}$, so that rarely-tried options get the benefit of the doubt.
- **Gradient bandit**: keep a preference $H(a)$ per option, choose by [[softmax and temperature|softmax]] over preferences, and nudge the chosen option's preference up when its reward beats the running average.

!!! algorithm "ε-greedy bandit"
        Parameters: ε ∈ (0, 1)
        Initialise Q(a) ← 0 and N(a) ← 0 for every option a
        Loop for each step:
            with probability ε: A ← a random option
            otherwise:          A ← argmax_a Q(a)    (ties broken at random)
            R ← the reward for taking A
            N(A) ← N(A) + 1
            Q(A) ← Q(A) + (R − Q(A)) / N(A)

## Relation to clude

[[Mr. Green]]'s [[bandit ensemble]] treats the other five methods as arms, with a fourth way of choosing, [[w:Thompson sampling|Thompson sampling]]: he draws a plausible score for each arm from its [[Beta distribution|Beta]] record and takes the highest.

## See also

[[Bandit ensemble]] · [[Ensemble voting]] · [[Reinforcement learning]] · [[Beta distribution]]

## References

{{references}}

[^book]: {{cite:sutton-barto|sections 2.2, 2.4, 2.7 and 2.8}}

{{navbox:clude}}
