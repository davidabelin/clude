"""Cartoon busts of the six suspects, for Wikiclude.

Each is uncoloured SVG like every other figure: shapes carry classes and
``clude_web/static/styles/wiki.css`` paints them. The clothes take the
suspect's own colour (``s-<suspect>``, from the look's tokens), so a bust
matches its token in every look; skin, hair and props use the ``pt-*``
classes, which keep one palette in light and dark alike, the way a
printed caricature would. One head-and-shoulders frame is shared; each
character adds hair, face and props over it.

The motifs, from the classic cast: Scarlett's bob, red lips and
cigarette holder; Mustard's handlebar moustache, monocle and medals;
White's cap and apron; Green's slick parting, bow tie and sly grin;
Peacock's pearls and feathered fascinator; Plum's spectacles,
mortarboard and goatee.
"""
from __future__ import annotations

VIEW = (200, 220)
"""Every bust's viewBox, width by height."""

OUTLINE = "pt-o"
"""The class that gives a shape the cartoon's dark outline."""


def _shape(tag: str, cls: str, **attrs) -> str:
    body = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<{tag} {body} class="{cls}"/>'


def _path(d: str, cls: str) -> str:
    return _shape("path", cls, d=d)


def _ellipse(cx, cy, rx, ry, cls: str) -> str:
    return _shape("ellipse", cls, cx=cx, cy=cy, rx=rx, ry=ry)


def _circle(cx, cy, r, cls: str) -> str:
    return _shape("circle", cls, cx=cx, cy=cy, r=r)


# --- the shared frame --------------------------------------------------------

TORSO = "M16 220 C20 180 56 160 100 158 C144 160 180 180 184 220 Z"
NECK = "M86 126 L86 160 Q100 166 114 160 L114 126 Z"


def _head(skin: str = "pt-skin") -> str:
    """Ears, then the face's oval."""
    return (
        _ellipse(62, 98, 7, 11, f"{skin} {OUTLINE}")
        + _ellipse(138, 98, 7, 11, f"{skin} {OUTLINE}")
        + _ellipse(100, 92, 38, 46, f"{skin} {OUTLINE}")
    )


def _neck() -> str:
    return _path(NECK, f"pt-skin {OUTLINE}") + _path("M88 140 Q100 146 112 140", "pt-shade-line")


def _eyes(y: float = 90, gap: float = 15, rx: float = 3.4, ry: float = 4.2) -> str:
    return _ellipse(100 - gap, y, rx, ry, "pt-ink") + _ellipse(100 + gap, y, rx, ry, "pt-ink")


def _lids(y: float = 88, gap: float = 15, w: float = 8) -> str:
    """Half-closed upper lids: the knowing look."""
    out = ""
    for x in (100 - gap, 100 + gap):
        out += _path(f"M{x - w} {y} Q{x} {y - 5} {x + w} {y} Z", "pt-skin-lid")
        out += _path(f"M{x - w} {y} Q{x} {y - 5} {x + w} {y}", "pt-stroke")
    return out


def _nose(d: str = "M100 94 Q95 108 102 110") -> str:
    return _path(d, "pt-stroke")


def _cheeks(y: float = 106) -> str:
    return _ellipse(78, y, 7, 4.5, "pt-cheek") + _ellipse(122, y, 7, 4.5, "pt-cheek")


# --- the six -----------------------------------------------------------------


