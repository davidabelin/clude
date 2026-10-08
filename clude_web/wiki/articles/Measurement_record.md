---
title: Measurement record
short: Dated index of benchmarks, arenas, sweeps and memory experiments
categories: Measurement
redirects: Measurements, Recorded measurements, Results archive
---
The **measurement record** indexes the experiments documented for [[clude]]: [[belief benchmark|belief benchmarks]], [[arena|arenas]], [[dial sweeps]], [[twin comparison|model comparisons]] and memory studies. It connects each result to its board, configuration and source record. It is an index of recorded evidence through 2 October 2026, not a new evaluation of the current characters.[^glossary]

Many main tuning results date from September 2026 and predate the [[landing rule]]. Later implementation and interface changes do not refresh those measurements automatically. The next [[character training|character-training phase]] is planned after Wikiclude's completion and review; its measurements remain to be made.

## How to read a result

A belief benchmark freezes evidence and asks how well a method estimates the answer. An arena lets choices change the next evidence and records playing outcomes. A sweep changes a setting, while a twin comparison changes whether a model pilots selected characters. Their scores have different meanings and denominators.

For any comparison, the board, roster, seat participation, seeds, profiles, implementation and starting memory belong with the result. Model, leash and memory depth also matter for LLM seats. A reported percentage with no errors in a short sample does not prove a zero long-run error rate. Runtime belongs to its recorded machine and workload; fallback frequency counts benchmark calls, not a fraction of the game spent sampling.

## Ring-board methods and presets

The early phases used a simplified ring. The historical Phase 4 benchmark used RandomBot evidence; the Phase 5 benchmark replaced it with FloorBot evidence. The [[belief benchmark]] article explains their checkpoint and scoring conventions. Neither is a current Classic-board benchmark.[^phase4][^ringbench]

Phase 5 recorded the first arena, the five-dial sweeps and the tuned-preset arena. [[Arena]] defines the outcome metrics; [[Dial sweeps]] now presents all five ring and grid sweep tables. The first ring sweeps preceded Plum's holder-order fix, so their within-process pairing was valid but current-code reruns need not reproduce absolute values.[^ringfirst][^ringsweep][^ringtuned]

The source sections retain the untuned profiles, tuned profiles, command lines and observations, rather than only the winning rows. Ring-era characters also rotated through tokens; seat locking began on 14 September. This change limits comparison with subsequent runs even before considering board geometry.[^ringpresets][^memory]

## Ring-board model and memory experiments

On 13 September the all-character twin comparison tested headless and model-piloted play on common seed schedules. The pooled leash sweep used three-seat all-model tables. Per-character ladders then varied Mustard or Plum against headless opponents; Mustard's ladder is discussed in [[leash]].[^ringtwin][^pooled][^ladders]

