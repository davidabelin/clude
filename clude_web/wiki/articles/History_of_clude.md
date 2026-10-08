---
title: History of clude
short: Development from a headless game to web tables and Wikiclude
categories: The app
---
**History of clude** traces the project's development from a headless [[Clue]] game to an app for people, numerical characters and language models. The phase plans record design decisions and completed work; the [[measurement record]] preserves the experiments used to assess it. A phase being built locally does not establish which version is deployed.[^plan]

## Engine, deductions and methods

Phases 1 and 2 established a rules engine, structured event log and [[deduction floor]]. The floor propagates what follows from hands, passes, refutations and hand sizes. Phase 3 added the six suspect methods as estimators of the hidden cards, before they selected actions. Phase 4 introduced a [[belief benchmark]] to compare their readings on common evidence.

Phase 5 added [[personality dials]], action scoring and [[arena|arena evaluation]]. Characters could now lose because of where they walked or when they accused, even with useful card estimates. Early experiments used a simplified ring board. Their figures remain historical results under that geometry, rather than measurements of the present [[Classic board]].

## Voice and memory

Phase 6 added the [[LLM wrapper]]: a scored legal menu, a [[persona]] and an optional remark. The [[leash]] bounds how far the model may depart from the numerical preference. Failed responses fall back to the character's own choice. Live twin comparisons and per-character leash ladders were recorded on 13 September 2026.

Phase 7 added persistent [[logbook|logbooks]], the [[debrief]] and a [[memory dial]]. Numerical [[method memory]] and model-written accounts remain separate. The ring-board memory experiments of 14 September tested both numerical learning and Plum's narrative notes.

## Classic board and people at the table

On 15 September 2026 the Classic grid replaced the ring simplification. Phase 8.0 repeated benchmarks and tuning on the grid, followed by model comparisons on 16 September. The [[landing rule]], adopted on 18 September, addressed repeated suggestions and passage loops. Much of the major tuning record predates that rule.[^measurements]

Phase 8.1 introduced the Flask app, [[the lobby]], [[Watch]] and [[replay]], with the initial Cloud Run deployment on 18 September. Phase 8.2 added human seats, open reservations and resumable tables. Phase 8.3 added model seats under spending caps, human chat, off-turn reactions and web-game debriefs.

## Chat seats and presentation

Phase 9 added [[a seat over MCP]], letting a chat agent occupy a human seat through the same registry as the browser. Subsequent work made responses compact, added account login and logout, and refined queued decisions, autopilot and game views.[^mcp]

Phase 10 developed the table's stage and rail, the board's visual treatment, sound effects and named [[looks]]. Case-file light became the default, beside Gaslight dark and Developer. Stored games were grouped into practice and development, and the footer added the AIX Laboratories attribution (since 2026-10-07 [[AIX Protodyne]]).

Phase 12 rebuilt [[Professor Plum]]. His exact enumeration, the slowest and least accurate mid-game method on the Classic board, was archived with its character as [[PlumOG]] on 5 October 2026, and a network trained by [[regularised Nash dynamics]] took his seat; the first trained weights were committed on 6 October and measured the next day.[^phase12]

Wikiclude began as Phase 10's explainer work. Its first articles introduced the characters and their methods, followed by rules, mathematics, personality, memory and evaluation. App and project articles and the classwork archive completed the initial collection. A final review checked prose, examples, navigation and presentation across the full collection. These are local development milestones, distinct from deployment.[^wiki]


## See also

[[clude]] · [[Measurement record]] · [[Classic board]] · [[Classwork archive]]

## References

{{references}}

[^plan]: {{cite:docs/phase-plan.md}}
[^measurements]: {{cite:docs/strategy-glossary.md|Re-measurement on the Classic board (2026-09-15)}}
[^mcp]: {{cite:docs/web.md|A seat over MCP (Phase 9)}}
[^wiki]: {{cite:docs/wikiclude-plan.md}}
[^phase12]: {{cite:docs/deepnash-plan.md|12. As implemented: N1's storage half and N5 (2026-10-07)}}

{{navbox:clude}}
