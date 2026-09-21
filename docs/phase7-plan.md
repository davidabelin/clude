# Phase 7 Plan: playerbot memory, the logbooks (approved 2026-09-14)

Status: **approved 2026-09-14; 7a-7c built the same day; 7d's live
run, the debrief timeout fix, the audit and flag tuning,
`--logbook-characters`, fixed seating and the paired leash-0.5
measurement all done the same day. Phase 7 is complete.** David's answers to the three decisions are in section 6;
what was actually built, and where it departed from this plan, is in
section 8. Same
shape as `docs/phase6-plan.md`: what the code dictates, the design,
sub-phases, decisions, out of scope.

## 1. Context

Phase 7 in `docs/phase-plan.md` is "Logbooks: persistent, per-character,
written after every game". `CLAUDE.md` adds the requirements: entries
modelled on `docs/zenbot_memories.json` (date and serial, title, what
happened, evaluations, key insights, lessons learned, outcome, standing
instructions; no koans) and written by the character's own model;
human tells must persist across games independent of seat; Mustard's
tree and White's Markov model are meant to learn from stored records
("Phase 7's business"); a logbook reset control for fairness; and David
expects Plum's own post-game notes may teach him out of the parking
before `movement_scores` is changed. `docs/architecture.md` ("Seats and
player identity") already sketched two layers: an immutable per-game
entry and a mutable per-opponent dossier.

David wants this done without fuss, then a UX design pass before
Phase 8. So the design is the smallest thing that meets every
requirement, keeps every golden fingerprint and LLM fixture untouched,
and leaves the schema display-ready for the Phase 8 case-file view.

## 2. What the code dictates

- **No record-to-view reconstructor exists.** `clude_storage/records.py`
  promises a seat's redacted view is "rebuilt from `events`", but
  nothing implements it; `trace.belief_trace` and
  `self_play.truncate_state` take a live `GameState`. A record has
  everything needed (`seats`, `hands`, `envelope`, ordered `events`),
  but `positions` and `active` must be folded from `MoveEvent`s and
  `AccusationEvent`s. This is the one piece every tier of memory needs.
- **The store is closed over two document kinds.** `RecordStore`
  (`clude_storage/stores.py`) has `put/get/list` for games and runs
  only; no generic key access, no delete. Logbooks need a third
  namespace.
- **`play` cannot persist a game.** `--store` exists only on `arena`
  and `sweep`; `cmd_play` drops `state, events`. The only post-game
  hook anywhere is the arena's `observe(RevealedOutcome)` loop, which
  runs *before* the `GameRecord` is built.
- **Mustard** (`clude_agents/decision_tree.py`): rows are built only in
  `_generate_training_rows` from `generate_snapshots`; `_features(obs,
  mask, card, category)` and `_build_tree(rows, ...)` take bare data,
  so rows from any masked observation plus its envelope can be
  appended. `reset` never retrains; two module caches key on the
  training settings.
- **White** (`clude_agents/markov.py`): the repeat/new chain is refit
  per call from four Laplace cells (`_PRIOR = 1.0`) per opponent, keyed
  by seat index. Seeding per-identity counts is a small change, but
  needs a seat-to-identity map at game start, which nothing provides.
- **Green** (`clude_agents/bandit.py`): posteriors persist within an
  arena run only; `reset` rebuilds the arms to Beta(1,1); no codec.
- **Goldens.** Mustard sits in three of the four pinned character games
  and Green in one (`tests/test_character.py`), so any memory must be
  explicitly off in fixtures and change nothing when off. CLI logbooks
  remain opt-in; new web tables default to remembering since 2026-09-21.
- **The LLM side.** `LLMRequest.key()` hashes system, user and schema
  (not `kind`); the system prompt is built once per character and is
  both the API cache key and the fixture key. `AnthropicBackend.params`
  sends one cached system block, and a test pins that dict.
  `schema_for`/`parse_response` index `LABEL_FIELDS[kind]` and need a
  branch for a new kind. Effort and `max_tokens` live on the backend
  instance, not the request. `LLMCharacter` has `new_game()` but no
  end-of-game method; it holds `decisions`, `transcript`, `persona`,
  `backend`, `settings`.
- **Dials.** `Profile` is `DIALS` + `UNIT_DIALS` + one field with a
  default; `to_dict`/`from_dict` and the existing dial tests already
  tolerate a new name, and `--set` and `sweep --dial` work for any name
  in `DIALS`.
- **Identity.** `SeatRecord.label` is the roster label ("Plum",
  "floor"); Phase 8 is expected to extend it with a human's display
  name rather than replace it. It is the natural identity key for both
  a character's own logbook and the opponents it writes about.

## 3. Design: three tiers of memory and one dial

```
Tier 0  the record      GameRecord in the store (exists)            omniscient, immutable
Tier 1  method memory   numeric, per method, headless, no LLM       logbooks/<id>/method.json
Tier 2  narrative       zenbot-shaped entries + a rolling head,     logbooks/<id>/entries/NNNN.json
        memory          written and read by the character's model   logbooks/<id>/head.json
```

One `Logbook` per identity, living beside the records in the same
store (`data/llm/logbooks/Plum/...` or the bucket), keyed by
`SeatRecord.label`. A character's logbook is its own whichever token it
plays; opponents are keyed by their labels, so a human's display name
(Phase 8) gets a dossier that follows them across seats with no further
work. "Each character writes to its logbook after every game" means:
Tier 1 updates on every game played with memory on (headless or not);
Tier 2 is written only by an LLM-piloted seat, since it needs a model.

Three characters (Scarlett, Plum, Peacock) have memoryless methods by
construction: their memory is Tier 2 only.

A new `Profile` dial, **`memory`** in [0, 1], default 0 for everyone,
sets how much of its own logbook an LLM-piloted character reads before
a game (Tier 2 read-back, below). Tier 1 is not gated by the dial: a
logbook is either on or off for a run.

### Tier 0 additions

- `clude_training/replay.py`: `state_from_record(record, k=None) ->
  GameState` (freeze hands, fold `positions` from moves and `active`
  from accusations, cut to the first `k` suggestions via
  `self_play.truncate_state`) and `seat_view(record, seat, k=None) ->
  ClueObservation` through `clude_constraints.observe`. Also what
  Phase 8's post-game replay of six belief traces will use.
- `RecordStore` gains four generic methods, `put_doc(key, doc)`,
  `get_doc(key)`, `list_keys(prefix)`, `delete_doc(key)`, on both
  `LocalStore` and `GcsStore`; the existing six stay as they are.
- `play --store URI [--run-id]` builds and stores a `GameRecord` for a
  single game (default run id `play-<seed>-<timestamp>`), so a game
  played from the CLI can leave memory.

### Tier 1: method memory (`clude_training/memory.py` + per-method hooks)

Per-method hooks stay in each method's module (one module per method):

- **Mustard**: `rows_from_view(obs, envelope)` factored out of
  `_generate_training_rows`; `DecisionTreeAgent(extra_rows=...)`
  appends them to the base 25-game rows before training. Memory file:
  `{"games": {game_id: [[f1..f8, label], ...]}}`, one block per stored
  game at the default checkpoints (0.5, 1.0), every seat's view. Keyed
  by game id so incremental updates and rebuilds are idempotent.
- **White**: `repeat_transitions(suggestion_log, viewer) -> {seat:
  counts}` factored out of `select_action`; `MarkovAgent(priors=...)`
  adds per-identity counts to the four Laplace cells; `set_table(labels)`
  maps seat index to identity for the current game. Memory file:
  `{"games": {game_id: {label: {"00": n, "01": n, "10": n, "11": n}}}}`,
  summed per opponent label at load. His "reads people" method becomes
  literally true across games.
- **Green**: `state_dict()` / `load_state()` for the five arms'
  `(alpha, beta)`; loaded after `reset`, saved after every game. Memory
  file: `{"arms": {name: [alpha, beta]}, "games": n}`.
- `Character.new_game(table=None)` forwards the table to the agent when
  it has `set_table` (only White); `LLMCharacter.new_game(table)` calls
  it. The arena calls `new_game(lineup)` on every character before each
  game (today only LLM seats get `new_game()`).
- `clude_training/memory.py` is the glue that knows both records and
  methods: `load_into(character, logbook)`, `update(logbook, record,
  seat)`, `rebuild(logbook, store)` (recompute the memory file from
  every record in a store; the bootstrap from the ~200 games already in
  `data/llm`, and the recovery path).

Determinism becomes "per seed and logbook state"; with no logbook,
nothing changes and every golden holds.

### Tier 2: narrative memory (`clude_storage/logbooks.py` + `clude_llm/logbook.py`)

**The entry** (zenbot minus koans; "model" = written by the model, the
rest computed by code from the record):

| field | source | zenbot field |
|---|---|---|
| `identity`, `serial`, `date`, `game_id`, `token`, `table`, `model` | code | date, serial_number |
| `outcome` (winner, won, turns, accused, correct, envelope) | code | final_outcome (the facts) |
| `title` | model | title |
| `summary` (one or two sentences, at most about 40 words) | model | new: the entry's own precis, read at depth >= 0.5 |
| `flags` (2-6 short lowercase keywords, reused across entries) | model | new: what connects entries |
| `what_happened` | model | user_problem_or_questions + response_summary |
| `evaluations` [{opponent, evaluation, notes}] | model | session_evaluations |
| `key_insights`, `lessons_learned` | model | same |
| `final_outcome` | model | same, in the character's words |
| `standing_instructions` | model | user_instructions, as notes to self |
| `dossiers` [{opponent, read}] | model | the architecture doc's layer 2 |

Entries are immutable, one file per game, `entries/0012.json`.

**The head** (`head.json`, mutable): `serial`, a computed `tally`
(games with an entry, won, wrong accusations, never accused),
`standing_instructions` (the last entry's list, whole), `dossiers`
`{label: {read, games_together, updated}}` where only the opponents
present at the last game were rewritten and the rest carry forward
untouched, and a computed `flags` index `{flag: [serials]}`. Bounds:
at most 8 standing instructions, each about a sentence; a read at most
about 60 words; the model is told the bounds and code truncates
defensively.

**The debrief call** (`clude_llm/logbook.py`), made once per LLM seat
after the game, before `new_game()` so it lands in that game's budget
and audit:

- System prompt: the character's existing persona + rules block,
  unchanged, so the API cache hits and no fixture key moves.
- User prompt: the table (labels and tokens), its hand, the suggestion
  log as the seat saw it (`explain.describe_suggestion`), the table
  talk with its own lines marked, its own decision audit in compact
  form (turn, decision, options offered, what it chose, deviations and
  fallbacks flagged), the outcome (winner, turns, envelope, its own
  accusation and verdict), its final belief against the truth, the
  whole deal face-up (every hand; decision 1), its prior head, the
  index of its earlier entries (summary and flags each, so flags get
  reused and entries connect), and the instructions: write the entry;
  rewrite your standing instructions carrying forward what still
  holds; rewrite your read on each opponent present. `rules.md` is not
  edited (that would invalidate both fixtures); the framing lives in
  the debrief prompt and in the header of the memory block.
- Schema: a third fixed schema, `LOGBOOK_SCHEMA`, the model-written
  fields only (`maxItems` on the lists), so the API's schema cache
  hits. `schema_for` / `parse_response` gain a `"logbook"` branch.
- Settings: `LLMRequest` gains optional `effort` and `max_tokens` (not
  hashed, so no key changes); the debrief uses effort `medium` and
  4096 tokens, decisions keep `low`/2048. `LLMSettings` gains
  `debrief: bool = True`, `debrief_effort`, `debrief_max_tokens`.
- Failure handling as for decisions: any error, refusal or malformed
  reply means no entry, a logged reason, the game unaffected. Tier 1
  still updates.
- Recorded and replayed by `RecordingBackend`/`ReplayBackend`
  unchanged (`kind="logbook"`).

**Read-back: the `memory` dial.** Before each game
`LLMCharacter.new_game(table)` renders one memory block from the head
and entries, by depth `m = profile.memory` over `n` entries:

| `memory` | what the character reads |
|---|---|
| 0 (default) | the head: tally, standing instructions, dossiers for the opponents present |
| 0 < m <= 0.5 | the head, plus an index of the most recent `ceil(n * m / 0.5)` entries, one line each (serial, date, token, opponents, outcome, `summary`, `flags`), headed by the recurring flags with counts; at 0.5 the whole index |
| 0.5 < m <= 1 | the head and the whole index, plus the most recent `ceil(n * (m - 0.5) / 0.5)` entries in full (every model-written field except the superseded standing instructions and dossiers); at 0.75 the most recent half, at 1 every entry |

This interpolates David's four anchor points (0 head, 0.5 all
summaries and flags, 0.75 the most recent full entries, 1 the entire
logbook); it is monotone in `m`, so the dial is sweepable.

The block travels as a **second cached system block**, not in the user
prompt: `LLMRequest.memory: str = ""`, appended by
`AnthropicBackend.params` as a second `system` text block with its own
`cache_control` only when non-empty, and hashed into
`LLMRequest.key()` only when non-empty. So an empty logbook leaves the
request, the pinned backend test and both fixtures byte-identical,
while a full logbook at depth 1 (perhaps 10-15K tokens after twenty
games) is written to the cache once per game and read at a tenth of
the price on every call after. In the user prompt the same block would
be fresh tokens on every call, about ten times the cost at high depth;
the persona+rules block stays the cross-game cache prefix underneath.
`prompt` prints the memory block as a third part. `ScriptedBackend`
records it like the rest of the request.

Keep-a-dial: `memory` should move tokens per game monotonically
(trivially true) and, the interesting question, win rate or wrong
accusations against depth. A fair sweep needs the same logbook at
every value and no writes during it, so `--logbook-readonly` (no
debriefs, no Tier 1 updates) joins `--logbook`, and `sweep --dial
memory --llm --logbook URI --logbook-readonly` is the test. Not run in
Phase 7; the mechanism is what Phase 7 delivers.

**One honest limit.** The logbook can only steer the model among
*allowed* options; it never widens the menu. Plum's escape from a
cleared room is allowed only at leash >= 0.34 (glossary,
"Per-character leash ladders"), so at the preset 0.25 his notes cannot
unpark him whatever they say. Testing David's hypothesis needs a
paired run at leash 0.5 with the logbook on and off (24 games, about
$10-13 with debriefs); that is a 7d option to price and ask about, not
a default.

### Wiring

- `run_arena(..., logbooks=None, logbooks_readonly=False)`: with a
  logbook store, build each character, `reset`, then
  `memory.load_into`; call `new_game(lineup)` on every character before
  each game; after each game build the `GameRecord` (whenever `store`
  or `logbooks` is set), `memory.update` for every seated character,
  `debrief` for LLM seats, save heads and entries. The LLM table gains
  `entries` (written) and the debrief's tokens fold into `tok/g`.
- `play --logbook [URI] [--logbook-readonly]`, `arena` likewise,
  `sweep` only with `--logbook-readonly` (memory carrying across a
  sweep's legs would break its paired design). URI defaults to
  `--store`'s.
- `logbook` subcommand: `list [--uri]`, `show --identity X [--entry N
  | --head | --method | --memory DEPTH]` (the last renders exactly the
  block a character at that depth would read), `reset --identity X
  [--keep-entries]`, `rebuild --identity X --from URI` (Tier 1 from
  records; the head and flag index from the entries).
- `agents` lists `memory` with the other dials; the dial table in
  `personality.py` gains its row.
- Cost line in `play --llm` and the arena footer includes debriefs.

### Cost

Debrief input is about 1.5K cached (system) plus 3-5K fresh (the
face-up deal and the entry index add to it); output 0.9-1.3K plus
thinking at medium effort. At Opus 5 list prices about $0.06-0.12 per
LLM seat-game on top of the $0.07-0.11 (Plum $0.25) measured in Phase
6. Read-back at `memory` 0 is a few hundred cached tokens per call,
near zero; at depth 1 with twenty entries roughly $0.15-0.20 per
seat-game (one cache write, then cached reads). The 7d live check is
one 3-seat, 6-game run with one LLM seat: $1.50-3.00. No other spend
in Phase 7 without a yes.

## 4. Sub-phases

Each leaves the suite green and works on its own.

| | Deliverable | Check | CLI |
|---|---|---|---|
| 7a | Tier 0: `clude_training/replay.py`; generic doc methods on both stores; `clude_storage/logbooks.py` (`LogbookEntry`, `LogbookHead`, `Logbook`, the flag index, the depth renderer as pure text); `play --store`; the `memory` dial on `Profile` | `state_from_record` reproduces a live game's `GameState` field for field and `seat_view` equals `clude_constraints.observe` for every seat and k; head/entry/method round trip on `LocalStore` and the GCS double; reset with and without entries; serials increase; the depth renderer hits David's four anchors and is monotone in length; the dial round-trips and old records load | `play --store`, `logbook list/show/reset` |
| 7b | Tier 1: the three method hooks, `Character.new_game(table)`, `clude_training/memory.py`, arena and `play` wiring, `--logbook-readonly`, `logbook rebuild` | rows from a replayed record equal rows from `generate_snapshots` on the same seeded game; the default tree and all goldens unchanged; White's seeded counts move `repeat_probability` the expected way and `set_table` is a no-op without a logbook; Green round-trips and survives `reset`; `rebuild` twice is idempotent; read-only writes nothing; same seed + same logbook state gives the same game | `play/arena --logbook`, `logbook rebuild` |
| 7c | Tier 2: `LOGBOOK_SCHEMA`, `LLMRequest` memory/effort/max_tokens and the second system block, `clude_llm/logbook.py` (debrief prompt, parse, write), `LLMCharacter.debrief` and `new_game(table)` rendering the block at the dial's depth, arena/play wiring, the LLM table column, `prompt` printing the block | a `ScriptedBackend` debrief writes an entry with the computed fields right, indexes its flags, and rewrites only the present opponents' dossiers; the next game's request carries the block at the right depth; an empty logbook leaves `LLMRequest.key()`, the pinned backend params and both fixtures byte-identical (zero fallbacks); a malformed or failed debrief leaves no entry and does not change the game; the debrief request records and replays; the debrief draws no character RNG | `play --llm --logbook`, `logbook show --memory` |
| 7d | One live run (with a yes), the entries read, the debrief prompt tuned; `docs/logbooks.md`; docs and `CLAUDE.md` updated | entries read as the character in its persona's voice, summaries are precis not repeats, flags recur across entries, standing instructions are specific and bounded, dossiers name real tells verified against the face-up deal | |

## 5. Files

New: `clude_training/replay.py`, `clude_training/memory.py`,
`clude_storage/logbooks.py`, `clude_llm/logbook.py`,
`tests/test_replay.py`, `tests/test_logbooks.py`, `docs/logbooks.md`.

Touched: `clude_storage/stores.py`, `clude_storage/__init__.py`,
`clude_agents/personality.py`, `clude_agents/decision_tree.py`,
`clude_agents/markov.py`, `clude_agents/bandit.py`,
`clude_agents/character.py`, `clude_llm/schema.py`,
`clude_llm/backend.py`, `clude_llm/anthropic_backend.py`,
`clude_llm/player.py`, `clude_training/arena.py`,
`clude_training/sweep.py`, `scripts/clude_cli.py`, the tests beside
each, and the docs: `architecture.md`, `cli.md`, `phase-plan.md`,
`strategy-glossary.md`, `llm-wrapper.md`, `README.md`, `CLAUDE.md`.

Reused as-is: `self_play.truncate_state`, `clude_constraints.observe`,
`explain.describe_suggestion`/`format_belief`,
`decision_tree._features` and `_build_tree`,
`markov._stationary_repeat_probability`, the
`RecordingBackend`/`ReplayBackend` pair, `ScriptedBackend`, the GCS
in-memory double in `tests/test_storage.py`, the golden-fingerprint
pattern, `arena.lineup_for_game`/`fill_seed`, `estimate_cost`,
`Profile.with_dials`/`--set`/`sweep --dial` for the new dial.

## 6. Decisions (David, 2026-09-14)

1. **What the debrief may see: the whole deal face-up.** Every hand and
   the envelope, a post-mortem with cards on the table. It cannot leak
   into the next game (a fresh deal) and lets a dossier verify a tell.
   (Not taken: only the envelope and what the seat saw.)
2. **Tier 1 scope: all three.** Mustard from records, White's
   per-identity priors, Green's persisted posteriors. (Not taken:
   Mustard and White only; narrative memory only.)
3. **Read-back is a dial, `memory`.** 1 loads the entire logbook, 0.75
   only the most recent full entries, 0.5 every entry's summary and
   flags but no full records, 0 the head only (default). Each entry
   carries its own brief summary and a set of flags shared across
   entries that connect them. The interpolation between those anchors
   (section 3) is the implementer's and can be adjusted.

Assumptions made unless David says otherwise: the debrief is written
by the same model and backend as the in-game decisions and always sees
the head plus the entry index whatever the dial says; Mustard learns
from every stored game's every seat, not only games he sat in;
headless characters' games count for Tier 1 but write no entry;
entries live in the logbook store and reference the record by game id
(no `RECORD_VERSION` bump); `rules.md` and the personas are not edited
in Phase 7; nothing is done about the parking mechanism; the six
presets all start `memory` at 0.

## 7. Out of scope for Phase 7

Off-turn chat, any UI, human seats (Phase 8; the identity key is ready
for them), any change to `movement_scores` or the other presets, any
change to a method's core algorithm beyond the memory seams above, the
`memory` sweep itself and any measurement run at ladder scale (the
leash-0.5 learning run is priced above as an option, not planned).

## 8. As implemented

### 7a, Tier 0 and the documents (2026-09-14)

- `clude_training/replay.py`: `state_from_record(record, k=None)`,
  `seat_view(record, seat, k=None)` and `snapshots_from_record(record,
  checkpoints)`. The fold has one step the plan did not name: a
  `SuggestionEvent` moves the named suspect's token into the room with
  no `MoveEvent` of its own (`engine.resolve_suggestion`), so the
  replay applies that too, in event order. `tests/test_replay.py`
  checks the rebuilt `GameState` field for field against the live one
  on FloorBot and RandomBot games (the latter for eliminations and
  token drags), every seat's view at every `k` against
  `clude_constraints.observe(truncate_state(...))`, and the snapshots
  against `generate_snapshots` on the same seeded game.
- `RecordStore` gained `put_doc`, `get_doc`, `delete_doc`, `list_docs`
  and `list_folders` (five, not four: listing sub-folders is how
  identities are discovered under `logbooks/`), with `validate_key` and
  `validate_prefix` reusing the run-id segment rule. Both backends
  implement them; the GCS double gained `delete`.
- `clude_storage/logbooks.py`: `LogbookEntry` (`build` computes the
  facts from the record and normalises the model's JSON: flags
  lower-cased and hyphenated, lists cleaned and capped, evaluations
  and dossiers kept only for opponents who were at the table),
  `LogbookHead` (`absorb`: tally, standing instructions, dossiers of
  the opponents present, flag index), `Dossier`, `Logbook` over a store
  (`add_entry`, `reset(keep_entries)`, `rebuild_head`, `method` /
  `save_method`, `memory(depth, opponents)`), `render_memory` with
  `memory_counts` (the depth ladder; float noise guarded so 0.3 of 10
  entries is 6, not 7), `render_entry`, `list_logbooks`. Two choices
  made here: an entry whose standing instructions are empty leaves the
  previous list standing (an empty list reads as a lapse, not a
  clearing), and an opponent present but not written about still gets
  a dossier with an empty read so `games_together` stays right.
- The `memory` dial: `DIALS`, `UNIT_DIALS`, `Profile.memory = 0.0`, a
  row in the dial table. No preset changed; stored records now carry
  eight dials and older ones load with the default.
- `play --store URI [--run-id]` writes the record as game 0 of a run
  and a one-game run summary in the arena's shape (without it `store`
  could not list the run). Default run id `play-<seed>-<UTC stamp>`.
