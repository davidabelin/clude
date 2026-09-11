# Docstring Guidelines

This project uses **NumPy-style docstrings** for developer-facing code, same
convention as `rps`.

## Scope and priorities

- Primary audience for docstrings: developers/maintainers.
- Primary audience for in-app explanatory UI copy: players.
- Use dual terminology based on context:
  - gameplay: **game / turn**
  - RL/training (Mustard's tree, benchmark self-play): **episode / step**

When both are valid, write both once, e.g. `turn index (episode step)`.

## Required sections (for public functions/classes)

- One-line summary in imperative tone.
- Optional short context paragraph if behavior is non-obvious.
- `Parameters`
- `Returns`
- `Raises` (when applicable)
- `Notes` (when tradeoffs/assumptions matter -- e.g. an agent's belief is an
  approximation, or a fallback path exists)

## Style rules

- Keep docstrings behavior-oriented, not implementation-narrative.
- Document perspective explicitly where it's ambiguous: whose hand, whose
  belief, whose turn (`ClueObservation` is always from the observing
  agent's perspective).
- State any encoding explicitly (e.g. envelope holder is the string
  `'envelope'`, not an index -- see the deduction-floor convention in
  `docs/architecture.md`).
- Prefer ASCII; avoid symbolic shorthand unless already standard.
- Keep private helper docstrings short unless the helper is tricky.

## Dual terminology conventions

- `ClueObservation.turn`: turn index for gameplay, or step index within a
  self-play episode (Phase 4+ benchmarking, Mustard's training data).
- `reward_delta` (Phase 4+ benchmarking only): always from the perspective
  of the actor represented by that transition.
