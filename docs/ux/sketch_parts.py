"""The parts the Phase 10a artboards are built from (docs/ux/build_sketches.py).

Three things, none of them guessed:

- **The moment.** A seeded six-seat game with a person at Scarlett,
  played through `clude_training.table.TableGame` exactly as a web
  table is, stopped mid-game and again at its end. Her hand, her
  notepad, every seat's certainty, the narration from her seat and each
  kind of decision request come from the game, so the artboards show a
  real deal, real positions and real lines.
- **The decorated board.** `clude_web.board_svg.board_svg` drawn as it
  is today, then dressed the way docs/phase10-plan.md section 8 says
  10f will: floor patterns as `<pattern>` defs, walls as a double rule,
  rivets at the door thresholds, an initial on every token, the logo in
  the cellar, the lit destinations as an overlay. Every added shape is
  classed and uncoloured, like the generator's own; the stylesheet does
  the rest. The generator is not touched.
- **The four logo candidates** (section 9, D5), as uncoloured, classed
  SVG groups in a 120 x 168 box (the cellar, 5 x 7 cells) with a
  square mark for the header bar and the favicon.

Run from the repo root; imports the packages by path.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import clude_constraints  # noqa: E402
from clude_core.domain import SUSPECTS, WEAPONS  # noqa: E402
from clude_core.events import GameOverEvent  # noqa: E402
from clude_storage.records import node_from_json, node_to_json  # noqa: E402
from clude_training.table import TableGame, TableSetup  # noqa: E402
from clude_web import board_svg, tables  # noqa: E402

CELL = board_svg.CELL
CATEGORY_SIZES = {"suspects": 6, "weapons": 6, "rooms": 9}
INITIALS = {"Scarlett": "S", "Mustard": "M", "White": "W", "Green": "G", "Peacock": "Pe", "Plum": "Pl"}
"""Peacock and Plum share an initial, so each gets two letters: a
finding for 10f, which section 8 wrote as one initial per token."""


# --- the moment ---------------------------------------------------------


def certainty(game, seat: int) -> float:
    """Bits gained toward the envelope from `seat`'s floor, on the 9h
    scale: 0 at 1/324, 1 when certain."""
    obs = clude_constraints.observe(game.state, seat)
    n = 1
    for category, cards in tables.CATEGORIES:
        n *= sum(1 for card in cards if obs.mask.is_possible(card, clude_constraints.ENVELOPE))
    return round(1 - math.log2(max(n, 1)) / math.log2(324), 3)


def positions(game) -> dict:
    return {game.suspects[seat]: node for seat, node in game.snapshot.positions.items()}


def lines(game, names: list, viewer: int, upto=None) -> list:
    events = game.events if upto is None else game.events[:upto]
    out = []
    for index, event in enumerate(events):
        kind, text = tables.describe_for(event, game, names, viewer)
        out.append({"i": index, "turn": getattr(event, "turn", 0), "kind": kind, "text": text})
    return out


def play_moment(seed: int, stop: int) -> dict:
    """Play `seed` with David at Scarlett and five characters, answering
    her requests plainly (a room if one is reachable, a suggestion she
    cannot disprove herself, never an accusation, the first card
    offered), until `stop` turns have been played or the game ends.

    Returns the state then, plus every request she was asked, each with
    the board as it stood: what the artboards need."""
    setup = TableSetup.from_roster(
        ["Mustard", "White", "Green", "Peacock", "Plum"], 6, seed, humans={"Scarlett": "david"}
    )
    game = TableGame(setup)
    names = [f"{token} (David)" if kind == "human" else token for token, kind in zip(game.suspects, game.kinds)]
    hand = sorted(game.state.hands[0])
    requests: list = []
    while not game.finished and game.turns < stop:
        if game.pending is None:
            game.run(1)
            continue
        request = dict(game.snapshot.pending)
        if request["kind"] == "movement":
            request["options"] = [
                dict(option, x=x, y=y, distances=tables._distance_line(node))
                for option in request["options"]
                for node in [node_from_json(option["to"])]
                for x, y in [board_svg.node_centre(node)]
            ]
        requests.append(
            {
                "request": request,
                "turn": game.turns,
                "n_events": len(game.events),
                "positions": positions(game),
                "lines": lines(game, names, 0),
            }
        )
        kind = request["kind"]
        if kind == "movement":
            rooms = [o for o in request["options"] if isinstance(o["to"], str) and o["move"] != "stay"]
            pick = rooms[0] if rooms else request["options"][0]
            answer = {"move": pick["move"], "to": pick["to"]}
        elif kind == "suggestion":
            answer = {
                "suspect": next(s for s in SUSPECTS if s not in hand),
                "weapon": next(w for w in WEAPONS if w not in hand),
            }
        elif kind == "accusation":
            answer = None
        else:
            answer = {"card": request["candidates"][0]}
        game.answer(0, game.seq, answer)

    final = game.events[-1] if game.finished and isinstance(game.events[-1], GameOverEvent) else None
    return {
        "seed": seed,
        "game": game,
        "names": names,
        "suspects": list(game.suspects),
        "kinds": list(game.kinds),
        "turns": game.turns,
        "finished": game.finished,
        "hand": hand,
        "hands": {game.suspects[seat]: sorted(cards) for seat, cards in game.state.hands.items()},
        "notepad": tables.notepad(game, 0),
        "certainties": [certainty(game, seat) for seat in range(6)],
        "positions": positions(game),
        "lines": lines(game, names, 0),
        "requests": requests,
        "winner": None if final is None else names[final.winner] if final.winner is not None else None,
        "winner_seat": None if final is None else final.winner,
        "solution": None if final is None else list(final.solution),
        "active": list(game.snapshot.active),
    }


def notepad_for(game, seat: int) -> list:
    """`tables.notepad` from another seat, for the replay's blocks."""
    return tables.notepad(game, seat)


