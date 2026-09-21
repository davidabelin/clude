"""The Classic board drawn as SVG, straight from `clude_core.board`.

Nothing here hard-codes the board. The rooms, the corridor, the cellar,
the doors and the start squares all come from `BOARD_MAP` and `DOORS`, so
the drawing cannot drift from the board the engine actually plays -- the
mistake worth designing out, since a replay showing a token somewhere the
rules would not allow is worse than no picture at all.

No colour is set here either: every shape carries a class and
`static/style.css` colours it, which is what lets Phase 10 restyle the
board without touching this module (`docs/phase8.1-plan.md` 1).

Imports no Flask, so it can be tested and rendered on its own.
"""
from __future__ import annotations

from clude_core import board
from clude_core.board import Square

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


def board_svg(tokens=None, *, title="The board") -> str:
    """The board as one SVG string.

    Parameters
    ----------
    tokens : dict or None
        Suspect name -> the node its token stands on, as
        `GameState.positions` gives once seats are read through
        `suspects_in_play`. Tokens sharing a room are fanned out.
    title : str
        The SVG's accessible title.

    Returns
    -------
    str
        An `<svg>` element. Every shape carries a class and no colour, so
        `static/style.css` decides how it looks.
    """
    width, height = board.N_COLS * CELL, board.N_ROWS * CELL
    out = [
        f'<svg class="board" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{_escape(title)}" '
        'xmlns="http://www.w3.org/2000/svg">',
        f"<title>{_escape(title)}</title>",
        # Behind everything, so the cells no one can stand on read as
        # off-board rather than as the page showing through.
        f'<rect class="board-void" x="0" y="0" width="{width}" height="{height}"/>',
    ]

    out.append('<g class="board-corridor">')
    for square in sorted(board.CORRIDOR):
        x, y = _xy(square)
        out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}"/>')
    out.append("</g>")

    out.append('<g class="board-cellar">')
    for square in sorted(board.CELLAR):
        x, y = _xy(square)
        out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}"/>')
    if board.CELLAR:
        rows = [c.row for c in board.CELLAR]
        cols = [c.col for c in board.CELLAR]
        cx = (sum(cols) / len(cols) + 0.5) * CELL
        cy = (sum(rows) / len(rows) + 0.5) * CELL
        # The middle of the board carries a logo in Phase 10; until then
        # the wordmark keeps the cellar from reading as a hole.
        out.append(
            f'<text class="board-mark" x="{cx}" y="{cy}" '
            'text-anchor="middle" dominant-baseline="middle">clude</text>'
        )
    out.append("</g>")

    for room in sorted(board.ROOM_CELLS):
        out.append(f'<g class="board-room" data-room="{_escape(room)}">')
        for cell in sorted(board.ROOM_CELLS[room]):
            x, y = _xy(cell)
            out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}"/>')
        out.extend(_room_outline(room))
        cx, cy = label_anchor(room)
        out.append(
            f'<text class="board-label" x="{cx}" y="{cy}" '
            f'text-anchor="middle" dominant-baseline="middle">{_escape(room)}</text>'
        )
        out.append("</g>")

    for room, cell, square in board.DOORS:
        out.append(_door_marker(room, cell, square))

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

    out.append("</svg>")
    return "\n".join(out)
