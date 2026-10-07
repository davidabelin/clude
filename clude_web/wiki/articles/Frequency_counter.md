---
title: Frequency counter
short: Count the opponent's moves and beat the most common one
kind: stub
categories: Algorithms
redirects: Statistical strategy, Mode counter, Empirical frequency
---
A **frequency counter** keeps a tally of every move the opponent has made and plays to beat the one they make most often. It is the simplest statistical player: its whole model of the opponent is the [[w:Empirical distribution function|empirical distribution]] of their moves, and its prediction is that distribution's most likely value.[^rps]

## The idea

After $n$ rounds with counts $N(m)$ for each move $m$, the predicted next move is

$$ \hat b = \arg\max_m \frac{N(m)}{n}, \qquad a = \operatorname{beat}(\hat b) $$

It exploits any opponent with a lasting bias, and it is exploited by any opponent who notices it: a player who leans on rock for a while, then switches, collects the counter's predictable answers.

!!! algorithm "Frequency counter"
        Initialise N(m) ← 0 for every move m
        Loop for each round:
            if every N(m) = 0: play a random move
            else: play the move that beats argmax_m N(m)
            observe the opponent's move b;  N(b) ← N(b) + 1

## Relation to clude

Counting is where several of clude's methods start. [[Miss Scarlett]]'s [[naive Bayes]] tallies how often each card has been named and answered, and [[Colonel Mustard]]'s [[decision tree]] reads such counts as features. Both, unlike the counter, turn counts into probabilities rather than a single guess.

## See also

[[Reactive strategies]] · [[Transition-matrix predictor]] · [[Pattern memory]] · [[Probability]]

## References

{{references}}

[^rps]: {{cite:rps|`rps_agents/heuristic/basic.py`, `StatisticalAgent`}}

{{navbox:clude}}
