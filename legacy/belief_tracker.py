"""
Legacy Bayesian belief tracker (marginal card x holder matrix).

Extracted from the claude.ai chat "Machine learning for Clue game in Python".
Code below the header is as it appeared in that chat; only this docstring and
the domain import were added. Status and known issues: see legacy/README.md.

Planned fate: demoted to Scarlett's (naive Bayes) approximate method.
"""
import numpy as np
from itertools import product

from .domain import SUSPECTS, WEAPONS, ROOMS, ALL_CARDS, GameState, Suggestion

class BayesianBeliefTracker:
    """
    Maintains a probability distribution over who holds each card.
    
    belief[c, p] = P(player p holds card c)
    where p=0 is "the solution envelope" (murder envelope).
    """
    
    def __init__(self, game_state: GameState):
        self.gs = game_state
        n = game_state.n_players
        self.n_holders = n + 1  # players + envelope
        self.cards = ALL_CARDS
        self.n_cards = len(self.cards)
        self.card_idx = {c: i for i, c in enumerate(self.cards)}
        
        # Uniform prior: shape (n_cards, n_holders)
        # holders: [envelope, player_0, player_1, ..., player_n-1]
        self.belief = np.ones((self.n_cards, self.n_holders))
        
        # Apply hard knowledge: my own cards
        self._apply_own_cards()
    
    def _apply_own_cards(self):
        """Cards I hold are definitely mine, definitely not elsewhere."""
        me = self.gs.my_index + 1  # +1 because holder 0 = envelope
        for card in self.gs.my_cards:
            ci = self.card_idx[card]
            self.belief[ci, :] = 0.0
            self.belief[ci, me] = 1.0
        self._normalize()
    
    def _normalize(self):
        """Each card must be held by exactly one entity."""
        row_sums = self.belief.sum(axis=1, keepdims=True)
        # Avoid divide-by-zero (should never happen in valid game)
        row_sums = np.where(row_sums == 0, 1, row_sums)
        self.belief /= row_sums
    
    def update_from_suggestion(self, suggestion: Suggestion):
        """
        Core Bayesian update step.
        
        Cases:
          - Nobody refuted: all three cards are in the envelope or with players
            who were skipped. Strong evidence.
          - Player p refuted: p holds at least one of {suspect, weapon, room}.
          - We saw the card: exact hard update.
        """
        s_cards = [suggestion.suspect, suggestion.weapon, suggestion.room]
        s_indices = [self.card_idx[c] for c in s_cards]
        
        if suggestion.refuter is None:
            # No one refuted — each of the 3 cards is either mine or in envelope
            # (players who were asked and skipped definitely don't have them)
            skipped = self._get_skipped_players(suggestion)
            for ci in s_indices:
                for p in skipped:
                    holder_idx = p + 1
                    self.belief[ci, holder_idx] = 0.0
        else:
            refuter_holder = suggestion.refuter + 1
            
            if suggestion.refuter == self.gs.my_index:
                # We're the refuter — we know exactly which card we showed
                # (this is handled by my_cards, already zeroed)
                pass
            elif suggestion.shown_to == self.gs.my_index:
                # We saw the card shown — hard update for that specific card
                # (caller should pass the actual card seen separately)
                pass
            else:
                # Soft update: refuter holds AT LEAST ONE of the three cards
                # Bayesian: increase belief for refuter on those cards
                # (this is a likelihood update, not a hard constraint)
                self._soft_update_refuter(s_indices, refuter_holder)
        
        self._normalize()
    
    def _soft_update_refuter(self, card_indices, refuter_holder):
        """
        Soft Bayesian update when we know player `refuter_holder` 
        holds at least one of the cards in `card_indices`.
        
        P(refuter holds card_i | refuter showed one card) is proportional
        to the prior probability that refuter holds card_i.
        """
        # Boost the refuter's probability on all three cards proportionally
        boost_factor = 1.5  # tunable; reflects "likely they have one"
        for ci in card_indices:
            if self.belief[ci, refuter_holder] > 0:
                self.belief[ci, refuter_holder] *= boost_factor
    
    def _get_skipped_players(self, suggestion: Suggestion) -> list:
        """Players who were asked and couldn't refute."""
        skipped = []
        n = self.gs.n_players
        p = (suggestion.suggester + 1) % n
        while p != suggestion.suggester:
            if suggestion.refuter is None or p != suggestion.refuter:
                skipped.append(p)
            if suggestion.refuter is not None and p == suggestion.refuter:
                break
            p = (p + 1) % n
        return skipped
    
    def mark_card_seen(self, card: str, holder: int):
        """Hard update when we're shown a specific card."""
        ci = self.card_idx[card]
        self.belief[ci, :] = 0.0
        self.belief[ci, holder + 1] = 1.0
        self._normalize()
    
    def envelope_probabilities(self) -> dict[str, float]:
        """P(card is in the murder envelope) for all cards."""
        return {card: self.belief[i, 0] 
                for i, card in enumerate(self.cards)}
    
    def most_likely_solution(self) -> tuple[str, str, str]:
        """Returns (suspect, weapon, room) with highest envelope probability."""
        env_probs = self.envelope_probabilities()
        best_s = max(SUSPECTS, key=lambda c: env_probs[c])
        best_w = max(WEAPONS,  key=lambda c: env_probs[c])
        best_r = max(ROOMS,    key=lambda c: env_probs[c])
        return best_s, best_w, best_r
    
    def is_solution_known(self, threshold=0.99) -> bool:
        """True if we're confident about all three solution cards."""
        env = self.envelope_probabilities()
        s_conf = max(env[c] for c in SUSPECTS) >= threshold
        w_conf = max(env[c] for c in WEAPONS)  >= threshold
        r_conf = max(env[c] for c in ROOMS)    >= threshold
        return s_conf and w_conf and r_conf