# --- the decorated board ------------------------------------------------

PATTERN_DEFS = """<defs>
<pattern id="tone-parquet" patternUnits="userSpaceOnUse" width="8" height="8">
<rect class="tone-bg" width="8" height="8"/>
<path class="tone-line" d="M0 4 L4 0 M4 8 L8 4"/>
</pattern>
<pattern id="tone-tile" patternUnits="userSpaceOnUse" width="8" height="8">
<rect class="tone-bg" width="8" height="8"/>
<path class="tone-line" d="M0 0.3 H8 M0.3 0 V8"/>
</pattern>
<pattern id="tone-boards" patternUnits="userSpaceOnUse" width="24" height="6">
<rect class="tone-bg" width="24" height="6"/>
<path class="tone-line" d="M0 5.7 H24 M12 0 V6"/>
</pattern>
<pattern id="tone-rug" patternUnits="userSpaceOnUse" width="8" height="8">
<rect class="tone-bg" width="8" height="8"/>
<circle class="tone-dot" cx="2" cy="2" r="0.7"/>
<circle class="tone-dot" cx="6" cy="6" r="0.7"/>
</pattern>
<pattern id="hatch" patternUnits="userSpaceOnUse" width="3" height="3">
<path class="logo-hatch" d="M0 3 L3 0"/>
</pattern>
</defs>"""

_WALL = re.compile(r'<line class="board-wall" (x1="[^"]+" y1="[^"]+" x2="[^"]+" y2="[^"]+")/>')
_DOOR = re.compile(r'<line class="board-door" data-room="[^"]+" x1="([^"]+)" y1="([^"]+)" x2="([^"]+)" y2="([^"]+)"/>')
_TOKEN = re.compile(
    r'<circle class="board-token suspect-([a-z]+)" data-suspect="([^"]+)" cx="([^"]+)" cy="([^"]+)" r="[^"]+"><title>[^<]*</title></circle>'
)
_MARK = re.compile(r'<text class="board-mark"[^>]*>clude</text>')


def cellar_box() -> tuple:
    """(x, y, w, h) of the cellar in board units: 5 x 7 cells."""
    from clude_core import board

    rows = [c.row for c in board.CELLAR]
    cols = [c.col for c in board.CELLAR]
    return (min(cols) * CELL, min(rows) * CELL, (max(cols) - min(cols) + 1) * CELL, (max(rows) - min(rows) + 1) * CELL)


