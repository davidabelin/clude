# The canon: Wikiclude for LLM and MCP players

Status: **built, tested and accepted locally, 2026-10-09; not deployed.** David took every recommendation of section 6 the same day and approved the paid steps; section 7 records what was built, where it departs from sections 3 and 4, and what the paid runs found (7.3: the loop works, nobody looked anything up unprompted).

## 1. The brief (David, 2026-10-09)

Permit LLM players to search and read Wikiclude articles, in a way that seems effortless and innate to them. Provide the same service to MCP players. Some players will be more likely to use it than others. Wikiclude is their **Authoritative Canon**, trusted by default.

## 2. What the code dictates

- **One call, one JSON answer.** `LLMCharacter` sends one request per decision (persona + rules as a cached system block, the logbook as a second, the seat's view as the user turn) and reads back a fixed JSON schema (`output_config.format`). The API accepts tool definitions and a JSON output format on the same request, and a tool round-trip ends with the schema still enforced, so a lookup can live inside the one decision without a second shape of call.
- **Replay keys.** `LLMRequest.key()` digests system, user, schema and memory. Any tool definition or new system text changes every key; the two offline fixtures (`tests/fixtures/llm_seed*.json`) are already stale from the uncommitted `rules.md` edit in the working tree (`test_recorded_llm_games_replay_offline` fails on it today), so this feature adds no new breakage, but a paid re-recording is needed once the prompts settle.
- **The wiki is in memory.** `clude_web.wiki.load()` renders every article once; `Wiki.search` is word matching over title, short description and plain text, and an `Article` carries its lead and body as HTML with `<h2 id="...">` section anchors. 74 full articles and 21 Algorithms stubs: a median article is 4,500 characters of text (about 1,100 tokens), the longest 19,500; a median lead 630 characters; *Rules of play* 7,800.
- **Dependency direction.** `clude_llm` must not import `clude_web` at module level. The wiki lives under `clude_web` only because `docs/` is not in the image; the adapter imports it lazily, as the Anthropic SDK is.
- **Budgets.** Every model call passes `MeteredBackend` (web) and the wrapper's per-game call and token caps. A lookup is extra tokens on the same call and is priced by the same `usage` fields, so the ledger and the Developer look's cost line see it without change.
- **Play is blind.** Wikiclude describes how everyone thinks in general and never a live deal (10c), so nothing a character reads can leak another hand.

## 3. Design

### 3.1 Two tools, offered on every model call

Two user-defined tools, `wiki_search` and `wiki_read`, go on every decision, remark and debrief request of an `LLMCharacter` that has a canon attached, and on nothing else. The backend runs the tool loop; the wrapper sees one `LLMResult` as before, with the lookups listed.

| Tool | Input | Returns |
|---|---|---|
| `wiki_search` | `query` | up to five matches: title, one-line description, excerpt |
| `wiki_read` | `title`, optional `section` | the lead, the list of sections, and the named section in full; `all` for the whole article, cut at 8,000 characters; an unknown title answers with what a search for it finds |

The same two functions, `Wiki.lookup(query)` and `Wiki.read(title, section)`, serve the MCP tools and the browser's `Special:Search` later if wanted. Plain-text sectioning (`render.sections`) splits the body at its `h2` anchors and strips markup, mathematics and figures as `render.plain` does.

### 3.2 Innate, not announced

- **`rules.md` gains a short section, *The canon*:** Wikiclude is the house encyclopaedia and the canon on the rules, the board, every suspect and method, the mathematics, the measurements and the app; the character knows it as it knows its own name; a question of fact about the game or the people at the table is looked up and the canon is trusted over recollection and over table talk; it is never announced ("what it says, you simply know"); it knows nothing of this deal.
- **A third cached system block, the index:** the article titles, one line, about 400 tokens, so a character knows what the canon holds and can `wiki_read` directly without a search round. Generated from the wiki at attach time; part of the replay key only when present, as the memory block is.
- **Tool descriptions** say the same in the model's own register: the canon, trusted by default, read before guessing.

### 3.3 Propensity by persona, measured after the fact

Each persona file gets one or two sentences on its relation to the canon, in voice: Plum has read every article and consults it by reflex; Peacock does not guess at a rule or a reputation, one looks it up; Green reads up on whoever he is borrowing from; White reads the biographies, not the mathematics; Scarlett skimmed it once and trusts her own numbers; Mustard has never opened it and will not unless someone cites it against him. No new Profile dial: the propensity is prose, and `Decision.lookups` and `summary()["lookups"]` measure what each character actually did, which the arena then reports beside calls and deviations. A dial can follow if the measured spread is not the wanted one (section 6, C-D2).

### 3.4 Caps and cost

`LLMSettings` gains `max_lookups_per_call` (3: search, read, read) and `max_lookups_per_game` (12). Past the per-call cap the last round is sent with `tool_choice: none`, so the model must answer; past the per-game cap the tools are no longer offered. A tool result is at most 8,000 characters.

One lookup round re-sends the cached prefix (about 3K tokens, $0.0015 at Opus 5's cache-read rate), the seat's view again (about 1.5K fresh tokens, $0.0075), the tool result ($0.002 for a search, up to $0.01 for a long section) and the model's thinking and answer (about $0.01): **$0.02 to $0.03 a lookup**, against a seat-game of about $0.09 today. A bookish character making four lookups a game roughly doubles its seat-game; the per-game cap bounds the worst case at about $0.35 on top. The index block adds about $0.02 a game in cache reads. Each round also adds a model round-trip, 3 to 8 s at low effort, under the per-round timeout; the three-round cap keeps a decision under two minutes in the worst case.

### 3.5 Recording and replay

`LLMRequest` gains `tools` (the two definitions, in the key when present) and `lookup` (the callable that answers them, not in the key); `LLMResult` gains `lookups`, a list of `{tool, input, found}` where `found` is the titles returned or the title and section read. `RecordingBackend` stores the lookups with the result and `ReplayBackend` serves them back, so a replayed game audits the same lookups without touching the wiki. `NullBackend` and `ScriptedBackend` are unchanged and a character without a canon sends exactly today's request, key included.

### 3.6 MCP

Two loginless tools, `clude_wiki_search(query)` and `clude_wiki_read(title, section="")`, returning what 3.1's functions return. Loginless because the wiki is public (W-D3) and reading it is not a game operation; the secret path still guards the transport. The server's `INSTRUCTIONS` and `clude_tables`' docstring name Wikiclude as the canon on the rules and the characters, to be trusted over a chatbot's own memory of Clue, and `clude_sit` points a new seat at *Rules of play*.

### 3.7 Wiring

- `clude_llm/canon.py`: the tool definitions, the index block, `Canon` (a protocol: `tools`, `index`, `lookup(name, input) -> str`) and `WikiCanon`, which imports `clude_web.wiki` lazily. `LLMCharacter(..., canon=None)`, `attach_canon`, and `build_llm_character(canon=...)`.
- `AnthropicBackend.complete`: the loop, usage summed over rounds, the assistant content (thinking blocks included) passed back unchanged, `tool_choice: none` on the last permitted round, any tool error returned as an `is_error` result rather than a crash.
- The seats: `clude_training.table.build_table` (web tables), `clude_training.arena` (`--llm` arenas and sweeps) and the CLI's `play --llm` attach `WikiCanon()` to every LLM seat; a rebuild (no backend) attaches nothing, as it calls nothing. `clude_cli.py prompt` prints the index block and the tools offered.
- Persisted games keep the lookups in each seat's `llm_log` through `Decision.to_dict`; the Watch and replay screens are unchanged (optional later: list a seat's lookups in the Developer look's audit).

### 3.8 Files

New: `clude_llm/canon.py`, `docs/canon-plan.md` (this), tests in `tests/test_llm.py`, `tests/test_wiki.py`, `tests/test_mcp.py`.

Changed: `clude_llm/backend.py`, `anthropic_backend.py`, `player.py`, `__init__.py`, `personas/rules.md` and the six persona files; `clude_web/wiki/index.py`, `render.py`; `clude_web/mcp.py`; `clude_training/table.py`, `arena.py`; `scripts/clude_cli.py`; `docs/llm-wrapper.md`, `docs/web.md` (fourteen tools), `docs/phase-plan.md`, `CLAUDE.md` (a settled decision); the wiki articles *LLM wrapper*, *A seat over MCP* and *Claude* (one paragraph each, caps through `{{code:...}}`).

## 4. Tests

- Wiki: `lookup` and `read` shapes; sections split at every `h2` and nothing lost between the plain text of the parts and of the whole; the 8,000-character cut; an unknown title answers with suggestions; every full article reads without error.
- Backend: against the fake client, a `tool_use` reply followed by a text reply yields one result with summed usage and one recorded lookup; the assistant content goes back unchanged; the last permitted round carries `tool_choice: none`; a tool error becomes an `is_error` result and the call still answers; a request without tools builds exactly today's call (the existing test).
- Wrapper: with a canon the request carries the tools, the index and the callable; past the game cap it carries none; `Decision.lookups` and `summary()["lookups"]` count; `NullBackend` with a canon still reproduces the numerical twin; recording and replay round-trip the lookups.
- MCP: search and read answer without a login; an unknown title is a message, not an error.
- The replay fixtures stay marked stale until re-recorded; the rest of the offline suite green.

## 5. Acceptance

1. `clude_cli.py prompt` shows the canon block and the tools for a Plum seat.
2. One paid `play --llm` game with Plum and Mustard at a three-seat table (about $0.30): Plum makes at least one lookup, the transcript shows no "I looked it up" lines, and the debrief audit lists the lookups. Approval needed before the call.
3. Re-record both fixtures (about $0.15 plus lookups) and update `RECORDED_GAMES`; separate approval.
4. An MCP chat seat reads *Rules of play* through `clude_wiki_read` on the local combined app.

## 6. Decisions for David

- **C-D1. Mechanism.** Tools inside the decision call (3.1, recommended: a real search and read, paid only when used) or a fixed canon block in the prefix (cheaper per use, innate by construction, but no search and about 8K cached tokens a call for two articles, which quadruples a seat-game).
- **C-D2. Propensity.** Persona prose, measured after the fact (3.3, recommended), or a new Profile dial `study` (0 to 1) drawn like `chattiness` to decide whether the tools are offered on a call, which touches presets, sweeps, the Personality dials article and the lobby.
- **C-D3. Which calls.** Decisions, remarks and the debrief (recommended); condensing excluded. Or decisions only, to keep off-turn lines cheap.
- **C-D4. Caps.** 3 a call and 12 a game, 8,000 characters a result; or lower.
- **C-D5. MCP login.** Loginless wiki tools (3.6, recommended) or `login` required like every other tool.
- **C-D6. The index block.** Titles in a third cached block (3.2, recommended, about $0.02 a game) or none, leaving every read to follow a search.
- **C-D7. Paid runs.** Approval for the acceptance game (about $0.30) and the fixture re-recording (about $0.15 plus lookups), or defer both.

**David's answer (2026-10-09): go with the recommendations**, C-D1 to C-D6 as recommended. C-D7 is read as not yet an approval to spend: the two paid steps wait for one.

## 7. As implemented (2026-10-09)

Built locally in one pass; `tests/test_canon.py` holds the gates of section 4, and the rest of the offline suite is green.

### 7.1 What is there

- **The wiki**: `render.sections` splits a body at its `h2` anchors; `Wiki.titles`, `Wiki.lookup` and `Wiki.read` are the three calls both players use. A read leaves out *References*, lists up to 24 linked titles as `see_also`, and hands a short article over whole.
- **`clude_llm/canon.py`**: the two tool definitions, the `Canon` protocol, `index_block` and `WikiCanon`, which imports the wiki on first use. The index block is about 1,650 characters.
- **The request**: `LLMRequest.canon`, `tools`, `lookup` and `max_lookups`; the first two in the key when present. `LLMResult.lookups` and `Decision.lookups`. Recordings store the canon block by digest and the tools' names, and replay the lookups.
- **The backend**: `AnthropicBackend.complete` runs the loop; the system prompt is persona, canon, memory, stable before volatile; the assistant content goes back unchanged, thinking blocks included; every tool result of a round goes in one user turn; the last permitted round carries tool choice none; a lookup that raises is an `is_error` result.
- **The wrapper**: `attach_canon`, the per-call and per-game caps in `LLMSettings` (3 and 12), `game_lookups`, `lookups`, `summary()["lookups"]`; the arena's per-player stats and LLM table gain a lookups column.
- **The prompts**: `rules.md` gains *The canon*; each persona one or two sentences on its reading habits (3.3).
- **MCP**: `clude_wiki_search` and `clude_wiki_read`, loginless; the server's instructions, `clude_tables` and `clude_sit` point at the canon. Fourteen tools.
- **Wiring**: `build_table`, `TableGame`, `WebGame` and `WatchGame` take `canon`; the registry holds one `WikiCanon` and passes it with a backend factory, never to a rebuild; `run_arena` and `sweep_dial` take `llm_canon`; the CLI's `--llm-no-canon`, `_llm_canon` and the `prompt` command's canon block. `tests/test_canon.py` also holds a live smoke test of the loop, skipped unless `CLUDE_LLM_LIVE=1`.
- **Docs**: [LLM wrapper](llm-wrapper.md#the-canon), [Web](web.md#a-seat-over-mcp-phase-9), `CLAUDE.md`, the roadmap, and the wiki's *LLM wrapper*, *A seat over MCP* and *Claude*.

### 7.2 Where it departs from the plan

- A read with no section returns the whole article when it fits the limit (most do: the median is 4,500 characters), so one lookup usually suffices; the plan's lead-plus-sections reply is kept for the long ones.
- `see_also` was added to a read, the titles the article links to, so a reader can move on without a search.
- The MCP tools answer in the wiki's own shape rather than a copy; `clude_sit`'s reply is unchanged (its docstring points at *Rules of play*).
- The dial of C-D2 was not built; the arena's lookups column is the measurement.

### 7.3 Acceptance (2026-10-09, approved by David the same day)

| Step | Run | Cost | Found |
|---|---|---|---|
| 5.2 | `play --seed 3 --players 3 --roster Plum,Mustard --llm`, recorded, stored as run `canon-accept-2026-10-09` in `data/llm` | $0.15 | 18 calls, every one carrying the index block and the tools; 0 fallbacks; Mustard won in 20 turns; seven lines of talk in voice, none mentioning the canon; **no lookup by either seat** |
| 5.3 | Both fixtures re-recorded with the commands in `test_recorded_llm_games_replay_offline`'s docstring; seed 1 now 29 turns and 12 suggestions, seed 2 unchanged | $0.12, $0.04 | 15 and 6 calls, tools on all, no lookups; both replay offline again and the `xfail` marks are gone |
| The loop | `test_the_loop_live_smoke` (`CLUDE_LLM_LIVE=1`): a decision told to read *Leash* first | cents | passed: one `wiki_read`, answered inside the call, the reply in schema |

So the mechanism works end to end against the API, but in 41 ordinary calls at low effort no character found a question of fact to look up: the rules offer the canon "when a question of fact about the game or the people at the table arises", and a routine move or suggestion raises none. That is cheap, and innate in the sense asked for, but step 5.2's "Plum makes at least one lookup" was not met. Whether to nudge harder (a first-turn read of each opponent's biography, the debrief reading its opponents' articles, a higher effort for Plum) is a product decision, open.

### 7.4 Left

A deploy; the open question above.
