"""Wikiclude's pictures: every one an uncoloured, classed SVG.

Like `clude_web.board_svg` and `clude_web.logo`, nothing here names a
colour. Each shape carries a class and `static/styles/wiki.css` dresses
it from the look's tokens, so one figure serves Case-file light,
Gaslight dark and Developer.

Two kinds:

- **Drawn here**, by the functions below, when the wiki is built: the
  pawns, the worked examples (computed by the real agents, through
  `facts.rope_question`), and the charts, whose numbers come from
  `facts.TABLES` and so cannot differ from the tables the articles print.
- **The method diagrams**, kept as files in ``figures/``. They are the
  `DIAGRAMS` registry of ``docs/ux/diagrams/build_diagrams.py``, drawn by
  Mermaid on a maintainer's machine and stripped of its colours by
  ``scripts/build_wiki_figures.py``; nothing ships Mermaid to a reader.

Every drawn figure is laid out 360 units wide, so at a phone's 390 px
its 12-unit type is 12 px type.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from html import escape
from itertools import product
from pathlib import Path

from . import facts

FILES = Path(__file__).resolve().parent / "figures"

SUSPECTS = ("Scarlett", "Mustard", "White", "Green", "Peacock", "Plum")

FULL_NAMES = {
    "Scarlett": "Miss Scarlett", "Mustard": "Colonel Mustard", "White": "Mrs. White",
    "Green": "Mr. Green", "Peacock": "Mrs. Peacock", "Plum": "Professor Plum",
}


@dataclass(frozen=True)
class Figure:
    """One picture: its key, a title for its own page, the caption it
    carries when an article gives none, and the SVG itself."""

    key: str
    title: str
    caption: str
    svg: str


def _svg(width: int, height: int, body: str, label: str, kind: str = "drawn") -> str:
    return (
        f'<svg class="fig fig-{kind}" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{escape(label, quote=True)}" xmlns="http://www.w3.org/2000/svg">{body}</svg>'
    )


def _text(x, y, text, cls="", anchor="start") -> str:
    classes = f"t {cls}".strip()
    return f'<text x="{x}" y="{y}" class="{classes}" text-anchor="{anchor}">{escape(str(text))}</text>'


# --- the pawns --------------------------------------------------------------


def _pawn(suspect: str, x: float = 0, y: float = 0, scale: float = 1.0) -> str:
    """A playing piece in a suspect's colour, with its initial."""
    key = suspect.lower()
    return (
        f'<g transform="translate({x} {y}) scale({scale})">'
        f'<ellipse cx="50" cy="107" rx="34" ry="7" class="pawn-shadow"/>'
        f'<path d="M39 49 Q50 56 61 49 L74 96 Q50 110 26 96 Z" class="pawn s-{key}"/>'
        f'<circle cx="50" cy="32" r="19" class="pawn s-{key}"/>'
        f'<text x="50" y="39" text-anchor="middle" class="pawn-initial si-{key}">{suspect[0]}</text>'
        f"</g>"
    )


def _token(suspect: str) -> Figure:
    return Figure(
        key=f"token-{suspect.lower()}",
        title=f"{FULL_NAMES[suspect]}'s token",
        caption=f"{FULL_NAMES[suspect]}'s token.",
        svg=_svg(100, 120, _pawn(suspect), f"{FULL_NAMES[suspect]}'s token", "pawn"),
    )


def _disc(suspect: str, cx: float, cy: float, r: float = 13) -> str:
    key = suspect.lower()
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" class="pawn s-{key}"/>'
        f'<text x="{cx}" y="{cy + 4.5}" text-anchor="middle" class="disc-initial si-{key}">{suspect[0]}</text>'
    )


def _card(x: float, y: float, w: float, text: str, cls: str = "") -> str:
    """A playing card as a small labelled plate."""
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="2" class="card {cls}"/>'
        + _text(x + w / 2, y + 17, text, "t-sm t-b", "middle")
    )


# --- a suggestion goes round the table --------------------------------------


