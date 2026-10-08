---
title: Maintainer CLI
short: Terminal tools for games, measurements, memory and administration
categories: The app
redirects: CLI, Command line
---
**Maintainer CLI** is the terminal interface at `scripts/clude_cli.py`. It runs [[clude]] games and experiments, inspects stored evidence, manages memory and administers web accounts and tables. It calls the same packages used by the app; running an arena or training command is an action that creates new results, rather than a way to read the existing [[measurement record]].[^cli]

## Finding the relevant tool

From the repository root, the virtual-environment Python can run the script with `--help`. A subcommand's `--help` lists its current arguments. The CLI documentation gives full examples and explains local and cloud store URIs.

| Command | Main use |
|---|---|
| `agents` | List the supported character methods |
| `play` | Play a game, optionally with a human or model seats |
| `prompt`, `trace`, `floor` | Inspect model menus, method readings or deductions |
| `benchmark` | Score beliefs on saved snapshots |
| `train-mustard`, `snapshots` | Build Mustard's supervised training data and inspect checkpoints |
| `arena`, `sweep` | Evaluate complete games or vary a dial |
| `store` | List, inspect or copy stored runs and games |
| `logbook` | Inspect narrative and numerical memory |
| `tables`, `users` | Administer live tables and app accounts |

For example, `python scripts/clude_cli.py arena --help` describes evaluation controls without launching games. [[Replay]] and the development folders offer a browser route into already stored games.

## Experimental state

An experiment specifies its board, roster, player counts, seed schedule, profiles and memory. Model comparisons additionally need the backend, model and wrapper configuration. Commands that enable live model seats can spend money, and remembered runs can update stored experience. Read-only comparisons require a fixed starting memory rather than successive values inheriting the previous value's learning.[^arena][^memory]

[[Character training]] explains the supported training processes. [[Dial sweeps]] explains what varying one setting holds fixed, and [[twin comparison]] explains what pairing does and does not control. Saving machine-readable results alongside records makes later interpretation less dependent on a terminal transcript.

## Administration and compatibility

The app's accounts are maintained here rather than through public sign-up. Table tools can inspect or end unfinished games and backfill historical cost totals. Store tools preserve records during copies. These operations have different effects from replaying a saved game, which does not alter the original event record.

The documentation is the command reference, while the parser is authoritative for accepted options. Historical commands in the strategy glossary identify recorded experiments; rerunning them on newer code does not automatically reproduce the original result.


## See also

[[Game records]] · [[Character training]] · [[Arena]] · [[Measurement record]]

## References

{{references}}

[^cli]: {{cite:docs/cli.md}}
[^arena]: {{cite:docs/cli.md|`arena`}}
[^memory]: {{cite:docs/cli.md|`logbook`}}

{{navbox:clude}}
