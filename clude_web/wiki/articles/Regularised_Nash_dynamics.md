---
title: Regularised Nash dynamics
short: Professor Plum's method since Phase 12: a network trained by self-play over the deduction floor
categories: Methods
redirects: R-NaD, RNaD, Regularized Nash dynamics, Plum's method, Policy network, Plum's network, NeuRD
dyk: ... that [[Professor Plum]]'s network has {{code:net.params}} weights and answers in under a millisecond, where the count it replaced took {{fact:bench.policy.PlumOG.ms}} ms?
dyk: ... that a network trained on a few hundred games' envelopes memorised them and scored a halfway log-loss of {{fact:policy.smoke.memorise}}, far worse than knowing nothing, until it was given a replay buffer?
---
{{infobox
title: Regularised Nash dynamics
figure: plum-network
caption: Plum's network: a trunk, four heads and a move scorer
Played by | [[Professor Plum]], since 5 October 2026
In a phrase | A learned estimate and a learned way of moving and asking, over the floor
Module | `deep_nash.py`, trained by `train_plum.py`
Evidence used | Everything the [[deduction floor]] knows, and who has named which cards
Weights | {{code:net.params}}, one file
Cost | About {{fact:bench.policy.Plum.ms}} ms a call
= Training
Games | {{fact:policy.run.games}} a run, two runs
Opponents | Half the games itself; half the other characters and the [[floor player]]
}}

**Regularised Nash dynamics** (R-NaD) is the learning method behind [[Professor Plum]]'s play since Phase 12. A small [[w:Artificial neural network|neural network]] reads the position the [[deduction floor]] has established and gives three kinds of answer: a [[belief]] about which cards are in [[the envelope]], scores for where to move and what to ask, and an estimate of how the game is going. The network learnt these by playing tens of thousands of games, against itself and against the other characters, with a training rule adapted from DeepNash, the system that learnt to play [[w:Stratego|Stratego]].[^paper][^plan]

It replaced [[exact posterior enumeration]], the method Plum played by until 5 October 2026, now kept as **PlumOG**. The count was exact when it could finish, but on the [[Classic board]] most mid-game positions were too large to count, and its sampled fallback did worse than knowing nothing at the halfway point. The network does not count anything. It estimates, and on the same benchmark positions its estimates are the best of any method from the start of a game to the halfway mark, at about a thousandth of the cost.[^bench]

The name describes the training, not the play. *Nash dynamics* are learning rules that move a policy towards a [[w:Nash equilibrium|Nash equilibrium]], the point where no player gains by changing strategy alone; *regularised* means each update is pulled gently back towards a recent copy of the policy, which keeps the learning from circling. The guarantee belongs to two-player [[w:Zero-sum game|zero-sum]] games. Clue has three to six players racing for one envelope, so here the method is a well-behaved way to train, not a proof that Plum plays an equilibrium.[^paper][^plan]

## At the table

A turn of Plum's runs through the network once. The [[deduction floor]] first settles what is certain; the network then reads the floor's state as {{code:net.state}} numbers and answers everything Plum needs from one pass.

