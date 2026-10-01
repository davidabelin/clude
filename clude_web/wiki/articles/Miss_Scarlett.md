---
title: Miss Scarlett
short: The character who reasons by tally, and accuses first
categories: Characters
redirects: Scarlett, Miss Scarlet
kind: stub
---
{{infobox
title: Miss Scarlett
class: suspect-scarlett
figure: token-scarlett
caption: Scarlett's token, the first in the order of play
Method | [[Naive Bayes]]
In a phrase | Overconfident, accuses early
Module | `naive_bayes.py`
Memory | A [[logbook]] only; her method remembers nothing
= Personality dials
[[Accusation threshold]] | {{code:preset.Scarlett.accuse_threshold}}
[[Bluff rate]] | {{code:preset.Scarlett.bluff_rate}}
[[Curiosity]] | {{code:preset.Scarlett.curiosity}}
[[Secrecy]] | {{code:preset.Scarlett.secrecy}}
[[Temperature]] | {{code:preset.Scarlett.temperature}}
= Record on the Classic board
Games won | {{fact:arena.grid.Scarlett.win}}% of {{fact:arena.grid.Scarlett.games}}
Wrong accusations | {{fact:arena.grid.Scarlett.wrong}}%
}}

**Miss Scarlett** is one of the six suspects of [[Clue]] and, in [[clude]], the [[Category:Characters|character]] who reasons by tally. Her method is [[Naive Bayes]]: every [[suggestion]] nudges the cards it names up or down, and she adds up the nudges as though each had nothing to do with the others. It makes her the fastest thinker at the table and the most easily misled. Her persona describes her as "quick, glamorous, and entirely sure of yourself".[^persona]

She accuses on far less than anyone else, at a confidence of {{code:preset.Scarlett.accuse_threshold}} where the other five wait for 0.7 to 0.9, and she makes more wrong accusations than any other character.[^arena] The project's notes are careful about where that comes from: her dial makes her early, and her method makes her wrong.[^glossary]

The method, with a worked example and what was measured, is described in full at [[Naive Bayes]].

## References

{{references}}

[^persona]: {{cite:clude_llm/personas/Scarlett.md|the character's persona}}
[^glossary]: {{cite:docs/strategy-glossary.md|Scarlett -- Naive Bayes}}
[^arena]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}

{{navbox:clude}}
