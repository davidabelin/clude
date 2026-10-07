"""Engraved busts of the six suspects, for Wikiclude.

Each is drawn like a plate from a Victorian periodical gone to brass and
steam: a parchment plate, a vignette of ruled lines behind the sitter,
shading laid in as parallel and crossed hatching, muted inks, and props
of brass, leather and glass. The faces are drawn to look back at the
reader with suspicion: narrowed lids, sidelong eyes, brows drawn down.

Like every other figure it is uncoloured SVG: shapes carry ``pt-*``
classes and ``clude_web/static/styles/wiki.css`` paints them, in one
palette for every look, as a printed plate would be. The hatching is
computed here (`_hatch` clips ruled lines to a shape), so the SVG needs
no patterns, clip paths or ids.

The motifs, from the classic cast: Scarlett's bob, goggles, choker and
cigarette holder; Mustard's handlebar moustache, mechanical monocle and
cog medals; White's mob cap, apron and ring of keys; Green's top hat with
goggles and his watch chain; Peacock's piled hair, peacock-feather
fascinator, high collar and cameo; Plum's mortarboard, hinged spectacles
and goatee.
"""
from __future__ import annotations

import math

VIEW = (200, 220)
"""Every bust's viewBox, width by height."""

OUTLINE = "pt-o"
"""The class that gives a shape the engraver's outline."""


# --- the engraver's tools ----------------------------------------------------


def _n(v: float) -> str:
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def _curve(points, closed: bool) -> list:
    """A Catmull-Rom spline through the points, as cubic Bezier segments
    ``(p1, c1, c2, p2)``. A point given twice makes a corner."""
    n = len(points)
    segments = []
    for i in range(n if closed else n - 1):
        p0 = points[(i - 1) % n] if (closed or i > 0) else points[i]
        p1, p2 = points[i], points[(i + 1) % n]
        p3 = points[(i + 2) % n] if (closed or i + 2 < n) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        segments.append((p1, c1, c2, p2))
    return segments


def _d(points, closed: bool = True, smooth: bool = True) -> str:
    if not smooth:
        return "M" + " L".join(f"{_n(x)} {_n(y)}" for x, y in points) + (" Z" if closed else "")
    d = f"M{_n(points[0][0])} {_n(points[0][1])}"
    for _, c1, c2, p2 in _curve(points, closed):
        d += f" C{_n(c1[0])} {_n(c1[1])} {_n(c2[0])} {_n(c2[1])} {_n(p2[0])} {_n(p2[1])}"
    return d + (" Z" if closed else "")


def _outline(points, smooth: bool = True, steps: int = 8) -> list:
    """The closed shape as a dense polygon, for hatching."""
    if not smooth:
        return list(points)
    out = []
    for p1, c1, c2, p2 in _curve(points, True):
        for k in range(steps):
            t = k / steps
            u = 1 - t
            out.append(tuple(
                u ** 3 * p1[i] + 3 * u * u * t * c1[i] + 3 * u * t * t * c2[i] + t ** 3 * p2[i] for i in (0, 1)
            ))
    return out


def _hatch(points, angle: float, gap: float, cls: str = "pt-hatch", smooth: bool = True) -> str:
    """Ruled lines at `angle` degrees, `gap` apart, clipped to the shape:
    the engraver's shading, one path per patch."""
    poly = _outline(points, smooth)
    a = math.radians(angle)
    dx, dy = math.cos(a), math.sin(a)
    nx, ny = -dy, dx
    proj = [x * nx + y * ny for x, y in poly]
    t, top, m = min(proj) + gap / 2, max(proj), len(poly)
    parts = []
    while t < top:
        cuts = []
        for i in range(m):
            s1, s2 = proj[i] - t, proj[(i + 1) % m] - t
            if (s1 < 0) != (s2 < 0):
                (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % m]
                f = s1 / (s1 - s2)
                cuts.append((x1 + (x2 - x1) * f) * dx + (y1 + (y2 - y1) * f) * dy)
        cuts.sort()
        for u0, u1 in zip(cuts[::2], cuts[1::2]):
            if u1 - u0 > 0.8:
                parts.append(
                    f"M{_n(t * nx + u0 * dx)} {_n(t * ny + u0 * dy)}L{_n(t * nx + u1 * dx)} {_n(t * ny + u1 * dy)}"
                )
        t += gap
    return f'<path d="{"".join(parts)}" class="{cls}"/>' if parts else ""


def _cross(points, angle: float, gap: float, cls: str = "pt-hatch", smooth: bool = True) -> str:
    """Crossed hatching: the deeper shadows."""
    return _hatch(points, angle, gap, cls, smooth) + _hatch(points, angle + 70, gap * 1.2, cls, smooth)


