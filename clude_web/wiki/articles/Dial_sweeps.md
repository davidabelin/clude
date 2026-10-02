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



## All five dials on the two boards

The recorded ring sweeps and the Classic-grid sweeps each used 48 paired games per value, seed 7100 and an interleaved character–floor roster, pooled into 120 character seat-games. The ring sweeps preceded the holder-order fix and the seat-locking change; the grid sweeps were recorded on 15 September 2026 with seat-locked characters. The same dial names and seed do not make these different-board runs a paired board comparison.[^record][^grid]

The following tables preserve the five sweeps rather than show only their selected presets. Won and Wrong are percentages of character seat-games; First accusation averages only games with an accusation, and Never accused supplies the missing part of that picture. Own cards shown counts distinct held cards exposed, Own cards named counts suggestions naming any held card, and Re-shown uses only refutations with several matching cards. Mean turns describes whole games, not turns taken by one character.

The ring bluff-rate table is above. Its other four sweeps were:

{{table:sweep.ring.accuse_threshold|Historical ring-board accuse threshold sweep; 48 games per value, pooled character results.}}

{{table:sweep.ring.curiosity|Historical ring-board curiosity sweep; 48 games per value, pooled character results.}}

{{table:sweep.ring.secrecy|Historical ring-board secrecy sweep; 48 games per value, pooled character results.}}

{{table:sweep.ring.temperature|Historical ring-board temperature sweep; 48 games per value, pooled character results.}}

The Classic-board results were:

{{table:sweep.grid.accuse_threshold|Classic-board accuse threshold sweep, 15 September 2026; 48 games per value, pooled character results.}}

{{table:sweep.grid.bluff_rate|Classic-board bluff rate sweep, 15 September 2026; 48 games per value, pooled character results.}}

{{table:sweep.grid.curiosity|Classic-board curiosity sweep, 15 September 2026; 48 games per value, pooled character results.}}

{{table:sweep.grid.secrecy|Classic-board secrecy sweep, 15 September 2026; 48 games per value, pooled character results.}}

{{table:sweep.grid.temperature|Classic-board temperature sweep, 15 September 2026; 48 games per value, pooled character results.}}

High temperature and always-bluffing settings had lower recorded win rates on both boards. Higher secrecy increased re-showing without a consistent win-rate improvement in these samples. Curiosity's low-end ranking differed between boards: the ring sample favoured 0.5 over 0, while the grid sample favoured 0 over 0.5. Those small differences do not establish a precise optimum. The grid's longer routes gave a practical reason to investigate lower curiosity for characters that pursued distant rooms.

## The pooled model leash sweep

The ring-board sweep of 13 September 2026 changed all model-piloted characters together at three-seat tables, with eight paired games per value, seed 7007 and 24 seat-games per value. Pooled win rate was uninformative: when all seats are swept and each game has one winner, it is one third by construction.[^leash]

{{table:leash.pooled|Historical pooled leash sweep. Reported +/- is the recorded plug-in binomial standard deviation in percentage points, not a confidence interval. Departure rate divides by accepted model choices.}}

The departure percentage did not rise throughout, partly motivating a different denominator in the later ladders: departures per eligible decision, alongside raw counts. More opportunities to accept a model choice can lower the percentage of accepted choices that depart from the top score. That explanation is a hypothesis about this record; it did not save the machine-readable counts needed to settle it.

The later [[leash|per-character ladders]] isolate Mustard and Plum against fixed headless opponents. They answer a different question from this all-model sweep, and the [[measurement record]] links their source records and the subsequent memory comparisons.

## See also

[[Personality dials]] · [[Arena]] · [[Twin comparison]] · [[Memory dial]] · [[Measurement record]]

## References

{{references}}

[^sweep]: {{cite:clude_training/sweep.py|`sweep_dial`, `pooled_stats` and `SweepResult.monotone`}}
[^record]: {{cite:docs/strategy-glossary.md|Dial sweeps}}
[^grid]: {{cite:docs/strategy-glossary.md|Dial sweeps on the grid (Stage 1c)}}
[^leash]: {{cite:docs/strategy-glossary.md|Leash sweep (2026-09-13)}}
[^memory]: {{cite:docs/logbooks.md|Running it}}

{{navbox:clude}}
