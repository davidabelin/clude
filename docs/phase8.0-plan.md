# Phase 8.0 Plan: re-measuring the glossary on the Classic board

Proposed 2026-09-15 as the "Re-measurement Plan" (`docs/remeasure-plan.md`);
renamed Phase 8.0 on 2026-09-16 (David). Its stages are numbered
8.0.N: Stage 0 is 8.0.0, Stage 1 is 8.0.1 (steps 8.0.1a-g), and so on.
The glossary's section titles keep the "Stage 1a" labels they were
written with; they mean the same steps.

Status (2026-09-16):

- **8.0.0 and 8.0.1 done** (2026-09-15, closed 2026-09-16). Presets
  retuned and the confirmation arena run: results under "Re-measurement
  on the Classic board" in `docs/strategy-glossary.md`, the 8.0.1e
  decisions under "Tuned presets on the grid". The board report (1g)
  was re-run over the tuned arena and the two Stage 2 baselines on
  2026-09-16, and the stall report checked against grid-era menus.
- **8.0.2a and 8.0.2b done, $14.24 together** (David's yes,
  2026-09-16, quoted $21-35; 2a $9.36, 2b $4.88; no fallbacks in either).
  2a reproduces both ring twin findings in direction: an LLM table beats
  Plum (37.5% to 6.2%) and Mustard's wrong accusations fall (31.2% to
  6.2%). 2b found the parking alive in a new form, a passage loop the
  leash hides from the model, which the trigger below could not see; the
  trigger is withdrawn. What follows (2c, 2d, a `movement_scores` change,
  or nothing) is David's decision (glossary, "Twin comparison on the
  grid" and "Plum with Claude on the grid").
  The free headless halves are in the store as
  `grid-twin-base-24` (24 games, 4 seats, the default six roster, mean
  41.9 turns) and `grid-plum-base-24` (24 games, the 3-seat
  `Plum,Mustard,Green` table, mean 31.9 turns), both at the retuned
  presets; the paid halves run as `grid-twin-llm-24` and
  `grid-plum-llm-24`. 2c and 2d each need their own yes.
- **8.0.3 done** (David's decision, 2026-09-16): all four logbooks
  reset after a copy to `data/llm/logbooks-ring`, and Mustard's and
  White's method memory rebuilt from grid-era records only (Stage 3,
  below).
- **8.0.4 done** (David's decision, 2026-09-18: the scoring change,
  headless, first): the landing rule in `features.room_features`. A
  placed room is a destination only when nobody else can refute with it
  (the agent's own, or the envelope's); one placed in another seat's
  hand scores as a place on the way. Measured as three paired arenas
  against the 8.0 baselines: games shorter on every table, exact repeats
  down by two thirds or more for every character, win rates within
  noise; goldens re-captured, fixtures re-recorded ($0.22). Numbers in
  the glossary under "The landing rule"; the record in
  `docs/phase8-plan.md` section 12. The parking question is closed; 2c
  and 2d were not run. Phase 8.0 is complete.

Each paid stage needs its own yes from David, with the cost quoted as a
range at the time (estimates have come in under twice). Every run goes
through `--store data/llm` and `--json <scratchpad path>`.

## 1. Why

Every number in `docs/strategy-glossary.md` was measured on the ring
board, and everything up to the Phase 6 ladders with characters rotating
through seats as well. On 2026-09-15 the engine moved to the Classic
grid and rules (`docs/board-plan.md`): corridors are long and open, the
Billiard Room is a short walk from the Hall instead of fifteen steps,
tokens must use their whole roll, and a token may stay in a room only
when a suggestion dragged it there. Games are shorter or longer in ways
the ring never showed, rooms are visited in different proportions, and
the free "stay" that Plum's parking lived on is gone. So the glossary
describes a game that no longer exists, and the presets tuned on it may
no longer be the right ones.

Two things did not move and need no re-measuring: the six belief
methods themselves (their inputs are suggestions and reveals, not
squares) and the deduction floor.

## 2. Order

Cheapest and most upstream first, because the paid stages depend on the
presets, and the presets depend on the free sweeps.

### Stage 0, bookkeeping (about $0.35)

- Re-record the two LLM fixtures with the command in
  `tests/test_llm.py` and update `RECORDED_GAMES`. **Done 2026-09-15,
  $0.13**; the suite is green.
- Date every existing glossary section as ring-era. Sections are kept,
  not deleted: they are the record of how the presets were reached.

### Stage 1, headless (free, about two hours of laptop time)

