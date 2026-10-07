---
title: Decision tree
short: Colonel Mustard's probability model trained on features from past games
categories: Methods
redirects: Decision trees, Mustard's method, Regression tree, CART, Decision tree learning
dyk: ... that [[Colonel Mustard]]'s tree has {{code:mustard.tree.nodes}} nodes, including {{code:mustard.tree.leaves}} leaves, and is trained on {{code:mustard.tree.games}} self-play games?
dyk: ... that on the Rope question Mustard's [[decision tree]] asks the same {{code:example.mustard.questions}} questions about all four open cards and reaches the same answer for each?
---
{{infobox
title: Decision tree
Played by | [[Colonel Mustard]]
In a phrase | Estimates from patterns in training games
Module | `decision_tree.py`
Evidence used | {{code:mustard.tree.features}} measurements of each card's situation
Assumes | The games it was grown from are like the game it is in
Cost | About {{fact:bench.grid.Mustard.ms}} ms a call at the Classic-board halfway checkpoint
= The tree, as grown
Questions | {{code:mustard.tree.nodes}} nodes, {{code:mustard.tree.leaves}} leaves, depth {{code:mustard.tree.depth}}
Grown from | {{code:mustard.tree.rows}} rows of {{code:mustard.tree.games}} games
}}

A **decision tree** estimates an answer by following a sequence of yes-or-no questions. [[Colonel Mustard]] uses one to form his [[belief]] about the cards in [[the envelope]]. The questions describe a card's situation: possible holders, how often it has been named and the stage of the game. Each sequence ends at a *leaf*, which assigns a score based on training examples with similar features. The [[deduction floor]] then masks and normalises these scores into card probabilities.[^module][^base]

Mustard's default tree is trained on {{code:mustard.tree.games}} floor-bot self-play games. When method memory is enabled, it is retrained with additional stored-game examples. Training chooses the questions rather than a programmer specifying them all. The method is inexpensive to consult, but its accuracy depends on how well those features and training games represent the current position.[^module]

[[w:Decision tree learning|Decision trees]] are widely used in [[w:Machine learning|machine learning]] because their paths can be inspected and followed by hand.[^cart] In the recorded Classic-board benchmark, Mustard had the lowest final log-loss of the six methods. The earlier ring-board run also gave him the lowest final loss, but substantially worse mid-game results. These outcomes show the importance of training data and evaluation conditions.[^glossary]

## At the table

