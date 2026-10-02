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
    if reference is not None:
        ref_y = y_of(reference[0])
        body.append(f'<path d="M{left} {ref_y} H{right}" class="ref"/>')
    body += labels  # over the reference line
    if reference is not None:
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


# --- one question, six answers (W2) ------------------------------------------


def _belief_six() -> Figure:
    """Every method's P(Mrs. White is in the envelope) on the Rope
    question, beside the floor's own."""
    example = facts.rope_question()
    exact = example["plum"]["White"]
    columns = [
        ("the floor", "alone", example["uniform"]["White"], "bar-neutral"),
        ("Scarlett", "naive Bayes", example["scarlett"][1]["White"], "s-scarlett"),
        ("Mustard", "tree", example["mustard"]["White"], "s-mustard"),
        ("White", "Markov", example["white"]["White"], "s-white"),
        ("Peacock", "D-S", example["peacock"]["White"], "s-peacock"),
        ("Plum", "exact", exact, "s-plum"),
    ]
    label = "P(Mrs. White is in the envelope), by method: " + ", ".join(
        f"{name} {value:.2f}" for name, _, value, _ in columns
    ) + "."
    return _columns(
        "belief-six", "One question, six answers",
        "The same evidence, read six ways. The count is exactly right; every other answer is a character.",
        columns, None, "P(Mrs. White is in the envelope)", label,
    )


# --- Plum's search, traced --------------------------------------------------


def _plum_search() -> Figure:
    """The backtracking search on the Rope question as a tree: every
    placing tried, the dead ends, and the three complete deals."""
    from clude_constraints import ENVELOPE

    search = facts.plum_search()
    root, order = search["tree"], search["order"]
    names = {"White": "Mrs. White", "Peacock": "Mrs. Peacock", "Rope": "the Rope", "Wrench": "the Wrench"}
    reasons = {
        "hand": "Mustard's hand is full",
        "category": "that category already has its envelope card",
        "contradiction": "Mustard would hold neither Peacock nor the Rope",
    }

    def leaves(node) -> int:
        return 1 if not node["children"] else sum(leaves(c) for c in node["children"])

    left, right = 70, 352
    slot = (right - left) / leaves(root)
    xs: dict = {}
    cursor = [0]

    def place(node) -> None:
        if not node["children"]:
            xs[id(node)] = left + slot * (cursor[0] + 0.5)
            cursor[0] += 1
            return
        for child in node["children"]:
            place(child)
        xs[id(node)] = sum(xs[id(c)] for c in node["children"]) / len(node["children"])

    place(root)
    top, step = 30, 58

    def y_of(depth: int) -> float:
        return top + depth * step

    body = [_text(xs[id(root)], y_of(0) + 4, "start", "t-xs t-soft", "middle")]
    for depth, card in enumerate(order):
        body.append(_text(4, y_of(depth + 1) + 4, names.get(card, card), "t-xs t-soft"))
    edges, nodes, deals = [], [], []

    def draw(node, depth: int) -> None:
        for child in node["children"]:
            x1, y1, x2, y2 = xs[id(node)], y_of(depth), xs[id(child)], y_of(depth + 1)
            edges.append(f'<path d="M{x1:.1f} {y1 + 11} L{x2:.1f} {y2 - 11}" class="ln ln-soft"/>')
            status = child["status"]
            cls = "node-open" if status == "open" else "node-deal" if status == "deal" else "node-dead"
            where = "in Mustard's hand" if child["holder"] != ENVELOPE else "in the envelope"
            note = f"{names[child['card']]} {where}" + (f": {reasons[status]}" if status in reasons else "")
            nodes.append(f'<circle cx="{x2:.1f}" cy="{y2}" r="11" class="node {cls}"><title>{escape(note)}</title></circle>')
            nodes.append(_text(x2, y2 + 4, "E" if child["holder"] == ENVELOPE else "M", "t-xs t-b node-initial", "middle"))
            if status in reasons:
                nodes.append(f'<path d="M{x2 - 4:.1f} {y2 + 16} l8 8 M{x2 + 4:.1f} {y2 + 16} l-8 8" class="ln mark-no"/>')
            if status == "deal":
                deals.append(child)
                nodes.append(_text(x2, y2 + 26, str(len(deals)), "t-xs t-b", "middle"))
            draw(child, depth + 1)

    draw(root, 0)
    body += edges + nodes
    y = y_of(len(order)) + 46
    body.append(f'<circle cx="14" cy="{y}" r="7" class="node node-open"/>')
    body.append(_text(26, y + 4, "placed", "t-xs t-soft"))
    body.append(f'<circle cx="86" cy="{y}" r="7" class="node node-deal"/>')
    body.append(_text(98, y + 4, "a complete deal, numbered", "t-xs t-soft"))
    body.append(f'<path d="M246 {y - 4} l8 8 M254 {y - 4} l-8 8" class="ln mark-no"/>')
    body.append(_text(260, y + 4, "a dead end", "t-xs t-soft"))
    y += 16
    body.append(_text(7, y + 4, "M: in Mustard's hand.  E: in the envelope.", "t-xs t-soft"))
    white = sum(1 for d in deals if d["deal"].get("White") == ENVELOPE)
    body.append(_text(180, y + 24, f"{len(deals)} deals survive; Mrs. White is in the envelope in {white} of them.", "t-sm t-b", "middle"))
    label = (
        f"Plum's search tries each open card in Mustard's hand and in the envelope in turn, {search['nodes']} steps in all. "
        f"Dead ends are a full hand, a category that already has its envelope card, or a placing that leaves the shown card nowhere. "
        f"{len(deals)} complete deals survive, with Mrs. White in the envelope in {white}."
    )
    return Figure(
        key="plum-search", title="Plum's search on the Rope question",
        caption="The search, step by step: each open card is tried in Mustard's hand and in the envelope, and a branch is abandoned as soon as it breaks a rule.",
        svg=_svg(360, int(y + 36), "".join(body), label),
    )