def _suggestion_round() -> Figure:
    """Plum suggests; Scarlett cannot answer; Mustard shows a card;
    Green is never asked."""
    rows = [
        ("Scarlett", "Miss Scarlett", "holds none of the three", "cannot disprove", "no"),
        ("Mustard", "Colonel Mustard", "holds the Rope", "shows it, to Plum alone", "show"),
        ("Green", "Mr. Green", "may hold any of them", "is never asked", "skip"),
    ]
    body = ['<rect x="6" y="6" width="348" height="88" rx="2" class="plate"/>']
    body.append(_disc("Plum", 32, 34))
    body.append(_text(54, 30, "Professor Plum suggests", "t-b"))
    body.append(_text(54, 46, "from the Hall, on his turn", "t-sm t-soft"))
    for i, name in enumerate(("Mrs. Peacock", "the Rope", "the Hall")):
        body.append(_card(18 + i * 110, 58, 104, name))
    y = 128
    body.append(f'<path d="M32 98 V{y + 2 * 68 - 18}" class="ln ln-soft"/>')
    for suspect, name, holds, outcome, mark in rows:
        body.append(f'<path d="M27 {y - 22} l5 6 l5 -6" class="ln ln-soft fl-none"/>')
        body.append(_disc(suspect, 32, y))
        body.append(_text(54, y - 3, name, "t-b"))
        body.append(_text(54, y + 13, f"{holds}: {outcome}", "t-sm t-soft"))
        if mark == "no":
            body.append(f'<path d="M324 {y - 8} l14 14 M338 {y - 8} l-14 14" class="ln mark-no"/>')
        elif mark == "show":
            body.append(f'<rect x="322" y="{y - 12}" width="18" height="24" rx="2" class="card card-shown"/>')
        else:
            body.append(f'<path d="M322 {y} h18" class="ln ln-soft"/>')
        y += 68
    label = (
        "Professor Plum suggests Mrs. Peacock, the Rope and the Hall. Miss Scarlett cannot disprove it. "
        "Colonel Mustard shows Plum the Rope. Mr. Green is never asked."
    )
    return Figure(
        key="suggestion-round",
        title="A suggestion goes round the table",
        caption="A suggestion passes to the left until somebody can disprove it.",
        svg=_svg(360, 300, "".join(body), label),
    )


# --- the worked example: counting deals -------------------------------------


def rope_deals() -> list:
    """The four ways the worked example's open cards could lie, and
    whether each survives the evidence: ``(envelope, hand, consistent)``."""
    deals = []
    for suspect, weapon in product(("White", "Peacock"), ("Rope", "Wrench")):
        hand = ({"White", "Peacock"} - {suspect}) | ({"Rope", "Wrench"} - {weapon})
        deals.append(((suspect, weapon), tuple(sorted(hand)), bool(hand & {"Peacock", "Rope"})))
    return deals


