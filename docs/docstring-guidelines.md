# Docstring Guidelines

Write for a maintainer meeting the API for the first time. Explain behavior, inputs, outputs, perspective and surprising constraints; keep development history and long rationale in the guides. Use NumPy-style sections where structured detail helps.

## Scope and priorities

Docstrings describe developer contracts. In-app help and MCP tool descriptions serve players; persona/rules Markdown is an executable prompt. Editing either can change model behavior, so treat it separately from inert comment cleanup.

## Required sections (for public functions/classes)

Start with a one-line summary. Add `Parameters`, `Returns` (or `Yields`), `Raises` and `Notes` when they convey information beyond names, type hints and defaults. A simple helper can use one sentence; complex boundaries should explain invalid inputs, side effects and failures.

Generators should describe yields, sent answers and delivery of the final return. Persistence/network operations should state what they read/write and whether they spend money or retry.

## Style rules

- State whose hand, belief or turn is involved. ClueObservation is per-seat; GameState/GameRecord are omniscient.
- Name encodings/order that affect callers: holder `"envelope"`, per-category belief sums, scores in candidate order.
- State RNG ownership, cache/memory dependencies and fallbacks where they affect reproducibility. Avoid claiming every CLI command is deterministic.
- Link to the owning guide for theory, measurements and phase history. Remove "later", "not yet" and phase scaffolding once shipped.
- Keep useful algorithm assumptions and compatibility notes; avoid repeating implementation narratives or Markdown tables in module docstrings.
- Prefer ASCII developer prose; preserve actual names/identifiers.

## Dual terminology conventions

Use **game/turn** for gameplay and **episode/step** for RL training. ClueObservation.turn is the game turn index; reward/return documentation identifies the seat whose transition it describes.
