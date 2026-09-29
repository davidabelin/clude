"""The logo, candidate E (D5, David's pick on 2026-09-29): a cartouche
wordmark under an escutcheon plate whose keyway is a question mark.

Drawn as SVG and, like the board, uncoloured: every shape carries a
``logo-*`` class and the look's stylesheet paints it, so the mark takes
the theme like everything else (docs/phase10-plan.md 9). Ported from
the artboards' drawing code (`docs/ux/sketch_parts.py`, `keyhole_q`
and `logo_group("E")`), which stays as the record of the candidates.

Three uses: the cellar in the middle of the board (`cellar`, placed by
`board_svg`), the header bar's mark (`mark_svg`), and the favicon
(`favicon_svg`), which is the one drawing with colours of its own, since
a browser tab has no stylesheet.

Imports nothing from Flask.
"""
from __future__ import annotations


def keyhole(cx: float, cy: float, s: float) -> str:
    """The escutcheon: a round shoulder tapering to a flat foot, a brass
    line inside its edge, and a question mark for the keyway. `s` is its
    height; (`cx`, `cy`) its centre."""
    w, h = s * 0.78, s
    top = cy - h / 2
    r = w / 2
    path = (
        f"M{cx - r:.1f} {top + r:.1f} A{r:.1f} {r:.1f} 0 0 1 {cx + r:.1f} {top + r:.1f} "
        f"L{cx + w * 0.4:.1f} {top + h:.1f} L{cx - w * 0.4:.1f} {top + h:.1f} Z"
    )
    return (
        f'<path class="logo-ink" d="{path}"/>'
        f'<path class="logo-brass-line" d="{path}" '
        f'transform="translate({cx:.1f} {cy:.1f}) scale(0.86) translate({-cx:.1f} {-cy:.1f})"/>'
        f'<text class="logo-hole logo-q" x="{cx:.1f}" y="{cy + s * 0.05:.1f}" font-size="{s * 0.7:.1f}" '
        'text-anchor="middle" dominant-baseline="central">?</text>'
    )


def cellar(w: float, h: float) -> str:
    """The whole logo filling a `w` x `h` box from its top-left corner:
    the keyhole above, the oval cartouche with ``clude`` below. The
    board's cellar is 5 x 7 cells, 120 x 168 units, the box it was drawn
    to in 10a."""
    cx = w / 2
    cy = h * 0.68
    rx, ry = w * 0.46, h * 0.15
    return (
        keyhole(cx, h * 0.26, h * 0.36)
        + f'<ellipse class="logo-plate" cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}"/>'
        + f'<ellipse class="logo-plate-ink" cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}"/>'
        + f'<ellipse class="logo-brass-line" cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx - 3:.1f}" ry="{ry - 3:.1f}"/>'
        + f'<text class="logo-word" x="{cx:.1f}" y="{cy + 1:.1f}" font-size="{h * 0.1:.1f}" '
        'text-anchor="middle" dominant-baseline="central">clude</text>'
    )


def mark_svg(px: int = 22) -> str:
    """The keyhole alone as an inline SVG `px` high, for the header bar;
    decorative, since the wordmark beside it says the name."""
    return (
        f'<svg class="logo" viewBox="0 0 40 40" width="{px}" height="{px}" '
        'aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg">'
        f"{keyhole(20, 20, 37.6)}</svg>"
    )


def favicon_svg() -> str:
    """The keyhole as a standalone SVG file for the browser tab, in ink
    and brass on nothing, gaslight's colours on a dark device. Colours
    are set here because a favicon has no page stylesheet."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">'
        "<style>"
        ".logo-ink{fill:#14110D}.logo-brass-line{fill:none;stroke:#A97B2C;stroke-width:1.4}"
        ".logo-hole{fill:#F5F0E4;font-family:Georgia,serif;font-weight:700}"
        "@media (prefers-color-scheme: dark){.logo-ink{fill:#EDE6D8}.logo-hole{fill:#121013}"
        ".logo-brass-line{stroke:#D6A75A}}"
        "</style>"
        f"{keyhole(20, 20, 37.6)}</svg>\n"
    )
