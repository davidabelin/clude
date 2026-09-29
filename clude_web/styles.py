"""The looks a player can choose between (Phase 9h).

A style is one stylesheet under ``static/styles/``: every colour, the
type, the sizes, the board's dressing. `clude_web.board_svg` draws the
board's geometry and sets no colour, so a style dresses what it draws
and the geometry stays in one place. Each account picks a style
(`clude_web.users.set_style`), changed at any time from the header bar,
mid-game included; `base.html` links the chosen sheet and marks
``<html data-style="...">`` so a rule can tell one look from another.

Two looks: Legacy, the look of Phases 8.1 to 9h frozen on 2026-09-26,
and Engraved, Phase 10's "engraved, not brass-plated", in the list as
a beta from 10b (2026-09-28) and the default once 10e lands (D7).
Legacy stays fully functional and selectable from here on (David,
2026-09-28); ``legacy.css`` is never edited.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Style:
    """One look: its key (stored on the account and set as
    ``data-style``), its title (the header bar's word for it) and its
    stylesheet, a path under ``static/``."""

    key: str
    title: str
    stylesheet: str


STYLES: dict = {
    "legacy": Style("legacy", "Legacy", "styles/legacy.css"),
    "engraved": Style("engraved", "Engraved (beta)", "styles/engraved.css"),
}
"""Every style, by key, in the order the header bar lists them."""

DEFAULT_STYLE = "legacy"
"""What an account with no choice recorded, and a signed-out page, gets.
Engraved takes over after Phase 10e (D7)."""


def style_named(key) -> Style:
    """The style for `key`, or the default for an unknown or missing
    one: a stored key from a style since removed must still render."""
    return STYLES.get(str(key or "").strip().lower(), STYLES[DEFAULT_STYLE])


def is_style(key) -> bool:
    """Whether `key` names a style on the list."""
    return str(key or "").strip().lower() in STYLES