# --- Peacock's two numbers --------------------------------------------------


def _peacock_interval() -> Figure:
    """Belief and plausibility for the four open cards, with the single
    number she reports between them."""
    example = facts.rope_question()
    belief, plaus, betp = example["peacock_belief"], example["peacock_plausibility"], example["peacock"]
    names = [("White", "Mrs. White"), ("Peacock", "Mrs. Peacock"), ("Rope", "the Rope"), ("Wrench", "the Wrench")]
    left, right, height = 86, 268, 14

    def x_of(value: float) -> float:
        return left + value * (right - left)

    body = []
    for tick in (0, 0.5, 1):
        body.append(_text(x_of(tick), 14, f"{tick:g}", "t-xs t-soft t-num", "middle"))
        body.append(f'<path d="M{x_of(tick):.1f} 20 V{20 + 40 * len(names)}" class="grid"/>')
    y = 28
    for card, name in names:
        body.append(_text(left - 8, y + 11, name, "t-sm", "end"))
        body.append(f'<rect x="{left}" y="{y}" width="{right - left}" height="{height}" class="interval-track"/>')
        body.append(f'<rect x="{left}" y="{y}" width="{x_of(plaus[card]) - left:.1f}" height="{height}" class="interval-pl"/>')
        body.append(f'<rect x="{left}" y="{y}" width="{x_of(belief[card]) - left:.1f}" height="{height}" class="interval-bel"/>')
        bx = x_of(betp[card])
        body.append(
            f'<path d="M{bx:.1f} {y - 3} l5 10 l-5 10 l-5 -10 Z" class="betp">'
            f"<title>{escape(name)}: belief {belief[card]:.2f}, plausibility {plaus[card]:.2f}, BetP {betp[card]:.2f}</title></path>"
        )
        body.append(_text(right + 8, y + 11, f"{belief[card]:.2f} to {plaus[card]:.2f}", "t-xs t-num"))
        y += 40
    y += 6
    body.append(f'<rect x="8" y="{y}" width="16" height="10" class="interval-bel"/>')
    body.append(_text(30, y + 9, "belief: what the evidence has established", "t-xs t-soft"))
    y += 16
    body.append(f'<rect x="8" y="{y}" width="16" height="10" class="interval-pl"/>')
    body.append(_text(30, y + 9, "plausibility: what it has failed to rule out", "t-xs t-soft"))
    y += 16
    body.append(f'<path d="M16 {y - 1} l5 6 l-5 6 l-5 -6 Z" class="betp"/>')
    body.append(_text(30, y + 9, "the one number she reports (BetP)", "t-xs t-soft"))
    label = "Peacock's belief and plausibility for each open card: " + "; ".join(
        f"{name} {belief[card]:.2f} to {plaus[card]:.2f}, reported as {betp[card]:.2f}" for card, name in names
    ) + "."
    return Figure(
        key="peacock-interval", title="Peacock's two numbers",
        caption="For each card, what the evidence has established (solid) and what it has failed to rule out (pale). The diamond is the one number she reports when a probability is required.",
        svg=_svg(360, y + 24, "".join(body), label),
    )


