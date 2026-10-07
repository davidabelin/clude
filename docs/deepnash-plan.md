# Phase 12, a new Plum: PlumOG mothballed, Plum rebuilt on a DeepNash variant

Proposed 2026-10-05; N2/N3 built the same day and N4 on 2026-10-06.
David's decisions are in section 7, scoring/agent implementation in
section 10, and training/smoke-run evidence in section 11. PyTorch is
a default developer dependency. Release readiness remains separate.

## Current state (2026-10-07)

N2-N5 are built. **The committed weights are the second long run's checkpoint 130** (section 11), exported on the evening of 2026-10-06: 49% at his own table and 22% at the six-character table on 96 games, the best belief log-loss on record from the 50% checkpoint on, no wrong accusations. N1's logbook commands and N5's headless evaluation followed on 2026-10-07 (section 12): presets kept, leash 0.35 the equal-rope candidate. N6's paid ladder the same day kept **leash 0.35** ($8.38), both LLM fixtures were re-recorded, and N7's wiki pass rewrote Plum's pages (section 13). Left: placing the portraits after David's review, the deploy and the three `logbook` commands on the bucket. The detailed designs below are proposals unless the implementation records confirm them.

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
`clude_agents/weights/plum.npz` (a few hundred KB), loaded once at
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
| N3 | The agent on random weights, so the suite is green before any training | `clude_agents/deep_nash.py`, `clude_agents/weights/plum.npz`; numpy in `requirements.txt` and `requirements-web.txt`; `tests/test_agents.py` (contract, determinism, the hooks) |
| N4 | Training | `scripts/train_plum.py` (`--games`, `--workers`, `--seed`, `--eta`, `--refresh`, `--lambda-belief`, `--eval-every`, `--out`, `--export`); `clude_training/rollout.py` (the engine driven with recording seats and the population draw, NumPy inference without torch); `tests/test_training.py` (a few hundred games on a tiny net: the curve file and the export's shape) |
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
   (the tuned table; PlumOG 37.5% under the landing rule) and the Plum
   table `--players 3 --roster Plum,Mustard,Green` (PlumOG 58.3% under
   the landing rule; the 62.5% first quoted here was the ring ladder's,
   corrected 2026-10-07).
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

- Resolved: this is Phase 12 (David, 2026-10-05), interleaved with Phase 11 documentation work.
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

- N1's storage half: `logbook copy Plum PlumOG` and `logbook reset-arm
  Green Plum`, and the pass over `data/llm` and the bucket.
- N4: `scripts/train_plum.py` and `clude_training/rollout.py` (built
  2026-10-06, section 11).
- The wiki still describes Plum as the enumerator, the lobby still
  prices him at $0.25 and Watch still calls him slow: N7.
- The goldens were captured on Linux; the plan says Orbit. The
  nine-place rounding is meant to make that moot, and N4's first
  export re-captures them on Orbit anyway.

## 11. As implemented: N4 (2026-10-06)

David's word: "Go ahead with N4: rollout.py first then the training
script. Yes, use torch and update requirements.txt to load by default."
Built on Orbit, where the venv had neither numpy nor torch until this
day (N3 was built in the cloud workspace); `pip install numpy torch`
gave numpy 2.5.3 and torch 2.14.1, the CPU wheel, which is all the
training needs.

### The rollout, `clude_training/rollout.py`

- `RecordingPlum` is Plum's `Character` over a `DeepNashAgent` with the
  weights being trained. It plays the accusation and the card to show
  exactly as the deployed Plum does and flips the bluff coin first as
  he does, so the only difference from the table's Plum is the sampler:
  the move and the suggestion cards are drawn from the network's own
  softmax (`policy_temperature` 1) rather than the `Character`'s
  sharpening sampler over it, so that the policy gradient is on-policy
  and the exploration is the policy's own. What is learned is the
  distribution; what is played is its peak.
- `draw_lineup` is the population of David's third answer: all network
  seats with probability `self_play` (one half), otherwise a draw per
  seat from the network, the five characters and the floor bot, each
  character once and at its own token through `arena.seat_lineup`, with
  at least one network seat. Table sizes cycle 3 to 6. Characters are
  built and reset as the arena builds them; network and floor seats get
  private RNGs from `fill_seed`.
- `play_game` returns an `Episode` per network seat: the encoded state
  at every decision (float32), the kind of step (move, suspect, weapon,
  or the accusation observation as a belief-only step), the options
  (the legal moves' feature rows, or the honest candidates' indices),
  the option taken, the envelope, the outcome reward (+1 won, -1 put
  out, 0 otherwise, 0 for everyone when the cap is hit) and `gains`,
  the floor's bits gained since the seat's previous turn on the
  certainty tag's scale. `play_games` is the process pool's task;
  `RolloutStats` summarises a batch.
- `deep_nash.DeepNashAgent._heads` became the public `heads`, which
  also keeps the encoded state, and `deep_nash.playing_with(weights)`
  installs a checkpoint as the registry's Plum (and Green's arm) for
  the length of a block, so a checkpoint is evaluated through the
  ordinary arena and benchmark.

### The script, `scripts/train_plum.py`

`PlumNet` holds one torch parameter per entry of `WEIGHT_SHAPES`, same
names and orientations, and agrees with the numpy forward pass to
float32 rounding (a test pins it). Each iteration: `--games` games
through a spawn pool of `--workers`; the NeuRD policy gradient on the
regularised return (the reward less `--eta` times ``log(pi / pi_ref)``
over the seat's own steps, `pi_ref` refreshed every `--refresh`
iterations; the sampled estimator with its ``1 / pi(a)`` weight capped
at 10 and DeepNash's logit threshold of 2; `--policy-grad softmax` for
the plain score-function gradient), the value head by regression, the
belief head by masked cross-entropy, an entropy bonus. Every
`--eval-every` iterations the free ladder of section 6 runs on the
current weights (the benchmark's log-loss on 20 floor-bot games, the
Plum table and the six-character table at seed 7007) and a checkpoint
is written; `best.npz` tracks the Plum-table win rate, `latest.npz`
the end, `--export` copies the end to `clude_agents/weights/plum.npz`.
`docs/cli.md` has the usage.

### What the smoke runs taught

Four runs of 256 games an iteration, six workers each, two at a time,
all seed 2026 (`data/plum-training/smoke-*` and `smoke2-*`, gitignored;
the curves are the record). About 17 s an iteration with two runs
sharing the laptop, 10,240 games in a quarter of an hour.

1. **The belief head memorises a batch.** The first pair (40
   iterations, 2 epochs at lr 1e-3, the belief loss on the iteration's
   own steps) scored *worse* than the floor's uniform on the benchmark
   at every evaluation (1.44 to 1.63 against 1.35 at the 50%
   checkpoint). Every step of a game shares one envelope, so the
   effective sample count is the games, not the steps, and a 76k-
   parameter net fits a few hundred games' envelopes in a handful of
   updates: on one 96-game batch, no learning rate from 1e-4 to 1e-3
   beat uniform at any step count, it only got worse, and 200 steps at
   1e-3 took the midpoint log-loss to 3.6. The fix is a replay buffer:
   the belief head trains on a quarter of each of the last ten
   iterations' steps (`--replay`, `--replay-fraction`), one pass an
   iteration at lr 3e-4.
2. **The policy gradient had nothing to push with.** Raw advantages on
   a return that is 0 almost everywhere, under a gradient clip of 1
   shared with a belief gradient of about 2, left the policy loss
   within 0.01 of zero and the entropy at the uniform 2.0 for all 40
   iterations. Advantages are now standardised over the iteration
   (`--no-adv-norm` to leave them raw) and the clip is 5.
3. With both changes (the second pair, 24 iterations, 6,144 games),
   the belief head is the best method on record from the midpoint on:

   | Belief log-loss | 25% | 50% | 75% | 100% |
   |---|---|---|---|---|
   | uniform (20 games, seed 4004) | 1.54 | 1.31 | 0.87 | 0.23 |
   | iteration 8 (2,048 games) | 1.65 | 1.34 | 0.94 | 0.24 |
   | iteration 16 (4,096 games) | 1.56 | 1.21 | 0.83 | 0.21 |
   | iteration 24 (6,144 games) | 1.52 | 1.17 | 0.82 | 0.20 |
   | PlumOG (60 games; glossary) | 1.52 | 1.44 | 1.00 | 0.22 |
   | White, the best before (60 games) | 1.54 | 1.28 | 0.91 | 0.23 |

   (The 20-game benchmark's uniform differs from the 60-game one's, so
   compare each row with its own uniform.) Both runs of the pair give
   the same belief curve to two places, as they should: same seed,
   same replay.
4. **The policy has barely begun.** Entropy fell from 2.00 to 1.98 on
   the outcome reward alone and to 1.91 with the shaped reward
   (`--shaping 1.0`, the floor's bits gained each turn added to the
   outcome); self-play games still run to about 100 turns, and the
   network's seats win 2% of self-play games on the outcome reward and
   6% with shaping, against the 0% of random weights. On the
   evaluation tables Plum accuses in one game in 24 at best and wins
   it, and never accuses wrongly. The plan's second milestone (PlumOG's
   37.5% at the six-character table, 58.3% at his own, on today's
   rules; first quoted as 31% and the ring-era 62.5%) is a long run
   away, and the first thing to try if it stalls is still the shaped
   reward, which is now a flag.

Departures from the plan: no "tiny net" for the test, since the layout
is pinned by `WEIGHT_SHAPES` (the test runs the real net on six games
and two iterations instead); the belief head trains from a replay
buffer rather than the iteration's own steps; advantages are
standardised; `--shaping` exists. Nothing exported: the committed
`plum.npz` is still the random draw, so no golden moved.

### The first long run, `run150a` (2026-10-06)

David's run, on Orbit with the laptop to itself:

```
python scripts\train_plum.py --iterations 150 --games 512 --workers 12 --shaping 1.0 --eval-every 10 --out data\plum-training\run150a
```

76,800 games, about 15 s an iteration (10 s of games, 5 s of
updates), under 40 minutes. What the curve shows:

- **The policy learned, then stalled.** Entropy fell from 2.00 to 1.65
  by iteration 70 and stayed there; self-play games shortened from
  105 turns to about 75; the network's seats went from winning 4% of
  self-play games to 15-17%, and 7-12% of the mixed games, from
  iteration 60 on. The regularised-reward term, the entropy bonus and
  the NeuRD logit threshold of 2 (which caps how peaked a head can
  get) are the suspects for the plateau; none was varied.
- **The belief head peaked early and drifted.** Best at iterations
  20-50 (1.12-1.13 at the 50% checkpoint on the 20-game benchmark),
  1.21 by 150: the policy gradient through the shared trunk, most
  likely, since the replay buffer did not change.
- **The late checkpoints, re-measured on 96 games a table** (the
  curve's 24-game evaluations have a ten-point standard deviation) and
  the full 60-game benchmark:

  | checkpoint | log-loss 25/50/75/100% | Plum table win | wrong | six-character win |
  |---|---|---|---|---|
  | 100 | 1.49 / 1.23 / 0.87 / 0.22 | 24.0 | 1.0 | 15.6 |
  | **110** | **1.47 / 1.22 / 0.86 / 0.21** | **32.3** | **0.0** | **12.5** |
  | 120 | 1.48 / 1.23 / 0.87 / 0.22 | 28.1 | 0.0 | 15.6 |
  | 130 | 1.50 / 1.26 / 0.90 / 0.23 | 20.8 | 1.0 | 10.9 |
  | 140 | 1.50 / 1.27 / 0.90 / 0.25 | 18.8 | 1.0 | 12.5 |
  | 150 | 1.51 / 1.27 / 0.91 / 0.24 | 12.5 | 1.0 | 4.7 |
  | uniform | 1.57 / 1.35 / 1.01 / 0.29 | | | |
  | PlumOG (glossary; 24 games, landing rule) | 1.52 / 1.44 / 1.00 / 0.22 | 58.3 | 0.0 | 37.5 |

  The six-character table is 64 games with Plum seated (he sits out
  the three- and four-seat games of the cycle). The run got worse
  after 120 on every measure, so the end of a run is not the weights
  to take; `best.npz` (chosen on the 24-game evaluation) was
  checkpoint 110, which the 96-game re-measurement confirms.
- **Checkpoint 110 against PlumOG:** better belief at every checkpoint
  but the start (1.22 against 1.44 mid-game, where PlumOG was worse
  than ignorance), the best mid- and late-game log-loss of any method
  on record (White's 1.28 and 0.91 were the marks), no wrong
  accusations in 96 games, and 0.3 ms a call against 669; but about
  half PlumOG's win rate at his own table and a third of it at the
  six-character table. Mustard and Green at his table win 37.5% and
  28.1% against him, where PlumOG held them to 20.8% each (on the
  grid; first written as the ring ladder's 25.0% and 12.5%, corrected
  2026-10-07).

Two script changes from reading this run: `--neurd-threshold` (was the
constant 2), and the rollout seats' `--policy-temperature` is now
applied to the learner's logits too, so a value other than 1 keeps the
gradient on-policy (it had been a silent mismatch, unused so far).

### The second run, `run2`, and the export (2026-10-06)

Resumed from `run150a`'s checkpoint 110 with the plateau's suspects
loosened:

```
python scripts\\train_plum.py --resume data\\plum-training\\run150a\\checkpoint-000110.npz --iterations 150 --games 512 --workers 12 --shaping 1.0 --eval-every 10 --lr 0.0001 --entropy 0.003 --neurd-threshold 4 --eta 0.05 --out data\\plum-training\\run2
```

Another 76,800 games, about 9 s an iteration now that games are
shorter. Entropy went on down from 1.65 to 1.35, self-play games from
75 turns to 50, the network's self-play wins from 16% to 20% and its
mixed-game wins from 8% to 12%; nothing degraded late, which the lower
learning rate was for. The belief head stayed where it was (1.20-1.22
at the 50% checkpoint on the 60-game benchmark at every checkpoint):
the policy's gain did not cost it, and nothing improved it either.

The checkpoints from 60 on, re-measured on 96 games a table and the
60-game benchmark:

| checkpoint | log-loss 25/50/75/100% | Plum table win | wrong | six-character win |
|---|---|---|---|---|
| 60 | 1.48 / 1.21 / 0.85 / 0.22 | 25.0 | 2.1 | 9.4 |
| 80 | 1.49 / 1.22 / 0.87 / 0.21 | 36.5 | 1.0 | 21.9 |
| 100 | 1.48 / 1.20 / 0.84 / 0.21 | 35.4 | 1.0 | 12.5 |
| 120 | 1.47 / 1.20 / 0.85 / 0.21 | 44.8 | 0.0 | 15.6 |
| **130** | **1.48 / 1.21 / 0.86 / 0.21** | **49.0** | **0.0** | **21.9** |
| 140 | 1.48 / 1.20 / 0.86 / 0.21 | 38.5 | 0.0 | 20.3 |
| 150 | 1.48 / 1.21 / 0.87 / 0.21 | 37.5 | 1.0 | 21.9 |
| run 1's 110, the first export | 1.47 / 1.22 / 0.86 / 0.21 | 32.3 | 0.0 | 12.5 |
| PlumOG (24 games, landing rule; glossary) | 1.52 / 1.44 / 1.00 / 0.22 | 58.3 | 0.0 | 37.5 |

(The six-character table is 64 games with Plum seated. The 96-game
win rates carry a standard deviation of about five points, PlumOG's
24-game ones about ten.) Checkpoints 120 to 150 sit between 38 and
49 at the Plum table, a plateau with noise on it rather than a trend;
130 is the top of it on both tables with no wrong accusation in 160
games, and was exported as **`clude_agents/weights/plum.npz`** the
same evening, replacing run 1's 110 exported earlier that day. At his
own table Mustard and Green now take 25% and 26% against him, where
against PlumOG on the grid they took 20.8% each.

**Where that leaves Plum against PlumOG**: better belief from the 50%
checkpoint on (1.21 against 1.44, and the best mid- and late-game
log-loss of any method), no wrong accusations, three orders of
magnitude faster; about five sixths of PlumOG's win rate at his own
table (49 against 58.3, the latter on 24 games) and three fifths of
it at the six-character table (22 against 37.5). (Corrected
2026-10-07: this paragraph first compared with the ring ladder's
62.5% and the pre-landing-rule 31%; see section 12.) A third run from
checkpoint 130 may add a little; the evidence of run 2 is that the
policy's ceiling under this recipe is near, and the belief head's
plateau at 1.20 is the more interesting limit, since what it reads
beyond the floor is Mustard's naming features and nothing about *who*
named what. Both are for after N5-N7, when a trained Plum is at the
tables and in the wiki.

### Tests and the suite

`tests/test_train_plum.py` (not `test_training.py`, which holds the
Phase 4 snapshot and benchmark tests): the rollout's record of every
decision, determinism per seed and characters at their own tokens, the
population draw, `playing_with`, the torch network against the numpy
forward pass, and the loop on six games writing the curve, the
checkpoints and a loadable export. Under pytest on Windows, torch's
first call prints "Windows fatal exception: access violation" and then
passes: pytest's faulthandler reporting a first-chance exception that
torch's MKL handles itself. The torch fixture disables faulthandler
while it is in use.

Noted, not touched: `clude_llm/personas/rules.md` was edited by hand
during this day's session (table talk about politics and the weather;
a dangling "The "), so `test_recorded_llm_games_replay_offline[llm_seed1]`
fails, since the fixture is keyed on the exact prompt. N6 re-records
`llm_seed2`; `llm_seed1` wants the same once the edit is finished.


## 12. As implemented: N1's storage half and N5 (2026-10-07)

David's word: "Let's get complete with Phase 12 today", and the plan
for the day approved: N1 storage, N5 measurements, then the paid N6
gate and N7.

### N1, the logbook commands

- `Logbook.copy_to(identity)` (`clude_storage/logbooks.py`) copies a
  logbook to another identity in the same store, as an archive: every
  entry with its `identity` rewritten and `token` kept, the head under
  the new name, the method memory as is. It refuses a destination that
  already has a logbook, and a source that has none.
- `Logbook.reset_arm(arm)` drops one arm from a stored bandit
  posterior, so `BanditAgent.load_state` gives it its prior; the other
  arms and the game count are untouched.
- `logbook copy --identity Plum --to PlumOG` and `logbook reset-arm
  --arm Plum` (`--identity` defaults to Green) in `scripts/clude_cli.py`;
  `tests/test_logbooks.py` runs both over the local store and the GCS
  double.
- Run on `data/llm`: Plum has no logbook there (no LLM Plum game was
  stored with logbooks), so there was nothing to archive; Green's Plum
  arm (0.75 after one game) was reset. The bucket pass waits for the
  deploy (N7).

### N5, the headless evaluation

All on the committed weights (run 2's checkpoint 130), results in
`data/plum-eval/` (gitignored) and the glossary's new section *The new
Plum (Phase 12, 2026-10-07)*, which holds the tables.

- **`benchmark` grows `--calibration`** (`clude_training/benchmark.py`):
  per agent, the P `best_triple` compares with `accuse_threshold`
  (through the spec's confidence function, so Peacock's lower bound),
  binned, against how often that triple was the envelope, and the
  accuracy at or above 0.8, 0.9 and 0.95; in the JSON as `calibration`.
  The "fell back to sampling" line now prints only for an agent that
  did, since the registry's Plum never samples.
- **Belief**, `benchmark --games 60 --seed 4004`: 1.48 / 1.21 / 0.86 /
  0.21, below uniform (1.57 / 1.35 / 1.01 / 0.29) everywhere, the best
  of any method to the halfway mark; 0.7 ms a call. Green, with the
  network as his Plum arm, ties him at 50% and edges him late, and his
  call falls from 524 ms to 1.6 ms.
- **Calibration**: at or above 0.9 Plum's triple was right in 132 of
  132 snapshots; below it, where there are numbers, he is
  underconfident. `accuse_threshold` 0.9 stands by the section 5 rule.
- **Arenas**, seed 7007, 24 games: 54.2% at his own table (Mustard
  20.8%, Green 25.0%), 12.5% of 16 at the six-character table, no
  wrong accusation.
- **A correction.** The PlumOG figures this plan compared with since
  section 6, 62.5% at his own table and 31% at the six-character one,
  were the ring ladder's headless leg and the six-character arena
  *before* the landing rule. On today's rules and the same deals
  (`grid-plum-prox2-24`, `arena-grid-prox2-24`, counted from their
  records) PlumOG won **58.3%** and **37.5%**, and Mustard and Green
  20.8% each at his table. Sections 6 and 11 are corrected in place.
  Paired with those runs, Plum is a game behind at his own table and
  four behind (2 of 16 against 6 of 16) at the six-character one.
- **Dials** (`sweep --seed 7100`, 192 games at six characters and 96
  at his table): lowering `accuse_threshold` to 0.6-0.8 buys at most
  six points at the big table, about a sigma, and costs 3-8% wrong
  accusations at his own, where 0.9 has none; `temperature` 0.05 is
  best or joint best on both tables. **Both presets kept**; no golden
  moved.
- **Leash width**, `scripts/leash_width.py` (new): at each of Plum's
  multi-option move and suggestion menus on his table, the options
  each leash would allow, for Plum and for PlumOG with his own dials
  on the same seeds. PlumOG at 0.25 allowed 1.75 a menu; Plum allows
  1.46 at 0.25 and **1.71 at 0.35**, the equal-rope match (0.30
  matches PlumOG's share of open menus instead). Plum faces 50 such
  menus a game against PlumOG's 31, since he suggests more, so at
  0.35 the model is asked about twice as often per game.
- `arena.deviation_rate` already divided by the model's played
  decisions; nothing to change.

### What N6 now costs

PlumOG's ring ladder spent about $6 a 24-game value for 380 model
calls. At 0.35 Plum should make about 500-600 calls a value and at
0.25 about 400, so the ladder `--roster Plum,Mustard,Green --seed 7007
--games 24` at 0.35 and 0.25 is quoted at **$15-22**, above the $8-16
of section 5, plus about $0.5 to re-record `llm_seed1` and `llm_seed2`.

## 13. As implemented: N6 and N7 (2026-10-07)

### N6, the leash ladder and the fixtures

The ladder ran as quoted (`sweep --dial leash --values 0.25 0.35 --characters Plum --roster Plum,Mustard,Green --players 3 --games 24 --seed 7007 --llm --llm-characters Plum --store data/llm --run-id plum-policy-ladder --json data/llm/ladder_plum_policy.json`), 50 minutes, **$8.38** against the $15-22 quote. The model calls were close to the estimate (354 at 0.25, 464 at 0.35, against about 400 and 500-600); each cost less than PlumOG's ring calls had, $0.008-0.012 against $0.016. A first launch without `ANTHROPIC_API_KEY` in the environment fell back on every call and spent nothing; its records were deleted before the real run. The CLI does not read `.env`; the key has to be set in the same shell call.

The results are in the glossary ("Plum with Claude, the network (N6)"). Both values win 54.2%, as the network does headless on the same seeds; 0.35 has no wrong accusation where 0.25 has one; the model departs from the top option a little more often at 0.35 (14.9% of asked decisions against 12.7%); both talk a median of six remarks a game, against PlumOG's 5.4. By the rule set before the run (keep 0.35 unless departures, wins or remarks argue for 0.25), **0.35 stays**. One 172-turn game at 0.35 reached the wrapper's 500K-token cap, cost $2.78 and caused all nine fallbacks; the median seat-game is $0.09 at both values.

- `clude_agents/personality.py`: Plum's preset `leash=0.35`. `PLUM_OG` had been the same object as the preset; it is now its own copy with PlumOG's 0.25, so the archive keeps his dials. Headless play ignores `leash`, so no golden moved.
- `tests/fixtures/llm_seed1.json` ($0.11) and `llm_seed2.json` ($0.03, White wins on turn 10 as before) re-recorded into fresh files (the recorder appends) and both replay tests un-skipped; the preset test allows Plum's 0.35.
- `docs/llm-wrapper.md` (Plum's leash and cost), the lobby's budget note (Plum no longer priced apart), `docs/architecture.md` (the committed weights are trained, not seeded).

### N7, the wiki and the web

[Wikiclude's plan](wikiclude-plan.md), section 13, records the wiki pass: *Regularised Nash dynamics*, *Professor Plum* rewritten with a PlumOG section, *Exact posterior enumeration* as PlumOG's method, the Rope question's network answer pinned in tests, the Plum figures and seven diagrams, algorithm boxes and 21 Algorithms entries. After N6, *Professor Plum* gains "With Claude" and *Leash* a section on Plum's network, from new facts (`ladder.policy`, `policy.llm.*`); `cost.seat_game.plum` now cites $0.09. Watch no longer calls Plum slow; `replay_data.METHOD_SHORT` already read "Self-play policy".

The six suspects' cartoon portraits (`clude_web/wiki/portraits.py`, contact sheet `docs/ux/portraits/`) are registered as figures and await David's review before they replace the tokens in the character infoboxes.

### Left

- The portraits in the infoboxes, after review.
- Deploy (`scripts\deploy.bat`, after checking `gcloud run revisions list`), then on `--uri gs://clude-game-data/llm`: `logbook copy --identity Plum --to PlumOG`, `logbook reset --identity Plum`, `logbook reset-arm --identity Green --arm Plum`. Both need David's yes.