- `logbook list | show | reset` on the CLI. `show` prints the head and
  an index by default, `--entry N` one entry (`--raw` for JSON),
  `--memory DEPTH` exactly the block a character at that depth reads.
- Suite: 227 passed, 2 skipped; every golden and both LLM fixtures
  untouched.

### 7b, method memory (2026-09-14)

- The hooks, one per module: `decision_tree.rows_from_view` (the row
  builder, now shared by self-play training and memory) and
  `DecisionTreeAgent(extra_rows=...)` / `set_extra_rows` / `n_extra_rows`
  (a tree with memory is built per agent; no extra rows means the
  cached default, so nothing moves when memory is off);
  `markov.transition_counts`, `prior_cells`, `suggestion_patterns` (the
  per-seat loop lifted out of `select_action`), and
  `MarkovAgent(priors=..., prior_mass=PRIOR_MASS)` with `set_priors` /
  `set_table`; `BanditAgent.state_dict` / `load_state`.
- White's prior is a *replacement at equal mass*, not an addition: a
  remembered opponent's transition frequencies (one phantom count per
  cell) are spread over `PRIOR_MASS = 4` pseudo-counts, the Laplace
  prior's own total, so the live sequence weighs exactly as before and
  only the chain's starting shape is informed. This is deliberate: a
  hundred games of history should not drown the regime he is watching
  now. `prior_mass` is there if that judgement changes.
