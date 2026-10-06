# clude

Clue for human players, numerical agents, and LLM characters. The six suspects use different methods above a shared logical deduction floor. A character can play silently or let an LLM choose from its scored legal options and supply table talk. A chatbot can also play its own seat over MCP.

This is a private project shared with family and friends. The name is a nod to Claude. Start here, then read [the architecture](docs/architecture.md) and the guide for the part you intend to change.

## Quick start

Python 3.14 in a plain virtual environment. From the repo root in PowerShell:

```powershell
py -3.14 -m venv .venv
& .venv\Scripts\python.exe -m pip install -r requirements.txt
& .venv\Scripts\python.exe -m pytest -q -n auto
& .venv\Scripts\python.exe scripts\clude_cli.py play --seed 1 --roster floor --verbose
```

Use the venv interpreter explicitly; shell calls do not activate it for later calls. `requirements.txt` installs the developer tools, including NumPy for Plum and PyTorch for training. `requirements-web.txt` is the smaller deployment set and excludes PyTorch, pytest and Playwright. Headless games need no credentials. GCS and real LLM calls use lazy imports.

To use the browser app, put `FLASK_SECRET_KEY` in the environment or the ignored `.env`, create an account, then start Flask:

```powershell
& .venv\Scripts\python.exe scripts\clude_cli.py users add NAME --uri data/llm
& .venv\Scripts\python.exe -m flask --app clude_web run --debug
```

Open <http://127.0.0.1:5000/>. The account's default password is `password`; the first login offers a change. See [the web guide](docs/web.md) for configuration, MCP serving, accounts and deployment.

## Current state

The engine, deduction floor, six characters, benchmarks, personality dials, logbooks, web play, Watch, replay and MCP seats are implemented. Phase 10's main visual work and sound effects are built; its help layer remains open. Phase 11 reviews documentation and docstrings.

Phase 12 is replacing Plum's enumeration method with a DeepNash variant. The registry and Green's ensemble already use the new network; the committed weights are still the seeded initial weights. Training infrastructure and smoke runs exist, but trained weights have not been exported. Evaluation, dial calibration and production rollout remain separate work. Older results for Plum describe **PlumOG**, the archived enumeration agent. See [the roadmap](docs/phase-plan.md) and [Phase 12](docs/deepnash-plan.md).

## The six methods

| Suspect | Method | Module in `clude_agents/` |
|---|---|---|
| Scarlett | Naive Bayes over suggestion evidence | `naive_bayes.py` |
| Plum | Neural policy and belief heads; training uses regularised Nash dynamics | `deep_nash.py` |
| Peacock | Dempster-Shafer belief/plausibility | `dempster_shafer.py` |
| Mustard | Decision tree trained on game snapshots | `decision_tree.py` |
| Green | Thompson-sampling ensemble over the other five | `bandit.py` |
| White | Markov model over opponents' suggestion sequences | `markov.py` |

Every belief respects the observing seat's deduction floor. Character agents are locked to their own suspect tokens. Human and MCP identities follow their accounts across tokens.

New Play and Watch tables remember by default, with an opt-out. The lobby choices are **empty**, **open**, **floorbot**, **me**, **X (LLM)** and **X (headless)**. LLM seats add persona, leashed choices and narrative memory; Mustard, White and Green also have numerical method memory in either mode. CLI memory is opt-in with `--logbook`.

## Maintainer reading map

| Guide | Use it for |
|---|---|
| [Architecture](docs/architecture.md) | Package boundaries, data flow, contracts, determinism and extension points |
| [CLI](docs/cli.md) | Reproducible games, measurement, training and store/account operations |
| [Web](docs/web.md) | Configuration, player visibility, table lifecycle, MCP and deployment |
| [LLM wrapper](docs/llm-wrapper.md) | Legal menus, fallbacks, prompts, backends and metering |
| [Logbooks](docs/logbooks.md) | Numerical and narrative memory, identity, reset and rebuild |
| [Strategy glossary](docs/strategy-glossary.md) | Method explanations and dated measurement evidence |
| [Board](docs/board.md) | Map provenance, topology and movement rules |
| [Roadmap](docs/phase-plan.md) | Completed phases, current scope and unfinished work |
| [Docstring guidelines](docs/docstring-guidelines.md) | Concise public API documentation |
| [CLAUDE.md](CLAUDE.md) | Repository working rules and settled product decisions |

`clude_core/` owns rules and observations; `clude_constraints/` owns the floor; `clude_agents/` owns inference and character decisions; `clude_llm/` owns model calls; `clude_training/` owns drivers and measurement; `clude_storage/` owns persistence; `clude_web/` owns the web/MCP adapters. `scripts/` contains maintainer entry points and `tests/` the checks. `legacy/` is reference code and is never imported.

Wikiclude is the public encyclopaedia under `clude_web/wiki/`; its [plan](docs/wikiclude-plan.md) is maintained separately and is outside this Phase 11 pass.
