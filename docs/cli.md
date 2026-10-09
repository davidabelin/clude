# Maintainer CLI (`scripts/clude_cli.py`)

Run from the repo root with the venv interpreter. `--help` is the complete argument reference; this guide explains workflows and output.

```powershell
& .venv\Scripts\python.exe scripts\clude_cli.py --help
& .venv\Scripts\python.exe scripts\clude_cli.py play --help
```

Examples below use `python` for readability; activate the venv or substitute its explicit path. Seeded numerical games reproduce with the same code, weights, settings and memory. Real model answers, timings and timestamped run IDs do not reproduce from a seed alone.

## Entry points and store defaults

**clude.bat targets the live store** for `users`, `tables`, `logbook` and `store`: `gs://clude-game-data/llm`, unless `--uri` is supplied. `clude live ...` also appends that URI. Direct Python invocations use these defaults:

| Command | Default store |
|---|---|
| `store`, `logbook` | `data` |
| `users`, `tables` | `data/llm` |
| `play`, `arena`, `sweep` | No record store unless `--store` is passed |

Use an explicit URI for account changes, reset/rebuild, abandon and copying. Read-only inspection does not imply every command is read-only: account operations, logbook reset/rebuild/copy/reset-arm/relabel, `store copy`, `store merge`, `tables abandon`, `tables costs --write`, recordings and training artifacts write data.

| Command | Purpose |
|---|---|
| `agents` | Registry, methods and presets |
| `play`, `prompt`, `trace`, `floor` | One game, model input, belief history or logical knowledge |
| `benchmark`, `snapshots` | Belief quality and data distribution |
| `train-mustard` | Tree inspection and held-out evaluation |
| `arena`, `sweep` | Full-game outcomes and dial comparisons |
| `store`, `logbook` | Records, copying and memory administration |
| `tables`, `users` | Web table/account administration |

`play`, `prompt`, `trace` and `floor` share players (3-6, default 4), seed (1), turn cap (300) and roster (`random`). With identical inputs they reconstruct the same numerical game. Viewer indices refer to the resulting **seat order**, not the input roster order.

`--roster random` or `floor` fills the table with that bot. A comma-separated roster mixes named characters and fill bots; short rosters are padded with FloorBot. Characters are locked to their own tokens and seated in board order. Fill bots take available tokens. Larger arena rosters rotate who sits out, never a character's token. `P0 Scarlett (floor)` means FloorBot occupying Scarlett; Plum never occupies Mustard.

## `agents`

Prints registered suspects, methods and preset dials. The names are accepted by `--agents`, `--agent`, `--roster` and character filters. Plum is the network agent; archived PlumOG is not a registry name.

## `play`

```text
python scripts/clude_cli.py play --seed 1 --roster floor --verbose
python scripts/clude_cli.py play --players 3 --roster Plum,Mustard,Green --store data --run-id smoke
python scripts/clude_cli.py play --human Scarlett --roster Mustard,White --players 3
```

Prints envelope, turns, suggestions, accusations and winner. `--verbose` prints the omniscient event log, including shown cards; `--hands` adds dealt hands. Neither is a player view. Grid corridor coordinates are `(row,col)`; older ring records use HallwayCell notation.

`--human TOKEN` runs the shared TableGame driver from the keyboard. Several comma-separated tokens make a hot-seat game. `--name` sets the identity label; `?` shows the floor, `pass` skips suggestion/accusation, and accusations require confirmation. Human CLI play does not yet combine with `--llm`, `--store` or `--logbook`.

`--store URI` saves game 0 and a one-game run summary. `--run-id` sets its key; otherwise a seed/timestamp name is used. Reusing an ID overwrites its documents.

### Model and memory options

```text
python scripts/clude_cli.py play --roster Plum,Scarlett,floor --llm --llm-backend null --verbose
python scripts/clude_cli.py play --players 3 --roster Plum,Mustard,Green --store data/llm --logbook
```

`--llm` wraps character seats. `--llm-characters` restricts which characters; `--llm-model` and `--llm-backend` choose the service/backend. `anthropic` and `record:PATH` can spend money; `null` and `replay:PATH` are offline. [LLM wrapper](llm-wrapper.md) covers credentials, menu rules and fallbacks.

