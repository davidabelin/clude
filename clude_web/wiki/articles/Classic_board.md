---
title: Classic board
short: The grid, rooms, doors and passages used for movement
categories: The game
redirects: The board, Board, Ring board, The ring board, Secret passages, Secret passage
dyk: ...that the [[Classic board]] drawing and its legal moves come from the same map?
---
The **Classic board** is the grid on which [[clude]] has played since 15 September 2026. It has {{code:board.columns}} columns and {{code:board.rows}} rows, nine rooms, {{code:board.doors}} doors and two pairs of [[secret passages]]. Corridors connect the rooms around an impassable central cellar. Movement uses one die, with the full roll required unless the token enters a room.[^source]

The layout matters because [[suggestion|suggestions]] can be made only in the token's current room. Doors, blocked corridors and passages affect how soon a player can ask a useful question. They do not restrict the room named in an [[accusation]]. An earlier ring-shaped board is retained for reading historical records, not for new games.

## Layout

{{figure:classic-board|wide|The actual engine map: nine rooms, their doors and the six starting positions. Names identify the rooms; the centre is not a playable room.}}

The drawing is generated from the same map and door table that determine legal moves. It shows all six start squares even at a table with fewer occupied tokens. Ordinary corridor squares hold at most one token; any number can share a room. The cellar has no solution card, no entrance and no movement role.[^drawing]

The [[rooms]] run clockwise from Kitchen at the upper left through Ballroom, Conservatory, Billiard, Library, Study, Hall, Lounge and Dining. Ballroom has four doors, Hall three, Dining, Billiard and Library two each, and the four corner rooms one each. More doors provide more possible exits, but only an unoccupied square outside a door can be used.

## Doors and routes

{{figure:conservatory-door|A detail of the Conservatory doorway. The token enters from the square below its door, not through the wall to the left.}}

Door cells are part of a room. Crossing from the corridor square a door faces enters the room and ends the move. A neighbouring corridor square on another side of the same cell is not automatically an entrance: the wall may block it. The explicit door table resolves this ambiguity.[^doors]

For example, the Conservatory's door is at row 4, column 18, using zero-based coordinates from the upper left. It opens towards row 5, column 18. Row 4, column 17 also touches the door cell but lies beside its wall, so a token cannot enter from there.

Corridor routes use orthogonal steps and cannot revisit a square. A roll of four must end four steps away along a legal route unless a room is entered earlier. Distance alone is insufficient: another token may block the route, and a room just left cannot be re-entered during that move.[^movement]

## Secret passages

| Pair | From one corner | To the opposite corner |
|---|---|---|
| Kitchen–Study | Kitchen, upper left | Study, lower right |
| Conservatory–Lounge | Conservatory, upper right | Lounge, lower left |

Each passage works both ways. Taking it is an alternative movement choice, not an extra step added to a corridor route. It puts the token in the destination room and permits a suggestion there that turn. The engine records a die roll at every active turn, including passage turns, but the roll does not limit passage travel.[^movement]

Passages make corner rooms close in movement terms even though they are far apart in the drawing. Repeated passage trips can nevertheless waste questions when opponents keep disproving them with already located room cards. The [[landing rule]] changes the characters' movement scores to reduce this behaviour; it does not close a passage or change its legality.

## Staying, summoning and blocking

A token normally must leave a room on its next turn. It may stay if another player's suggestion moved it there since its previous turn. This one-turn permission allows a question without moving. Merely mentioning a token already in the room does not count as moving it.[^movement]

A token that has no legal destination stays put. Occupied corridor squares block both travel and landing; eliminated players' tokens remain in place. Rooms permit shared occupancy, so a player cannot block a room by standing inside it. Suggestions can move occupied suspect tokens between rooms independently of the die, but do not move weapons or create tokens for empty seats.

## Map and implementation

`clude_core.board` represents a corridor position as `Square(row, col)` and a room as its name. `BOARD_MAP` defines the cell types, `DOORS` defines their openings, and `SECRET_PASSAGES` defines the corner links. `reachable` finds legal destinations with token obstructions. `room_distances` supplies a separate distance estimate for decision scoring, including passages but ignoring other tokens.[^source]

The original map was measured from the project's reference image. Some edge cells were accepted as unplayable as drawn; the result is a chosen implementation of that image rather than a claim that every physical board has identical geometry.

## History

The earlier **ring board** put the nine rooms in a cycle with four corridor cells between neighbouring rooms. It retained the corner passages but allowed movement up to the roll and staying in a room on every turn. These differences made repeated questions easier and travel generally shorter.[^history]

The Classic board replaced it on 15 September 2026. The [[belief benchmark]] and [[arena]] were rerun, and some presets and search budgets were changed. Ring-board measurements remain historical evidence for the earlier implementation. Their game lengths and win rates cannot be carried over as predictions for the current grid. Old corridor positions survive as `HallwayCell` so stored games can still be loaded and replayed.


## See also

[[Rules of play]] · [[Rooms]] · [[Curiosity]] · [[Landing rule]] · [[Determinism and seeds]]

## References

{{references}}

[^source]: {{cite:docs/board.md|Source and measurement}}
[^drawing]: {{cite:clude_web/board_svg.py|`board_svg`}}
[^doors]: {{cite:docs/board.md|Doors}}
[^movement]: {{cite:docs/board.md|Movement rules}}
[^history]: {{cite:docs/board.md|History: the ring board (Phase 1 to 2026-09-15)}}

{{navbox:clude}}
