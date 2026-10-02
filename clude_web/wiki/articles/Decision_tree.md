---
title: Decision tree
short: Colonel Mustard's method: a tree of questions grown from past games
categories: Methods
redirects: Decision trees, Mustard's method, Regression tree, CART, Decision tree learning
dyk: ... that [[Colonel Mustard]]'s whole method is {{code:mustard.tree.leaves}} numbers at the ends of {{code:mustard.tree.nodes}} questions, and that it was grown from {{code:mustard.tree.games}} games it watched?
dyk: ... that on the Rope question Mustard's [[decision tree]] asks the same {{code:example.mustard.questions}} questions about all four open cards and reaches the same answer for each?
---
{{infobox
title: Decision tree
Played by | [[Colonel Mustard]]
In a phrase | Pattern-matches; confidently wrong on unusual deals
Module | `decision_tree.py`
Evidence used | {{code:mustard.tree.features}} measurements of each card's situation
Assumes | The games it was grown from are like the game it is in
Cost | About {{fact:bench.grid.Mustard.ms}} ms a call
= The tree, as grown
Questions | {{code:mustard.tree.nodes}} nodes, {{code:mustard.tree.leaves}} leaves, depth {{code:mustard.tree.depth}}
Grown from | {{code:mustard.tree.rows}} rows of {{code:mustard.tree.games}} games
}}

A **decision tree** is the method by which [[Colonel Mustard]] forms his [[belief]] about what is in [[the envelope]]. It is a [[w:Decision tree learning|tree of yes-or-no questions]] about a card: how many players could still hold it, how often it has been named and by how many different players, how far the game has run. Each answer leads to the next question, and the last leads to a number, the share of cards in past games that gave the same answers and turned out to be the envelope's. The tree is not written; it is *grown*, by a program that reads the records of games already played and finds the questions that best separate the envelope's cards from the rest. Mustard's is grown from {{code:mustard.tree.games}} games played out between purely logical players, and with a [[logbook]] it is regrown from every game since.[^glossary]

The method reasons by resemblance. It does not count deals, as [[Professor Plum]] does, or multiply evidence, as [[Miss Scarlett]] does; it asks whether cards *like this one* were usually the envelope's, and answers with the confidence that experience of many games gives. That is its strength at the end of a game, where the patterns are strong and it has the best belief of the six, and its weakness in the middle, where an unusual deal matches a pattern it has no business matching and the tree is, in the project's phrase, "confidently wrong".[^glossary]

Decision trees are one of the oldest and most used tools in [[w:Machine learning|machine learning]], valued for being fast to consult and easy to read: the whole of what Mustard believes can be printed on a page and followed by hand.[^cart]

## At the table

