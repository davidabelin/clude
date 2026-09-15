"""Board topology: the Classic 24 x 25 grid, its rooms, doors, secret
passages and start squares, and movement under the Classic rules.

The board is `BOARD_MAP`, a text picture measured from the reference
image (`docs/board.md` has the source and the measurement). Everything
else in this module is parsed from it at import, except `DOORS`, which
is stated explicitly because a door's *facing* is not in the map: three
door cells touch two corridor squares and open onto only one of them.

Nodes
-----
A position is a `Node`: a room name (`str`) or a `Square(row, col)` in
the corridor. Rooms have no interior geometry -- a token in a room is
"in the room". `HallwayCell` is the pre-2026-09-15 ring position, kept
only so that stored records from the ring era still load
(`clude_storage.records`); nothing places a token on one.

Rules (David, 2026-09-15; `docs/board-plan.md` section 6)
---------------------------------------------------------
One die. The full roll must be used unless the token enters a room,
which ends the move. No diagonal steps, no passing through or landing
on an occupied corridor square, no square visited twice in one move,
no leaving a room and re-entering it in the same move. Any number of
tokens may share a room. Secret passages are a separate move type
(`engine.legal_moves`), as is "stay", which the engine offers only to
a token that a suggestion moved into its room.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Union

from .domain import ROOMS, SUSPECTS

# One character per cell, 25 rows of 24. Upper-case letter: a room cell;
# lower-case: a door cell of that room; '.': corridor; 'X': the cellar
# (impassable); a space: off the board. Start squares: w White, g Green,
# p Peacock, u Plum, r Scarlett (red), m Mustard: letters no room uses. `docs/ux/board_map.txt` is
# the same picture for humans; `tests/test_board.py` keeps them equal
# (trailing spaces aside: editors strip them, so the parser pads rows).
BOARD_MAP = """\
         w    g
KKKKKK ...BBBB... CCCCCC
KKKKKK..BBBBBBBB..CCCCCC
KKKKKK..BBBBBBBB..CCCCCC
KKKKKK..BBBBBBBB..cCCCCC
KKKKKK..bBBBBBBb...CCCCC
KKKKkK..BBBBBBBB.......p
........BbBBBBbB.......
 .................IIIIII
DDDDD.............iIIIII
DDDDDDDD..XXXXX...IIIIII
DDDDDDDD..XXXXX...IIIIII
DDDDDDDd..XXXXX...IIIIiI
DDDDDDDD..XXXXX........
DDDDDDDD..XXXXX...LLlLLL
DDDDDDdD..XXXXX..LLLLLLL
 .........XXXXX..lLLLLLL
m................LLLLLLL
 ........HHhhHH...LLLLLL
