# clude

A web app for playing Clue with a mix of human and LLM players. Each LLM character uses a distinct probabilistic reasoning method: Naive Bayes, Exact Bayesian Inference, Dempster–Shafer, Decision Trees, Multi-Armed Bandits, and Markov Models.

**Status:** Early development. Phase 2 (deduction floor and rules engine) is complete. See [CLAUDE.md](CLAUDE.md) for design details and project roadmap.

## Quick Start

```bash
python -m pytest tests/
```

## Architecture

The project follows the structure of David's `rps` repository:

```
clude/
├── clude_agents/        # Agent implementations (one per suspect)
├── clude_core/          # Rules engine and domain logic
├── clude_constraints/   # Deduction and constraint propagation
├── clude_web/           # Web frontend (planned)
├── scripts/             # Utilities and CLI tools
├── tests/               # Unit and integration tests
├── docs/                # Architecture and design documentation
├── legacy/              # Code from earlier iterations
└── CLAUDE.md            # Detailed project notes and decisions
```

## The Six Agents

Each suspect is implemented as an agent with its own reasoning model:

| Suspect | Method | Flavor |
|---------|--------|--------|
| Scarlett | Naive Bayes | Overconfident, accuses early |
| Plum | Exact posterior enumeration | Correct but slow |
| Peacock | Dempster–Shafer | Cautious, won't commit early |
| Mustard | Decision tree | Pattern-matches, confidently wrong |
| Green | Multi-armed bandit ensemble | Adapts over time |
| White | Markov model | Reads opponents |

All agents implement a shared `AgentProtocol` with `reset()`, `select_action()`, and `observe()` methods.

## Key Concepts

- **Deduction Floor:** Constraint propagation layer that masks logically impossible worlds before agent reasoning. Agents receive only valid hypotheses.
- **ClueObservation:** Unified event contract consumed by all agents; rich enough to support post-game replay of all belief traces.
- **Logbooks:** Each agent writes persistent game records; later used for training Mustard's decision tree and history for White's Markov model.

## Next Steps

See [CLAUDE.md](CLAUDE.md) for:
- Full design decisions and philosophy
- Proposed features and shelved ideas
- Development roadmap (phases 1–8)
- Collaboration guidelines

For architectural details, see [docs/architecture.md](docs/architecture.md).

For notes on the earlier codebase, see [legacy/README.md](legacy/README.md).

## Development

- Python 3.14 with venv (no conda)
- Windows 11 environment
- See [CLAUDE.md](CLAUDE.md) for collaboration guidelines
