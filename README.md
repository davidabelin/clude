# clude

A web app for playing Clue with a mix of human and LLM players. Each of
the six suspects is an LLM character backed by a genuinely different
probabilistic method -- naive Bayes, exact posterior enumeration,
Dempster-Shafer, a decision tree, a bandit ensemble, and a Markov model
-- all sharing one logical deduction floor, so they differ in how they
reason under uncertainty and never in what is certain.

Private project, shared with family and friends. The name is a nod to
Claude. See [CLAUDE.md](CLAUDE.md) for the design decisions and the
working notes that drive development.

## Status

Phases 1-5 of the [phase plan](docs/phase-plan.md) are done: a headless
rules engine and event log, the deduction floor, the six strategy
agents, a self-play benchmark of their belief quality, and now the
personality layer that turns each agent's belief into moves, with an
arena and dial sweeps to measure it and game records stored locally or
in Cloud Storage. Phase 6, the LLM wrapper (`clude_llm`), is done: a
model chooses within a leash of each character's own scores and adds a
line of table talk, and anything illegal or failed falls back to the
character. It is live-checked, persona-tuned and measured on Opus 5
([docs/phase6-plan.md](docs/phase6-plan.md), results in
[docs/strategy-glossary.md](docs/strategy-glossary.md)). Phase 7,
logbooks, is built: every character has a persistent memory in the
record store, numeric for the three methods that can use one and, for
an LLM-piloted seat, a zenbot-shaped entry its own model writes after
each game and reads back before the next at the depth of a `memory`
dial ([docs/phase7-plan.md](docs/phase7-plan.md),
[docs/logbooks.md](docs/logbooks.md)), live-checked and measured on
Opus 5: at leash 0.5 Plum's own notes cut his stalls by more than half
over 24 games, at the price of two early accusations
([docs/strategy-glossary.md](docs/strategy-glossary.md)). Since
2026-09-14 every character is locked to its own token: Plum is always
Plum. Phase 8.1 put the first screens in front of it: a Flask app with a
login, a lobby, a replay scrubber and a Watch screen, run locally or on
Cloud Run for family and friends ([docs/web.md](docs/web.md)). Since
Phase 8.2 people sit at the table too: a table in the lobby seats you
beside the characters and the game is played from the browser, or from
the terminal with `play --human`. Since Phase 8.3 a character can play
as **X (LLM)** at a web table under a spend cap, people talk at the
table and the model seats answer off-turn, and a remembering table ends
with each model seat writing its logbook.

