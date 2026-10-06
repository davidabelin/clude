# Phase 8: landing rule, people and web chat

Completed 2026-09-19. This historical summary covers 8.0.4 and 8.2-8.3; [Phase 8.1](phase8.1-plan.md) covers the scaffold/deploy. Current operations are in [Web](web.md), [CLI](cli.md) and [Logbooks](logbooks.md).

## 9. Decisions (David, 2026-09-18)

Measure the landing-score change headlessly first. Add human seats before model seats on the web. Use FloorBot as stand-in, request-driven work and per-table/day budgets; accept cold starts rather than keeping an instance warm. Login keys identify people across suspect tokens.

The original player view included compact readings; Phase 10 removed them from seated payloads. Remembering initially shipped off; David changed new web Play/Watch defaults to on on 2026-09-21. Current LLM lobby depth is 1. These later decisions supersede the initial UI defaults.

## 12. As implemented

### 8.0.4, the landing rule (2026-09-18)

Rooms located in another seat's hand became places on the way, while own-hand/envelope rooms remained useful suggestion destinations. The first candidate demoted all located rooms and overshot. The kept version shortened games and reduced repeats on three paired tables; small win-rate movements were inconclusive. Both candidates, commands and samples remain in the glossary. Goldens/recordings were deliberately updated.

### 8.2a, the driver and the terminal seat (2026-09-18)

SeatSpec/TableSetup describe tokens, occupants and saved settings. TableGame drives `game_steps`, validates external answers before sending, publishes snapshots and encodes entries for replay. `play --human` proves the same Flask-free driver from the keyboard. It still does not combine with records/model/memory CLI options.

### 8.2b-c, the web table (2026-09-18)

One TableRegistry persists setups, entries and memory inputs; live games are caches restored by single-flight rebuild. Browser forms use legal choices/CSRF/sequence checks. Open seats reserve tokens, account labels persist across games, and spectators receive a separate view. Autopilot and elimination cannot block mandatory refutation. Finish records the game and updates supported method memory.

### 8.2d, live check (2026-09-19)

Two accounts played through JSON routes and replay; a redeploy/resume checked the pending decision after cold rebuild. Scripts retain this workflow. Historical timings are in Web; offline passing tests alone do not verify production rebuild.

### 8.3a, model seats (2026-09-19)

LLM seats are externally driven one decision per work request; stored answer/audit/remarks prevent model calls during rebuild. MeteredBackend enforces the configured budget/day cap; unavailable keys disable/refuse seats and call failures fall back numerically.

### 8.3b, off-turn talk (2026-09-19)

Human lines and model reactions use RemarkEvents, never formal card evidence. Chattiness/reply-depth/pacing and per-turn/game limits bound participation. Work serves reactions so request-driven hosting needs no background worker.

### 8.3c-d, debrief and close (2026-09-19)

Remembering model seats read before deal and debrief after finish, face up, one seat per work request. Opponent dossiers use account keys. The live table with two model seats had no fallbacks and cost $0.34 at the time. Later Phase 9 recorded final table/seat costs including debriefs.

Remaining visual/help work moved to Phase 10; new Plum training is Phase 12. No public release was part of Phase 8.
