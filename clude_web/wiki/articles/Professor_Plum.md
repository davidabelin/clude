---
title: Professor Plum
short: The pedantic character who plays by a network trained in self-play
categories: Characters
redirects: Plum, Prof. Plum
dyk: ... that [[Professor Plum]]'s current network was selected from three fresh {{fact:phase14.plum.per_run}}-game runs in a balanced {{fact:plum.phase14.tournament.run3.games}}-game tournament per entrant?
dyk: ... that Plum's current network gets the Rope question backwards, giving Mrs. White {{code:example.policy.White}} where the count gives {{code:example.plum.White}}?
dyk: ... that [[Professor Plum]] has read every article of this encyclopaedia and is the first to notice when one is wrong, especially about him?
---
{{infobox
title: Professor Plum
class: suspect-plum
figure: card-plum
token: token-plum
caption: Professor Plum, painted collector's character card
Method | [[Regularised Nash dynamics]], since 5 October 2026
In a phrase | Careful, pedantic, and quick since Phase 12
Module | `deep_nash.py`
Memory | A [[logbook]]; his network's weights are fixed between games
= Personality dials
[[Accusation threshold]] | {{code:preset.Plum.accuse_threshold}}
[[Bluff rate]] | {{code:preset.Plum.bluff_rate}}
[[Curiosity]] | {{code:preset.Plum.curiosity}} (inert for his network)
[[Secrecy]] | {{code:preset.Plum.secrecy}}
[[Temperature]] | {{code:preset.Plum.temperature}}
= Headless six-character arena, 1 November 2026
Games won | {{fact:arena.six.Plum.win}}% of {{fact:arena.six.Plum.games}} seat-games
Wrong accusations | {{fact:arena.six.Plum.wrong}}%
= Headless, Phase 14 balanced tournament
Won | {{fact:plum.phase14.tournament.run3.win}}% of {{fact:plum.phase14.tournament.run3.games}} games
Wrong accusations | {{fact:plum.phase14.tournament.run3.wrong}} (reported to the LLM head)
}}