- `Character.new_game(table=None)` and `LLMCharacter.new_game(table)`;
  the arena now calls `new_game(lineup)` on every character before
  every game (it used to call it on LLM seats only), which draws no
  RNG, so every golden held.
- `clude_training/memory.py`: `mustard_rows`, `white_counts`,
  `empty_memory`, `absorb`, `extra_rows`, `priors`, `load_into`,
  `update`, `rebuild`, `describe_memory`, `MEMORY_KINDS`. Documents are
  ``{"version", "kind": rows|counts|state, "games": {...}}``, keyed by
  game id, so an incremental update and a rebuild agree and re-absorbing
  a game is a no-op. Green's document is his live `state_dict`, saved
  after every game; `rebuild` refuses his kind, since no record holds
  what his arms predicted.
- The arena reloads a character's memory before the next game only when
  its document changed (a `stale` set), so a read-only run retrains
  nothing. `run_arena(logbook_store=..., logbooks_readonly=...)`,
  `ArenaResult.memory` in the summary, `sweep_dial(logbook_store=...)`
  always read-only.
- CLI: `--logbook [URI]` and `--logbook-readonly` on `play` and
  `arena`, `--logbook [URI]` on `sweep` (read-only by construction),
  `logbook rebuild --identity X [--from URI]`, `train-mustard --logbook
  URI`, and `logbook list`/`show` describing the method memory.
