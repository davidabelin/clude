"""
Legacy Dueling DQN + prioritized replay. DEFERRED -- not one of the six methods.

Extracted from the claude.ai chat "Machine learning for Clue game in Python".
Code below the header is as it appeared in that chat; only this docstring and
the local imports were added. Requires torch. Status: see legacy/README.md.
"""
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import random

from .belief_tracker import BayesianBeliefTracker

# --- State Encoding ---

def encode_state(tracker: BayesianBeliefTracker, 
                 current_room_idx: int,
                 n_players: int) -> torch.Tensor:
    """
    Flatten belief matrix + room position + game metadata into a fixed vector.
    
    Dimensions:
      - belief matrix: 21 cards × (n_players + 1) holders  → 21*(n+1) floats
      - current room:  one-hot over 9 rooms                 → 9 floats
      - turn count:    normalized                           → 1 float
    """
    belief_flat = tracker.belief.flatten().astype(np.float32)
    
    room_onehot = np.zeros(9, dtype=np.float32)
    room_onehot[current_room_idx] = 1.0
    
    return torch.FloatTensor(
        np.concatenate([belief_flat, room_onehot])
    )

def state_dim(n_players: int) -> int:
    return 21 * (n_players + 1) + 9

# --- Action Space ---
# Simplified: pick (suspect_idx, weapon_idx) — room fixed by position
# Or make accusation (bool). Full action count:
ACTION_SUGGEST = [(s, w) for s in range(6) for w in range(6)]  # 36
ACTION_ACCUSE  = [(s, w, r) for s in range(6) for w in range(6) for r in range(9)]  # 324

N_ACTIONS = len(ACTION_SUGGEST) + 1  # 37 (36 suggestions + 1 "accuse best guess")

# --- Neural Network ---

class ClueQNetwork(nn.Module):
    """
    Dueling DQN architecture: separate value and advantage streams.
    Dueling works well for Clue because the value of a state is 
    largely independent of which specific suggestion you make.
    """
    
    def __init__(self, state_dim: int, n_actions: int, hidden: int = 256):
        super().__init__()
        
        self.shared = nn.Sequential(
            nn.Linear(state_dim, hidden),
            nn.LayerNorm(hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.LayerNorm(hidden),
            nn.ReLU(),
        )
        
        # Value stream: V(s)
        self.value_head = nn.Sequential(
            nn.Linear(hidden, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
        )
        
        # Advantage stream: A(s, a)
        self.advantage_head = nn.Sequential(
            nn.Linear(hidden, 128),
            nn.ReLU(),
            nn.Linear(128, n_actions),
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        shared = self.shared(x)
        value  = self.value_head(shared)
        adv    = self.advantage_head(shared)
        # Q(s,a) = V(s) + A(s,a) - mean(A(s,:))
        return value + adv - adv.mean(dim=-1, keepdim=True)

# --- Replay Buffer ---

class PrioritizedReplayBuffer:
    """
    Prioritized experience replay — important for Clue because 
    winning/accusing episodes are rare and extremely informative.
    """
    
    def __init__(self, capacity: int = 50_000, alpha: float = 0.6):
        self.capacity = capacity
        self.alpha = alpha
        self.buffer = []
        self.priorities = np.zeros(capacity, dtype=np.float32)
        self.pos = 0
    
    def push(self, state, action, reward, next_state, done):
        max_priority = self.priorities.max() if self.buffer else 1.0
        
        if len(self.buffer) < self.capacity:
            self.buffer.append((state, action, reward, next_state, done))
        else:
            self.buffer[self.pos] = (state, action, reward, next_state, done)
        
        self.priorities[self.pos] = max_priority
        self.pos = (self.pos + 1) % self.capacity
    
    def sample(self, batch_size: int, beta: float = 0.4):
        n = len(self.buffer)
        priorities = self.priorities[:n]
        probs = priorities ** self.alpha
        probs /= probs.sum()
        
        indices = np.random.choice(n, batch_size, p=probs, replace=False)
        weights = (n * probs[indices]) ** (-beta)
        weights /= weights.max()
        
        batch = [self.buffer[i] for i in indices]
        states, actions, rewards, next_states, dones = zip(*batch)
        
        return (
            torch.stack(states),
            torch.LongTensor(actions),
            torch.FloatTensor(rewards),
            torch.stack(next_states),
            torch.FloatTensor(dones),
            indices,
            torch.FloatTensor(weights),
        )
    
    def update_priorities(self, indices, priorities):
        for idx, priority in zip(indices, priorities):
            self.priorities[idx] = priority + 1e-5  # small epsilon

# --- DQN Training Loop ---

class DQNAgent:
    def __init__(self, state_dim: int, n_actions: int, lr: float = 3e-4):
        self.n_actions = n_actions
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.q_net     = ClueQNetwork(state_dim, n_actions).to(self.device)
        self.target_net = ClueQNetwork(state_dim, n_actions).to(self.device)
        self.target_net.load_state_dict(self.q_net.state_dict())
        
        self.optimizer = optim.Adam(self.q_net.parameters(), lr=lr)
        self.buffer = PrioritizedReplayBuffer()
        
        self.gamma   = 0.99
        self.epsilon = 1.0
        self.eps_min = 0.05
        self.eps_decay = 0.995
        self.steps   = 0
        self.target_update_freq = 500  # steps
    
    def act(self, state: torch.Tensor, legal_actions: list) -> int:
        if random.random() < self.epsilon:
            return random.choice(legal_actions)
        
        with torch.no_grad():
            q_values = self.q_net(state.unsqueeze(0).to(self.device))
        
        # Mask illegal actions with -inf
        mask = torch.full((self.n_actions,), -1e9)
        for a in legal_actions:
            mask[a] = 0
        q_masked = q_values.squeeze() + mask.to(self.device)
        
        return q_masked.argmax().item()
    
    def train_step(self, batch_size: int = 64):
        if len(self.buffer.buffer) < batch_size:
            return None
        
        states, actions, rewards, next_states, dones, indices, weights = \
            self.buffer.sample(batch_size)
        
        states      = states.to(self.device)
        next_states = next_states.to(self.device)
        actions     = actions.to(self.device)
        rewards     = rewards.to(self.device)
        dones       = dones.to(self.device)
        weights     = weights.to(self.device)
        
        # Current Q-values
        current_q = self.q_net(states).gather(1, actions.unsqueeze(1)).squeeze()
        
        # Double DQN target: action selected by online net, evaluated by target
        with torch.no_grad():
            next_actions = self.q_net(next_states).argmax(dim=1, keepdim=True)
            next_q = self.target_net(next_states).gather(1, next_actions).squeeze()
            target_q = rewards + self.gamma * next_q * (1 - dones)
        
        # Weighted Huber loss (for prioritized replay)
        loss = (weights * nn.functional.huber_loss(
            current_q, target_q, reduction='none'
        )).mean()
        
        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.q_net.parameters(), 10.0)
        self.optimizer.step()
        
        # Update priorities
        td_errors = (current_q - target_q).detach().abs().cpu().numpy()
        self.buffer.update_priorities(indices, td_errors)
        
        # Decay epsilon
        self.epsilon = max(self.eps_min, self.epsilon * self.eps_decay)
        self.steps  += 1
        
        # Sync target network
        if self.steps % self.target_update_freq == 0:
            self.target_net.load_state_dict(self.q_net.state_dict())
        
        return loss.item()
