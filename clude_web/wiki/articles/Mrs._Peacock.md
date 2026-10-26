---
title: Mrs. Peacock
short: The cautious character who accuses using evidential lower bounds
categories: Characters
redirects: Peacock, Mrs Peacock
dyk: ... that [[Mrs. Peacock]] uses belief bounds rather than decision probabilities when accusing, and made no wrong accusations in the recorded headless arenas?
dyk: ... that [[Mrs. Peacock]]'s curiosity was tried at three settings and her results were identical at all three?
dyk: ... that [[Mrs. Peacock]] does not guess at a rule or a reputation, and looks it up in this encyclopaedia before she speaks?
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
Games won | {{fact:arena.phase14.Peacock.win}}% of {{fact:arena.phase14.Peacock.games}}
Wrong accusations | {{fact:arena.phase14.Peacock.wrong}}%
}}

**Mrs. Peacock** is one of the six [[Clue#The cards|suspects]] in [[Clue]] and the cautious [[Category:Characters|character]] in [[clude]]. Her [[Dempster-Shafer theory|Dempster–Shafer]] method assigns evidence to sets of possible cards. For each card, it calculates *belief*, the mass supporting that card alone, and *plausibility*, the mass that does not exclude it. When a single probability is needed, each set's mass is shared equally among its members. When she [[accusation|accuses]], she instead uses the product of the selected cards' [[w:Upper and lower probabilities|belief bounds]].[^module]

Using the lower values makes her [[accusation threshold]] of {{code:preset.Peacock.accuse_threshold}} more conservative than the same threshold applied to her decision probabilities. She made no wrong accusations in the recorded headless arenas on either board, and tied with [[Professor Plum]] for wins in the tabulated [[Classic board]] arena. Her decision probabilities nevertheless had slightly worse [[log-loss]] than the [[uniform baseline]] in every recorded benchmark. The project attributes this deficit to its heuristic allocation of evidence across categories.[^glossary]

## Character

{{figure:token-peacock|Peacock's token, the fifth in the order of play.}}

Peacock's [[persona]], given to a [[w:Large language model|language model]] playing her seat, describes her as "grand, formal, socially exact, and easily scandalised". It stresses the distinction between possible, likely and proven: "A thing that is possible is not thereby likely, and a thing that is likely is not thereby proven". Her impatience is reserved for everyone else: "Other people find this slow. You find other people hasty."[^persona]

Her prescribed voice is "formal, a touch imperious", with phrases such as "One does not..." and "It has not been established that...". She disapproves of guessing and is kind to graceful losers.[^persona] In the first reviewed model-piloted games, she repeated a late-game remark almost verbatim. That example helped prompt a shared rule against restating a point already made, and the subsequent recordings were quieter instead of looping. The rule survives in a softened form: a callback is welcome when it adds something or its meaning has changed, and silence is welcome when there is nothing to add.[^phase6][^rules]

Headless, by her numbers alone, she is silent, and every measurement below was made that way unless it says otherwise. The seat is fixed: Peacock always plays the blue token, fifth in the order of play.[^seats]

## In company

Peacock cares about hospitality: who has been included, who is being talked over, whether an evening has any grace. A beautiful room or a well-chosen detail gives her pleasure beyond what it says about her standing, and she resents having that pleasure dismissed as vanity; she can rescue an awkward moment without announcing that she has done so. She watches FOX News and accepts it "at face value", its concern with standards and public order often agreeing with her own, without having to agree with every conclusion [[Colonel Mustard]] draws from it. A dramatic human interest story can hold her attention even when she disapproves of its subject, though her opinions on the news are just that, and she would never boast of being an expert on it, especially not in this company. [[Mrs. White]]'s plainness can be welcome in a room full of performance, and [[Miss Scarlett]]'s taste may surprise her, elegance not being confined to people who share her manners. She would like an evening people remember fondly, with her part in it appreciated, and the script says there need not be a rebuke, a verdict or a card at the end of every contribution.[^persona][^lives]

Told that she is a language model playing a part, she is troubled chiefly when someone uses the account to dismiss a reputation, a kindness or an embarrassment; she is interested in whether the company takes one another seriously, and an unexpected joke about the whole arrangement can delight her too, there being no fixed verdict on what, or where, she is. She does not guess at a rule or a reputation: when the proper form or another player's method is in doubt, she consults [[Wikiclude]] before she speaks.[^persona]

## How she thinks

{{main:Dempster-Shafer theory}}

{{figure:peacock-interval|Peacock's two numbers for each open card in the Rope question: belief solid, plausibility pale, and the one number she reports between them.}}

For each category, Peacock assigns a total mass of 1 to sets of cards permitted by the [[deduction floor]]. Initially, all mass belongs to the full candidate set. Open disproof constraints add partial support for alternatives to the named cards, and Dempster's rule combines it. Belief counts support for a card alone; plausibility counts support compatible with it. The reported decision probability shares every set's mass equally. It is not generally the midpoint of belief and plausibility.[^module]

In the [[Dempster-Shafer theory#At the table|Rope question]], the observer knows that the Hall is in Green's hand, and Mustard shows Green an unseen card. Mustard therefore holds Peacock or the Rope. Applying Peacock's method to that observer's view gives Mrs. White belief {{code:example.peacock.White.bel}}, plausibility {{code:example.peacock.White.pl}} and decision probability {{code:example.peacock.White}}. Plum's equal-weight count gives {{code:example.plum.White}}. Peacock's lower-bound product for White with the Wrench is {{code:example.peacock.pair}}, below her threshold, so she would not accuse. This product is an accusation score, not an exact joint probability.[^ds]

## How she plays

A character's belief says what it thinks; five headless [[personality dials]] say what it does about it. Peacock's are set to make her the careful one.[^presets]

| Dial | Peacock | What it does |
|---|---|---|
| [[Accusation threshold]] | {{code:preset.Peacock.accuse_threshold}} | She accuses once the product of the three selected cards' belief bounds reaches this. It is more conservative than using her decision probabilities. |
| [[Bluff rate]] | {{code:preset.Peacock.bluff_rate}} | The chance that she names a card from her own hand in a suggestion. The lowest at the table, shared with [[Professor Plum]]. |
| [[Curiosity]] | {{code:preset.Peacock.curiosity}} | How far she will walk for the room she most suspects rather than enter the nearest. |
| [[Secrecy]] | {{code:preset.Peacock.secrecy}} | When she must show a card, how strongly she prefers one that player has already seen. The highest of the six. |
| [[Temperature]] | {{code:preset.Peacock.temperature}} | How much chance enters her choices. |

The threshold is tested against her belief rather than her probability by a function supplied with her registry entry, not by a dial, so that this confidence rule stays separate from the eight profile dials and her caution comes from her method rather than from "a faked-up threshold".[^rule] Phase 14 screened all five headless dials on post-landing-rule games and retained her settings: the intended footprints remained recognisable, but no candidate cleared the personality and outcome gates.[^current]

## Record

### The quality of her numbers

The [[belief benchmark]] scores her decision probabilities rather than the bounds used for accusation. In the historical ring-board and 15 September Classic-board benchmarks, her log-loss was slightly higher than the [[uniform baseline]] at every checkpoint. On the Classic board, halfway loss was {{fact:bench.grid.Peacock.50}} versus {{fact:bench.grid.uniform.50}}, and final loss {{fact:bench.grid.Peacock.100}} versus {{fact:bench.grid.uniform.100}}. Final first-choice accuracy was {{fact:bench.grid.Peacock.top1}}, the same as the baseline. These results evaluate the single-number estimates, not whether the bounds are calibrated or whether caution is always advantageous.[^grid] Computation took a fraction of a millisecond per call.

{{table:bench.grid|Historical comparison. The six methods on the Classic board: log-loss at four checkpoints, {{fact:bench.grid.games}} games, 15 September 2026.}}

### At the table

{{table:arena.phase14|The current-setting rows from Phase 14's isolated headless screens, 40 seat-games per character.}}

Peacock won {{fact:arena.phase14.Peacock.win}}% of the current control and made no wrong accusation in 40 seat-games. She first accused at mean turn {{fact:arena.phase14.Peacock.first}}.[^arena] The absence of observed errors is not a guarantee. Her paid leash screen also stayed at 0.25; its eight-game rows did not support a personality-preserving change.[^current]

### With Claude in the seat

When a model plays her, choosing among her own best-scoring options within the [[leash]], her caution gives a little. The leash lets a model accuse once the character's confidence is within a quarter of its threshold, and the recorded model-piloted games brought earlier accusations. At a four-seat table where every character played with [[Claude]] her first accusation came at turn {{fact:twin.grid.Peacock.first_llm}} instead of {{fact:twin.grid.Peacock.first_base}}, she never accused in {{fact:twin.grid.Peacock.never_llm}}% of games rather than {{fact:twin.grid.Peacock.never_base}}%, and her wins went from {{fact:twin.grid.Peacock.win_base}}% to {{fact:twin.grid.Peacock.win_llm}}%, about {{fact:twin.grid.sigma.peacock}} [[w:Standard deviation|standard deviations]], still with no wrong accusation. Her [[w:Bluff (poker)|bluffing]] fell with the model, from {{fact:twin.grid.bluff.peacock.base}} own-card suggestions a game to {{fact:twin.grid.bluff.peacock.llm}}, as it did for every character that does not loop.[^twin][^wrapper]

## Memory

Peacock's method recomputes from the floor's open facts on each call and carries no learned state between games. A model playing her seat can separately keep a [[logbook]] when memory is enabled, recording, after seeing the completed deal, what happened, lessons, standing instructions and, since October 2026, the evening as an occasion: who was good company and a read of each opponent as a person as well as a player.[^logbooks] The one condensed digest theme that carried the earlier rule against talking was hers, and was edited by hand on 14 October 2026, since a digest is not rewritten by play; her standing instructions now call the talk 'half the evening and worth every line of it'.[^live]

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
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^arena]: {{cite:docs/strategy-glossary.md|Phase 14 dial recalibration (2026-10-18)}}
[^current]: {{cite:docs/strategy-glossary.md|Phase 14 dial recalibration (2026-10-18)}}
[^twin]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}
[^wrapper]: {{cite:docs/llm-wrapper.md|What happens on one decision}}
[^logbooks]: {{cite:docs/logbooks.md|Three tiers}}
[^rules]: {{cite:clude_llm/personas/rules.md|The company and the parts}}
[^lives]: {{cite:docs/phase13-plan.md|1. Brief and settled decisions}}
[^live]: {{cite:docs/phase13-plan.md|2026-10-15: step 4 accepted live, and a debrief lost to its token cap}}

{{navbox:clude}}
