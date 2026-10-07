---
title: Proximal policy optimisation
short: A policy gradient that takes several small steps per batch and clips any step that goes too far
kind: stub
categories: Algorithms
redirects: Proximal policy optimization, PPO, Clipped surrogate objective
---
**Proximal policy optimisation** (PPO) is a [[policy gradient]] method that reuses each batch of experience for several updates while keeping the policy from moving too far from the one that gathered it. It does so by clipping: once an action's probability has changed by more than a set fraction, the objective stops rewarding further change. A distributed version of it trained the simulated walkers of the classwork archive's locomotion paper.[^ppo][^walk]

## The idea

With $r_t(\theta) = \pi_\theta(a_t \mid s_t) / \pi_{\theta_{\text{old}}}(a_t \mid s_t)$ the change in an action's probability and $\hat A_t$ its estimated advantage, PPO maximises

$$ \mathbb{E}_t\Big[\min\big(r_t(\theta)\, \hat A_t,\; \text{clip}(r_t(\theta), 1 - \epsilon, 1 + \epsilon)\, \hat A_t\big)\Big] $$

The minimum makes the bound one-sided: improvements are capped, mistakes are not.[^ppo]

!!! algorithm "PPO with the clipped objective"
        Parameters: clip ε (about 0.2);  epochs K;  minibatch size M
        Loop for each iteration:
            run the current policy π_old to collect a batch of steps
            compute advantage estimates Â_t (for example from a learnt value)
            repeat K times, over minibatches of M steps:
                r_t ← π_θ(a_t | s_t) / π_old(a_t | s_t)
                L ← mean of min(r_t Â_t, clip(r_t, 1−ε, 1+ε) Â_t)
                take a gradient step to raise L (and fit the value)
            π_old ← π_θ

## Relation to clude

[[Regularised Nash dynamics]], which trains [[Professor Plum]], addresses the same worry differently: instead of clipping how far a step may move the policy, it charges the reward for moving away from a reference copy, and it caps how far the policy's scores may be pushed.

## See also

[[Policy gradient]] · [[Actor-critic]] · [[Regularised Nash dynamics]]

## References

{{references}}

[^ppo]: {{cite:schulman-2017}}
[^walk]: {{cite:heess-2017}}

{{navbox:clude}}