# --- Mustard's path through the tree ----------------------------------------

FEATURE_WORDS: dict = {
    "possible_holders_frac": "holders still possible",
    "or_constraint_involvement": "open facts it is in",
    "times_named_unrefuted": "times named, undisproved",
    "times_named_total": "times named",
    "turn_fraction": "turn, as a share of 50",
    "category_size_frac": "category size, of nine",
    "distinct_namers": "players who named it",
    "named_beside_located": "named beside placed cards",
}
"""Each of the tree's eight features (`decision_tree.FEATURE_NAMES`) in
words, for the figure and the article's table."""


def _mustard_path() -> Figure:
    """The questions the trained tree asked about the card the Rope
    question's suggestion named, and the leaf it reached."""
    example = facts.rope_question()
    path, (leaf, rows) = example["mustard_path"], example["mustard_leaf"]
    body, y = [], 6
    for step in path:
        name = FEATURE_WORDS.get(step["feature"], step["feature"])
        threshold = f"{step['threshold']:.2f}".rstrip("0").rstrip(".")
        value = f"{step['value']:.2f}".rstrip("0").rstrip(".")
        answer = "yes" if step["yes"] else "no"
        body.append(f'<rect x="6" y="{y}" width="348" height="34" rx="2" class="plate"/>')
        body.append(_text(14, y + 14, f"{name} at most {threshold}?", "t-sm t-b"))
        body.append(_text(14, y + 28, f"this card: {value}; {step['n']:,} training rows asked this", "t-xs t-soft"))
        body.append(f'<rect x="304" y="{y + 7}" width="42" height="20" rx="10" class="badge badge-{answer}"/>')
        body.append(_text(325, y + 21, answer, f"t-xs t-b badge-text-{answer}", "middle"))
        y += 34
        body.append(f'<path d="M180 {y} v10 M176 {y + 6} l4 4 l4 -4" class="ln ln-soft fl-none"/>')
        y += 12
    body.append(f'<rect x="6" y="{y}" width="348" height="34" rx="2" class="plate plate-leaf"/>')
    body.append(_text(14, y + 14, f"the leaf says {leaf:.3f}", "t-sm t-b"))
    body.append(_text(14, y + 28, f"{rows:,} training rows ended here; the same leaf for all four open cards", "t-xs t-soft"))
    label = "Mustard's tree asks: " + "; ".join(
        f"{FEATURE_WORDS.get(s['feature'], s['feature'])} at most {s['threshold']:.2f}, {'yes' if s['yes'] else 'no'}" for s in path
    ) + f". The leaf reached says {leaf:.3f}."
    return Figure(
        key="mustard-path", title="Mustard's tree on the Rope question",
        caption="The questions the trained tree asked about Mrs. Peacock's card, top to bottom, and the leaf it reached. Every one of the four open cards reaches the same leaf.",
        svg=_svg(360, y + 42, "".join(body), label),
    )


# --- White's chain ----------------------------------------------------------