def _scarlett() -> str:
    back_hair = _path(
        "M58 96 C52 52 78 34 102 34 C130 34 152 54 144 98 C144 116 140 128 130 132 "
        "L128 104 L72 104 L70 132 C60 128 58 114 58 96 Z",
        f"pt-hair-black {OUTLINE}",
    )
    shoulders = _path(TORSO, f"pt-skin {OUTLINE}")
    dress = _path(
        "M22 220 C28 196 48 186 68 190 C84 200 116 200 132 190 C152 186 172 196 178 220 Z",
        f"s-scarlett {OUTLINE}",
    )
    boa = "".join(
        _circle(x, y, 7, f"s-scarlett pt-boa {OUTLINE}")
        for x, y in ((28, 202), (38, 194), (49, 189), (60, 187), (71, 189), (129, 189), (140, 187), (151, 189), (162, 194), (172, 202))
    )
    fringe = _path(
        "M60 86 C60 54 84 40 104 42 C128 44 144 60 140 86 C130 72 118 68 108 76 "
        "C100 62 80 62 70 76 C66 80 62 84 60 86 Z",
        f"pt-hair-black {OUTLINE}",
    )
    shine = _path("M78 58 Q96 48 116 52", "pt-shine")
    face = (
        _eyes(92, 15, 3.2, 4)
        + _lids(90, 15, 8)
        + "".join(_path(f"M{x} 86 l{d} -5", "pt-thin") for x, d in ((80, -3), (84, -1), (116, 1), (120, 3)))
        + _path("M74 80 Q84 74 93 79", "pt-stroke")
        + _path("M107 79 Q116 74 126 80", "pt-stroke")
        + _nose("M100 96 Q97 106 102 107")
        + _path("M89 117 Q94 111 100 114 Q106 111 111 117 Q100 125 89 117 Z", f"pt-lip {OUTLINE}")
        + _circle(118, 110, 1.6, "pt-ink")
        + _cheeks(106)
        + _circle(63, 112, 3.2, f"pt-gold {OUTLINE}")
    )
    holder = (
        _path("M108 119 L178 100", "pt-holder")
        + _path("M170 102 L184 98", "pt-cigarette")
        + _circle(185, 97.6, 2.2, "pt-ember")
        + _path("M186 92 C180 82 192 76 186 66 C180 56 192 50 188 40", "pt-smoke")
    )
    return back_hair + shoulders + dress + boa + _neck() + _head() + fringe + shine + face + holder


def _mustard() -> str:
    tunic = _path(TORSO, f"s-mustard {OUTLINE}")
    collar = _path("M80 156 L80 170 Q100 178 120 170 L120 156 Q100 162 80 156 Z", f"pt-dark {OUTLINE}")
    epaulettes = (
        _ellipse(40, 180, 20, 8, f"pt-gold {OUTLINE}")
        + _ellipse(160, 180, 20, 8, f"pt-gold {OUTLINE}")
        + "".join(_path(f"M{x} 187 l0 9", "pt-thin") for x in (28, 34, 40, 46, 52, 148, 154, 160, 166, 172))
    )
    buttons = "".join(_circle(100, y, 3.2, f"pt-gold {OUTLINE}") for y in (184, 198, 212))
    medals = ""
    for i, (x, ribbon) in enumerate(((60, "pt-ribbon-a"), (72, "pt-ribbon-b"), (84, "pt-ribbon-a"))):
        medals += _shape("rect", f"{ribbon} {OUTLINE}", x=x - 4, y=184, width=8, height=11, rx=1)
        medals += _circle(x, 201, 4.6, f"pt-gold {OUTLINE}")
    side_hair = (
        _path("M60 86 C52 92 54 108 62 110 C60 100 62 92 66 88 Z", f"pt-hair-grey {OUTLINE}")
        + _path("M140 86 C148 92 146 108 138 110 C140 100 138 92 134 88 Z", f"pt-hair-grey {OUTLINE}")
    )
    shine = _ellipse(88, 58, 10, 5, "pt-glint")
    face = (
        _path("M72 80 Q84 70 94 78 L92 82 Q84 78 74 84 Z", f"pt-hair-silver {OUTLINE}")
        + _path("M106 78 Q116 70 128 80 L126 84 Q116 78 108 82 Z", f"pt-hair-silver {OUTLINE}")
        + _eyes(91, 15, 3, 3.4)
        + _ellipse(100, 104, 9, 8, f"pt-skin pt-nose {OUTLINE}")
        + _cheeks(108)
        + _path(
            "M100 112 C92 108 82 110 74 116 C66 120 60 116 62 108 C64 116 70 116 76 112 "
            "C84 104 94 106 100 110 C106 106 116 104 124 112 C130 116 136 116 138 108 "
            "C140 116 134 120 126 116 C118 110 108 108 100 112 Z",
            f"pt-hair-silver {OUTLINE}",
        )
        + _path("M92 124 Q100 121 108 124", "pt-stroke")
    )
    monocle = _circle(115, 91, 9, f"pt-glass {OUTLINE}") + _path("M124 94 C134 118 128 150 112 182", "pt-chain")
    return tunic + collar + epaulettes + buttons + medals + _neck() + _head() + side_hair + shine + face + monocle