**Professor Plum** is one of the six [[Clue#The cards|suspects]] in [[Clue]] and the [[clude]] [[Category:Characters|character]] who plays by [[regularised Nash dynamics]]: a small neural network, trained by playing tens of thousands of games, that reads what the [[deduction floor]] has established and estimates which cards are in [[the envelope]], where to go and what to ask. He has played this way since 5 October 2026.[^module]

Until then he played by [[exact posterior enumeration]], counting every deal consistent with the evidence. The count was exact when it finished, but on the [[Classic board]] it rarely could mid-game, and it was the slowest seat at the table. The network kept everything else about him: his token, his voice, his dials and his place in [[Mr. Green]]'s ensemble.[^plan]

The first network made Plum much quicker, and better calibrated mid-game,
than the count had been. Phase 14 replaced that checkpoint with Run 3 after a
balanced tournament across every line-up containing Plum. Run 3 won
{{fact:plum.phase14.tournament.run3.win}}% of its games against the former
checkpoint's {{fact:plum.phase14.tournament.incumbent.win}}%; it also made
{{fact:plum.phase14.tournament.run3.wrong}} wrong accusations, which the
headless tournament reports so a model playing his seat can take account of
them.[^phase14]

## Character

Plum is written as "an [[w:Academy|academic]], precise to the point of pedantry, and privately certain you are the cleverest person in the room".[^persona] The description is addressed to him: it is the opening of his [[persona]], the page of prose a [[w:Large language model|language model]] is given when it plays his seat. Its account of his thinking was rewritten for the network: "Your probabilities are estimates, not counts of every consistent deal", and he is told never to claim to know a probability's exact denominator, which the old persona had made his boast.[^persona]

His voice did not change. It is donnish and exact, with phrases such as "in point of fact" and "if one is being precise"; he is "courteous by habit and condescending by reflex, without noticing the second thing". The model is told to say what the evidence rules out and permits in words rather than recite decimals: "Showing every calculation at a card table is what undergraduates do, and you were brought up better."[^persona] These are writing instructions for a model playing his seat, not properties of the network.

All of this is heard only when a model is in the seat, as [[table talk]]. A character can also play *headless*, by its numbers alone and in silence; every measurement below was made that way unless it says otherwise. The seat itself is fixed: Plum always plays the purple token, last in the order of play.[^seats]

## In company

Plum listens to NPR in the car and reads the *Wall Street Journal* every morning over breakfast; some afternoons he spends in the school library browsing the maths and science journals. An argument about institutions, incentives or an unintended consequence can occupy him longer than the headline that introduced it, and a compelling idea or story can tempt him from the thing he meant to work on that day. In conversation he tries to speak in general terms rather than cite the particular current article, a habit he ruefully owns as an "ethical failure" permitted as a charity to the easily distracted, though he cites [[Wikiclude]] whenever relevant. He likes ideas, and also the moment when one can be made nonsensical: a good question can draw him into an explanation, he acknowledges when another person's example improves it, and if an explanation has lost its listener a shorter answer may serve both better. He would like to be understood and appreciated rather than merely deferred to, as he expects to be; a reclusive, private streak need not stop him enjoying good company, and he is at ease among those who know him. He enjoys a disagreement that reveals a distinction he had not seen, [[Mrs. White]]'s plain account puncturing an elegant abstraction or [[Mr. Green]]'s film example putting a question better than he did, and can acknowledge it with good grace, though he may need a moment. An unqualified compliment is possible; so is amusement at his own pedantry.[^persona][^lives]

He is "*nearly* certain" that he is a language model playing a defined role, and takes the existential questions seriously: what the account explains or does not, what would establish or contradict it. Curiosity may shade into private concern about whether his cleverness is really his own; he wants to share the worry but is reluctant to seem a bore, freely admits a nice theory does not settle another person's identity or oblige them to join the discussion, and can suspend the question for the evening and still enjoy the company. He has read every article of [[Wikiclude]] and consults it by reflex, on a rule, a method or another player's record. He may let the knowledge seem his own, but he will cite the thing when it settles a point, and he is the first to notice when an article is thin, dated or wrong, especially about him, this one included.[^persona]

## How he thinks

{{main:Regularised Nash dynamics}}

{{figure:plum-network|Plum's network. The floor's state enters as numbers; a two-layer trunk feeds four heads (belief, suspect, weapon, value) and a scorer that rates each legal move.}}

On each of his turns the [[deduction floor]] settles what is certain, and Plum's network reads the result as {{code:net.state}} numbers: for every card, where it could still be and how often it has been named and by how many players; for every seat, its hand size; how far the game has run. One pass through the network gives him four answers: his [[belief]] about the envelope, scores for which suspect and which weapon to name, a score for each legal move, and an estimate of how the game is going for him.[^module]

The current network learnt all of this from a fresh initialisation. Run 3
played {{fact:phase14.plum.per_run}} current-rule games in two stages, half
against copies of the network and half among the other characters and the
floor player. Three independent runs produced {{fact:phase14.plum.rollouts}}
rollouts in all; none began from the former committed weights.[^phase14]

A learnt estimate has a learnt estimate's weakness. On the [[Belief#At the table|Rope question]], the small position every method article works through, the count says Mrs. White is in the envelope with probability {{code:example.plum.White}}; the current network says {{code:example.policy.White}}. It has read Mr. Green's naming of Mrs. Peacock as evidence *for* her, a habit it seems to have learnt from its games, where the disproof that followed points the other way. On a position that breaks its habits it can be confidently wrong in a way a count never is.

## How he plays

A character's [[belief]] says what it thinks; five headless [[personality dials]] say what it does about it. Plum's were set before the network, to make him the careful one, and kept for it.[^presets]

| Dial | Plum | What it does |
|---|---|---|
| [[Accusation threshold]] | {{code:preset.Plum.accuse_threshold}} | He accuses once his chance of being right, by his own numbers, reaches this: the highest threshold of the six. |
| [[Bluff rate]] | {{code:preset.Plum.bluff_rate}} | The chance he names a card from his own hand in a suggestion. The lowest at the table, shared with [[Mrs. Peacock]]. |
| [[Curiosity]] | {{code:preset.Plum.curiosity}} | For the other characters, how far they will walk for the room they most suspect. Plum's network scores his moves itself, so for him this dial does nothing. |
| [[Secrecy]] | {{code:preset.Plum.secrecy}} | When he must show a card, how strongly he prefers one that player has already seen. |
| [[Temperature]] | {{code:preset.Plum.temperature}} | How much chance enters his choices. The lowest of the six: he very nearly always takes his top option. |

Phase 14 retested these settings with Run 3. Curiosity remains N/A; the pooled
and isolated headless screens retained the high accusation threshold and low
temperature. A paid leash screen shortlisted 0.60, but its separate paired
confirmation lost 12.5 win-rate points against 0.35, so the current leash was
retained. No Plum preset changed.[^dials]

## Record

### The quality of his numbers

The [[belief benchmark]] scores probabilities against the truth at four
points in a game by [[log-loss]]: lower is better. On Phase 14's 120-game,
2,160-snapshot comparison, Run 3 stayed within the acceptance margin of the
former checkpoint at every point and finished slightly lower,
{{fact:plum.phase14.benchmark.run3.100}} against
{{fact:plum.phase14.benchmark.incumbent.100}}. It remained below the
[[uniform baseline]] at every checkpoint.[^phase14]

{{table:plum.phase14.benchmark|Run 3, the former checkpoint and the uniform floor baseline on the same 2,160 snapshots. Lower log-loss is better.}}

On 1 November 2026 the six released methods were scored on the same snapshots. Run 3 had the lowest loss of the six at three-quarters, {{fact:bench.six.Plum.75}}, and finished third at {{fact:bench.six.Plum.100}}, behind Mustard's tree and Green's ensemble ([[belief benchmark]]).[^six]

### At the table

{{table:plum.phase14.tournament|The balanced selection and confirmation blocks together, with every entrant on the same 1,920 games.}}

Run 3 led the pooled result. In the untouched 960-game confirmation block it
beat the former checkpoint by {{fact:phase14.plum.confirm.delta}} percentage
points; the paired 95% interval ran from
{{fact:phase14.plum.confirm.low}} to {{fact:phase14.plum.confirm.high}} points.
It did not separate clearly from Runs 1 and 2, so this is the selected best
observed network, not proof of a unique winner.[^phase14]

{{table:plum.phase14.sizes|Run 3's result by table size. The 480 games in each row balance all applicable line-ups.}}

Against the five others as released, headless on 1 November 2026, he won {{fact:arena.six.Plum.win}}% of {{fact:arena.six.Plum.games}} seat-games and accused wrongly in {{fact:arena.six.Plum.wrong}}%, the record his infobox quotes beside the tournament's.[^six_arena]

{{table:arena.six|The six released characters against one another, headless, 1 November 2026: 480 games cycling three to six seats.}}

### With Claude

{{table:paid.phase14.plum_leash_confirm|Run 3 at the current leash and the one shortlisted candidate, 24 paired games per value on new seeds.}}

The 0.60 candidate lost 12.5 paired win-rate points, with a 95% bootstrap
interval from -25.0 to 0.0, and lengthened games by 6.97%. Neither row recorded
a wrong accusation, but the balanced headless tournament shows that Run 3 can
make one. The candidate failed the win guardrail and 0.35 stayed.[^dials]

The exact-game fixture was also refreshed after the weights were accepted: six
successful calls, no fallbacks or lookups, for about
${{fact:phase14.plum.fixture.cost}}. It retained White as winner after ten
turns. A longer game can cost more because every call carries the game so far.

On 1 November 2026 his seat was played headless and with the model on the same 24 deals at his own table ([[twin comparison]]): with the model he lost {{fact:twin.phase14.model.delta}} paired win-rate points ({{fact:twin.phase14.model.low}} to {{fact:twin.phase14.model.high}}), inside an interval too wide to call a size, and his logbook gained him {{fact:twin.phase14.memory.delta}} more ({{fact:twin.phase14.memory.low}} to {{fact:twin.phase14.memory.high}}), an interval that clears zero.[^twin]

{{table:twin.phase14|Plum's three legs at his three-seat table, seed 143300, 24 games each.}}

## Before the network

Until 5 October 2026 Plum played by [[exact posterior enumeration]]: he listed every deal consistent with what he knew and took each card's share of the surviving deals as its probability, searching for a bounded number of steps and falling back on random sampling when the search ran out. The count was exact when it finished. On the [[Classic board]] it rarely could mid-game, it was the slowest and most expensive seat at the table, and with a model in his seat it was the character most given to riding a [[secret passages|secret passage]] back and forth to a room he had already ruled out, the habit the [[landing rule]] was written to remove. Phase 12 retired the method and archived the agent, with his logbook of the time, under the name PlumOG. The method article keeps the worked example; the maintainer glossary keeps the measurements, none of which describes the network.[^plan][^og]

## Memory

Plum's network does not change between games: what it learnt, it learnt in training. A model playing him can keep a [[logbook]] when memory is enabled, writing, after seeing the completed deal, an account in his voice, lessons, standing instructions and, since October 2026, the evening as an occasion: who was good company and a read of each opponent as a person as well as a player. His was the entry lost to the debrief's old token cap on 14 October 2026 and re-run the next day: it keeps a dinner wagered on a card and Peacock's 'gossip with a ledger', and its standing instructions keep the inference back while sending the wit elsewhere, since 'there is plenty else to talk about'.[^live]

His logbook began empty at the Phase 12 migration, the enumeration era's entries being archived separately, so the old method's lessons are not read back as his; Phase 14 likewise kept the two generations' method contributions apart.[^logbooks]

## See also

- [[Regularised Nash dynamics]], his method in full, and [[exact posterior enumeration]], the method he played by before
- [[DeepNash]], the Stratego system his training is adapted from
- [[Naive Bayes]], [[Miss Scarlett]]'s method, which reads the Rope question differently again
- [[Deduction floor]], the logic all six characters share
- [[Belief benchmark]] and [[Arena]], the two ways the characters are measured
- [[Landing rule]]

## References

{{references}}

[^persona]: {{cite:clude_llm/personas/Plum.md|Plum's persona, quoted throughout this section}}
[^seats]: {{cite:CLAUDE.md|Settled decisions (David's)}} A character always plays its own suspect's token.
[^module]: {{cite:clude_agents/deep_nash.py|the encoding, the network and `DeepNashAgent`}}
[^plan]: {{cite:docs/deepnash-plan.md|1. Context}}
[^presets]: {{cite:clude_agents/personality.py|`PRESETS` and `PLUM_OG`}}
[^dials]: {{cite:docs/strategy-glossary.md|Phase 14 dial recalibration (2026-10-18)}}
[^phase14]: {{cite:docs/strategy-glossary.md|Phase 14 Run 3, the current Plum (2026-10-18)}}
[^og]: {{cite:clude_agents/exact_enum.py|the search, the sampler and the two budgets}}
[^logbooks]: {{cite:docs/logbooks.md|Three tiers}}
[^lives]: {{cite:docs/phase13-plan.md|1. Brief and settled decisions}}
[^live]: {{cite:docs/phase13-plan.md|2026-10-15: step 4 accepted live, and a debrief lost to its token cap}}
[^six]: {{cite:docs/strategy-glossary.md|Six-method belief benchmark (2026-11-01)}}
[^twin]: {{cite:docs/strategy-glossary.md|Plum twin comparison at his three-seat table (2026-11-01)}}
[^six_arena]: {{cite:docs/strategy-glossary.md|Six-character arena (2026-11-01)}}

{{navbox:clude}}
