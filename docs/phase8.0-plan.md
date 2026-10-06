# Phase 8.0: Classic-board re-measurement

Completed 2026-09-18. Stage labels in [the glossary](strategy-glossary.md) correspond to steps 8.0.N. This historical record summarizes the process; tables, commands, seeds, costs and caveats remain in the glossary.

## Completed stages

| Stage | Result |
|---|---|
| 8.0.0 | Establish grid-era baselines and preserve ring-era evidence |
| 8.0.1 | Re-run belief/arena/dial/board reports and retune presets (2026-09-15/16) |
| 8.0.2a-b | Paid paired grid twins/PlumOG table (2026-09-16) |
| 8.0.3 | Archive ring logbooks and reset/rebuild current memory from grid records |
| 8.0.4 | Measure and keep the shared landing rule (2026-09-18) |

## Decisions and findings

Scarlett's threshold moved to 0.3; PlumOG's curiosity to 0.5 and sample budget to 10,000. Other presets stood after confirmation. Larger samples were still needed to distinguish small win-rate changes.

David approved 8.0.2a-b at $21-35; actual spend was $14.24. The paired results retained the direction of the ring twins, but the old parking trigger missed a passage loop. A movement-scoring change, measured headlessly first, replaced further paid experiments. Steps 2c/2d were **not run**.

All four logbooks were copied to `data/llm/logbooks-ring` before reset; Mustard/White rebuilt only grid-era records. Rebuild's default minimum version became 3 so old records could not leak back into memory.

The first landing-rule candidate demoted every located room and overshot, removing useful own-hand/envelope rooms too. The kept rule demotes only rooms held by another seat. Three paired arenas showed shorter games and fewer loops; win-rate changes remained noisy. Goldens and LLM fixtures were refreshed. [Phase 8](phase8-plan.md) records implementation; the glossary's landing-rule section preserves both variants.

## Later scope

Current Plum is the Phase 12 network. These results describe PlumOG and the older Green arm, not acceptance evidence for the replacement. Each future paid run still needs its own estimate/approval.
