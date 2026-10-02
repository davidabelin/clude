---
title: Mrs. White
short: The character who reads the players, not the cards
categories: Characters
redirects: White, Mrs White, The housekeeper
dyk: ... that [[Mrs. White]] had the best belief of the six for most of a game on the Classic board, and has never accused wrongly in any arena on any board?
dyk: ... that [[Mrs. White]] bluffs more than any other character, and that with a language model in her seat she all but stopped?
---
{{infobox
title: Mrs. White
class: suspect-white
figure: token-white
caption: White's token, the third in the order of play
Method | [[Markov chain]]
In a phrase | Reads people rather than cards
Module | `markov.py`
Memory | How each opponent has asked their questions, game after game
= Personality dials
[[Accusation threshold]] | {{code:preset.White.accuse_threshold}} (neutral)
[[Bluff rate]] | {{code:preset.White.bluff_rate}}
[[Curiosity]] | {{code:preset.White.curiosity}}
[[Secrecy]] | {{code:preset.White.secrecy}}
[[Temperature]] | {{code:preset.White.temperature}}
= Record on the Classic board
Games won | {{fact:arena.grid.White.win}}% of {{fact:arena.grid.White.games}}
Wrong accusations | {{fact:arena.grid.White.wrong}}%
}}

**Mrs. White** is one of the six [[Clue#The cards|suspects]] of [[Clue]] and, in [[clude]], the [[Category:Characters|character]] who reads the players instead of the cards. Her method is a [[Markov chain]] fitted to each opponent's run of [[suggestion|suggestions]]: a player who keeps naming a card they have named before has, she reasons, not yet been shown it and does not hold it, and a card nobody can be shown may well be in [[the envelope]]. She notices [[w:Tell (poker)|tells]] in how people behave long before she knows what is hidden, and she is, in her own description, better at knowing who is about to win than at knowing what they will say.

The method is the one of the six that takes no notice of who showed what. It reads the asking. That makes her the strongest reasoner at the table through the middle of a game, where players re-name the cards they have not resolved and her chain reads them doing it, and a weaker one at the very end, where the facts the [[deduction floor]] has collected say more than any habit. On the [[Classic board]] hers is the best [[belief]] of the six at every checkpoint until the last.[^grid]

She plays patiently and tells little. Her [[accusation threshold]] is the neutral {{code:preset.White.accuse_threshold}}, kept so that any wrong accusation would be the method's, and she has not made one in any arena on either board. She [[bluffing|bluffs]] more than any other character and gives away her own cards least willingly. She is one of three characters whose method remembers from game to game, and what hers remembers is people.

## Character

White is written as "the [[w:Housekeeper (domestic worker)|housekeeper]], dry, watchful, and unimpressed by everyone's airs, including her own."[^persona] The description is addressed to her: it is the opening of her [[persona]], the page of prose a [[w:Large language model|language model]] is given when it plays her seat. The persona describes the method from the inside: "You read people, not cards. Who keeps naming the same suspect, turn after turn; who changed their tune after being shown something; who has gone quiet. A card somebody keeps asking about is a card they do not hold. A player who has stopped fishing is a player who is close." It ends on a preference rather than a rule: "Cards do not lie; people do, and people are more interesting."[^persona]

Her voice is "plain, economical, a little sharp. You say what you have noticed about someone and let it sit." The persona gives her two lines as examples, "You've asked about the Rope three times now" and "He's gone quiet. He knows something", and one manner: "polite in the way that staff are polite: precisely, and not one inch further."[^persona] In the first recorded games with a model in every seat the method was audible in the voice without being asked for: "Mustard's stopped fishing for the Candlestick and started asking about rooms", which the notes record as "the method audible in the voice, which is what the personas were for". She needed no edit.[^phase6]

Headless, by her numbers alone, she is silent, and every measurement below was made that way unless it says otherwise. The seat is fixed: White always plays the white token, third in the order of play.[^seats]

## How she thinks

{{main:Markov chain}}

{{figure:white-chain|One opponent's run of suggestions, each a repeat or all new, and the two-state chain White fits to it.}}

For each opponent White keeps a tally of the cards they have named and a string of two symbols, one per suggestion of theirs: *repeat* if it named a card they had named before, *new* if not. To the string she fits the simplest model of a sequence there is, a two-state [[w:Markov chain|Markov chain]], and reads from it the [[w:Stationary distribution|long-run chance]] that the opponent is repeating. Every card the floor has not placed starts at a flat score, and each opponent adds to every card they have named their naming count times that chance; the floor then strikes out what it has ruled out and the scores become probabilities within each category.[^module]

On the worked example the method articles share, the Rope question, she is the odd one out. Mr. Green has suggested Mrs. Peacock and the Rope, and Colonel Mustard has shown him a card. Every other method reads the showing, which the floor hands them as "Mustard holds Peacock or the Rope", and lowers Peacock and the Rope; [[Professor Plum]]'s count puts Mrs. White in the envelope at {{code:example.plum.White}}. White's chain reads the asking, and Green's asking about Peacock and the Rope makes them a little more suspect: Mrs. White at {{code:example.white.White}}, Mrs. Peacock at {{code:example.white.Peacock}}. In this one position the habit points the wrong way; over a longer game the two readings converge, because the cards a player keeps naming are, usually, the ones nobody has shown them.[^markov]

## How she plays

A character's belief says what it thinks; five [[personality dials]] say what it does about it. White's are set to make her the one who tells least.[^presets]

| Dial | White | What it does |
|---|---|---|
| [[Accusation threshold]] | {{code:preset.White.accuse_threshold}} | She accuses once her own estimate of being right reaches this. The neutral setting, kept on purpose, so that a wrong accusation of hers would be the method's. |
| [[Bluff rate]] | {{code:preset.White.bluff_rate}} | The chance that she names a card from her own hand in a suggestion. The highest at the table: she "bluffs the most". |
| [[Curiosity]] | {{code:preset.White.curiosity}} | How far she will walk for the room she most suspects rather than enter the nearest. |
| [[Secrecy]] | {{code:preset.White.secrecy}} | When she must show a card, how strongly she prefers one that player has already seen. Second only to [[Mrs. Peacock]]'s: she "gives away the least". |
| [[Temperature]] | {{code:preset.White.temperature}} | How much chance enters her choices. |

None of her dials has moved since the first tuning.[^grid-presets] The bluff rate is the one that shows: on the Classic board she names a card of her own in {{fact:arena.grid.White.named}} suggestions a game, against {{fact:arena.grid.Plum.named}} for Plum, and the sweeps that set the presets found bluffing a quarter of the time cost nothing and bluffing always cut the win rate to a third.[^sweeps] Her secrecy is the dial the project has least confidence in: a sweep of it moved the re-show rate it directly controls and nothing else, since a hand of a few cards gets exposed by forced single-card disproofs whatever a character does with its rare choices.[^sweeps]

## Record

### The quality of her numbers

{{table:bench.ring|The six methods on the ring board, Phase 5: log-loss at four checkpoints. Lower is better.}}

On the first benchmark of all, her belief was the worst of the six by a distance, a [[log-loss]] of {{fact:white.phase4}} against the baseline's {{fact:uniform.phase4}} at the end of a game, {{fact:white.phase4.zeros}} per cent of it from cards no opponent had yet named, which her method then read as impossible. Phase 5 gave every unplaced card a flat starting score, so that an unnamed card is merely unsuspicious, and left the method otherwise unchanged; that and the floor-bot games, where players do re-name what they have not resolved, "turned him from the worst belief of the six into the second-best mid-game".[^phase4][^glossary] On the ring board she then beat the [[uniform baseline]] at every checkpoint and had the best score of the six at the halfway mark, {{fact:bench.ring.White.50}}; at the end, {{fact:bench.ring.White.100}}, three methods that read the floor's facts more closely were ahead of her.[^ring]

{{table:bench.grid|The same benchmark on the Classic board, {{fact:bench.grid.games}} games, 15 September 2026.}}

On the Classic board she is the best method at every checkpoint until the end: {{fact:bench.grid.White.25}}, {{fact:bench.grid.White.50}} and {{fact:bench.grid.White.75}}, and at the end {{fact:bench.grid.White.100}}, second only to [[Colonel Mustard]]. She answers in a fraction of a millisecond.[^grid]

### At the table

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, tables of three to six, 15 September 2026.}}

White "wins by patience". She has not accused wrongly in any arena on either board, and her wins have been {{fact:arena.ring.White.win}}% on the ring board at the tuned presets, {{fact:arena.grid.first.White.win}}% in the Classic board's first arena and {{fact:arena.grid.White.win}}% in its second, in neither of which anything of hers changed. The fifteen-point swing between the last two is the measurement's noise floor, and the notes name it as the reason nothing is decided on a single arena: a character plays 16 to 20 of the 24 games, and a percentage carries a [[w:Standard error|standard error]] of {{fact:arena.noise}} points.[^ring-arena][^arena][^grid-presets] The [[landing rule]] took her exact repeats of her own earlier suggestions on the mixed table from {{fact:landing.repeats.White.mixed}}.[^landing]

### With Claude in the seat

When a model plays her, choosing among her own best-scoring options within the [[leash]], she stays the patient one and wins more. At a four-seat table where every character played with [[Claude]] her wins went from {{fact:twin.ring.White.win_base}}% to {{fact:twin.ring.White.win_llm}}% on the ring board, and on the Classic board she won {{fact:twin.grid.White.win_llm}}% of her games, the most of anyone, with and without the model; her first accusation came at turn {{fact:twin.grid.White.first_llm}} instead of {{fact:twin.grid.White.first_base}}, and she was wrong in none.[^twin-ring][^twin]

What the model changed was her [[w:Bluff (poker)|bluffing]]. Her suggestions naming one of her own cards fell from {{fact:twin.ring.bluff.white.base}} a game to {{fact:twin.ring.bluff.white.llm}} on the ring board and from {{fact:twin.grid.bluff.white.base}} to {{fact:twin.grid.bluff.white.llm}} on the Classic board, the largest fall of any character, while the cards she actually gave away barely moved. The model treats naming its own card as a wasted question rather than a feint, and since the project's settled view is that characters should learn what over-sharing costs rather than be designed away from it, the notes mark this as a dial to revisit: the personas currently give them no reason to pay for a bluff.[^twin-ring]

## Memory

White's method remembers people. For every opponent she has met, the four counts her chain is fitted from (new to new, new to repeat, repeat to new, repeat to repeat) are summed over every stored game that opponent played and kept under their name, whether or not she sat at the same table. At a new table the neutral prior for a known opponent is replaced by their own frequencies, spread over the same {{code:white.prior_mass}} phantom observations the prior had, so that the live sequence weighs exactly as before and only the chain's starting shape is informed by the past. The choice is deliberate: "a hundred games of history should not drown the regime he is watching now". Rebuilt from one measurement run's stored games, her memory held {{fact:white.memory.green}} transitions for Green, {{fact:white.memory.mustard}} for Mustard and {{fact:white.memory.plum}} for Plum.[^memory][^phase7] A person at a web table gets a dossier the same way, under their account's name, so that her read on them follows them to whichever token they play next.[^logbooks]

Like every character she can also keep a narrative [[logbook]], written by a model after each game it played her seat.

## See also

- [[Markov chain]], her method in full, with the worked example and the mathematics
- [[Colonel Mustard]] and [[Mr. Green]], the other two characters whose methods remember
- [[Bluffing]] and [[Bluff rate]]
- [[Professor Plum]] and [[Exact posterior enumeration]], which read the answer where she reads the question
- [[Belief benchmark]] and [[Arena]]

## References

{{references}}

[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^persona]: {{cite:clude_llm/personas/White.md|White's persona, quoted throughout this section}}
[^phase6]: {{cite:docs/phase6-plan.md|6c, the real backend (2026-09-12; live checks done 2026-09-13)}}
[^seats]: {{cite:CLAUDE.md|Settled decisions (David's)}} A character always plays its own suspect's token.
[^module]: {{cite:clude_agents/markov.py|`suggestion_patterns`, `_stationary_repeat_probability` and `MarkovAgent.select_action`}}
[^markov]: Computed by the live module on the Rope question; see [[Markov chain#At the table]].
[^presets]: {{cite:clude_agents/personality.py|`PRESETS`, White's entry and its note}}
[^grid-presets]: {{cite:docs/strategy-glossary.md|Tuned presets on the grid (Stage 1e, 2026-09-15)}}
[^sweeps]: {{cite:docs/strategy-glossary.md|Dial sweeps}}
[^phase4]: {{cite:docs/strategy-glossary.md|Phase 4 benchmark results (RandomBot regime, historical)}}
[^glossary]: {{cite:docs/strategy-glossary.md|White -- Markov model over suggestion sequences}}
[^ring]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^ring-arena]: {{cite:docs/strategy-glossary.md|Arena, tuned presets}}
[^arena]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}
[^landing]: {{cite:docs/strategy-glossary.md|The landing rule (Phase 8.0.4, 2026-09-18)}}
[^twin-ring]: {{cite:docs/strategy-glossary.md|Twin comparison (2026-09-13)}}
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}
[^memory]: {{cite:docs/logbooks.md|Tier 1: method memory}}
[^phase7]: {{cite:docs/phase7-plan.md|7b, method memory (2026-09-14)}}
[^logbooks]: {{cite:docs/logbooks.md|The debrief}}

{{navbox:clude}}
