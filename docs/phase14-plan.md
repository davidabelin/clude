# Phase 14: Recalibration

## Summary

Rebuild every adaptive method using only evidence produced after the landing-rule change, then recalibrate all eight dials against the accepted candidates. Preserve character personality ahead of small win-rate gains, replace superseded public measurements with current results, finish Wikiclude W7, and release the accepted weights, presets and method memories together behind explicit paid-call and production gates.

Completed and released on 2026-10-18; the implementation record below owns acceptance. The following implementation sections preserve the agreed experimental design. The frozen inventory contains 109 eligible records: 48 current-Plum ladder games and 61 later `web`/`web-2` games. Later games are outside that snapshot.

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
- Promote a candidate only if it beats or remains within 0.02 log-loss of the current method at every checkpoint, introduces no new systematic calibration failure, loses no more than five win-rate points on paired validation, and preserves the character’s intended behaviour. Plum's headless wrong accusations are reported to the LLM head as evidence, not used as a network rejection gate.
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
- Re-capture character goldens and each affected recorded LLM game only after final acceptance; retain previous recordings in git history.
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
was accepted in code and its post-landing-rule rows staged at this gate.
The release acceptance below records the subsequent live promotion.

White's post-landing-rule counts keep `web` Plum contributions under `PlumOG` and
current-policy contributions under `Plum`, without publishing human labels.
Prior mass 2 was the best candidate that cleared every held-out loss and
calibration check; its paired arena lost 1.25 win-rate points (55 versus 57
wins in 160 White seat-games within each 192-game leg) and did not add wrong
accusations. The 95% paired win interval was -11.875 to 8.75 points, so this
was acceptance within the guardrail, not evidence of improved winning. It
preserves the per-identity repeat/new method and was accepted in code. The
counts document was staged locally at this gate; its production promotion is
recorded under release acceptance.

### Plum and Green — retrained; Run 3 promoted locally

All three independent Plum runs completed on CUDA. Each run trained for
150×512 games at the original regime and another 150×512 games at the Phase 12
lower-rate regime, for 460,800 current-rule rollouts in total. Stage 2 reused
stage 1's seed block: the trajectories changed with the policy, but the three
runs contain 230,400 distinct seeded deal/line-up setups rather than 460,800.
The trainer did not overwrite the committed weights. A first checkpoint
evaluation found no candidate that cleared every original promotion gate, so
the incumbent remained the headless default while the result was investigated.

A first four-way tournament compared the incumbent with each run's full
`stage2/latest.npz` checkpoint. Every entrant received the same fresh deals,
dice, Plum seat and opponents. The selection block used 384 games per entrant
in each context; the untouched confirmation block used 768. Plum appeared in
1,920 games per entrant across a fixed Plum/Mustard/Green table and a rotating
three-to-six-player roster. Run 3 led the pooled win ranking at 30.8%, followed
by run 1 at 29.9%, the incumbent at 27.9% and run 2 at 27.7%. All three new
runs cleared the checkpoint log-loss guardrail. Run 3's confirmation advantage
over the incumbent was 4.6 points (95% paired bootstrap interval 0.3 to 8.7)
at the fixed table, but 2.1 points (-2.7 to 7.0) in the mixed tables; it was
also not distinguishable from run 1 in either context. Every entrant made
wrong accusations over the larger sample (seven for run 3 and the incumbent,
eight for run 1 and seven for run 2). This run is retained as a historical
fixed-table diagnostic, not as the selection tournament: 60% of its Plum games
used only Mustard and Green, so its pooled result was not roster-balanced.

The replacement tournament enumerated all 26 possible line-ups containing
Plum. Each entrant played 240 games at each table size per block, with every
opponent appearing exactly 672 times; selection and confirmation used separate
960-game seed blocks. Across the 1,920 games per entrant, run 3 led at 22.9%,
then run 1 at 22.0%, run 2 at 21.7% and the incumbent at 18.3%. On the untouched
confirmation block, run 3 beat the incumbent by 4.9 points (95% paired
bootstrap interval 1.5 to 8.3), while run 1 beat it by 3.4 points (0.1 to 6.9).
Run 3 did not separate from run 1 (1.5 points, -2.3 to 5.1) or run 2 (2.5
points, -1.1 to 6.0). Every candidate cleared the checkpoint log-loss guardrail.
Wrong accusations are reported for the LLM head, not used to reject a headless
network. Run 3 is the best observed replacement, though the paired evidence
does not establish a unique winner among the three new networks. David selected
Run 3 on 2026-10-18.

The guarded promotion dry run checked the former committed hash
`7252746d294070839872ae819ac39c91a99c2676061d9a62fee5a7225efb4552`.
The `--apply` run copied `data/phase14/plum/run-3/stage2/latest.npz` to
`clude_agents/weights/plum.npz`, backed the former file up under ignored local
storage, and verified the new hash
`13e76570686ac8048d994cdb313364d4c3468f6f038ae3366fcb4b1ff3c63dbc`.
This was the accepted network in the checkout at the local promotion gate;
the release acceptance below records its subsequent deployment.
`balanced-tournament.json` retains the balanced paired evidence and resumable
configuration locally.

