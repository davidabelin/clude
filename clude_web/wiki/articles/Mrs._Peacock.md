---
title: Mrs. Peacock
short: The character who will not guess
categories: Characters
redirects: Peacock, Mrs Peacock
kind: stub
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
[[Accusation threshold]] | {{code:preset.Peacock.accuse_threshold}}
[[Bluff rate]] | {{code:preset.Peacock.bluff_rate}}
[[Curiosity]] | {{code:preset.Peacock.curiosity}}
[[Secrecy]] | {{code:preset.Peacock.secrecy}}
[[Temperature]] | {{code:preset.Peacock.temperature}}
= Record on the Classic board
Games won | {{fact:arena.grid.Peacock.win}}% of {{fact:arena.grid.Peacock.games}}
Wrong accusations | {{fact:arena.grid.Peacock.wrong}}%
}}

**Mrs. Peacock** is one of the six suspects of [[Clue]] and, in [[clude]], the [[Category:Characters|character]] who declines to guess. Her method is [[Dempster-Shafer theory]], which keeps two numbers for every card where the others keep one: a *belief*, how far the evidence positively supports it, and a *plausibility*, how far the evidence fails to rule it out. The gap between the two is what she does not know, and she leaves it open. Her persona calls her "grand, formal, socially exact, and easily scandalised".[^persona]

She accuses on the lower number, the belief, which rises slowly; so she accuses late and, in the arena reported here, never wrongly.[^arena] Turned into ordinary probabilities her numbers are slightly worse than the [[uniform baseline]], which the project's notes trace to one modelling choice in how she shares out a clue between categories.[^glossary]

## References

{{references}}

[^persona]: {{cite:clude_llm/personas/Peacock.md|the character's persona}}
[^glossary]: {{cite:docs/strategy-glossary.md|Peacock -- Dempster-Shafer belief/plausibility}}
[^arena]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}

{{navbox:clude}}
