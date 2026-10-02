---
title: Professor Plum
short: The cautious character who enumerates consistent deals
categories: Characters
redirects: Plum, Prof. Plum
featured: yes
dyk: ... that [[Professor Plum]] used sampling in {{fact:plum.fallback.calls}} of {{fact:bench.grid.snapshots}} calls in the original Classic-board benchmark?
dyk: ... that in the Classic-board budget comparison, five times as many samples took Plum's halfway log-loss from {{fact:budget.grid.200k-2k.50}} to {{fact:budget.grid.200k-10k.50}}, and that the floor-only uniform baseline scored {{fact:budget.grid.uniform.50}}?
dyk: ... that Plum once spent fifty turns riding a [[secret passages|secret passage]] back and forth, making the same [[suggestion]] twenty times?
---
{{infobox
title: Professor Plum
class: suspect-plum
figure: token-plum
caption: Plum's token, last of the six in the order of play
Method | [[Exact posterior enumeration]]
In a phrase | Cautious, methodical and computationally expensive
Module | `exact_enum.py`
Memory | A [[logbook]] only; his method remembers nothing
= Personality dials
[[Accusation threshold]] | {{code:preset.Plum.accuse_threshold}}
[[Bluff rate]] | {{code:preset.Plum.bluff_rate}}
[[Curiosity]] | {{code:preset.Plum.curiosity}}
[[Secrecy]] | {{code:preset.Plum.secrecy}}
[[Temperature]] | {{code:preset.Plum.temperature}}
= Classic-board arena, 15 September 2026
Games won | {{fact:arena.grid.Plum.win}}% of {{fact:arena.grid.Plum.games}}
Wrong accusations | {{fact:arena.grid.Plum.wrong}}%
}}

