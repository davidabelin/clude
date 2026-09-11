"""Self-play data generation, training, and benchmarking. Deliberately
minimal (no eager submodule imports) so `clude_agents.decision_tree` can
depend on `clude_training.self_play` without a cycle back through
`clude_training.benchmark`, which depends on `clude_agents` -- see
docs/architecture.md.
"""