def _fill(points, cls: str, smooth: bool = True) -> str:
    return f'<path d="{_d(points, True, smooth)}" class="{cls}"/>'


def _line(points, cls: str = "pt-line", smooth: bool = True) -> str:
    return f'<path d="{_d(points, False, smooth)}" class="{cls}"/>'


def _circle(cx, cy, r, cls: str) -> str:
    return f'<circle cx="{_n(cx)}" cy="{_n(cy)}" r="{_n(r)}" class="{cls}"/>'


def _ellipse(cx, cy, rx, ry, cls: str) -> str:
    return f'<ellipse cx="{_n(cx)}" cy="{_n(cy)}" rx="{_n(rx)}" ry="{_n(ry)}" class="{cls}"/>'


def _mirror(points) -> list:
    return [(200 - x, y) for x, y in points]


def _both(points, draw) -> str:
    """Draw a left-hand shape and its mirror image."""
    return draw(points) + draw(_mirror(points))


def _gear(cx, cy, r, teeth: int = 8, cls: str = "pt-brass") -> str:
    """A brass cog with a dark hub."""
    pts = []
    for k in range(teeth * 4):
        a = 2 * math.pi * (k + 0.5) / (teeth * 4)
        rr = r if k % 4 in (0, 1) else r * 0.76
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return _fill(pts, f"{cls} {OUTLINE}", smooth=False) + _circle(cx, cy, r * 0.32, f"pt-dark {OUTLINE}")


def _lens(cx, cy, r, tint: str = "pt-glass", rivets: int = 8) -> str:
    """A goggle or spectacle lens in a riveted brass rim, with a glint."""
    out = (
        _circle(cx, cy, r, f"{tint} pt-o-thin")
        + _circle(cx, cy, r + 1.4, "pt-brass-rim")
        + _circle(cx, cy, r + 2.8, "pt-rim-edge")
    )
    for k in range(rivets):
        a = 2 * math.pi * k / rivets
        out += _circle(cx + (r + 1.4) * math.cos(a), cy + (r + 1.4) * math.sin(a), 0.7, "pt-ink")
    a0, a1 = math.radians(200), math.radians(250)
    rr = r * 0.62
    out += _line(
        [(cx + rr * math.cos(a), cy + rr * math.sin(a)) for a in (a0, (a0 + a1) / 2, a1)], "pt-glint-line"
    )
    return out


# --- the plate ---------------------------------------------------------------


def _plate() -> str:
    """Parchment, and a vignette of ruled lines behind the sitter."""
    oval = [(100 + 84 * math.cos(a / 24 * math.pi), 102 + 94 * math.sin(a / 24 * math.pi)) for a in range(48)]
    return (
        f'<rect x="3" y="3" width="194" height="214" class="pt-plate"/>'
        + _hatch(oval, 0, 3.0, "pt-rule", smooth=False)
    )


def _border() -> str:
    """A parchment mat over anything drawn past the inner rule, then the
    plate's two rules."""
    return (
        '<path d="M0 0H200V220H0Z M7 7V213H193V7Z" class="pt-mat"/>'
        '<rect x="3" y="3" width="194" height="214" class="pt-frame"/>'
        '<rect x="7" y="7" width="186" height="206" class="pt-frame-thin"/>'
    )


# --- the head ----------------------------------------------------------------

FACE = [
    (100, 46), (121, 50), (134, 64), (137, 86), (133, 108), (122, 127), (108, 139), (100, 141),
    (92, 139), (78, 127), (67, 108), (63, 86), (66, 64), (79, 50),
]
EAR = [(66, 82), (58, 78), (53, 89), (56, 101), (66, 106)]
NECK = [(86, 120), (86, 164), (114, 164), (114, 120)]


def _scale(points, sx: float = 1.0, sy: float = 1.0, cy: float = 92) -> list:
    return [(100 + (x - 100) * sx, cy + (y - cy) * sy) for x, y in points]


def _neck() -> str:
    return (
        _fill(NECK, f"pt-skin {OUTLINE}", smooth=False)
        + _cross([(86, 124), (114, 124), (114, 158), (100, 150), (86, 146)], 60, 2.4, smooth=False)
    )


