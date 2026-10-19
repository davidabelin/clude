# Plum's weights

`plum.npz` is the network `clude_agents/deep_nash.py` plays with: the
arrays named in `WEIGHT_SHAPES` there, stored as float32 and read back
as float64. It is part of Plum's determinism: a seeded game depends on
the seed and on this file, as Mustard's depends on the seed and his
logbook state, so it is committed and only ever replaced on purpose,
with the goldens re-captured (`tests/test_character.py`).

As of 2026-10-18 the file is Phase 14 `run-3/stage2/latest.npz`, trained
from a fresh initialisation for two 150 x 512-game stages and selected by
the balanced four-network tournament in `docs/phase14-plan.md`. Its SHA-256
is `13e76570686ac8048d994cdb313364d4c3468f6f038ae3366fcb4b1ff3c63dbc`.
It replaced Phase 12 run 2 checkpoint 130, whose SHA-256 was
`7252746d294070839872ae819ac39c91a99c2676061d9a62fee5a7225efb4552`.
Before 2026-10-06 the file was `init_weights(INIT_SEED)`'s seeded random
draw. Training writes checkpoints under ignored local storage and cannot
replace this file.
Phase 14 promotion uses `scripts/phase14_recalibrate.py promote-plum`
with an explicitly selected checkpoint, the expected hash of this file
and a local backup path. It is a dry run unless `--apply` is supplied.
The 2026-10-18 promotion used that guard, an ignored local backup of the
former file, and `--apply`. That local promotion did not deploy anything; the separate Phase 14 release deployed these weights in revision `clude-00038-jws` on the same date. Evaluate and accept
future checkpoints before promotion, record the run and checkpoint in the
plan, then refresh the goldens and affected exact-game recordings deliberately.