| Step | Command (as in the glossary) | Time | What it answers |
|---|---|---|---|
| 1a | `benchmark --games 60 --show-green` (seed 4004) | ~10 min | Belief quality on FloorBot snapshots from grid games. Expect small movement: the snapshots' suggestion mix changes with the rooms visited. |
| 1b | Mustard's default tree | none | Trained at build time from the 25 FloorBot self-play games (seed 2026), so it is already a grid tree. Check its held-out numbers in 1a. |
| 1c | `sweep --dial <dial> --values ... --games 48 --seed 7100 --roster Scarlett,floor,Mustard,floor,White,floor,Green,floor,Peacock,floor,Plum,floor`, five dials | ~1-2 h | Whether each dial still moves its metric and in which direction. `curiosity` and `accuse_threshold` are the ones most likely to move: distances changed, and games end at a different pace. |
| 1d | Scarlett's three 24-game arenas with only her threshold moved (seed 7007) | ~5 min | Her threshold was set by her own runs, not the pooled sweep. |
| 1e | Decision point: re-tune presets if 1c or 1d says so. David decides; the tuned table in the glossary is replaced, the old one kept. **Done 2026-09-15**: Scarlett's threshold 0.15 to 0.3, Plum's curiosity 0.8 to 0.5, Plum's sample budget 2,000 to 10,000; Green's threshold and Scarlett's and Peacock's curiosity stand. Every character golden re-captured and both fixtures re-recorded ($0.13). | ~1 h | |
| 1f | `arena --games 24 --seed 7007 --store data/llm --run-id arena-grid-24` at the (re)tuned presets | ~2 min | The headless table: win%, wrong%, first accusation, never%, leaks, re-shows, mean turns. Pairs with nothing earlier. **Run twice**: at the ring presets (`arena-grid-24`) and again at the retuned ones (`arena-grid-tuned-24`). |
| 1g | A board report over 1f's records (a script beside `parking_report.py`): turns per game, suggestions per game, visits per room, stays used after a summons, passages taken, blocked turns | ~5 min | The board-specific facts the ring could not show, and the baseline the paid stages compare against. |

Stage 1 can run while the UX pass continues; it costs nothing but the
laptop. **Ran 2026-09-15**: the benchmark 799 s, the sweeps 676-936 s
each in parallel, the four arenas about 250 s each; all of it in
under an hour of wall time on Orbit, records under `data/llm` as
`sweep-grid-*`, `arena-grid-*`. The board report is
`data/llm/board_report.py`; on 2026-09-16 it was re-run over
`arena-grid-tuned-24`, `grid-twin-base-24` and `grid-plum-base-24` so
the paid stages have a baseline at the presets they run at (glossary,
"How the game plays on the board").

### Stage 2, LLM-piloted (paid; a yes per step)

| Step | Was | Quote now | Run only if |
|---|---|---|---|
| 2a Twin arena: all six with Claude, 24 games, 4 seats, against the headless twin | $6.98 | $12-20 (grid games run about twice the ring's turns, so the model is asked about twice as often per game) | always: it is the check that the new menu text (corridor squares) draws no fallbacks and that an LLM table still changes outcomes the way it did. Headless half done: `grid-twin-base-24` |
| 2b Plum alone with Claude at the preset leash, 24 games on `Plum,Mustard,Green` seed 7007, with the parking report | $6-8 (one ladder leg) | $9-15 (same reason) | always: it is the question the board change bears on most. If the Classic stay rule has ended the parking, the leash ladders and the logbook pair below are not needed. Headless half done: `grid-plum-base-24`, where Plum wins 37.5% against the ring's 62.5% on the same table |
| 2c Per-character leash ladders, Mustard (4 values) and Plum (3 values) | $8.94 and $18.13 | $10-20 and $18-36 | 2b still shows stalls, or 2a shows the leash mattering |
| 2d Plum's logbook on against off at leash 0.5, 24 paired games | $10.19 | $10-20 | 2b still shows stalls; it re-asks whether his own notes fix them on the grid |
| 2e Pooled leash sweep | $14.99 | skip | never: it could not see individual characters and the ladders superseded it |

Minimum path (0, 1, 2a, 2b): about $14-27. Full path: about $50-100.
The 2b quote assumed grid games run twice the ring's turns; the
headless half says 1.33x on Plum's table (31.9 against 24.0), so 2b
should land nearer the low end of its range.

**What counts as a stall on the grid, and the trigger for 2c and 2d**
(written 2026-09-16, before 2a and 2b finished). `parking_report.py`
counts move calls where the model chose a room whose envelope
probability is zero while an allowed option led toward a live one. On
the ring nearly all of those were "stay"; on the grid "stay" exists
only after a summons, so the same count now catches *entering* a
cleared room over heading for a live one. The recorded grid fixtures
already show the menu that makes it likely: "enter the Lounge"
(P 0.00) scored 0.30, above a step toward the Dining (P 0.20) at 0.25,
because `movement_scores` still pays for any room a suggestion can be
made in this turn. The trigger, fixed before the results:

- **2c Plum and 2d** are proposed if 2b shows any of: such calls in 10%
  or more of Plum's move calls; three or more games with five or more
  such calls; Plum's win% with Claude more than 12 points (about one
  binomial sigma at 24 games) below `grid-plum-base-24`.