def _head(sx: float = 1.0, sy: float = 1.0) -> str:
    """Ears, the face and its shading: light from the upper left, so the
    sitter's left cheek, the jaw's underside and the eye sockets fall in
    shadow, and a gaunt hollow under each cheekbone."""
    face = _scale(FACE, sx, sy)
    ears = _both(_scale(EAR, sx, sy), lambda p: _fill(p, f"pt-skin {OUTLINE}"))
    shade = _scale(
        [(118, 49), (132, 62), (137, 86), (133, 108), (122, 127), (108, 139), (100, 141),
         (110, 127), (120, 107), (125, 86), (123, 66)],
        sx, sy,
    )
    hollows = _scale([(68, 104), (76, 109), (84, 124), (75, 120)], sx, sy)
    return (
        ears
        + _hatch(_scale([(137, 84), (146, 86), (145, 101), (138, 104)], sx, sy), 70, 2.2)
        + _fill(face, f"pt-skin {OUTLINE}")
        + _hatch(face, 100, 3.2, "pt-hatch-soft")
        + _hatch(shade, 65, 2.2)
        + _hatch(_scale([(121, 106), (131, 104), (126, 120), (116, 124)], sx, sy), -25, 2.4)
        + _hatch(hollows, 35, 2.4)
        + _hatch(_scale([(86, 135), (114, 135), (100, 141)], sx, sy), 20, 1.8, smooth=False)
    )


def _eye(cx: float, y: float, h: float, gx: float, gy: float = 0.0) -> str:
    """A narrowed eye: the white, an iris glancing `gx` sideways, the
    heavy upper lid drawn over it, the lower lid and a tired bag."""
    white = [(cx - 9, y + 0.5), (cx - 3, y - h), (cx + 4, y - h + 0.4), (cx + 9, y), (cx + 3, y + h * 0.7),
             (cx - 4, y + h * 0.65)]
    r = min(3.1, h + 0.6)
    lid = [(cx - 10.5, y + 1), (cx - 3, y - h - 0.2), (cx + 4, y - h + 0.2), (cx + 10.5, y + 0.6),
           (cx + 11, y - 9), (cx - 11, y - 9)]
    return (
        _fill(white, "pt-eye")
        + _circle(cx + gx, y + 0.4 + gy, r, "pt-iris")
        + _circle(cx + gx, y + 0.4 + gy, r * 0.45, "pt-ink")
        + _circle(cx + gx - 1, y - 0.6 + gy, 0.7, "pt-glint")
        + _fill(lid, "pt-skin")
        + _cross([(cx - 10, y - 1), (cx, y - h - 2.5), (cx + 10, y - 1), (cx + 9, y - 7), (cx - 9, y - 7)], -35, 1.7)
        + _hatch([(cx - 7, y + h + 1), (cx + 7, y + h), (cx + 6, y + h + 4.5), (cx - 5, y + h + 5)], 30, 1.4)
        + _line([(cx - 10.5, y + 1), (cx - 3, y - h - 0.2), (cx + 4, y - h + 0.2), (cx + 10.5, y + 0.6)], "pt-lid")
        + _line([(cx - 7, y + h * 0.65 + 0.6), (cx, y + h * 0.95), (cx + 7, y + h * 0.5)], "pt-line-thin")
        + _line([(cx - 6, y + h + 3.4), (cx + 1, y + h + 4.6), (cx + 7, y + h + 2.6)], "pt-line-thin")
    )


def _eyes(y: float = 90, h: float = 2.8, gx: float = 0.0, gy: float = 0.0) -> str:
    return _eye(84, y, h, gx, gy) + _eye(116, y, h, gx, gy)


def _brow(inner: float, peak: float, outer: float, thick: float, cls: str) -> str:
    """The sitter's right brow (the reader's left); `_brows` mirrors it.
    A low `inner` with high ends draws the brows down into a scowl."""
    pts = [(96, inner), (84, peak), (71, outer), (71, outer), (72, outer + thick * 0.55),
           (84, peak + thick), (95, inner + thick * 0.8), (95, inner + thick * 0.8)]
    return _fill(pts, cls)


def _brows(left: tuple, right: tuple = None, cls: str = "pt-brow-black") -> str:
    right = right or left
    return _brow(*left, cls) + _fill(_mirror(_brow_points(*right)), cls)


def _brow_points(inner, peak, outer, thick) -> list:
    return [(96, inner), (84, peak), (71, outer), (71, outer), (72, outer + thick * 0.55),
            (84, peak + thick), (95, inner + thick * 0.8), (95, inner + thick * 0.8)]


def _furrow(y: float = 90) -> str:
    """Two creases between drawn-down brows."""
    return _line([(97, y - 9), (98.4, y - 3)], "pt-line-thin") + _line([(103, y - 9), (101.6, y - 3)], "pt-line-thin")


def _nose(y: float = 90) -> str:
    return (
        _hatch([(101, y + 3), (105, y + 14), (107, y + 20), (102, y + 18)], 70, 1.8)
        + _line([(98, y + 1), (97, y + 12), (94.5, y + 18.5), (97.5, y + 21.5), (102, y + 22), (106, y + 20)])
        + _ellipse(96.5, y + 20, 1.7, 1, "pt-ink")
        + _ellipse(103.5, y + 20, 1.7, 1, "pt-ink")
        + _hatch([(94, y + 23), (106, y + 23), (103, y + 26), (97, y + 26)], 0, 1.4)
    )