def _white() -> str:
    bun = _circle(100, 46, 16, f"pt-hair-grey {OUTLINE}")
    dress = _path(TORSO, f"pt-dark {OUTLINE}")
    apron = (
        _path("M66 220 L72 178 Q100 184 128 178 L134 220 Z", f"s-white {OUTLINE}")
        + _path("M72 178 L56 166", "pt-strap")
        + _path("M128 178 L144 166", "pt-strap")
        + _path("M84 158 L100 172 L116 158 L118 166 L100 178 L82 166 Z", f"s-white {OUTLINE}")
    )
    hair = _path(
        "M62 92 C58 62 78 46 100 46 C122 46 142 62 138 92 C130 76 116 70 100 74 C84 70 70 76 62 92 Z",
        f"pt-hair-grey {OUTLINE}",
    )
    cap = (
        _path("M66 66 C70 40 130 40 134 66 C120 58 80 58 66 66 Z", f"s-white {OUTLINE}")
        + "".join(_circle(x, 64 - 0.0035 * (x - 100) ** 2 * -1, 4.4, f"s-white {OUTLINE}") for x in range(68, 136, 8))
    )
    face = (
        _path("M76 82 Q85 79 93 83", "pt-stroke")
        + _path("M107 83 Q115 79 124 82", "pt-stroke")
        + _eyes(91, 15, 3, 3.6)
        + _path("M78 97 Q85 100 92 97", "pt-thin")
        + _path("M108 97 Q115 100 122 97", "pt-thin")
        + _nose("M100 95 Q96 106 102 108")
        + _cheeks(108)
        + _path("M90 118 Q100 124 110 118", "pt-stroke")
        + _path("M84 124 Q86 128 90 129", "pt-thin")
        + _path("M116 124 Q114 128 110 129", "pt-thin")
    )
    return bun + dress + apron + _neck() + _head() + hair + cap + face


def _green() -> str:
    jacket = _path(TORSO, f"s-green {OUTLINE}")
    shirt = _path("M82 158 L100 210 L118 158 Q100 166 82 158 Z", f"pt-cloth {OUTLINE}")
    lapels = _path("M82 158 L72 182 L92 196 L100 210 Z", f"s-green {OUTLINE}") + _path(
        "M118 158 L128 182 L108 196 L100 210 Z", f"s-green {OUTLINE}"
    )
    bow = _path("M100 168 L86 160 L86 176 Z", f"pt-dark {OUTLINE}") + _path(
        "M100 168 L114 160 L114 176 Z", f"pt-dark {OUTLINE}"
    ) + _circle(100, 168, 3.5, f"pt-dark {OUTLINE}")
    pocket = _path("M140 192 L146 184 L150 192 L156 186 L158 194 Z", f"pt-cloth {OUTLINE}")
    hair = _path(
        "M60 92 C54 58 76 40 102 40 C128 40 146 56 140 92 C138 74 130 64 112 62 "
        "C96 60 82 66 78 66 C74 72 66 80 60 92 Z",
        f"pt-hair-brown {OUTLINE}",
    )
    part = _path("M86 46 Q82 56 78 66", "pt-stroke") + _path("M96 52 Q118 50 134 66", "pt-shine")
    face = (
        _path("M74 84 Q84 80 93 84", "pt-stroke")
        + _path("M107 80 Q117 70 127 76", "pt-stroke")
        + _eyes(92, 15, 3.2, 3.6)
        + _lids(90, 15, 7)
        + _nose("M100 95 Q95 106 101 108")
        + _path("M84 114 Q96 112 108 112 Q116 112 120 106", f"pt-stroke")
        + _path("M88 116 Q100 124 114 114", "pt-thin")
        + _path("M88 110 Q100 106 112 110", "pt-hair-brown-line")
    )
    return jacket + shirt + lapels + bow + pocket + _neck() + _head() + hair + part + face


def _peacock() -> str:
    updo = _ellipse(100, 44, 32, 20, f"pt-hair-auburn {OUTLINE}")
    dress = _path(TORSO, f"s-peacock {OUTLINE}")
    neckline = _path("M76 162 Q100 186 124 162", "pt-stroke")
    pearls = "".join(
        _circle(100 + 26 * c, 160 + 18 * s, 3.6, f"pt-pearl {OUTLINE}")
        for c, s in ((-0.98, 0.0), (-0.9, 0.35), (-0.75, 0.62), (-0.5, 0.84), (-0.2, 0.97), (0.1, 0.99),
                     (0.4, 0.9), (0.66, 0.72), (0.86, 0.48), (0.97, 0.2))
    )
    hair = _path(
        "M60 96 C54 60 76 44 100 44 C124 44 146 60 140 96 C134 76 120 66 100 68 C80 66 66 76 60 96 Z",
        f"pt-hair-auburn {OUTLINE}",
    )
    hat = (
        _ellipse(126, 54, 18, 8, f"s-peacock {OUTLINE}")
        + _path("M128 50 C140 26 154 14 172 6", "pt-quill")
        + _path("M150 24 C158 12 172 8 178 4 C176 14 166 24 150 24 Z", f"s-peacock {OUTLINE}")
        + _ellipse(170, 10, 5, 4, f"pt-gold {OUTLINE}")
        + _ellipse(170, 10, 2, 1.8, "pt-ink")
    )
    face = (
        _path("M72 80 Q83 72 94 79", "pt-stroke")
        + _path("M106 79 Q117 72 128 80", "pt-stroke")
        + _eyes(93, 15, 3, 3)
        + _lids(92, 15, 8.5)
        + _nose("M100 96 Q97 107 103 108")
        + _path("M92 120 Q100 116 108 120 Q100 123 92 120 Z", f"pt-lip {OUTLINE}")
        + _cheeks(108)
        + _circle(63, 112, 3, f"pt-pearl {OUTLINE}")
        + _circle(137, 112, 3, f"pt-pearl {OUTLINE}")
    )
    return updo + dress + neckline + pearls + _neck() + _head() + hair + hat + face


