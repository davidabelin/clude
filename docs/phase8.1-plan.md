# Phase 8.1: browser scaffold and Cloud Run

Local scaffold built 2026-09-17, deployed 2026-09-18. This is a historical summary. [Web](web.md) owns current configuration/deploy instructions; [architecture](architecture.md) owns engine boundaries. The original replay artboards remain under `docs/ux/`.

## Decisions

Use an app login, not a Google-account allowlist. Accounts are CLI-created and stored alongside records, with hashed passwords and a one-time password offer. Convenience was deliberately favored: default `password`, any non-empty password, case-insensitive names. Keep centralized route gating, CSRF, rate limiting and HTTPS cookies.

Replay follows the scrubber design; Watch uses compact progress readings without named private cards. Generate the board from the rules map and leave colors to stylesheets. Use Cloud Run with a narrow runtime identity, scaling to zero; no always-warm instance.

## 8. As implemented

- `game_steps` became the single resumable turn loop; `run_game` drains it for numerical play. External DecisionRequests later enable human/model seats without duplicate rules.
- Flask factory/config/auth/users provide store selection, stable secrets, session/cookie policy and centralized private-by-default routes.
- Board SVG and event frames use the engine map/log. Shared-room tokens fan out; absent suspects acquire no invented positions.
- Belief traces cache expensive reconstructed analysis. The original limitation remains: fresh agents without live method memory/Green feedback do not reproduce live beliefs exactly.
- Login, lobby, run listings, replay and Watch work against local/GCS stores. Summary fetches are parallel rather than one bucket round trip at a time.
- Docker/ignore files exclude keys, `.env` and data; `requirements-web.txt` supplies runtime dependencies. `store copy` moves selected records/traces/logbooks, not accounts or live tables.
- The runtime identity is distinct from the project-owner deploy identity. Live timings were recorded after deployment; they are historical evidence in Web, not current guarantees.

Later phases replaced the Flask-only server command with the combined ASGI app, added human/LLM/MCP seats, made privacy/wiki public and renamed Legacy to Developer. Use the current Web guide rather than replaying this phase's original provisioning sequence.
