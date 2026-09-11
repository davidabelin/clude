"""Cards and the Suggestion/Accusation record types.

Card lists and names match `legacy/domain.py` (see CLAUDE.md: clude copies
the Classic game's real names). Unlike the legacy version, `Suggestion`
carries `card_shown`, closing the gap noted in `legacy/README.md`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

SUSPECTS = ["Scarlett", "Mustard", "White", "Green", "Peacock", "Plum"]
WEAPONS = ["Candlestick", "Knife", "Lead_Pipe", "Revolver", "Rope", "Wrench"]
ROOMS = [
    "Kitchen", "Ballroom", "Conservatory", "Billiard", "Library",
    "Study", "Hall", "Lounge", "Dining",
]
ALL_CARDS = SUSPECTS + WEAPONS + ROOMS


@dataclass(frozen=True)
class Suggestion:
    """One suggestion and its resolution.

    Parameters
    ----------
    suggester : int
        Player index who made the suggestion.
    suspect, weapon, room : str
        The three named cards. `room` must be the suggester's current room.
    refuter : int or None
        Player index who showed a card, or None if nobody could refute.
    shown_to : int
        Player index the card was shown to (equals `suggester` in the
        normal case; kept separate for observation-building generality).
    card_shown : str or None
        The specific card shown. Populated only from the perspective of an
        observer entitled to know it (the suggester and the refuter); other
        players' `ClueObservation` sees this suggestion with `card_shown =
        None` even though a refutation happened.
    """

    suggester: int
    suspect: str
    weapon: str
    room: str
    refuter: Optional[int]
    shown_to: int
    card_shown: Optional[str]

    def cards(self) -> tuple[str, str, str]:
        return (self.suspect, self.weapon, self.room)


@dataclass(frozen=True)
class Accusation:
    """One accusation and whether it matched the envelope."""

    accuser: int
    suspect: str
    weapon: str
    room: str
    correct: bool

    def cards(self) -> tuple[str, str, str]:
        return (self.suspect, self.weapon, self.room)
