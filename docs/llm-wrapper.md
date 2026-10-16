# The LLM wrapper (`clude_llm`)

An LLMCharacter wraps the same numerical Character shown as **X (headless)** in the lobby. **X (LLM)** adds persona, leashed choices and talk. Memory is independent of this choice: [Logbooks](logbooks.md) owns attachment/depth rules and [Web](web.md) owns spend caps/lifecycle.

## What happens on one decision

1. Build a legal menu from Character's pure scoring helpers, including any agent policy hooks. Movement, accusation and show use one letter; suggestion uses suspect/weapon letters. Own-hand bluff options are labelled explicitly.
2. Allow scores at least `(1 - leash) * best_score`. Zero leash retains best ties; one opens all legal options. A single allowed choice needs no model call.
3. Send persona/rules, the canon's index and the optional stable memory block as cached system blocks, the seat's observation and a fixed JSON response schema to the backend, with the canon's two tools while the game's lookups are under their cap.
4. Validate the response and play an allowed choice. Budget exhaustion, backend errors/timeouts/refusals, malformed JSON and invalid letters fall back to Character, consuming its RNG as ordinary numerical play would. NullBackend therefore reproduces the numerical twin.
5. Audit the menu, choice, fallback, deviation, proposed/spoken line, tokens and time in Decision; persisted games keep per-seat `llm_log`.

The accusation menu allows the best triple once `P(correct) >= (1 - leash) * accuse_threshold`; passing is allowed below threshold or whenever leash is nonzero. At zero leash it matches Character's threshold test. Peacock uses her lower belief bound rather than pignistic probabilities.

An on-turn remark becomes a RemarkEvent as written: it arrives in the same reply as the decision, so there is nothing to save by dropping it, and a character that prefers silence answers with an empty string (Phase 13 step 6). Off-turn `react` requests use a `say`-only schema and fail silently; the web reaction queue decides participation/pacing, drawing each seat at `chattiness ** (depth + 1)` before it pays for a call. Every line a model writes is cleaned like a person's -- control characters out, whitespace collapsed, 240 characters at most -- so one remark is one line in the record, a fixture and the next debrief prompt. Budget usage includes reactions and debriefs. Web LLM seats are driven externally and their answers/audits/remarks stored, so cold rebuild never repeats a call.

## What the model is shown, and what it is not

Live decision/remark prompts use the observing seat's ClueObservation, not omniscient GameState: identity/token, public seats, own hand, floor, method probabilities/diagnostics, accusation test, redacted history, recent talk and legal menu. Other hands, the envelope and private shown cards remain hidden. Post-game debrief deliberately sees the whole deal face up.

Use `clude_cli.py prompt` to inspect the actual prompt without spending. Persona plus rules form the stable system prefix; attached memory is a second block stable within a game. Backend caching is an optimization, not a correctness condition.

## Personas

`personas/<Suspect>.md` describes identity, method and voice; `rules.md` supplies shared behavior. These are executable prompts. Keep numerical flaws in agents/dials, rather than ordering the persona to make deliberately wrong decisions. Scarlett's current preset threshold is 0.3; Plum's method is the policy/belief network, not PlumOG's enumeration.