- **2c Mustard** is proposed only if Mustard's line in 2a moves against
  `grid-twin-base-24` by more than one sigma on win% or wrong%.
- Either way the numbers are written up; below the trigger, the
  parking question is closed for the grid and the open question on
  `movement_scores` in `CLAUDE.md` is answered "not needed".

**Withdrawn the same day, after 2b.** The count above reuses
`parking_report.py`, which only sees moves the model was *asked* about
with an *allowed* live option. On the grid at leash 0.25 the escape
toward a live room usually falls outside the leash, so the wrapper
plays the parked move without asking. The trigger read 1 parked move in
145, while Plum made 148 trips into a cleared room that ended in a
suggestion he had already made, 108 of them never put to the model,
riding the Study-Kitchen and Conservatory-Lounge passages and repeating
half his suggestions (glossary, "Plum with Claude on the
grid"). By its letter no condition was met; the conclusion it promised
("closed for the grid") does not follow, and I have not drawn it.
`data/llm/loop_report.py` counts parked and wasted moves, asked and not asked.
Which of 2c, 2d, a `movement_scores` change or nothing comes next is
David's decision.

### Stage 3, memory (free, one decision)

Mustard's and White's method memory in `data/llm/logbooks` was rebuilt
from 193 ring games. Mustard's rows come from each seat's view of the
suggestions, so they are not wrong on the grid, but they are from a
game whose pace differs. Decision for David: reset the method memory
and rebuild from grid-era records once Stage 2 has produced some
(`logbook reset`, then `logbook rebuild`), or keep mixing eras. My
recommendation is to reset once 2a and 2b are in the store, so the
memory measured in future is grid memory.

**Decided 2026-09-16 (David): reset all four**, not only the two
method memories: Plum's entries and head (written on the ring during
7d, whose standing instructions are about leaving rooms a free "stay"
kept him in) and Green's posteriors (which no record can rebuild; he
starts again from the prior). Two things were found on the way:

- `logbook rebuild` read every record in the store, and `data/llm`
  holds the ring games beside the grid ones, so a reset followed by a
  rebuild would have re-absorbed the ring. `clude_training.memory.rebuild`
  now takes `min_version` (default 3, the first grid record version;
  `logbook rebuild --min-version`) and reports what it skipped.
- `logbook reset` deletes, so `data/llm/logbooks` is copied to
  `data/llm/logbooks-ring` first.

The order: 2a and 2b land, copy, `logbook reset` for each of the four,
`logbook rebuild` for Mustard and White.

**Done 2026-09-16**, after both paid runs were stored. The copy in
`data/llm/logbooks-ring` is byte-identical to what was reset (30 files:
Plum's 24 entries and head; Mustard's 10,929 rows from 199
games; White's chains from 193; Green's posteriors after 6 games). Both
rebuilds read 1,322 grid-era games and skipped 249 ring-era records.
Mustard now holds 116,311 rows (17 MB against 1.6 MB), White's chains
cover every seat label including `floor`, and Plum and Green start
empty.

One consequence to know before memory is next switched on: Mustard
retrains his tree on those rows when his logbook loads, which takes a
3-seat `play` from 1 s to 30 s. 70% of the rows (81,252) come from the dial
sweeps (floor-heavy tables at extreme dial values), not from games as
the presets play them. Nothing measured today runs with memory on, and
no golden or fixture reads a logbook; if the load time or the mix
matters later (a web game with memory on, 8.2 onward), the options are
rebuilding from a store holding only the arenas (`logbook rebuild
--from`), capping the rows, or caching the trained tree.

## 3. What gets written

Each step appends a dated section to `docs/strategy-glossary.md` in
the shape of the one it supersedes, with the ring-era section kept
above it and marked. The presets, if re-tuned, change in
`clude_agents/personality.py` with the goldens re-captured on purpose.
`CLAUDE.md`'s status paragraph records the spend and the dates.

## 4. Out of scope

Any change to a method's algorithm, to `movement_scores`, or to the
menu shape; those wait for what Stage 2b shows. Phases 8.1-8.3 are not
gated on any of this; the board drawing is generated from the map and
needs no measurement.