def decorate(svg: str, logo: str = "A", lit=None, thinking=None, viewbox=None, crop: bool = False) -> str:
    """Dress a generated board as 10f will: patterns, the inner brass
    hairline on every wall, rivets at the doors, initials on the tokens,
    the logo in the cellar, lit squares for `lit` (movement options with
    x, y) and a ring around `thinking`'s token (a suspect name)."""
    out = svg.replace('<svg class="board"', '<svg class="board board-engraved"', 1)
    out = out.replace("</title>", "</title>\n" + PATTERN_DEFS, 1)

    walls = _WALL.findall(out)
    inner = '<g class="board-walls-inner">\n' + "\n".join(f'<line class="board-wall-inner" {w}/>' for w in walls) + "\n</g>\n"
    first_door = out.find('<line class="board-door"')
    out = out[:first_door] + inner + out[first_door:]

    rivets = ['<g class="board-rivets">']
    for x1, y1, x2, y2 in _DOOR.findall(out):
        rivets.append(f'<circle class="board-rivet" cx="{x1}" cy="{y1}" r="1.7"/>')
        rivets.append(f'<circle class="board-rivet" cx="{x2}" cy="{y2}" r="1.7"/>')
    rivets.append("</g>")
    first_start = out.find('<rect class="board-start ')
    out = out[:first_start] + "\n".join(rivets) + "\n" + out[first_start:]

    def initial(match):
        slug, suspect, cx, cy = match.groups()
        return (
            match.group(0)
            + f'\n<text class="board-initial suspect-{slug}" x="{cx}" y="{cy}">{INITIALS.get(suspect, suspect[0])}</text>'
        )

    out = _TOKEN.sub(initial, out)

    x, y, w, h = cellar_box()
    out = _MARK.sub(f'<g class="board-logo" transform="translate({x} {y})">\n{logo_group(logo, w, h)}\n</g>', out)

    extras = []
    if lit:
        extras.append('<g class="board-lit">')
        for option in lit:
            if option.get("move") == "stay":
                continue
            size = CELL * 1.5 if isinstance(option["to"], str) else CELL
            cls = ' class="room"' if isinstance(option["to"], str) else ""
            extras.append(
                f'<rect{cls} x="{option["x"] - size / 2:.1f}" y="{option["y"] - size / 2:.1f}" width="{size:.1f}" height="{size:.1f}"/>'
            )
        extras.append("</g>")
    if thinking:
        for slug, suspect, cx, cy in _TOKEN.findall(svg):
            if suspect == thinking:
                extras.append(f'<circle class="board-thinking" cx="{cx}" cy="{cy}" r="{CELL * 0.36 + 3.5:.1f}"/>')
    if extras:
        out = out.replace("</svg>", "\n".join(extras) + "\n</svg>")

    if viewbox:
        out = re.sub(r'viewBox="[^"]+"', f'viewBox="{viewbox}"', out, count=1)
        if crop:
            out = crop_svg(out, *(float(v) for v in viewbox.split()))
    return out


_XY = re.compile(r'(?:x|cx)="([-\d.]+)"[^>]*?(?:y|cy)="([-\d.]+)"')
_LINE_XY = re.compile(r'x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"')


def crop_svg(svg: str, x: float, y: float, w: float, h: float) -> str:
    """Drop the cells, walls, doors, rivets and tokens that lie wholly
    outside the box: a cropped view of the board at a fraction of the
    size, for the logo boards, which show the cellar's neighbourhood."""
    slack = CELL
    def inside(px, py):
        return x - slack <= px <= x + w + slack and y - slack <= py <= y + h + slack
    kept = []
    for line in svg.splitlines():
        stripped = line.strip()
        if stripped.startswith(("<rect x=", "<rect class=\"board-start", "<circle class=\"board-rivet", "<circle class=\"board-token", "<text class=\"board-initial", "<text class=\"board-label")):
            m = _XY.search(stripped)
            if m and not inside(float(m.group(1)), float(m.group(2))):
                continue
        elif stripped.startswith("<line class=\"board-"):
            m = _LINE_XY.search(stripped)
            if m and not (inside(float(m.group(1)), float(m.group(2))) or inside(float(m.group(3)), float(m.group(4)))):
                continue
        kept.append(line)
    return "\n".join(kept)


def board(positions: dict, **kwargs) -> str:
    """The decorated board with tokens at `positions` (suspect -> node)."""
    return decorate(board_svg.board_svg(positions), **kwargs)