def _torso(cls: str) -> str:
    """Shoulders in the sitter's coat, shaded on the far side."""
    body = [(10, 214), (10, 214), (15, 194), (33, 177), (62, 166), (86, 160), (114, 160), (138, 166),
            (167, 177), (185, 194), (190, 214), (190, 214)]
    return (
        _fill(body, f"{cls} {OUTLINE}")
        + _hatch(body, 75, 3.6, "pt-hatch-soft")
        + _hatch([(118, 162), (140, 168), (167, 178), (185, 195), (190, 217), (128, 217), (126, 190)], 60, 2.8)
        + _hatch([(150, 186), (185, 196), (190, 217), (148, 217)], -50, 2.8)
        + _hatch([(12, 205), (24, 186), (30, 190), (22, 217), (12, 217)], 60, 3.2)
    )


# --- the six -----------------------------------------------------------------


def _scarlett() -> str:
    back_hair = [(60, 90), (56, 62), (70, 40), (100, 32), (130, 40), (144, 62), (140, 92), (143, 116),
                 (134, 128), (124, 118), (76, 118), (66, 128), (57, 116)]
    bodice = [(24, 217), (24, 217), (30, 196), (50, 186), (70, 189), (86, 197), (100, 194), (114, 197),
              (130, 189), (150, 186), (170, 196), (176, 217), (176, 217)]
    fringe = [(64, 86), (61, 62), (77, 45), (100, 40), (123, 45), (139, 62), (137, 86), (126, 70),
              (110, 66), (100, 72), (88, 64), (74, 72)]
    lips = [(88, 122), (95, 118.5), (100, 120.5), (105, 118.5), (113, 119), (113, 119), (106, 125.5),
            (100, 126.5), (94, 125.5)]
    smoke = [(188, 96), (183, 86), (191, 76), (185, 64), (192, 52), (186, 40), (190, 30)]
    return (
        _fill(back_hair, f"pt-hair-black {OUTLINE}")
        + _hatch(back_hair, 80, 2.2, "pt-hatch-light")
        + _neck()
        + _fill([(10, 214), (10, 214), (15, 194), (33, 177), (62, 166), (86, 160), (114, 160), (138, 166),
                 (167, 177), (185, 194), (190, 214), (190, 214)], f"pt-skin {OUTLINE}")
        + _hatch([(122, 164), (160, 174), (185, 195), (190, 217), (150, 217)], 60, 2.6)
        + _fill(bodice, f"pt-coat-scarlett {OUTLINE}")
        + _hatch([(108, 198), (130, 190), (150, 187), (170, 197), (176, 217), (112, 217)], 60, 2.4)
        + _hatch([(140, 192), (170, 197), (176, 217), (140, 217)], -45, 2.4)
        + _line([(100, 195), (100, 217)], "pt-brass-line", smooth=False)
        + "".join(_circle(x, y, 1.3, f"pt-brass {OUTLINE}") for x, y in ((94, 202), (106, 202), (94, 211), (106, 211)))
        + _fill([(86, 146), (114, 146), (114, 152), (86, 152)], f"pt-dark {OUTLINE}", smooth=False)
        + _gear(100, 159, 6, 8)
        + _head()
        + _eyes(91, 2.5, -2.4)
        + _brows((86, 76, 79, 2.4), (86, 74, 78, 2.4)) + _furrow(91)
        + _nose(91)
        + _fill(lips, f"pt-lip {OUTLINE}-thin")
        + _hatch(lips, 0, 1.6, "pt-hatch-light")
        + _line([(88, 122), (100, 122.6), (113, 119)], "pt-line")
        + _circle(120, 112, 1.3, "pt-ink")
        + _circle(62, 107, 2.4, f"pt-brass {OUTLINE}") + _ellipse(62, 114, 2, 3.2, f"pt-garnet {OUTLINE}")
        + _fill(fringe, f"pt-hair-black {OUTLINE}")
        + _line([(70, 66), (82, 52), (98, 47)], "pt-glint-line")
        + _line([(108, 50), (124, 52), (133, 64)], "pt-glint-line")
        + _line([(60, 64), (82, 52), (118, 52), (140, 64)], "pt-strap")
        + _lens(84, 50, 8.5, "pt-glass-amber")
        + _lens(116, 50, 8.5, "pt-glass-amber")
        + _line([(110, 124), (176, 104)], "pt-holder", smooth=False)
        + _line([(150, 112), (156, 110)], "pt-brass-band", smooth=False)
        + _line([(176, 104), (187, 100.5)], "pt-cig-edge", smooth=False)
        + _line([(176, 104), (187, 100.5)], "pt-cigarette", smooth=False)
        + _circle(188, 100, 1.8, "pt-ember")
        + _line(smoke, "pt-smoke")
        + _line([(s[0] - 5, s[1] + 2) for s in smoke[2:]], "pt-smoke")
    )


