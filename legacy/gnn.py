"""
Legacy card-player graph neural network. DEFERRED -- torch-geometric dependency,
and not one of the six methods.

Extracted from the claude.ai chat "Machine learning for Clue game in Python".
Code below the header is as it appeared in that chat; only this docstring and
the local imports were added. Requires torch + torch-geometric.
"""
# pip install torch-geometric

import torch
import torch.nn as nn
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv, global_mean_pool

from .domain import SUSPECTS, WEAPONS, ALL_CARDS
from .belief_tracker import BayesianBeliefTracker

class ClueGNN(nn.Module):
    """
    Model the Clue game state as a bipartite graph:
      - Nodes: cards (21) + players (n) + envelope (1)
      - Edges: possible "held-by" relationships, weighted by belief probability
    
    Learns richer representations than a flat MLP.
    Particularly useful for generalizing across different player counts.
    """
    
    def __init__(self, n_players: int, hidden: int = 64, out_dim: int = 32):
        super().__init__()
        n_card_types = 3  # suspect=0, weapon=1, room=2
        n_holder_types = 2  # player=0, envelope=1
        
        # Node features:
        # Cards: [type_onehot(3), is_mine(1), belief_in_envelope(1)] → 5 dims
        # Holders: [type_onehot(2), player_index_norm(1)]            → 3 dims
        # We'll pad to the same dim with zeros
        node_feat_dim = 5
        
        self.conv1 = GCNConv(node_feat_dim, hidden)
        self.conv2 = GCNConv(hidden, hidden)
        self.out   = nn.Linear(hidden, out_dim)
    
    def build_graph(self, tracker: BayesianBeliefTracker) -> Data:
        """Convert belief matrix to a PyG graph."""
        n_cards   = 21
        n_holders = tracker.n_holders  # players + 1 (envelope)
        n_nodes   = n_cards + n_holders
        
        # Node features (simplified)
        x = torch.zeros(n_nodes, 5)
        # Card type encoding
        for i, card in enumerate(ALL_CARDS):
            if card in SUSPECTS: x[i, 0] = 1.0
            elif card in WEAPONS: x[i, 1] = 1.0
            else: x[i, 2] = 1.0
            x[i, 3] = 1.0 if card in tracker.gs.my_cards else 0.0
            x[i, 4] = tracker.belief[i, 0]  # P(in envelope)
        
        # Holder features
        for h in range(n_holders):
            x[n_cards + h, 3] = 1.0 if h == 0 else 0.0  # is_envelope
            x[n_cards + h, 4] = h / n_holders  # normalized index
        
        # Edges: card → holder when belief > threshold
        edges = []
        weights = []
        threshold = 0.05
        for ci in range(n_cards):
            for hi in range(n_holders):
                if tracker.belief[ci, hi] > threshold:
                    edges.append([ci, n_cards + hi])
                    weights.append(tracker.belief[ci, hi])
        
        edge_index = torch.LongTensor(edges).T
        edge_attr  = torch.FloatTensor(weights).unsqueeze(1)
        
        return Data(x=x, edge_index=edge_index, edge_attr=edge_attr)
    
    def forward(self, data: Data) -> torch.Tensor:
        x = torch.relu(self.conv1(data.x, data.edge_index))
        x = torch.relu(self.conv2(x, data.edge_index))
        # Global pool over card nodes only
        return self.out(x[:21].mean(dim=0))  # card embedding
