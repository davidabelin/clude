# Board

The engine plays on the Classic Clue board: a grid of 24 columns and
25 rows of corridor squares around nine rooms and a cellar, with the
real doors, the two secret passages and the six start squares. David
decided this on 2026-09-15 (`docs/board-plan.md`); until then the
engine played a ring simplification, described at the end.

## Source and measurement

The reference is `docs/ux/sample_board_A.png`, a rendering of the
Classic board. It was measured cell by cell: the checkerboard pitch is
19.3 px, which gives 24 by 25 cells inside the border; each cell was
classified as corridor, room, cellar, or off the board; the doors were
found as gaps in the black room walls between a room cell and a
corridor square; the start squares and the passage arrows are the
coloured cells. The result is `docs/ux/board_map.txt`, embedded in
`clude_core/board.py` as `BOARD_MAP`; `tests/test_board.py` keeps the
two identical (trailing spaces aside).

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

`K` Kitchen, `B` Ballroom, `C` Conservatory, `D` Dining, `I` Billiard,
`L` Library, `O` Lounge, `H` Hall, `S` Study; `X` the cellar
(impassable, where the logo goes); `.` a corridor square; a space is
off the board. A lower-case room letter is a door cell. Start squares:
`w` White (0,9), `g` Green (0,14), `p` Peacock (6,23), `u` Plum
(19,23), `r` Scarlett (24,7), `m` Mustard (17,0), each walked like any
corridor square. Rows count from the top, columns from the left.

Counts: 182 corridor squares plus the 6 start squares, 345 room cells,
35 cellar cells, 17 doors.

### Doors

A door cell is part of its room; a token enters the room from the
corridor square the door faces. Three door cells touch two corridor
squares and open onto only one of them, which is why `board.DOORS`
states every door explicitly rather than reading it from the map.

| Room | Door cell | Entered from |
|---|---|---|
| Kitchen | (6,4) | (7,4) |
| Ballroom | (5,8) | (5,7) |
| Ballroom | (5,15) | (5,16) |
| Ballroom | (7,9) | (8,9) |
| Ballroom | (7,14) | (8,14) |
| Conservatory | (4,18) | (5,18), not (4,17) |
| Dining | (12,7) | (12,8) |
| Dining | (15,6) | (16,6) |
| Billiard | (9,18) | (9,17) |
| Billiard | (12,22) | (13,22) |
| Library | (14,20) | (13,20) |
| Library | (16,17) | (16,16) |
| Lounge | (19,6) | (18,6), not (19,7) |
| Hall | (18,11) | (17,11) |
| Hall | (18,12) | (17,12) |
| Hall | (20,14) | (20,15) |
| Study | (21,17) | (20,17), not (21,16) |

Secret passages: Kitchen and Study, Conservatory and Lounge.

### Cells taken from the image on trust

The image leaves a few edge cells white and unplayable: (8,0), (16,0),
(18,0), (7,23), (13,23), (20,23), (24,8) and (24,15); and it has a
single corridor square at (24,16) between the Hall and the Study. David
chose to take the image as it stands (2026-09-15); a physical board
would settle them, and `BOARD_MAP` is the one place to change.

## Movement rules

Decided by David on 2026-09-15 (`docs/board-plan.md`, section 6),
implemented in `board.reachable` and `engine.legal_moves`:

- One die, rolled by the engine.
- The whole roll must be used, unless the token enters a room, which
  ends the move. A room reached in fewer steps is a destination; a
  corridor square short of the roll is not.
- Orthogonal steps only, through corridor squares. No square is
  visited twice in one move. A corridor square holding another token
  can be neither passed through nor landed on. Any number of tokens may
  share a room.
- A token in a room leaves through any of its doors and may not
  re-enter that room in the same move. With a secret passage, it may
  take it instead of rolling.
- "Stay" is offered only to a token that another player's suggestion
  moved into the room since its last turn (`GameState.summoned`, set by
  `engine.resolve_suggestion` and cleared when that player's next turn
  begins); it may then suggest without moving. Otherwise a token in a
  room must move or take its passage.
- A token with no legal step (boxed in, or in a room whose door
  squares are all occupied and with no passage) stays put for the turn.
- A suggestion moves the named suspect's token into the room, as in the
  rules; that is the only way a token moves outside its own turn.

## What the module exposes

`Square(row, col)` is a corridor position; a room is its name; `Node`
is either. `CORRIDOR`, `ROOM_CELLS`, `DOOR_CELLS`, `CELLAR` and
`START_SQUARES` are parsed from the map; `DOORS` is the table above,
with `ENTRANCES` (square to the room it lets into) and `EXITS` (room to
the squares outside its doors) derived from it. `neighbors`,
`reachable`, `room_distances` (breadth-first over squares, rooms and
passages, ignoring tokens: the proximity measure the characters'
movement scoring uses) and `node_sort_key` are the API the engine and
the agents call. `HallwayCell` is the ring-era position, kept only so
records written before 2026-09-15 still load and replay.

The board drawing for the UI will be generated from the same map, so
the picture and the rules cannot drift apart.

## History: the ring board (Phase 1 to 2026-09-15)

Phase 1 modelled the board as the nine rooms in a cycle, in the order
`Kitchen, Ballroom, Conservatory, Billiard, Library, Study, Hall,
Lounge, Dining`, taken from a published redrawing (*"Redrawing of the
classic Cluedo board"* by CMG Lee, CC BY-SA 4.0, Wikimedia Commons,
`File:Cluedo_board.svg`), with one corridor of four single-occupancy
cells between each neighbouring pair, exactly two doors per room, the
two secret passages as chords, and each start on the corridor cell
beside a room. Movement was "up to" the roll and a token could stay in
its room every turn. Phase 5b fixed two rules bugs on it (a token could
not leave its starting room by a door; a boxed-in token had no move).
Every measurement in `docs/strategy-glossary.md` dated before
2026-09-15 was made on that ring; `docs/remeasure-plan.md` schedules
the re-run on the Classic board.
