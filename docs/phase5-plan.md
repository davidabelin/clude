# Phase 5: personality, self-play and storage

Completed 2026-09-12. This is a condensed historical decision record. Use [architecture](architecture.md), [CLI](cli.md) and [the glossary](strategy-glossary.md) for current contracts and dated measurements. Plum here means the enumeration agent now archived as PlumOG; this phase ran on the ring board.

## 1. What the measurements say

Early benchmarks exposed hard zeros in Mustard/White, weak information in RandomBot games and an outcome reward dominated by the shared floor. Early timings were taken on a board where tokens could not leave rooms correctly; they were not reliable estimates for purposeful play.

## 3. Where this differs

Keep six distinct algorithms. Correct absence-of-evidence handling and data generation before tuning personalities; do not replace weak methods with a stronger common inference engine. Peacock's caution comes from her lower belief bound, not a second artificial personality flaw.

### 4.1 The self-play regime: a `FloorBot`

FloorBot became the standard training/opponent baseline. Uniform movement failed because suggestions dragged tokens into already-located rooms; purposeful movement toward useful rooms was required for continuing information gain.

### 4.2 Mustard: calibration, then distribution

Use m-estimated leaf values instead of hard zeros, richer card features and FloorBot training games. A leaf's absence of positive training rows is not proof of impossibility. Keep distribution mismatch visible rather than claiming this makes the tree calibrated.

### 4.3 White: the same zero, a different cause

Start every unresolved card at the floor's uniform prior and add Markov evidence. An unnamed card is unsuspicious, not impossible. The repeat/new model remains White's own method.

### 4.4 Green: a reward with signal in it

Rank arm log-loss on each revealed envelope rather than rewarding absolute probability dominated by the floor. Best arm gets 1, worst 0, with interpolation; tied losses get equal reward. Feedback cadence is per snapshot in the benchmark, per finished game in the arena.

## 6. Decisions needed

David approved observer injection, FloorBot, smoothing/prior fixes, rank reward, five initial dials and a per-spec confidence function. Storage started early with local/GCS backends using the existing project account. Keep a dial only when it has a measured effect, with room to prune after the first pass.

## 8. As implemented (2026-09-12)

- PlayerProtocol gained per-seat observations; Character combines belief with Profile for four decisions.
- FloorBot seeks useful rooms and suggests unlocated cards. Starting-room reachability and boxed-in movement bugs were fixed; goldens were deliberately regenerated.
- Satisfied OR constraints were dropped so Peacock would not treat them as open evidence.
- Mustard gained smoothing and distinct-namer/probe features; White gained an unresolved-card prior; Green gained rank feedback.
- Arena/sweeps measure full-game outcomes on paired deals/dice; records and run summaries persist through one RecordStore interface.
- Holder ordering was fixed for cross-process determinism: mixed int/`envelope` frozensets must never supply RNG-dependent iteration order.
- Secrecy moved re-show rate but not total cards leaked. It was retained provisionally; small sweeps report direction/std, not significance.

Measurements and tuned presets remain in the glossary. LLM calls, UI and logbooks were outside this phase and arrived later.
