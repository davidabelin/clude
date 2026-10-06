# Plum's weights

`plum.npz` is the network `clude_agents/deep_nash.py` plays with: the
arrays named in `WEIGHT_SHAPES` there, stored as float32 and read back
as float64. It is part of Plum's determinism: a seeded game depends on
the seed and on this file, as Mustard's depends on the seed and his
logbook state, so it is committed and only ever replaced on purpose,
with the goldens re-captured (`tests/test_character.py`).

As of 2026-10-06, no training run has been exported. The committed
file is `init_weights(INIT_SEED)`'s seeded random draw: a Plum who
knows nothing and plays close to uniformly. Training writes checkpoints under
`data/plum-training/<run>/` (gitignored). `--export` replaces this file with
the final state, not an automatically selected best checkpoint. Evaluate
before replacing it, record the exported run/checkpoint in
[Phase 12](../../docs/deepnash-plan.md), and refresh the goldens each time.
