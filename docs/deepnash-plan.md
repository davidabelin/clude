# Phase 12, a new Plum: PlumOG mothballed, Plum rebuilt on a DeepNash variant

Status: **proposed 2026-10-05; N2 and N3 built the same day** (section
10), on David's word "Call it Phase 12, go ahead with N2 and N3". His
four answers of that day are in section 7. N1's logbook commands, N4
training and N5-N7 are not started. (Phase 11 is the release, and this
work is meant to land before it closes.)

## 1. Context

David's brief (2026-10-05): mothball Plum and his enumeration agent,
logbooks included; that Plum is **PlumOG** from now on, set aside. Build
a **new Plum**, set up exactly as PlumOG was, with the same personality
settings and the same LLM head, except that the headless agent uses
DeepNash or a suitable variant. Identify the settings the change
invalidates (`leash` first) and propose the best way to re-measure them.

Why the method was due for replacement, from the record
(`docs/strategy-glossary.md`, "Re-measurement on the Classic board"):

- On the Classic grid the exact search exhausts its node budget in 490
  of 1,080 benchmark calls, so his mid-game numbers are the sampling
  fallback's noise: log-loss 1.44 at the 50% checkpoint against
  uniform's 1.35, "worse than ignorance mid-game". Ten times the nodes
  takes the fallbacks only to 384. The glossary's own verdict: "an
  algorithm change, not a budget".
- He is the slowest seat (0.67-1.1 s a call), the dearest with Claude
  (about $0.25 a seat-game against $0.07-0.11), and Green inherits both
  through his `"Plum"` arm: a four-character table with Green runs
  7.5 s a game against 0.03 s without him (measured 2026-10-05).

What stays: Plum's token, his persona's voice, his dials (section 5
says which keep their meaning), his place at every table and in Green's
ensemble, the wrapper and the logbook system around him.

## 2. What the code dictates

- **The contract between a method and its character** is
  `ClueBelief.probabilities`, 21 cards summing to 1 within each category
  through `mask_and_normalize`, plus the one action a method owns,
  `choose_destination` (`clude_agents/base.py`). Suggestion, accusation
  and card-to-show belong to `Character`, scored from the belief and the
  dials (`clude_agents/character.py`).
- **The LLM menus are built from the Character's pure scores**, not the
  agent's pick: `movement_scores` is the curiosity blend of the shared
  room features, `suggestion_candidates` the belief per card, and
  `within_leash` keeps every option scoring at least `(1 - leash)` of the
  best (`clude_llm/menu.py`). An agent that chooses its destination its
  own way is invisible to the menu; `character.py`'s docstring admits
  it. A learned policy makes that gap matter: the leash must bind to the
  numbers Plum plays by.
- **One string, `"Plum"`**, is the suspect token, the registry key, the
  agent's `name`, the preset key, the persona file, the roster label,
  `SeatRecord.label` and the logbook identity. The seat lock requires
  label == token (`clude_training/table.py`, `arena.seat_lineup`). So
  the new method takes the key `"Plum"`, and PlumOG gets none (section
  7, his first answer).
- **Green's arms are hard-coded** (`clude_agents/bandit.py`,
  `"Plum": ExactEnumAgent()`), his posteriors keyed by arm name in his
  `method.json`. A new method under the same arm name silently inherits
  the old posterior unless it is reset.
- **`explain.format_extra`** renders `extra["method"]` in `{"exact",
  "sampled"}` as Plum's search diagnostics; the benchmark and the CLI
  count `"sampled"` as his fallback.
- **The wiki pins the old module**: `clude_web/wiki/facts.py` imports
  `ExactEnumAgent`, `_Search` and the two budgets and asserts
  `extra["method"] == "exact"` for the Rope question; `figures.py` draws
  the search. All of that keeps working against the archived module.
- **`clude_agents` runs on the standard library alone today**
  (`bandit.py` avoids numpy on purpose). David's second answer admits
  numpy for the forward pass; torch stays a developer dependency.
