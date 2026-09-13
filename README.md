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
in Cloud Storage. Phase 6, the LLM wrapper (`clude_llm`), is built and
tested on fake backends: a model chooses within a leash of each
character's own scores and adds a line of table talk, and anything
illegal or failed falls back to the character. Its live checks and arena
measurements wait on an API key ([docs/phase6-plan.md](docs/phase6-plan.md)).
There is no UI and no chat yet.

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
```

[docs/cli.md](docs/cli.md) explains every subcommand and how to read
its output.

## Layout

```
clude_core/          domain model, board, event log, GameState/ClueObservation, rules engine
clude_constraints/   the shared deduction floor (constraint propagation) and FloorBot
clude_agents/        AgentProtocol, the AgentSpec registry, one module per method,
                     and the personality layer (Profile, features, Character)
clude_llm/           the LLM wrapper: menus, personas, prompts, backends, LLMCharacter
clude_training/      self-play snapshots, the belief benchmark, post-game replay, arena, sweeps
clude_storage/       game records; local-directory and Cloud Storage record stores
scripts/             clude_cli.py, the maintainer CLI
tests/               pytest suite
docs/                architecture, phase plan, strategy glossary, CLI guide
legacy/              code from an earlier chat; ported from, never imported
```

The structure mirrors the `rps` repo (a shared protocol, a name-keyed
registry, sibling packages by concern). Planned but not yet present:
`clude_web/` (Flask/Cloud Run app, chat).

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
- [docs/llm-wrapper.md](docs/llm-wrapper.md) -- how an LLM pilots a character: menus, leash, personas, backends, cost
- [docs/strategy-glossary.md](docs/strategy-glossary.md) -- each method in plain language, with benchmark and arena results
- [docs/cli.md](docs/cli.md) -- the maintainer CLI
- [docs/board.md](docs/board.md) -- board topology and its simplifications
- [legacy/README.md](legacy/README.md) -- what the legacy code is and what is wrong with it
