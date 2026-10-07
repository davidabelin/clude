---
title: Self-play
short: Generating game histories and private observations with automated players
categories: Measurement
redirects: Self play, Training games
---
**Self-play** in [[clude]] generates completed games between automated players, then extracts private observations for training and evaluation. The default regime uses [[floor player|floor players]]; the historical regime uses [[random bot|random bots]]. Both provide card evidence without requiring paid model calls.[^self]

For five of the six characters the term does not mean that they train by playing themselves; fixed bot policies generate the histories. [[Professor Plum]] is the exception since Phase 12: his network was trained by [[regularised Nash dynamics]] in games against copies of itself and against the other characters. Mustard uses labelled features from those histories, while the [[belief benchmark]] evaluates predictions on their observations.

## One generated game

The generator chooses a table size from its configured cycle and runs a seeded game. Once it finishes, the true envelope is known to the analysis code. At each requested checkpoint, the suggestion history is truncated and reconstructed separately for every viewer.[^self]

One game can consequently contribute several checkpoints times several seat views. They share a deal and much public evidence but differ in their private hand and shown cards. The target envelope accompanies each observation as a separate label, rather than being inserted into the player's input.

## Two regimes

| Regime | Policy | Typical evidence pattern |
|---|---|---|
| Floor player | Pursues unresolved cards and accuses on proof | Questions continue to narrow possibilities |
| Random bot | Chooses without card reasoning and sometimes guesses | Many redundant questions; early information can plateau |

In the documented historical comparison, floor-player games ended in about {{fact:floor.suggestions}} suggestions, while the earlier random regime ran {{fact:random.suggestions}}. Those ranges describe the recorded early regime and board, not guaranteed lengths for current Classic-board games.[^architecture]

Floor movement was made purposeful because uniform legal movement could repeatedly bring summoned tokens into a room whose card answered every question. Targeting unresolved rooms, then rooms nobody else can disprove with their room card, kept the evidence changing.

## Training and evaluation

Mustard's tree converts a viewer's checkpoint observation into features for each card and labels whether that card was in the finished envelope. The method learns smoothed leaf frequencies from these examples, then maps them into category probabilities. Training data reflects the generating policy.[^tree]

The benchmark instead supplies a full masked observation to each method. Its scores compare estimates under a common evidence stream. Agents did not select the questions that created those observations, so the test does not measure their complete playing policy.

Training and evaluation seeds and configuration should be recorded separately. A held-out set is one not used to fit the model being evaluated; merely changing a command's name does not establish separation. Method memory can add rows from stored games and therefore must also be controlled when judging a trained tree.

## Snapshot details

Checkpoint fractions count suggestions, not turns. The helper clears accusations, marks players active and uses the prefix length as the turn field. This prepares a card-evidence snapshot rather than reconstructing every token's historical position at that real turn.[^self]

The generator defaults to a floor regime and skips games with no suggestions. Fixed player counts can isolate a table size; cycling sizes broadens the observations. A seed reproduces this setup under the same implementation, but the bots use the engine's random stream in these self-play games, unlike private-stream arena fillers.

## Limits of generated evidence

A method trained or scored against one policy can change performance against another. White's reading of repeated questions, for example, assumes a behavioural relationship that uninformed random choices do not provide. Board changes alter travel and the rate at which informative questions arrive.

Self-play supplies plentiful, inspectable examples, but cannot alone certify human-table behaviour or model conversation. The [[arena]] and [[twin comparison]] add complete decision feedback, while new held-out observations test whether prediction findings survive another regime.


## See also

[[Floor player]] · [[Random bot]] · [[Decision tree]] · [[Belief benchmark]] · [[Method memory]]

## References

{{references}}

[^self]: {{cite:clude_training/self_play.py|`generate_snapshots`, `make_bots` and `truncate_state`}}
[^architecture]: {{cite:docs/architecture.md|Self-play regimes: `RandomBot` and `FloorBot` (Phase 5b)}}
[^tree]: {{cite:clude_agents/decision_tree.py|training rows and tree construction}}

{{navbox:clude}}
