# Phase 6: the LLM wrapper

Completed and live-measured 2026-09-13. This historical record is condensed; [LLM wrapper](llm-wrapper.md) owns current behavior and [the glossary](strategy-glossary.md) the measured tables. This phase used the ring board and the original enumeration Plum.

## 6. Decisions (David, 2026-09-12)

The model chooses only from a scored legal menu, supplies a short remark and falls back to the numerical character on failure. Keep menus derived from the character's method, not a new inference layer. Add leash/chattiness to Profile, use the configured Anthropic backend, and compare paired numerical/model games before changing presets.

## 8. As implemented

### 6a, the seam (2026-09-12)

Character scoring was exposed as pure helpers; explanation functions render per-seat knowledge. SpeakingPlayer buffers remarks into RemarkEvents. Records gained model seat metadata/audits; non-speaking seeded games remained unchanged.

### 6b, the wrapper on fake backends (2026-09-12)

LLMCharacter, menus, response schemas, personas, requests/results, null/scripted/record/replay backends and audits were built. Menus spend no RNG; malformed/illegal/error replies use the original numerical decision. NullBackend and adversarial replies were checked against golden games.

### 6c, the real backend (2026-09-12; live checks done 2026-09-13)

AnthropicBackend added cached persona/rules, structured output, effort/timeouts and one SDK retry. SDK failures become error results rather than breaking play. Live checks verified calls/cache usage at the time, not future provider behavior. Organization-scoped keys failed without a workspace header.

Persona tuning addressed repeated talk and Plum reciting decimals; his voice stayed pedantic. Mustard, Green and White needed no edits. Replay recordings are coupled to exact system prompts, menus and state. They were refreshed after later board/preset changes; **both are stale again after Phase 11's rules/persona edits**, pending separately approved paid refresh.

`prompt --decision move` renders from reconstructed positions with a supplied plausible roll; it is inspection, not a saved real turn's decision.

### 6d, the arena (2026-09-12; measured 2026-09-13)

Arena/sweep gained model usage/fallback/deviation/talk/cost metrics and persisted audits. The twin run showed a faster LLM table reducing PlumOG's advantage; Mustard's gains did not reproduce when only he was LLM-piloted. Small/pooled sweeps were not enough to retune everyone. Leash 0.25 and chattiness 0.5 stood; per-character ladders exposed parking that later motivated memory and the landing rule.

Full commands, cost, sample counts, tables and limitations remain under Phase 6 in the glossary. Off-turn chat, web seats and logbooks were later phases.