def _rope_deals() -> Figure:
    deals = rope_deals()
    alive = [d for d in deals if d[2]]
    white = [d for d in alive if "White" in d[0]]
    body = []
    for i, (envelope, hand, ok) in enumerate(deals):
        x, y = 4 + (i % 2) * 178, 4 + (i // 2) * 118
        body.append(f'<rect x="{x}" y="{y}" width="174" height="112" rx="2" class="plate{"" if ok else " plate-out"}"/>')
        body.append(_text(x + 9, y + 19, f"Deal {i + 1}", "t-xs t-soft t-caps"))
        body.append(_text(x + 9, y + 41, "In the envelope", "t-sm t-soft"))
        body.append(_text(x + 9, y + 59, " + ".join(envelope), "t-b" + (" t-accent" if ok and "White" in envelope else "")))
        body.append(_text(x + 9, y + 82, "In Mustard's hand", "t-sm t-soft"))
        body.append(_text(x + 9, y + 100, " + ".join(hand)))
        if not ok:
            body.append(f'<path d="M{x + 6} {y + 106} L{x + 168} {y + 6}" class="ln mark-no"/>')
            body.append(_text(x + 165, y + 19, "ruled out", "t-xs t-b t-warn t-halo", "end"))
    body.append(_text(180, 258, f"{len(alive)} deals survive.", "t-b", "middle"))
    body.append(_text(180, 276, f"Mrs. White is in the envelope in {len(white)} of them.", "t-b", "middle"))
    label = (
        f"Four possible deals. One is ruled out because Mustard would hold neither Peacock nor the Rope. "
        f"Of the {len(alive)} that survive, Mrs. White is in the envelope in {len(white)}."
    )
    return Figure(
        key="rope-deals",
        title="Counting the deals that are still possible",
        caption="Every deal still possible, counted. The one in which Mustard holds neither card he must hold is struck out.",
        svg=_svg(360, 286, "".join(body), label),
    )


# --- charts -----------------------------------------------------------------


def _columns(key, title, caption, columns, reference, y_label, label) -> Figure:
    """A column chart of probabilities with one labelled reference line.

    `columns` is ``(label, sublabel, value, cls)`` per column; `reference`
    is ``(value, text)``.
    """
    left, right, top, bottom = 44, 350, 30, 190
    height = bottom - top

    def y_of(v):
        return bottom - v * height

    body = [_text(left - 34, 14, y_label, "t-xs t-soft")]
    for tick in (0, 0.25, 0.5, 0.75, 1.0):
        y = y_of(tick)
        body.append(f'<path d="M{left} {y} H{right}" class="grid"/>')
        body.append(_text(left - 6, y + 4, f"{tick:.2f}".rstrip("0").rstrip(".") if tick else "0", "t-xs t-soft t-num", "end"))
    slot = (right - left) / len(columns)
    labels = []
    for i, (name, sub, value, cls) in enumerate(columns):
        cx = left + slot * (i + 0.5)
        y = y_of(value)
        body.append(
            f'<path d="M{cx - 12} {bottom} V{y + 4} q0 -4 4 -4 h16 q4 0 4 4 V{bottom} Z" class="bar {cls}">'
            f"<title>{escape(name)}: {value:.2f}</title></path>"
        )
        labels.append(_text(cx, y - 6, f"{value:.2f}", "t-sm t-b t-num t-halo", "middle"))
        body.append(_text(cx, bottom + 16, name, "t-xs", "middle"))
        if sub:
            body.append(_text(cx, bottom + 29, sub, "t-xs t-soft", "middle"))
    ref_y = y_of(reference[0])
    body.append(f'<path d="M{left} {ref_y} H{right}" class="ref"/>')
    body += labels  # over the reference line
    body.append(_text(left + 4, ref_y - 5, reference[1], "t-xs t-b t-halo"))
    body.append(f'<path d="M{left} {bottom} H{right}" class="axis"/>')
    return Figure(key=key, title=title, caption=caption, svg=_svg(360, 228, "".join(body), label, "chart"))


def _rope_bars() -> Figure:
    example = facts.rope_question()
    exact = example["plum"]["White"]
    said = example["scarlett"]
    columns = [("before", "", example["uniform"]["White"], "bar-neutral")] + [
        (word, "", said[n]["White"], "s-scarlett") for n, word in ((1, "heard once"), (2, "twice"), (3, "three times"))
    ]
    label = (
        "Scarlett's probability that Mrs. White is in the envelope: "
        + ", ".join(f"{name} {value:.2f}" for name, _, value, _ in columns)
        + f". The exact answer stays at {exact:.2f}."
    )
    return _columns(
        "rope-bars", "Scarlett hears the same thing three times",
        "The same fact, heard three times. The exact answer does not move after the first; Scarlett's does.",
        columns, (exact, "exact: 2/3"), "P(Mrs. White is in the envelope)", label,
    )


def _logloss(key, title, caption, series, label) -> Figure:
    """A line chart of log-loss at the benchmark's four checkpoints.

    `series` is ``(name, values, cls, label_dy)`` per line, at most
    three; the 50% value of each is labelled, offset by `label_dy`.
    """
    left, right, top, bottom = 40, 344, 44, 220
    top_value = 2.0
    xs = [left + 12 + i * (right - left - 24) / 3 for i in range(4)]

    def y_of(v):
        return bottom - v / top_value * (bottom - top)

    body = []
    for row, (name, _, cls, _) in enumerate(series):  # the legend: the top right is always empty
        y = top + 8 + 15 * row
        body.append(f'<path d="M{right - 150} {y} h18" class="line {cls}"/><circle cx="{right - 141}" cy="{y}" r="4" class="dot {cls}"/>')
        body.append(_text(right - 126, y + 4, name, "t-xs"))
    body.append(_text(left - 34, 34, "log-loss (lower is better)", "t-xs t-soft"))
    for tick in (0, 0.5, 1.0, 1.5, 2.0):
        y = y_of(tick)
        body.append(f'<path d="M{left} {y} H{right}" class="grid"/>')
        body.append(_text(left - 6, y + 4, f"{tick:.1f}" if tick else "0", "t-xs t-soft t-num", "end"))
    for i, word in enumerate(("25%", "50%", "75%", "the end")):
        body.append(_text(xs[i], bottom + 16, word, "t-xs t-soft", "middle"))
    body.append(_text((left + right) / 2, bottom + 32, "share of the game's suggestions already made", "t-xs t-soft", "middle"))
    body.append(f'<path d="M{left} {bottom} H{right}" class="axis"/>')
    for name, values, cls, _ in series:
        points = " ".join(f"{'M' if i == 0 else 'L'}{xs[i]:.1f} {y_of(v):.1f}" for i, v in enumerate(values))
        body.append(f'<path d="{points}" class="line {cls}"/>')
    labels = []
    for name, values, cls, dy in series:
        for i, v in enumerate(values):
            stage = ("25%", "50%", "75%", "the end")[i]
            body.append(
                f'<circle cx="{xs[i]:.1f}" cy="{y_of(v):.1f}" r="4" class="dot {cls}">'
                f"<title>{escape(name)}, {stage}: {v:.2f}</title></circle>"
            )
        labels.append(_text(
            xs[1] + (9 if dy == 0 else 0), y_of(values[1]) + dy + (4 if dy == 0 else 0), f"{values[1]:.2f}",
            "t-xs t-b t-num t-halo", "start" if dy == 0 else "middle",
        ))
    body += labels  # over every line and dot
    return Figure(key=key, title=title, caption=caption, svg=_svg(360, 258, "".join(body), label, "chart"))


def _row(table: str, row: str) -> list:
    cells = facts.TABLES[table].cells(row)
    return [float(c) for c in cells[:4]]


def _plum_budget() -> Figure:
    before, after, uniform = _row("budget.grid", "200k-2k"), _row("budget.grid", "200k-10k"), _row("budget.grid", "uniform")
    series = [
        ("Plum, 2,000 samples", before, "sl-plum dashed", -9),
        ("Plum, 10,000 samples", after, "sl-plum", 0),
        ("uniform baseline", uniform, "sl-neutral", 15),
    ]
    label = (
        f"Log-loss at four checkpoints. Plum with 2,000 samples: {before}. Plum with 10,000 samples: {after}. "
        f"The uniform baseline: {uniform}."
    )
    return _logloss(
        "plum-budget", "Plum's mid-game, before and after the larger sample",
        "Plum against the uniform baseline on the Classic board. Five times the samples repaired most of his mid-game, not all of it.",
        series, label,
    )


def _scarlett_bench() -> Figure:
    scarlett, uniform = _row("bench.grid", "Scarlett"), _row("bench.grid", "uniform")
    series = [("Scarlett", scarlett, "sl-scarlett", -9), ("uniform baseline", uniform, "sl-neutral", 15)]
    label = f"Log-loss at four checkpoints. Scarlett: {scarlett}. The uniform baseline: {uniform}."
    return _logloss(
        "scarlett-bench", "Scarlett against the uniform baseline",
        "Scarlett against the uniform baseline on the Classic board: a little worse than knowing only what is certain, at every checkpoint.",
        series, label,
    )


# --- the method diagrams, from files ----------------------------------------

DIAGRAM_TEXT: dict = {
    "floor-then-method": (
        "The deduction floor, and where every method sits",
        "One gate in front of the six methods and one after: they differ in how they reason under uncertainty, never in what is certain.",
    ),
    "floor-propagation": (
        "Inside the deduction floor",
        "The floor's four seeding steps, then its three rules, repeated until a pass changes nothing.",
    ),
    "scarlett-update": (
        "Scarlett's whole method",
        "Scarlett's whole method: three kinds of suggestion, two multiplications, then the mask every method ends with.",
    ),
    "scarlett-net": (
        "The independence assumption, and the edge that is missing",
        "Three suggestions, one player answering all three. Scarlett multiplies three times; one card in that hand could explain them all.",
    ),
    "mustard-tree": (
        "Mustard's trained tree",
        "The decision tree Mustard actually plays with, grown from the live model.",
    ),
}
"""Title and default caption for each committed diagram, by its key in
``docs/ux/diagrams/build_diagrams.py``'s `DIAGRAMS`."""


def _diagram(key: str) -> Figure:
    title, caption = DIAGRAM_TEXT[key]
    return Figure(key=key, title=title, caption=caption, svg=(FILES / f"{key}.svg").read_text(encoding="utf-8"))


_DRAWN: dict = {
    "suggestion-round": _suggestion_round,
    "rope-deals": _rope_deals,
    "rope-bars": _rope_bars,
    "plum-budget": _plum_budget,
    "scarlett-bench": _scarlett_bench,
    **{f"token-{s.lower()}": (lambda s=s: _token(s)) for s in SUSPECTS},
}


def keys() -> list:
    """Every figure an article may ask for."""
    return sorted(set(_DRAWN) | {k for k in DIAGRAM_TEXT if (FILES / f"{k}.svg").is_file()})


@lru_cache(maxsize=None)
def figure(key: str) -> Figure:
    """The figure with this key.

    Raises
    ------
    KeyError
        If there is no such figure (or its diagram file is missing).
    """
    if key in _DRAWN:
        return _DRAWN[key]()
    if key in DIAGRAM_TEXT and (FILES / f"{key}.svg").is_file():
        return _diagram(key)
    raise KeyError(key)
