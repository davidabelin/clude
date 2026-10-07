---
title: Transition-matrix predictor
short: Learn how an opponent's move follows their last one, and counter a draw from it
kind: stub
categories: Algorithms
redirects: Opponent transition matrix, Transition matrix predictor
---
A **transition-matrix predictor** models the opponent as a [[Markov chain]]: their next move depends only on their last one. It counts how often each move has followed each other move, turns each row of counts into probabilities, draws a prediction from the row for the opponent's last move, and plays to beat it.[^rps]

## The idea

With $N(i, j)$ the number of times the opponent played $j$ right after $i$, the estimated transition probability is

$$ \hat P(b_t = j \mid b_{t-1} = i) = \frac{N(i, j)}{\sum_{j'} N(i, j')} $$

Drawing from that row, rather than always taking its largest entry, keeps the predictor itself from becoming predictable.

!!! algorithm "Transition-matrix predictor"
        Initialise N(i, j) ← 0 for all moves i, j;  previous ← none
        Loop for each round:
            if previous is none or row N(previous, ·) is all zero: play a random move
            else:
                draw a prediction j with probability N(previous, j) / Σ_j' N(previous, j')
                play the move that beats j
            observe the opponent's move b
            if previous is not none: N(previous, b) ← N(previous, b) + 1
            previous ← b

## Relation to clude

[[Mrs. White]] fits a two-state chain of exactly this kind to each opponent, with states "repeats an earlier card" and "names a new one", and reads the fitted chain as evidence about their hand. The [[Markov chain]] article gives the mathematics.

## See also

[[Markov chain]] · [[Pattern memory]] · [[Reactive strategies]]

## References

{{references}}

[^rps]: {{cite:rps|`rps_agents/heuristic/opponent_transition.py`, `OpponentTransitionMatrixAgent`}}

{{navbox:clude}}
