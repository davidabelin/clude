---
title: Measurement record
short: Dated index of benchmarks, arenas, sweeps and memory experiments
categories: Measurement
redirects: Measurements, Recorded measurements, Results archive
---
The **measurement record** indexes the current experimental evidence for [[clude]]. Phase 14 froze 109 eligible version 3 games made after the [[landing rule]] change, split them by seed group, retrained every adaptive method and recalibrated all eight dials. Names belonging to human accounts were not published.[^phase14]

## How to read a result

A [[belief benchmark]] freezes evidence and scores probability estimates. An [[arena]] lets decisions change the next evidence and records playing outcomes. A [[dial sweeps|sweep]] changes one setting, while a [[twin comparison]] changes whether a model pilots a seat. Their denominators and questions differ.

The board, roster, seats, seeds, profiles, code, weights and starting memory belong with a result. A zero observed failure count is not a guaranteed zero rate. Paid rows also require the model, prompt revision, calls, tokens, fallbacks and cost.

## Frozen corpus and adaptive methods

The Phase 14 manifest contains source URI, record hash, run and index, seed group, split and Plum generation for each eligible record. `web/*` records describe [[PlumOG]], while `plum-policy-ladder-*` and `web-2/*` describe the current network. The training split contains 90 records and validation 19, with no seed group crossing the boundary.[^phase14]

[[Decision tree|Mustard]] was rebuilt from 50 fresh self-play games plus the post-landing training rows, at depth 6, minimum leaf 40 and smoothing 1. [[Markov chain|White]] retained prior mass 2 and rebuilt her per-opponent transition counts. [[Bandit ensemble|Green]] began again at Beta(1,1), selected step 4 and decay 1.05, then trained and validated on separate 200-game blocks. Their accepted method documents were staged without changing narrative logbooks.

[[Regularised Nash dynamics|Plum]] was trained three times from fresh initialisation on CUDA. Each network saw 150×512 games at the original regime and 150×512 at the lower-rate regime. A balanced four-network tournament covered every line-up containing Plum and gave each entrant 1,920 games. Run 3 led at 22.9% wins and was selected as the new network; its wrong accusations remain evidence for the model head rather than a rejection gate.[^plum]

## Current dial record

The pooled headless grids use 200 paired games per value, seed 142000 and an interleaved character/FloorBot roster. The isolated screens cover 29 applicable character–dial combinations at 96 games per value; curiosity is N/A for Plum.

{{table:arena.phase14|Current-setting control from the isolated Phase 14 screens. Percentages use each character's 40 seat-games.}}

The complete current grids, paired bootstrap intervals and direct behavioural footprints are on [[dial sweeps]]. None justified changing a headless preset.

The paid screen fixed the accepted code, weights and a read-only logbook snapshot. It used 4,748 valid calls with no fallback for $53.3074 at list price. The separate Plum leash confirmation cost $8.6005 and rejected 0.60 after it lost 12.5 paired win-rate points against 0.35. No paid dial changed.[^dials]

## Reproducibility and underlying games

The ignored local Phase 14 evidence holds the corpus manifest, baseline, candidate reports, sweep JSON, confidence intervals, token use, estimated and actual costs, and interrupted-run provenance. The maintenance command can snapshot and report without mutation; staging and live method promotion require explicit hashes, backups and `--apply`.

Signed-in readers can use [[the lobby]]'s development folders to inspect available games and open their [[replay|replays]]. A store need not contain every historical source run. A recorded event log remains evidence of that game even if current code would play it differently.

## Archive note

Ring-board, pre-landing and earlier Classic-board calibrations are superseded. Their detailed evidence, commands and limitations remain in the maintainer strategy glossary and git history, but they are no longer presented as the public calibration of the current characters.

## See also

[[Belief benchmark]] · [[Arena]] · [[Dial sweeps]] · [[Character training]] · [[Game records]]

## References

{{references}}

[^phase14]: {{cite:docs/phase14-plan.md|Implementation record}}
[^plum]: {{cite:docs/strategy-glossary.md|Phase 14 Run 3, the current Plum (2026-10-18)}}
[^dials]: {{cite:docs/strategy-glossary.md|Phase 14 dial recalibration (2026-10-18)}}

{{navbox:clude}}