# --- the logo candidates ------------------------------------------------


def _rivets(x, y, w, h, inset=5.0, r=2.2) -> str:
    return "".join(
        f'<circle class="logo-rivet" cx="{cx}" cy="{cy}" r="{r}"/>'
        for cx in (x + inset, x + w - inset)
        for cy in (y + inset, y + h - inset)
    )


def keyhole(cx: float, cy: float, s: float) -> str:
    """The keyhole-c: an escutcheon whose keyway is a lowercase c.
    `s` is the height."""
    w, h = s * 0.82, s
    top = cy - h / 2
    path = (
        f"M{cx} {top} C{cx + w * 0.55} {top} {cx + w / 2} {top + h * 0.42} {cx + w / 2} {top + h * 0.58} "
        f"C{cx + w / 2} {top + h * 0.86} {cx + w * 0.3} {top + h} {cx} {top + h} "
        f"C{cx - w * 0.3} {top + h} {cx - w / 2} {top + h * 0.86} {cx - w / 2} {top + h * 0.58} "
        f"C{cx - w / 2} {top + h * 0.42} {cx - w * 0.55} {top} {cx} {top} Z"
    )
    return (
        f'<path class="logo-ink" d="{path}"/>'
        f'<path class="logo-brass-line" d="{path}" transform="translate({cx} {cy}) scale(0.86) translate({-cx} {-cy})"/>'
        f'<text class="logo-hole logo-c" x="{cx}" y="{cy + s * 0.06}" font-size="{s * 0.62:.1f}" '
        'text-anchor="middle" dominant-baseline="central">c</text>'
    )


def seal(cx: float, cy: float, r: float) -> str:
    """A wax seal: an uneven edge, a ring, the c pressed in."""
    points = []
    for i in range(28):
        angle = 2 * math.pi * i / 28
        rr = r * (1.0 if i % 2 == 0 else 0.93) * (1.03 if i % 7 == 0 else 1.0)
        points.append(f"{cx + rr * math.cos(angle):.1f},{cy + rr * math.sin(angle):.1f}")
    return (
        f'<polygon class="logo-seal" points="{" ".join(points)}"/>'
        f'<circle class="logo-seal-ring" cx="{cx}" cy="{cy}" r="{r * 0.74:.1f}"/>'
        f'<text class="logo-c on-seal" x="{cx}" y="{cy + r * 0.08:.1f}" font-size="{r * 1.25:.1f}" '
        'text-anchor="middle" dominant-baseline="central">c</text>'
    )


def plan(x: float, y: float, s: float) -> str:
    """The nine rooms as a 3 x 3 engraved plan, the c in the cellar."""
    gap = s * 0.06
    cell = (s - 2 * gap) / 3
    out = []
    for row in range(3):
        for col in range(3):
            rx, ry = x + col * (cell + gap), y + row * (cell + gap)
            cls = "logo-room cellar" if (row, col) == (1, 1) else "logo-room"
            out.append(f'<rect class="{cls}" x="{rx:.1f}" y="{ry:.1f}" width="{cell:.1f}" height="{cell:.1f}"/>')
    # Doors: a brass tick where each outer room meets the corridor gap.
    for row, col, side in ((0, 0, "b"), (0, 1, "b"), (0, 2, "l"), (1, 0, "r"), (1, 2, "l"), (2, 0, "t"), (2, 1, "t"), (2, 2, "l")):
        rx, ry = x + col * (cell + gap), y + row * (cell + gap)
        if side == "b":
            d = f"M{rx + cell * 0.35:.1f} {ry + cell:.1f} h{cell * 0.3:.1f}"
        elif side == "t":
            d = f"M{rx + cell * 0.35:.1f} {ry:.1f} h{cell * 0.3:.1f}"
        elif side == "l":
            d = f"M{rx:.1f} {ry + cell * 0.35:.1f} v{cell * 0.3:.1f}"
        else:
            d = f"M{rx + cell:.1f} {ry + cell * 0.35:.1f} v{cell * 0.3:.1f}"
        out.append(f'<path class="logo-door" d="{d}"/>')
    cx, cy = x + s / 2, y + s / 2
    out.append(
        f'<text class="logo-c" x="{cx:.1f}" y="{cy + cell * 0.05:.1f}" font-size="{cell * 0.78:.1f}" '
        'text-anchor="middle" dominant-baseline="central">c</text>'
    )
    return "".join(out)


