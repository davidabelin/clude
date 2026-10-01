"""The Classic board drawn as SVG, straight from `clude_core.board`.

Nothing here hard-codes the board. The rooms, the corridor, the cellar,
the doors and the start squares all come from `BOARD_MAP` and `DOORS`, so
the drawing cannot drift from the board the engine actually plays -- the
mistake worth designing out, since a replay showing a token somewhere the
rules would not allow is worse than no picture at all.

No colour is set here either: every shape carries a class and
`static/style.css` colours it, which is what lets Phase 10 restyle the
board without touching this module (`docs/phase8.1-plan.md` 1).

Dressed (Phase 10f, plan section 8), the board gains shapes and still
no paint: a floor pattern per room in a `<defs>` whose children carry
classes (the stylesheet fills each room with its own and colours it;
nine since 2026-10-01, four before), a brass hairline inside every
wall, every door a closed leaf across its doorway, hinged at one jamb
so a page can swing it open as a token goes in (2026-10-01; a brass bar
with a rivet at each end before, which read as more wall), a marker in
the corner of each room a secret passage leaves from, an initial on
every token, and the logo in the cellar where the wordmark was. An Engraved look asks for it; Legacy's sheet has no rules for any
of it, so Legacy gets the board it was frozen with.

Imports no Flask, so it can be tested and rendered on its own.
"""
from __future__ import annotations

from clude_core import board
from clude_core.board import Square

from . import logo

CELL = 24
"""Side of one grid cell, in SVG user units. The viewBox scales, so this
only sets the ratio of stroke widths and text to the grid."""

SUSPECT_SLUG = {
    "Scarlett": "scarlett",
    "Mustard": "mustard",
    "Plum": "plum",
    "Peacock": "peacock",
    "Green": "green",
    "White": "white",
}
"""Suspect -> the class suffix that colours its token and start square."""

INITIALS = {"Scarlett": "S", "Mustard": "M", "White": "W", "Green": "G", "Peacock": "Pe", "Plum": "Pl"}
"""The letter on a dressed token, so the six are told apart without
colour (plan 12). Peacock and Plum share a P, so both carry two (10a)."""

def _floor(room: str, width: float, height: float, shapes: str) -> str:
    return (
        f'<pattern id="floor-{room_slug(room)}" class="floor floor-{room_slug(room)}" '
        f'patternUnits="userSpaceOnUse" width="{width}" height="{height}">'
        f'<rect class="tone-bg" width="{width}" height="{height}"/>{shapes}</pattern>'
    )


def room_slug(room: str) -> str:
    """The room's name as an id and class suffix: "Billiard" -> "billiard"."""
    return room.lower().replace(" ", "-")


FLOORS = {
    # Checker tile.
    "Kitchen": (12, 12, '<rect class="tone-fill" width="6" height="6"/><rect class="tone-fill" x="6" y="6" width="6" height="6"/>'),
    # Chevron parquet.
    "Ballroom": (16, 8, '<path class="tone-line" d="M0 6 L4 2 L8 6 L12 2 L16 6"/>'),
    # A diamond trellis.
    "Conservatory": (10, 10, '<path class="tone-line" d="M0 0 L10 10 M10 0 L0 10"/>'),
    # Baize, stippled.
    "Billiard": (6, 6, '<circle class="tone-dot" cx="1.5" cy="1.5" r="0.6"/><circle class="tone-dot" cx="4.5" cy="4.5" r="0.6"/>'),
    # Panelling: a double rule every eight.
    "Library": (8, 8, '<path class="tone-line" d="M0.4 0 V8 M2.4 0 V8"/>'),
    # A single diagonal hatch.
    "Study": (6, 6, '<path class="tone-line" d="M-1.5 1.5 L1.5 -1.5 M0 6 L6 0 M4.5 7.5 L7.5 4.5"/>'),
    # Flagstones, staggered.
    "Hall": (16, 12, '<path class="tone-line" d="M0 0.3 H16 M0 6.3 H16 M0.3 0 V6 M8.3 6 V12"/>'),
    # A rug of rosettes.
    "Lounge": (12, 12, '<circle class="tone-ring" cx="6" cy="6" r="2"/><circle class="tone-dot" cx="6" cy="6" r="0.7"/>'
               '<circle class="tone-dot" cx="0" cy="0" r="0.7"/><circle class="tone-dot" cx="12" cy="0" r="0.7"/>'
               '<circle class="tone-dot" cx="0" cy="12" r="0.7"/><circle class="tone-dot" cx="12" cy="12" r="0.7"/>'),
    # Planks, staggered.
    "Dining": (24, 8, '<path class="tone-line" d="M0 0.3 H24 M0 4.3 H24 M8 0 V4 M20 4 V8"/>'),
}
"""Each room's floor (2026-10-01), at a pitch that survives a phone:
nine patterns, no two alike, where 10f had four shared between them.
The stylesheet gives each its own pale tint."""