Phase 13 steps 1-3 broaden the six scripts with interests and social motives: shared NPR/New Yorker habits, Mustard's Freemasonry, Mustard and Peacock's FOX News loyalty, Green and Scarlett's distinct film interests, Plum's Economist reading and White's French news interest. The scripts allow warmth, disagreement and changes of impression without changing methods or dials. These are fictional background habits, not live news retrieval. Shared rules describe what the actors have been told about their origin, with differing, changeable individual responses; unfamiliar player identity is not inferred from a name or token. Decision and reaction prompts encourage listening, useful callbacks and silence, without requiring a tactical conclusion to every line. The recent-talk window remains eight by default. Step 6 gives a seat one set of participant names for the whole evening: `attach_names` takes what the table screen shows -- the token, and a person's capitalised display name after it -- and the on-turn, off-turn and debrief prompts all use it, where the on-turn prompt used to fall back to bare suspect tokens. The debrief still names the roster labels its dossiers are keyed on. Without the call, as in a headless arena or the CLI, the prompts fall back to seat labels. Step 5's wiki alignment was written on 2026-10-16 as [Wikiclude's W8](wikiclude-plan.md#15-as-implemented-w8-2026-10-16).

Exact system text participates in LLMRequest replay keys, so any persona, rules or menu change leaves the recorded fixtures stale; never rewrite keys to pretend they are fresh. Phase 11's prompt edits did so; both fixtures were re-recorded on 2026-10-07 (Phase 12 N6), with the trained network and Plum's leash of 0.35, and again on 2026-10-09 for the canon ($0.12 and $0.04; neither game made a lookup). Phase 13 steps 1-6 changed personas, rules and request text again, and both were re-recorded on 2026-10-15 once that text settled ($0.1149 and $0.0375, approved that day; neither game made a lookup, and no seat fell back). Seed 1 gained a suggestion, seed 2 replayed to the same shape, and both keep the envelope their seed dictates. With the on-turn talk gate gone these are the first recordings that carry everything the models said rather than half of it. The canon's index block is part of the same key, so a new Wikiclude article moves the recordings as a persona edit does: W8's *Wikiclude* article (2026-10-16) did, and both were re-recorded that day ($0.1602 and $0.0362, approved; no lookup, no fallback; seed 1 now runs 35 turns, seed 2 the same shape). The earlier recordings stay in the history as evidence and are never relabelled; independent recording/replay and fake-backend checks remain active.

## The two Phase 6 dials

`leash` governs allowable choices; `chattiness` draws the off-turn replies (it no longer gates an on-turn line, which is published as written). Both are Profile dials, ignored by numerical Character. Current defaults are 0.25/0.5, except Plum's leash of 0.35: his policy spreads its scores wider than PlumOG's enumeration did, so the same leash value gave him narrower menus. 0.35 matches PlumOG's menu width and was kept by the paid ladder of 2026-10-07 ([glossary](strategy-glossary.md), "Plum with Claude, the network (N6)").

## Memory (Phase 7)

A logbook attachment supplies a stable cached block at Profile.memory depth. Zero reads the condensed head; one reads the digest, if any, and every entry after it in full. Empty/unattached memory sends no block. After a game, `debrief` requests an entry against LOGBOOK_SCHEMA; failure leaves `last_debrief` and writes nothing. Outside any game, `condense_logbook` asks the character's model, under its persona, for a digest against CONDENSE_SCHEMA; failure writes nothing. [Logbooks](logbooks.md) explains schema, model-visible content and administration.

## The canon

Wikiclude is the standing reference an LLM seat knows ([the plan](canon-plan.md), 2026-10-09; its authority brief superseded by Phase 13 step 5, 2026-10-15). With a `WikiCanon` attached (`LLMCharacter(canon=...)`, `attach_canon`), every decision, remark and debrief request carries a third cached system block, the index of article titles, and two tools, `wiki_search` and `wiki_read`, which `AnthropicBackend` answers inside the one call through `Wiki.lookup` and `Wiki.read`: up to `max_lookups_per_call` rounds, the last sent with tool choice none so the model must answer in schema, and no tools once a game's lookups reach `max_lookups_per_game` (the index block still goes). A read hands over a short article whole, else its lead and section list and then one section at a time, never more than 8,000 characters; footnotes are left out. The rules now draw a line: on how this house plays the encyclopaedia beats a model's recollection of Clue, and legality is the engine's menu in any case, while on everything else -- a biography, a method description, an article about the character itself -- it may be doubted and disputed roughly as Wikipedia may be, and nothing in it outranks a card the character was shown. Mentioning or quoting it is allowed, the unparaded version remaining the usual style; each persona says how readily it consults it, so the propensity is prose, measured after the fact: lookups are audited per decision (`Decision.lookups`, kept in `llm_log`), summed in `summary()` and reported by the arena. Recordings keep the lookups and replay them without touching the wiki; a request without a canon is byte for byte the earlier one, and the null backend with a canon is still the headless twin. Web tables, `play --llm`, arenas and sweeps attach the canon; `--llm-no-canon` withholds it, and `prompt` prints the block and the tools. Condensing makes no lookups. One lookup round costs about $0.02 to $0.03 at Opus 5 list prices; the per-game cap bounds it at about $0.35 a seat-game.

## Backends

| `--llm-backend` | Behavior | Can call the service? |
|---|---|---|
| `anthropic` | AnthropicBackend; SDK imported lazily | Yes |
| `null` | Always fails; numerical fallback | No |
| `record:PATH` | Real backend plus saved requests/replies | Yes |
| `replay:PATH` | Reply lookup by request digest; ReplayMiss on mismatch | No |

The backend delegates authentication to the SDK; direct scripts should export `ANTHROPIC_API_KEY` explicitly. Web config also supports selected `.env` fallbacks. In earlier live checks, organization keys failed because the backend does not supply a workspace header; use the workspace-scoped key provisioned for the service. Missing/bad credentials produce fallback, which must be distinguished from a successful model run.

Defaults in LLMSettings: configured model `claude-opus-5`, low effort, 2048 tokens, 30 s timeout, 200 calls/500K tokens per game, eight recent talk lines; debrief medium effort/8192 tokens/180 s; condensing the debrief's effort and timeout with 8192 tokens; reaction 200 tokens; three lookups a call and twelve a game. AnthropicBackend defaults to one SDK retry. These are code settings, not verified current provider capabilities/pricing.

MeteredBackend wraps web calls, pricing model IDs from the repository table. It checks table/day caps before calls; actual usage can overshoot the remaining allowance by the final accepted call. It refuses unpriced models. Table/seat ledger persists across UTC midnight; daily ledger is service-wide. Model-visible prompts/logbooks contain no spend.

## Cost

These are historical ring-board measurements of PlumOG and the old presets,
not a current quote for the network or hosted provider prices.

Most menus have one allowed option at the default leash (refutations
especially), so a game asks the model far less often than it decides:
at seed 1 Scarlett made 7 calls across 17 decisions, Peacock 11 across
18. `play --llm` prints an estimate at list prices per game.

Measured on Opus 5 (2026-09-13), at list prices:

| Game | Seats | Turns | Cost | Cached |
|---|---|---|---|---|
| seed 1, 3 players, 2 LLM seats | 2 | 16 | $0.14 | 52% |
| seed 2, 4 players, 4 LLM seats | 4 | 39 | $0.43 | 46% |

That is roughly **$0.07-0.11 per LLM seat-game**, which is the number to
budget an arena with: a 24-game, 4-seat run is order $10. The network
Plum's seat-game has a median of $0.09 and a mean of $0.11, at leash
0.35 on his three-seat table (2026-10-07); one game in 24 ran 172 turns
and reached the 500K-token cap at $2.78. PlumOG's games ran long and
asked the model often, about $0.20-0.25 a seat-game. A
logbook (Phase 7) adds a debrief per seat-game, measured on six Plum
games (2026-09-14) at $0.06-0.11, mean $0.09: 2.5-7K fresh input
tokens, 2K cached, 1.8-3.1K output including thinking, 33-48 s at
medium effort; over the 24-game run of 7d, 24 debriefs cost $2.24,
$0.093 and 42 s each. At the default `memory` of 0 the read-back is a
few hundred cached tokens per call.

Read the usage fields carefully: `input_tokens` counts only the *fresh*
tokens and `cache_read_input_tokens` the cached ones, disjointly -- so
the cache share is `cached / (input + cached)`, not `cached / input`,
and `estimate_cost` bills them separately at $5 and $0.50 per MTok. On
seed 2 that is 57.6K cached against 68.9K fresh: 46%, and about $0.26
saved on a $0.43 game. Expect the share to fall as a game lengthens,
since the cached system block is fixed while the per-turn state grows.

## Measuring it

Compare numerical/model twins on the same seeds and fixed memory state. Arena reports calls, fallback/deviation rates, remarks, usage and latency; sweep varies one dial. Real backend choices are not deterministic. Record model, dates, seeds, board version, weights and memory alongside measurements. Old Plum costs/results refer to enumeration; they do not price or validate the new network. [The glossary](strategy-glossary.md) owns the dated evidence.

Fixture refresh after approval uses `play --llm --llm-backend record:PATH --verbose` with each fixture's seed, players and roster; update RECORDED_GAMES from its transcript. Commands and pending status are in [Phase 11](phase11-plan.md). Restore current-prompt replay tests only after fresh recordings exist.