def _arrow(x: float, y: float, dx: float, dy: float) -> str:
    """A small arrowhead with its tip at (x, y), pointing along (dx, dy)."""
    from math import atan2, cos, pi, sin

    angle = atan2(dy, dx)
    points = [(x, y)]
    for turn in (pi * 5 / 6, -pi * 5 / 6):
        points.append((x + 8 * cos(angle + turn), y + 8 * sin(angle + turn)))
    return '<path d="M' + " L".join(f"{px:.1f} {py:.1f}" for px, py in points) + ' Z" class="arc-head"/>'


def _white_chain() -> Figure:
    """One opponent's run of suggestions, and the two-state chain fitted
    to it."""
    example = facts.chain_example()
    sequence = example["sequence"]
    p01, p10, stationary = float(example["p01"]), float(example["p10"]), float(example["stationary"])
    body = [_text(6, 14, "one opponent's suggestions, in order", "t-xs t-soft")]
    for i, symbol in enumerate(sequence):
        cx = 26 + i * 44
        body.append(f'<circle cx="{cx}" cy="36" r="9" class="sym-{"repeat" if symbol else "new"}"/>')
        body.append(_text(cx, 58, "repeat" if symbol else "new", "t-xs t-soft", "middle"))
    ax, bx, cy, r = 96, 264, 158, 30
    mid = (ax + bx) / 2
    # new -> repeat, over the top; repeat -> new, under.
    body.append(f'<path d="M{ax + 26} {cy - 15} Q{mid} {cy - 52} {bx - 26} {cy - 15}" class="arc"/>')
    body.append(_arrow(bx - 26, cy - 15, bx - 26 - mid, 37))
    body.append(_text(mid, cy - 36, f"{p01:.2f}", "t-sm t-b t-num t-halo", "middle"))
    body.append(f'<path d="M{bx - 26} {cy + 15} Q{mid} {cy + 52} {ax + 26} {cy + 15}" class="arc"/>')
    body.append(_arrow(ax + 26, cy + 15, ax + 26 - mid, -37))
    body.append(_text(mid, cy + 46, f"{p10:.2f}", "t-sm t-b t-num t-halo", "middle"))
    # staying put: a loop over each state
    for x, stay in ((ax, 1 - p01), (bx, 1 - p10)):
        body.append(f'<path d="M{x - 12} {cy - 28} C{x - 44} {cy - 72} {x + 44} {cy - 72} {x + 12} {cy - 28}" class="arc"/>')
        body.append(_arrow(x + 12, cy - 28, -32, 44))
        body.append(_text(x, cy - 66, f"{stay:.2f}", "t-xs t-b t-num t-halo", "middle"))
    body.append(f'<circle cx="{ax}" cy="{cy}" r="{r}" class="state"/>')
    body.append(_text(ax, cy + 4, "new", "t-sm t-b", "middle"))
    body.append(f'<circle cx="{bx}" cy="{cy}" r="{r}" class="state state-on"/>')
    body.append(_text(bx, cy + 4, "repeat", "t-sm t-b state-on-text", "middle"))
    body.append(_text(180, 234, f"in the long run, P(repeat) = {stationary:.2f}", "t-sm t-b", "middle"))
    label = (
        "One opponent's suggestions, " + ", ".join("repeat" if s else "new" for s in sequence) + ". "
        f"The fitted chain moves from new to repeat with probability {p01:.2f} and from repeat to new with {p10:.2f}; "
        f"in the long run it repeats with probability {stationary:.2f}."
    )
    return Figure(
        key="white-chain", title="White's two-state chain",
        caption="A run of one opponent's suggestions, each a repeat of a card they had named before or all new, and the chain White fits to it.",
        svg=_svg(360, 246, "".join(body), label),
    )


# --- Green's arms -----------------------------------------------------------


def _beta_pdf(x: float, a: float, b: float) -> float:
    from math import gamma

    return x ** (a - 1) * (1 - x) ** (b - 1) * gamma(a + b) / (gamma(a) * gamma(b))


