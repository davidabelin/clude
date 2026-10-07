---
title: Actor-critic
short: A policy (the actor) trained step by step against a learnt value (the critic)
kind: stub
categories: Algorithms
redirects: Actor–critic, Actor critic, Advantage actor-critic, A2C
---
An **actor-critic** method keeps two learners. The *actor* is a policy; the *critic* estimates state values. After each step the critic judges the actor's action by the [[temporal-difference learning|TD error]], the reward plus the next state's estimated value less the current state's, and the actor moves towards actions the critic judged better than expected. It is a [[policy gradient]] method that learns every step instead of waiting for the episode to end.[^book]

## The idea

$$ \delta_t = R_{t+1} + \gamma\, \hat v(S_{t+1}, \mathbf{w}) - \hat v(S_t, \mathbf{w}) $$
$$ \mathbf{w} \leftarrow \mathbf{w} + \alpha_{\mathbf{w}}\, \delta_t\, \nabla \hat v(S_t, \mathbf{w}), \qquad \boldsymbol\theta \leftarrow \boldsymbol\theta + \alpha_{\boldsymbol\theta}\, \delta_t\, \nabla \ln \pi(A_t \mid S_t, \boldsymbol\theta) $$

{{figure:actor-critic|The actor acts; the critic turns each step's outcome into a TD error that trains them both.}}

!!! algorithm "One-step actor-critic"
        Input: a policy π(a | s, θ) and a value v̂(s, w);  step sizes α_θ, α_w;  discount γ
        Loop for each episode:
            S ← the first state;  I ← 1
            Loop until S is terminal:
                A ← a draw from π(· | S, θ);  take A;  observe R and S′
                δ ← R + γ v̂(S′, w) − v̂(S, w)      (v̂(S′, w) = 0 if S′ is terminal)
                w ← w + α_w δ ∇_w v̂(S, w)
                θ ← θ + α_θ I δ ∇_θ ln π(A | S, θ)
                I ← γ I;  S ← S′

## Relation to clude

[[Professor Plum]]'s network has an actor and a critic in one body: its suspect, weapon and move heads are the actor, its value head the critic. It is trained on whole-game returns rather than one-step TD errors, so in the textbook's terms it is closer to REINFORCE with a baseline than to the one-step method above.

## See also

[[Policy gradient]] · [[Regularised Nash dynamics]] · [[Proximal policy optimisation]] · [[Temporal-difference learning]]

## References

{{references}}

[^book]: {{cite:sutton-barto|section 13.5}}

{{navbox:clude}}
