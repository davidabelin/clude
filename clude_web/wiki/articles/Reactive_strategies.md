---
title: Reactive strategies
short: Players who answer only the last round: copy, react, or counter the reactor
kind: stub
categories: Algorithms
redirects: Copy opponent, Reactionary strategy, Counter-reactionary strategy, Win-stay lose-shift
---
**Reactive strategies** choose each move from the last round alone. The rps project keeps three. The *copier* plays whatever the opponent played last. The *reactionary* keeps a move that just won and otherwise switches to the move that beats the opponent's last one, a version of the "win-stay, lose-shift" rule studied in game theory. The *counter-reactionary* assumes its opponent is a reactionary and plays to beat the switch it expects.[^rps]

## The idea

Each strategy is a function from the last round to the next move. If $a_{t-1}$ was my move, $b_{t-1}$ the opponent's and $\operatorname{beat}(m)$ the move that beats $m$:

$$ a_t^{\text{copy}} = b_{t-1}, \qquad a_t^{\text{react}} = \begin{cases} a_{t-1} & \text{if } a_{t-1} \text{ beat } b_{t-1} \\ \operatorname{beat}(b_{t-1}) & \text{otherwise} \end{cases} $$

They are easy to read, which is their purpose: they are the opponents a learning player should learn to exploit first.

!!! algorithm "The reactionary"
        Input: last round's moves (mine, theirs), or none in round one
        if there is no last round: play a random move
        else if my last move beat theirs: play my last move again
        else: play the move that beats their last move

!!! algorithm "The counter-reactionary"
        if there is no last round: play a random move
        else if my last move beat theirs:
            (they will now switch to beat it) play the move that beats that switch
        else: play the move that beats their last move

## Relation to clude

Clue players can be reactive too. [[Mrs. White]]'s [[Markov chain]] watches whether each opponent repeats the cards they named last time, a one-step memory of exactly this kind, and reads repetition as information about their hand.

## See also

[[Frequency counter]] · [[Transition-matrix predictor]] · [[Mixed-strategy Nash equilibrium]] · [[Ensemble voting]]

## References

{{references}}

[^rps]: {{cite:rps|`rps_agents/heuristic/basic.py`: `CopyOpponentAgent`, `ReactionaryAgent`, `CounterReactionaryAgent`}}

{{navbox:clude}}