FLOOR_PATTERNS = "<defs>" + "".join(_floor(room, *FLOORS[room]) for room in sorted(FLOORS)) + "</defs>"
"""The floors as one `<defs>`. Each pattern holds a background rect,
since a pattern is transparent wherever it does not draw (10a), and
carries the class `floor-<room>`, which the stylesheet tints."""

_DOOR_PAIRS = frozenset((cell, square) for _room, cell, square in board.DOORS)
"""Every (door cell, corridor square) pair, to leave a gap in the room's
outline where a token can actually walk through."""


def _escape(text) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _xy(square: Square) -> tuple[float, float]:
    """Top-left corner of a cell, in user units."""
    return square.col * CELL, square.row * CELL


def _centre(square: Square) -> tuple[float, float]:
    x, y = _xy(square)
    return x + CELL / 2, y + CELL / 2


def room_centre(room: str) -> tuple[float, float]:
    """The middle of a room's cells, where its tokens go.

    The mean of the cells rather than the middle of a bounding box: every
    room on this board is close enough to rectangular that the mean lands
    inside it, and the mean does not drift into a notch.
    """
    cells = board.ROOM_CELLS[room]
    rows = sum(c.row for c in cells) / len(cells)
    cols = sum(c.col for c in cells) / len(cells)
    return (cols + 0.5) * CELL, (rows + 0.5) * CELL