def _plum() -> str:
    jacket = _path(TORSO, f"s-plum {OUTLINE}")
    shirt = _path("M84 158 L100 196 L116 158 Q100 166 84 158 Z", f"pt-cloth {OUTLINE}")
    lapels = _path("M84 158 L74 184 L92 192 L100 196 Z", f"s-plum {OUTLINE}") + _path(
        "M116 158 L126 184 L108 192 L100 196 Z", f"s-plum {OUTLINE}"
    )
    bow = _path("M100 168 L87 161 L87 175 Z", f"pt-gold {OUTLINE}") + _path(
        "M100 168 L113 161 L113 175 Z", f"pt-gold {OUTLINE}"
    ) + _circle(100, 168, 3.2, f"pt-gold {OUTLINE}")
    sides = _path("M60 80 C54 90 56 108 64 112 L66 86 Z", f"pt-hair-black {OUTLINE}") + _path(
        "M140 80 C146 90 144 108 136 112 L134 86 Z", f"pt-hair-black {OUTLINE}"
    )
    board = (
        _path("M64 62 Q100 54 136 62 L134 72 Q100 64 66 72 Z", f"pt-dark {OUTLINE}")
        + _path("M100 32 L160 50 L100 66 L40 50 Z", f"pt-dark {OUTLINE}")
        + _circle(100, 49, 3, "pt-gold")
        + _path("M100 49 L146 56 L148 84", "pt-tassel")
        + _path("M144 84 L148 98 L152 84 Z", f"pt-gold {OUTLINE}")
    )
    face = (
        _path("M72 80 Q83 76 93 81", "pt-stroke")
        + _path("M107 78 Q118 68 128 76", "pt-stroke")
        + _eyes(92, 15, 2.8, 3.2)
        + _circle(85, 92, 10, f"pt-glass {OUTLINE}")
        + _circle(115, 92, 10, f"pt-glass {OUTLINE}")
        + _path("M95 92 Q100 88 105 92", "pt-stroke")
        + _path("M75 90 L63 92", "pt-stroke")
        + _path("M125 90 L137 92", "pt-stroke")
        + _nose("M100 98 Q96 108 102 110")
        + _path("M90 118 Q100 120 112 115", "pt-stroke")
        + _path("M93 133 Q100 154 107 133 Q100 137 93 133 Z", f"pt-hair-black {OUTLINE}")
        + _path("M88 114 Q100 110 112 114", "pt-hair-black-line")
    )
    return jacket + shirt + lapels + bow + _neck() + _head() + sides + board + face


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
    "pt-o", "pt-skin", "pt-skin-lid", "pt-shade-line", "pt-ink", "pt-stroke", "pt-thin", "pt-cheek",
    "pt-shine", "pt-glint", "pt-nose", "pt-lip", "pt-hair-black", "pt-hair-brown", "pt-hair-grey",
    "pt-hair-auburn", "pt-hair-silver", "pt-hair-brown-line", "pt-hair-black-line", "pt-cloth", "pt-dark", "pt-gold",
    "pt-pearl", "pt-glass", "pt-chain", "pt-strap", "pt-holder", "pt-cigarette", "pt-ember", "pt-smoke",
    "pt-ribbon-a", "pt-ribbon-b", "pt-quill", "pt-tassel", "pt-boa",
)
"""The portraits' own classes; each has a rule in wiki.css."""


def body(suspect: str) -> str:
    """One suspect's bust, the SVG body inside a ``0 0 200 220`` viewBox."""
    return DRAW[suspect]()