OOOOOOo..HHHHHH........u
OOOOOOO..HHHHHh........
OOOOOOO..HHHHHH..sSSSSSS
OOOOOOO..HHHHHH..SSSSSSS
OOOOOOO..HHHHHH..SSSSSSS
OOOOOOOr HHHHHH .SSSSSSS
"""

N_ROWS = 25
N_COLS = 24

ROOM_LETTERS: dict[str, str] = {
    "K": "Kitchen", "B": "Ballroom", "C": "Conservatory", "D": "Dining",
    "I": "Billiard", "L": "Library", "O": "Lounge", "H": "Hall", "S": "Study",
}
START_LETTERS: dict[str, str] = {
    "w": "White", "g": "Green", "p": "Peacock", "u": "Plum", "r": "Scarlett", "m": "Mustard",
}

SECRET_PASSAGES: dict[str, str] = {
    "Kitchen": "Study",
    "Study": "Kitchen",
    "Conservatory": "Lounge",
    "Lounge": "Conservatory",
}


@dataclass(frozen=True, order=True)
class Square:
    """One corridor square, `row` 0-24 from the top, `col` 0-23 from the
    left, as in `BOARD_MAP`."""

    row: int
    col: int


@dataclass(frozen=True)
class HallwayCell:
    """Legacy: a cell of the ring board played until 2026-09-15 (edge
    `room_a`-`room_b`, `k` from 1 next to `room_a`). Only
    `clude_storage.records` builds one, reading a version-1 or -2
    record; `room_of` and `node_sort_key` accept it so a replayed ring
    game keeps its positions, and every other function here refuses it.
    """

    room_a: str
    room_b: str
    k: int


Node = Union[str, Square]

# Every door: (room, door cell, the corridor square it opens onto). The
# door cell is part of the room (a lower-case letter in the map); the
# token steps into the room from the square. Three doors -- the
# Conservatory's, the Lounge's and the Study's -- have a second corridor
# square beside them that the wall blocks, which is why this is a table
# and not parsed from the map. Measured as wall gaps in the reference
# image (docs/board.md).
DOORS: list[tuple[str, Square, Square]] = [
    ("Kitchen", Square(6, 4), Square(7, 4)),
    ("Ballroom", Square(5, 8), Square(5, 7)),
    ("Ballroom", Square(5, 15), Square(5, 16)),
    ("Ballroom", Square(7, 9), Square(8, 9)),
    ("Ballroom", Square(7, 14), Square(8, 14)),
    ("Conservatory", Square(4, 18), Square(5, 18)),
    ("Dining", Square(12, 7), Square(12, 8)),
    ("Dining", Square(15, 6), Square(16, 6)),
    ("Billiard", Square(9, 18), Square(9, 17)),
    ("Billiard", Square(12, 22), Square(13, 22)),
    ("Library", Square(14, 20), Square(13, 20)),
    ("Library", Square(16, 17), Square(16, 16)),
    ("Lounge", Square(19, 6), Square(18, 6)),
    ("Hall", Square(18, 11), Square(17, 11)),
    ("Hall", Square(18, 12), Square(17, 12)),
    ("Hall", Square(20, 14), Square(20, 15)),
    ("Study", Square(21, 17), Square(20, 17)),
]


def _parse_map() -> tuple[
    frozenset[Square], dict[str, frozenset[Square]], dict[str, frozenset[Square]],
    frozenset[Square], dict[str, Square],
]:
    lines = BOARD_MAP.split("\n")[:N_ROWS]
    assert len(lines) == N_ROWS, len(lines)
    corridor: set[Square] = set()
    rooms: dict[str, set[Square]] = {room: set() for room in ROOMS}
    door_cells: dict[str, set[Square]] = {room: set() for room in ROOMS}
    cellar: set[Square] = set()
    starts: dict[str, Square] = {}
    for r, line in enumerate(lines):
        line = line.rstrip().ljust(N_COLS)  # editors strip trailing spaces; pad, never trust them
        assert len(line) == N_COLS, (r, len(line))
        for c, ch in enumerate(line):
            sq = Square(r, c)
            if ch == ".":
                corridor.add(sq)
            elif ch == "X":
                cellar.add(sq)
            elif ch in ROOM_LETTERS:
                rooms[ROOM_LETTERS[ch]].add(sq)
            elif ch.upper() in ROOM_LETTERS:
                rooms[ROOM_LETTERS[ch.upper()]].add(sq)
                door_cells[ROOM_LETTERS[ch.upper()]].add(sq)
            elif ch in START_LETTERS:
                starts[START_LETTERS[ch]] = sq
                corridor.add(sq)  # a start square is walked like any other
            else:
                assert ch == " ", (r, c, ch)
    return (
        frozenset(corridor),
        {room: frozenset(cells) for room, cells in rooms.items()},
        {room: frozenset(cells) for room, cells in door_cells.items()},
        frozenset(cellar),
        starts,
    )


CORRIDOR, ROOM_CELLS, DOOR_CELLS, CELLAR, START_SQUARES = _parse_map()


def _check_doors() -> None:
    seen: set[Square] = set()
    for room, cell, square in DOORS:
        assert cell in DOOR_CELLS[room], (room, cell)
        assert square in CORRIDOR, (room, square)
        assert abs(cell.row - square.row) + abs(cell.col - square.col) == 1, (room, cell, square)
        seen.add(cell)
    for room, cells in DOOR_CELLS.items():
        assert cells <= seen, (room, cells - seen)
    assert set(START_SQUARES) == set(SUSPECTS), START_SQUARES


_check_doors()

# Corridor square -> the room it lets a token into (a square serves one
# door only; a test checks it), and room -> the squares outside its doors.
ENTRANCES: dict[Square, str] = {square: room for room, _cell, square in DOORS}
EXITS: dict[str, tuple[Square, ...]] = {
    room: tuple(sorted(square for r, _c, square in DOORS if r == room)) for room in ROOMS
}


def start_position(suspect: str) -> Node:
    """The start square of a suspect's token."""
    return START_SQUARES[suspect]