def _mustard() -> str:
    tache = [(100, 112), (92, 109), (82, 110), (74, 112), (68, 109), (65.5, 103), (67.5, 98.5), (69.5, 103.5),
             (73, 107), (81, 105), (91, 104), (100, 107.5), (109, 104), (119, 105), (127, 107), (130.5, 103.5),
             (132.5, 98.5), (134.5, 103), (132, 109), (126, 112), (118, 110), (108, 109)]
    chop = [(64, 80), (61, 94), (65, 104), (71, 103), (70, 93), (69, 82)]
    epaulette = [(26, 182), (40, 172), (62, 172), (64, 180), (44, 188), (28, 190)]
    return (
        _neck()
        + _torso("pt-coat-mustard")
        + _fill([(80, 150), (80, 168), (100, 174), (120, 168), (120, 150), (100, 156)], f"pt-dark {OUTLINE}")
        + _line([(80, 160), (100, 166), (120, 160)], "pt-brass-line")
        + "".join(_circle(x, y, 2.8, f"pt-brass {OUTLINE}") for x in (88, 112) for y in (186, 199, 212))
        + _fill(epaulette, f"pt-brass {OUTLINE}") + _fill(_mirror(epaulette), f"pt-brass {OUTLINE}")
        + "".join(_line([(x, 189 - (x - 28) * 0.05), (x - 1, 198)], "pt-brass-line", smooth=False)
                  for x in (30, 35, 40, 45, 50))
        + "".join(_line([(200 - x, 189 - (x - 28) * 0.05), (201 - x, 198)], "pt-brass-line", smooth=False)
                  for x in (30, 35, 40, 45, 50))
        + _fill([(52, 192), (60, 192), (60, 200), (52, 200)], f"pt-ribbon-a {OUTLINE}", smooth=False)
        + _fill([(63, 192), (71, 192), (71, 200), (63, 200)], f"pt-ribbon-b {OUTLINE}", smooth=False)
        + _gear(56, 207, 5, 7) + _gear(67, 207, 5, 7)
        + _head(1.06, 1.0)
        + _hatch([(72, 52), (100, 44), (128, 52), (122, 60), (100, 54), (78, 60)], 0, 2.6, "pt-hatch-light")
        + _line([(78, 56), (92, 50)], "pt-glint-line")
        + _both(chop, lambda p: _fill(p, f"pt-hair-silver {OUTLINE}") + _hatch(p, 80, 1.8, "pt-hatch-light"))
        + _eyes(91, 2.3, 2.2)
        + _brows((88, 76, 78, 4.2), cls="pt-brow-silver")
        + _line([(94, 80), (97, 86)], "pt-line-thin") + _line([(106, 80), (103, 86)], "pt-line-thin")
        + _nose(91)
        + _fill(_scale(tache, 0.86, 1.0, 106), f"pt-hair-silver {OUTLINE}")
        + _hatch(_scale(tache, 0.86, 1.0, 106), 12, 1.6, "pt-hatch-light")
        + _line([(91, 123), (100, 120), (109, 123)], "pt-line")
        + _lens(116, 91, 9, "pt-glass")
        + _circle(116, 91, 13.5, "pt-brass-ring")
        + _gear(131, 101, 4.5, 7)
        + _line([(127, 98), (138, 122), (130, 150), (114, 176)], "pt-chain")
    )


