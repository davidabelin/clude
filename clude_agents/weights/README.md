# Plum's weights

`plum.npz` is the network `clude_agents/deep_nash.py` plays with: the
arrays named in `WEIGHT_SHAPES` there, stored as float32 and read back
as float64. It is part of Plum's determinism: a seeded game depends on
the seed and on this file, as Mustard's depends on the seed and his
logbook state, so it is committed and only ever replaced on purpose,
with the goldens re-captured (`tests/test_character.py`).

Until `scripts/train_plum.py` (Phase 12, N4) has run, the file is
`init_weights(INIT_SEED)`'s seeded random draw: a Plum who knows
nothing and plays close to uniformly. A training run exports its chosen
checkpoint here; `docs/deepnash-plan.md`'s "as implemented" section
records which run and which checkpoint.