def room_of(node) -> str | None:
    """The room a node represents, or None for a corridor square (or a
    legacy `HallwayCell`)."""
    return node if isinstance(node, str) else None


def _adjacent(square: Square) -> list[Square]:
    r, c = square.row, square.col
    return [
        sq
        for sq in (Square(r - 1, c), Square(r + 1, c), Square(r, c - 1), Square(r, c + 1))
        if sq in CORRIDOR
    ]


def neighbors(node: Node) -> list[Node]:
    """Nodes one step away. From a room: the corridor squares outside its
    doors. From a square: the orthogonal corridor squares plus, if the
    square is outside a door, that room. Secret passages are not steps
    (`room_distances` adds them; the engine offers them as a move)."""
    if isinstance(node, str):
        return list(EXITS[node])
    if not isinstance(node, Square):
        raise TypeError(f"not a board position: {node!r}")
    result: list[Node] = list(_adjacent(node))
    room = ENTRANCES.get(node)
    if room is not None:
        result.append(room)
    return result


def reachable(
    start: Node, roll: int, occupied: frozenset[Square], room_left: str | None = None
) -> set[Node]:
    """Where a token may end its move from `start` with `roll`.

    Every simple path of up to `roll` steps through unoccupied corridor
    squares is walked. A room reached at any step is a destination and
    ends that path; a corridor square is a destination only at exactly
    `roll` steps (the whole roll must be used). A token starting in a
    room leaves through any of its doors and may not re-enter that room
    this move; `room_left` names a room to forbid when the start is a
    square (unused by the engine, kept for tests and callers that walk
    a move in parts).

    Parameters
    ----------
    start : Node
        Current position. Never in the result.
    roll : int
        The die, 1-6.
    occupied : frozenset[Square]
        Corridor squares holding other tokens; neither passed nor
        landed on.
    room_left : str or None
        A room the path may not enter; the start room when `start` is
        a room.

    Returns
    -------
    set[Node]
        Rooms and squares the move may end on.
    """
    if isinstance(start, str):
        room_left = start
    elif not isinstance(start, Square):
        raise TypeError(f"not a board position: {start!r}")
    result: set[Node] = set()

    def walk(node: Node, depth: int, visited: frozenset[Square]) -> None:
        for nb in neighbors(node):
            if isinstance(nb, str):
                if nb != room_left:
                    result.add(nb)
                continue
            if nb in occupied or nb in visited:
                continue
            if depth + 1 == roll:
                result.add(nb)
            else:
                walk(nb, depth + 1, visited | {nb})

    if roll >= 1:
        walk(start, 0, frozenset([start]) if isinstance(start, Square) else frozenset())
    return result


@lru_cache(maxsize=None)
def room_distances(node: Node) -> dict[str, int]:
    """Steps from `node` to every room by breadth-first search over
    corridor squares, rooms (passed through) and secret passages (one
    step), ignoring other tokens and the per-move rules. A proximity
    measure, not a turn count.

    Parameters
    ----------
    node : Node
        A room name or `Square` (both hashable, so results cache).

    Returns
    -------
    dict[str, int]
        Room -> steps; 0 for `node` itself when it is a room.
    """
    dist: dict[Node, int] = {node: 0}
    frontier: list[Node] = [node]
    while frontier:
        next_frontier: list[Node] = []
        for n in frontier:
            nbs = list(neighbors(n))
            if isinstance(n, str) and n in SECRET_PASSAGES:
                nbs.append(SECRET_PASSAGES[n])
            for nb in nbs:
                if nb not in dist:
                    dist[nb] = dist[n] + 1
                    next_frontier.append(nb)
        frontier = next_frontier
    return {room: dist[room] for room in ROOMS}


def node_sort_key(node) -> tuple:
    """A total order over positions that does not depend on Python's
    per-process string-hash randomization: rooms by name, then squares
    by (row, col), then legacy cells. `reachable` returns a set; sort by
    this key before any seeded RNG indexes into it (see the Phase 5
    note that used to live here: an identical seed once produced a
    different game per process for want of it)."""
    if isinstance(node, str):
        return (0, node, 0, 0, "")
    if isinstance(node, Square):
        return (1, "", node.row, node.col, "")
    return (2, node.room_a, node.k, 0, node.room_b)