def _white() -> str:
    cap = [(60, 76), (56, 54), (72, 32), (100, 24), (128, 32), (144, 54), (140, 76), (122, 66), (100, 63),
           (78, 66)]
    frill = [(62 + 6.4 * k, 74 - 9 * math.sin(math.pi * k / 12)) for k in range(13)]
    temples = [(64, 88), (61, 72), (78, 66), (71, 77), (68, 90)]
    key = [(146, 196), (146, 214)]
    return (
        _neck()
        + _torso("pt-dark")
        + _fill([(68, 217), (68, 217), (74, 180), (100, 186), (126, 180), (132, 217), (132, 217)],
                f"pt-coat-white {OUTLINE}")
        + _hatch([(108, 186), (126, 181), (132, 217), (112, 217)], 70, 2.6)
        + _line([(74, 180), (58, 166)], "pt-strap") + _line([(126, 180), (142, 166)], "pt-strap")
        + _fill([(84, 158), (100, 172), (116, 158), (118, 166), (100, 178), (82, 166)], f"pt-coat-white {OUTLINE}",
                smooth=False)
        + _gear(100, 176, 6, 8)
        + _circle(146, 190, 6, "pt-brass-ring")
        + _line(key, "pt-key", smooth=False) + _line([(146, 210), (151, 210), (151, 214)], "pt-key", smooth=False)
        + _line([(141, 194), (136, 210)], "pt-key", smooth=False)
        + _line([(136, 206), (132, 205), (131, 209)], "pt-key", smooth=False)
        + _head(1.0, 1.02)
        + _line([(70, 96), (65, 93)], "pt-line-thin") + _line([(130, 96), (135, 93)], "pt-line-thin")
        + _both(temples, lambda p: _fill(p, f"pt-hair-grey {OUTLINE}") + _hatch(p, 70, 1.8, "pt-hatch-light"))
        + _eyes(91, 2.2, -2.6)
        + _brows((87, 79, 81, 2.4), cls="pt-brow-grey") + _furrow(91)
        + _nose(91)
        + _line([(91, 124), (100, 121), (109, 124)], "pt-line")
        + _line([(97, 120), (96.5, 117.5)], "pt-line-thin") + _line([(103, 120), (103.5, 117.5)], "pt-line-thin")
        + _line([(86, 126), (88, 130), (91, 131)], "pt-line-thin") + _line([(114, 126), (112, 130), (109, 131)], "pt-line-thin")
        + _fill(cap, f"pt-coat-white {OUTLINE}")
        + _hatch([(118, 30), (144, 54), (140, 76), (122, 66), (124, 46)], 65, 2.4)
        + _line([(70, 46), (100, 38), (130, 46)], "pt-line-thin")
        + "".join(_circle(x, y, 4.2, f"pt-coat-white {OUTLINE}") for x, y in frill)
    )


def _green() -> str:
    crown = [(71, 52), (71, 52), (73, 10), (73, 10), (127, 10), (127, 10), (129, 52), (129, 52)]
    brim = [(50, 57), (60, 49), (100, 46), (140, 49), (150, 57), (140, 61), (100, 58), (60, 61)]
    slick = [(62, 60), (60, 84), (66, 94), (67, 74), (78, 62)]
    coat = [(10, 214), (10, 214), (15, 194), (33, 177), (62, 166), (86, 160), (114, 160), (138, 166),
            (167, 177), (185, 194), (190, 214), (190, 214)]
    return (
        _neck()
        + _torso("pt-coat-green")
        + _fill([(82, 158), (100, 217), (118, 158), (100, 166)], f"pt-cloth {OUTLINE}", smooth=False)
        + _fill([(88, 182), (100, 217), (112, 182), (126, 217), (74, 217)], f"pt-waistcoat {OUTLINE}", smooth=False)
        + _hatch([(100, 196), (112, 182), (126, 217), (100, 217)], 60, 2.2, smooth=False)
        + _fill([(82, 158), (70, 184), (90, 198), (100, 217)], f"pt-coat-green {OUTLINE}", smooth=False)
        + _fill([(118, 158), (130, 184), (110, 198), (100, 217)], f"pt-coat-green {OUTLINE}", smooth=False)
        + _hatch([(118, 158), (130, 184), (110, 198), (100, 217)], -60, 2.2, smooth=False)
        + _fill([(91, 160), (109, 160), (104, 176), (100, 182), (96, 176)], f"pt-dark {OUTLINE}", smooth=False)
        + _circle(100, 170, 1.6, "pt-brass")
        + _line([(80, 204), (92, 210), (108, 210), (120, 204)], "pt-chain")
        + _circle(121, 206, 4, f"pt-brass {OUTLINE}")
        + _head()
        + _both(slick, lambda p: _fill(p, f"pt-hair-brown {OUTLINE}") + _hatch(p, 75, 1.7, "pt-hatch-light"))
        + _eyes(91, 2.4, 2.6)
        + _brows((86, 76, 79, 2.6), (81, 71, 75, 2.4), cls="pt-brow-brown") + _furrow(91)
        + _nose(91)
        + _line([(90, 116.5), (95, 115), (100, 115.8), (105, 115), (110, 116.5)], "pt-tache")
        + _line([(88, 123), (98, 123.5), (107, 121.5), (114, 116.5)], "pt-line")
        + _line([(115, 114), (117, 119)], "pt-line-thin")
        + _hatch([(94, 125), (106, 124), (104, 128), (96, 128)], 0, 1.4)
        + _fill(crown, f"pt-dark {OUTLINE}", smooth=False)
        + _hatch([(108, 10), (127, 10), (129, 52), (110, 52)], 80, 2.0, "pt-hatch-light", smooth=False)
        + _line([(84, 14), (84, 46)], "pt-glint-line", smooth=False)
        + _fill([(71, 40), (129, 40), (129, 50), (71, 50)], f"pt-leather {OUTLINE}", smooth=False)
        + _lens(88, 38, 7.5, "pt-glass-green")
        + _lens(112, 38, 7.5, "pt-glass-green")
        + _gear(124, 22, 5.5, 8)
        + _fill(brim, f"pt-dark {OUTLINE}")
    )