!!! example "Worked example: the Rope question"
    {{figure:mustard-path|The questions the trained tree asked about Mrs. Peacock's card in the Rope question, and the leaf it reached.}}

    Late in a three-handed game Mustard's [[detective notepad|notepad]] has every card placed except four: of the suspects, **Mrs. White** or **Mrs. Peacock** is in the envelope; of the weapons, the **Rope** or the **Wrench**. [[Mr. Green]] has just suggested *Mrs. Peacock, with the Rope, in the Hall*, and Mustard himself showed him a card. The game is at turn 30.

    For each of the four open cards the tree asks its questions. For Mrs. Peacock's card: has it been named at most {{code:example.mustard.step.1.threshold}} times? {{code:example.mustard.step.1.answer}}, once. Named without being disproved at most {{code:example.mustard.step.2.threshold}} times? {{code:example.mustard.step.2.answer}}, never. Named by at most {{code:example.mustard.step.3.threshold}} players? {{code:example.mustard.step.3.answer}}, by one. Are at most {{code:example.mustard.step.4.threshold}} of the possible holders still possible for it? {{code:example.mustard.step.4.answer}}: two of the four (Mustard and the envelope), which is {{code:example.mustard.step.4.value}}. At most {{code:example.mustard.step.5.threshold}}? {{code:example.mustard.step.5.answer}}. Is the game at most {{code:example.mustard.step.6.threshold}} of the way through its first fifty turns? {{code:example.mustard.step.6.answer}}. The {{code:example.mustard.questions}} answers end at a leaf that says **{{code:example.mustard.leaf}}**: of the {{code:example.mustard.leaf.n}} cards in the training games that answered the same way, about that share were the envelope's.

    Mrs. White's card answers every question the same way, so does the Rope, and so does the Wrench. All four reach the same leaf, and when the four raw numbers are turned into probabilities within each category every open card is at **{{code:example.mustard.White}}**. The overheard answer, which told [[Professor Plum]] exactly that Mrs. White is at {{code:example.plum.White}}, has told Mustard nothing at all.

The tree does have a question that could have told the cards apart, whether a card is in an open "one of these" fact, and it asks it elsewhere in the tree. On this path it never gets there. That is the method in one example: it answers from the questions experience taught it to ask, and the right question is not always among them.

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

## Formally

### The split criterion

Mustard's tree is a [[w:Decision tree learning|CART]]-style [[w:Regression analysis|regression]] tree with binary splits, in the family [[w:Leo Breiman|Leo Breiman]] and his colleagues set out in 1984. For a group of rows with a share $p$ of positives, the [[w:Decision tree learning#Gini impurity|Gini impurity]] is

$$ G = 2p(1 - p) $$

which is 0 for a pure group and largest, $1/2$, for an even mixture. A candidate split sends $n_L$ rows left and $n_R$ right; its gain is the parent's impurity less the impurity of the children weighted by size,

$$ \Delta = G_{\text{parent}} - \frac{n_L\, G_L + n_R\, G_R}{n_L + n_R} $$

and the split with the largest gain is taken. Candidate cuts are the midpoints between consecutive distinct values of each measurement, so the tree's thresholds, {{code:example.mustard.step.1.threshold}} for "times named" at the root, are halfway points between values that occurred.[^cart]

### The leaf value

A leaf with $n$ rows of which $k$ are positive predicts not $k/n$ but the **m-estimate**

$$ \hat p = \frac{k + m\, r}{n + m} $$

where $r$ is the whole training set's base rate and $m$ the number of phantom rows at that rate mixed into every leaf, {{code:mustard.tree.smoothing}} for Mustard. A leaf with no positives among 40 rows predicts about 0.01 rather than 0. The difference matters because a character [[accusation|accuses]] on the product of its best three probabilities: a category whose other cards all read exactly 0 reads as certainty, and before the smoothing was added the hard zeros were {{fact:mustard.phase4.zeros}} per cent of Mustard's error on the first benchmark.[^phase5][^phase4]

### Why it is called a regression tree

The tree predicts a number in $[0, 1]$, not a class, which is what makes it a regression tree rather than a classifier; but its labels are 0 and 1 and its splits are chosen by a classification criterion. In practice it is a [[w:Probabilistic classification|probability estimator]], and its probabilities are known to be poorly [[w:Calibration (statistics)|calibrated]] in the way trees usually are: a leaf's value is the average over whatever mixture of situations reached it, confident in proportion to its size and not to its relevance.[^cart]

## In clude

The module is `clude_agents/decision_tree.py`. It contains the eight measurements, the row builder, the training-set generator (which plays the {{code:mustard.tree.games}} games itself, from a fixed seed, {{code:mustard.tree.seed}}, through the [[deduction floor|floor bot]]), the tree grower, and the agent. Rows and trees are cached by their settings, so that [[Mr. Green]]'s ensemble, which builds a Mustard of its own, does not grow the tree a second time.[^module]

Which questions the grown tree asks is read from it here, not from the documentation. It splits {{code:mustard.tree.splits.turn_fraction}} times on the turn, {{code:mustard.tree.splits.possible_holders_frac}} times on the holders still possible, {{code:mustard.tree.splits.times_named_total}} on times named, {{code:mustard.tree.splits.or_constraint_involvement}} on the open facts a card is in, {{code:mustard.tree.splits.distinct_namers}} on the players who named it, {{code:mustard.tree.splits.times_named_unrefuted}} on undisproved namings, {{code:mustard.tree.splits.category_size_frac}} on the category's size, and {{code:mustard.tree.splits.named_beside_located}} on probing; the counts change whenever the training games or the hyperparameters do.

### The training regime

The tree is only as good as the games it was grown from, and the first tree was grown from the wrong ones. Phase 4's training games were played by players who moved and suggested at random, and on a board with a bug that kept tokens from leaving a room except by [[Classic board|secret passage]]; the tables piled into one room, re-suggested the same cards, and the floor learned nothing after the first few turns. Mustard's rows came from that plateau. Phase 5 replaced the random players with the [[deduction floor|floor bot]], which suggests only about cards it has not placed and accuses only on proof, so that its games carry information throughout and end by deduction; the tree was regrown on them with the two new measurements and the smoothed leaves.[^phase5]

### Memory

Mustard is one of three characters whose method itself remembers. With a logbook, rows built from every seat's view of every stored game, at the same two checkpoints, are appended to the self-play base before the tree is grown, and the tree is grown afresh for him at each table. He learns from games he did not sit in, since a row is a row. Rebuilt from {{fact:mustard.memory.games}} stored games ({{fact:mustard.memory.rows}} rows) and scored on {{fact:mustard.memory.held_out}} held-out games, a first and noisy look: his mid-game [[log-loss]] went from {{fact:mustard.memory.mid.before}} to {{fact:mustard.memory.mid.after}}, better, and his end-of-game score from {{fact:mustard.memory.end.before}} to {{fact:mustard.memory.end.after}}, worse. The tree with memory pattern-matches three-seat character games rather than floor-bot self-play, which, as the notes observe, is the character.[^memory]

## Measured

### The quality of his numbers

{{table:bench.ring|The six methods on the ring board, Phase 5: log-loss at four checkpoints. Lower is better.}}

On the ring board the tree had the best belief of the six at the end of a game, {{fact:bench.ring.Mustard.100}}, and one of the worst in the middle, {{fact:bench.ring.Mustard.50}} and {{fact:bench.ring.Mustard.75}} against the baseline's {{fact:bench.ring.uniform.50}} and {{fact:bench.ring.uniform.75}}: confidently wrong, where the other methods were merely uncertain.[^ring] On the first benchmark of all, before the floor bot and the smoothing, its score at the end had been {{fact:mustard.phase4}} against the baseline's {{fact:uniform.phase4}}, two-thirds of it from the {{fact:phase4.zero_categories}} per cent of categories where a leaf put exactly nothing on the true card.[^phase4]

{{table:bench.grid|The same benchmark on the Classic board, {{fact:bench.grid.games}} games, 15 September 2026.}}

On the Classic board the tree, now grown from games on that board, matches the baseline in the middle ({{fact:bench.grid.Mustard.50}} to {{fact:bench.grid.uniform.50}}) and is the best method at the end, {{fact:bench.grid.Mustard.100}}, with the best first choice, {{fact:bench.grid.Mustard.top1}}. The notes put it as "the same method on data that suits it better".[^grid]

### At the table

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, 15 September 2026.}}

