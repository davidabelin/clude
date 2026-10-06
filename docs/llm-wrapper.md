# The LLM wrapper (`clude_llm`)

An LLMCharacter wraps the same numerical Character shown as **X (headless)** in the lobby. **X (LLM)** adds persona, leashed choices and talk. Memory is independent of this choice: [Logbooks](logbooks.md) owns attachment/depth rules and [Web](web.md) owns spend caps/lifecycle.

## What happens on one decision

1. Build a legal menu from Character's pure scoring helpers, including any agent policy hooks. Movement, accusation and show use one letter; suggestion uses suspect/weapon letters. Own-hand bluff options are labelled explicitly.
2. Allow scores at least `(1 - leash) * best_score`. Zero leash retains best ties; one opens all legal options. A single allowed choice needs no model call.
3. Send persona/rules, optional stable memory block, the seat's observation and a fixed JSON response schema to the backend.
4. Validate the response and play an allowed choice. Budget exhaustion, backend errors/timeouts/refusals, malformed JSON and invalid letters fall back to Character, consuming its RNG as ordinary numerical play would. NullBackend therefore reproduces the numerical twin.
5. Audit the menu, choice, fallback, deviation, proposed/spoken line, tokens and time in Decision; persisted games keep per-seat `llm_log`.

The accusation menu allows the best triple once `P(correct) >= (1 - leash) * accuse_threshold`; passing is allowed below threshold or whenever leash is nonzero. At zero leash it matches Character's threshold test. Peacock uses her lower belief bound rather than pignistic probabilities.

On-turn remarks pass a `chattiness` gate and become RemarkEvents. Off-turn `react` requests use a `say`-only schema and fail silently; the web reaction queue decides participation/pacing. Budget usage includes reactions and debriefs. Web LLM seats are driven externally and their answers/audits/remarks stored, so cold rebuild never repeats a call.

## What the model is shown, and what it is not

Live decision/remark prompts use the observing seat's ClueObservation, not omniscient GameState: identity/token, public seats, own hand, floor, method probabilities/diagnostics, accusation test, redacted history, recent talk and legal menu. Other hands, the envelope and private shown cards remain hidden. Post-game debrief deliberately sees the whole deal face up.

Use `clude_cli.py prompt` to inspect the actual prompt without spending. Persona plus rules form the stable system prefix; attached memory is a second block stable within a game. Backend caching is an optimization, not a correctness condition.

## Personas

`personas/<Suspect>.md` describes identity, method and voice; `rules.md` supplies shared behavior. These are executable prompts. Keep numerical flaws in agents/dials, rather than ordering the persona to make deliberately wrong decisions. Scarlett's current preset threshold is 0.3; Plum's method is the policy/belief network, not PlumOG's enumeration.

Phase 11 updated Plum's method description and condensed shared rules. Exact system text participates in LLMRequest replay keys, so both historical fixtures are stale. Keep them as historical recordings; do not rewrite keys to pretend they are fresh. Paid re-recording and outcome/tally updates require separate approval. Phase 12's trained-weight validation can change menus again.

## The two Phase 6 dials

`leash` governs allowable choices; `chattiness` gates proposed talk. Both are Profile dials, ignored by numerical Character. Current defaults are 0.25/0.5. A policy agent can have different score spread from enumeration, so the same leash value does not imply the same menu width. Phase 12 must re-measure Plum's leash.

## Memory (Phase 7)

A logbook attachment supplies a stable cached block at Profile.memory depth. Zero reads the condensed head; one reads full entries. Empty/unattached memory sends no block. After a game, `debrief` requests an entry against LOGBOOK_SCHEMA; failure leaves `last_debrief` and writes nothing. [Logbooks](logbooks.md) explains schema, model-visible content and administration.

## Backends

| `--llm-backend` | Behavior | Can call the service? |
|---|---|---|
| `anthropic` | AnthropicBackend; SDK imported lazily | Yes |
| `null` | Always fails; numerical fallback | No |
| `record:PATH` | Real backend plus saved requests/replies | Yes |
| `replay:PATH` | Reply lookup by request digest; ReplayMiss on mismatch | No |

The backend delegates authentication to the SDK; direct scripts should export `ANTHROPIC_API_KEY` explicitly. Web config also supports selected `.env` fallbacks. In earlier live checks, organization keys failed because the backend does not supply a workspace header; use the workspace-scoped key provisioned for the service. Missing/bad credentials produce fallback, which must be distinguished from a successful model run.

Defaults in LLMSettings: configured model `claude-opus-5`, low effort, 2048 tokens, 30 s timeout, 200 calls/500K tokens per game, eight recent talk lines; debrief medium effort/4096 tokens/180 s; reaction 200 tokens. AnthropicBackend defaults to one SDK retry. These are code settings, not verified current provider capabilities/pricing.

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
budget an arena with: a 24-game, 4-seat run is order $10. Plum's games
run long and ask the model often, so his seat-game is about $0.25. A
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