def _peacock() -> str:
    hair = [(63, 88), (57, 58), (70, 32), (100, 22), (130, 32), (143, 58), (137, 88), (126, 66), (100, 58),
            (74, 66)]
    bun = [(80, 30), (82, 14), (100, 6), (118, 14), (120, 30)]
    collar = [(82, 128), (118, 128), (122, 166), (78, 166)]
    vane = [(132, 34), (146, 22), (162, 10), (178, 8), (172, 18), (156, 28), (140, 36)]
    return (
        _fill([(10, 214), (10, 214), (12, 190), (26, 168), (50, 158), (78, 160), (122, 160), (150, 158),
               (174, 168), (188, 190), (190, 214), (190, 214)], f"pt-coat-peacock {OUTLINE}")
        + _hatch([(122, 162), (150, 159), (174, 169), (188, 191), (190, 217), (130, 217)], 60, 2.6)
        + _hatch([(156, 180), (188, 191), (190, 217), (156, 217)], -50, 2.6)
        + _hatch([(12, 196), (26, 170), (34, 172), (22, 217), (12, 217)], 60, 3.0)
        + _fill(collar, f"pt-coat-peacock {OUTLINE}", smooth=False)
        + _hatch([(104, 128), (118, 128), (122, 166), (108, 166)], 80, 1.8, smooth=False)
        + "".join(_circle(82 + 4 * k, 128, 2.4, f"pt-pearl {OUTLINE}") for k in range(10))
        + _ellipse(100, 150, 6.5, 8.5, f"pt-brass {OUTLINE}") + _ellipse(100, 150, 4.3, 6, f"pt-pearl {OUTLINE}")
        + _ellipse(100, 150, 1.8, 3, "pt-hair-grey")
        + _head(0.98, 1.0)
        + _eyes(92, 2.0, -1.8, 0.4)
        + _brows((85, 74, 77, 1.9), cls="pt-brow-auburn")
        + _nose(92)
        + _fill([(91, 121), (100, 119.5), (109, 121), (100, 123.5)], f"pt-lip {OUTLINE}-thin")
        + _line([(89, 122.5), (91, 121)], "pt-line-thin") + _line([(111, 122.5), (109, 121)], "pt-line-thin")
        + _both([(62, 108), (62, 116)], lambda p: _line(p, "pt-line-thin", smooth=False))
        + _circle(62, 118, 2.6, f"pt-pearl {OUTLINE}") + _circle(138, 118, 2.6, f"pt-pearl {OUTLINE}")
        + _fill(bun, f"pt-hair-auburn {OUTLINE}") + _hatch(bun, 70, 1.8, "pt-hatch-light")
        + _fill(hair, f"pt-hair-auburn {OUTLINE}")
        + _hatch([(112, 26), (130, 32), (143, 58), (137, 88), (126, 66), (118, 50)], 70, 2.0, "pt-hatch-light")
        + _line([(72, 56), (86, 40), (102, 34)], "pt-glint-line")
        + _line([(66, 74), (74, 56), (90, 46)], "pt-glint-line")
        + _line([(130, 40), (150, 22), (178, 6)], "pt-quill")
        + _fill(vane, f"pt-feather {OUTLINE}-thin")
        + _hatch(vane, 50, 1.6, "pt-hatch-light")
        + _ellipse(172, 11, 5, 4, f"pt-brass {OUTLINE}") + _ellipse(172, 11, 2.6, 2.1, "pt-feather")
        + _circle(172, 11, 1, "pt-ink")
        + _ellipse(128, 40, 14, 6, f"pt-dark {OUTLINE}")
        + _gear(124, 38, 6, 8)
    )