def _green_arms() -> Figure:
    """Each arm's Beta posterior after one lesson, the Rope question
    scored against its answer, over the flat prior they all began with."""
    example = facts.rope_question()
    arms = sorted(example["green_arms"].items(), key=lambda item: -item[1][2])
    left, right, top, bottom, top_value = 36, 346, 18, 196, 3.2

    def x_of(v: float) -> float:
        return left + v * (right - left)

    def y_of(v: float) -> float:
        return bottom - v / top_value * (bottom - top)

    body = [_text(left - 30, 12, "how likely each arm is to be the best, as Green now sees it", "t-xs t-soft")]
    for tick in (0, 0.25, 0.5, 0.75, 1):
        body.append(f'<path d="M{x_of(tick):.1f} {top} V{bottom}" class="grid"/>')
        body.append(_text(x_of(tick), bottom + 14, f"{tick:g}", "t-xs t-soft t-num", "middle"))
    body.append(f'<path d="M{left} {bottom} H{right}" class="axis"/>')
    body.append(f'<path d="M{left} {y_of(1):.1f} H{right}" class="ref"/>')
    body.append(_text(left + 4, y_of(1) - 5, "the prior, Beta(1, 1)", "t-xs t-soft t-halo"))
    steps = 60
    for name, (a, b, _mean) in arms:
        points = []
        for i in range(steps + 1):
            x = 0.004 + (0.992 * i) / steps
            points.append(f"{'M' if i == 0 else 'L'}{x_of(x):.1f} {y_of(min(_beta_pdf(x, a, b), top_value)):.1f}")
        path = " ".join(points)
        if name == "White":
            body.append(f'<path d="{path}" class="line sl-under"/>')
        body.append(f'<path d="{path}" class="line sl-{name.lower()}"><title>{escape(name)}: Beta({a:g}, {b:g}), mean {_mean:.2f}</title></path>')
    # The legend under the axis, clear of every curve.
    for row, (name, (a, b, mean)) in enumerate(arms):
        x, y = left + 8, bottom + 34 + 15 * row
        if name == "White":
            body.append(f'<path d="M{x} {y} h18" class="line sl-under"/>')
        body.append(f'<path d="M{x} {y} h18" class="line sl-{name.lower()}"/>')
        body.append(_text(x + 24, y + 4, f"{name}: Beta({a:g}, {b:g}), mean {mean:.2f}", "t-xs"))
    label = "Each arm's Beta posterior after one lesson: " + "; ".join(
        f"{name} Beta({a:g}, {b:g}), mean {mean:.2f}" for name, (a, b, mean) in arms
    ) + ". The prior for every arm was Beta(1, 1), flat."
    return Figure(
        key="green-arms", title="Green's arms after one lesson",
        caption="Every arm began at Beta(1, 1), the flat line. One question, scored against its answer, has already bent each one.",
        svg=_svg(360, bottom + 34 + 15 * len(arms) + 4, "".join(body), label, "chart"),
    )


def _green_trust() -> Figure:
    """The arms' posterior means after the ring board's benchmark."""
    names = [("Plum", "plum", "exact"), ("Mustard", "mustard", "tree"), ("White", "white", "Markov"), ("Peacock", "peacock", "D-S"), ("Scarlett", "scarlett", "naive Bayes")]
    columns = [(name, sub, float(facts.fact(f"green.arms.ring.{key}")), f"s-{key}") for name, key, sub in names]
    label = "The mean of each arm's Beta posterior after sixty benchmark games on the ring board: " + ", ".join(
        f"{name} {value:.2f}" for name, _, value, _ in columns
    ) + "."
    return _columns(
        "green-trust", "Whom Green came to trust",
        "After sixty benchmark games on the ring board: the mean of each arm's Beta posterior, against the prior's 0.5.",
        columns, (0.5, "the prior: 0.5"), "mean of the arm's posterior", label,
    )


# --- the floor's notepad ----------------------------------------------------


