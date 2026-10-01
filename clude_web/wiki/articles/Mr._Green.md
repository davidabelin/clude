---
title: Mr. Green
short: The character who trusts whichever method has been doing best
categories: Characters
redirects: Green, Reverend Green, Rev. Green
kind: stub
---
{{infobox
title: Mr. Green
class: suspect-green
figure: token-green
caption: Green's token, the fourth in the order of play
Method | [[Bandit ensemble]]
In a phrase | Opportunistic; only as good as the method he is trusting
Module | `bandit.py`
Memory | How well each of the other five methods has done
= Personality dials
[[Accusation threshold]] | {{code:preset.Green.accuse_threshold}}
[[Bluff rate]] | {{code:preset.Green.bluff_rate}}
[[Curiosity]] | {{code:preset.Green.curiosity}}
[[Secrecy]] | {{code:preset.Green.secrecy}}
[[Temperature]] | {{code:preset.Green.temperature}}
= Record on the Classic board
Games won | {{fact:arena.grid.Green.win}}% of {{fact:arena.grid.Green.games}}
Wrong accusations | {{fact:arena.grid.Green.wrong}}%
}}

**Mr. Green** is one of the six suspects of [[Clue]] and, in [[clude]], the [[Category:Characters|character]] with no method of his own. He consults the other five, and on each turn adopts the belief of whichever he currently trusts most. Which to trust is a [[w:Multi-armed bandit|multi-armed bandit]] problem, and he solves it by [[w:Thompson sampling|Thompson sampling]]: each method is an "arm" with a running record, and after every game the arms are ranked by how close they came to the truth. His method is called the [[bandit ensemble]]. His persona calls him "affable, a little nervous, eager to be agreed with, and more calculating than you let on".[^persona]

Over many games he comes to trust the methods the [[belief benchmark]] also ranks highest. He is as slow as [[Professor Plum]], whose count he has to wait for, plus everybody else.[^glossary] In the arena reported here he won {{fact:arena.grid.Green.win}}% of his games.[^arena]

## References

{{references}}

[^persona]: {{cite:clude_llm/personas/Green.md|the character's persona}}
[^glossary]: {{cite:docs/strategy-glossary.md|Green -- Bandit ensemble over the other five}}
[^arena]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}

{{navbox:clude}}
