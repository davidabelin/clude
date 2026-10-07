---
title: Mixed-strategy Nash equilibrium
short: Playing at random in exactly the proportions no opponent can exploit
kind: stub
categories: Algorithms
redirects: Mixed strategy, Nash equilibrium (mixed), Mixed Nash equilibrium
---
A **mixed-strategy Nash equilibrium** is a way of playing in which each player chooses at random, in fixed proportions, and no player can do better by changing their own proportions while the others keep theirs. In [[w:Rock paper scissors|rock, paper, scissors]] the equilibrium is to play each move a third of the time: against it, every strategy wins, draws and loses equally often in the long run, so there is nothing to exploit and nothing to gain.[^rps]

## The idea

A strategy that can be predicted can be beaten. Randomising removes the prediction, and the equilibrium proportions are the ones that leave every opponent move with the same expected payoff, so the opponent has no reason to prefer any of them. The equilibrium is safe, not clever: it never loses on average, and it never exploits an opponent's habits either.

For a two-player [[w:Zero-sum game|zero-sum]] game with payoff matrix $A$, the row player's equilibrium mixture $x$ solves

$$ \max_{x} \; \min_{j} \; \sum_i x_i A_{ij}, \qquad \sum_i x_i = 1,\; x_i \ge 0 $$

the best guaranteed payoff against the worst reply. For rock, paper, scissors it is $x = (\tfrac13, \tfrac13, \tfrac13)$, worth 0.[^nash]

!!! algorithm "The equilibrium player (rock, paper, scissors)"
        Input: nothing; it keeps no record of the opponent
        Loop for each round:
            draw u uniformly from [0, 1)
            if u < 1/3: play rock
            else if u < 2/3: play paper
            else: play scissors

## Relation to clude

The rps project keeps this player as its baseline: a measure of how much a learning player gains over a player who cannot be read.[^rps] Clue has no such simple equilibrium, because it is a race among three to six players with hidden cards, but the idea runs under [[regularised Nash dynamics]], the training rule behind [[Professor Plum]], whose regularisation is borrowed from methods that converge to equilibria in two-player zero-sum games.

## See also

[[Regularised Nash dynamics]] · [[DeepNash]] · [[Reactive strategies]] · [[Frequency counter]]

## References

{{references}}

[^rps]: {{cite:rps|`rps_agents/heuristic/constants.py`, `NashEquilibriumAgent`}}
[^nash]: {{cite:perolat-2022|the equilibrium the method approximates}}

{{navbox:clude}}
