# Board Plan: the real grid replaces the ring (proposed 2026-09-15)

Status: **built on 2026-09-15 (B1-B3, section 8) on David's decisions in
section 6; the two LLM fixtures wait for a paid re-recording.** Same shape as the phase plans: context, what the code
dictates, design, sub-phases, files, decisions, out of scope, and an
"as implemented" section once the work lands.

## 1. Context

Since Phase 1 the engine has played on a simplification: nine rooms in
a ring, one corridor of four cells between each neighbouring pair, two
doors per room, the two secret passages as chords (`docs/board.md`,
"Simplification"). Every golden, fixture and measurement since sits on
that ring. On 2026-09-15 David decided that the engine and the players
must play on the real board (`docs/ux/sample_board_A.png`, "Board A"),
and that the game will display that board with its grid, decorated
more ornately than the graph diagram in `sample_board_B.png`, with a
logo rather than the big "?" in the middle.

This plan replaces the ring with Board A's grid and brings the movement
rules up to the Classic game's, before the UX pass draws the board and
before Phase 8 builds on it.

## 2. What the code dictates

Positions are a `Node`: a room name (`str`) or a `HallwayCell`
(`room_a`, `room_b`, `k`). Thirteen modules mention the topology; most
only through four functions that keep their names and meaning:

| Function | Used by | Survives |
|---|---|---|
| `board.room_of(node)` | engine, features, FloorBot, menu, CLI | yes, unchanged |
| `board.reachable(start, roll, occupied)` | `engine.legal_moves` | yes, new rules inside |
| `board.room_distances(node)` | features (movement scores), FloorBot | yes, BFS over squares |
| `board.start_position(suspect)` | `engine.setup` | yes, a square |
| `board.node_sort_key(node)` | `engine.legal_moves` | yes, `(row, col)` |
| `HallwayCell` | records (JSON), menu text, CLI text, tests | replaced by `Square` |

`engine.legal_moves` builds the option list (stay, secret passage, every
reachable node) and `apply_move` sets the position; nothing else in the
engine knows the shape of the board. `MoveEvent.destination` is a
`Node`, serialised by `records.node_to_json` (version 2 writes
`{room_a, room_b, k}` for a cell). The prompt menu describes a cell as
"the hallway between the X and the Y"; the CLI prints it as
`X~Y[k]`. The characters never see coordinates: `room_features` reduces
every non-room destination to distances-to-rooms, so their scoring is
untouched by the change of board, though its numbers will move.

Goldens (`tests/test_character.py`) and both LLM fixtures
(`tests/fixtures/llm_seed*.json`) encode ring games and will all
change. Stored records in `data/llm` hold ring positions; they remain
readable (below) and Mustard's and White's memory, which is built from
suggestions, not moves, is unaffected.

## 3. The board, measured

Board A is the Classic 24-column, 25-row grid. The cells were read off
the image (19.3 px per cell), the doors found as gaps in the room walls
between a room cell and a corridor cell, the start squares and passage
arrows as the coloured cells. The result is `docs/ux/board_map.txt`,
which the plan proposes as the single source of truth, embedded in
`clude_core/board.py`:

```
     012345678901234567890123
  0           w    g
  1  KKKKKK ...BBBB... CCCCCC
  2  KKKKKK..BBBBBBBB..CCCCCC
  3  KKKKKK..BBBBBBBB..CCCCCC
  4  KKKKKK..BBBBBBBB..cCCCCC
  5  KKKKKK..bBBBBBBb...CCCCC
  6  KKKKkK..BBBBBBBB.......p
  7  ........BbBBBBbB.......
  8   .................IIIIII
  9  DDDDD.............iIIIII
 10  DDDDDDDD..XXXXX...IIIIII
 11  DDDDDDDD..XXXXX...IIIIII
 12  DDDDDDDd..XXXXX...IIIIiI
 13  DDDDDDDD..XXXXX........
 14  DDDDDDDD..XXXXX...LLlLLL
 15  DDDDDDdD..XXXXX..LLLLLLL
 16   .........XXXXX..lLLLLLL
 17  m................LLLLLLL
 18   ........HHhhHH...LLLLLL
 19  OOOOOOo..HHHHHH........u
 20  OOOOOOO..HHHHHh........
 21  OOOOOOO..HHHHHH..sSSSSSS
 22  OOOOOOO..HHHHHH..SSSSSSS
 23  OOOOOOO..HHHHHH..SSSSSSS
 24  OOOOOOOr HHHHHH .SSSSSSS
```