def label_anchor(room: str) -> tuple[float, float]:
    """Where a room's name goes: above its centre, so the tokens that
    gather in the middle do not sit on top of it.

    Falls back to the centre when the shifted point would leave the room,
    which a notched room could do.
    """
    cx, cy = room_centre(room)
    lifted = cy - CELL * 1.2
    cell = Square(int(lifted // CELL), int(cx // CELL))
    return (cx, lifted) if cell in board.ROOM_CELLS[room] else (cx, cy)


def node_centre(node) -> tuple[float, float]:
    """Where a token standing on `node` is drawn."""
    if isinstance(node, Square):
        return _centre(node)
    return room_centre(node)


def _room_outline(room: str) -> list[str]:
    """One line per cell edge that borders something other than this room,
    minus the edges a door opens through.

    Cheaper than unioning the cells into a polygon, and it gives the same
    picture: a crisp wall with a gap at every door.
    """
    cells = board.ROOM_CELLS[room]
    lines = []
    for cell in sorted(cells):
        x, y = _xy(cell)
        sides = (
            (Square(cell.row - 1, cell.col), (x, y, x + CELL, y)),
            (Square(cell.row + 1, cell.col), (x, y + CELL, x + CELL, y + CELL)),
            (Square(cell.row, cell.col - 1), (x, y, x, y + CELL)),
            (Square(cell.row, cell.col + 1), (x + CELL, y, x + CELL, y + CELL)),
        )
        for neighbour, (x1, y1, x2, y2) in sides:
            if neighbour in cells:
                continue
            if (cell, neighbour) in _DOOR_PAIRS:
                continue  # a doorway, drawn as a door instead of a wall
            lines.append(
                f'<line class="board-wall" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'
            )
    return lines


def _door_marker(room: str, cell: Square, square: Square) -> str:
    """A thick stroke across the threshold between a door cell and the
    corridor square it opens onto."""
    x, y = _xy(cell)
    if square.row < cell.row:
        x1, y1, x2, y2 = x, y, x + CELL, y
    elif square.row > cell.row:
        x1, y1, x2, y2 = x, y + CELL, x + CELL, y + CELL
    elif square.col < cell.col:
        x1, y1, x2, y2 = x, y, x, y + CELL
    else:
        x1, y1, x2, y2 = x + CELL, y, x + CELL, y + CELL
    return (
        f'<line class="board-door" data-room="{_escape(room)}" '
        f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'
    )


def _door_leaf(index: int, room: str, cell: Square, square: Square, hinge_at_start: bool) -> str:
    """A door, closed (2026-10-01): a leaf lying across the doorway from
    its hinge to the other jamb, `data-door` its index in `board.DOORS`.
    Its style carries the hinge as `transform-origin` and, as `--swing`,
    the quarter turn that opens it into the room, so the stylesheet can
    swing it open and shut as a token comes through -- geometry, never
    paint."""
    door = _door_marker(room, cell, square)
    x1, y1, x2, y2 = (float(door.split(f'{name}="')[1].split('"')[0]) for name in ("x1", "y1", "x2", "y2"))
    (hx, hy), (ox, oy) = ((x1, y1), (x2, y2)) if hinge_at_start else ((x2, y2), (x1, y1))
    dx, dy = cell.col - square.col, cell.row - square.row  # into the room
    # Turning (ox - hx, oy - hy) by +90 degrees in SVG's y-down frame
    # gives (-(oy - hy), ox - hx); if that points into the room, the
    # door opens clockwise.
    clockwise = (-(oy - hy), ox - hx) == (dx * CELL, dy * CELL)
    return (
        f'<line class="board-door board-door-leaf" data-door="{index}" data-room="{_escape(room)}" '
        f'x1="{hx:g}" y1="{hy:g}" x2="{ox:g}" y2="{oy:g}" '
        f'style="transform-origin: {hx:g}px {hy:g}px; --swing: {90 if clockwise else -90}deg"/>'
    )


def passage_cell(room: str) -> Square:
    """The cell of `room` a secret passage's marker sits on: the one
    farthest from the middle of the board, the room's outer corner, as
    on the printed board."""
    mid_row, mid_col = (board.N_ROWS - 1) / 2, (board.N_COLS - 1) / 2
    return max(sorted(board.ROOM_CELLS[room]), key=lambda c: (c.row - mid_row) ** 2 + (c.col - mid_col) ** 2)


def _passage_marker(room: str, to: str) -> str:
    """A secret passage's mark (2026-10-01): a plate in the room's outer
    corner with a flight of steps going down toward that corner, titled
    with where it leads."""
    cell = passage_cell(room)
    x, y = _xy(cell)
    # The steps are drawn going down toward the bottom-left; flipped to
    # go down toward whichever corner this room is in.
    sx = -1 if cell.col > (board.N_COLS - 1) / 2 else 1
    sy = 1 if cell.row > (board.N_ROWS - 1) / 2 else -1
    c = CELL / 2
    return (
        f'<g class="board-passage" data-room="{_escape(room)}" data-to="{_escape(to)}" '
        f'transform="translate({x + c:g} {y + c:g}) scale({sx} {sy})">'
        f"<title>Secret passage to the {_escape(to)}</title>"
        f'<rect class="board-passage-plate" x="{-c + 2.5:g}" y="{-c + 2.5:g}" width="{CELL - 5:g}" height="{CELL - 5:g}"/>'
        '<path class="board-passage-steps" d="M-6.5 6.5 V2.5 H-2.5 V-1.5 H1.5 V-5.5 H6.5"/>'
        "</g>"
    )


def _hinges() -> list[bool]:
    """For each of `board.DOORS`, whether its hinge is the door edge's
    first end: the end no other door of the same room shares, so a pair
    side by side (the Hall's) opens as a double door; the first end
    otherwise."""
    ends: dict = {}
    edges = []
    for room, cell, square in board.DOORS:
        door = _door_marker(room, cell, square)
        a, b = ((door.split(f'{n}="')[1].split('"')[0] for n in pair) for pair in (("x1", "y1"), ("x2", "y2")))
        a, b = tuple(a), tuple(b)
        edges.append((room, a, b))
        for end in (a, b):
            ends[(room, end)] = ends.get((room, end), 0) + 1
    return [ends[(room, a)] == 1 for room, a, b in edges]


def _fan(nodes_at: list, centre: tuple[float, float]) -> list[tuple[float, float]]:
    """Spread several tokens sharing one node around its centre.

    Rooms hold up to six tokens and a corridor square exactly one, so this
    only ever has to open out a room; one token sits dead centre.
    """
    cx, cy = centre
    if len(nodes_at) == 1:
        return [(cx, cy)]
    step = CELL * 0.62
    spread = (len(nodes_at) - 1) / 2
    return [(cx + (i - spread) * step, cy) for i in range(len(nodes_at))]


def token_points(tokens: dict) -> dict:
    """Suspect -> the point its token is drawn at, fanning out any that
    share a node so they do not stack.

    The one place that decides where a token goes. It has to be, because
    two things ask: this module when it draws the board, and
    `replay_data.screen_payload` when it sends positions to the scrubber.
    They disagreed once -- the drawing fanned and the payload did not, so
    two characters in one room sat exactly on top of each other the
    moment the page became live.
    """
    by_node: dict = {}
    for suspect, node in tokens.items():
        by_node.setdefault(node, []).append(suspect)
    points = {}
    for node, suspects in by_node.items():
        ordered = sorted(suspects)
        for suspect, point in zip(ordered, _fan(ordered, node_centre(node))):
            points[suspect] = point
    return points


def cellar_box() -> tuple:
    """(x, y, width, height) of the cellar in board units: 5 x 7 cells."""
    rows = [c.row for c in board.CELLAR]
    cols = [c.col for c in board.CELLAR]
    return (
        min(cols) * CELL,
        min(rows) * CELL,
        (max(cols) - min(cols) + 1) * CELL,
        (max(rows) - min(rows) + 1) * CELL,
    )


def board_svg(tokens=None, *, title="The board", dressed=False) -> str:
    """The board as one SVG string.

    Parameters
    ----------
    tokens : dict or None
        Suspect name -> the node its token stands on, as
        `GameState.positions` gives once seats are read through
        `suspects_in_play`. Tokens sharing a room are fanned out.
    title : str
        The SVG's accessible title.
    dressed : bool
        Phase 10f's decoration (the module docstring): what an Engraved
        look asks for. Off, the drawing is exactly the board of 8.1-10e.

    Returns
    -------
    str
        An `<svg>` element. Every shape carries a class and no colour, so
        `static/style.css` decides how it looks.
    """
    width, height = board.N_COLS * CELL, board.N_ROWS * CELL
    out = [
        f'<svg class="board{" board-engraved" if dressed else ""}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{_escape(title)}" '
        'xmlns="http://www.w3.org/2000/svg">',
        f"<title>{_escape(title)}</title>",
    ]
    if dressed:
        out.append(FLOOR_PATTERNS)
    # Behind everything, so the cells no one can stand on read as
    # off-board rather than as the page showing through.
    out.append(f'<rect class="board-void" x="0" y="0" width="{width}" height="{height}"/>')

    out.append('<g class="board-corridor">')
    for square in sorted(board.CORRIDOR):
        x, y = _xy(square)
        out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}"/>')
    out.append("</g>")

    out.append('<g class="board-cellar">')
    for square in sorted(board.CELLAR):
        x, y = _xy(square)
        out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}"/>')
    if board.CELLAR and dressed:
        # The logo in the middle of the board (plan 8, D5).
        x, y, w, h = cellar_box()
        out.append(f'<g class="board-logo" transform="translate({x} {y})">{logo.cellar(w, h)}</g>')
    elif board.CELLAR:
        rows = [c.row for c in board.CELLAR]
        cols = [c.col for c in board.CELLAR]
        cx = (sum(cols) / len(cols) + 0.5) * CELL
        cy = (sum(rows) / len(rows) + 0.5) * CELL
        # Undressed, the wordmark keeps the cellar from reading as a hole.
        out.append(
            f'<text class="board-mark" x="{cx}" y="{cy}" '
            'text-anchor="middle" dominant-baseline="middle">clude</text>'
        )
    out.append("</g>")

    inner = []
    for room in sorted(board.ROOM_CELLS):
        out.append(f'<g class="board-room" data-room="{_escape(room)}">')
        for cell in sorted(board.ROOM_CELLS[room]):
            x, y = _xy(cell)
            out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}"/>')
        walls = _room_outline(room)
        out.extend(walls)
        inner.extend(wall.replace('class="board-wall"', 'class="board-wall-inner"') for wall in walls)
        cx, cy = label_anchor(room)
        out.append(
            f'<text class="board-label" x="{cx}" y="{cy}" '
            f'text-anchor="middle" dominant-baseline="middle">{_escape(room)}</text>'
        )
        out.append("</g>")

    if dressed:
        # Walls as a double rule: the ink line, a brass hairline over it
        # (10a found this reads engraved and needs no offset geometry).
        out.append('<g class="board-walls-inner">')
        out.extend(inner)
        out.append("</g>")

    if dressed:
        # Doors closed, each ready to swing open into its room.
        out.extend(
            _door_leaf(index, room, cell, square, hinge)
            for index, ((room, cell, square), hinge) in enumerate(zip(board.DOORS, _hinges()))
        )
        out.extend(_passage_marker(room, to) for room, to in sorted(board.SECRET_PASSAGES.items()))
    else:
        out.extend(_door_marker(room, cell, square) for room, cell, square in board.DOORS)

    for suspect, square in sorted(board.START_SQUARES.items()):
        x, y = _xy(square)
        inset = CELL * 0.26
        slug = SUSPECT_SLUG.get(suspect, "unknown")
        # A square, not a disc: a start square is a place, and tokens are
        # the round things. Drawn alike they read as extra pieces.
        out.append(
            f'<rect class="board-start suspect-{slug}" '
            f'data-suspect="{_escape(suspect)}" '
            f'x="{x + inset}" y="{y + inset}" '
            f'width="{CELL - 2 * inset}" height="{CELL - 2 * inset}"/>'
        )

    for suspect, (cx, cy) in sorted(token_points(tokens or {}).items()):
        slug = SUSPECT_SLUG.get(suspect, "unknown")
        out.append(
            f'<circle class="board-token suspect-{slug}" '
            f'data-suspect="{_escape(suspect)}" '
            f'cx="{cx}" cy="{cy}" r="{CELL * 0.36}"><title>'
            f"{_escape(suspect)}</title></circle>"
        )
        if dressed:
            # Placed by a CSS transform rather than x and y, so it can
            # glide with its disc (a text element's x and y cannot be
            # transitioned); the pages move both.
            out.append(
                f'<text class="board-initial suspect-{slug}" data-suspect="{_escape(suspect)}" '
                f'x="0" y="0" style="transform: translate({cx}px, {cy}px)" aria-hidden="true">'
                f"{_escape(INITIALS.get(suspect, suspect[:1]))}</text>"
            )

    out.append("</svg>")
    return "\n".join(out)