**Professor Plum** is one of the six [[Clue#The cards|suspects]] in [[Clue]] and the [[clude]] [[Category:Characters|character]] who uses [[exact posterior enumeration]]. He calculates each card's [[w:Probability|probability]] of being in [[the envelope]] by counting the deals consistent with the evidence and finding the share that contains it. A completed count is exact under his model, which gives equal weight to consistent deals and ignores behavioural evidence about opponents' choices.[^module]

Early positions can be too large to enumerate. With one card of each kind in his own hand at a six-seat table, there are {{code:deals.6}} possible deals before further evidence. Plum limits the search and uses [[w:Monte Carlo method|random sampling]] when it exceeds the budget. In the original [[Classic board]] benchmark, this happened in nearly half the calls. Sampling introduced noise and bias; increasing the sample budget improved his accuracy, but his halfway log-loss remained slightly worse than the [[uniform baseline]]. At later checkpoints, when fewer possibilities remained, he was among the lowest-loss methods.[^grid][^budget]

Plum plays cautiously. His [[accusation threshold]] is {{code:preset.Plum.accuse_threshold}}, and he rarely [[bluffing|bluffs]]. He made no wrong accusations in the headless [[arena|arenas]] reported below. Caution did not always make him efficient: an earlier movement score encouraged him to repeat uninformative [[suggestion|suggestions]] through secret passages. The [[landing rule]] substantially reduced that behaviour.[^presets][^landing]

## Character

Plum is written as "an [[w:Academy|academic]], precise to the point of pedantry, and privately certain you are the cleverest person in the room".[^persona] The description is addressed to him: it is the opening of his [[persona]], the page of prose a [[w:Large language model|language model]] is given when it plays his seat. The persona goes on to describe the method from the inside: "Nothing you believe is a hunch; it is a fraction, and you know its denominator."[^persona]

His [[persona]] specifies a donnish, precise voice, with phrases such as "in point of fact" and "if one is being precise". It describes him as "courteous to a fault and condescending by reflex".[^persona] The model is instructed to explain his deductions in words rather than recite [[w:Decimal|decimals]]. Sampling supplies a comic vulnerability: he finds it "faintly humiliating" when the count is too large to finish. These are writing instructions for a model playing his seat, rather than properties of the numerical algorithm.

All of this is heard only when a model is in the seat, as [[table talk]]. A character can also play *headless*, by its numbers alone and in silence; every measurement of Plum's reasoning below was made that way unless it says otherwise. The seat itself is fixed: Plum always plays the purple token, last in the order of play.[^seats]

## How he thinks

{{main:Exact posterior enumeration}}

### Counting deals

A *deal* puts one suspect, one weapon and one room unseen into [[the envelope]], then distributes the other {{code:cards.dealt}} cards round the table. Plum keeps, in principle, every deal compatible with his evidence, removing possibilities as he learns. The surviving deals yield his [[w:Posterior probability|posterior]]: a probability revised in the light of evidence.

!!! example "Worked example: three deals"
    {{figure:rope-deals|Four ways the open cards could lie, one of them impossible. Plum's probability for a card is the share of the surviving deals that have it in the envelope.}}

    Late in a three-handed game Plum's [[detective notepad|notepad]] has every card placed except four. Of the suspects, either **Mrs. White** or **Mrs. Peacock** is in the envelope; of the weapons, either the **Rope** or the **Wrench**. Whichever of each pair is not in the envelope is in [[Colonel Mustard]]'s hand, which has exactly two cards unaccounted for. That leaves four possible deals, and with nothing else to go on each open card would be an [[w:Even money|even bet]]: {{code:example.uniform.White}}.

    Then [[Mr. Green]] suggests *Mrs. Peacock, with the Rope, in the Hall*. Plum cannot [[suggestion#In the rules|disprove]] it. Mustard can, and shows Green a card that Plum does not see. The Hall is in Green's own hand, so the card Mustard showed was Peacock or the Rope: Mustard holds at least one of the two.

    That rules out exactly one deal, the one in which the envelope holds Peacock and the Rope and Mustard is left with White and the Wrench. **{{code:example.deals}} deals survive**, and Mrs. White is in the envelope in two of them. Plum's probability for White is therefore {{code:example.plum.White}}, and for Peacock {{code:example.plum.Peacock}}; likewise {{code:example.plum.Wrench}} for the Wrench and {{code:example.plum.Rope}} for the Rope. The four probabilities follow directly from the three equally weighted surviving deals.

The example can be checked by hand. In larger positions, Plum uses a [[w:Backtracking|backtracking]] search over a [[w:Constraint satisfaction problem|constraint satisfaction problem]].[^aima] The [[deduction floor]] supplies possible holders, hand sizes and open constraints. The search tries each unresolved card with each possible holder and abandons a branch when a hand overfills, a category has two envelope cards or a constraint becomes impossible. Each complete, consistent deal is counted once.[^module]

### When the count is too long

The number of deals [[w:Combinatorial explosion|grows explosively]] with the number of unplaced cards. For example, with two cards of each kind in hand at a three-seat table and no other evidence, there are {{code:deals.3}} possible deals. With one of each kind at a six-seat table, there are {{code:deals.6}}.[^count] Plum allows his search {{code:plum.node_budget}} steps. If it has not finished by then he abandons it and draws up to {{code:plum.sample_budget}} random deals instead, building each by placing the unplaced cards in a shuffled order and discarding any attempt that paints itself into a corner.[^module] The share of the valid samples with a card in the envelope stands in for the exact share.

The fallback uses [[w:Rejection sampling|rejection]] of invalid draws, but does not generate every valid deal with equal probability. Finite samples introduce [[w:Sampling error|noise]], and the random construction procedure introduces [[w:Bias (statistics)|bias]] towards deals it can build more easily. These errors explain why a sampled answer can be less accurate than the floor's uniform baseline. The method article describes the sampler in detail.[^module]

### What the count assumes

The count is exact when the surviving deals are equally weighted under the evidence model. It uses the logical consequences of [[suggestion#In the rules|disproofs]] and known cards, while ignoring preferences in [[suggestion#Showing a card|which card to show]]. For example, if Mustard holds Peacock and the Rope and chooses uniformly between them, showing the Rope is half as likely as when it is his only matching card. The count retains both deals at equal weight. The effect depends on Mustard's choice policy, as the [[w:Monty Hall problem|Monty Hall problem]] illustrates. Plum also ignores which questions opponents prefer to ask, the behavioural evidence used by [[Mrs. White]]'s [[Markov chain]].

The shared accusation test introduces another approximation. It multiplies the best suspect, weapon and room probabilities as if the categories were [[w:Independence (probability theory)|independent]]. In the example, {{code:example.plum.White}} times {{code:example.plum.Wrench}} gives about {{code:example.plum.pair}}, although only one of the three surviving deals has White with the Wrench: the joint probability is 1/3. Exact card probabilities therefore do not make Plum's accusation estimate exact.[^character]

## How he plays

A character's [[belief]] says what it thinks, as a set of [[w:Probability|probabilities]]; five [[personality dials]] say what it does about it. Plum's are set to make him the careful one.[^presets]

| Dial | Plum | What it does |
|---|---|---|
| [[Accusation threshold]] | {{code:preset.Plum.accuse_threshold}} | He accuses once his chance of being right, by his own numbers, reaches this. The highest threshold of the six. |
| [[Bluff rate]] | {{code:preset.Plum.bluff_rate}} | The chance that he names a card from his own hand in a suggestion. The lowest at the table, shared with [[Mrs. Peacock]]: he asks about what he does not know. |
| [[Curiosity]] | {{code:preset.Plum.curiosity}} | How far he will walk for the room he most suspects, rather than enter the nearest. Halved from 0.8 on the Classic board, where a long walk is several turns with no suggestion. |
| [[Secrecy]] | {{code:preset.Plum.secrecy}} | When he must show a card, how strongly he prefers one that player has already seen. |
| [[Temperature]] | {{code:preset.Plum.temperature}} | How much chance enters his choices. The lowest of the six: he very nearly always takes his top-scoring option. |

Plum's threshold was chosen through measurement. His original 0.95 setting performed poorly in the sweep; 1.0 waited for proof and lost races to quicker players such as [[Miss Scarlett]]. At 0.9, he won most often on the old [[ring board]] without a wrong accusation in that arena.[^tuned]

## Record

### The quality of his numbers

{{figure:plum-budget|Plum's [[log-loss]] through a game on the Classic board, before and after his sample was raised from 2,000 to 10,000, against the [[uniform baseline]]. Lower is better.}}

The [[belief benchmark]] scores each method's probabilities against the truth at four points in a game, by [[log-loss]]: lower is better, and the [[uniform baseline]] is what a player scores who knows what the deduction floor has proved and nothing more. On the ring board, the first the game was played on, Plum was the best or joint-best of the six from three-quarters of the way through a game onward.[^ring]

The move to the [[Classic board]] on 15 September 2026 changed the benchmark results. The new self-play histories left more possibilities open at the recorded checkpoints, and his search ran out of steps in {{fact:plum.fallback.calls}} of {{fact:bench.grid.snapshots}} calls. Halfway through a game he scored {{fact:budget.grid.200k-2k.50}} against the baseline's {{fact:budget.grid.uniform.50}}: the sampling fallback scored worse than the floor-only baseline, with [[w:Sampling error|sampling noise]] contributing to the loss.[^grid]

Four budgets were then tried on the same {{fact:bench.grid.games}} games.

{{table:budget.grid|Plum's log-loss at four budgets, Classic board. Each column is a checkpoint: the share of the game's suggestions already made.}}

In these trials, increasing the sample budget improved accuracy more than increasing the search budget. Five times the samples changed halfway log-loss from {{fact:budget.grid.200k-2k.50}} to {{fact:budget.grid.200k-10k.50}}, at about twice the time per call; five times the search steps helped less and cost more. The larger sample was adopted. The measured [[w:Test suite|test-suite]] runtime rose from about {{fact:plum.suite.before}} to {{fact:plum.suite.after}} seconds.[^budget] The larger sample still trailed the uniform baseline at halfway, caught up by three-quarters and finished among the best. The trials improved the approximation without making the early search exhaustive.

### At the table

The [[arena]] measures complete games rather than probability accuracy. Its results include movement, suggestion choices, accusation timing and the opposition.

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, tables of three to six, 15 September 2026. Won, accused wrongly and never accused are percentages of the games each played.}}

Each character played 16 to 20 of the 24 games in this arena. The estimated [[w:Standard error|standard error]] of a percentage is {{fact:arena.noise}} percentage points, so small differences do not establish a reliable ranking.[^noise] Across the reported arenas, Plum, Peacock and White recorded no wrong accusations, Scarlett had the most, and Plum was at or near the top by win rate.

### With Claude in the seat

When a model plays him, choosing among his own best-scoring options within the [[leash]], the result depends on the company. At a four-seat table where all six characters took turns to play with [[Claude]], Plum's win rate fell from {{fact:twin.grid.Plum.win_base}}% to {{fact:twin.grid.Plum.win_llm}}%, a drop of about {{fact:plum.twin.sigma}} [[w:Standard deviation|standard deviations]] and the largest change any character showed. Two things worked against him at once: his opponents, with a model choosing for them, accused sooner, and his own habit of repeating himself (below) grew worse. Sixteen games cannot say in what proportion.[^twin] At a three-seat table where he alone had a model and [[Colonel Mustard]] and [[Mr. Green]] played by their numbers, it rose from {{fact:plum.claude.base.win}}% to {{fact:plum.claude.llm.win}}%.[^plumclaude] He made no wrong accusations in either comparison.

### The parking

An earlier movement rule caused Plum to loop between rooms. It gave full marks to any room reachable that turn, regardless of its envelope probability. From a corner room, a [[secret passages|secret passage]] to a room he had already ruled out could therefore score above a walk towards an unresolved room: {{fact:plum.landing.passage}} against {{fact:plum.landing.walk}}.[^landing]

In one recorded game, played with [[Claude]] in his seat, he was in the Kitchen with only the room left to find, the Conservatory or the Dining Room at even odds. He took the passage to the Study, a card he held himself, suggested a pair nobody could disprove, came back through the passage and was shown the Kitchen again. From turn {{fact:plum.loop.game.from}} to turn {{fact:plum.loop.game.to}} he did nothing else. Green won on turn {{fact:plum.loop.game.won}}.[^plumclaude] Playing alone, Plum repeated {{fact:plum.loop.alone.pct}}% of his own suggestions; with Claude, {{fact:plum.loop.claude.pct}}%, because the walk he needed scored too low to be on the model's menu at all.

The [[landing rule]] of 18 September 2026 reduced the incentive to revisit a room whose card is known to be in another player's hand. On the mixed table, Plum's exact repeats fell from {{fact:plum.loop.before}} suggestions ({{fact:plum.loop.before.pct}}%) to {{fact:plum.loop.after}} ({{fact:plum.loop.after.pct}}%). The mean game length fell by eight turns in that comparison.[^landing] The rule changes scores rather than forbids revisits.

## Memory

Plum's method recomputes from the current game's evidence and has no learned state to carry between games. [[Colonel Mustard]], [[Mrs. White]] and [[Mr. Green]] do retain method state. Separately, a model playing Plum can keep a [[logbook]] when memory is enabled. After seeing the completed deal, it writes an account in his voice, lessons and standing instructions for future games.[^logbooks]

A logbook experiment used {{fact:plum.logbook.games}} paired games on the [[ring board]], with the [[leash]] increased to 0.5 to give the model more choice. With logbooks enabled, stalls fell from {{fact:plum.logbook.stalls.off}} to {{fact:plum.logbook.stalls.on}} over the run, and from {{fact:plum.logbook.last.off}} to {{fact:plum.logbook.last.on}} in its last quarter. Plum's entries repeatedly identified "room-anchoring" and "slow-tempo". However, he also made two wrong accusations below his usual threshold while trying to increase [[w:Tempo (chess)|tempo]]. Win rates changed little: {{fact:plum.logbook.off.win}}% without logbooks and {{fact:plum.logbook.on.win}}% with them.[^logbook] The reduced stalls did not establish an overall competitive advantage.

## See also

- [[Exact posterior enumeration]], his method in full
- [[Naive Bayes]], [[Miss Scarlett]]'s method, which reaches a different answer from the same evidence
- [[Deduction floor]], the logic all six characters share
- [[Belief benchmark]] and [[Arena]], the two ways the characters are measured
- [[Landing rule]]

## References

{{references}}

[^persona]: {{cite:clude_llm/personas/Plum.md|Plum's persona, quoted throughout this section}}
[^seats]: {{cite:CLAUDE.md|Settled decisions (David's)}} A character always plays its own suspect's token.
[^module]: {{cite:clude_agents/exact_enum.py|the search (`_Search.backtrack`), the sampler (`_sample_once`) and the two budgets}}
[^aima]: {{cite:russell-norvig|Chapter 6, "Constraint Satisfaction Problems", covers backtracking search}}
[^count]: The envelopes a player's own hand leaves open, multiplied by the ways the cards they cannot see can fall into the other hands. For three players holding six cards each, two of each kind in hand: 4 × 4 × 7 envelopes and 924 ways to split the other twelve cards. For six players holding three each, one of each kind in hand: 5 × 5 × 8 envelopes and {{code:deals.6.hands}} ways to split the other fifteen.
[^character]: {{cite:clude_agents/character.py|`best_triple`: the product of the best probability in each category}}
[^presets]: {{cite:clude_agents/personality.py|`PRESETS`}}
[^tuned]: {{cite:docs/strategy-glossary.md|Tuned presets}}
[^ring]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^budget]: {{cite:docs/strategy-glossary.md|Tuned presets on the grid (Stage 1e, 2026-09-15)}}
[^noise]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}} The same section records two characters' win rates moving by 15 and 19 points between arenas in which none of their own settings changed.
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}
[^plumclaude]: {{cite:docs/strategy-glossary.md|Plum with Claude on the grid (Stage 2b, 2026-09-16)}}
[^landing]: {{cite:docs/strategy-glossary.md|The landing rule (Phase 8.0.4, 2026-09-18)}}
[^logbooks]: {{cite:docs/logbooks.md|Three tiers}}
[^logbook]: {{cite:docs/strategy-glossary.md|Plum's logbook at leash 0.5 (2026-09-14)}}

{{navbox:clude}}