Legend: `K` Kitchen, `B` Ballroom, `C` Conservatory, `D` Dining Room,
`I` Billiard Room, `L` Library, `O` Lounge, `H` Hall, `S` Study, `X` the
cellar (impassable; the logo goes here), `.` a corridor square, a
space is off the board. A lower-case room letter is a door cell: it is
part of the room and is entered from the corridor square beside it.
The six start squares are `w` White (0,9), `g` Green (0,14), `p`
Peacock (6,23), `u` Plum (19,23), `r` Scarlett (24,7), `m` Mustard
(17,0). Secret passages: Kitchen and Study, Conservatory and Lounge.

Counts: 182 corridor squares, 345 room cells, 17 doors (Kitchen 1,
Ballroom 4, Conservatory 1, Dining 2, Billiard 2, Library 2, Lounge 1,
Hall 3, Study 1). Every door and every start square opens onto a
corridor square.

**To verify against a physical board, if David has one:** the white
edge cells that the image leaves unplayable, at (8,0), (16,0), (18,0),
(7,23), (13,23), (20,23), (24,8) and (24,15), and the single corridor
square at (24,16) between the Hall and the Study. Nothing else in the
map is in doubt.

## 4. Design

### The graph

- `Square(row, col)`, frozen, replaces `HallwayCell`. Rooms stay
  strings. `Node = Union[str, Square]`.
- `BOARD_MAP` is the text above, parsed at import into `CORRIDOR`
  (squares), `ROOM_CELLS` (room to squares), `DOORS` (room to the list
  of (door cell, corridor square) pairs), `START_SQUARES`, `CELLAR`,
  `SECRET_PASSAGES`. `docs/ux/board_map.txt` stays the human copy, and
  a test asserts the two are identical.
- `neighbors(square)` is the four orthogonal corridor squares plus, for
  a square beside a door, the room. `neighbors(room)` is every
  corridor square beside one of its doors. Rooms have no interior
  geometry: a token in a room is "in the room", as today.
- `reachable(start, roll, occupied, room_left=None)` walks the
  corridor under the rules in section 6. `room_distances` is a
  breadth-first search over squares, rooms and passages, as today, so
  `room_features` and FloorBot need no change beyond the import.
- `start_position` returns the start square. `node_sort_key` sorts
  rooms first, then squares by `(row, col)`.

### The rules (defaults proposed; section 6 decides)

- One die.
- The full roll must be used unless the token enters a room, which
  ends the move. A room reached in fewer steps is a destination; a
  corridor square short of the roll is not.
- No diagonal steps, no passing through or landing on an occupied
  corridor square, no visiting a square twice in one move, any number
  of tokens in a room.
- A token may not leave a room and re-enter it in the same move.
- "Stay" is offered only when the token was moved into the room by
  another player's suggestion since its last turn; otherwise a token
  in a room must roll and leave, or take its passage. This is the
  Classic rule and it removes the free "stay" that Plum's parking
  lives on (`CLAUDE.md`, "The parking mechanism").
- A blocked token with no legal step stays put, as today.

### What else moves

- `engine.legal_moves` gains the "stay" condition, which needs one bit
  of state: `GameState.summoned[player]`, set by `resolve_suggestion`
  when it drags a token and cleared at the start of that player's turn.
- `records`: `RECORD_VERSION` 3 writes a square as `{row, col}`.
  `node_from_json` still reads `{room_a, room_b, k}` into a kept,
  read-only `HallwayCell` so every stored ring game replays
  (`clude_training.replay`) and `logbook rebuild` keeps working.
- `clude_llm.menu`: a square is described by what the character cares
  about, "a corridor square N steps from the Library door", never by
  coordinates. `rules.md` gains nothing: the menu already lists only
  legal options.
- `scripts/clude_cli.py`: `(r,c)` in place of `X~Y[k]`.
- `tests/test_board.py` rewritten around the map: counts, every door
  opens onto the corridor, starts, reachability cases (the Kitchen
  door with a 1, the Ballroom's four doors, blocking, no re-entry, the
  cellar impassable). Goldens re-captured on purpose; both LLM
  fixtures re-recorded (about $0.35 at the last two re-recordings).
- The board drawing for the UX pass is generated from the same map:
  an SVG with the grid, the rooms, the doors and the cellar, which the
  replay sketches then use instead of the ring.

## 5. Sub-phases

- **B1, the board.** `board.py` on the grid with the rules; the
  `Square` type; `test_board.py`. The engine still runs, on the old
  "up to" semantics, until B2.