- Checked on the real store: `logbook rebuild --uri data/llm` absorbed
  the 193 stored ladder games in 3 s (Mustard 10,703 rows; White 902 /
  985 / 1,211 transitions for Green / Mustard / Plum). Training
  Mustard on base plus memory takes 1.9 s, so per-game retraining in
  the arena is cheap. On 8 held-out FloorBot games (noisy) memory
  improves his mid-game log-loss (1.50 to 1.15) and Brier (0.0895 to
  0.0824) and worsens the end checkpoint (log-loss 0.11 to 0.15, top-1
  0.99 to 0.94): the tree now pattern-matches three-seat character
  games rather than FloorBot self-play, which is the character.
- Suite: 238 passed, 2 skipped; goldens and fixtures untouched.

### 7c, narrative memory (2026-09-14)

- `LLMRequest` gained `memory`, `effort` and `max_tokens`. `key()`
  hashes `memory` only when it is non-empty, so every recording made
  before logbooks existed still replays; `effort` and `max_tokens` are
  never hashed. `RecordingBackend` stores the block once per digest in
  its `systems` map, since it repeats on every call of a game.
- `AnthropicBackend.params` sends the block as a second `system` text
  block with its own `cache_control`, and honours a request's `effort`
  and `max_tokens` over its own. With no block the call is byte for
  byte the Phase 6 one, which the pinned backend test still checks.
