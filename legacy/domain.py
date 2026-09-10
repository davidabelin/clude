"""
Legacy domain model for clude.

Extracted from the claude.ai chat "Machine learning for Clue game in Python".
Code below the header is as it appeared in that chat; only this docstring was
added. Status and known issues: see legacy/README.md.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import numpy as np

# --- Domain ---
SUSPECTS = ["Scarlett", "Mustard", "White", "Green", "Peacock", "Plum"]
WEAPONS  = ["Candlestick", "Knife", "Lead_Pipe", "Revolver", "Rope", "Wrench"]
ROOMS    = ["Kitchen", "Ballroom", "Conservatory", "Billiard",
            "Library", "Study", "Hall", "Lounge", "Dining"]
ALL_CARDS = SUSPECTS + WEAPONS + ROOMS  # 21 cards total

@dataclass
class Suggestion:
    suggester: int           # player index
    suspect: str
    weapon: str
    room: str
    refuter: Optional[int]   # None if no one could refute
    shown_to: int            # who saw the card (usually == suggester)

@dataclass
class GameState:
    n_players: int
    my_index: int
    my_cards: frozenset
    suggestions: list[Suggestion] = field(default_factory=list)
    accusations: list[tuple] = field(default_factory=list)
    active_players: list[bool] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.active_players:
            self.active_players = [True] * self.n_players
