"""
Legacy constraint propagator (hard logical deductions).

Extracted from the claude.ai chat "Machine learning for Clue game in Python".
Code below the header is as it appeared in that chat; only this docstring and
the domain import were added. Status and known issues: see legacy/README.md.

Planned fate: basis of the shared "deduction floor" -- but see README, the
elimination bookkeeping is stubbed and must be finished first.
"""
from typing import Optional, Dict, List, Set
from itertools import combinations

from .domain import SUSPECTS, WEAPONS, ROOMS, ALL_CARDS, GameState

class ConstraintPropagator:
    """
    Tracks hard logical constraints derived from the game:
    
    1. Each card belongs to exactly one holder.
    2. Each player holds exactly (total_cards // n_players) cards.
    3. Suggestions that go unrefuted eliminate possibilities.
    4. Refutations create 'OR' constraints.
    """
    
    def __init__(self, game_state: GameState, cards_per_player: int):
        self.gs = game_state
        self.cpp = cards_per_player
        n = game_state.n_players
        
        # known[card] = player_index or 'envelope' or None (unknown)
        self.known: Dict[str, Optional[str]] = {c: None for c in ALL_CARDS}
        
        # or_constraints: list of (frozenset_of_cards, player) meaning
        # "player holds at least one of these cards"
        self.or_constraints: List[tuple] = []
        
        # Player hand sizes: known_count[p] = exact number of cards held
        self.hand_size = {p: cards_per_player for p in range(n)}
        
        # Apply own cards
        for card in game_state.my_cards:
            self._set_known(card, game_state.my_index)
    
    def _set_known(self, card: str, holder):
        """Hard assignment: card belongs to holder."""
        if self.known[card] is not None:
            return  # already known, check consistency
        
        self.known[card] = holder
        # Propagate: no other holder can have this card
        self._propagate()
    
    def add_refutation_constraint(self, refuter: int, cards: tuple[str, str, str]):
        """Refuter holds at least one of (suspect, weapon, room)."""
        # Filter to only cards we don't already know the location of
        unknown_cards = frozenset(
            c for c in cards 
            if self.known[c] != refuter  # not already assigned to refuter
            and self.known[c] is None    # not assigned elsewhere
        )
        
        if len(unknown_cards) == 0:
            return  # Constraint already satisfied
        if len(unknown_cards) == 1:
            # Only one possibility — hard assignment!
            card = next(iter(unknown_cards))
            self._set_known(card, refuter)
        else:
            self.or_constraints.append((unknown_cards, refuter))
        
        self._propagate()
    
    def add_no_refutation(self, skipped_players: list, cards: tuple):
        """None of the skipped players hold any of these cards."""
        for p in skipped_players:
            for card in cards:
                if self.known[card] is None:
                    # This player definitely doesn't have this card
                    # Mark as "not p" — implement via process of elimination
                    self._eliminate(card, p)
    
    def _eliminate(self, card: str, player: int):
        """Card is definitely NOT held by player."""
        # Check remaining possible holders for this card
        possible = self._possible_holders(card)
        possible.discard(player)
        
        if len(possible) == 1:
            holder = next(iter(possible))
            self._set_known(card, holder)
        elif len(possible) == 0:
            raise ValueError(f"Contradiction: no valid holder for {card}")
    
    def _possible_holders(self, card: str) -> Set:
        """All entities that could still hold this card."""
        # Holders: players 0..n-1 plus 'envelope'
        all_holders = set(range(self.gs.n_players)) | {'envelope'}
        if self.known[card] is not None:
            return {self.known[card]}
        return all_holders  # simplified; track eliminations in production
    
    def _propagate(self):
        """
        Arc-consistency propagation:
        Re-check OR constraints with updated knowledge.
        """
        changed = True
        while changed:
            changed = False
            new_constraints = []
            for (cards_set, player) in self.or_constraints:
                # Remove cards we now know are elsewhere
                remaining = frozenset(
                    c for c in cards_set
                    if self.known.get(c) is None  # still unknown
                    or self.known.get(c) == player  # assigned to this player
                )
                
                if len(remaining) == 0:
                    # Someone else has all these cards — impossible! 
                    # (In practice means no card was refuted — handle upstream)
                    continue
                elif len(remaining) == 1:
                    # Forced: player must hold this card
                    card = next(iter(remaining))
                    if self.known[card] is None:
                        self._set_known(card, player)
                        changed = True
                else:
                    new_constraints.append((remaining, player))
            
            self.or_constraints = new_constraints
    
    def certain_solution(self) -> Optional[tuple]:
        """Returns (suspect, weapon, room) if all three are proven."""
        s = next((c for c in SUSPECTS if self.known[c] == 'envelope'), None)
        w = next((c for c in WEAPONS  if self.known[c] == 'envelope'), None)
        r = next((c for c in ROOMS    if self.known[c] == 'envelope'), None)
        if s and w and r:
            return (s, w, r)
        return None
