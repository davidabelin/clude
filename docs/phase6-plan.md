# Phase 6 Plan: the LLM wrapper (approved 2026-09-12)

Status: **complete. Approved 2026-09-12, and 6a-6d were built the same
day and tested on fake backends. The live smoke test, persona tuning and
arena measurements followed on 2026-09-13.** One open follow-up remains:
a per-character leash sweep before any preset changes (section 8, 6d).
David's answers to the four
decisions are in section 6; what was actually built, and where it
departed from this plan, is in section 8. Same shape as `docs/phase5-plan.md`: what the code
dictates, the design, sub-phases, decisions, out of scope.

## 1. Context

Phases 1-5 give every suspect a `Character` that turns its method's
belief into the four engine decisions through five numeric dials. Phase 6
(`docs/phase-plan.md` row 6) puts an LLM between those numbers and the
action: the character's own scored menu of legal options plus its persona
go to the model, which returns a structured choice and one line of
in-character table talk; anything illegal, malformed, refused, or failed
falls back to the character's own decision, so a game can never stall.
Phase 7 (logbooks) and Phase 8 (front end, chat, human seats) sit on top
of this, so the dialogue event, the menu shape, and the seat-side prompt
rendering built here are what they will reuse: `docs/architecture.md`
promises a human seat "the identical reachable-room menu and feature
vector", and the `Menu` below is that object.

Three invariants Phase 6 keeps. The LLM never sees anything its seat
cannot see: prompts are rendered from `ClueObservation`, never
`GameState`. It can never make an illegal move or dodge a required
reveal: the engine trusts its players completely (`apply_move` and
`resolve_suggestion` do no membership checks), so every check lives in
the wrapper, and `docs/architecture.md` "Reveal integrity" already asks
for the regression test. And the test suite never spends money: fake and
replay backends, one env-gated live smoke test, the `CLUDE_GCS_LIVE`
pattern.

## 2. What the code dictates

- **The four decisions differ in how interceptable they are**
  (`clude_agents/character.py`). Movement is already a pure score plus a
  sample (`features.room_features` -> `score_choices` -> `sample_softmax`).
  Suggestion (`_pick_suggestion_card`) and card-to-show compute scores as
  locals fused with the sample, and suggestion draws the bluff coin from
  the character's RNG *before* scoring. Accusation is a pure threshold
  test on `best_triple(confidence_fn(belief))`, no RNG. So a small
  extraction refactor comes first, and it must leave the RNG stream
  untouched so every seeded Phase 5 game stays byte-identical.
- **Legality is defined by the engine's inputs, and nowhere enforced.**
  `choose_movement` must return one of `choices`; `choose_card_to_show`
  one of `candidates` (computed from `state.hands`, ground truth);
  suggestion names are unconstrained (any `SUSPECTS`/`WEAPONS`);
  `choose_suggestion` and `choose_accusation` may return `None`.
- **The engine has no dialogue channel.** `PlayerProtocol` is a bare
  Protocol returning actions; `run_game` returns `(GameState,
  list[GameEvent])` with four event kinds and one injectable,
  `observer`. `tests/test_engine.py` holds golden fingerprints of seeded
  games.
- **`reset`, `observe`, `n_calls`, `seconds`, `name` are duck-typed** by
  the arena, which builds characters once per run and diffs the
  counters per game. The wrapper needs the same surface.
- **Prompt-ready text exists only inside the CLI script**
  (`_describe_suggestion`, `_format_belief`, `_format_extra`,
  `_format_accusation_test`), all pure functions of an
  observation/belief/character. They get lifted into a package rather
  than copied a third time.
- **`ClueObservation` has no positions.** Board positions are public in
  Clue, but nothing an agent decides needs them; the movement menu's
  destinations and the engine-supplied current room already tell the
  LLM where it is and can go. Nothing to add in Phase 6.
- **`AgentSpec` is where the non-numeric part of a character lives**
  (`confidence_fn` set the precedent), and `build_character(name,
  profile)` is the one constructor the arena and CLI use. Personas are
  per-character and seat-locked (`docs/architecture.md`, Seats:
  "MissScarlettbot is always naive Bayes, always Scarlett").
- **Records need one more event kind.** `clude_storage/records.py`
  `event_to_json`/`event_from_json` raise on unknown kinds;
  `RECORD_VERSION = 1`.