!!! example "Worked example: the Rope question"
    {{figure:mustard-path|The questions the trained tree asked about Mrs. Peacock's card in the Rope question, and the leaf it reached.}}

    An observer at a three-handed table has every card placed except four: **Mrs. White**, **Mrs. Peacock**, the **Rope** and the **Wrench**. One suspect and one weapon are in the envelope; the alternatives are in [[Colonel Mustard]]'s hand. [[Mr. Green]] suggests *Mrs. Peacock, with the Rope, in the Hall*, whose room card is known to be in Green's hand. Mustard shows Green a card the observer cannot see. At turn 30, Mustard's tree is evaluated on this observer's view, not on Mustard's own private hand. This is the same comparison position used by the other method articles.

    For each of the four open cards the tree asks its questions. For Mrs. Peacock's card: has it been named at most {{code:example.mustard.step.1.threshold}} times? {{code:example.mustard.step.1.answer}}, once. Named without being disproved at most {{code:example.mustard.step.2.threshold}} times? {{code:example.mustard.step.2.answer}}, never. Named by at most {{code:example.mustard.step.3.threshold}} players? {{code:example.mustard.step.3.answer}}, by one. Are at most {{code:example.mustard.step.4.threshold}} of the possible holders still possible for it? {{code:example.mustard.step.4.answer}}: two of the four (Mustard and the envelope), which is {{code:example.mustard.step.4.value}}. At most {{code:example.mustard.step.5.threshold}}? {{code:example.mustard.step.5.answer}}. Is the game at most {{code:example.mustard.step.6.threshold}} of the way through its first fifty turns? {{code:example.mustard.step.6.answer}}. The {{code:example.mustard.questions}} answers end at a leaf that says **{{code:example.mustard.leaf}}**: of the {{code:example.mustard.leaf.n}} cards in the training games that answered the same way, about that share were the envelope's.

    Mrs. White's card answers every question the same way, so does the Rope, and so does the Wrench. All four reach the same leaf, and when the four raw numbers are turned into probabilities within each category every open card is at **{{code:example.mustard.White}}**. The same disproof gives Mrs. White probability {{code:example.plum.White}} under [[Professor Plum]]'s count. On this path, the tree makes no corresponding distinction.

One available feature counts a card's involvement in open disjunctions. It would distinguish the two named cards from the alternatives, but this path does not test it. The tree uses only the features selected along the path, even when another feature matters in the current position.

## How it works

### The eight measurements

The tree never sees a card's name. It sees {{code:mustard.tree.features}} numbers that describe the card's situation from the viewer's chair, all computed from the [[deduction floor]]'s mask and the history of [[suggestion|suggestions]]:[^module]

| Measurement | What it is |
|---|---|
| Holders still possible | The share of the table, envelope included, that could still hold the card |
| Open facts it is in | How many "at least one of these" facts name it |
| Times named, undisproved | How many suggestions named it that nobody could disprove |
| Times named | How many suggestions named it at all |
| Turn, as a share of 50 | How far the game has run, capped at 1 |
| Category size, of nine | 6/9 for a suspect or weapon, 1 for a room |
| Players who named it | How many different players have named it |
| Named beside placed cards | On average, how many of the other cards in those suggestions the floor had already placed |

The last two were added when the training games became informative enough to make them mean something: a card named beside two cards the floor has already placed is being *probed*, and a card named by several players is of general interest.[^phase5]

### Growing the tree

The training set is one row per card the floor had not placed, in every player's view of every training game at two points, halfway through and at the end: the eight measurements and a label, 1 if that card turned out to be the envelope's. Mustard's default set is {{code:mustard.tree.rows}} rows, of which {{code:mustard.tree.positives}} are the envelope's, a base rate of {{code:mustard.tree.base_rate.pct}} per cent.[^module]

Growing is [[w:Recursion|recursive]]. At the root the program tries every measurement and every cut between two of its values, and picks the question that best separates the rows into a purer "yes" group and a purer "no" group. It then does the same for each group, and so on, until a group is too small to split, too deep in the tree, or already pure. Each final group is a leaf, and its value is the share of its rows that were the envelope's, smoothed a little towards the base rate so that no leaf says exactly 0 or exactly 1. Mustard's tree stops at depth {{code:mustard.tree.max_depth}} and will not split a group of fewer than twice {{code:mustard.tree.min_leaf}} rows; grown, it has {{code:mustard.tree.nodes}} nodes, {{code:mustard.tree.leaves}} of them leaves, whose values run from {{code:mustard.tree.leaf.min}} to {{code:mustard.tree.leaf.max}}.[^module]

{{figure:mustard-tree|wide|Mustard's tree as it is actually played with, grown from the live model. A leaf's colour is how sure it is: cold under 0.10, cool to 0.35, warm to 0.65, hot above.}}

### Consulting it

To form a belief the method computes the eight measurements for every unplaced card, follows each down the tree to a leaf, takes the leaf's value as the card's raw score, and hands the scores to the step every method ends with: the floor sets to zero any card it has ruled out and to 1 any it has proved, and what remains is scaled to sum to 1 within each category.[^base] The tree is grown once, the first time anyone asks, and kept for the life of the program; consulting it is a handful of comparisons, which is why Mustard answers in a fraction of a millisecond.

!!! algorithm "Mustard's belief"
        Input: the trained regression tree; the floor's mask
        for each card c the floor has not placed:
            x ← c's eight measurements (how often named, how often unrefuted,
                by how many players, where it could still be, how far the game has run, …)
            node ← the root
            while node is not a leaf:
                node ← its left child if x[feature] ≤ threshold, else its right child
            score(c) ← the leaf's value (its training cards' smoothed share in the envelope)
        mask and normalise within each category

## Formally

### The split criterion

Mustard's tree is a [[w:Decision tree learning|CART]]-style [[w:Regression analysis|regression]] tree with binary splits, in the family [[w:Leo Breiman|Leo Breiman]] and his colleagues set out in 1984. For a group of rows with a share $p$ of positives, the [[w:Decision tree learning#Gini impurity|Gini impurity]] is

$$ G = 2p(1 - p) $$

which is 0 for a pure group and largest, $1/2$, for an even mixture. A candidate split sends $n_L$ rows left and $n_R$ right; its gain is the parent's impurity less the impurity of the children weighted by size,

$$ \Delta = G_{\text{parent}} - \frac{n_L\, G_L + n_R\, G_R}{n_L + n_R} $$