def _floor_notepad() -> Figure:
    """The deduction floor's grid for the Rope question, from the
    viewer's chair: every card against every holder."""
    from clude_constraints import ENVELOPE
    from clude_core.domain import ROOMS, SUSPECTS, WEAPONS

    mask = facts.rope_question()["mask"]
    holders = [(facts.ROPE_SEATS["me"], "you"), (facts.ROPE_SEATS["holder"], "Mustard"), (facts.ROPE_SEATS["third"], "Green"), (ENVELOPE, "envelope")]
    names = {
        "Scarlett": "Miss Scarlett", "Mustard": "Colonel Mustard", "White": "Mrs. White", "Green": "Mr. Green",
        "Peacock": "Mrs. Peacock", "Plum": "Professor Plum", "Lead_Pipe": "Lead Pipe",
        "Billiard": "Billiard Room", "Dining": "Dining Room",
    }
    x0, column, row = 118, 58, 13
    body = []
    for i, (_, title) in enumerate(holders):
        body.append(_text(x0 + column * (i + 0.5), 14, title, "t-xs t-b", "middle"))
    y = 20
    for title, category in (("Suspects", SUSPECTS), ("Weapons", WEAPONS), ("Rooms", ROOMS)):
        y += 5
        body.append(_text(6, y + 10, title, "t-xs t-caps t-soft"))
        y += 15
        for card in category:
            located = mask.holder_of(card)
            body.append(_text(6, y + 10, names.get(card, card), "t-xs"))
            for i, (holder, _) in enumerate(holders):
                cx = x0 + column * (i + 0.5)
                if located is not None and holder == located:
                    cls = "cell-env" if holder == ENVELOPE else "cell-located"
                    body.append(f'<rect x="{cx - 4:.1f}" y="{y + 2}" width="8" height="8" class="{cls}"/>')
                elif located is None and mask.is_possible(card, holder):
                    body.append(f'<circle cx="{cx:.1f}" cy="{y + 6}" r="3.5" class="cell-possible"/>')
                else:
                    body.append(f'<rect x="{cx - 3:.1f}" y="{y + 5}" width="6" height="2" class="cell-out"/>')
            y += row
        body.append(f'<path d="M6 {y + 2} H352" class="row-rule"/>')
    y += 10
    body.append(f'<rect x="8" y="{y}" width="8" height="8" class="cell-located"/>')
    body.append(_text(20, y + 8, "held", "t-xs t-soft"))
    body.append(f'<rect x="56" y="{y}" width="8" height="8" class="cell-env"/>')
    body.append(_text(68, y + 8, "proven the envelope's", "t-xs t-soft"))
    body.append(f'<circle cx="190" cy="{y + 4}" r="3.5" class="cell-possible"/>')
    body.append(_text(198, y + 8, "still possible", "t-xs t-soft"))
    body.append(f'<rect x="276" y="{y + 3}" width="6" height="2" class="cell-out"/>')
    body.append(_text(286, y + 8, "ruled out", "t-xs t-soft"))
    y += 22
    for cards, holder in mask.or_constraints:
        who = dict(holders)[holder]
        body.append(_text(6, y, f"and {who} holds at least one of: " + ", ".join(names.get(c, c) for c in sorted(cards)), "t-xs t-b"))
        y += 14
    label = (
        "The floor's grid for the Rope question: every card against you, Mustard, Green and the envelope. "
        "Seventeen cards are placed, the Study is proven the envelope's, and Mrs. White, Mrs. Peacock, the Rope "
        "and the Wrench could each be Mustard's or the envelope's; Mustard holds at least one of Peacock and the Rope."
    )
    return Figure(
        key="floor-notepad", title="The floor's notepad for the Rope question",
        caption="What the deduction floor knows in the Rope question, from the viewer's chair. The four open cards are the only ones it leaves to the methods.",
        svg=_svg(360, int(y + 4), "".join(body), label),
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
    "belief-six": _belief_six,
    "plum-search": _plum_search,
    "peacock-interval": _peacock_interval,
    "mustard-path": _mustard_path,
    "white-chain": _white_chain,
    "green-arms": _green_arms,
    "green-trust": _green_trust,
    "floor-notepad": _floor_notepad,
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
