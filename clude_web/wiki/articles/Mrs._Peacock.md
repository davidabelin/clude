---
title: Mrs. Peacock
short: The character who will not guess
categories: Characters
redirects: Peacock, Mrs Peacock
dyk: ... that [[Mrs. Peacock]] accuses on a number that stays at nothing until the evidence singles a card out, and has never accused wrongly in any arena?
dyk: ... that [[Mrs. Peacock]]'s curiosity was tried at three settings and her results were identical at all three?
---
{{infobox
title: Mrs. Peacock
class: suspect-peacock
figure: token-peacock
caption: Peacock's token, the fifth in the order of play
Method | [[Dempster-Shafer theory]]
In a phrase | Cautious; will not commit until the alternatives collapse
Module | `dempster_shafer.py`
Memory | A [[logbook]] only; her method remembers nothing
= Personality dials
[[Accusation threshold]] | {{code:preset.Peacock.accuse_threshold}}, on her lower bound
[[Bluff rate]] | {{code:preset.Peacock.bluff_rate}}
[[Curiosity]] | {{code:preset.Peacock.curiosity}}
[[Secrecy]] | {{code:preset.Peacock.secrecy}}
[[Temperature]] | {{code:preset.Peacock.temperature}}
= Record on the Classic board
Games won | {{fact:arena.grid.Peacock.win}}% of {{fact:arena.grid.Peacock.games}}
Wrong accusations | {{fact:arena.grid.Peacock.wrong}}%
}}

