---
title: Mrs. White
short: The observant character who models opponents' repeated questions
categories: Characters
redirects: White, Mrs White, The housekeeper
dyk: ... that [[Mrs. White]] had the lowest log-loss at the first three Classic-board benchmark checkpoints and made no wrong accusations in the recorded headless arenas?
dyk: ... that [[Mrs. White]] has the highest bluff-rate preset, but made far fewer held-card suggestions in the model-piloted twin runs?
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
= Classic-board arena, 15 September 2026
Games won | {{fact:arena.grid.White.win}}% of {{fact:arena.grid.White.games}}
Wrong accusations | {{fact:arena.grid.White.wrong}}%
}}

**Mrs. White** is one of the six [[Clue#The cards|suspects]] in [[Clue]] and the observant [[clude]] [[Category:Characters|character]]. Her [[Markov chain]] method models whether each opponent's [[suggestion|suggestions]] are new or repeat earlier cards. It gives more weight to cards named often by players with high estimated repeat rates. The behavioural assumption is that unresolved cards are asked about repeatedly. This may be a useful [[w:Tell (poker)|tell]], but is not proof that a player lacks the card or that it is in [[the envelope]].[^module]

Her soft score updates use questions rather than disproofs, while the shared [[deduction floor]] still enforces known facts. In the recorded [[Classic board]] benchmark, she had the lowest [[log-loss]] at the first three checkpoints and the second-lowest at the last. The project relates this performance to floor-bot opponents, which repeatedly ask about unresolved cards.[^grid]

White's [[accusation threshold]] is the neutral {{code:preset.White.accuse_threshold}}, and she made no wrong accusations in the recorded headless arenas. She has the highest [[bluff rate]] preset and the second-highest [[secrecy]]. Her method memory stores opponents' repetition histories across games.[^presets]

## Character

White's [[persona]], given to a [[w:Large language model|language model]] playing her seat, casts her as the [[w:Housekeeper (domestic worker)|housekeeper]], "dry, watchful, and unimpressed by everyone's airs, including her own". It directs attention to repeated questions and changes of interest: "You read people, not cards." Its closing observation is "Cards do not lie; people do, and people are more interesting."[^persona] These lines express her character's outlook rather than establish her method's assumptions as facts.

Her prescribed voice is "plain, economical, a little sharp", with comments such as "You've asked about the Rope three times now". She states an observation and leaves it to the table.[^persona] In the first reviewed model-piloted games, "Mustard's stopped fishing for the Candlestick and started asking about rooms" expressed her focus on changing behaviour. The review retained her persona.[^phase6]

Headless, by her numbers alone, she is silent, and every measurement below was made that way unless it says otherwise. The seat is fixed: White always plays the white token, third in the order of play.[^seats]

## How she thinks

{{main:Markov chain}}

{{figure:white-chain|One opponent's run of suggestions, each a repeat or all new, and the two-state chain White fits to it.}}

White classifies each opponent's suggestions as *repeat* if any named card has appeared in that opponent's earlier questions, and *new* otherwise. A two-state [[w:Markov chain|Markov chain]] estimates the [[w:Stationary distribution|stationary repeat probability]]. Each unresolved card starts at a flat score; each opponent adds their naming count multiplied by that repeat probability. The floor then masks and normalises the scores into category probabilities. The chain summarises a habit; the scoring rule makes the separate assumption that naming a card increases its suspicion.[^module]

In the [[Markov chain#At the table|Rope question]], Green names Peacock and the Rope and Mustard shows him a card hidden from the observer. The Hall is known to be Green's own card. White's method favours the named cards, giving Mrs. White {{code:example.white.White}} and Mrs. Peacock {{code:example.white.Peacock}}. Plum's count gives Mrs. White {{code:example.plum.White}} instead. Mustard's tree stays at 0.5, so not every other method moves towards the count. This position illustrates how a behavioural update can conflict with the logical constraint supplied by a disproof.[^markov]

## How she plays

A character's belief says what it thinks; five [[personality dials]] say what it does about it. White's are set to make her the one who tells least.[^presets]

| Dial | White | What it does |
|---|---|---|
| [[Accusation threshold]] | {{code:preset.White.accuse_threshold}} | She accuses once her own estimate of being right reaches this. The neutral setting avoids adding an unusually low or high threshold to the method's effects. |
| [[Bluff rate]] | {{code:preset.White.bluff_rate}} | The chance that she names a card from her own hand in a suggestion. The highest at the table: she "bluffs the most". |
| [[Curiosity]] | {{code:preset.White.curiosity}} | How far she will walk for the room she most suspects rather than enter the nearest. |
| [[Secrecy]] | {{code:preset.White.secrecy}} | When she must show a card, how strongly she prefers one that player has already seen. Second only to [[Mrs. Peacock]]'s: she "gives away the least". |
| [[Temperature]] | {{code:preset.White.temperature}} | How much chance enters her choices. |

White's dials have remained unchanged since the first tuning.[^grid-presets] On the Classic board she named a card from her own hand in {{fact:arena.grid.White.named}} suggestions per game, against Plum's {{fact:arena.grid.Plum.named}}. The pooled sweeps found little win-rate change at a bluff rate of one quarter, but a fall to about one third of the original rate when characters always bluffed.[^sweeps] A secrecy sweep changed the rate of showing previously seen cards without a clear effect on wins. The notes suggest that forced single-card disproofs expose small hands regardless of the choices made on rarer multi-card answers.[^sweeps]

## Record

### The quality of her numbers

{{table:bench.ring|The six methods on the ring board, Phase 5: log-loss at four checkpoints. Lower is better.}}

In the first, random-bot benchmark, White had the highest final [[log-loss]]: {{fact:white.phase4}}, compared with {{fact:uniform.phase4}} for the baseline. Unnamed cards received zero probability and accounted for {{fact:white.phase4.zeros}}% of the loss. Phase 5 added a flat initial score so unnamed cards remained possible, and changed the game regime to floor-bot self-play.[^phase4][^glossary] In the subsequent ring-board run, she beat the [[uniform baseline]] at all four checkpoints and had the lowest halfway loss, {{fact:bench.ring.White.50}}. Her final loss was {{fact:bench.ring.White.100}}, behind three other methods.[^ring]

{{table:bench.grid|The same benchmark on the Classic board, {{fact:bench.grid.games}} games, 15 September 2026.}}

In the Classic-board benchmark, her losses at the first three checkpoints were {{fact:bench.grid.White.25}}, {{fact:bench.grid.White.50}} and {{fact:bench.grid.White.75}}, each the lowest of the six. Final loss was {{fact:bench.grid.White.100}}, second to [[Colonel Mustard]]. She answered in a fraction of a millisecond per call.[^grid]

### At the table

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, tables of three to six, 15 September 2026.}}

White made no wrong accusations in the recorded headless arenas. Her win rates were {{fact:arena.ring.White.win}}% on the tuned ring board, {{fact:arena.grid.first.White.win}}% in the first Classic-board arena and {{fact:arena.grid.White.win}}% in the second. Her settings were unchanged between the last two, but the opposition was not identical. The fifteen-percentage-point swing illustrates variability, rather than defining a universal noise floor. Each character played 16 to 20 games per arena, with estimated [[w:Standard error|standard error]] {{fact:arena.noise}} percentage points.[^ring-arena][^arena][^grid-presets] After the [[landing rule]] change, her exact repeats on the mixed table changed from {{fact:landing.repeats.White.mixed}}.[^landing]

### With Claude in the seat

In the four-seat [[Claude]] twin comparison, White's win rate rose from {{fact:twin.ring.White.win_base}}% to {{fact:twin.ring.White.win_llm}}% on the ring board. On the Classic board, she won {{fact:twin.grid.White.win_llm}}% of her model-piloted games, the highest rate in the run, as it had been headless. Her mean first-accusation turn changed from {{fact:twin.grid.White.first_base}} to {{fact:twin.grid.White.first_llm}}, and she recorded no wrong accusations. These are results from the paired runs, not a general guarantee that model piloting improves her play.[^twin-ring][^twin]

The model-piloted runs used fewer [[w:Bluff (poker)|held-card suggestions]]. Their mean count fell from {{fact:twin.ring.bluff.white.base}} to {{fact:twin.ring.bluff.white.llm}} per game on the ring board and from {{fact:twin.grid.bluff.white.base}} to {{fact:twin.grid.bluff.white.llm}} on the Classic board. The number of cards shown changed little. The notes suggest that the personas give little encouragement to bluff, but the measured counts do not establish a single motive for every choice.[^twin-ring]

## Memory

White's method memory sums four transition counts per opponent over their stored games: new to new, new to repeat, repeat to new and repeat to repeat. At a new table, a known opponent's frequencies shape a prior with the same total weight, {{code:white.prior_mass}}, as the neutral prior. A long history therefore changes its shape without overwhelming the current game's evidence. One rebuilt memory contained {{fact:white.memory.green}} transitions for Green, {{fact:white.memory.mustard}} for Mustard and {{fact:white.memory.plum}} for Plum.[^memory][^phase7] Human opponents are identified by account name, so their records follow them between tokens.[^logbooks]

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