Mustard's wrong accusations are the tree's. His [[accusation threshold]] is the neutral {{code:preset.Mustard.accuse_threshold}} on purpose, so that when he is wrong the method is to blame and not a dial. On the ring board the tree put him out of {{fact:arena.ring.first.Mustard.wrong}}% of his games at the first pass and {{fact:arena.ring.Mustard.wrong}}% at the tuned presets; on the Classic board, {{fact:arena.grid.Mustard.wrong}}%.[^arena][^ringarena]

With [[Claude]] in his seat at a table where every character had one, his wrong accusations fell from {{fact:twin.grid.Mustard.wrong_base}}% to {{fact:twin.grid.Mustard.wrong_llm}}% and his wins rose from {{fact:twin.grid.Mustard.win_base}}% to {{fact:twin.grid.Mustard.win_llm}}%, on both boards. The obvious reading, that a judgement layer rescues a pattern-matcher from its confident errors, did not survive the ladder that tested it: alone with Claude at a table of headless characters, his wrong rate at the preset [[leash]] was {{fact:ladder.mustard.0.25.wrong}}% against {{fact:ladder.mustard.headless.wrong}}% without, and his wins did not move at any leash. What improved him in the twin run was the table, five other model-piloted seats ending games sooner.[^twin][^ladder]

## Limitations

- **It matches patterns, not deals.** The tree has no notion of a deal's consistency; the floor supplies what is certain and the tree guesses the rest from resemblance.
- **Its confidence is the training set's, not the position's.** A leaf is as sure as its rows were, whatever the present deal is like. This is the mid-game error, measured.
- **The questions are fixed by what the training games showed.** A fact that mattered rarely in those games is asked about rarely in the tree, however much it matters now; the Rope question is an example.
- **It is only ever as good as its past is like the present.** Grown from floor-bot games it is at its best against floor bots; grown from character games it changes, in behaviour and not only in accuracy, and so does the character. In the vocabulary of machine learning the tree is exposed to [[w:Overfitting|overfitting]] and to shift in the distribution it was trained on, and its depth and leaf size are the only guards.

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
