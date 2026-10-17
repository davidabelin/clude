# Phase 14: Recalibration

## Summary

Rebuild every adaptive method using only evidence produced after the landing-rule change, then recalibrate all eight dials against the accepted candidates. Preserve character personality ahead of small win-rate gains, replace superseded public measurements with current results, finish Wikiclude W7, and release the accepted weights, presets and method memories together behind explicit paid-call and production gates.

The current live-store inventory contributes 109 eligible records: 48 current-Plum ladder games and 61 later `web`/`web-2` games. Freeze the final inventory when Phase 14 begins so later games cannot change the experiment midway.

## Implementation

### 1. Freeze an auditable corpus and baseline

- Add a Phase 14 driver that snapshots eligible records into ignored local storage and writes a manifest containing source URI, cutoff, record hash, run/index, seed group, train/validation split and Plum generation.
- Accept only record version 3 games produced after the landing-rule commit; explicitly exclude `web/00000`–`00003`, every ring-era record and all old method-memory documents.
- Split approximately 80/20 by seed group, not individual record, so paired ladder games and repeated deals cannot cross the train/validation boundary.
- Classify Plum correctly: `web/*` describes PlumOG, while `plum-policy-ladder-*` and `web-2/*` describe the current network. Aggregate public reports without exposing human account names.
- Capture the current weights hash, presets, live method-memory hashes and baseline benchmark/arena results before training.

### 2. Retrain and accept all adaptive methods

- **Mustard:** rebuild stored-game rows from the training split and compare fresh current-rule self-play bases of 25, 50 and 100 games across depths 4/6/8, minimum leaves 10/20/40 and smoothing 1/3/6. Select by held-out Brier/log-loss and calibration, then arena-check wrong accusations and wins.
- **White:** rebuild opponent transition counts with the Plum/PlumOG mapping above; compare prior masses 1/2/4/8/16 on held-out records and arenas. Preserve per-identity behaviour without publishing identities.
- **Plum:** train three independent networks from fresh initialisation—never from the existing checkpoint—using the proven two-stage schedule: 150×512 current-rule games at the original learning regime, then 150×512 at the lower-rate Phase 12 regime. Evaluate checkpoints on untouched seeds using a 60-game belief benchmark plus paired 192-game Plum-table and six-character arenas.
- **Green:** after the other three methods are fixed, start from Beta(1,1), compare step sizes 1/2/4 and decay rates 1.02/1.05/1.10, then train the chosen configuration through 200 fresh current-rule arena games and validate on a separate 200-game block. Do not claim that old live posteriors were reconstructed.
- Promote a candidate only if it beats or remains within 0.02 log-loss of the current method at every checkpoint, introduces no new systematic calibration failure, loses no more than five win-rate points on paired validation, and preserves the character’s intended behaviour. Plum must make no wrong accusation in the validation arenas.
- If no candidate clears those gates, retain that component’s production state and record “retrained but not promoted”; do not ship a known regression merely to force a replacement.

### 3. Re-run all eight dial sweeps

- Run pooled headless sweeps against the interleaved character/FloorBot roster, 200 paired games per value:

  - `accuse_threshold`: 0.2, 0.4, 0.6, 0.8, 1.0
  - `bluff_rate`: 0, 0.25, 0.5, 1.0
  - `curiosity`: 0, 0.5, 1.0
  - `secrecy`: 0, 0.5, 1.0
  - `temperature`: 0, 0.05, 0.1, 0.2, 0.5, 2.0

- Follow with isolated 96-game screens for each applicable character: unit dials at preset ±0.2 and temperature at 0/current/twice current. Curiosity is explicitly N/A for Plum. Confirm every proposed preset change on a separate 192-game seed block.
- Use paired-seed bootstrap intervals and report both the dial’s direct footprint and secondary outcomes. Change a preset only when the footprint replicates, character differentiation remains recognisable, and validation stays within the five-point win, five-point wrong-accusation and ten-per-cent game-length guardrails.
- Before paid runs, analyse leash menu widths, chattiness opportunities and memory prompt sizes offline. Quote the resulting cost and obtain explicit approval.
- With the current production model and frozen code:

  - Screen leash per character for eight games at 0, current, current+0.25 capped at 1, and 1.
  - Screen chattiness at 0, 0.25, 0.5, 0.75 and 1 over eight paired four-seat games per value; judge off-turn replies and tokens because on-turn speech is no longer gated.
  - Screen memory at the same five values against one read-only snapshot of the accepted logbooks, with no debrief writes.
  - Confirm current versus the single shortlisted value for each affected dial with 24 paired games.

- Stop and discard a paid leg if credentials are absent, fallbacks or token caps compromise pairing, or the frozen memory/code revision differs. Refresh exact-game fixtures only once, after final weights and presets, under a separate approved cost.

### 4. Evidence, Wikiclude and release