{{table:ladder.plum|Plum's historical ring-board ladder, 13 September 2026: Plum with Mustard and Green, three seats, 24 games per completed leg, seed 7007. The leash-zero leg was aborted after one long game and is excluded from this table. Won and Wrong are per-seat-game percentages; departure percentage is per eligible decision.}}

The ladder's parking observations motivated work on movement and repeated questions; they do not prove that Plum always stalls or never accuses wrongly. Its separate aborted record is named `ladder-plum-leash-0-aborted` in the source, and should not be treated as another completed 24-game leg.[^plumladder]

On 14 September the memory record examined Mustard's stored-game training, White's opponent counts and Green's persistent arms. It also introduced fixed-state narrative read-back. The separate Plum logbook comparison used seat-locked characters and fresh paired legs; [[logbook]] and [[method memory]] explain the different kinds of learning.[^memory][^plumlog]

## Classic-board re-measurement

The grid work of 15 September repeated the belief benchmark, played an arena at ring-tuned presets, swept all five numerical dials and tested Scarlett's threshold separately. It also examined how travel, suggestions and passages affected play.[^gridbench][^gridfirst][^gridsweep][^scarlett][^gameplay]

Further targeted tests considered Green's threshold, curiosity and Plum's search budgets. The budget experiment recorded how many calls fell back to sampling; its counts should be read alongside the number of benchmark calls and each checkpoint, as explained in [[exact posterior enumeration]]. Preset changes and a tuned-grid arena followed. The tuned arena's complete outcome table is in [[arena#Recorded tuned-grid arena|Arena]].[^gridpresets][^gridtuned]

The 16 September grid twin comparison used 24 four-seat games per leg, seed 7007, with each character participating in sixteen games. A separate three-seat comparison isolated Plum with Claude against Mustard and Green. [[Twin comparison]] presents the paired losses and gains rather than treating aggregate swings as independent evidence.[^gridtwin][^plumgrid]

The landing-rule record of 18 September compared repeated suggestions before and after the rule at several table configurations. [[Landing rule]] explains the behavioural change and its measured limits. Those results follow the major grid tuning tables; they do not retroactively update their rankings.[^landing]

## Opening the underlying games

Signed-in readers can use [[the lobby]]'s development folders (phase one, and phase two since the new Plum) to browse saved arenas, sweeps, ladders and fixtures, then open their [[replay|replays]]. The practice sets contain games completed through the app, including Watch. The folders list runs present in the selected store, which need not include every historical source run.

The strategy glossary retains run identifiers and commands for the experiments above. [[Maintainer CLI]] can inspect stores and exported results. A recorded event log remains evidence of that game even if a new version would play it differently; rerunning a historical command is a new experiment whose version and date should be recorded.


## See also

[[Belief benchmark]] · [[Arena]] · [[Dial sweeps]] · [[Character training]] · [[Game records]]

## References

{{references}}

[^glossary]: {{cite:docs/strategy-glossary.md}}
[^phase4]: {{cite:docs/strategy-glossary.md|Phase 4 benchmark results (RandomBot regime, historical)}}
[^ringbench]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^ringfirst]: {{cite:docs/strategy-glossary.md|Arena, first pass (untuned presets)}}
[^ringsweep]: {{cite:docs/strategy-glossary.md|Dial sweeps}}
[^ringtuned]: {{cite:docs/strategy-glossary.md|Arena, tuned presets}}
[^ringpresets]: {{cite:docs/strategy-glossary.md|Tuned presets}}
[^ringtwin]: {{cite:docs/strategy-glossary.md|Twin comparison (2026-09-13)}}
[^pooled]: {{cite:docs/strategy-glossary.md|Leash sweep (2026-09-13)}}
[^ladders]: {{cite:docs/strategy-glossary.md|Per-character leash ladders (2026-09-13)}}
[^plumladder]: {{cite:docs/strategy-glossary.md|Plum}}
[^memory]: {{cite:docs/strategy-glossary.md|Phase 7: memory (2026-09-14)}}
[^plumlog]: {{cite:docs/strategy-glossary.md|Plum's logbook at leash 0.5 (2026-09-14)}}
[^gridbench]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^gridfirst]: {{cite:docs/strategy-glossary.md|Arena on the grid, presets as tuned on the ring (Stage 1f)}}
[^gridsweep]: {{cite:docs/strategy-glossary.md|Dial sweeps on the grid (Stage 1c)}}
[^scarlett]: {{cite:docs/strategy-glossary.md|Scarlett's threshold on the grid (Stage 1d)}}
[^gameplay]: {{cite:docs/strategy-glossary.md|How the game plays on the board (Stage 1g)}}
[^gridpresets]: {{cite:docs/strategy-glossary.md|Tuned presets on the grid (Stage 1e, 2026-09-15)}}
[^gridtuned]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}
[^gridtwin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}
[^plumgrid]: {{cite:docs/strategy-glossary.md|Plum with Claude on the grid (Stage 2b, 2026-09-16)}}
[^landing]: {{cite:docs/strategy-glossary.md|The landing rule (Phase 8.0.4, 2026-09-18)}}

{{navbox:clude}}