and the split with the largest gain is taken. Candidate cuts are the midpoints between consecutive distinct values of each measurement, so the tree's thresholds, such as {{code:example.mustard.step.1.threshold}} for "times named" on the illustrated path, are halfway points between values that occurred.[^cart]

### The leaf value

A leaf with $n$ rows of which $k$ are positive predicts not $k/n$ but the **m-estimate**

$$ \hat p = \frac{k + m\, r}{n + m} $$

where $r$ is the whole training set's base rate and $m$ the number of phantom rows at that rate mixed into every leaf, {{code:mustard.tree.smoothing}} for Mustard. A leaf with no positives among 40 rows predicts about 0.01 rather than 0. The difference matters because a character [[accusation|accuses]] on the product of its best three probabilities: a category whose other cards all read exactly 0 reads as certainty, and before the smoothing was added the hard zeros were {{fact:mustard.phase4.zeros}} per cent of Mustard's error on the first benchmark.[^phase5][^phase4]

### Why it is called a regression tree

The implementation calls the model a regression tree because its leaves return numerical scores. With binary labels, Gini-based splits and smoothed class frequencies, it also acts as a [[w:Probabilistic classification|probability estimator]]. A leaf summarises the training rows that reached it, not a count of deals consistent with the current evidence. The resulting probabilities need not be well [[w:Calibration (statistics)|calibrated]], especially when the current games differ from the training regime.[^module]

## In clude

The module is `clude_agents/decision_tree.py`. It contains the eight measurements, the row builder, the training-set generator (which plays the {{code:mustard.tree.games}} games itself, from a fixed seed, {{code:mustard.tree.seed}}, through the [[deduction floor|floor bot]]), the tree grower, and the agent. Rows and trees are cached by their settings, so that [[Mr. Green]]'s ensemble, which builds a Mustard of its own, does not grow the tree a second time.[^module]

Which questions the grown tree asks is read from it here, not from the documentation. It splits {{code:mustard.tree.splits.turn_fraction}} times on the turn, {{code:mustard.tree.splits.possible_holders_frac}} times on the holders still possible, {{code:mustard.tree.splits.times_named_total}} on times named, {{code:mustard.tree.splits.or_constraint_involvement}} on the open facts a card is in, {{code:mustard.tree.splits.distinct_namers}} on the players who named it, {{code:mustard.tree.splits.times_named_unrefuted}} on undisproved namings, {{code:mustard.tree.splits.category_size_frac}} on the category's size, and {{code:mustard.tree.splits.named_beside_located}} on probing; the counts change whenever the training games or the hyperparameters do.

### The training regime

The tree is only as good as the games it was grown from, and the first tree was grown from the wrong ones. Phase 4's training games were played by players who moved and suggested at random, and on a board with a bug that kept tokens from leaving a room except by [[Classic board|secret passage]]; the tables piled into one room, re-suggested the same cards, and the floor learned nothing after the first few turns. Mustard's rows came from that plateau. Phase 5 replaced the random players with the [[deduction floor|floor bot]], which suggests only about cards it has not placed and accuses only on proof, so that its games carry information throughout and end by deduction; the tree was regrown on them with the two new measurements and the smoothed leaves.[^phase5]

### Memory

Mustard has persistent method memory. When it is enabled, rows from stored games are appended to the self-play training set, and his tree is rebuilt for each table. Rows include every seat's view, so he can learn from games he did not play. An initial comparison added {{fact:mustard.memory.rows}} rows from {{fact:mustard.memory.games}} stored games and evaluated {{fact:mustard.memory.held_out}} held-out games. Mid-game log-loss improved from {{fact:mustard.memory.mid.before}} to {{fact:mustard.memory.mid.after}}, while final loss worsened from {{fact:mustard.memory.end.before}} to {{fact:mustard.memory.end.after}}. This small experiment gives mixed evidence of benefit and changes the training distribution from floor-bot self-play towards character games.[^memory]

## Measured

### The quality of his numbers

{{table:bench.ring|The six methods on the ring board, Phase 5: log-loss at four checkpoints. Lower is better.}}

On the ring board the tree had the best belief of the six at the end of a game, {{fact:bench.ring.Mustard.100}}, and one of the worst in the middle, {{fact:bench.ring.Mustard.50}} and {{fact:bench.ring.Mustard.75}} against the baseline's {{fact:bench.ring.uniform.50}} and {{fact:bench.ring.uniform.75}}: confidently wrong, where the other methods were merely uncertain.[^ring] On the first benchmark of all, before the floor bot and the smoothing, its score at the end had been {{fact:mustard.phase4}} against the baseline's {{fact:uniform.phase4}}, two-thirds of it from the {{fact:phase4.zero_categories}} per cent of categories where a leaf put exactly nothing on the true card.[^phase4]