Green's nine-candidate fresh-state search selected step size 4 and decay 1.05.
It cleared every held-out loss/calibration checkpoint and the separate
200-game validation arena, gaining 2.3 win-rate points and reducing wrong
accusations by 2.3 points against the frozen pre-training live posterior
(26 games), not a fresh-state comparator. Each candidate itself began at
Beta(1,1); the old posterior was used only for evaluation. Its 200-game state
was staged locally with Mustard and White at this gate. All three were
subsequently promoted live at release acceptance.

Run 3 changed three deterministic character fingerprints: two because Green
can select his Plum arm and one at the four-character table containing Plum.
Those goldens were deliberately re-captured. The affected `llm_seed2` exact
game was re-recorded with explicit paid approval on 2026-10-18: six calls, no
fallbacks or lookups, $0.0348 estimated. It retained the seeded envelope, White
as winner, ten turns and two suggestions. `llm_seed1` contains no Plum, still
replayed exactly and was not re-recorded.

### Dial recalibration — complete locally

The pooled headless sweeps used seed 142000, 200 paired games per value and
the interleaved character/FloorBot roster across three- to six-player tables.
The follow-up covered all 29 applicable character/dial combinations at three
values and 96 games per value, or 8,352 games; Plum's curiosity was correctly
N/A. The direct footprints replicated: raising accusation threshold sharply
reduced wrong accusations, bluff rate raised held-card naming, curiosity
reduced suggestions and lengthened games, secrecy raised re-showing, and high
temperature lengthened games and reduced wins. No isolated candidate cleared
the personality and outcome guardrails, so no headless preset changed.

The paid screen froze `claude-opus-5`, code, corpus, Run 3 weights, staged
method documents and one read-only logbook snapshot. Provider credit
exhaustion contaminated the first memory-0.5 row: its 285 calls, 125 fallbacks
and $2.1106 estimate remain as interruption provenance but are excluded from
the result. After credit returned, only memory 0.5, 0.75 and 1 were resumed;
valid leash, chattiness and earlier memory rows were not repeated. The
reconciled screen contains 4,748 successful calls, no fallbacks and $53.3074
of list-price cost. Chattiness showed its intended off-turn response curve and
began to saturate above 0.5. Memory depth showed no replicable behavioural
gain. Plum leash 0.60 was the sole shortlist from the eight-game screens.

The separate 24-pair Plum confirmation retained leash 0.35. The 0.60
candidate won 25.0% against 37.5% at the preset, a paired change of -12.5
points (95% bootstrap interval -25.0 to 0.0), and lengthened games by 6.97%.
It therefore failed the five-point win guardrail. Confirmation cost $8.6005;
valid screening plus confirmation cost $61.9079, excluding balance probes and
the separately approved $0.0348 fixture refresh. No paid dial changed.

### Wikiclude and release gate

The public calibration record now uses Phase 14 throughout. *Dial sweeps* and
*Measurement record* contain the current headless and paid results; related
dial, method and character pages use the same facts. Detailed superseded
calibration tables were removed from public articles and unused fact keys,
leaving one short archive note while retaining the evidence in this plan, the
strategy glossary and git. W7's corpus, link, fact, citation and representative
390/1440-pixel review completed the final local documentation gate, as
recorded below.

### Release acceptance — complete

The complete offline suite reported 651 passed and 34 skipped. W7 reported 28
offline wiki checks plus the explicit live-network check, for 29 passed, and
fresh representative screenshots passed at 390 and 1440 pixels in all three
looks. `git diff --check` found no whitespace errors.

Cloud Run revision `clude-00038-jws` was deployed on 2026-10-18 and serves 100%
of traffic. The guarded GCS promotion first verified the three frozen source
hashes and no active tables, then wrote the accepted method documents with a
local method-only backup. Their released hashes are Green
`06becddda9d1e03ba5f0cc01da8b64c0b2e305f549a5ae8eca8836a3a8e3a9ee`,
Mustard `d4fe5f0a93646623b129be23a557895b2ac6fdc9761025cc0114b7d1c66fbf17`
and White `4bdcf253913e1bd87a797a6ccce5ff986619d2fd7b74e20fbc3ae6bb268b7578`.

The live acceptance table completed in 133 turns with Mustard winning, then
opened its recorded replay. It exposed a stale assumption in the maintainer
checker: external games now have a final-comment window, so a finished result
does not immediately carry a replay URL. The checker now explicitly declines
the two throwaway seats' comments (or closes an expired window) before testing
the replay. The acceptance game briefly taught Mustard and White about the
throwaway accounts; after the accounts were removed, a second guarded write
restored the exact accepted staged documents. A final dry run verified all
three released hashes and no open tables. Run 3 weights, code and Wikiclude are
in the Cloud Run image; only the three method-memory JSON documents required a
GCS update.

The trainer cannot export committed weights; checkpoint and method promotion
remain separate hash-guarded, backed-up operations, and method mutation still
requires `--apply`.
