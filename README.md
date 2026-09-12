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

Phases 1-4 of the [phase plan](docs/phase-plan.md) are done: a headless
rules engine and event log, the deduction floor, the six strategy
agents (belief only, no actions yet), and a self-play benchmark of their
belief quality. Phase 5 -- personality profiles that turn beliefs into
actions -- is next. There is no UI, no LLM call, and no persistence yet.

## Quick start

```
C:\Users\David\AppData\Local\Python\pythoncore-3.14-64\python.exe -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest
python scripts/clude_cli.py --help
```

Python 3.14 in a plain venv, no conda. Only `pytest` is a dependency;
everything else is the standard library.

## Try it

```
python scripts/clude_cli.py play --seed 1 --verbose        # watch one random-bot game
python scripts/clude_cli.py trace --seed 1 --viewer 0      # replay every agent's belief from one seat
python scripts/clude_cli.py floor --seed 1 --convergence   # watch the deduction floor close in
python scripts/clude_cli.py benchmark --games 12           # score the six methods' beliefs
python scripts/clude_cli.py train-mustard --render         # train and inspect Mustard's tree
```

[docs/cli.md](docs/cli.md) explains every subcommand and how to read
its output.

## Layout

```
clude_core/          domain model, board, event log, GameState/ClueObservation, rules engine
clude_constraints/   the shared deduction floor (constraint propagation)
clude_agents/        AgentProtocol, the AgentSpec registry, one module per method
clude_training/      self-play snapshots, the belief benchmark, post-game replay
scripts/             clude_cli.py, the maintainer CLI
tests/               pytest suite
docs/                architecture, phase plan, strategy glossary, CLI guide
legacy/              code from an earlier chat; ported from, never imported
```

The structure mirrors the `rps` repo (a shared protocol, a name-keyed
registry, sibling packages by concern). Planned but not yet present:
`clude_storage/` (logbooks, game logs) and `clude_web/` (Flask/Cloud
Run app, chat).

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
floor, and is documented in [docs/strategy-glossary.md](docs/strategy-glossary.md).

## Documentation

- [CLAUDE.md](CLAUDE.md) -- settled decisions, proposals, and how to work on this repo
- [docs/architecture.md](docs/architecture.md) -- package layout, the deduction floor, `ClueObservation`, `AgentProtocol`
- [docs/phase-plan.md](docs/phase-plan.md) -- what each phase delivered and what is out of scope
- [docs/strategy-glossary.md](docs/strategy-glossary.md) -- each method in plain language, with benchmark results
- [docs/cli.md](docs/cli.md) -- the maintainer CLI
- [docs/board.md](docs/board.md) -- board topology and its simplifications
- [legacy/README.md](legacy/README.md) -- what the legacy code is and what is wrong with it
