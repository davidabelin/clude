---
title: Multilayer perceptron
short: Layers of weighted sums and simple bends, fitted by gradient descent
kind: stub
categories: Algorithms
redirects: MLP, Feedforward neural network, Neural network
---
A **multilayer perceptron** (MLP) is the plainest [[w:Artificial neural network|neural network]]: a stack of layers, each taking a weighted sum of the previous layer's numbers and bending it with a simple non-linear function. Fitted by [[w:Gradient descent|gradient descent]] on examples, it can approximate a very wide range of functions. The rps project can train one, with hidden layers of 64 and 32 units by default, to predict a person's next move from their last five.[^rps] [[Professor Plum]]'s network is an MLP too.

## The idea

Each layer computes $h_{\ell} = \sigma(W_{\ell} h_{\ell-1} + b_{\ell})$, with $\sigma$ a bend such as the rectifier $\max(0, z)$; the last layer gives scores, which a [[softmax and temperature|softmax]] turns into probabilities. Training lowers a loss $L$, such as [[log-loss]], by moving every weight a little against its gradient,

$$ W \leftarrow W - \alpha \, \nabla_W L $$

with the gradients computed layer by layer from the output back, which is [[w:Backpropagation|backpropagation]].[^book]

!!! algorithm "Training a multilayer perceptron"
        Input: examples (x, y); layer sizes; step size α; epochs E
        initialise every W_ℓ with small random numbers, every b_ℓ with zeros
        Loop for each epoch:
            Loop for each batch of examples:
                forward:   h_0 ← x;  h_ℓ ← σ(W_ℓ h_(ℓ−1) + b_ℓ);  p ← softmax(last layer)
                loss:      L ← − mean log p(y)
                backward:  compute ∇L for every W_ℓ, b_ℓ, last layer first
                step:      W_ℓ ← W_ℓ − α ∇_W L;  b_ℓ ← b_ℓ − α ∇_b L

## Relation to clude

[[Professor Plum]] plays by an MLP with a trunk of two layers of {{code:net.hidden}} units and five small heads, trained not on labelled examples alone but by [[regularised Nash dynamics]]; its belief head is fitted to the true envelope by exactly the loss above.

## See also

[[Regularised Nash dynamics]] · [[Deep Q-network]] · [[Function approximation]] · [[Softmax and temperature]]

## References

{{references}}

[^rps]: {{cite:rps|`rps_training/supervised.py`, `TrainConfig` and `train_model`}}
[^book]: {{cite:sutton-barto|section 9.7, "Nonlinear Function Approximation: Artificial Neural Networks"}}

{{navbox:clude}}
