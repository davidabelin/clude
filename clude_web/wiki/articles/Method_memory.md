---
title: Method memory
short: Numerical state learned across games by Mustard, White and Green
categories: Memory
redirects: Numerical memory
---
**Method memory** is numerical information retained across games by three [[clude]] methods. Mustard accumulates training rows, White retains opponent-specific transition counts, and Green retains the parameters used to choose among his five arms. It can be loaded and updated for either headless or model-piloted seats when remembering is enabled.[^memory]

This differs from a narrative [[logbook]]. No language model is needed to use method memory, and the [[memory dial]] does not control it. Scarlett, Plum and Peacock recompute their methods from the current observation without persistent numerical method memory.

## Three different forms

| Character | Retained state | Effect in a later game |
|---|---|---|
| [[Colonel Mustard]] | Training rows from stored game views | Additional data when growing the decision tree |
| [[Mrs. White]] | Repeat/new transition counts by opponent identity | A shaped prior for that opponent's chain |
| [[Mr. Green]] | Beta parameters over the five arms | Changed arm draws at the next belief call |

The shared term 'memory' does not mean these states have the same statistical interpretation. Each alters a different part of its method.[^memory]

## Mustard's training rows

Stored records can generate labelled card-feature rows from every seat's masked view at training checkpoints. These rows are appended to Mustard's self-play base before a tree is grown. The label uses the finished game's envelope, while the features use the evidence available to that seat at the checkpoint.[^code]

Mustard can learn from eligible stored games he did not play in. Contributions are keyed by game id, so updating from the same game twice does not add a second copy. A more varied history can change which tests and leaf frequencies the tree learns, but extra data can also shift it away from the evaluation policy.

In the historical ring-era memory experiment, {{fact:mustard.memory.games}} stored ladder games supplied {{fact:mustard.memory.rows}} rows. On {{fact:mustard.memory.held_out}} held-out floor-player games, mid-game log-loss improved from {{fact:mustard.memory.mid.before}} to {{fact:mustard.memory.mid.after}}, while final-checkpoint loss worsened from {{fact:mustard.memory.end.before}} to {{fact:mustard.memory.end.after}}. More training history did not improve every checkpoint.[^measured]

## White's opponent priors

White pools repeat/new transition counts under an opponent's roster identity. At a later table, those frequencies shape the starting transition prior for that identity, at the same total pseudo-count mass as the default prior. A large historical count therefore does not enter the live chain as thousands of extra observations.[^white]

An opponent who repeatedly changed questions in earlier games can start with a different prior shape from one who often repeated cards. Current-game transitions still update that chain. The interpretation connecting repeated questions to hidden cards remains White's heuristic; remembering it does not turn it into a logical rule.

Like Mustard, White can use games she did not occupy because records include the relevant histories. Version-filtered rebuilding prevents old ring-board behaviour from automatically re-entering a Classic-board reset.

## Green's arm state

Green evaluates all five methods on his own observation, draws from their Beta records and copies one arm's prediction. When the outcome is revealed, he ranks their last predictions by [[log-loss]] and updates every arm with a fractional rank reward and decay.[^green]

Those live predictions are not all preserved in the ordinary game record. His arm state can therefore be saved and restored but not rebuilt from records in the same way as Mustard's rows or White's counts. His parameters are decayed preference records, not calibrated probabilities that a method is best.

## Comparisons and limitations

Reproducibility becomes a matter of seed **and memory state**. A fair fixed-state comparison loads the same memories read-only on each leg. A run that writes memory after every game instead measures an evolving system, and later games may depend on the earlier order.

Empty memory preserves the prior behaviour covered by recorded tests. Populated memory can change decisions and outcomes even if every dial remains fixed. [[Determinism and seeds]] and [[twin comparison]] describe the controls needed to interpret those changes.


## See also

[[Logbook]] · [[Decision tree]] · [[Markov chain]] · [[Bandit ensemble]] · [[Self-play]]

## References

{{references}}

[^memory]: {{cite:docs/logbooks.md|Tier 1: method memory}}
[^code]: {{cite:clude_training/memory.py|record contributions and rebuild}}
[^measured]: {{cite:docs/strategy-glossary.md|Phase 7: memory (2026-09-14)}}
[^white]: {{cite:clude_agents/markov.py|`prior_cells`}}
[^green]: {{cite:clude_agents/bandit.py|`observe`, `state_dict` and `load_state`}}

{{navbox:clude}}
