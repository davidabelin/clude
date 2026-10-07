---
title: Ensemble voting
short: Several predictors decide together, by weighted vote or by taking turns
kind: stub
categories: Algorithms
redirects: Polling agent, Rotating ensemble, Voting ensemble
---
**Ensemble voting** combines several players into one. The rps project has two forms. The *polling* player asks seven simpler players for their move each round and plays the one with most votes, its decision tree's vote counting five times over. The *rotating* player hands control to one of the seven at a time and changes hands at random intervals of a prime number of rounds, so that an opponent cannot learn the schedule.[^rps]

## The idea

With voters $v_1, \dots, v_K$, weights $w_k$ and each voter's proposed move $a^{(k)}$, the polling player plays

$$ a = \arg\max_m \sum_{k=1}^{K} w_k \,[\, a^{(k)} = m \,] $$

Every voter keeps learning from every round, whether or not its vote won, so each is ready when it is consulted.

!!! algorithm "Polling"
        Input: voters v_1 … v_K with weights w_1 … w_K
        Loop for each round:
            for each move m: score(m) ← Σ_k w_k · [v_k proposes m]
            play argmax_m score(m)
            pass the round's outcome to every voter

!!! algorithm "Rotation"
        Input: voters; a list of prime periods
        choose a voter and a period at random
        Loop for each round t:
            if t is a multiple of the period: choose a new voter and a new period at random
            play the chosen voter's move;  pass the outcome to every voter

## Relation to clude

[[Mr. Green]]'s [[bandit ensemble]] is clude's ensemble. It neither votes nor rotates on a schedule: it keeps a record of how well each of the other five methods has predicted envelopes and picks one by [[w:Thompson sampling|Thompson sampling]], so the choice follows the evidence. The rps project has a bandit ensemble too, beside these two.

## See also

[[Bandit ensemble]] · [[Bandit action selection]] · [[Reactive strategies]]

## References

{{references}}

[^rps]: {{cite:rps|`rps_agents/heuristic/ensemble.py`: `PollingAgent`, `RotatingEnsembleAgent`}}

{{navbox:clude}}
