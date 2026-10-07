# Logbooks: playerbot memory

Logbooks belong to a persistent identity (`SeatRecord.label`) in the same local/GCS store as game records. Characters use their own names and are seat-locked; people use normalized account keys across tokens. Characters can write dossiers *about* people; human seats do not themselves write model entries.

## Three tiers

| Tier | Content | Storage |
|---|---|---|
| 0: record | Omniscient deal, events, seats and outcome | `games/<run>/<index>.json` |
| 1: method memory | Numerical state for Mustard, White and Green | `logbooks/<identity>/method.json` |
| 2: narrative | Model-written entries and rolling head | `logbooks/<identity>/entries/NNNN.json`, `head.json` |

New web Play/Watch tables remember by default; uncheck to opt out. Saved settings remain, and old documents missing the field read as false. CLI games require `--logbook`; bare TableGame does no memory I/O.

Both **X (headless)** and **X (LLM)** use X's numerical method and supported Tier 1 memory. Only LLM seats read/write Tier 2. Scarlett, Plum and Peacock have no persistent method memory; Plum's committed network weights are model parameters, not a per-game logbook. Planned learning from stored records is outside current Phase 12.

## Tier 1: method memory

| Character | Remembered | Applied |
|---|---|---|
| Mustard | Training contributions from stored games, built from every seat's masked view | Extra rows appended to the 25-game self-play base before per-agent tree fitting |
| White | Repeat/new transition counts per opponent identity | Reshape the four-cell Laplace prior at the same total mass |
| Green | Beta posteriors over his five agent arms | Restore after reset; update with live predictions/outcome |

Mustard/White can learn from records of games they did not play. Contributions are keyed by game ID, making repeated updates idempotent; rebuilding over the same records reproduces their accumulated memory. Green's arm predictions are not in GameRecord, so his memory cannot be rebuilt from records.

Memory changes reproducibility: numerical play depends on code, seed, weights **and memory state**. Empty/absent memory reproduces the ordinary baseline. Web tables snapshot loaded contributions/posteriors so cold rebuild uses the original inputs, not newer games' memory. Finish merges Green's feedback against the latest stored posteriors.

## Tier 2: the entry and the head

Entry metadata is computed by code: identity, serial/date, game ID, token, opponents, outcome and model. The model writes:

| Fields | Content |
|---|---|
| `title`, `summary`, `flags` | Short title, summary up to 40 words, normalized connecting keywords |
| `what_happened`, `final_outcome` | Narrative and result in the character's voice |
| `evaluations` | Reads/notes on opponents present |
| `key_insights`, `lessons_learned` | Short lists |
| `standing_instructions` | Revised list, at most eight |
| `dossiers` | Revised opponent reads, at most 60 words each |

LogbookEntry.build normalizes/caps lists and retains only opponents present. The rolling head computes tally and flag index, carries instructions and per-opponent dossiers, and updates only dossiers touched by an entry. An entry with no instructions leaves the previous list standing. The schema was adapted from the Zenbot memory example in `docs/zenbot_memories.json`; that sample is historical reference, not the current schema authority.

## The `memory` dial: what a character reads back

Profile/SeatSpec/CLI default to 0; new lobby LLM seats default to 1. **Zero is condensed memory, not off.** Attachment/remembering determines whether memory is used at all.

| Depth `m` | Read-back |
|---|---|
| 0 | Head: tally, instructions and dossiers on current opponents |
| `0 < m <= 0.5` | Head plus latest `ceil(n*m/0.5)` index entries: summary, flags, date, table and result |
| `0.5 < m <= 1` | Head/full index plus latest `ceil(n*(m-0.5)/0.5)` full entries |

At 0.5 the whole index appears; at 0.75 half the full entries; at 1 all. The block is stable for a game and sent after persona/rules as a second cached system block. Empty memory sends no block. `logbook show --memory DEPTH` renders exactly this selection.

Narrative memory steers choices only inside the existing leash; it cannot widen the menu. Historical PlumOG parking/logbook findings are in [the glossary](strategy-glossary.md#plums-logbook-at-leash-05-2026-09-14), not acceptance evidence for current Plum.

## The debrief

A remembering LLM seat receives the whole deal face up, its live-view history, talk, audited choices, final belief versus truth, existing head/index and field instructions. `resolve_opponents` maps model names to the opponents' persistent labels. Response schema is LOGBOOK_SCHEMA; defaults are medium effort, 4096 tokens and 180 s. Failure/refusal/malformed data writes no entry and records `last_debrief`; the finished game remains valid. `debrief=False` skips it.

Web wrap-up performs one seat's debrief per work request. Costs belong to the completed game and settle after entries finish; closing all clients can leave wrap-up pending until work resumes. Headless games update method memory without model calls or narrative entries.

## Running it

```text
python scripts/clude_cli.py play --players 3 --roster Plum,Mustard,Green --store data/llm --logbook
python scripts/clude_cli.py logbook list --uri data/llm
python scripts/clude_cli.py logbook show --uri data/llm --identity Mustard --memory 0.75
python scripts/clude_cli.py logbook rebuild --uri data/llm --identity Mustard
```

`--logbook [URI]` on play/arena reads then updates; omitted URI uses `--store`. `--logbook-readonly` reads without writes, and sweeps always use read-only memory. `--logbook-characters` restricts attachment.

`logbook reset --identity NAME` removes head/method/entries; `--keep-entries` retains the archive. `rebuild` reconstructs the head and supported method memory, using `--from URI` if given. `--min-version` defaults to 3, excluding ring-era records; 1 includes every era. Green cannot be reconstructed. `copy --identity NAME --to ARCHIVE` archives a logbook under another identity, refusing an existing one; `reset-arm --arm NAME` forgets one arm of Green's posteriors. Phase 12's PlumOG archive is `copy --identity Plum --to PlumOG`, then `reset --identity Plum` and `reset-arm --arm Plum`: done on `data/llm` 2026-10-07, not yet on the bucket, so do not assume the live Plum logbook has been archived.

## Cost

Numerical method memory spends no API tokens but can add tree-fitting latency. Narrative decisions/read-back/debriefs use the configured model; [LLM wrapper](llm-wrapper.md#cost) and [the glossary](strategy-glossary.md) retain dated cost measurements. Those old Plum costs refer to PlumOG. The web ledger includes debriefs and may stop later calls when a cap is reached.

## Where things are

| Module | Responsibility |
|---|---|
| `clude_storage/logbooks.py` | Entry/head documents, Logbook and render_memory |
| `clude_training/replay.py` | Records reconstructed into omniscient state or masked views |
| `clude_training/memory.py` | Record contributions, load/update/rebuild |
| `clude_llm/logbook.py` | Debrief prompt and opponent resolution |
| `clude_llm/player.py` | Attachment, read-back and model debrief call |

Focused checks: `tests/test_logbooks.py`, `test_replay.py`, `test_memory.py`, `test_debrief.py`, plus web memory/wrap-up tests.