- `LOGBOOK_SCHEMA` is the third fixed schema (`schema_for("logbook")`,
  `parse_response("logbook", ...)` passes the object through). It has
  **no `maxItems`**, against the plan: structured outputs support only
  a subset of JSON Schema and the bounds are enforced by
  `LogbookEntry.build` anyway, so the prompt states them and the code
  clips.
- `clude_llm/logbook.py`: `debrief_prompt` (outcome and envelope, the
  hand, the deal face up, the suggestions as the seat saw them, the
  table talk with the seat's own lines marked, the decisions put to
  the model with deviations and fallbacks marked, the final belief
  against the truth, the head, the entry index with flags, the flag
  counts, and the field instructions with the bounds);
  `resolve_opponents`, not in the plan: the model may call an opponent
  "Mrs. Peacock", "the Mustard token" or `P2 White (Green)`, and the
  entry keys dossiers by roster label, so every alias of every other
  seat (label, display name, token, token's display name, seat label)
  is mapped before `build`. It imports `clude_training.replay` for the
  seat's live view; the arena sits above both, so there is no cycle.
- `LLMCharacter.attach_logbook`, `read_back` (the block at
  `profile.memory` with the dossiers of the opponents at the table,
  every dossier when no table is known), `debrief(record, seat)`
  (`last_debrief` carries the reason when no entry is written, as a
  decision's fallback would), `entries_written` in `summary()`;
  `new_game(table)` re-renders the block. The debrief draws no
  character RNG.
- `LLMSettings.debrief`, `debrief_effort = "medium"`,
  `debrief_max_tokens = 4096`.
- The arena's per-game block was restructured so the debrief runs
  before the per-game LLM stats are sliced: the seats and the record
  are built first, then method memory and debriefs, then the stats.
  `PlayerStats.llm_entries`, an `entries` column in the LLM table,
  `"entries"` in `LLM_SUMMARY_KEYS`.
- CLI: `play --llm --logbook` debriefs each LLM seat and prints the
  entry's serial and title (or why none was written); the record and
  logbook writes now come before the LLM trailer so the cost line
  includes the debrief. `prompt --logbook URI [--memory DEPTH]` prints
  the memory block as a third part.
- `tests/test_debrief.py`: the schema; the key and the backend params
  moving only with a block; recording and replay of the block; the
  read-back at 0 and 0.5 riding every decision and an empty logbook
  leaving the request key identical to a wrapper without one; alias
  resolution; a scripted debrief writing an entry (computed fields,
  resolved opponents, head, flags, tokens, no RNG) and the second
  debrief seeing the head, index and flag counts; every failure mode
  writing nothing; the arena debriefing LLM seats, reading the logbook
  back in game two, and writing nothing read-only.
- Suite: 246 passed, 2 skipped; every golden and both fixtures
  untouched.

### 7d, the live run and what it changed (2026-09-14)

- **The smoke run wrote nothing.** `arena --games 6 --players 3 --roster
  Plum,Mustard,Green --seed 7007 --llm --llm-characters Plum --store
  data/llm --logbook data/llm --run-id logbook-smoke`: 760 s, $1.56, and
  `entries 0`. Every debrief timed out at the wrapper's 30 s call
  timeout, and the SDK's one retry made that 62 s of nothing per game.
  Fix: `LLMRequest.timeout`, `LLMSettings.debrief_timeout = 180`, passed
  per call by `AnthropicBackend.complete` as a call option (not a param,
  so the pinned params test holds). The six stored games were then
  debriefed from their records with a scratch script that rebuilds the
  `Decision`s from `llm_log`: 33-48 s and $0.06-0.11 each. That logbook
  is kept at `data/llm-smoke` (rotating seats, leash 0.25, the prompt
  before the tuning below).
- **What the entries showed.** Persona voice throughout; summaries are
  precis; tells are checked against the face-up deal ("he accused the
  Study while holding the Study"); eight specific standing instructions
  by entry 2. By entry 3 ("Thirty Turns in the Conservatory") Plum names
  the repetition trap himself and writes the instruction to move when
  his move and suggestion repeat, although at leash 0.25 the escape was
  never on his menu (`parking_report.py`: no allowed escape in his
  83-turn game), which is the limit recorded in 7c. Flags were spent on
  the table and the result ("three-handed", "large-hand", "won"/"lost"
  on every entry).
- **Prompt tuning, two changes.** The decision audit is grouped by kind,
  carries the note the menu showed beside the chosen option, and
  collapses a run of one decision into one line ("turns 28-98, 37 times
  running"), so a stall reads as a stall and the character sees
  "P(envelope room = Ballroom) 0.00" beside his own choice; what he said
  is no longer repeated from the table talk. The flags instruction asks
  for patterns of play, not the result or the table size. `logbook show
  --entry` now prints the standing instructions and dossiers an entry
  wrote (`render_entry(full=True)`).
- **`--logbook-characters`** on `play`, `arena` and `sweep`
  (`run_arena(logbook_characters=...)`, `ArenaResult.memory
  ["characters"]`): only the named characters get a logbook, so one
  character's memory can be measured with the rest of the table exactly
  as it plays without memory.
- **Fixed seating, mid-run** (David: "No more characters moving their
  seats"; "Plum must never play Scarlett's seat"): `seat_lineup`, the
  engine's `suspects`, `ClueObservation.suspects`; recorded in
  `CLAUDE.md` and `docs/architecture.md`. Every character golden was
  re-captured and both LLM fixtures re-recorded ($0.32). It also meant
  the paired leash-0.5 run needed both legs fresh, since the ladder's
  leash-0.5 leg rotated seats.
- **The measurement** (`docs/strategy-glossary.md`, "Plum's logbook at
  leash 0.5"): 24 paired games, Plum alone with Claude at leash 0.5
  and `memory` 0, logbook on (Plum only, from empty) against off.
  His stalls fall from 97 to 40 over the run and from 37 to 3 in the
  last quarter on the same deals, games with a long stall from 8 to
  2, games five turns shorter; the price is two wrong accusations at
  P 0.50 and 0.80 inside the leash window, so wins are a wash (net
  -1). Deviations per decision 5.2% to 8.8%. Debriefs $0.093 and 42 s
  each, $2.24 for the leg. Every entry parsed; no fallbacks. The 7d
  check list holds: persona voice, precis summaries, recurring flags,
  bounded and specific standing instructions, dossiers verified
  against the deal.
- Spend for 7d: smoke $1.56, six retro-debriefs $0.53, fixtures $0.32,
  the two legs $4.63 and $5.56; about $12.60 in all.
