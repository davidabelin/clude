---
title: Character training
short: What clude learns, what is tuned and how changes are evaluated
categories: The app
redirects: Training
---
**Character training** in [[clude]] includes several distinct processes: supervised fitting of Mustard's tree, accumulated numerical [[method memory]], narrative [[logbook|logbooks]] and selection of [[personality dials|dial presets]]. These processes use different evidence and improve different parts of a player. Since Phase 12 one of them is a trained policy: [[Professor Plum]]'s network, trained by [[regularised Nash dynamics]] in self-play; the other five do not train a [[deep Q-network]] or any reinforcement-learning policy.[^methods][^memory]

## Numerical learning

[[Colonel Mustard]] learns a [[decision tree]] from card-level examples extracted from completed games. Features describe the evidence available to a seat; the revealed outcome supplies the training label. The tree predicts card probabilities, after which the floor masks impossible cards and the common action scorer chooses play. It is supervised learning of an estimator, rather than learning an action's long-term reward directly.

[[Mrs. White]] keeps per-opponent counts for her model of [[Markov chain|suggestion sequences]]. A person's account identity lets those counts follow the opponent across suspect tokens. [[Mr. Green]] updates Beta-distributed arm feedback from the revealed outcome and the methods' rankings. His [[bandit ensemble]] combines the existing estimators; it is not a table-wide learned Q-function.

The other supported method implementations recompute their estimates from evidence rather than fit a persistent policy after every game. Ordinary play can still change a method's within-game state. Persistent memory and a fresh reading of the current observation should not be conflated.

## Narrative experience and model-piloted play

A remembering LLM seat can read a logbook before playing and write a [[debrief]] after the finish. The [[memory dial]] controls read-back depth. This gives the model a textual account of prior encounters and lessons; it does not update the language model's weights.

Headless and LLM seats share the numerical character. Headless play selects from numerical scores; the [[LLM wrapper]] lets the model choose within the [[leash]]. Training or tuning one therefore needs to say which layer changed. More narrative detail cannot be assumed to improve the underlying probability estimates.

## Tuning and evaluation

[[Dial sweeps]] test settings across paired games, including the dial's intended footprint: bluff rate should change held-card naming, for example. [[Arena|Arenas]] measure wins, accusations, disclosure and game length. The [[belief benchmark]] separately measures the quality and cost of estimates on common saved evidence.

A fair comparison records the starting memory, board, roster, seed schedule and code version. If one variant learns during the run while another reads fixed memory, their difference includes that learning. A confirmation run on separate deals helps distinguish a useful change from tuning to a small sample.

## Recorded work and the next phase

The [[measurement record]] indexes ring-board and Classic-board experiments, including numerical training, leash ladders and Plum's logbook comparison. Many key preset measurements predate the current landing rule. They are starting evidence for the next phase, not fresh acceptance tests of today's players.

Phase 12 trained Plum's network: two runs of {{fact:policy.run.games}} games each, measured on the same belief benchmark and arenas as the other characters. Its protocol and results are in [[regularised Nash dynamics]]. The [[classwork archive]] supplies wider learning concepts for that work without implying that its algorithms have already been implemented.[^wiki]


## See also

[[Method memory]] · [[Decision tree]] · [[Dial sweeps]] · [[Classwork archive]]

## References

{{references}}

[^methods]: {{cite:docs/strategy-glossary.md}}
[^memory]: {{cite:docs/logbooks.md}}
[^wiki]: {{cite:docs/wikiclude-plan.md}}

{{navbox:clude}}
