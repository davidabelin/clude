---
title: Policy gradient
short: Learning a policy directly by nudging it towards the actions that did better than expected
kind: stub
categories: Algorithms
redirects: REINFORCE, Policy gradient methods, Policy gradient theorem
---
**Policy gradient** methods learn the policy itself, a probability for each action given the state, instead of learning values and acting greedily on them. After each episode, every action taken is made a little more likely if what followed was better than expected and a little less likely if it was worse. The simplest is REINFORCE; subtracting a *baseline*, an estimate of how good the state was anyway, makes it far less noisy without biasing it.[^book]

## The idea

For a policy $\pi(a \mid s, \boldsymbol\theta)$, the [[w:Policy gradient method|policy gradient theorem]] gives an update whose expectation climbs the expected return:

$$ \boldsymbol\theta \leftarrow \boldsymbol\theta + \alpha\, \big(G_t - b(S_t)\big)\, \nabla_{\boldsymbol\theta} \ln \pi(A_t \mid S_t, \boldsymbol\theta) $$

with $G_t$ the return that followed and $b$ the baseline, often a learnt state value.[^book]

!!! algorithm "REINFORCE with a baseline"
        Input: a policy π(a | s, θ) and a value v̂(s, w), both differentiable;
               step sizes α_θ, α_w;  discount γ
        Loop for each episode:
            play S_0, A_0, R_1, …, S_T following π
            Loop for t = 0, 1, …, T−1:
                G ← Σ_{k=t+1..T} γ^(k−t−1) R_k
                δ ← G − v̂(S_t, w)
                w ← w + α_w δ ∇_w v̂(S_t, w)
                θ ← θ + α_θ γ^t δ ∇_θ ln π(A_t | S_t, θ)

## Relation to clude

[[Professor Plum]] is trained by a policy gradient of this shape: whole-game returns, a learnt value as the baseline, standardised advantages. Two of DeepNash's changes make it [[regularised Nash dynamics]]: the reward is regularised towards a reference policy, and the step is taken on the policy's raw scores (NeuRD) rather than on the log-probability above.

## See also

[[Actor-critic]] · [[Regularised Nash dynamics]] · [[Proximal policy optimisation]] · [[Monte Carlo methods]]

## References

{{references}}

[^book]: {{cite:sutton-barto|sections 13.2 to 13.4}}

{{navbox:clude}}