{{table:bench.grid|The same benchmark on the Classic board, {{fact:bench.grid.games}} games, 15 September 2026.}}

In the Classic-board benchmark, with the tree trained on that board, halfway loss was {{fact:bench.grid.Mustard.50}}, compared with the baseline's {{fact:bench.grid.uniform.50}}. Final loss was {{fact:bench.grid.Mustard.100}}, the lowest of the six methods, and final first-choice accuracy was {{fact:bench.grid.Mustard.top1}}, the highest. The improved results are consistent with training on a more suitable game distribution, although several aspects of the regime changed together.[^grid]

### At the table

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, 15 September 2026.}}

Mustard uses the neutral [[accusation threshold]] of {{code:preset.Mustard.accuse_threshold}} to keep the method's effect visible without an unusually low or high threshold. Wrong accusations still depend on both the estimates and this decision rule. He accused wrongly in {{fact:arena.ring.first.Mustard.wrong}}% of games in the first ring-board arena, {{fact:arena.ring.Mustard.wrong}}% with tuned presets, and {{fact:arena.grid.Mustard.wrong}}% in the tabulated Classic-board arena.[^arena][^ringarena]

In the Classic-board twin comparison, with [[Claude]] piloting every character, Mustard's wrong-accusation rate fell from {{fact:twin.grid.Mustard.wrong_base}}% to {{fact:twin.grid.Mustard.wrong_llm}}%, and wins rose from {{fact:twin.grid.Mustard.win_base}}% to {{fact:twin.grid.Mustard.win_llm}}%.[^twin] A separate ring-board leash experiment, with only Mustard model-piloted, did not reproduce that reduction: at the preset [[leash]], his wrong rate was {{fact:ladder.mustard.0.25.wrong}}%, compared with {{fact:ladder.mustard.headless.wrong}}% headless.[^ladder] The project attributes much of the twin-run improvement to other model-piloted seats ending games earlier. The trials do not isolate a reliable benefit from model judgement alone.

## Limitations

- **It matches patterns, not deals.** The tree has no notion of a deal's consistency; the floor supplies what is certain and the tree guesses the rest from resemblance.
- **Its confidence is the training set's, not the position's.** A leaf is as sure as its rows were, whatever the present deal is like. This is the mid-game error, measured.
- **The questions are fixed by what the training games showed.** A fact that mattered rarely in those games is asked about rarely in the tree, however much it matters now; the Rope question is an example.
- **Training and play can differ.** Changing the board, opponents or stored-game data can change accuracy. Depth limits, minimum leaf sizes and smoothing help control [[w:Overfitting|overfitting]], but do not guarantee performance under a different distribution.

## See also

- [[Colonel Mustard]], the character who plays by this method
- [[Exact posterior enumeration]] and [[Naive Bayes]], two methods that reason from the position rather than from experience
- [[Deduction floor]], whose floor bot played the games the tree was grown from
- [[Logbook]], where the method's memory of stored games is kept
- [[Belief benchmark]] and [[Log-loss]]
- [[w:Decision tree learning|Decision tree learning]] and [[w:Additive smoothing|additive smoothing]] on Wikipedia

## References

{{references}}

[^glossary]: {{cite:docs/strategy-glossary.md|Mustard -- Decision tree on game logs}}
[^cart]: {{cite:breiman-1984}}
[^module]: {{cite:clude_agents/decision_tree.py|`FEATURE_NAMES` and `_features`, `_build_tree`, `_leaf_value`, the defaults, and the module's notes}}
[^phase5]: {{cite:docs/phase5-plan.md|4.2 Mustard: calibration, then distribution}}
[^base]: {{cite:clude_agents/base.py|`mask_and_normalize`}}
[^phase4]: {{cite:docs/strategy-glossary.md|Phase 4 benchmark results (RandomBot regime, historical)}}
[^memory]: {{cite:docs/strategy-glossary.md|Phase 7: memory (2026-09-14)}}
[^ring]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^arena]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}
[^ringarena]: {{cite:docs/strategy-glossary.md|Arena, tuned presets}}
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}
[^ladder]: {{cite:docs/strategy-glossary.md|Mustard}} The per-character leash ladder, 2026-09-13.

{{navbox:clude}}
