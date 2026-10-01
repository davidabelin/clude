---
title: Colonel Mustard
short: The character who reasons from the games he has seen
categories: Characters
redirects: Mustard, Col. Mustard
kind: stub
---
{{infobox
title: Colonel Mustard
class: suspect-mustard
figure: token-mustard
caption: Mustard's token, the second in the order of play
Method | [[Decision tree]]
In a phrase | Pattern-matches; confidently wrong on unusual deals
Module | `decision_tree.py`
Memory | Every game he has seen played, as training rows for his tree
= Personality dials
[[Accusation threshold]] | {{code:preset.Mustard.accuse_threshold}}
[[Bluff rate]] | {{code:preset.Mustard.bluff_rate}}
[[Curiosity]] | {{code:preset.Mustard.curiosity}}
[[Secrecy]] | {{code:preset.Mustard.secrecy}}
[[Temperature]] | {{code:preset.Mustard.temperature}}
= Record on the Classic board
Games won | {{fact:arena.grid.Mustard.win}}% of {{fact:arena.grid.Mustard.games}}
Wrong accusations | {{fact:arena.grid.Mustard.wrong}}%
}}

**Colonel Mustard** is one of the six suspects of [[Clue]] and, in [[clude]], the [[Category:Characters|character]] who reasons from experience. His method is a [[decision tree]] grown from the records of past games: for each card still in doubt it asks a short series of questions (how many players could still hold it, how often it has been named, how far the game has run) and answers with how such cards turned out before. His persona calls him "hearty, bluff, decisive, a military man who has played a great many games of this and remembers most of them".[^persona]

The tree gives him one of the best beliefs of the six at the end of a game, and on the earlier [[ring board]] one of the worst in the middle, where a pattern that usually holds can be confidently wrong about an unusual deal.[^glossary] In the arena reported here he won {{fact:arena.grid.Mustard.win}}% of his games.[^arena] He is one of three characters whose method itself remembers from game to game.

## References

{{references}}

[^persona]: {{cite:clude_llm/personas/Mustard.md|the character's persona}}
[^glossary]: {{cite:docs/strategy-glossary.md|Mustard -- Decision tree on game logs}}
[^arena]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}

{{navbox:clude}}
