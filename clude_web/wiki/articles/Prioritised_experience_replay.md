---
title: Prioritised experience replay
short: Replaying the surprising experiences more often than the dull ones
kind: stub
categories: Algorithms
redirects: Prioritized experience replay, PER, Prioritised replay
---
**Prioritised experience replay** changes how a [[deep Q-network]] samples its memory. Plain experience replay picks stored transitions uniformly; the prioritised version picks them in proportion to how wrong the network was about them last time, the size of their [[temporal-difference learning|TD error]], so learning concentrates where there is most to learn. Because that skews the sample, each update is reweighted to correct the bias.[^paper]

## The idea

Transition $i$ with TD error $\delta_i$ gets priority $p_i = |\delta_i| + \epsilon$ and is drawn with probability

$$ P(i) = \frac{p_i^{\alpha}}{\sum_k p_k^{\alpha}}, \qquad w_i = \Big(\frac{1}{N \cdot P(i)}\Big)^{\beta} $$

where $\alpha$ sets how strongly priority counts and the importance weight $w_i$, raised towards full correction as $\beta \to 1$, scales the update.

!!! algorithm "Learning from a prioritised buffer"
        Parameters: α, β, batch size B, step size η
        Loop for each learning step:
            draw B transitions, transition i with probability P(i) = p_i^α / Σ_k p_k^α
            for each drawn i:
                δ_i ← r_i + γ max_a Q_target(s′_i, a) − Q(s_i, a_i)
                w_i ← (N · P(i))^(−β), divided by the largest w in the batch
                p_i ← |δ_i| + ε
            take a gradient step on Σ_i w_i δ_i², with step size η

## Relation to clude

[[Professor Plum]]'s trainer keeps a replay buffer for its belief head, sampled uniformly: its purpose was to stop the head memorising one batch, not to favour the surprising positions.

## See also

[[Deep Q-network]] · [[Dueling network architecture]] · [[Dyna-Q]]

## References

{{references}}

[^paper]: {{cite:schaul-2016}}

{{navbox:clude}}