`--logbook [URI]` reads memory before play and updates it afterwards; omitted URI uses `--store`. `--logbook-readonly` reads without updating. `--logbook-characters` limits attachment. Without a logbook store, the memory dial alone has no effect. [Logbooks](logbooks.md) owns depth/schema details.

## `prompt`

```text
python scripts/clude_cli.py prompt --players 3 --roster Plum,Mustard,Green --viewer 2 --at 4
python scripts/clude_cli.py prompt --roster floor --agent Plum --decision move --roll 6
```

Prints system and user prompts without calling a model. `--at N` reconstructs after N suggestions; omitted means the final game. `--decision` is `move`, `suggest`, `accuse` or `show`; `--agent` overrides the viewer's roster character. `--logbook URI --memory DEPTH` includes narrative read-back. Inspect this before editing personas or checking visibility.

## `trace`

```text
python scripts/clude_cli.py trace --seed 1 --roster floor --viewer 0 --agents Plum,Scarlett
```

Queries methods after each suggestion from one viewer's redacted observation. `--every N` thins output, always retaining start/end; `--top N` or `--all-cards` controls detail. It prints the floor, per-category rankings, method diagnostics and the character's accusation threshold test. This is a reconstructed belief analysis, not a log of live agent state or a replay of model choices.

## `floor`

```text
python scripts/clude_cli.py floor --seed 1 --roster floor --viewer 0 --at 10
python scripts/clude_cli.py floor --seed 1 --roster floor --convergence
```

Shows possible holders, unresolved OR constraints and proven envelope cards. In the grid, `#` means located, `x` possible, `.` ruled out. `envelope` is a holder, not a seat index. `--convergence` prints located-card counts for every viewer over the suggestion history. `--hands` is omniscient diagnostic output.

## `benchmark`

```text
python scripts/clude_cli.py benchmark --games 12 --seed 4004 --show-green --json data/exports/bench.json
```

Scores beliefs on the same self-play snapshots. Default games: 60, seed: 4004, bot: FloorBot; table sizes cycle 3-6 unless fixed. Checkpoints are fractions of suggestions, not turns. `--bot random` selects the historical rules-exercising regime.

| Column | Interpretation |
|---|---|
| Brier | Mean squared error over all 21 cards; lower is better |
| Log-loss | Mean negative log probability of the true card per category; lower is better |
| Top-1 | Fraction of categories whose highest-probability card is correct |
| ms/call | Measured wall time, not a deterministic metric |
| fallback | Sampling fallback diagnostics, printed only when a method fell back (PlumOG) |

Uniform over the floor's allowed cards is the control. Belief quality is distinct from win rate. Agent instances persist across benchmark games, and Green receives revealed-envelope feedback after each snapshot. `--show-green` prints his final arm posteriors. `--calibration` prints each agent's accusation-test P, binned, against how often that triple was the envelope, and the accuracy at or above 0.8, 0.9 and 0.95 (also in the JSON); it is the evidence for an `accuse_threshold`. Historical enumeration fallback numbers apply to PlumOG, not current Plum.

## `train-mustard`

```text
python scripts/clude_cli.py train-mustard --games 50 --max-depth 8 --render --eval-games 8
python scripts/clude_cli.py train-mustard --mermaid docs/ux/mustard-tree.html --eval-games 0
```

Trains an inspection tree with explicit self-play/hyperparameters and optionally scores held-out games. It does not replace the registry's cached default tree. `--render` prints rules; `--mermaid [PATH]` prints a fenced diagram without PATH or writes an HTML page with PATH. The page uses vendored Mermaid, so render it in a browser. `--logbook URI` adds stored training rows. Smoothing avoids hard zeros; zero smoothing is an explicit comparison, not the default.

## Training Plum (`scripts/train_plum.py`, not a subcommand)

```text
python -m clude_training.rollout --games 8
python scripts/train_plum.py --help
python scripts/train_plum.py --iterations 20 --games 256 --workers 8
```

`python -m clude_training.rollout` (from the repo root; run as a file, like any module here, it cannot find its sibling packages) plays a few games on the committed weights and prints what the rollout records, for a look at the data before a run.