- **Headless speed**: a floor-bot game is 0.03 s, and a four-character
  table without Plum or Green the same, so self-play at 10^5-10^6 games
  is hours on Orbit's cores, not days. The engine, not the network, is
  the cost of training.
- **Determinism is per seed.** The goldens touched are
  `GOLDEN_FOUR_CHARACTER_GAME` (`tests/test_character.py`: Green,
  Mustard, Peacock, Plum at seed 17) and `tests/test_determinism.py`'s
  sampled-path test; the LLM fixture `llm_seed2.json` (roster
  `Plum,Mustard,Green,White`) is keyed on the system prompt, so the
  persona edit re-records it.
- **No archive or rename exists for a logbook**: `Logbook` has reset and
  rebuild, the store copy, and `add_entry` refuses an entry whose
  `identity` differs from the logbook's.

## 3. Design

### 3.1 The variant: Regularised Nash Dynamics over the floor

DeepNash (Perolat et al., 2022) is R-NaD: a policy-and-value network
trained by self-play with (a) a NeuRD-style policy gradient, (b) rewards
regularised toward a reference policy that is refreshed every K steps,
which is what gives the dynamics their convergence, and (c) V-trace for
off-policy correction, in a two-player zero-sum game. Clue has three to
six seats, a general-sum outcome, and the deduction floor as a public
state that already does most of the work the paper's network had to
learn. The variant keeps (a) and (b) and drops (c): rollouts are
on-policy with a value baseline, so no importance weights. Each seat has
its own value; nothing is zero-sum. The name for the glossary and the
wiki: **regularised Nash dynamics over the floor**.

**Input** (built from `obs` and `obs.mask`, about 330 numbers): per card
the possible-holder bits over the seats and the envelope, the resolved
holder, the or-constraint count, times named, times named unrefuted,
distinct namers, named beside located, in own hand (Mustard's feature
set, widened per holder); per seat active, hand size, is-me; the board:
current room one-hot, steps to each of the nine rooms, in-room flag;
turn fraction, number of players.

**Network** (`clude_agents/deep_nash.py`): an MLP trunk, two layers of
128, with heads:

- `belief`: 21 logits, softmax within each category after the mask.
  This is `ClueBelief.probabilities`, so the accusation test, the
  certainty tag, the notes, Green's arm and the replay trace work
  unchanged.
- `move`: a per-choice scorer over `[trunk embedding ; choice features]`
  (information, proximity, steps, kind one-hot, target room one-hot), so
  any number of legal moves is scored. Owns `choose_destination`.
- `suggest_suspect`, `suggest_weapon`: 6 logits each, own-hand cards
  masked out. The `bluff_rate` coin flip stays the Character's and comes
  first, so the RNG stream keeps its shape.
- `value`: this seat's expected outcome (+1 win, -1 out, 0 otherwise).

Accusation and card-to-show stay the Character's: the threshold test on
the belief head keeps `accuse_threshold` and the certainty tag
meaningful, and `secrecy` keeps its decision. Both could become heads in
a later version.

**Forward pass** in numpy. The weights are one JSON file,
`clude_agents/weights/plum.json` (a few hundred KB), loaded once at
module level as Mustard's tree is cached. Every score is rounded to
1e-9 before a softmax or an argmax so BLAS rounding between Windows and
Linux cannot flip a pick; goldens are captured on Orbit.

### 3.2 Training

`scripts/train_plum.py`, torch, developer-only (optional in
`requirements.txt` like Playwright, never in the image). A worker pool
plays games through the real engine with the net's seats answered by a
torch copy of the current weights; each game yields, per decision, the
state, the action, the legal mask, the reward and the true envelope.

Loss = NeuRD policy gradient on the regularised reward (the reward less
eta times log(pi / pi_ref)) with the value baseline, plus value
regression, plus belief cross-entropy against the true envelope (weight
lambda), plus an entropy bonus. The reference policy is refreshed every
K updates: the R-NaD outer loop.

