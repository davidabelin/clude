# Phase Plan

Current roadmap as of 2026-10-10. This describes the checkout, not a live production audit. Completed plans are historical decision records; the maintainer guides describe current behavior. The strategy glossary keeps dated measurements, including superseded ring-board and PlumOG results.

## Completed phases

| Phase | Delivered | Record |
|---|---|---|
| 1 | Headless engine, per-seat observations and event log | [Architecture](architecture.md#the-engine-seam-phase-5a) |
| 2 | Logical deduction floor with soundness checks | [Architecture](architecture.md#the-deduction-floor-clude_constraints) |
| 3 | Six belief agents and a suspect-keyed registry | [Strategy glossary](strategy-glossary.md) |
| 4 | Self-play snapshots and belief benchmark | [CLI](cli.md#benchmark) |
| 5 | Character profiles, FloorBot, arena, sweeps and record storage | [Phase 5](phase5-plan.md) |
| 6 | LLM legal menus, persona, fallbacks and measured twin comparisons | [Phase 6](phase6-plan.md) |
| 7 | Numerical/narrative logbooks, debrief and memory depth | [Phase 7](phase7-plan.md) |
| Board | Classic 24-column by 25-row grid replaced the ring on 2026-09-15 | [Board plan](board-plan.md), [current rules](board.md) |
| 8.0 | Grid re-measurement, retuned presets, memory reset and landing rule | [Phase 8.0](phase8.0-plan.md) |
| 8.1 | Flask login, lobby, Watch/replay and Cloud Run deployment | [Phase 8.1](phase8.1-plan.md) |
| 8.2-8.3 | Human seats, resumable tables, web LLM seats, chat and debriefs | [Phase 8](phase8-plan.md) |
| 9 | MCP seat on the same registry; account login, compact views, timeouts, costs, watch/replay | [Phase 9](phase9-plan.md), [9h](phase9h-plan.md) |

Phase numbers changed during planning: grid re-measurement became 8.0, human seats moved ahead of web chat, and MCP became 9, shifting UX to 10 and release cleanup to 11. Earlier references to Plum in measurements mean the enumeration agent now archived as PlumOG.

## Phase 10 scope

The main visual implementation is built: typography/tokens, blind play views, separate Talk and Record panels, phone tabs, decorated board/logo, three account-selected looks, narration, doors/passages and six sound cues. Current looks are Case-file light (default), Gaslight dark and Developer; only Developer displays costs. Sound starts off; music remains out of scope.

[Phase 10](phase10-plan.md) preserves the brief, decisions D1-D28 and implementation record. Earlier defaults and cost-display proposals were superseded by later rounds. Its help layer (10h) remains open. Former 10i explainers became Wikiclude, tracked separately and excluded from this round.

## Phase 11 scope

This round reviews documentation for a first-time maintainer, including docstrings. It does not declare version 1.0.0 ready.

- Make README the entry point and the roadmap a short status index.
- Give each guide one responsibility; remove repeated history and obsolete proposals from current instructions.
- Match contracts, CLI examples, dependencies, identity, memory, visibility and deployment instructions to the code.
- Condense completed plans while retaining decisions, rationale, cited headings and links to measurement evidence.
- Review docstrings for behavior, perspective, side effects and determinism. Preserve MCP descriptions as player-facing instructions.
- Update executable persona prompts, including Plum's enumeration description. Mark stale replay fixtures; paid re-recording requires a separate estimate and approval.
- Check Markdown targets/anchors, executable examples, Python behavior equivalence outside approved prompts, and the offline suite.

Wikiclude articles, rendering and assets are outside this pass. Existing source citations and fact checks must still resolve. Release polish, missing help, production checks and trained Plum acceptance remain separate work. See [Phase 11 record](phase11-plan.md).

## Phase 12 scope

[Phase 12](deepnash-plan.md) replaces PlumOG with a DeepNash variant over the floor. Work is interleaved with Phase 11; a trained checkpoint is committed (2026-10-06) and evaluated headless (N5, 2026-10-07); the paid leash ladder, the fixture refresh and the wiki pass (N6-N7) followed the same day, and the deploy with the bucket's logbook pass (revision `clude-00026-bsp`, 2026-10-07). Phase 12 is complete.

| Step | State in this checkout | Remaining work |
|---|---|---|
| N1 | Enumeration agent archived and removed from seating/Green's arms; `logbook copy`, `reset-arm` and `relabel` built; local and bucket passes done | None |
| N2 | Pure movement/suggestion scoring hooks built | Keep headless and LLM menus consistent |
| N3 | NumPy agent built; weights are run 2's checkpoint 130 | Replace weights only after validation |
| N4 | Rollouts, PyTorch trainer, two long runs and the export | A further run is optional, after N7 |
| N5 | Calibration table, arenas, dial sweeps and leash-width match measured; presets kept | None |
| N6 | Persona wording updated in Phase 11; paid ladder kept leash 0.35 ($8.38); both LLM fixtures re-recorded and replaying | None |
| N7 | Wiki rewritten for the network, with figures, diagrams, algorithm boxes and 21 Algorithms entries; lobby and Watch copy updated; engraved portraits in the character infoboxes; deployed 2026-10-07 | None |

The trained Plum has the best mid-game belief of any method, no wrong accusations and sub-millisecond calls; he wins a little less than PlumOG at his own table and less at six. Curiosity is inert for his policy hook; `accuse_threshold` and `temperature` were re-measured and kept; leash 0.35 matches PlumOG's menu width and the paid ladder kept it. With Claude he wins as often as headless, and a typical seat-game costs about $0.09. See [Phase 12](deepnash-plan.md) sections 11-13.

## Phase 13 scope

[Phase 13: Character development](phase13-plan.md) is the active plan, agreed 2026-10-10. Begin with a light editorial cleanup of the existing narrative logbooks; then broaden the six characters' lives, soften their fourth-wall premise, improve listening and social continuity, make Wikiclude explicitly fallible, and address participant naming and measured conversation pacing. The `focus` dial and character-authored wiki edits remain deferred.

Step 0's editorial pass is live (2026-10-10). Steps 1-3's six broader persona scripts, light fourth-wall premise and listening guidance are edited locally for review, using the five available current characters' history; no PlumOG history is assigned to current Plum. A live memory audit on 2026-10-14 revised the pathway: the bucket had run ahead of the edited snapshot, and the head layer proved to regenerate every game, so one of step 0's thirty-five edited standing instructions survives live while its digests survive intact. Six clauses in four characters' heads were rules against talking, and one digest theme; Mustard had none. Step 0's remaining scope is narrowed to the layers play does not rewrite, and isolating the reply taper becomes a precondition for the rehearsals that judge steps 1-5. Step 4's debrief and condensation guidance is implemented with the step 3 clause that conversation is not a tactical expense, reusing the existing narrative fields rather than extending the schema, and is deployed and accepted live (revision `clude-00029-8k8`, 2026-10-14): two games that evening show the characters remembering the company, and no live head carries a rule against talking. The generator change retired those six clauses itself, so only the digest theme needed applying by hand and the staged head pass is closed as moot. The broader entries outgrew the debrief's 4096-token cap, which covers thinking and reply together, and cost Plum his entry for one of those games; the cap is now 8192 and a truncated reply is reported as truncated rather than as bad JSON. Steps 5 and 6 then landed locally and wait on one deploy: Wikiclude is briefed as a fallible encyclopaedia in the shared rules, the canon tools, the MCP transport and two personas, with the three articles that restated the old brief corrected; a seat is given one set of participant names across its own turn, its off-turn replies and its debrief; every model line is cleaned as a person's is; and the on-turn `chattiness` gate is removed, having discarded 42 of the 81 lines those two games paid for, while the off-turn taper is left alone pending a comparison. The five-scene rehearsal is complete at $0.1373. Both exact-game replay recordings were refreshed on 2026-10-15 ($0.1524) and replay again, so the suite runs 622 tests. Step 0's remainder is prepared as `scripts/phase13_flag_hygiene.py` and awaits one `--apply`; the off-turn taper is left alone on the evidence with its baseline recorded; and Wikiclude's article pass is handed to [its own plan](wikiclude-plan.md) as W8. What remains of Phase 13 is the deploy of steps 5-6 and that one command. Offline checks verify prompt integrity and runtime contracts; character behavior still needs approved model rehearsals. [The implementation record](phase13-plan.md#10-implementation-record) owns the details.

## Logbook condensing

Built 2026-10-08, outside the numbered phases. `logbook condense` has each character's own model fold its logbook into a digest that replaces the condensed entries in read-back and the debrief, and merges near-duplicate flags; the entries stay as the archive. [Logbooks](logbooks.md#condensing-the-digest) owns the details. The paid run on `data/llm` and the bucket waits on David's approval of the dry run's estimate.

## The canon

Proposed 2026-10-09, outside the numbered phases: Wikiclude as the canon that LLM seats and MCP players search and read, through two tools inside the decision call and two loginless MCP tools. [The canon plan](canon-plan.md) holds the design, the cost estimate, David's decisions and the implementation record. Built, tested and accepted locally on 2026-10-09 ($0.31 in paid runs: the loop works against the API, both fixtures re-recorded, no seat looked anything up unprompted), not deployed.

## Legacy code disposition

`legacy/` is reference only and never imported. Its domain/constraints, belief tracker, opponent model and information agent informed current packages; DQN/GNN/reward-shaping experiments remain deferred. See [legacy README](../legacy/README.md).

## Open questions

Release remains private, for family and friends. Public release needs a separate IP review. Version 1.0.0, help scope and further live measurement/deployment are not approved by this pass.
