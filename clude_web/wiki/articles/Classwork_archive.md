---
title: Classwork archive
short: Learning references kept with the project and their relevance to clude
categories: Classwork
redirects: Classwork, Reference archive
---
The **classwork archive** is the collection of learning references supplied with [[clude]] in a Google Drive folder. It includes Sutton and Barto's reinforcement-learning textbook, a revision sheet, papers on deep reinforcement learning and imperfect-information games, and wider machine-learning and network references. These are background sources; their presence does not mean that clude implements their algorithms.[^archive]

Wikiclude begins the archive with [[reinforcement learning]], [[Markov decision process|Markov decision processes]], [[Q-learning]], [[deep Q-network|deep Q-networks]] and [[DeepNash]]. [[Character training]] describes the learning actually supported by the current project.

## Textbook and revision aid

`RL text.pdf` identifies itself as Richard S. Sutton and Andrew G. Barto's *Reinforcement Learning: An Introduction*, second edition, 2018. Its early chapters introduce rewards, policies and value functions; Chapter 3 develops finite Markov decision processes, and Chapter 6 explains temporal-difference learning and Q-learning. The archive copy contains typesetting placeholders, so citations identify chapters and sections rather than assume that PDF page positions match printed pagination.[^book]

`RL cheatsheet.pdf` is a compact revision aid; the folder also contains a file named `cheatsheet.pdf`. The textbook supplies the fuller definitions and assumptions. The sheets are not evidence that a method has been tested in Clue.[^sheet]

## Deep reinforcement learning

The DQN paper, `DeepQNetworks_Nature.pdf`, describes learning action values from game experience with a neural network. It introduces experience replay and a separate target network in an Atari evaluation.[^dqn]

`dueling DQN.pdf` separates a network's state-value and action-advantage streams. `prioity replay.pdf`, whose filename has that spelling, studies sampling stored transitions by their learning priority rather than uniformly. [[Deep Q-network]] explains both extensions and distinguishes experience replay used for learning from clude's finished-game replay screen.[^duel][^priority]

## Imperfect information and environment design

`DeepNash.pdf` studies Stratego, where opponents' piece identities are hidden. Its self-play method is a useful comparison for reasoning and strategic uncertainty, though its two-player zero-sum setting differs from multiplayer Clue. [[DeepNash]] explains the distinction.[^nash]

`RL walk learning.pdf`, *Emergence of Locomotion Behaviours in Rich Environments*, studies simulated bodies learning locomotion across varied terrain with a reward based on forward progress. It illustrates how the environment helps shape learned behaviour. For clude, the relevant question is how training deals, opponents and rewards shape a player; the paper provides no Clue evaluation.[^walk]

## Wider references

`dcgan_paper.pdf` is Radford, Metz and Chintala's paper on deep convolutional generative adversarial networks. It concerns learned image representations, rather than hidden-card inference or a game-playing reward policy.[^gan]

`osmnx.pdf` is Geoff Boeing's paper on constructing and analysing street networks from OpenStreetMap. Its graph and route concepts relate broadly to movement, but clude's [[Classic board]] is its own fixed graph and does not use OSMnx.[^osmnx]

## Access and scope

References link to the supplied Drive copies and public originals where available. Drive copies may require permission, and a publisher or author site may be temporarily unavailable. Wikiclude supplies its own explanations without requiring readers to open the archive first.

The archive contains ancillary files as well as papers. This guide covers the technical sources relevant to the project, with the reference PDFs checked on 2 October 2026.


## See also

[[Reinforcement learning]] · [[Deep Q-network]] · [[DeepNash]] · [[Character training]]

## References

{{references}}

[^archive]: {{cite:drive-classwork}}
[^book]: {{cite:sutton-barto|Chapters 1, 3 and 6}}
[^sheet]: {{cite:drive-cheatsheet}}
[^dqn]: {{cite:mnih-2015}}
[^duel]: {{cite:wang-2016}}
[^priority]: {{cite:schaul-2016}}
[^nash]: {{cite:perolat-2022}}
[^walk]: {{cite:heess-2017}}
[^gan]: {{cite:radford-2016}}
[^osmnx]: {{cite:boeing-2017}}

{{navbox:clude}}