def _plum() -> str:
    board = [(100, 20), (158, 36), (100, 52), (42, 36)]
    cap = [(66, 54), (68, 40), (132, 40), (134, 54), (100, 60)]
    sides = [(62, 70), (59, 96), (66, 108), (67, 82), (72, 66)]
    beard = [(92, 132), (95, 140), (100, 154), (105, 140), (108, 132), (100, 136)]
    return (
        _neck()
        + _torso("pt-coat-plum")
        + _fill([(84, 158), (100, 200), (116, 158), (100, 166)], f"pt-cloth {OUTLINE}", smooth=False)
        + _fill([(84, 158), (72, 186), (92, 194), (100, 200)], f"pt-coat-plum {OUTLINE}", smooth=False)
        + _fill([(116, 158), (128, 186), (108, 194), (100, 200)], f"pt-coat-plum {OUTLINE}", smooth=False)
        + _hatch([(116, 158), (128, 186), (108, 194), (100, 200)], -60, 2.2, smooth=False)
        + _fill([(100, 168), (88, 161), (88, 175)], f"pt-dark {OUTLINE}", smooth=False)
        + _fill([(100, 168), (112, 161), (112, 175)], f"pt-dark {OUTLINE}", smooth=False)
        + _circle(100, 168, 2.8, f"pt-dark {OUTLINE}")
        + _gear(80, 182, 4.5, 7)
        + _fill([(136, 182), (142, 176), (148, 182), (146, 186), (138, 186)], f"pt-cloth {OUTLINE}", smooth=False)
        + _head(0.96, 1.04)
        + _both(sides, lambda p: _fill(p, f"pt-hair-black {OUTLINE}") + _hatch(p, 75, 1.8, "pt-hatch-light"))
        + _eyes(92, 2.2, 2.4)
        + _brows((88, 75, 77, 2.8)) + _furrow(92)
        + _nose(93)
        + _line([(88, 119), (94, 116.5), (100, 117.5), (106, 116.5), (112, 119)], "pt-tache")
        + _line([(90, 124), (100, 124.5), (111, 121)], "pt-line")
        + _fill(beard, f"pt-hair-black {OUTLINE}") + _hatch(beard, 80, 1.6, "pt-hatch-light")
        + _lens(85, 92, 8.5) + _lens(115, 92, 8.5)
        + _line([(94, 91), (100, 88), (106, 91)], "pt-brass-line")
        + _line([(73, 90), (62, 92)], "pt-brass-line", smooth=False)
        + _line([(127, 90), (138, 92)], "pt-brass-line", smooth=False)
        + _line([(122, 84), (127, 77)], "pt-brass-line", smooth=False)
        + _lens(130, 73, 4.5, "pt-glass-amber", rivets=6)
        + _fill(cap, f"pt-dark {OUTLINE}")
        + _fill(board, f"pt-dark {OUTLINE}", smooth=False)
        + _hatch([(100, 20), (158, 36), (100, 52)], 20, 2.0, "pt-hatch-light", smooth=False)
        + _gear(100, 36, 4, 7)
        + _line([(100, 36), (148, 46), (150, 76)], "pt-tassel")
        + _fill([(146, 76), (150, 92), (154, 76)], f"pt-brass {OUTLINE}", smooth=False)
    )


DRAW: dict = {
    "Scarlett": _scarlett,
    "Mustard": _mustard,
    "White": _white,
    "Green": _green,
    "Peacock": _peacock,
    "Plum": _plum,
}
"""Each suspect's bust, as the SVG body inside the shared viewBox."""

CLASSES = (
    "pt-plate", "pt-mat", "pt-rule", "pt-frame", "pt-frame-thin", "pt-o", "pt-o-thin", "pt-hatch",
    "pt-hatch-light", "pt-hatch-soft", "pt-brass-rim", "pt-rim-edge", "pt-cig-edge",
    "pt-line", "pt-line-thin", "pt-lid", "pt-ink", "pt-skin", "pt-eye", "pt-iris", "pt-lip", "pt-glint",
    "pt-glint-line", "pt-brow-black", "pt-brow-silver", "pt-brow-grey", "pt-brow-brown", "pt-brow-auburn",
    "pt-tache", "pt-hair-black", "pt-hair-grey", "pt-hair-silver", "pt-hair-brown", "pt-hair-auburn",
    "pt-coat-scarlett", "pt-coat-mustard", "pt-coat-white", "pt-coat-green", "pt-coat-peacock", "pt-coat-plum",
    "pt-waistcoat", "pt-cloth", "pt-dark", "pt-leather", "pt-brass", "pt-brass-line", "pt-brass-ring",
    "pt-brass-band", "pt-chain", "pt-key", "pt-strap", "pt-glass", "pt-glass-amber", "pt-glass-green",
    "pt-garnet", "pt-pearl", "pt-feather", "pt-quill", "pt-tassel", "pt-ribbon-a", "pt-ribbon-b",
    "pt-holder", "pt-cigarette", "pt-ember", "pt-smoke",
)
"""The portraits' own classes; each has a rule in wiki.css."""


def body(suspect: str) -> str:
    """One suspect's bust, the SVG body inside a ``0 0 200 220`` viewBox:
    the plate, the sitter and the plate's border."""
    return _plate() + DRAW[suspect]() + _border()
