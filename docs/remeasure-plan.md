# Re-measurement Plan: the glossary on the Classic board (proposed 2026-09-15)

Status: **Stages 0 and 1 done on 2026-09-15**, presets retuned and the
confirmation arena run (results under "Re-measurement on the Classic
board" in `docs/strategy-glossary.md`; the Stage 1e decisions are
David's and are recorded under "Tuned presets on the grid"). **Stage 2
is half run:** the free headless halves of the 2a and 2b pairs are in
the store as `grid-twin-base-24` (24 games, 4 seats, the default six
roster, mean 41.9 turns) and `grid-plum-base-24` (24 games, the 3-seat
`Plum,Mustard,Green` table, mean 31.9 turns). The two paid halves have
not run and are waiting on David. Neither headless run is written up
yet: each is the pair half of a measurement that is not complete. Each paid stage needs its own yes
from David, with the cost quoted as a range at the time (estimates have
come in under twice). Every run goes through `--store data/llm` and
`--json <scratchpad path>`.

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
`data/llm/board_report.py`.

### Stage 2, LLM-piloted (paid; a yes per step)

| Step | Was | Quote now | Run only if |
|---|---|---|---|
| 2a Twin arena: all six on the model, 24 games, 4 seats, against the headless twin | $6.98 | $12-20 (grid games run about twice the ring's turns, so the model is asked about twice as often per game) | always: it is the check that the new menu text (corridor squares) draws no fallbacks and that an LLM table still changes outcomes the way it did. Headless half done: `grid-twin-base-24` |
| 2b Plum alone on the model at the preset leash, 24 games on `Plum,Mustard,Green` seed 7007, with the parking report | $6-8 (one ladder leg) | $9-15 (same reason) | always: it is the question the board change bears on most. If the Classic stay rule has ended the parking, the leash ladders and the logbook pair below are not needed. Headless half done: `grid-plum-base-24`, where Plum wins 37.5% against the ring's 62.5% on the same table |
| 2c Per-character leash ladders, Mustard (4 values) and Plum (3 values) | $8.94 and $18.13 | $10-20 and $18-36 | 2b still shows stalls, or 2a shows the leash mattering |
| 2d Plum's logbook on against off at leash 0.5, 24 paired games | $10.19 | $10-20 | 2b still shows stalls; it re-asks whether his own notes fix them on the grid |
| 2e Pooled leash sweep | $14.99 | skip | never: it could not see individual characters and the ladders superseded it |

Minimum path (0, 1, 2a, 2b): about $14-27. Full path: about $50-100.

### Stage 3, memory (free, one decision)

Mustard's and White's method memory in `data/llm/logbooks` was rebuilt
from 193 ring games. Mustard's rows come from each seat's view of the
suggestions, so they are not wrong on the grid, but they are from a
game whose pace differs. Decision for David: reset the method memory
and rebuild from grid-era records once Stage 2 has produced some
(`logbook reset`, then `logbook rebuild`), or keep mixing eras. My
recommendation is to reset once 2a and 2b are in the store, so the
memory measured in future is grid memory.

## 3. What gets written

Each step appends a dated section to `docs/strategy-glossary.md` in
the shape of the one it supersedes, with the ring-era section kept
above it and marked. The presets, if re-tuned, change in
`clude_agents/personality.py` with the goldens re-captured on purpose.
`CLAUDE.md`'s status paragraph records the spend and the dates.

## 4. Out of scope

Any change to a method's algorithm, to `movement_scores`, or to the
menu shape; those wait for what Stage 2b shows. Phase 8 and the UX pass
are not gated on any of this except the board drawing, which is
generated from the map and needs no measurement.