- **`chattiness` was proposed in the pre-Phase-5 review and never
  added**; `Profile.DIALS` is five, and two tests use "chattiness" as
  their example of a rejected dial name.
- **No LLM prior art anywhere.** `rps` has no LLM code, no `.env`, no
  config module: settings are `os.getenv` with defaults, secrets resolve
  explicit value -> Secret Manager -> nothing, and tests inject doubles
  through constructors (`clude`'s `GcsStore(client=...)` is the stronger
  form). `requirements.txt` justifies each non-stdlib dependency inline
  and imports it lazily; `anthropic` joins the same way.
- **The persona must not encode the flaw twice.** `personality.py` keeps
  Mustard and White neutral on `accuse_threshold` so their wrong
  accusations are attributable to the method. A persona that *instructs*
  "accuse early" on top of Scarlett's 0.15 threshold would double-count.
  Persona prose carries voice and self-image; the numbers carry the
  behaviour.

## 3. Design

### Package: `clude_llm`

A sibling package by concern, importing `clude_core`, `clude_constraints`,
`clude_agents`; nothing below it imports it (`clude_training.arena` and
the CLI import it optionally).

| Module | Job |
|---|---|
| `menu.py` | `Option(label, action, score, note)` and `Menu(kind, options, top, allowed)`; builders `movement_menu`, `suggestion_menu`, `accusation_menu`, `show_menu`, each a pure function of the wrapped character's scoring helpers. No RNG. Capped at 12 options, best first. The same object a Phase 8 human seat will be shown. |
| `prompt.py` | `system_prompt(persona)` (persona file + the standing rules) and `user_prompt(obs, belief, character, menu, remarks)`. Takes only the seat's observation, belief, profile and confidence: hidden information is unreachable by construction. Composes `clude_agents/explain.py` (the lifted formatters). |
| `persona.py` | `Persona` loaded from `clude_llm/personas/<Suspect>.md` (voice, how you think about your numbers, habits) plus `clude_llm/personas/rules.md` (what the numbers mean, the menu contract, bluffing about your own hand is allowed, the formal reveal is the engine's to decide, speak only when you have something to say). Editable prose, no code changes to tune a voice. |
| `schema.py` | Four fixed JSON schemas, one per decision kind: `{"choice": enum of fixed labels, "say": string}`; suggestion has `suspect` and `weapon` enums. Fixed so the API's 24-hour schema compilation cache hits; the menu maps labels to options per call. |
| `backend.py` | `LLMBackend` protocol `complete(system, user, schema) -> LLMResult(text, usage, stop_reason, model, error)`. Implementations: `AnthropicBackend`, `NullBackend` (always fails), `ScriptedBackend` (canned answers for tests), `RecordingBackend(inner, path)` and `ReplayBackend(path, strict)` keyed by a hash of the request, so a recorded game replays with zero spend and a prompt change surfaces as a key miss. |
| `player.py` | `LLMCharacter(character, persona, backend, settings)` implementing `PlayerProtocol` plus the arena's duck-typed surface; `Decision` audit records; per-game call and token budget. |

### `LLMCharacter`, one decision

1. Build the menu from the wrapped `Character`'s scores. No RNG, so the
   fallback path below consumes exactly the RNG the headless character
   would.
2. Apply the leash: `allowed` = options scoring at least `(1 - leash)`
   of the best. Own-hand cards are always listed in the suggestion menu
   as bluff options, labelled as such, with the character's `bluff_rate`
   stated as a number in the prompt (the coin flip is the headless
   mechanism; discretion is the LLM's). If exactly one option remains,
   take it with no call: most refutations have one candidate, and this
   is the main cost saver.
3. Render, call the backend under the game budget.
4. Parse: valid JSON with a label in `allowed` -> that action; `say`
   becomes a remark, published with probability `chattiness`. Anything
   else (bad JSON, unknown or disallowed label, API error, timeout,
   `refusal` stop, budget exhausted) -> **fallback: call the wrapped
   `Character`'s own method** and log why. A dead backend therefore
   reproduces the headless character byte for byte, RNG stream included.
   This is a deliberate departure from the phase table's "top-scored
   action" wording: at the presets' temperatures the two coincide nearly
   always, and "NullBackend == headless twin" is a far stronger
   invariant to test and to pair against in the arena.
5. Record a `Decision` (kind, menu, label chosen, fallback reason,
   tokens, ms) for the audit trail, the arena's columns, and Phase 7.

Accusation is the high-stakes case, and per decision 2 the leash applies
to it symmetrically. The menu is `[accuse (best triple, P), pass]` with
P the character's own confidence (the DS lower bound for Peacock), and:

- `accuse` is allowed iff `P >= (1 - leash) * accuse_threshold`;
- `pass` is allowed iff `P < accuse_threshold` or `leash > 0`.

So at `leash = 0` the menu is always one option, the headless answer,
and no call is made; with any rope the LLM may jump early within the
leash or hold back above the threshold. `rules.md` tells it that a
proven envelope is not something to sit on. The arena's
wrong-accusation rate against the headless twin is the direct measure
of what this rope costs each character.

### Anthropic backend

`anthropic` SDK, `client.messages.create` with
`output_config={"format": {"type": "json_schema", ...}}`; model from
settings, default `claude-opus-5` (decision 3); Opus 5 thinks adaptively
by default, so `output_config.effort="low"` for these short picks and
`max_tokens` about 2048 to leave thinking room; `timeout` 30 s and
`max_retries` 1 rather than the SDK's 10 min and 2, since a timeout is
just a fallback; the system block carries `cache_control` (Opus 5's
512-token minimum is easily met by persona + rules; Haiku 4.5's 4096 is
not). Credentials resolve exactly as the SDK does, `ANTHROPIC_API_KEY`
or an `ant auth login` profile, with an explicit `api_key=` and a
`client=` injection point for doubles, nothing stored in the repo,
documented beside the GCS key in `docs/architecture.md`. The API
guidance also asks that Opus 5 code enable server-side refusal
fallbacks by default (`betas=["server-side-fallback-2026-07-01"]`,
`fallbacks="default"`); it is redundant given our own fallback, so it is
a settings toggle, on by default, one line to drop.

Cost. One call is roughly 1.5K cached + 1K fresh input tokens and 150
output. A 4-seat, 30-turn game with every seat an LLM is about 120
decisions, of which the single-option skip removes perhaps a third to a
half:

| Model | per call | per game, 4 LLM seats | 24-game arena |
|---|---|---|---|
| claude-opus-5 ($5/$25 per M) | ~$0.010 | $0.60-1.20 | $15-28 |
| claude-sonnet-5 ($2/$10) | ~$0.004 | $0.25-0.45 | $6-11 |
| claude-haiku-4-5 ($1/$5, no cache under 4K) | ~$0.003 | $0.15-0.30 | $4-7 |

Latency is a few seconds per call, so a fully LLM table is a 5-10 minute
headless game: fine for play, slow for sweeps. The replay backend is
what keeps the suite and re-analysis free.

### Engine and storage changes (small, `clude_core` still imports nothing)

- `clude_core/events.py`: `Remark(turn, seat, text, about)`, `about` in
  `move | suggest | accuse | show`, added to the `GameEvent` union. Phase
  8's off-turn chat reuses the type with a new `about`.
- `clude_core/engine.py`: a `runtime_checkable` `SpeakingPlayer` protocol
  with `take_remarks() -> list[str]`. After each action's event the
  engine drains the acting seat (and, after a suggestion, the refuter)
  and appends `Remark`s in order. Existing players lack the method, so
  the golden fingerprints do not move. Chosen over a wrapper-side
  transcript because replay and Phase 8's live view both want dialogue
  interleaved with actions in one ordered log.
- `clude_storage/records.py`: serialize `Remark`; `SeatRecord.kind`
  gains `"llm"` and a `model` field; `GameRecord` gains an optional
  `llm_log` (the `Decision` audit per seat); `RECORD_VERSION` -> 2 with
  `from_dict` accepting version 1.

### Dials (decision 4: Profile dials)

`leash` and `chattiness` join `Profile.DIALS` and `UNIT_DIALS` (seven
dials, all in [0, 1]), consumed only by `LLMCharacter`; the headless
`Character` ignores them, so no Phase 5 behaviour or fingerprint moves.
Each owns one wrapper decision and one arena metric, per the
keep-a-dial rule: `leash` -> deviation rate (and, through the
accusation rule, wrong-accusation rate vs the twin); `chattiness` ->
remarks per game. Presets start uniform, `leash = 0.25` and `chattiness
= 0.5` for all six, and 6d's sweep sets them; `chattiness` per character
is as much a voice choice as a tuning one, so David sets those by hand
if he prefers. `personality.py`'s dial table, the `agents` CLI listing,
`SeatRecord.profile` (via `to_dict`), and the two tests that use
"chattiness" as their unknown-dial example all update; `from_dict`
already defaults missing dials, so stored version-1 records still load.

### Arena and CLI

- `run_arena(..., llm=None)`: when given an `LLMSettings`, every
  character seat is wrapped once per run (backend shared); `PlayerStats`
  gains `llm_calls`, `fallback%`, `deviate%` (chose something other than
  the character's top option), `tok/game`, `llm ms/call`. The twin
  comparison is two arena runs on the same seeds, with and without
  `--llm`, exactly the paired design `sweep` already uses; pitting a
  character against its own twin in one table would confound it.
- `play --llm [--llm-model M] [--llm-backend anthropic|null|record:PATH|replay:PATH] [--llm-characters Plum,Scarlett]`;
  `--verbose` prints remarks inline; a trailer prints calls, fallbacks,
  tokens, and estimated cost. `arena --llm` takes the same flags.
- `prompt --seed --players --roster --viewer --at K --decision move|suggest|accuse|show`:
  prints exactly what that seat's LLM would be sent at that point, no
  call made. The prompt-iteration and fairness-review tool.

## 4. Sub-phases

Each leaves the suite green and is a working system on its own.

| | Deliverable | Check | CLI |
|---|---|---|---|
| 6a | The seam: pure scoring helpers extracted from `Character` (suggestion, card-to-show); formatters lifted into `clude_agents/explain.py`; `Remark`, `SpeakingPlayer`, record serialization and version bump | every seeded character game byte-identical before/after (a fingerprint test beside the engine goldens); records round-trip a `Remark` and read a version-1 file | `trace`/`play` output unchanged |
| 6b | `clude_llm` on fake backends only: menus, leash, schemas, parse/validate/fallback, budget, `LLMCharacter`, `Decision` audit, `Remark` emission; the two new dials | `NullBackend` game == headless game byte for byte, per character and seed; scripted illegal/disallowed/malformed/error/refusal each fall back and are logged; the reveal-integrity regression (an adversarial backend over many seeds never gets a card outside `candidates` shown, never an illegal move); one-option menus make no call; a schema is the same object across menu sizes; the LLM path draws no engine RNG | `play --llm --llm-backend null` |
| 6c | `AnthropicBackend`, six persona files and `rules.md`, `prompt` subcommand, record/replay, `CLUDE_LLM_LIVE` smoke test, `requirements.txt`; a handful of real games read and the personas iterated | live smoke returns a valid label and the second call shows `cache_read_input_tokens > 0`; a small recorded game under `tests/fixtures/` replays offline in the suite | `play --llm`, `prompt` |
| 6d | Measurement: `arena --llm` twin runs, a `leash` sweep, presets set; `docs/llm-wrapper.md`; results in `docs/strategy-glossary.md` | deviation, fallback, and remark rates per character; win rate and wrong-accusation rate vs the headless twin with binomial std at 12-24 games and 3-4 seats, reported as direction and magnitude like the Phase 5 sweeps; `leash` moves deviation rate monotonically (the keep-a-dial check) | `arena --llm`, `sweep --dial leash` |

## 5. Files

New: `clude_llm/{__init__,menu,prompt,persona,schema,backend,player}.py`,
`clude_llm/personas/{Scarlett,Plum,Peacock,Mustard,Green,White,rules}.md`,
`clude_agents/explain.py`, `tests/test_llm.py`, `tests/fixtures/`,
`docs/llm-wrapper.md`.

Touched: `clude_agents/character.py` (extract helpers),
`clude_agents/__init__.py` (persona on `AgentSpec`, `build_llm_character`),
`clude_agents/personality.py` (two new dials, presets, dial table),
`clude_core/events.py`, `clude_core/engine.py`,
`clude_storage/records.py`, `clude_training/arena.py`,
`scripts/clude_cli.py` (lift formatters, new flags, `prompt`),
`requirements.txt`, the tests beside each, and the docs:
`architecture.md` (layout, data flow, credentials), `phase-plan.md`,
`cli.md`, `strategy-glossary.md`, `README.md`, `CLAUDE.md` status.

Reused as-is: `features.room_features`/`score_choices`/`sample_softmax`,
`character.best_triple` and the two confidence functions,
`clude_constraints.observe`, `build_character`, `parse_roster`/
`lineup_for_game`/`fill_seed`, the constructor-injected double and
env-gated live test from `tests/test_storage.py`, the golden fingerprint
pattern from `tests/test_engine.py`, the tuned `PRESETS` and the
glossary's per-character narration as persona raw material.

## 6. Decisions (David, 2026-09-12)

1. **How free is the LLM?** Leashed shortlist: options within `leash` of
   the character's best, `leash` a per-character number the arena can
   sweep. (Alternatives not taken: any legal option with scores shown;
   narrator only.)
2. **Accusation authority.** Symmetric leash: the same rope on both
   sides of the tuned threshold, as specified above. (Not taken: hold
   back only; no LLM say.) Consequence to watch in 6d: any rise in a
   character's wrong-accusation rate over its headless twin is now
   attributable to the leash, not the method, and the sweep will show
   where each character's rope should be cut.
3. **Model and spend.** `claude-opus-5` default, `--llm-model` for
   cheaper arena runs.
4. **Where `leash` and `chattiness` live.** New `Profile` dials.

## 7. Out of scope for Phase 6

Off-turn chat and its pacing (Phase 8), logbooks and cross-game memory
(Phase 7; in-game the prompt sees this game's remarks only), any UI,
human seats, any change to a method or to the tuned presets, and
parallel game execution in the arena (a later speed item if LLM sweeps
ever need it). One note for Phase 8, found while surveying `rps`: its
web app streams with server-sent events, not websockets, which is a
cheaper fit for Cloud Run's idle-cost caveat; the websocket decision can
wait until then.

## 8. As implemented

### 6a, the seam (2026-09-12)

- The event type is `RemarkEvent`, not `Remark`, to match the module's
  naming (`MoveEvent`, ...). Its `about` is one of `move`, `suggest`,
  `accuse`, `show`.
- The engine drains the acting seat after *every* accusation decision,
  including a pass, so a character that says "not yet" is heard; after
  a suggestion it drains the suggester and then the refuter.
- The pure helpers are `suggestion_candidates(obs, belief, category)`,
  `cards_exposed(obs, shown_to)` and `show_scores(...)` at module level
  in `clude_agents/character.py`, plus `Character.movement_scores(obs,
  choices)` and `Character.accusation_test(obs)`. The bluff coin is
  still flipped before the honest scoring, so the RNG stream is
  unchanged: four golden fingerprints (three cheap all-pure-method
  tables and the Green/Mustard/Peacock/Plum game at seed 17), captured
  on the Phase 5 code, pass on the split code, in a fresh process.
- The formatters live in `clude_agents/explain.py`; `describe_suggestion`
  takes seat labels rather than `GameState`, and `format_mask` takes
  `n_players`, so nothing there can reach hidden state. `play --verbose`,
  `trace` and `floor` output was diffed against the pre-6a script:
  identical apart from `trace`'s elapsed-time trailer.
- `RECORD_VERSION` is 2. `SeatRecord.model` and `GameRecord.llm_log` wait
  for 6b, when there is a `Decision` to store; they will not bump the
  version again, since no version-2 records exist yet.

### 6b, the wrapper on fake backends (2026-09-12)

- Two response schemas, not four: `CHOICE_SCHEMA` serves move, accuse
  and show, `SUGGEST_SCHEMA` the suggestion. Same fixed-enum idea.
- `SpeakingPlayer` gained `hear(remark)`, not in the plan: the engine
  tells every other speaking seat each `RemarkEvent` as it appends it,
  so table talk reaches the other LLM seats' prompts without adding a
  field to `ClueObservation` (the six methods do not read remarks).
- A single-option menu makes no call, as planned, but the option is
  *not* returned directly: the wrapped character decides, so its
  temperature sampling and RNG consumption are exactly the headless
  ones. That is what makes `NullBackend` byte-identical to the twin.
- Bluff options are allowed only with `leash > 0` and `bluff_rate > 0`,
  so a leash of zero leaves the LLM no discretion anywhere and a
  character that never bluffs headless never bluffs piloted.
- Deviation is defined strictly: the played option scored below the
  character's top option (ties are not deviations); for the accusation,
  it differed from the threshold answer.
- `SeatRecord.model` and `GameRecord.llm_log` landed here, still under
  `RECORD_VERSION` 2.
- `play --llm` takes `--llm-backend` (default `anthropic`, which arrives
  in 6c; `null`, `record:PATH`, `replay:PATH` work now), `--llm-model`
  and `--llm-characters`; `--verbose` prints remarks inline and a
  trailer summarises each LLM seat. The arena's `--llm` is 6d.
- The chattiness gate draws from the wrapper's own RNG, seeded from the
  same seed as the character's, so the character's stream is untouched
  even when the LLM speaks.

### 6c, the real backend (2026-09-12; live checks done 2026-09-13)

- `AnthropicBackend` calls `client.beta.messages.create` with the
  `server-side-fallback-2026-07-01` beta and `fallbacks="default"` while
  `server_fallbacks` is on (the default), else `client.messages.create`;
  both accept `output_config` (format + effort) on SDK 1.5.0, which is
  what `requirements.txt` pins to. `thinking` is omitted: Opus 5 thinks
  adaptively by default and `effort="low"` sets the depth.
- Every SDK error is one broad catch mapped to an error result, on
  purpose: the wrapper falls back on any failure and retries nothing at
  this layer, so telling a 429 from a 500 buys nothing here; the SDK's
  own `max_retries=1` covers the transient ones.
- The `prompt` subcommand renders from the finished game's positions
  (`truncate_state` keeps them), so `--decision move` shows the menu
  text for a plausible roll, not a real turn's legal moves.
- The live smoke test passes
  (`CLUDE_LLM_LIVE=1 python -m pytest tests/test_llm.py -k live`), and
  prompt caching is real: the system block carries
  `cache_control: ephemeral`, and a recorded 4-seat game read 57.6K
  cached tokens against 68.9K fresh -- 46%, saving about $0.26 on a
  $0.43 game. Mind the arithmetic: `input_tokens` and
  `cache_read_input_tokens` are disjoint (that is why `estimate_cost`
  bills them separately at $5 and $0.50 per MTok), so the share is
  `cached / (input + cached)`. Dividing by `input` alone overstates it
  badly, and can exceed 100%.
- **The key must be workspace-scoped.** An organisation-level key fails
  every call with a 400, "not scoped to a workspace, so this request
  must include the anthropic-workspace-id header". The backend sends no
  such header by design; create the key inside a workspace instead.
- The offline fixture is `tests/fixtures/llm_seed1.json`, recorded with
  `python scripts/clude_cli.py play --seed 1 --players 3 --roster Scarlett,Peacock --llm --llm-backend record:tests/fixtures/llm_seed1.json --verbose`
  and replayed by `test_recorded_llm_game_replays_offline`.
  **The fixture is coupled to the prompt text**: `LLMRequest.key()`
  hashes the system block, so editing any persona or `rules.md`
  invalidates every key and the replay starts missing. Re-record it and
  update the transcript landmarks whenever the personas change. The
  envelope follows from the seed and holds; the winner and turn count do
  not, because the model's choices are its own and are not deterministic
  across recordings.
- Persona tuning, from two recorded games: seed 1 (3 players,
  Scarlett+Peacock, 23 turns) and seed 2 (4 players,
  Plum+Mustard+Green+White, 39 turns). Both fixtures on disk are
  *re-recordings* made after the edits below, so they are shorter and
  their transcripts differ; the observations here come from the
  originals, which the edits then invalidated.
  - Both defects were about *talk*, not choices: across all six seats
    there were no fallbacks and only five deviations, so the leash and
    the menus held.
  - **Repetition**, fixed in `rules.md` for everyone. Late in a game the
    deduction narrows and every remaining remark wants to be the same
    remark; Peacock restated a line almost verbatim three turns apart.
    The prompt already showed her the last eight remarks, so this was
    never a plumbing gap — she could see the repeat and made it anyway.
    The new paragraph tells the characters to say nothing rather than
    restate. It works: in seed 2's twenty-turn stalemate the table went
    quiet instead of looping, and the re-recorded seed 1 has no
    duplicates.
  - **Plum recited his numbers**, against `rules.md`'s "no reciting your
    numbers", in three of seven lines ("0.26 and 0.21, the two largest
    fractions on the board"). His own persona invited it: "it is a
    fraction, and you know its denominator". Fixed in `Plum.md` by
    routing the restraint through his pedantry -- quoting decimals is
    showing your working, which is what undergraduates do -- rather than
    by bolting on a second prohibition.
  - Mustard, Green and White needed no edits. Green's bandit ensemble
    surfaced unprompted as borrowing other players' reasoning ("Scarlett's
    fractions were quite persuasive, so I'll poke somewhere she hasn't"),
    and White's Markov model as reading people rather than cards
    ("Mustard's stopped fishing for the Candlestick and started asking
    about rooms"). Both are the method audible in the voice, which is
    what the personas were for. Mustard volunteered that he held a room
    he was standing in -- a real tell, in bounds under the over-sharing
    decision, and exactly the kind of thing the logbooks should punish
    later.
  - Scarlett was left alone. She explained her arithmetic once in five
    lines, which her persona already forbids; one borderline line is too
    thin to tune on.

### 6d, the arena (2026-09-12; measured 2026-09-13)

- `run_arena` takes `llm_backend`, `llm_settings` and `llm_characters`;
  the wrapped characters share one backend, get `new_game()` before
  every game, and are diffed on `LLMCharacter.summary()` per game the
  way belief calls already were. Their seats are `kind="llm"` with the
  model, and each game's `Decision` audit goes into `GameRecord.llm_log`.
  The default run id becomes `llm-<seed>-<games>`.
- Rates are defined against the right denominators: `fallback_rate` is
  fallbacks over decisions that were the model's to make (all but
  single-option menus), `deviation_rate` is deviations over choices the
  model actually played. Both are NaN when the denominator is zero, so
  a row where nothing was played shows dashes rather than a false zero.
  Note that `leash = 0` still lets the model choose among *ties* on the
  character's own score (early-game rooms, unshown cards), so its row
  can show calls, with a deviation rate of exactly zero. `sweep`'s
  metric list gained the two rates and `remarks_per_game`.
- `NullBackend` in the arena reproduces the headless run's winners and
  turn counts game for game, which is the paired-comparison guarantee
  the twin runs rest on (`tests/test_llm.py`).
- Measured on Opus 5, full tables and analysis in
  `docs/strategy-glossary.md` under "Phase 6". Total live spend for 6c
  and 6d was about $22.60 at list prices.
  - Twin run: `arena --seed 7007 --games 24 --players 4`, headless and
    `--llm`, all six characters ($6.98). No fallbacks in 807 calls. The
    results: Plum falls from 75% to 31% (about 3 sigma), because the
    LLM table ends games sooner (26.8 to 20.3 turns) and he is the
    slowest accuser. Mustard's wrong accusations drop from 37.5% to 6.2%
    and his win rate triples. LLM seats name their own cards far less
    often than the headless characters do.
  - Sweep: `sweep --dial leash --values 0 0.25 0.5 1 --llm --games 8
    --players 3` ($14.99). The first quarter of rope halves game length.
    wrong% reaches zero at 0.5. `deviation_rate` is not monotone (0.0,
    1.7, 11.1, 4.1), which fails the keep-a-dial test as posed. The
    likely cause is the metric's denominator, since played choices grow
    with the leash. This is unconfirmed, because that run saved no
    `--json`.
  - Pooled win% in that sweep is 33.3 at every value by construction.
    All seats are swept characters, so the sweep cannot show per-character
    effects.
- **Presets left at `leash` 0.25 and `chattiness` 0.5.** The pooled sweep
  favours 0.5. But it is 8 games per value, it cannot see individual
  characters, and more rope likely deepens Plum's loss. That makes it a
  design call about keeping the six methods distinct, not a tuning call.
  Open follow-up: a per-character leash sweep (`--llm-characters Plum`,
  then Mustard, at 0.25 and 0.5, with `--json`).
