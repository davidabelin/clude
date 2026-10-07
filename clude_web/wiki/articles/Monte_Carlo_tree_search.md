---
title: Monte Carlo tree search
short: Planning by growing a search tree towards the moves whose simulated games go best
kind: stub
categories: Algorithms
redirects: MCTS, UCT
---
**Monte Carlo tree search** (MCTS) decides a move by simulation. From the current position it grows a tree of possible continuations, choosing which branch to explore by how well its simulated games have gone so far and how little it has been tried, plays each new branch out quickly to the end, and passes the result back up the tree. After many simulations it plays the move whose branch was explored most. It was central to the computer Go programs of the 2010s, including AlphaGo.[^book]

## The idea

Each simulation has four phases. *Selection* walks down the tree choosing, at each node, the child with the best upper confidence bound,

$$ \frac{W(c)}{N(c)} + c_{\text{explore}} \sqrt{\frac{\ln N(\text{parent})}{N(c)}} $$

where $W$ counts wins and $N$ visits ([[bandit action selection|the UCB rule]] applied at every node). *Expansion* adds a child; *simulation* plays to the end with a fast default policy; *backup* adds the result to every node on the path.

{{figure:mcts-phases|The four phases of one simulation in Monte Carlo tree search.}}

!!! algorithm "Monte Carlo tree search (UCT)"
        Input: the current position s_0;  a simulation budget
        tree ← a single node for s_0
        repeat until the budget is spent:
            node ← root
            while node is fully expanded and not terminal:
                node ← the child with the highest W/N + c √(ln N(node) / N(child))
            if node is not terminal: node ← a new child of node, for an untried move
            result ← play from node to the end with a fast random policy
            for each node on the path back to the root:
                N(node) ← N(node) + 1;  W(node) ← W(node) + result (for the player to move there)
        play the move to the root's most-visited child

## Relation to clude

Clue's hidden cards make plain MCTS awkward: a simulation needs a full deal, so it must sample one consistent with what is known, as [[exact posterior enumeration]]'s fallback once did. No clude character searches ahead this way; each decides from its current [[belief]].

## See also

[[Bandit action selection]] · [[Dyna-Q]] · [[Monte Carlo methods]] · [[DeepNash]]

## References

{{references}}

[^book]: {{cite:sutton-barto|sections 8.10, 8.11 and 16.6}}

{{navbox:clude}}
