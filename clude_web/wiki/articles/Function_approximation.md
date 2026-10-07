---
title: Function approximation
short: Replacing a table of values with a function that generalises: semi-gradient TD
kind: stub
categories: Algorithms
redirects: Value function approximation, Semi-gradient TD, Linear function approximation
---
**Function approximation** replaces a table of values, one entry per state, with a function of the state's features and a much smaller set of weights. It is the only option when states are too many to list, as in almost every real game, and it lets learning about one state carry over to similar ones. The price is that changing the weights for one state changes the estimates for others, which can make learning unstable.[^book]

## The idea

The value estimate is $\hat v(s, \mathbf{w})$, for example linear, $\hat v(s, \mathbf{w}) = \mathbf{w}^\top \mathbf{x}(s)$ for a feature vector $\mathbf{x}(s)$, or a [[multilayer perceptron]]. Learning moves the weights to reduce the error against a target $U_t$ by stochastic gradient descent:

$$ \mathbf{w} \leftarrow \mathbf{w} + \alpha \big[U_t - \hat v(S_t, \mathbf{w})\big] \nabla_{\mathbf{w}} \hat v(S_t, \mathbf{w}) $$

With a [[Monte Carlo methods|Monte Carlo]] target $U_t = G_t$ this is a true gradient method. With a [[temporal-difference learning|TD]] target $U_t = R_{t+1} + \gamma \hat v(S_{t+1}, \mathbf{w})$ the target itself depends on the weights, and ignoring that is why the method is called *semi-gradient*.[^book]

!!! algorithm "Semi-gradient TD(0)"
        Input: the policy π;  a differentiable v̂(s, w);  step size α;  discount γ
        Initialise w (for example to 0)
        Loop for each episode:
            S ← the first state
            Loop until S is terminal:
                take the action π gives;  observe R and S′
                target ← R  if S′ is terminal,  else R + γ v̂(S′, w)
                w ← w + α [target − v̂(S, w)] ∇_w v̂(S, w)
                S ← S′

## Relation to clude

[[Professor Plum]]'s network is a function approximator of this kind, with {{code:net.params}} weights reading {{code:net.state}} features of the [[deduction floor]]'s state; its value head is trained with a Monte Carlo target, and its policy with a [[policy gradient]]. [[Colonel Mustard]]'s [[decision tree]] is another, of a non-differentiable kind.

## See also

[[Multilayer perceptron]] · [[Deep Q-network]] · [[Temporal-difference learning]] · [[Policy gradient]]

## References

{{references}}

[^book]: {{cite:sutton-barto|sections 9.3 and 9.4}}

{{navbox:clude}}