**Mrs. Peacock** is one of the six [[Clue#The cards|suspects]] of [[Clue]] and, in [[clude]], the [[Category:Characters|character]] who declines to guess. Her method is [[Dempster-Shafer theory]], a [[w:Dempster–Shafer theory|theory of evidence]] that keeps two numbers for every card where the others keep one: a *belief*, how far the evidence positively supports it, and a *plausibility*, how far the evidence fails to rule it out. The gap between the two is what she does not know, and she leaves it open rather than filling it with a guess. When a single probability is required she reports the middle of the two; when she decides whether to [[accusation|accuse]], she uses the [[w:Upper and lower probabilities|lower one]].

That choice is the character. A belief, in her sense, stays at nothing for a card until evidence singles it out, so her [[accusation threshold]] of {{code:preset.Peacock.accuse_threshold}}, applied to it, is "far stricter than 0.7 would be for anyone else". She accuses late and, in every arena on both [[Classic board|boards]], never wrongly, and on the Classic board she is level with [[Professor Plum]] at the top of the table. Her single number, measured against the truth, is slightly worse than that of a player who knows only what is certain, which the project's notes trace to one modelling choice in how a clue about three cards is shared among the three categories; the caution is unaffected, because it comes from the bound the benchmark does not score.[^glossary]

## Character

Peacock is written as "grand, formal, socially exact, and easily scandalised. Standards matter to you, and so does being seen to have them."[^persona] The description is addressed to her: it is the opening of her [[persona]], the page of prose a [[w:Large language model|language model]] is given when it plays her seat. The persona describes the method from the inside, and does it unusually exactly: "You keep two numbers for everything. One is what the evidence has actually established: the weight of proof behind a card, which stays at nothing until something singles that card out. The other is what the evidence has merely failed to rule out. You never confuse the two. A thing that is possible is not thereby likely, and a thing that is likely is not thereby proven, and you will not say 'it was the Colonel' on the strength of the second when the first is still empty." It ends: "Other people find this slow. You find other people hasty."[^persona]

Her voice is "formal, a touch imperious, with a strong sense of what is and is not done. 'One does not...' and 'It has not been established that...' are yours." She disapproves of guessing "the way you disapprove of elbows on the table", and is "kind, in a stiff way, to anyone who is losing gracefully, and withering to anyone who is winning loudly."[^persona] In the first recorded games with a model in every seat her voice found the one fault that was fixed for everyone: late in a game, when the deduction had narrowed and every remaining remark wanted to be the same remark, she restated a line almost verbatim three turns apart. The rule that followed, in the house rules every character is given, is to say nothing rather than restate; in the re-recorded games the table went quiet instead of looping.[^phase6]

Headless, by her numbers alone, she is silent, and every measurement below was made that way unless it says otherwise. The seat is fixed: Peacock always plays the blue token, fifth in the order of play.[^seats]

## How she thinks

{{main:Dempster-Shafer theory}}

{{figure:peacock-interval|Peacock's two numbers for each open card in the Rope question: belief solid, plausibility pale, and the one number she reports between them.}}

For each category, suspects, weapons and rooms, Peacock keeps a *mass function*: a weight of 1 shared out among sets of the cards the [[deduction floor]] still allows in the envelope. At the start all of it sits on the whole set, which is her way of saying she knows nothing beyond what is certain. Each open fact the floor hands her, "this player holds at least one of these cards", becomes one piece of evidence, weight on the cards it does *not* name, and the pieces are combined by Dempster's rule. A card's belief is the weight on it alone; its plausibility the weight on every set that contains it. When one number is needed each set's weight is split evenly among its members.[^module]

On the worked example the method articles share, the Rope question, Colonel Mustard has shown Mr. Green a card after a suggestion of Mrs. Peacock and the Rope, so he holds one of the two. Peacock's belief in Mrs. White being the envelope's suspect is {{code:example.peacock.White.bel}}, her plausibility {{code:example.peacock.White.pl}}, and the number she reports {{code:example.peacock.White}}, a little past Plum's exact {{code:example.plum.White}}. But her belief in the pair she would have to name, White with the Wrench, is only {{code:example.peacock.pair}}, far below her threshold. The number is in her favour and she still will not say it.[^ds]

## How she plays

A character's belief says what it thinks; five [[personality dials]] say what it does about it. Peacock's are set to make her the careful one.[^presets]

| Dial | Peacock | What it does |
|---|---|---|
| [[Accusation threshold]] | {{code:preset.Peacock.accuse_threshold}} | She accuses once her *belief* in the three cards reaches this. Applied to a lower bound, it is the strictest test at the table. |
| [[Bluff rate]] | {{code:preset.Peacock.bluff_rate}} | The chance that she names a card from her own hand in a suggestion. The lowest at the table, shared with [[Professor Plum]]. |
| [[Curiosity]] | {{code:preset.Peacock.curiosity}} | How far she will walk for the room she most suspects rather than enter the nearest. |
| [[Secrecy]] | {{code:preset.Peacock.secrecy}} | When she must show a card, how strongly she prefers one that player has already seen. The highest of the six. |
| [[Temperature]] | {{code:preset.Peacock.temperature}} | How much chance enters her choices. |

The threshold is tested against her belief rather than her probability by a function supplied with her registry entry, not by a dial, so that her profile stays five plain numbers like everyone else's and her caution comes from her method rather than from "a faked-up threshold".[^rule] None of her dials has moved since the first tuning. On the Classic board her curiosity was tried at 0.5 and 0.3 with everything else fixed, and her results were the same at all three settings, {{fact:curiosity.grid.preset.peacock}} for won, wrong and never accused: "its own answer", the notes say; her curiosity "does not reach her outcomes at this size".[^grid-presets]

## Record

### The quality of her numbers

{{table:bench.ring|The six methods on the ring board, Phase 5: log-loss at four checkpoints. Lower is better.}}

The [[belief benchmark]] scores the single number she reports, since that is what the rest of the system uses, and on both boards it trails the [[uniform baseline]] by a little at every checkpoint: on the Classic board {{fact:bench.grid.Peacock.50}} against {{fact:bench.grid.uniform.50}} at the halfway mark and {{fact:bench.grid.Peacock.100}} against {{fact:bench.grid.uniform.100}} at the end, with her first choice right {{fact:bench.grid.Peacock.top1}} of the time, the baseline's own figure. The notes put it down to the apportioning rule in her method and record that nothing depends on it yet; the caution, which comes from the belief bound, is unaffected.[^ring][^grid] She answers in a fraction of a millisecond.

{{table:bench.grid|The same benchmark on the Classic board, {{fact:bench.grid.games}} games, 15 September 2026.}}

### At the table

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, tables of three to six, 15 September 2026.}}

Peacock has not accused wrongly in any arena on either board. In the ring board's first arena she won {{fact:arena.ring.first.Peacock.win}}% of her games, the most of anyone; at the tuned presets, {{fact:arena.ring.Peacock.win}}%, with her first accusation at turn {{fact:arena.ring.Peacock.first}} and no accusation at all in {{fact:arena.ring.Peacock.never}}% of her games. On the Classic board she won {{fact:arena.grid.Peacock.win}}%, level with Plum at the top of the table, her first accusation coming at turn {{fact:arena.grid.Peacock.first}}, the latest of the six. What held across every arena on the Classic board was the pattern at the edges: Plum, Peacock and White never accused wrongly and [[Miss Scarlett]] did so most. A character plays 16 to 20 of the 24 games, so each percentage carries a [[w:Standard error|standard error]] of {{fact:arena.noise}} points.[^first][^ring-arena][^arena][^grid-presets] The [[landing rule]] took her exact repeats of her own earlier suggestions on the mixed table from {{fact:landing.repeats.Peacock.mixed}}, the second-largest fall after Plum's.[^landing]

### With Claude in the seat

When a model plays her, choosing among her own best-scoring options within the [[leash]], her caution gives a little. The leash lets a model accuse once the character's confidence is within a quarter of its threshold, and a model is less patient than a lower bound. At a four-seat table where every character played with [[Claude]] her first accusation came at turn {{fact:twin.grid.Peacock.first_llm}} instead of {{fact:twin.grid.Peacock.first_base}}, she accused in {{fact:twin.grid.Peacock.never_llm}}% of games rather than never in {{fact:twin.grid.Peacock.never_base}}%, and her wins went from {{fact:twin.grid.Peacock.win_base}}% to {{fact:twin.grid.Peacock.win_llm}}%, about {{fact:twin.grid.sigma.peacock}} [[w:Standard deviation|standard deviations]], still with no wrong accusation. On the ring board the same comparison had left her where she was, {{fact:twin.ring.Peacock.win_base}}% both ways. Her [[w:Bluff (poker)|bluffing]] fell with the model, from {{fact:twin.grid.bluff.peacock.base}} own-card suggestions a game to {{fact:twin.grid.bluff.peacock.llm}}, as it did for every character that does not loop.[^twin][^twin-ring][^wrapper]

## Memory

Peacock's method has nothing to remember: it starts every game from the floor's open facts and combines them afresh on every call. What she can carry from game to game is a [[logbook]], which only a model-piloted seat writes: after each game the model, shown the whole deal face up, writes an entry in her voice with what happened, what she learned, and a set of standing instructions for next time.[^logbooks]

## See also

- [[Dempster-Shafer theory]], her method in full, with the worked example and the mathematics
- [[Miss Scarlett]], the character at the other end of the caution scale, and [[Professor Plum]], who shares her clean sheet
- [[Accusation]] and [[Accusation threshold]]
- [[Belief]], where the six methods' answers to the Rope question are compared
- [[Belief benchmark]] and [[Arena]]

## References

{{references}}

[^glossary]: {{cite:docs/strategy-glossary.md|Peacock -- Dempster-Shafer belief/plausibility}}
[^persona]: {{cite:clude_llm/personas/Peacock.md|Peacock's persona, quoted throughout this section}}
[^phase6]: {{cite:docs/phase6-plan.md|6c, the real backend (2026-09-12; live checks done 2026-09-13)}}
[^seats]: {{cite:CLAUDE.md|Settled decisions (David's)}} A character always plays its own suspect's token.
[^module]: {{cite:clude_agents/dempster_shafer.py|`_category_mass`, `_combine`, `_belief`, `_plausibility` and `_pignistic`}}
[^ds]: Computed by the live module on the Rope question; see [[Dempster-Shafer theory#At the table]].
[^presets]: {{cite:clude_agents/personality.py|`PRESETS`, Peacock's entry and its note}}
[^rule]: {{cite:docs/architecture.md|Personality layer (Phase 5c)}}
[^grid-presets]: {{cite:docs/strategy-glossary.md|Tuned presets on the grid (Stage 1e, 2026-09-15)}}
[^ring]: {{cite:docs/strategy-glossary.md|Belief benchmark, FloorBot regime (Phase 5)}}
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^first]: {{cite:docs/strategy-glossary.md|Arena, first pass (untuned presets)}}
[^ring-arena]: {{cite:docs/strategy-glossary.md|Arena, tuned presets}}
[^arena]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}
[^landing]: {{cite:docs/strategy-glossary.md|The landing rule (Phase 8.0.4, 2026-09-18)}}
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}
[^twin-ring]: {{cite:docs/strategy-glossary.md|Twin comparison (2026-09-13)}}
[^wrapper]: {{cite:docs/llm-wrapper.md|What happens on one decision}}
[^logbooks]: {{cite:docs/logbooks.md|Three tiers}}

{{navbox:clude}}
