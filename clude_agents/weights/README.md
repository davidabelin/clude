# Plum's weights

`plum.npz` is the network `clude_agents/deep_nash.py` plays with: the
arrays named in `WEIGHT_SHAPES` there, stored as float32 and read back
as float64. It is part of Plum's determinism: a seeded game depends on
the seed and on this file, as Mustard's depends on the seed and his
logbook state, so it is committed and only ever replaced on purpose,
with the goldens re-captured (`tests/test_character.py`).

As of the evening of 2026-10-06 the file is checkpoint 130 of the
second training run (`run2`, resumed from the first run's checkpoint
110; `docs/deepnash-plan.md` 11 has both runs and the measurements
that chose it). Before that day it was `init_weights(INIT_SEED)`'s
seeded random draw. Training writes checkpoints under
`data/plum-training/<run>/` (gitignored) and cannot replace this file.
Phase 14 promotion uses `scripts/phase14_recalibrate.py promote-plum`
with an explicitly selected checkpoint, the expected hash of this file
and a local backup path. It is a dry run unless `--apply` is supplied.
Evaluate and accept the checkpoint before promotion, record the run and
checkpoint in the plan, then refresh the goldens deliberately.
