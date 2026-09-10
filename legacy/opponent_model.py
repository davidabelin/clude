"""
Legacy opponent model (suggestion-history heuristics).

Extracted from the claude.ai chat "Machine learning for Clue game in Python".
Code below the header is as it appeared in that chat; only this docstring and
the local imports were added. Status and known issues: see legacy/README.md.

Planned fate: starting point for White's Markov / behavioral model.
"""
from typing import Dict, List

from .domain import ALL_CARDS, Suggestion

class OpponentModel:
    """
    Tracks what each opponent likely knows, so we can:
    1. Avoid suggestions that reveal our knowledge to dangerous opponents.
    2. Infer which cards an opponent has based on their suggestion patterns.
    """
    
    def __init__(self, n_players: int):
        self.n_players = n_players
        # estimated_knowledge[p][card] = P(player p knows where card c is)
        self.estimated_knowledge = {
            p: {c: 0.0 for c in ALL_CARDS}
            for p in range(n_players)
        }
        # Track suggestion history per player
        self.suggestion_history: Dict[int, List[Suggestion]] = {
            p: [] for p in range(n_players)
        }
    
    def observe_suggestion(self, suggestion: Suggestion):
        """
        A player's suggestion reveals their uncertainty:
        - Including cards you know they HAVE → they're fishing for others.
        - Including only cards they've seen → they're being strategic.
        - Making the same suggestion twice → they're stuck / bluffing.
        """
        p = suggestion.suggester
        self.suggestion_history[p].append(suggestion)
        
        # Heuristic: if a player suggests the same card multiple times,
        # they likely DON'T have it (otherwise they'd know to stop)
        card_counts = {}
        for sug in self.suggestion_history[p]:
            for card in [sug.suspect, sug.weapon, sug.room]:
                card_counts[card] = card_counts.get(card, 0) + 1
        
        for card, count in card_counts.items():
            # Repeated suggestions about a card → probably don't hold it
            if count >= 2:
                self.estimated_knowledge[p][card] = min(
                    0.9, self.estimated_knowledge[p][card] + 0.2
                )
    
    def danger_score(self, player: int) -> float:
        """
        How close is this player to solving the game?
        High danger → avoid suggestions they'd benefit from.
        """
        # Player is dangerous if they have high knowledge about many cards
        known_count = sum(
            1 for v in self.estimated_knowledge[player].values() if v > 0.7
        )
        return known_count / len(ALL_CARDS)
    
    def safe_to_suggest(self, suspect: str, weapon: str, room: str,
                        min_refutation_probability: float = 0.3) -> bool:
        """
        Is this suggestion 'safe' — i.e., unlikely to be refuted by 
        a dangerous player who would learn too much from the pattern?
        """
        # Simplified: check if the most dangerous opponent can refute
        most_dangerous = max(
            range(self.n_players),
            key=lambda p: self.danger_score(p)
        )
        danger = self.danger_score(most_dangerous)
        return danger < 0.6  # threshold: don't help players close to winning
