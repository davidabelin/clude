"""The looks a player can choose between (Phase 9h).

A style is one stylesheet under ``static/styles/``: every colour, the
type, the sizes, the board's dressing. `clude_web.board_svg` draws the
board's geometry and sets no colour, so a style dresses what it draws
and the geometry stays in one place. Each account picks a style
(`clude_web.users.set_style`), changed at any time from the header bar,
mid-game included; `base.html` links the chosen sheet and marks
``<html data-style="...">`` so a rule can tell one look from another.

Three looks since 2026-09-29 (David's fourth round, D17): Case-file
light, the default, and Gaslight dark, Phase 10's "engraved, not
brass-plated" in its two themes on one sheet, each fixing
``<html data-theme="...">``; and Developer, which was Legacy, the look
of Phases 8.1 to 9h frozen on 2026-09-26. ``legacy.css`` is still never
edited; Developer differs from the other two in content as well as
dress (a game's cost is shown only there).

"Engraved (auto)", which followed the device, is gone: on a dark device
it was Gaslight dark, and David could not tell them apart. A key stored
or held in a session from before is read through `RENAMED`.

A look is `engraved` when it wears the Phase 10 screens: the table's
stage and rail, the decorated board, the header bar's mark. Developer
keeps the markup Legacy was frozen with, since its sheet has no rules
for anything newer and never will.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Style:
    """One look: its key (stored on the account and set as
    ``data-style``), its title (the header bar's word for it), its
    stylesheet (a path under ``static/``), its fixed theme (``"light"``,
    ``"dark"``, or empty to leave it to the sheet), whether it wears
    the Phase 10 screens, and whether it shows what a stored game cost
    (the Developer look only, D17)."""

    key: str
    title: str
    stylesheet: str
    theme: str = ""
    engraved: bool = False
    costs: bool = False


STYLES: dict = {
    "casefile": Style("casefile", "Case-file light", "styles/engraved.css", theme="light", engraved=True),
    "gaslight": Style("gaslight", "Gaslight dark", "styles/engraved.css", theme="dark", engraved=True),
    "developer": Style("developer", "Developer", "styles/legacy.css", costs=True),
}
"""Every style, by key, in the order the header bar lists them."""

DEFAULT_STYLE = "casefile"
"""What an account with no choice recorded, and a signed-out page, gets
(David, 2026-09-29, D17)."""

RENAMED: dict = {"legacy": "developer", "engraved": "gaslight"}
"""Keys a look had before, and the look each is now: Legacy renamed
Developer, and Engraved (auto) folded into Gaslight dark (D17)."""


def canonical(key) -> str:
    """`key` normalised, and brought forward if it names a look by an
    older key (`RENAMED`)."""
    key = str(key or "").strip().lower()
    return RENAMED.get(key, key)


def style_named(key) -> Style:
    """The style for `key`, or the default for an unknown or missing
    one: a stored key from a style since removed must still render."""
    return STYLES.get(canonical(key), STYLES[DEFAULT_STYLE])


def is_style(key) -> bool:
    """Whether `key` names a style on the list, by its current key."""
    return str(key or "").strip().lower() in STYLES
