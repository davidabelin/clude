# clude

Private Clue game for family and friends, with human, numerical and LLM players. Owner: David Abelin (github.com/davidabelin). Call him David, never Dave. The name is a nod to Claude.

## Read this first

Start with `git log --oneline -5` and `git status`, then [the roadmap](docs/phase-plan.md) and the active phase's plan. Current guides describe the code; completed plans explain historical decisions. Where an older proposal and its implementation record disagree, trust the implementation record, then verify against code before changing it.

## Status (2026-10-07)

Phases 1-9 are implemented. Phase 10's main UX/sound work is built; 10h help remains open. Wikiclude has its own [plan](docs/wikiclude-plan.md) and is outside Phase 11. The canon (2026-10-09), Wikiclude read by LLM and MCP players, is built and tested offline, not deployed; both replay fixtures are stale until re-recorded.

Phase 11 condenses maintainer docs and docstrings. Phase 12 is complete and deployed (2026-10-07, revision `clude-00026-bsp`): N2-N4 (scoring hooks, NumPy Plum, rollout/trainer) are built, and the committed weights are a trained checkpoint (the second long run's 130, exported 2026-10-06: 49% at his own table, 22% at the six-character table, the best mid-game belief on record). N1's logbook commands, N5's headless evaluation (presets kept), N6's paid ladder (leash 0.35 kept, $0.09 a typical seat-game; both LLM fixtures re-recorded) and N7's wiki pass are done; the engraved portraits are in the character infoboxes; the bucket's logbooks are archived (PlumOG) and relabelled, and a further training run is optional. PlumOG is archived, not seatable. [Phase 12](docs/deepnash-plan.md) contains evidence and acceptance steps; [the roadmap](docs/phase-plan.md) owns status. Checkout state does not confirm live deployment.

## Settled decisions (David's)

- **Six distinct methods.** Each suspect has its own agent, rather than one algorithm with six profiles. [README](README.md#the-six-methods) lists the mapping. Green ensembles the other five.
- **Shared deduction floor.** Methods honor logical constraints; differences concern uncertainty. Character turns numbers plus Profile into actions; LLMs choose inside scored legal menus and add voice.
- **Private Classic game.** Real names/rules, fresh visual assets, Python 3.14 in a plain venv, Cloud Run deployment. Public publication requires a separate IP scrub. Nothing new in the cloud project without approval.
- **Seat-locked characters.** Characters play their own tokens. People/MCP accounts keep identity across tokens; records and dossiers use normalized keys, display names are capitalized.
- **Talk and bluffing about own cards: allowed.** Formal refutation uses actual hands; refusing a required reveal is a house-rule backstop. Chat claims never replace engine checks.
- **Persistent logbooks.** Mustard, White and Green retain method memory; LLM seats additionally read/write narrative entries. New web Play/Watch tables remember; only Developer shows the opt-out (and the LLM budget); CLI opts in. Stored settings are retained. `memory=0` means condensed read-back, not off; lobby LLM seats start at 1. `logbook condense` has a character's own model fold its entries into a digest (paid; entries kept as the archive). [Logbooks](docs/logbooks.md) owns details. Debriefs see the whole deal face up.
- **Convenience over secrecy.** CLI-created, case-insensitive accounts default to `password`; any non-empty password is accepted and first login offers a change once. Later changes use `users passwd`. Passwords are stored as hashes. App login, CSRF and rate limits remain.
- **MCP players are web players.** Chatbots use their own account and `clude_login`, supplying the returned login to tools. A secret path guards transport; account login guards game operations.
- **No persona advises a chat seat.** It gets the floor's notepad and reasons for itself; no character method/persona is behind it.
- **Wikiclude is the canon.** LLM seats carry its index and two lookup tools inside their calls; MCP players have two loginless wiki tools. Trusted by default, never cited aloud; propensity is persona prose, measured by audited lookups, capped per call and per game. [The canon plan](docs/canon-plan.md) owns details.
- **Tables end, seats time out, the deal waits.** Open seats must fill before dealing. Anyone seated or the starter can end a table. Decisions time out after 90 s (30 s in speed mode); card-show decisions get at most 30 s. FloorBot plays that turn; three consecutive timed-out turns hand the seat over. Chat does not reset the deadline.
- **Spectators, and what the seat bars give away.** Live spectators need accounts and see compact readings, which can reveal hand composition indirectly. This is an accepted social boundary. Seated players receive no spectator `readings`; everybody sees certainty tags on a bits-gained scale. Full replay is face up.
- **Current UX.** Case-file light is default, Gaslight dark is fixed dark, Developer preserves Legacy's stylesheet and alone displays costs. `legacy.css` stays frozen. Methods appear on the seat rail; Talk and Record are separate. Six synthesized sound cues, opt-in; no music. [Phase 10](docs/phase10-plan.md) retains D1-D34 and rationale.
- **Wikiclude.** Public encyclopaedia, Wikipedia-style layout in clude's looks, linked articles for lay/technical readers together. Its own plan governs article work, outside this pass.
- **Say agents and personas** in prose; avoid calling either a "head". Keep actual identifiers (`LogbookHead`, `head.json`), network heads and the lobby's `(headless)` label where they identify concrete concepts.
- **Plum, Phase 12.** PlumOG stays archived/unseatable; NumPy runs the new agent, developer-only PyTorch trains it against a mixed population. Its academic/pedantic voice stays; its method description follows the network. Validate trained weights before export; get paid-refresh approval. Old Plum measurements do not validate the new policy.

## Architecture in brief

`clude_core` owns rules/redacted observations; `clude_constraints` attaches a fresh floor; `clude_agents` produces masked beliefs and Character decisions; `clude_llm` wraps them; `clude_training` supplies measurement/resumable drivers; `clude_storage` persists documents; `clude_web` serves browser/MCP transports on one TableRegistry. Never expose omniscient state to a player. Beliefs normalize per category, force eliminated candidates to zero and proven ones to one.

[Architecture](docs/architecture.md) owns contracts, replay limitations and determinism. Keep setup in README, operations in CLI/Web, memory in Logbooks, measurements in the glossary and status in the roadmap; link instead of copying.

## Working with David

- Agree on scope before code; update active plans/implementation records. Change working systems incrementally.
- Prefer simple modular code, concise behavior-oriented docstrings and meaningful tests. Run the whole offline suite before calling work done.
- Give an independent assessment. Correct wrong numbers wherever they propagated; distinguish offline evidence from live acceptance.
- David commits from VS Code. After non-trivial changes, print a paste-ready commit message as **uncompiled Markdown in a code block**: title, short rationale, bullets as needed, without hard-wrapping bullets. Do not write `commit_msg.md`, commit or push on his behalf. Do not invent a co-author identity.
- Quote costs/run sizes and get approval before real API calls. Store measurements with `--store data/llm` and `--json PATH`.
- Persona/rules files are executable prompts. Exact text affects replay keys: never relabel old recordings as new. Phase 11 prompt updates leave fixtures pending a separately approved paid refresh.
- Ask about product ambiguities while continuing independent work. Use game/turn for play and episode/step for training.

## Environment and how to run

**David works in Windows cmd.exe, not PowerShell**, with the `clude` venv activated (his prompt reads `(clude) Thu 10/08/2026 17:26:51.94 >`). Commands for him to run are cmd syntax from the repo root: `python ...` (the active venv's), `clude ...` for clude.bat, `scripts\deploy.bat`. Never give him PowerShell's `& .venv\...` or `$env:` forms.

```bat
python -m pytest -q -n auto
python scripts\clude_cli.py --help
```

An agent's own tool calls on his machine may run without the venv: there, use `.venv\Scripts\python.exe ...` explicitly, since bare Python may resolve outside the venv. Tool calls do not share exported variables; set them in the call needing them.

[README](README.md) owns installation; [Web](docs/web.md) owns configuration, optional browser/live checks and deployment. Direct CLI defaults to local stores; **clude.bat defaults users/tables/logbook/store to the live bucket** unless `--uri` is explicit.

Secrets and `data/` are ignored. Never print/commit `.env` or `clude-game-sa.json`. Cloud Run uses `clude-run@clude-game.iam.gserviceaccount.com`. Cloud commands must name `--account=clude-sa@clude-game.iam.gserviceaccount.com` and `--project=clude-game`: the active configuration may belong to another project. [scripts/deploy.bat](scripts/deploy.bat) is the canonical deploy command, not an instruction to deploy this pass.

## Open questions (ask, don't assume)

[The roadmap](docs/phase-plan.md) tracks help/release scope and Phase 12 acceptance. Shelved alternatives, historical spend approvals and old theme defaults are not current instructions. Phase 8.0.4 resolved the parking problem.

## Docs map

Use [README's reading map](README.md#maintainer-reading-map). Completed plans preserve decisions/deviations; the glossary retains dated tables. Wikiclude's plan stays separate.