New Play and Watch tables **remember by default**, with a checkbox to
opt out. The seat choices are **empty**, **open**, **floorbot**,
**me (signed-in name)**, **X (LLM)** and **X (headless)**. X is that seat's
named character: LLM adds Claude's choices, voice and narrative logbook;
headless plays silently using its numerical method. Mustard, White and
Green retain method memory in either mode. LLM seats have a memory-depth
dial (0 = condensed notes, 1 = full entries); they require a service key.
CLI memory still requires `--logbook`. See [the lobby guide](docs/web.md#the-lobby).

## Quick start

```
C:\Users\David\AppData\Local\Python\pythoncore-3.14-64\python.exe -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest
python scripts/clude_cli.py --help
```

Python 3.14 in a plain venv, no conda. `pytest`, `google-cloud-storage`
and `anthropic` are the only dependencies; the last two are imported
lazily (for `gs://` record stores and for LLM-piloted seats), so
everything else runs on the standard library.

## Try it

```
python scripts/clude_cli.py play --seed 1 --roster floor --verbose      # watch a deduction-driven game
python scripts/clude_cli.py play --roster Plum,Scarlett,Peacock,floor    # watch three characters play
python scripts/clude_cli.py trace --seed 1 --roster floor --viewer 0     # replay every character's belief from one seat
python scripts/clude_cli.py floor --seed 1 --roster floor --convergence  # watch the deduction floor close in
python scripts/clude_cli.py benchmark --games 12                         # score the six methods' beliefs
python scripts/clude_cli.py arena --games 24                             # who wins, who accuses wrongly
python scripts/clude_cli.py sweep --dial accuse_threshold --values 0.2 0.6 1.0
python scripts/clude_cli.py play --roster Plum,Scarlett,floor --llm --verbose   # LLM-piloted seats (needs ANTHROPIC_API_KEY)
python scripts/clude_cli.py prompt --roster Plum,Scarlett,floor --viewer 1     # what that seat's model would be sent
python scripts/clude_cli.py play --roster Plum,Mustard,Green --players 3 --store data --logbook   # play with memory on
python scripts/clude_cli.py logbook show --uri data --identity Mustard        # what a character has remembered
```

[docs/cli.md](docs/cli.md) explains every subcommand and how to read
its output.

## Layout

```
clude_core/          domain model, board, event log, GameState/ClueObservation, rules engine
clude_constraints/   the shared deduction floor (constraint propagation) and FloorBot
clude_agents/        AgentProtocol, the AgentSpec registry, one module per method,
                     and the personality layer (Profile, features, Character)
clude_llm/           the LLM wrapper: menus, personas, prompts, backends, LLMCharacter, the debrief
clude_training/      self-play snapshots, the belief benchmark, trace, record replay, method memory, arena, sweeps
clude_storage/       game records and logbooks; local-directory and Cloud Storage stores
clude_web/           the Flask app: the login gate, accounts, the lobby, tables people play at, Watch and the replay; and `mcp.py`, a seat a Claude in a chat window plays over MCP
Dockerfile           the Cloud Run image (with requirements-web.txt, .gcloudignore, .dockerignore)
scripts/             clude_cli.py, the maintainer CLI
tests/               pytest suite
docs/                architecture, phase plan, strategy glossary, CLI guide
legacy/              code from an earlier chat; ported from, never imported
```

The structure mirrors the `rps` repo (a shared protocol, a name-keyed
registry, sibling packages by concern). `clude_web/` is the newest: the
login gate, the lobby, the table you play at, the replay and Watch
screens, served locally with `flask run` or from Cloud Run
(`docs/web.md`, "Deploying").

## The six

| Suspect | Method | Module | Intended flavor |
|---|---|---|---|
| Scarlett | Naive Bayes | `naive_bayes.py` | Overconfident, accuses early |
| Plum | Exact posterior enumeration | `exact_enum.py` | Correct but slow |
| Peacock | Dempster-Shafer belief/plausibility | `dempster_shafer.py` | Cautious until plausibility collapses |
| Mustard | Decision tree on self-play logs | `decision_tree.py` | Pattern-matches, confidently wrong on unusual deals |
| Green | Bandit ensemble over the other five | `bandit.py` | Opportunistic, only as good as his arms |
| White | Markov model over suggestion sequences | `markov.py` | Reads people rather than cards |

Every agent implements `reset` / `select_action` / `observe`, returns a
belief over the 21 cards already masked and renormalized against the
floor, and plays through a `Character` that combines that belief with
five personality dials. Each is documented in
[docs/strategy-glossary.md](docs/strategy-glossary.md).

## Documentation

- [CLAUDE.md](CLAUDE.md) -- settled decisions, proposals, and how to work on this repo
- [docs/architecture.md](docs/architecture.md) -- package layout, the deduction floor, `ClueObservation`, the engine seam, `AgentProtocol`, the personality layer, storage
- [docs/phase-plan.md](docs/phase-plan.md) -- what each phase delivered and what is out of scope
- [docs/phase5-plan.md](docs/phase5-plan.md) -- the Phase 5 plan, David's decisions, and how the build departed from it
- [docs/phase6-plan.md](docs/phase6-plan.md) -- the Phase 6 plan, David's decisions, and what was built
- [docs/phase7-plan.md](docs/phase7-plan.md) -- the Phase 7 plan, David's decisions, and what was built
- [docs/phase8-plan.md](docs/phase8-plan.md) -- Phase 8 to completion: the landing rule, human players, the model and chat on the web, and what was built
- [docs/web.md](docs/web.md) -- the Flask app: running it, accounts, the table, Watch, the replay, and deploying to Cloud Run
- [docs/llm-wrapper.md](docs/llm-wrapper.md) -- how an LLM pilots a character: menus, leash, personas, backends, cost
- [docs/logbooks.md](docs/logbooks.md) -- playerbot memory: the three tiers, the `memory` dial, the debrief, the CLI
- [docs/strategy-glossary.md](docs/strategy-glossary.md) -- each method in plain language, with benchmark and arena results
- [docs/cli.md](docs/cli.md) -- the maintainer CLI
- [docs/board.md](docs/board.md) -- board topology and its simplifications
- [legacy/README.md](legacy/README.md) -- what the legacy code is and what is wrong with it