- **B2, the engine and everything downstream.** `summoned`, the stay
  rule, records version 3 with the legacy reader, menu and CLI text,
  goldens, fixtures. Suite green. `play --verbose` on seed 7007 read
  end to end against the map.
- **B3, the record.** `docs/board.md` rewritten (source, the map, the
  rules, what was simplified before), `docs/architecture.md`,
  `docs/strategy-glossary.md` (a dated note that every measurement
  before B2 was on the ring, and that Plum's parking must be
  re-measured under the stay rule before any `movement_scores`
  change), `CLAUDE.md`. The board SVG for the canvas.

## 6. Decisions (David, 2026-09-15)

1. **One die.**
2. **Classic:** the full roll must be used unless the token enters a room.
3. **Classic:** "stay" only when a suggestion moved the token into the room since its last turn.
4. **Forbid** leaving and re-entering the same room in one move.
5. **The image stands** for the unplayable edge cells and the (24,16) square.
6. **Keep** old ring records readable through a legacy `HallwayCell` reader.
7. **Then a plan to re-measure everything in the glossary** on the new board (a plan, costed, before any run).

## 7. Out of scope

The board drawing's decoration and the logo (the UX pass); Phase 8;
any change to the characters' scoring or dials, including
`movement_scores`; any paid measurement. The change of board and
rules will move every number in the glossary; re-measuring is a
separate, costed decision.

## 8. As implemented (2026-09-15)

- **B1, the board.** `clude_core/board.py` rewritten around `BOARD_MAP`
  (parsed at import into `CORRIDOR`, `ROOM_CELLS`, `DOOR_CELLS`,
  `CELLAR`, `START_SQUARES`) and the explicit `DOORS` table, checked
  against the map at import. Two departures from the plan: the map
  cannot carry a door's facing, so `DOORS` is a table rather than
  parsed (three doors sit beside two corridor squares); and start
  squares needed letters no room uses, so Scarlett's is `r`, since `s`
  is the Study's door letter (the first parse read her start as a
  door). Editors strip trailing spaces, so the parser pads rows.
  `reachable` walks every simple path with a depth-first search: a room
  at any depth is a destination and ends the path, a square only at
  exactly the roll. `room_distances` is the same breadth-first search
  as before over the new graph. `HallwayCell` stays as a legacy type;
  `room_of` and `node_sort_key` accept it, everything else refuses it.
  `tests/test_board.py` rewritten: 17 tests, including the three door
  facings, the whole-roll rule, no revisits, blocking with a detour,
  no re-entry, and the docs copy of the map.
- **B2, the engine and downstream.** `GameState.summoned` (empty for
  states built without it, which reads as all False); `setup` fills
  it; `resolve_suggestion` sets it when it actually moves a token;
  `run_game` clears it right after `legal_moves` for the turn, so the
  right lasts one turn used or not; `legal_moves` offers "stay" only on
  it. Records: `RECORD_VERSION` 3, a square as `{row, col}`, the old
  `{room_a, room_b, k}` still read into a `HallwayCell`. The prompt
  menu says "the corridor square at row 7, column 4"; the CLI prints
  `(7,4)`. Every hand-built ring position in the tests became a square;
  the engine goldens and all four character goldens were re-captured
  on purpose (the random-bot games are much shorter now: everyone
  accuses wrongly sooner with fewer suggestions, so the observation
  probe test moved to seed 7). Seed 7007 on `Plum,Mustard,Green` was
  read end to end against the map: every move a legal walk, both
  passages used, Green's turn-11 jump the Hall summons from Plum's
  suggestion, Mustard's turn 25 a Classic stay after Green dragged him
  into the Lounge; Plum wins on turn 30.
- **B3, the record.** `docs/board.md` rewritten; `docs/architecture.md`,
  `docs/cli.md`, `docs/strategy-glossary.md` (dated note), `docs/phase-plan.md`
  and `CLAUDE.md` updated; `docs/phase8.0-plan.md` written (David's
  decision 7). The board SVG for the canvas is not yet generated.
- **Suite:** 256 passed and 2 skipped once the fixtures are re-recorded;
  until then `test_recorded_llm_games_replay_offline` fails twice. The
  suite runs about 95 s: character games are longer on the grid, and
  the 120-turn four-character golden game alone takes 17 s.
- **Not done:** the fixture re-recording (about $0.35, needs a yes), the
  board SVG, and every measurement (`docs/phase8.0-plan.md`).