The separate PyTorch script gathers engine rollouts, fits policy/value/belief heads and evaluates the NumPy agent. It writes configuration, curve, checkpoints, `best.npz` and `latest.npz` under ignored `data/plum-training/<run>/`. `--export` additionally replaces committed `clude_agents/weights/plum.npz` with the **final** weights; it does not select the best checkpoint automatically. Export is a deliberate validated change requiring golden updates. See [weights](../clude_agents/weights/README.md) and [Phase 12](deepnash-plan.md), sections 11-12.

`scripts/leash_width.py --games 24 --seed 7007` plays Plum's table headless and counts, at each of Plum's multi-option move and suggestion menus, how many options each leash from 0.1 to 0.5 would allow, for the network and for PlumOG with his old dials (`--methods`). It is how a new method's leash is matched to an old one's menu width; PlumOG takes a couple of minutes.

## `snapshots`

```text
python scripts/clude_cli.py snapshots --games 12 --bot floor
```

Reports self-play lengths, floor convergence and training distribution. Use it to diagnose data coverage before interpreting a trained tree or benchmark. `--players`, `--checkpoints`, `--seed`, `--max-turns` and `--bot` choose the same generation inputs as the benchmark.

## `arena`

```text
python scripts/clude_cli.py arena --games 24 --seed 7007 --store data --json data/exports/arena.json
python scripts/clude_cli.py arena --games 24 --players 3 --roster Plum,Mustard,Green --set Plum.temperature=0
```

Plays full games and reports per-player seats/games, win and wrong-accusation rates, first accusation, suggestions, own cards named/leaked, re-show rate and time. Rates are per seat-game unless a column says otherwise; look at sample counts before comparing characters who sat out. `--set LABEL.DIAL=VALUE` is repeatable. `--store` saves records/summary and `--json` the complete result.

LLM flags add calls, fallbacks, deviations, talk, tokens, latency, entries and estimated cost. Model audits are in `GameRecord.llm_log`. Numerical paired runs share deals/dice; model runs add non-deterministic choices. Stored method memory changes a baseline, so freeze it with `--logbook-readonly` for comparisons.

## `sweep`

```text
python scripts/clude_cli.py sweep --dial accuse_threshold --values 0.3 0.6 0.9 --games 24
python scripts/clude_cli.py sweep --dial temperature --values 0 0.05 0.2 --characters Plum --players 3 --roster Plum,Mustard,Green
```

Runs the arena at each value on paired seeds, reporting mean/std across seeds. `--characters` limits which profiles change. `--logbook [URI]` is always read-only, so each value reads one fixed memory state. `--llm` enables model comparisons and can spend money. Curiosity is inert for current Plum; old dial results in the glossary describe dated implementations. Small sweeps show direction/magnitude, not statistical significance.

## `store`

```text
python scripts/clude_cli.py store --uri data
python scripts/clude_cli.py store --uri data --run smoke
```

