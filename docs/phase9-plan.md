# Phase 9: a seat over MCP

Built/deployed through 9j by 2026-09-27. Historical decision record; [Web](web.md#a-seat-over-mcp-phase-9) owns current transport/account/tool behavior. Initial proposals for a fixed Claude account and an advising character method were superseded.

## 5. Decisions (David's)

MCP, rather than a parallel custom API, lets a chatbot play an ordinary human seat on the existing table driver. Share the same TableRegistry with browser routes; two independent cached registries would race. The public transport is guarded by a secret path; each chatbot now also logs into its own CLI-created account. No character agent or persona advises it: the chatbot reasons from its hand, log and optional floor.

A person creates/deals the table in the browser. Open seats must fill first; starter/seated players may end it. Live spectators need accounts; a seated viewer cannot receive spectator readings. Private card reveals remain limited to their two participants. Tool descriptions are player instructions, not merely developer comments.

## 8. As implemented

| Step / date | Result and reason |
|---|---|
| 9a (2026-09-20) | Renumber MCP to 9, UX to 10, cleanup/release to 11 |
| 9b-c (2026-09-21) | SDK server/combined ASGI factory, shared registry, secret mount and first deployed game |
| 9d-e (2026-09-22) | Compact redacted views, robust decisions, notes, table ending, spectator separation and sequence stability |
| 9f (2026-09-25) | Room-name movement, one deadline for up to 60 s waits, skip unchanged notepad/seat data |
| 9g (2026-09-25) | Per-seat/table ledgers, final costs including entries, midnight-safe table budgets, historical cost backfill |
| 9h (2026-09-26) | Typing, per-turn timeout/three strikes, speed mode, certainty tags, replay animation and saved look |
| 9i (2026-09-26) | Wait for deal, hold advance pass on new certainty, hand sizes/disproof order, hard-mode notepad and absolute replay URLs |
| 9j (2026-09-27) | Per-account login tokens, watch/game/replay tools and display-name capitalization |

The first live view consumed too much context; event cursors/digests and unchanged-field replies made it practical. A stale answer quotes `seq` and is rejected, while `since` tracks events; they are distinct counters. Notes live on the table document, not in replay entries. Restoring a conversation with `since=0` supplies a complete own-seat view.

Flask runs through an ASGI bridge with independent request threads. The combined factory handles MCP lifespan and mounts the endpoint outside the browser login gate; unsupported OAuth/OpenID discovery returns JSON 404 only when the secret mount is enabled. Without a secret, ordinary Flask routing remains.

A pre-given pass is held back after an undisproved suggestion or a proven solution, avoiding the lost opportunity seen in a live game. Hard mode is selected before dealing (`full`, `shown`, `none`) and suppresses the seat's own certainty when deductions are hidden.

Phase 10 subsequently renamed Legacy to Developer, restricted all cost displays to that look, and added `clude_logout` with account epochs. There are now twelve tools; do not use the original seven-tool list as the current contract. The old three-minute takeover was replaced by 9h's decision/turn handling. [9h](phase9h-plan.md) records that bug and ruling.

Deployment revisions/live timings remain historical evidence; this documentation pass does not claim a live endpoint/login/game verification. Fake-backend SDK tests check complete games, stale/invalid answers, privacy, mount routing and rebuild.