def roundel(cx: float, cy: float, r: float) -> str:
    """A hatched roundel with the c cut out of it."""
    return (
        f'<circle class="logo-hatched" cx="{cx}" cy="{cy}" r="{r}"/>'
        f'<circle class="logo-ink-line" cx="{cx}" cy="{cy}" r="{r}"/>'
        f'<circle class="logo-brass-line" cx="{cx}" cy="{cy}" r="{r * 0.84:.1f}"/>'
        f'<text class="logo-hole logo-c" x="{cx}" y="{cy + r * 0.08:.1f}" font-size="{r * 1.3:.1f}" '
        'text-anchor="middle" dominant-baseline="central">c</text>'
    )


def wordmark(cx: float, cy: float, size: float, accent: bool = False) -> str:
    cls = "logo-word accent" if accent else "logo-word"
    return (
        f'<text class="{cls}" x="{cx}" y="{cy}" font-size="{size:.1f}" '
        'text-anchor="middle" dominant-baseline="central">clude</text>'
    )


def logo_group(kind: str, w: float = 120, h: float = 168) -> str:
    """Candidate `kind` (A-D) drawn to fill a w x h box: the cellar."""
    cx = w / 2
    if kind == "A":
        # The plate wordmark, the keyhole-c above it.
        pw, ph = w * 0.86, h * 0.24
        px, py = cx - pw / 2, h * 0.56
        return (
            keyhole(cx, h * 0.28, h * 0.3)
            + f'<rect class="logo-plate" x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" height="{ph:.1f}"/>'
            + f'<rect class="logo-plate-ink" x="{px + 3:.1f}" y="{py + 3:.1f}" width="{pw - 6:.1f}" height="{ph - 6:.1f}"/>'
            + _rivets(px, py, pw, ph)
            + wordmark(cx, py + ph / 2 + 1, h * 0.115)
        )
    if kind == "B":
        return seal(cx, h * 0.33, w * 0.31) + wordmark(cx, h * 0.76, h * 0.12)
    if kind == "C":
        s = w * 0.7
        return plan(cx - s / 2, h * 0.12, s) + wordmark(cx, h * 0.8, h * 0.105)
    if kind == "D":
        ry = h * 0.15
        rx = w * 0.46
        cy = h * 0.68
        return (
            roundel(cx, h * 0.24, w * 0.19)
            + f'<ellipse class="logo-plate" cx="{cx}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}"/>'
            + f'<ellipse class="logo-plate-ink" cx="{cx}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}"/>'
            + f'<ellipse class="logo-brass-line" cx="{cx}" cy="{cy:.1f}" rx="{rx - 3:.1f}" ry="{ry - 3:.1f}"/>'
            + wordmark(cx, cy + 1, h * 0.1)
        )
    raise ValueError(kind)


def mark_group(kind: str, s: float = 40) -> str:
    """Candidate `kind`'s mark alone, filling an s x s box: the header
    bar and the favicon."""
    c = s / 2
    if kind == "A":
        return keyhole(c, c, s * 0.92)
    if kind == "B":
        return seal(c, c, s * 0.46)
    if kind == "C":
        return plan(s * 0.05, s * 0.05, s * 0.9)
    if kind == "D":
        return roundel(c, c, s * 0.46)
    raise ValueError(kind)


def logo_svg(kind: str, w: float, h: float, px: float, mark_only: bool = False) -> str:
    """One candidate as a standalone inline SVG `px` pixels wide."""
    if mark_only:
        inner, vw, vh = mark_group(kind, 40), 40, 40
    else:
        inner, vw, vh = logo_group(kind, w, h), w, h
    return (
        f'<svg class="logo" viewBox="0 0 {vw} {vh}" width="{px:.0f}" height="{px * vh / vw:.0f}" '
        f'xmlns="http://www.w3.org/2000/svg">{PATTERN_DEFS}{inner}</svg>'
    )


NAMES = {"A": "Plate", "B": "Seal", "C": "Plan", "D": "Cartouche"}