- Record commands, manifests, sample sizes, seeds, costs, rejected candidates and accepted results in a new Phase 14 plan and a current-results section of the strategy glossary. Update the roadmap, maintainer guides and docstrings with only accepted behaviour.
- Update Wikiclude after each accepted gate: adaptive-method pages first, headless dial and character pages second, then Leash, Chattiness, Memory dial and related model pages after paid confirmation.
- Rewrite *Dial sweeps* and *Measurement record* around Phase 14. Keep one short public archive note acknowledging superseded experiments, but remove their detailed tables and calibration claims from public articles and delete now-unused historical fact keys. Preserve the detailed evidence in maintainer plans, the glossary and git.
- Keep article titles stable. Update `facts.py`, citations, figures and character biographies together, using direct British English, current sample context and no universal claims from zero observed failures.
- Fold W7 into the final gate: reread the whole corpus, run link/fact/citation audits and inspect representative pages at 390 and 1440 pixels in all three looks.
- Stage Mustard, White and Green method documents without touching narrative heads, digests or entries. Add dry-run and expected-hash checks plus a local backup for method-only promotion.
- After explicit release approval, require no open tables, deploy the accepted code/weights/presets, promote the three staged method documents, run offline and live acceptance, and verify the public wiki. Roll back to the previous Cloud Run revision and restore the backed-up method documents if acceptance fails.
- Finish with repository status/diff review and a paste-ready, uncompiled Markdown commit message for VS Code.

## Interfaces and artifacts

- No gameplay, web, MCP or `GameRecord` schema change.
- Add a versioned Phase 14 corpus-manifest format and a read-only loader shared by training and reports.
- Add a Phase 14 maintenance command with `snapshot`, `stage-methods`, `report` and guarded `promote` operations; mutation requires `--apply`, expected source hashes and backup paths.
- Extend sweep JSON with corpus/code/weights hashes, per-character rows, paired deltas, confidence intervals, tokens and estimated/actual cost.
- Promote Plum only from an explicitly selected checkpoint; never let the trainer’s final checkpoint overwrite committed weights automatically.

## Test and acceptance plan

- Unit-test cutoff/version filtering, record hashing, seed-group splitting, Plum/PlumOG classification, identity privacy and manifest reproducibility.
- Test deterministic Mustard/White rebuilds, Green’s fresh-state training, checkpoint validation and method-only promotion/rollback.
- Test all dial grids, paired seeds, immutable memory input, N/A dials, cost/token aggregation and interruption-safe result files.
- Re-capture character goldens and both recorded LLM games only after final acceptance; retain previous recordings in history.
- Run focused agent, training, arena, memory, LLM and Wikiclude tests, then the complete offline suite and `git diff --check`.
- Treat local tests, paid behavioural acceptance, production deployment and live-store promotion as separate evidence gates.

## Assumptions

- “Post-landing-rule” begins after commit `dda86f0`; the four earlier `web` records are excluded even though they are version 3.
- “All adaptive methods” means Plum, Mustard, White and Green; Scarlett and Peacock have no persistent trainable state.
- Character personality outranks small performance gains.
- Paid work and production mutation each require fresh explicit approval.
- Phase 14 includes the final W7 reread and a full gated production release.

## Implementation record

### Frozen corpus and baseline — complete locally, 2026-10-17

`scripts/phase14_recalibrate.py snapshot` listed the source keys before
reading any record, then scanned 1,435 live-store records without writing to
the bucket. Exactly 109 version 3, post-`dda86f0` records were eligible. The
67 indivisible seed groups split into 90 training and 19 validation records;
the four explicit `web/00000`–`00003` exclusions and 1,322 records at or
before the cutoff were recorded separately. The copied corpus hash is
`de43af10c37148ec2e174c9c1f896a30cad05af3495aed6a8e666fc204708051`.
The ignored local snapshot also holds hash-checked copies of the three
pre-training method documents; no narrative logbook document was copied into
a candidate or changed live.

The frozen baseline is `data/phase14/baseline.json`: 60 current-rule belief
games and paired 192-game Plum-table and six-character arenas. This is local
evidence, not production acceptance. Among the reference arena results, Plum
won 31.8% with no wrong accusation at his three-character table and 17.2%
with no wrong accusation when seated in the six-character rotation.

### Mustard and White — accepted locally, not released

Mustard's 81-candidate search found one configuration that cleared every
held-out checkpoint: 50 fresh self-play games, depth 6, minimum leaf 40 and
smoothing 1. Its validation log-loss was lower than the frozen live method at
all four checkpoints. In the paired 192-game arena it gained 3.1 win-rate
points and added 4.7 wrong-accusation points, inside the five-point guardrail.
It remains the same self-play regression-tree character, so the configuration
is accepted in code. The post-ring training rows are staged locally only.

White's post-ring counts keep `web` Plum contributions under `PlumOG` and
current-policy contributions under `Plum`, without publishing human labels.
Prior mass 2 was the best candidate that cleared every held-out loss and
calibration check; its paired arena lost 3.1 win-rate points and did not add
wrong accusations. It preserves the per-identity repeat/new method and is
accepted in code. The counts document is staged locally only.

Plum, Green, all dial sweeps, paid confirmation, fixture refresh, production
deployment and live method promotion remain open. The trainer cannot export
committed weights; checkpoint and method promotion are separate hash-guarded,
backed-up dry runs unless `--apply` is explicitly supplied.
