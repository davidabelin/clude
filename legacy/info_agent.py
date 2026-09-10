"""
Legacy information-theoretic suggestion chooser.

Extracted from the claude.ai chat "Machine learning for Clue game in Python".
Code below the header is as it appeared in that chat; only this docstring and
the local imports were added. Status and known issues: see legacy/README.md.
"""
import math
import numpy as np
from scipy.stats import entropy as scipy_entropy

from .domain import SUSPECTS, WEAPONS, ROOMS
from .belief_tracker import BayesianBeliefTracker

class InformationAgent:
    """
    Chooses suggestions to maximize expected reduction in uncertainty
    about the solution (measured in bits of entropy).
    """
    
    def __init__(self, tracker: BayesianBeliefTracker):
        self.tracker = tracker
    
    def _solution_entropy(self) -> float:
        """
        Current uncertainty about the solution in bits.
        H(solution) = H(suspect) + H(weapon) + H(room)  [approximately]
        """
        env = self.tracker.envelope_probabilities()
        
        def category_entropy(cards):
            probs = np.array([env[c] for c in cards])
            probs = probs / probs.sum()  # renormalize
            # Clip to avoid log(0)
            probs = np.clip(probs, 1e-10, 1.0)
            return -np.sum(probs * np.log2(probs))
        
        return (category_entropy(SUSPECTS) + 
                category_entropy(WEAPONS) + 
                category_entropy(ROOMS))
    
    def _expected_info_gain(self, suspect: str, weapon: str, room: str) -> float:
        """
        Simulate all possible outcomes of suggesting (s, w, r) and compute
        the expected reduction in entropy.
        
        E[IG] = H_current - E[H_after]
              = sum_outcome P(outcome) * H(solution | outcome)
        """
        current_H = self._solution_entropy()
        
        # Outcomes: each player might refute, or no one refutes
        # For each outcome, we'd do a Bayesian update and recompute entropy
        # This is expensive in full generality; here's an approximation:
        
        suggested_cards = [suspect, weapon, room]
        env = self.tracker.envelope_probabilities()
        
        # P(no refutation) — all three cards are in envelope
        p_in_envelope = np.prod([env[c] for c in suggested_cards])
        
        # P(refutation from player p) — at least one card is with p
        p_refuted_by = []
        for p in range(self.tracker.gs.n_players):
            if p == self.tracker.gs.my_index:
                continue
            holder = p + 1
            p_p_has_any = 1 - np.prod([
                1 - self.tracker.belief[self.tracker.card_idx[c], holder]
                for c in suggested_cards
            ])
            p_refuted_by.append((p, p_p_has_any))
        
        # Approximate: if no one can refute, we gain ~1.5 bits
        # If someone refutes, we gain info proportional to specificity
        # (In production: simulate the actual Bayesian update for each outcome)
        
        gain_no_refute  = p_in_envelope * 2.0   # strong signal
        gain_refutation = sum(p * 0.8 for _, p in p_refuted_by)  # soft signal
        
        return gain_no_refute + gain_refutation
    
    def best_suggestion(self, current_room: str) -> tuple[str, str, str]:
        """
        Find the (suspect, weapon) pair with highest expected info gain.
        Room is constrained to current room in Clue.
        """
        best_gain = -1.0
        best = (SUSPECTS[0], WEAPONS[0], current_room)
        
        # In production, use smarter search; here we check unknown cards only
        candidate_suspects = [s for s in SUSPECTS 
                               if self.tracker.envelope_probabilities()[s] > 0.01]
        candidate_weapons  = [w for w in WEAPONS  
                               if self.tracker.envelope_probabilities()[w] > 0.01]
        
        for suspect in candidate_suspects:
            for weapon in candidate_weapons:
                gain = self._expected_info_gain(suspect, weapon, current_room)
                if gain > best_gain:
                    best_gain = gain
                    best = (suspect, weapon, current_room)
        
        return best
