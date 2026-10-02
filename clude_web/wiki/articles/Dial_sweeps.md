---
title: Dial sweeps
short: Paired game runs varying one setting over a series of values
categories: Measurement
redirects: Dial sweep, Sweep, Leash sweep
---
**Dial sweeps** compare [[arena]] runs at several values of one [[personality dials|dial]], holding the seed schedule and other configured settings fixed. They test whether the dial changes its intended behaviour and how that affects outcomes. A sweep can vary all selected characters together or isolate one character.[^sweep]

The method supports comparisons rather than proving a universal optimum. Changing several players' same dial still changes their interactions, and a small set of paired deals may favour one value by chance. Remembered state and live model replies require additional controls.

## A behavioural question

For [[bluff rate]], the intended effect is more suggestions naming held cards. The historical ring-board sweep set the dial on all six characters and measured them against interleaved floor-player seats. It used 48 paired games per value, pooled into 120 character seat-games.[^record]

{{table:sweep.bluff|Historical ring-board sweep over bluff rate. The characters were changed together; their pooled own-card naming rose across these values.}}

The naming count rose while win rate did not rise throughout. That separates the implemented behaviour from its tactical value. The non-zero naming count at dial zero came from held room cards, since the room is fixed by position.

## How a sweep is run

The runner builds an arena for each chosen dial value, using the same base seed, roster, player counts and other settings. It pools selected characters' statistics for the sweep row and retains the underlying per-character results. Non-selected opponents keep their configured profiles.[^sweep]

With characters and private filler streams, the same seeds produce the same deals and die sequence. Different moves and suggestions still lead to different evidence. Pairing reduces variation in setup; it does not hold the entire course of play constant.

## Monotonicity

The implementation checks whether a metric is non-decreasing, non-increasing, flat or mixed across values, allowing a small numerical tolerance. A sequence that moves consistently in one direction passes the intended directional check. Missing values make that verdict unavailable.[^sweep]

For example, lower thresholds should tend to make accusations available earlier and increase risk, while higher secrecy should favour previously exposed cards when choices exist. Win rate need not move monotonically: an intermediate risk setting can balance early mistakes against waiting too long.

The monotonicity check is descriptive, not a statistical significance test or causal proof. A monotone sequence in a short sample can happen by chance, and a genuine effect can look non-monotone in noisy observations.

## Pooled and isolated effects

Moving the dial on all characters asks about a table-wide change. Moving it only on Plum asks how Plum fares against otherwise fixed profiles. Their conclusions can differ because opponents determine the evidence and the race to accuse.

A pooled result can hide opposing per-character responses. It also gives more weight to identities with more seat-games. The recorded per-character results should be consulted before adopting a preset from the pooled row.

## Memory and model controls

A [[memory dial|memory-depth sweep]] uses a fixed logbook read-only so later values do not receive a more developed history. Method memory likewise needs a common starting state. Otherwise the dial change is confounded with additional training or experience.[^memory]

A [[leash]] sweep opens different model menus and may make different numbers of calls. Live replies are not guaranteed identical, so it measures that configured model-piloted behaviour rather than a fully deterministic numerical intervention. Audit columns help distinguish increased opportunity from actual departures.

## Recorded history and limits

Ring-era sweeps informed the first presets; grid-era sweeps informed later changes. The early ring sweep preceded a fix to Plum's holder ordering: within-process pairing was valid, but those absolute values do not exactly reproduce on the fixed code.[^record]

The current [[landing rule]] also postdates the major grid tuning tables. New sweeps should name their board and implementation rather than inherit historical conclusions automatically. A confirmation arena on separate or clearly identified seeds is needed to test whether a promising setting generalises.


## See also

[[Personality dials]] · [[Arena]] · [[Twin comparison]] · [[Memory dial]]

## References

{{references}}

[^sweep]: {{cite:clude_training/sweep.py|`sweep_dial`, `pooled_stats` and `SweepResult.monotone`}}
[^record]: {{cite:docs/strategy-glossary.md|Dial sweeps}}
[^memory]: {{cite:docs/logbooks.md|Running it}}

{{navbox:clude}}
