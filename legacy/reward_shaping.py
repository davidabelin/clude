"""
Legacy reward shaper for RL training. DEFERRED with the DQN.

Extracted from the claude.ai chat "Machine learning for Clue game in Python".
Code below the header is as it appeared in that chat; only this docstring and
the local imports were added. Status and known issues: see legacy/README.md.
"""
import numpy as np

from .domain import SUSPECTS, WEAPONS, ROOMS, Suggestion
from .belief_tracker import BayesianBeliefTracker

class ClueRewardShaper:
    """
    Dense reward signal to accelerate RL training.
    
    The core challenge: in a 4-player game with ~20 turns, 
    a reward only at game-end means ~1/4 win rate with a random policy.
    Shaped rewards provide signal every turn.
    """
    
    def __init__(self, entropy_weight: float = 0.3, 
                       win_bonus: float = 10.0,
                       lose_penalty: float = -5.0):
        self.entropy_weight = entropy_weight
        self.win_bonus      = win_bonus
        self.lose_penalty   = lose_penalty
        self.prev_entropy   = None
    
    def step_reward(self, 
                    tracker: BayesianBeliefTracker,
                    suggestion: Suggestion,
                    won: bool = False,
                    lost: bool = False,
                    made_accusation: bool = False) -> float:
        """Compute shaped reward for one turn."""
        r = 0.0
        
        # Terminal rewards
        if won:
            return self.win_bonus
        if lost:
            return self.lose_penalty
        
        # Information gain reward
        current_entropy = self._solution_entropy(tracker)
        if self.prev_entropy is not None:
            entropy_reduction = self.prev_entropy - current_entropy
            r += self.entropy_weight * entropy_reduction
        self.prev_entropy = current_entropy
        
        # Bonus for eliminating a card (a certainty jump)
        env = tracker.envelope_probabilities()
        certain_envelope = sum(1 for v in env.values() if v > 0.95)
        r += certain_envelope * 0.1
        
        # Penalty for accusation without certainty (high risk move)
        if made_accusation:
            is_certain = tracker.is_solution_known(threshold=0.95)
            if not is_certain:
                r -= 3.0  # risky accusation
        
        # Small per-turn penalty to encourage speed
        r -= 0.01
        
        return r
    
    def _solution_entropy(self, tracker: BayesianBeliefTracker) -> float:
        env = tracker.envelope_probabilities()
        def H(cards):
            p = np.array([env[c] for c in cards])
            p = p / p.sum()
            p = np.clip(p, 1e-10, 1.0)
            return -np.sum(p * np.log2(p))
        return H(SUSPECTS) + H(WEAPONS) + H(ROOMS)
