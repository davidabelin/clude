# Phase 7: persistent logbooks

Completed and measured 2026-09-14. Historical record; [Logbooks](logbooks.md) owns current schema/operations and [the glossary](strategy-glossary.md) the learning-run evidence. Plum here is PlumOG and the board was the ring.

## 6. Decisions (David, 2026-09-14)

Debrief sees the whole deal face up. All three numerical memories are included: Mustard's records, White's per-identity priors and Green's posteriors. Narrative depth is a Profile dial: 0 head, 0.5 entry summaries/flags, 0.75 recent full entries, 1 all entries. Intermediate selection was implemented proportionally. Entries add summary/connecting flags to the Zenbot-shaped narrative.

Characters became seat-locked the same day; people would use persistent labels independent of token. No persona changes or movement-score fix were part of Phase 7.

## 8. As implemented

### 7a, Tier 0 and the documents (2026-09-14)

Records gained opponent/model audit context and replay into masked seat views. Logbooks use method.json, immutable per-game narrative entries and a rolling head under identity keys. Generic store documents avoid a game-record version bump for memory.

### 7b, method memory (2026-09-14)

Mustard/White absorb stored records by game ID, idempotently, including games they did not play. Mustard's memory tree is per-agent; absent memory uses the cached baseline. White's remembered opponent prior has fixed total mass. Green restores/persists live Beta posteriors; records cannot rebuild his missing arm predictions. Read-only comparisons freeze memory.

### 7c, the narrative (2026-09-14)

LLMCharacter attaches/renders memory as a second stable cached block and requests a post-game entry. Debrief has its own timeout, maps opponent names to labels, validates/caps schema fields, and leaves the game intact on failure. CLI gained attachment/filter/read-only, show/reset/rebuild; narrative writes require an LLM.

### 7d, live measurement (2026-09-14)

Twenty-four paired games at PlumOG leash 0.5 reduced stalls but introduced two below-threshold wrong accusations; wins were within sampling noise. The memory-depth dial above zero and transfer to another table were not measured. Commands, costs and quarter-by-quarter counts remain in the glossary.

Later defaults: new web tables remember, lobby LLM depth starts at 1, CLI still opts in. Classic-grid rebuilds default to record version 3; ring archives remain readable but excluded unless requested. Those are current guide instructions, not the original Phase 7 defaults.
