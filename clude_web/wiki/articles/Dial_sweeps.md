---
title: Dial sweeps
short: Paired game runs varying one setting over a series of values
categories: Measurement
redirects: Dial sweep, Sweep, Leash sweep
---
**Dial sweeps** compare [[arena]] runs at several values of one [[personality dials|dial]], while keeping the seed schedule, roster and other settings fixed. They show whether a dial changes its intended behaviour and whether the change damages play. Pairing controls the deal, dice and line-up; later choices can still make the games diverge.[^runner]

Phase 14 recalibrated all eight dials after the [[landing rule]] change and after Run 3 became [[Professor Plum]]'s network. The headless sweeps used 200 games per value at seed 142000, tables of three to six and characters interleaved with [[deduction floor|FloorBot]] seats. Each applicable character then received a 96-game isolated screen at its preset and nearby values. Plum does not use curiosity.[^record]

## What the new runs establish

The current-rule runs confirmed the intended directions of the five headless dials. They retained every preset after the isolated screens, then retained the paid dials after screening and the one independent leash confirmation. This supports keeping the settings under the stated behavioural and outcome gates; it does not establish a unique optimum.

The tables pool counts over **seat-games**: every participating character has equal weight. Paired estimates instead average the participating characters **within each game**, subtract matching seed pairs, and bootstrap those game differences. Every game then has equal weight, including the smaller tables. Consequently the paired change can differ from subtraction of the pooled percentages: the threshold table's 38.6% to 0% is a pooled fall of 38.6 points, while the game-weighted paired estimate is -39.5 points.

The 95% intervals use 2,000 bootstrap resamples. They are pointwise intervals, without correction for the many values screened. Pairing reduces variation from deals; it does not make all observations independent or prove a long-run effect at other tables.[^paired]

## Headless dials

Won, Wrong and Never are percentages of character seat-games. First accusation averages only games in which that seat accused. Own cards shown and named are per seat-game; re-showing divides by eligible multi-card refutations, and mean turns uses whole games. Direct footprints matter more than small changes in wins: a bluff dial should move own-card naming, for example, whether or not bluffing happens to win a particular sample.

{{table:sweep.phase14.accuse_threshold|Phase 14 pooled accusation-threshold sweep. Higher values sharply reduced wrong accusations and made more seats wait through the end of the game.}}

The paired change in wrong accusations from 0.2 to 1 was -39.5 percentage points, with a 95% bootstrap interval from -44.4 to -34.7. The zero observed errors at 1 are a property of these 500 seat-games, not a universal rate.

{{table:sweep.phase14.bluff_rate|Phase 14 pooled bluff-rate sweep. Own cards named is the dial's direct footprint.}}

Own-card naming rose by 3.335 suggestions per seat-game between the endpoints, with a 95% interval from 2.912 to 3.770. Always bluffing also lost 17.75 paired win-rate points, so the direct effect is clear without making it a performance target.

{{table:sweep.phase14.curiosity|Phase 14 pooled curiosity sweep. Plum is excluded because curiosity is N/A for his network.}}

From zero to one, suggestions fell by 2.622 per seat-game, with a 95% interval from -2.942 to -2.303, and games lengthened by 10.36 turns. In this implementation higher curiosity is a stronger willingness to pursue a distant room; it can therefore reduce the number of suggestions completed before another player ends the game.

{{table:sweep.phase14.secrecy|Phase 14 pooled secrecy sweep. Re-shown uses only refutations for which the player held several matching cards.}}

Re-showing rose from 31.5% to 44.4%. The paired interval for distinct own cards exposed included zero, and the secondary outcomes did not support moving a preset.

{{table:sweep.phase14.temperature|Phase 14 pooled temperature sweep. Temperature samples among headless choices; it is not a model setting.}}

From zero to two, games lengthened by 19.47 turns, with a 95% interval from 16.99 to 22.09, while wins fell by 21.25 points. The current character temperatures remain deliberately low.

## Isolated screens and decision

The isolated screens moved one character at a time: unit dials at preset minus 0.2, preset and preset plus 0.2, and temperature at zero, current and twice current. This produced 8,352 games over 29 applicable character–dial combinations. The current-setting control was identical across each character's screens:

{{table:arena.phase14|Current-setting rows from the Phase 14 isolated screens. Each character has 40 seat-games in the shared 96-game seed block.}}

The intended footprints remained recognisable, but no proposed headless preset change cleared the personality and outcome gates. There was consequently no separate 192-game headless confirmation block. Retaining a preset is a measured decision, not a claim that its exact number is uniquely optimal.[^record]

## Paid dials

Paid screens fixed `claude-opus-5`, the accepted code and weights, and a read-only logbook snapshot. All accepted rows had zero fallbacks. [[Leash]] was screened separately for every character, [[table talk|chattiness]] at five values over common opportunities, and [[memory dial|memory depth]] at five values without debrief writes.

{{table:paid.phase14.chattiness|Phase 14 chattiness screen. On-turn speech is not gated by this dial; calls and spoken lines here are off-turn reactions.}}

The 183 opportunities are fixed suggestion/accusation trigger events, replayed from the same eight saved games. Several seats and reply chains can respond to one trigger, so 210 lines at 0.5 is not a response probability above 100%. The line count increased and began to flatten above 0.5, with the simulation limited to two replies per turn and forty per game. The current 0.5 setting was retained; this replay screen does not test a win-rate effect or establish a natural conversational ceiling.

{{table:paid.phase14.memory|Phase 14 memory-depth screen against one immutable logbook snapshot. Each row contains eight four-seat games.}}

Each game contributes one win across the four changing model seats, so the eight wins per row cannot distinguish depths. The screen found no basis to advance a candidate, but eight games and one snapshot cannot establish equal playing strength or measure long-term social continuity. Deeper memory could cost more; the present head-only profile default and full-depth new-lobby convention remain.

The leash screen shortlisted Plum at 0.60, then a separate 24-pair confirmation rejected it:

{{table:paid.phase14.plum_leash_confirm|Plum leash confirmation on new seeds. The candidate lost 12.5 paired win-rate points and stayed within the wrong-accusation and game-length guardrails.}}

The candidate failed the five-point win guardrail. No paid dial or preset changed. Valid screening and confirmation cost $61.9079 at list price; one memory row compromised by provider credit exhaustion was discarded rather than counted, and the valid earlier legs were not rerun.[^record]

## Archive note

Earlier ring-board and pre-landing-rule sweeps informed older presets. Their detailed tables and calibration claims are superseded here; the dated evidence remains in the maintainer strategy glossary and git history.

## See also

[[Personality dials]] · [[Arena]] · [[Leash]] · [[Memory dial]] · [[Measurement record]]

## References

{{references}}

[^paired]: {{cite:clude_training/sweep.py|`_paired_game_differences`, `_bootstrap_interval` and `SweepResult.paired_deltas`}}
[^runner]: {{cite:clude_training/sweep.py|`sweep_dial`, `pooled_stats` and `SweepResult.monotone`}}
[^record]: {{cite:docs/strategy-glossary.md|Phase 14 dial recalibration (2026-10-18)}}

{{navbox:clude}}