Population, per game (David's third answer): with probability one half
every seat is the current net; otherwise each seat is drawn from the
current net, the five other characters and the floor bot, the table he
will actually sit at. Table sizes 3-6 as `self_play` draws them.

A run writes checkpoints and a curve (belief log-loss at the four
checkpoints, win rate on a fixed 24-game evaluation table) to
`data/plum-training/<run>/`, gitignored. The chosen checkpoint is
exported to `plum.json` and committed. Determinism is then "per seed and
weights file", as Mustard's is "per seed and logbook state"; a fixture
or golden depends on the committed file and nothing else.

Training runs on Orbit (the cloud workspace has no GPU and no
`data/llm`). The GPU is optional: the net is small and the engine is
the cost, so the worker count matters more than the card.

### 3.3 The seams

- `AgentProtocol` gains two optional hooks beside `choose_destination`:
  `movement_scores(obs, choices, features, profile)` and
  `suggestion_scores(obs, candidates, category)`. `Character.movement_scores`
  and `suggestion_candidates` use them when the agent defines them and
  today's arithmetic otherwise. The headless pick and the LLM menu then
  agree for every method, which also closes the admitted gap for any
  method to come.
- `explain.format_extra` learns `extra["method"] == "policy"` (the value
  and the top move), leaving `"exact"` and `"sampled"` to the archived
  module's output in the wiki.

### 3.4 Mothballing PlumOG

- `clude_agents/exact_enum.py` stays, as the module of record:
  `ExactEnumAgent` with `name = "PlumOG"` and a docstring headed
  "PlumOG (archived 2026-10-05)". It leaves `AGENT_SPECS`; no
  `PRESETS["PlumOG"]` (the presets == registry test holds); his dials
  are kept in `personality.py` as `PLUM_OG = Profile(...)` with a
  comment, since the new Plum starts from exactly those values.
- Green's `"Plum"` arm points at the new agent (the ensemble is over the
  other five methods, and Plum's method changed). His posterior for the
  arm is reset at deploy with a new `logbook reset-arm Green Plum`
  (Beta(1, 1) for that arm, the others untouched).
- The logbook archive: a new `logbook copy Plum PlumOG` on `Logbook`
  (entries, head and method memory; the `identity` field rewritten,
  `token` kept), then `logbook reset Plum`. Run on `data/llm` and on
  the bucket (`--uri gs://clude-game-data/llm`); the ring-era copy in
  `logbooks-ring` is the precedent. Other characters' dossiers on
  "Plum" stay: they are about the token.
- `users.RESERVED_NAMES` adds `plumog`.
- Wiki: *Exact posterior enumeration* opens as PlumOG's method,
  *Professor Plum* gets a section on PlumOG, `facts.py` keeps importing
  the archived module; *DeepNash*'s "Clude does not implement DeepNash"
  becomes the implementation note in N7.

## 4. Sub-phases

| | What | Files |
|---|---|---|
| N1 | Mothball PlumOG (3.4). Lands with N3, since the registry needs a Plum at all times | `clude_agents/exact_enum.py`, `__init__.py`, `personality.py`, `bandit.py`; `clude_storage/logbooks.py` (`copy`, `reset_arm`); `scripts/clude_cli.py` (`logbook copy`, `logbook reset-arm`); `clude_web/users.py`; tests for both commands |
| N2 | The seams (3.3), headless first | `clude_agents/base.py`, `character.py`, `explain.py`; tests in `tests/test_character.py` and `tests/test_llm.py` that a hooked agent's menu top equals its headless pick |
| N3 | The agent on random weights, so the suite is green before any training | `clude_agents/deep_nash.py`, `clude_agents/weights/plum.json`; numpy in `requirements.txt` and `requirements-web.txt`; `tests/test_agents.py` (contract, determinism, the hooks) |
| N4 | Training | `scripts/train_plum.py` (`--games`, `--workers`, `--seed`, `--eta`, `--refresh`, `--lambda-belief`, `--eval-every`, `--out`, `--export`); `clude_training/rollout.py` (the engine driven with recording seats and the population draw, stdlib only); `tests/test_training.py` (a few hundred games on a tiny net: the curve file and the export's shape) |
| N5 | Headless evaluation and the dials (5, 6) | `benchmark` grows a calibration table; `arena`'s `deviation_rate` divides by decisions; goldens re-captured on purpose; glossary section "The new Plum" |
| N6 | The LLM head | `clude_llm/personas/Plum.md` ("How you think" rewritten, the voice kept); the leash ladder (paid, quoted, a yes first); `llm_seed2` re-recorded (~$0.26); `docs/llm-wrapper.md` |
| N7 | Web, wiki, deploy | `clude_web/replay_data.py` (`METHOD_SHORT`, the description), `lobby.html` and `watch.html` (Plum no longer slow or dear), a *Regularised Nash dynamics* article on Plum's pattern with a figure from `build_wiki_figures.py`, *DeepNash* and *Professor Plum* updated, `docs/strategy-glossary.md`, `docs/architecture.md`, `CLAUDE.md`, this doc's "as implemented"; deploy, then the three `logbook` commands on the bucket |

Order N2, N3 with N1, N4, N5, N6, N7. Each lands with the suite green
and is reviewed before the next; N4's runs are David's to start on
Orbit.

## 5. The dials: which change meaning, and how each is re-measured

PlumOG's preset: `accuse_threshold` 0.9, `bluff_rate` 0.05, `curiosity`
0.5, `secrecy` 0.7, `temperature` 0.05, and the defaults `leash` 0.25,
`chattiness` 0.5, `memory` 0. The new Plum starts from the same values.

| Dial | Same meaning? | Re-measure |
|---|---|---|
| `accuse_threshold` 0.9 | Same test, different calibration: the belief head is a trained softmax, not an enumeration | Free. A calibration curve from the benchmark (60 games, seed 4004): P(triple correct) binned by the product the test compares. Keep 0.9 if the bin at 0.9 is within five points; otherwise move the threshold to the product whose empirical accuracy is 0.9. Confirm with `sweep --dial accuse_threshold --values 0.7 0.8 0.9 0.95 --characters Plum --games 48 --seed 7100` and the keep-a-dial monotone test on the wrong-accusation rate and the first-accusation turn. |
| `curiosity` 0.5 | No. The move head owns the destination; the dial no longer enters his scores | Retired for Plum, inert as `leash` is for a headless character; the value stays in the preset for the record, documented in `personality.py`. |
| `temperature` 0.05 | Same sampler, now over policy scores | Free: `sweep --dial temperature --values 0 0.05 0.2` on win rate and exact repeats; expected to stand. |
| `bluff_rate` 0.05, `secrecy` 0.7 | Same decisions, same code | None. |
| `leash` 0.25 | No. The leash is a fraction of the top score, and policy scores have a different spread, so 0.25 opens a different number of options than it did | Two steps. (1) Free, the equal-rope match: over the benchmark's 1,080 snapshots, the mean number of options `within_leash` allows per menu for PlumOG at 0.25 and for Plum at 0.1, 0.15, ... 0.5; the candidate is the value whose menu width matches PlumOG's. (2) One paid confirmation ladder, Plum alone with Claude at the standard table `Plum,Mustard,Green`, seed 7007, 24 games per value, at the matched value and at 0.25: deviations per decision, win rate against the headless baseline, remarks per game. Quote $8-16 (PlumOG's three-value ladder was $18.13; a faster Plum whose menus are single-option more often should be cheaper), and a yes before it runs. |
| `chattiness` 0.5 | Same gate, but it is applied once per model call, so a Plum with fewer multi-option menus talks less | Remarks per game off the same ladder; adjust only if it falls outside PlumOG's range. |
| `memory` 0 | Unchanged | None. |
| node and sample budgets | Gone | Replaced by the weights file; the hyperparameters live in the training script and this doc's record. |

## 6. The evaluation ladder (headless and free, before any paid run)

1. The belief benchmark, `benchmark --games 60 --seed 4004 --show-green`:
   log-loss below uniform (1.35) at every checkpoint, PlumOG's 1.44 the
   number to beat; ms a call (about 5 against 669).
2. Paired arenas on the standard seeds: `arena --games 24 --seed 7007`
   (the tuned table; PlumOG 37.5% on the grid twin) and the Plum table
   `--players 3 --roster Plum,Mustard,Green` (PlumOG 62.5% headless).
   Win rate, wrong-accusation rate, first-accusation turn, exact repeats
   (`loop_report.py` on Orbit), games with five or more parked moves.
3. Green with the new arm on the same arenas: his game time and his
   selected-arm shares.
4. The dial steps of section 5, then the one paid ladder.

## 7. Decisions (David's, 2026-10-05)

- **PlumOG is archived, not seatable.** No second character on the Plum
  token, so no token field on `AgentSpec` and no seat plumbing.
- **numpy enters `clude_agents`** for the forward pass; torch is a
  developer dependency for training only, never in the Cloud Run image.
- **A mixed population**: half the games pure self-play, half against
  the other characters and the floor bot.
- **The persona's "How you think" section is rewritten**, the voice and
  every dial kept; `llm_seed2` re-recorded once at the end.

## 8. Open questions

- The phase's number and where it sits against Phase 11.
- Whether the show decision and the accusation should become heads in a
  later version (left with the Character here, so the dials keep their
  meaning).
- Plum's Tier 1 memory: a learned policy can take fine-tuning from
  stored human and LLM records the way Mustard's rows do. Not in this
  plan; worth a line in the logbook doc when it is.

## 9. Out of scope

A seatable PlumOG. V-trace, a transformer trunk, learning from records.
Any change to the other five characters beyond Green's arm.

## 10. As implemented: N2 and N3 (2026-10-05)

David's word the same day: "Call it Phase 12, go ahead with N2 and
N3." Both built on `claude/sleepy-heisenberg-vl6uxz`: 579 passed, 34
skipped with `-n auto` (the one fixture that cannot pass until N6 is
skipped, below; the browser tests not run in this workspace).

### N2, the seams

- `AgentProtocol` (`clude_agents/base.py`) documents two optional,
  pure hooks: `movement_scores(obs, choices, features, profile)` and
  `suggestion_scores(obs, candidates, category)`, each one score in
  [0, 1] per option in order.
- `Character.movement_scores` returns the agent's scores when it has
  the hook, the curiosity blend otherwise; a new
  `Character.suggestion_scores(obs, category)` does the same for a
  suggestion slot over `suggestion_candidates`, and
  `_pick_suggestion_card` runs its softmax over it, the bluff coin flip
  still first. `clude_llm.menu.suggestion_menu` reads
  `character.suggestion_scores`, so the menu and the headless pick now
  agree for every method (`tests/test_llm.py`,
  `test_menus_rank_by_a_hooked_agents_own_scores`: at temperature 0
  Plum's headless move is the menu's top and the suggestion menu's
  scores are his distribution).
- `explain.format_extra` prints `method: "policy"` as
  ``[policy: value +0.12]``; `exact` and `sampled` stay for PlumOG's
  output in the wiki.

### N3, the agent on random weights

- `clude_agents/deep_nash.py`: `encode_state` (356 numbers: per card
  the floor's holder bits counted from this seat round the table, the
  resolution, the or-constraint count, Mustard's naming features and
  own-hand; per seat active, hand size, present; turn and table size),
  `encode_choices` (25 per legal move), `forward` (trunk 356-128-128,
  heads belief 21, suspect 6, weapon 6, value 1) and `move_scores`
  (the scorer over hidden plus choice features, 153-64-1);
  `WEIGHT_SHAPES` the one statement of the layout; `init_weights`,
  `save_weights`, `load_weights` (float32 on disk, float64 in play,
  checked against the shapes); `DeepNashAgent`, `name = "Plum"`, with
  `select_action` (the belief head softmaxed per category through
  `mask_and_normalize`, `extra = {"method": "policy", "value": v}`),
  the two hooks as distributions over the options, and
  `choose_destination` a seeded softmax draw over its own scores at the
  profile's temperature. Every score is rounded to nine places before
  a pick. The trunk runs once per observation object, cached like the
  Character's belief.
- `clude_agents/weights/plum.npz` (280 KB) is `init_weights(2026)`:
  heads scaled by 0.01, so this Plum's every distribution is close to
  uniform. `weights/README.md` says what the file is and that the
  goldens pin it.
- The registry's Plum is `DeepNashAgent` with the description
  "Self-play policy by regularised Nash dynamics over the floor (a
  DeepNash variant)"; `METHOD_SHORT["Plum"]` is "Self-play policy";
  Green's `"Plum"` arm is the new agent (his stored posterior for that
  arm is reset in N1's bucket pass).
- `ExactEnumAgent.name` is `"PlumOG"`, the module docstring headed
  "Archived 2026-10-05"; the class stays importable and out of the
  registry. `personality.PLUM_OG` keeps his dials under his name, and
  Plum's preset comment says curiosity is inert for the new Plum and
  which dials are to be re-measured. `users.RESERVED_NAMES` adds
  `plumog`.
- numpy is in both requirements files (the first numerical dependency
  of the agents, David's call); the Dockerfile is unchanged.
- `tests/test_web_tables.play_out`, the helper that drives a web table
  through the JSON routes, now stops the off-turn talk's clock
  (`chat.delay`) as well as the work interval: it counts steps, not
  seconds, and a queued reaction otherwise waits out its two to eight
  seconds while `work` answers "waiting". PlumOG's slow calls had let
  that clock run unnoticed; with the new Plum answering in milliseconds,
  seven table tests ran out of steps on one reaction at turn 29.
- Tests: `tests/test_agents.py` gains four (the contract and the
  `ValueError` without a mask, PlumOG's name and absence, the encoding
  and weights layout with a round trip and a refused file, the hooks
  as pure distributions and the seeded pick); `tests/test_determinism.py`
  runs PlumOG's sampled path by class and Plum's policy path by
  registry under two hash seeds; `tests/test_explain.py` the policy
  line. `GOLDEN_FOUR_CHARACTER_GAME` re-captured (100 events, where
  PlumOG's game ended in 49: a Plum who knows nothing wanders) and
  commented as pinning the weights file too. `llm_seed2` is skipped
  with its reason until N6 re-records it.

### Measured

- A table `Plum,Mustard,Green,White` at four seats: 0.31 s a game
  against 7.5 s with PlumOG (three games, seed 7007, this workspace's
  CPU); the mean turns 96, the random policy's wandering.
- Belief, movement and suggestion from the random weights all sit
  within a few hundredths of uniform, as the head scale intends.

### Left for the next steps

- N1's storage half and N4: section 11.
- The wiki still describes Plum as the enumerator, the lobby still
  prices him at $0.25 and Watch still calls him slow: N7.
- The goldens were captured on Linux; the plan says Orbit. The
  nine-place rounding is meant to make that moot, and N4's first
  export re-captures them on Orbit anyway.

## 11. As implemented: N1's storage half and N4 (2026-10-05)

N2 and N3 were merged the same day (pull requests 5 and 6 of
`davidabelin/clude`); David: "Merged. Please proceed." Built on the
branch restarted from main.

### N1, the storage half

- `Logbook.copy_to(identity)` (`clude_storage/logbooks.py`): every
  entry stored again under the new identity, its `identity` and the
  label of its own seat's `table` row rewritten and its `token` kept,
  the target's head built by `add_entry` (never copied, so the tally,
  dossiers and flags agree with the entries), the method document
  copied as it is; refuses the same identity or a target with any
  logbook; the source untouched.
- `memory.reset_arm(logbook, arm)` (`clude_training/memory.py`): one of
  Green's arms back to `[1.0, 1.0]` in his `state` document, the
  others untouched. Written, not removed: a table in play reloads the
  document at its finish and `BanditAgent.load_state` skips a missing
  arm, which would write the old posterior back.
- `logbook copy --identity A --to B` and `logbook reset-arm --arm NAME`
  (`--identity` Green by default) on the CLI, both exiting 1 when
  refused; `docs/cli.md` and `docs/logbooks.md`.
- Tests: `_exercise_copy` in `tests/test_logbooks.py` over the local
  store and the fake bucket; `test_reset_arm_...` in
  `tests/test_memory.py`; both commands in `tests/test_cli.py` on the
  two-game Green store.
- **The pass is David's, on Orbit, after the merge**, with no table in
  play on the service:
  ```
  python scripts/clude_cli.py logbook copy --uri data/llm --identity Plum --to PlumOG
  python scripts/clude_cli.py logbook reset --uri data/llm --identity Plum
  python scripts/clude_cli.py logbook reset-arm --uri data/llm --identity Green --arm Plum
  ```
  then the same three with `--uri gs://clude-game-data/llm`.

### N4, the rollouts and the trainer

- `clude_training/rollout.py` (numpy, no torch): `RecordingCharacter`,
  a `Character` over `DeepNashAgent` at Plum's preset with temperature
  1 that writes down each move (the encoded state, the choice matrix,
  the index drawn from the agent's own scores and RNG, exactly as
  `choose_destination` draws) and each honest suggestion slot (the
  candidate indices and the index drawn; a bluff is the dial's coin and
  goes unrecorded); `draw_table`, seeded, `n_players` tokens in board
  order and per seat the network, a floor bot or the token's own
  character (Plum's token never his character, since that is the
  network; at least one network seat; `"self"` all network, `"mixed"` a
  coin per game); `play_one`, the engine with those seats and the
  outcome (winner from the last event, a seat out on a wrong
  accusation; rewards +1, -1, 0; the envelope; `capped`); `GameTrace`
  and `to_arrays` (the ragged options as one array plus offsets);
  `rollout_batch`, serial or a `multiprocessing.Pool` with the weights
  through the initializer, the same result either way; `evaluate`, the
  arena's per-game loop with Plum's agent injected on the tuned table
  and the Plum table. Characters at the table get `new_game` and
  `observe` as the arena gives them.
- `scripts/train_plum.py` (torch): `TorchNet` is `WEIGHT_SHAPES` as
  parameters with the same arithmetic (a test checks every head
  against `deep_nash.forward` to 1e-4); `stack_traces` and
  `option_logits` put a batch's ragged options through the right head
  with one logit per option row; `losses` is the policy gradient on the
  regularised reward (the seat's outcome less `--eta` times the log
  ratio to the reference policy, the advantage against the value
  head), the value regression, the belief cross-entropy over the cards
  the floor allows, and the entropy bonus; the reference is refreshed
  every `--refresh` updates; AdamW with `--weight-decay`, the gradient
  clipped at 1. A run writes `args.json`, `curve.jsonl`, `ckpt-NNNN.npz`
  and `eval.jsonl` (`rollout.evaluate` and the belief benchmark against
  uniform), `final.npz`, and with `--export` the weights file Plum
  reads. The script is the one place torch is imported;
  `requirements.txt` lists it as optional.
- Tests: four in `tests/test_training.py` (the draw, one rollout's
  decisions and outcome and arrays, serial equals pool, the two
  tables) and two in `tests/test_train_plum.py`, skipped without torch
  (the forward-pass equivalence; a one-batch run fitted hard, its
  records, the export and a resumed run through the pool).

### What a short run showed

Measured here, on this workspace's four cores, before any real run:

- An untrained network at a self-play table never accuses, so those
  games cap at 150 turns; with floor bots and the characters in the
  mix, games end and rewards flow. Rollouts with recording cost
  0.1-0.3 s a game.
- A few hundred games of untrained play carry no envelope signal the
  belief head can generalise: on a held-out batch its loss stays at the
  masked-uniform floor (1.66 nats a category on 40-turn games) while
  one batch fitted repeatedly goes to 0.001 in sample and above uniform
  out of sample. So the unit test asserts the in-sample fit, and
  generalisation is measured on the smoke run below and, for real, on
  Orbit.

