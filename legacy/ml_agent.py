"""
Legacy all-in-one agent (the old chat's "one strong agent" design).

Extracted from the claude.ai chat "Machine learning for Clue game in Python".
Code below the header is as it appeared in that chat; only this docstring and
the local imports were added. Requires torch (via dqn.py).

Kept as a reference for how the pieces were wired together. clude replaces
this with six distinct agents behind a shared protocol -- see CLAUDE.md.
"""
from .domain import ROOMS, GameState, Suggestion
from .belief_tracker import BayesianBeliefTracker
from .constraints import ConstraintPropagator
from .info_agent import InformationAgent
from .opponent_model import OpponentModel
from .reward_shaping import ClueRewardShaper
from .dqn import DQNAgent, encode_state, state_dim, N_ACTIONS

class ClueMLAgent:
    """
    Production-grade Clue agent combining:
    - Bayesian belief tracking (for probabilities)
    - Constraint propagation (for hard deductions)
    - Information-theoretic suggestion selection
    - DQN policy (for high-level strategy)
    - Opponent modelling (for competitive play)
    """
    
    def __init__(self, game_state: GameState, cards_per_player: int):
        self.gs = game_state
        n_players = game_state.n_players
        
        # Core reasoning engine
        self.tracker    = BayesianBeliefTracker(game_state)
        self.constraint = ConstraintPropagator(game_state, cards_per_player)
        self.info_agent = InformationAgent(self.tracker)
        self.opp_model  = OpponentModel(n_players)
        self.reward_shaper = ClueRewardShaper()
        
        # RL policy (loaded from checkpoint or freshly initialized)
        s_dim = state_dim(n_players)
        self.rl_agent = DQNAgent(s_dim, N_ACTIONS)
        
    def observe(self, suggestion: Suggestion, shown_card: str = None):
        """Process a game event."""
        # 1. Update hard constraints
        if suggestion.refuter is not None:
            self.constraint.add_refutation_constraint(
                suggestion.refuter,
                (suggestion.suspect, suggestion.weapon, suggestion.room)
            )
        else:
            # No refutation: strong constraint on envelope
            pass
        
        # 2. Update probabilistic beliefs
        self.tracker.update_from_suggestion(suggestion)
        
        # 3. If we were shown a card, hard-update
        if shown_card is not None:
            self.tracker.mark_card_seen(shown_card, suggestion.refuter)
            self.constraint._set_known(shown_card, suggestion.refuter)
        
        # 4. Update opponent model
        self.opp_model.observe_suggestion(suggestion)
    
    def choose_action(self, current_room: str) -> tuple:
        """
        Decide: suggest or accuse? If suggest, what?
        
        Decision hierarchy:
        1. If solution is certain → accuse immediately.
        2. If RL policy selects "accuse" with high confidence → accuse.
        3. Otherwise → use information-theoretic suggestion.
        """
        # Check for certain solution (deterministic win condition)
        certain = self.constraint.certain_solution()
        if certain:
            return ("ACCUSE", *certain)
        
        if self.tracker.is_solution_known(threshold=0.98):
            return ("ACCUSE", *self.tracker.most_likely_solution())
        
        # Get RL state encoding
        room_idx = ROOMS.index(current_room)
        state = encode_state(self.tracker, room_idx, self.gs.n_players)
        
        # RL picks the suggestion pair
        legal = list(range(N_ACTIONS))
        action_idx = self.rl_agent.act(state, legal)
        
        if action_idx == N_ACTIONS - 1:
            # RL says accuse — only do it if probability is high enough
            sol = self.tracker.most_likely_solution()
            env = self.tracker.envelope_probabilities()
            confidence = min(env[sol[0]], env[sol[1]], env[sol[2]])
            if confidence > 0.85:
                return ("ACCUSE", *sol)
        
        # Fall back to info-theoretic suggestion
        suspect, weapon, room = self.info_agent.best_suggestion(current_room)
        return ("SUGGEST", suspect, weapon, room)
