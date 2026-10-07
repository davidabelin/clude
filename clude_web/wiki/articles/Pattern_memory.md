---
title: Pattern memory
short: Remember short runs of play and predict what followed them last time
kind: stub
categories: Algorithms
redirects: Memory patterns, N-gram predictor, Pattern matching (rps)
---
**Pattern memory** predicts an opponent from the recent history of play. It remembers short windows of the mixed sequence of both players' moves and, for each window, how the opponent moved next. When a remembered window recurs, it predicts that the opponent will do what they most often did after it before, and plays to beat that. It is an [[w:N-gram|n-gram]] model of the game.[^rps]

## The idea

With a window $w$ of the last $k$ moves (both players', interleaved) and counts $N(w, b)$ of the opponent's next move $b$ after each past occurrence of $w$:

$$ \hat b = \arg\max_b N(w, b), \qquad a = \operatorname{beat}(\hat b) $$

A longer window is more specific and needs more history before it recurs; a shorter one recurs sooner and says less. The rps player uses six moves.

!!! algorithm "Pattern memory"
        Parameters: window length k
        Initialise an empty table of windows, each with counts N(·) of the next move
        Loop for each round:
            w ← the last k moves of the game, both players'
            if w is in the table: play the move that beats argmax_b N(w, b)
            else: play a random move
            observe the opponent's move b
            add w to the table if new;  N(w, b) ← N(w, b) + 1

## Relation to clude

[[Mrs. White]]'s [[Markov chain]] is the clude method closest in spirit: it reads sequences of suggestions rather than single ones. Pattern memory looks further back and keeps no probabilities, only counts and a best guess.

## See also

[[Transition-matrix predictor]] · [[Markov chain]] · [[Frequency counter]]

## References

{{references}}

[^rps]: {{cite:rps|`rps_agents/heuristic/memory_patterns.py`, `MemoryPatternAgent`}}

{{navbox:clude}}
