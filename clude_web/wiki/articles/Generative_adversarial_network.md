---
title: Generative adversarial network
short: Two networks in a contest: one forges examples, the other learns to spot forgeries
kind: stub
categories: Algorithms
redirects: GAN, GANs, DCGAN, Deep convolutional GAN
---
A **generative adversarial network** (GAN) trains two networks against each other. The *generator* turns random noise into made-up examples, images for instance; the *discriminator* is shown real examples and the generator's, and learns to tell them apart. Each improves by beating the other, and when training goes well the generator's examples become hard to tell from the real thing. The classwork archive's DCGAN paper showed that convolutional networks, with a few careful design rules, make this contest stable enough to learn useful image features.[^gan][^dcgan]

## The idea

The discriminator $D$ maximises, and the generator $G$ minimises, one shared objective:

$$ \min_G \max_D \; \mathbb{E}_{x \sim \text{data}}\big[\ln D(x)\big] + \mathbb{E}_{z \sim \text{noise}}\big[\ln\big(1 - D(G(z))\big)\big] $$

It is a two-player zero-sum game, and its ideal end is an equilibrium in which the generator's examples follow the data's distribution and the discriminator can only guess.[^gan]

{{figure:gan|A generative adversarial network: the generator forges, the discriminator judges, and each learns from the judgement.}}

!!! algorithm "Training a GAN"
        Input: real data;  a generator G(z; θ_G) and a discriminator D(x; θ_D)
        Loop for each training step:
            draw a batch of real examples x and of noise z
            update θ_D to raise  log D(x) + log(1 − D(G(z)))       (better judge)
            draw fresh noise z
            update θ_G to raise  log D(G(z))                         (better forger)

## Relation to clude

Nothing in clude generates images or examples. The connection is the game: like [[DeepNash]] and [[regularised Nash dynamics]], a GAN is trained towards an equilibrium between players rather than towards a fixed target.

## See also

[[Multilayer perceptron]] · [[Mixed-strategy Nash equilibrium]] · [[Classwork archive]]

## References

{{references}}

[^gan]: {{cite:goodfellow-2014}}
[^dcgan]: {{cite:radford-2016}}

{{navbox:clude}}
