"""Account-selectable looks and their content/style policy.

Case-file light is default, Gaslight dark fixes the dark theme, and Developer
uses frozen legacy.css and alone displays costs. Old keys map through
RENAMED; absent/unknown choices fall back. Templates/scripts use the style's
flags rather than duplicating names. See docs/web.md for token/assets.
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
