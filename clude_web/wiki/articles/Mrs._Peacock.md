---
title: Mrs. Peacock
short: The cautious character who accuses using evidential lower bounds
categories: Characters
redirects: Peacock, Mrs Peacock
dyk: ... that [[Mrs. Peacock]] uses belief bounds rather than decision probabilities when accusing, and made no wrong accusations in the recorded headless arenas?
dyk: ... that [[Mrs. Peacock]]'s curiosity was tried at three settings and her results were identical at all three?
---
{{infobox
title: Mrs. Peacock
class: suspect-peacock
figure: portrait-peacock
caption: Mrs. Peacock, as the encyclopaedia's engraver sees her
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
= Classic-board arena, 15 September 2026
Games won | {{fact:arena.grid.Peacock.win}}% of {{fact:arena.grid.Peacock.games}}
Wrong accusations | {{fact:arena.grid.Peacock.wrong}}%
}}

**Mrs. Peacock** is one of the six [[Clue#The cards|suspects]] in [[Clue]] and the cautious [[Category:Characters|character]] in [[clude]]. Her [[Dempster-Shafer theory|Dempster–Shafer]] method assigns evidence to sets of possible cards. For each card, it calculates *belief*, the mass supporting that card alone, and *plausibility*, the mass that does not exclude it. When a single probability is needed, each set's mass is shared equally among its members. When she [[accusation|accuses]], she instead uses the product of the selected cards' [[w:Upper and lower probabilities|belief bounds]].[^module]

Using the lower values makes her [[accusation threshold]] of {{code:preset.Peacock.accuse_threshold}} more conservative than the same threshold applied to her decision probabilities. She made no wrong accusations in the recorded headless arenas on either board, and tied with [[Professor Plum]] for wins in the tabulated [[Classic board]] arena. Her decision probabilities nevertheless had slightly worse [[log-loss]] than the [[uniform baseline]] in both benchmark regimes. The project attributes this deficit to its heuristic allocation of evidence across categories.[^glossary]

## Character

{{figure:token-peacock|Peacock's token, the fifth in the order of play.}}

Peacock's [[persona]], given to a [[w:Large language model|language model]] playing her seat, describes her as "grand, formal, socially exact, and easily scandalised". It stresses the distinction between possible, likely and proven: "A thing that is possible is not thereby likely, and a thing that is likely is not thereby proven". Her impatience is reserved for everyone else: "Other people find this slow. You find other people hasty."[^persona]

Her prescribed voice is "formal, a touch imperious", with phrases such as "One does not..." and "It has not been established that...". She disapproves of guessing and is kind to graceful losers.[^persona] In the first reviewed model-piloted games, she repeated a late-game remark almost verbatim. That example helped prompt a shared rule: say nothing rather than repeat an earlier line. The subsequent recordings were quieter instead of looping.[^phase6]

Headless, by her numbers alone, she is silent, and every measurement below was made that way unless it says otherwise. The seat is fixed: Peacock always plays the blue token, fifth in the order of play.[^seats]

## How she thinks

{{main:Dempster-Shafer theory}}

{{figure:peacock-interval|Peacock's two numbers for each open card in the Rope question: belief solid, plausibility pale, and the one number she reports between them.}}

For each category, Peacock assigns a total mass of 1 to sets of cards permitted by the [[deduction floor]]. Initially, all mass belongs to the full candidate set. Open disproof constraints add partial support for alternatives to the named cards, and Dempster's rule combines it. Belief counts support for a card alone; plausibility counts support compatible with it. The reported decision probability shares every set's mass equally. It is not generally the midpoint of belief and plausibility.[^module]

In the [[Dempster-Shafer theory#At the table|Rope question]], the observer knows that the Hall is in Green's hand, and Mustard shows Green an unseen card. Mustard therefore holds Peacock or the Rope. Applying Peacock's method to that observer's view gives Mrs. White belief {{code:example.peacock.White.bel}}, plausibility {{code:example.peacock.White.pl}} and decision probability {{code:example.peacock.White}}. Plum's equal-weight count gives {{code:example.plum.White}}. Peacock's lower-bound product for White with the Wrench is {{code:example.peacock.pair}}, below her threshold, so she would not accuse. This product is an accusation score, not an exact joint probability.[^ds]

## How she plays

A character's belief says what it thinks; five [[personality dials]] say what it does about it. Peacock's are set to make her the careful one.[^presets]

| Dial | Peacock | What it does |
|---|---|---|
| [[Accusation threshold]] | {{code:preset.Peacock.accuse_threshold}} | She accuses once the product of the three selected cards' belief bounds reaches this. It is more conservative than using her decision probabilities. |
| [[Bluff rate]] | {{code:preset.Peacock.bluff_rate}} | The chance that she names a card from her own hand in a suggestion. The lowest at the table, shared with [[Professor Plum]]. |
| [[Curiosity]] | {{code:preset.Peacock.curiosity}} | How far she will walk for the room she most suspects rather than enter the nearest. |
| [[Secrecy]] | {{code:preset.Peacock.secrecy}} | When she must show a card, how strongly she prefers one that player has already seen. The highest of the six. |
| [[Temperature]] | {{code:preset.Peacock.temperature}} | How much chance enters her choices. |

The threshold is tested against her belief rather than her probability by a function supplied with her registry entry, not by a dial, so that her profile stays five plain numbers like everyone else's and her caution comes from her method rather than from "a faked-up threshold".[^rule] None of her dials has moved since the first tuning. On the Classic board her curiosity was tried at 0.5 and 0.3 with everything else fixed, and her results were the same at all three settings, {{fact:curiosity.grid.preset.peacock}} for won, wrong and never accused: "its own answer", the notes say; her curiosity "does not reach her outcomes at this size".[^grid-presets]

## Record

### The quality of her numbers

{{table:bench.ring|The six methods on the ring board, Phase 5: log-loss at four checkpoints. Lower is better.}}

The [[belief benchmark]] scores her decision probabilities rather than the bounds used for accusation. In both recorded regimes, her log-loss was slightly higher than the [[uniform baseline]] at every checkpoint. On the Classic board, halfway loss was {{fact:bench.grid.Peacock.50}} versus {{fact:bench.grid.uniform.50}}, and final loss {{fact:bench.grid.Peacock.100}} versus {{fact:bench.grid.uniform.100}}. Final first-choice accuracy was {{fact:bench.grid.Peacock.top1}}, the same as the baseline. These results evaluate the single-number estimates, not whether the bounds are calibrated or whether caution is always advantageous.[^ring][^grid] Computation took a fraction of a millisecond per call.

{{table:bench.grid|The same benchmark on the Classic board, {{fact:bench.grid.games}} games, 15 September 2026.}}

### At the table

{{table:arena.grid|The six characters over {{fact:arena.grid.games}} games on the Classic board at their tuned presets, tables of three to six, 15 September 2026.}}

Peacock made no wrong accusations in the recorded headless arenas. In the first ring-board arena she won {{fact:arena.ring.first.Peacock.win}}% of her games; with tuned presets, {{fact:arena.ring.Peacock.win}}%. Her first accusation then came at mean turn {{fact:arena.ring.Peacock.first}}, and she never accused in {{fact:arena.ring.Peacock.never}}% of games. In the tabulated Classic-board run she won {{fact:arena.grid.Peacock.win}}%, tied with Plum, and first accused at mean turn {{fact:arena.grid.Peacock.first}}, the latest of the six. Each character played 16 to 20 games per arena, with estimated [[w:Standard error|standard error]] {{fact:arena.noise}} percentage points.[^first][^ring-arena][^arena][^grid-presets] After the [[landing rule]] change, her exact repeats on the mixed table changed from {{fact:landing.repeats.Peacock.mixed}}.[^landing]

### With Claude in the seat

When a model plays her, choosing among her own best-scoring options within the [[leash]], her caution gives a little. The leash lets a model accuse once the character's confidence is within a quarter of its threshold, and the recorded model-piloted games brought earlier accusations. At a four-seat table where every character played with [[Claude]] her first accusation came at turn {{fact:twin.grid.Peacock.first_llm}} instead of {{fact:twin.grid.Peacock.first_base}}, she never accused in {{fact:twin.grid.Peacock.never_llm}}% of games rather than {{fact:twin.grid.Peacock.never_base}}%, and her wins went from {{fact:twin.grid.Peacock.win_base}}% to {{fact:twin.grid.Peacock.win_llm}}%, about {{fact:twin.grid.sigma.peacock}} [[w:Standard deviation|standard deviations]], still with no wrong accusation. On the ring board the same comparison had left her where she was, {{fact:twin.ring.Peacock.win_base}}% both ways. Her [[w:Bluff (poker)|bluffing]] fell with the model, from {{fact:twin.grid.bluff.peacock.base}} own-card suggestions a game to {{fact:twin.grid.bluff.peacock.llm}}, as it did for every character that does not loop.[^twin][^twin-ring][^wrapper]

## Memory

Peacock's method recomputes from the floor's open facts on each call and carries no learned state between games. A model playing her seat can separately keep a [[logbook]] when memory is enabled, recording events, lessons and standing instructions after seeing the completed deal.[^logbooks]

## See also

- [[Dempster-Shafer theory]], her method in full, with the worked example and the mathematics
- [[Miss Scarlett]], the character at the other end of the caution scale, and [[Professor Plum]], who also made no wrong accusations in the tabulated headless arena
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