!!! example "Worked example: the Rope question"
    The method articles share one small position, the [[Belief#At the table|Rope question]]. Late in a three-handed game, every card is placed except four: of the suspects, **Mrs. White** or **Mrs. Peacock** is in the envelope; of the weapons, the **Rope** or the **Wrench**. [[Mr. Green]] suggests *Mrs. Peacock, with the Rope, in the Hall*, and [[Colonel Mustard]] shows him a card the viewer does not see. Mustard holds at least one of Peacock and the Rope, and counting the deals that remain gives Mrs. White {{code:example.plum.White}}.

    The network gives Mrs. White **{{code:example.policy.White}}** and Mrs. Peacock {{code:example.policy.Peacock}}. It has the direction backwards. Its inputs include how often each card has been named and by how many players. In the games it learnt from, it seems, a card that players keep naming tends to be in the envelope, and here that habit outweighs the one disproof, which points the other way. On the [[bandit ensemble|Mr. Green's]] scoring of this position it is the worst of his five arms.

    The example is one position, chosen for being small enough to count by hand, and the network was never trained on positions built that way. On a thousand positions from real games its estimates beat every other method's by halfway (below). It is still a fair warning: an estimate learnt from games carries the habits of those games, and a position that breaks them can fool it in a way a count cannot be fooled.

## How it works

### What the network reads

For each of the 21 cards, the network is given {{code:net.card_features}} numbers: where the floor says the card could still be, seat by seat counted round the table from Plum, and the envelope; whether it has been resolved; how many open facts mention it; how many times it has been named in [[suggestion|suggestions]], how often without anyone disproving, by how many different players; and whether it is in Plum's own hand. Then three numbers for each seat (in the game, hand size, present) and two for the game (how far it has run, how many players). That is {{code:net.state}} numbers in all.[^module]

### What it answers

{{figure:plum-network|The network as `deep_nash.py` lays it out. The trunk turns the floor's {{code:net.state}} numbers into {{code:net.hidden}}; four heads read them, and a separate scorer reads them beside each legal move.}}

The numbers pass through a *trunk* of two layers of {{code:net.hidden}} units. Four *heads* read the trunk's output:

- **belief**: one score per card, turned into probabilities within each category ([[softmax and temperature|softmax]]) *after* the floor's mask, so a card the floor has ruled out is exactly 0 and a proven one exactly 1. This is Plum's [[belief]], read by the accusation test, the [[the certainty tag|certainty tag]], his notes and [[Mr. Green]]'s Plum arm.
- **suspect** and **weapon**: scores for which honest card to name in a suggestion, over the cards he does not hold.
- **value**: a single number, the network's estimate of how this game will end for him, from −1 (put out) to +1 (won).

Movement needs a different shape, because the number of legal moves changes from turn to turn. A *move scorer* takes the trunk's {{code:net.hidden}} numbers together with {{code:net.choice}} describing one move (the room it aims at and the room it lands in, how far it still has to go, whether it is a walk, a secret passage or a stay, and the same information and proximity numbers every character's movement reads) and gives that move one score. It runs once per legal move, and the scores become a distribution over the moves.[^module]

!!! algorithm "One of Plum's decisions"
        Input: the floor's state for Plum's seat; the legal options
        x ← encode(state)                            (the floor, as numbers)
        h ← relu(W2 · relu(W1 · x + b1) + b2)        (the trunk)
        belief ← softmax within each category of mask(Wbelief · h)
        if the decision is a move:
            for each legal move m:  score(m) ← w · relu(Wm · [h ; features(m)])
            choose a move by softmax of the scores at Plum's temperature
        if the decision is a suggestion:
            with probability bluff_rate: name a card of his own   (the Character's dial)
            else choose from the suspect (weapon) head's scores at his temperature
        if the decision is whether to accuse:
            accuse if P(best triple) under belief ≥ accuse_threshold   (the Character's test)

### What stays with the character

The network owns the belief, the destination and the honest suggestion cards. Everything else is the [[personality dials]], applied exactly as for the other five characters: the coin flip for a [[bluffing|bluff]] comes first; the accusation test compares the belief's best triple with his [[accusation threshold]]; which card to show is [[secrecy]]'s decision. One dial lost its meaning: [[curiosity]], which weighs a far room against a near one, does not enter the network's move scores, so for Plum it is inert.[^dials]

When a model plays his seat, its menus are built from the same scores the network plays by, so the [[leash]] measures distance from the network's own preference and the headless pick is always the menu's first option.[^seams]

## Training

### The rule

{{figure:plum-training-loop|One iteration of Plum's training, and the checkpoints around it.}}

Training repeats one cycle. A batch of 512 games is played through the real engine, with every network seat drawing its moves and suggestions from the network's own distributions. Each seat's record of the game (the states it saw, what it chose, and how the game ended) then drives four corrections at once:[^script]

- **The policy** moves towards choices that went better than the value head expected. DeepNash's version of this, *neural replicator dynamics* (NeuRD), pushes on the chosen option's raw score rather than its probability, which keeps a rarely-chosen option from being starved of correction; and a score already far ahead of the others is not pushed further, which stops the policy collapsing onto one option.
- **The reward is regularised.** Each step's reward is reduced by how far the policy has moved from a *reference* copy of itself, refreshed every few iterations. This is the regularisation in the name:

$$ \tilde r_t = r_t - \eta \,\log \frac{\pi(a_t \mid s_t)}{\pi_{\text{ref}}(a_t \mid s_t)} $$

- **The value head** is fitted to the regularised return, so that it can say what "better than expected" means.
- **The belief head** is fitted to the envelope that turned out to be true, by [[log-loss]] in each category:

$$ L_{\text{belief}} = -\sum_{k \in \{S,\, W,\, R\}} \log p_k(e_k) $$

where $e_k$ is the true card of category $k$ and $p_k$ the belief head's masked probabilities. The four terms are added, with a small bonus for keeping the policy uncertain, and one step of gradient descent is taken.

!!! algorithm "Regularised Nash dynamics, as Plum is trained"
        Input: initial weights θ; iterations N; refresh interval K;
               regulariser η; games per iteration G
        θ_ref ← θ;  buffer ← empty
        Loop for iteration n = 1 … N:
            play G games; each seat is the network (θ) with probability 1/2
                for the whole table, else drawn from the network, the five
                characters and the floor player
            for each network seat's record (s_t, a_t, outcome):
                r̃_t ← reward_t − η · log π_θ(a_t|s_t) / π_ref(a_t|s_t)
                G_t ← sum of r̃ from t to the end of the game
                A_t ← G_t − V_θ(s_t),  standardised over the iteration
            add a quarter of the iteration's states to buffer (last 10 kept)
            loss ← NeuRD(A, capped 1/π weight, logit threshold)
                   + c_v · (G − V)²  + λ · belief log-loss over buffer
                   − β · entropy(π)
            θ ← θ − α · ∇loss
            every K iterations: θ_ref ← θ
            every few iterations: measure, and save a checkpoint

### The opponents

David chose a mixed population: half the games are the network against copies of itself, and half seat it among the characters it will meet, [[Miss Scarlett]] to [[Mr. Green]] and the [[floor player]], each at their own token. Pure self-play can learn to beat only itself; the mix keeps the policy honest about the table it will actually sit at.[^plan]

### Three lessons from the trial runs

**The belief head memorised its first games.** Every step of one game shares the same envelope, so a few hundred games are really only a few hundred examples, and a network of {{code:net.params}} weights fits them quickly. Trained only on each iteration's own games, the belief head got *worse* than the [[uniform baseline]]: on one batch it reached a halfway log-loss of {{fact:policy.smoke.memorise}}. The fix was a [[Deep Q-network#Replay and the target network|replay buffer]]: the belief head trains on a sample from the last ten iterations' games, so it never sees one batch long enough to memorise it.[^smoke]

**The policy had nothing to push with.** A game's reward is 0 almost everywhere and arrives only at the end. Raw, those signals were drowned by the belief head's corrections, and the policy did not move for forty iterations. Standardising the advantages and loosening the gradient clip let it learn. A *shaped* reward, the bits of certainty the floor gained each turn, helped further.[^smoke]

**The end of a run is not the best of it.** The first long run, {{fact:policy.run.games}} games in under {{fact:policy.run.minutes}} minutes, taught the network to finish games and then began to drift: its late checkpoints won less and estimated worse. A second run resumed from the first's best checkpoint with a smaller step, a weaker regulariser and a looser logit threshold, and did not drift; its games shortened to about {{fact:policy.run2.turns.to}} turns.[^runs]

{{figure:plum-checkpoints|Win rate at his own table at each re-measured checkpoint of the two runs, 96 games each, against PlumOG's mark.}}

## Measured

### The quality of its numbers

{{figure:plum-policy-logloss|The network against PlumOG's count and the uniform baseline on the same positions. Lower is better.}}

The [[belief benchmark]] scores beliefs at four points of 60 games, {{fact:policy.bench.snapshots}} positions, against the truth.

{{table:bench.policy|Log-loss at four checkpoints on the Classic board, 7 October 2026, with the network as Plum; PlumOG's row is his larger-sample measurement of September. Lower is better.}}

The network is below the uniform baseline at every checkpoint and the best of the seven methods from the start to the halfway mark, {{fact:bench.policy.Plum.50}} against PlumOG's {{fact:bench.policy.PlumOG.50}} and the baseline's {{fact:bench.policy.uniform.50}}. Mr. Green, who carries it as his Plum arm, comes to lean on it more than on any other arm and matches it at halfway.[^bench]

Its probabilities are also honest about its confidence. Where the accusation test would fire, at a triple probability of {{code:preset.Plum.accuse_threshold}} or more, its triple was right in {{fact:policy.calibration.n}} of {{fact:policy.calibration.n}} positions; below that, where it is unsure, it is if anything too modest. His accusation threshold was kept.[^calibration]

### At the table

{{table:arena.policy|24 games at seed 7007 each, on today's rules. PlumOG's rows are the same deals, played under the landing rule in September.}}

Paired on the same deals, the network is a game behind PlumOG at his own table and four games behind among all six characters, where Plum played sixteen of the twenty-four. On 96 games a table the exported weights won {{fact:policy.own.96}}% at his own table and {{fact:policy.six.96}}% among six. Neither method has made a wrong accusation. The network estimates better than PlumOG and plays a little worse; what it reads of the table's habits has not yet become a way of winning races among six.[^arenas]

## Limitations

- **It learns the habits of its games.** The Rope question shows the risk: a position unlike the ones it trained on can draw a confident wrong answer that a count would never give. Its strength is the typical game, and it has no guarantee for the unusual one.
- **Its inputs do not say who named what.** It knows how often a card has been named and by how many players, not which player named which card, so it cannot read one opponent's habits the way [[Mrs. White]]'s [[Markov chain]] does. The belief plateau at about {{fact:bench.policy.Plum.50}} at halfway is probably that limit.[^runs]
- **No equilibrium is claimed.** The training rule converges to an equilibrium in two-player zero-sum games. In a three-to-six-player race it is a stable way to train, and the result is measured, not proved.
- **The weights decide.** Plum's play is reproducible from the seed and the weights file; a new file is a new Plum, and the replay fixtures and the [[determinism and seeds|goldens]] are pinned to the committed one.

## History

The method was chosen on 5 October 2026, when [[exact posterior enumeration]] had become the slowest and least accurate mid-game method on the Classic board and the most expensive with a model in the seat. The plan kept everything about Plum but his method: his token, his voice, his dials, his place in Mr. Green's ensemble. The scoring hooks that let a method own its move and suggestion scores, the network on random weights, the rollout and the trainer were built over two days; the first trained weights were committed on 6 October and measured on 7 October.[^plan][^runs]

## See also

- [[Professor Plum]], who plays by it
- [[DeepNash]], the Stratego system it is adapted from, and [[Reinforcement learning]]
- [[Exact posterior enumeration]], the method it replaced
- [[Self-play]], [[Belief benchmark]] and [[Arena]]

## References

{{references}}

[^paper]: {{cite:perolat-2022|the R-NaD method and NeuRD}}
[^plan]: {{cite:docs/deepnash-plan.md|3.1 The variant: Regularised Nash Dynamics over the floor}}
[^module]: {{cite:clude_agents/deep_nash.py|`encode_state`, `encode_choices`, `forward` and `move_scores`}}
[^dials]: {{cite:docs/deepnash-plan.md|5. The dials: which change meaning, and how each is re-measured}}
[^seams]: {{cite:docs/deepnash-plan.md|N2, the seams}}
[^script]: {{cite:scripts/train_plum.py|`neurd_term`, the loss and the loop}}
[^smoke]: {{cite:docs/deepnash-plan.md|What the smoke runs taught}}
[^runs]: {{cite:docs/deepnash-plan.md|The second run, `run2`, and the export (2026-10-06)}}
[^bench]: {{cite:docs/strategy-glossary.md|Belief benchmark, the network (N5)}}
[^calibration]: {{cite:docs/strategy-glossary.md|Calibration of the accusation test}}
[^arenas]: {{cite:docs/strategy-glossary.md|Arenas on the standard seeds}}

{{navbox:clude}}