Lists runs/record counts or a stored run summary. Records are omniscient. [Architecture](architecture.md#cloud-storage) owns layout and credential resolution.

### `store copy`

```text
python scripts/clude_cli.py store copy --uri data/llm --to gs://clude-game-data/llm --dry-run
```

Remove `--dry-run` to copy. Takes runs whose every record meets `--min-version` (3 by default), summaries, records, cached traces and all `logbooks/`. Excludes account documents, live tables, watch state, ring archives and loose root files. `--workers` defaults to 10. Matching keys are overwritten; destination-only objects are not deleted. This copies data, not accounts or a live service.

### `store merge`

```text
python scripts/clude_cli.py store merge --dry-run
python scripts/clude_cli.py store merge --from data/llm_bucket --into data/llm
```

Folds a bucket download (`--from`, default `data/llm_bucket`) into the local store (`--into`, default `data/llm`) in place. Both must be local folders. The download is not changed and its names win a clash. Documents that differ only in line endings are equal.

- **Runs.** If a shared game record differs, the local run becomes `<run>_local`, including its summary, records and traces. Local references to it are rewritten, such as `web/00001` → `web_local/00001`. A local record the download lacks fills its gap.
- **Logbooks.** The download's entries, head and digest stay. Local entries it lacks follow its last serial and are absorbed into its head. An entry older than the download's newest leaves newer standing instructions and reads in place. Mustard's and White's method memory takes the union of games. Green's local lessons are replayed on the download's posteriors.
- **Spend.** A shared day's spend combines both days' tables.
- **Live documents.** Accounts, tables, watch state, per-table spend and cached traces keep the download's version; the local one is dropped.
- **Everything else.** If another document differs, the local one moves to `<name>_local.json`.

Files only on the local side stay. Running it again with the same download changes nothing. `clude.bat store merge` works too, because `--uri` is ignored.

## `logbook`

```text
python scripts/clude_cli.py logbook list --uri data/llm
python scripts/clude_cli.py logbook show --uri data/llm --identity Mustard --memory 0.75
python scripts/clude_cli.py logbook rebuild --uri data/llm --identity Mustard
python scripts/clude_cli.py logbook condense --uri data/llm --all --dry-run
```

`show` prints the head/index, `--entry N` one entry, `--raw` JSON, or `--memory DEPTH` the exact read-back block. `reset --identity NAME` removes head, method memory and entries; `--keep-entries` retains the archive. `rebuild` recomputes the head and Mustard/White memory from records; `--from URI` changes source, `--min-version` defaults to 3. Green's live arm feedback cannot be reconstructed. `copy --identity Plum --to PlumOG` archives a logbook under another identity (entries, head and method memory; it refuses an existing destination). `reset-arm --arm Plum` forgets one arm of Green's stored posteriors, which then loads at Beta(1, 1); `--identity` defaults to Green. `relabel --label Plum --to PlumOG` calls an opponent by a new label in every logbook of the store (or `--identity NAME` alone): entry tables, evaluations and dossiers, the head's dossier, and White's per-opponent transition counts; `--dry-run` reports without writing. A later White `rebuild` reads labels from the game records, where PlumOG's seats say Plum, so rerun the relabel after one.

`condense --identity NAME` or `--all` asks each character's own model to fold its logbook into a digest and merge its flags ([Logbooks](logbooks.md#condensing-the-digest)); **these are paid calls**. Every identity first prints its entries to fold in, prompt words, estimated input tokens and a conservative cost, with the output priced at the call's 8192-token cap. `--dry-run` stops there and writes nothing. `--all` skips logbooks that are not a character's, such as PlumOG, which has no persona; naming one with `--identity` is refused. An identity with nothing new since its digest makes no call. `--llm-backend` and `--llm-model` work as in `play`, and `null` exercises the command without a model. A failed call writes nothing. `list` and `show` report the digest, and `show --memory` renders read-back with it.

## `tables`

| Action | Effect |
|---|---|
| `list` | Inspect active lobby tables |
| `abandon TABLE_ID` | End/remove an active table; no unfinished-game record |
| `costs` | Inspect finished LLM-game costs and possible backfills |
| `costs --write` | Write missing totals from historical daily ledgers |

All take `--uri`, default `data/llm`. Cost backfills update record, web summary and table document; older ledgers lack seat splits. Games still writing debriefs are left for the app to settle. Costs include debrief calls. Ending an already finished table does not erase its record.

## `users`

| Action | Effect |
|---|---|
| `add NAME [PASSWORD]` | Create account, default password `password` |
| `list` | List accounts without hashes |
| `passwd NAME [PASSWORD]` | Change password; prompts if omitted |
| `remove NAME` | Delete account; retain records/logbooks |

All take `--uri`, default `data/llm`. Direct `users` commands do not inherit `CLUDE_WEB_STORE`; pass the app's store explicitly when it differs. User keys are lower-case, matched case-insensitively; display names are capitalized separately. Reserved character/bot names cannot be accounts. Password handling intentionally favors convenience for this private game; see [Accounts](web.md#accounts).

## Adding a subcommand

Add `cmd_<name>(args) -> int` and its `build_parser` block with `set_defaults(fn=...)`. Keep reusable logic in packages; the script parses/prints. Add a tiny CLI smoke check and document side effects/store defaults here.
