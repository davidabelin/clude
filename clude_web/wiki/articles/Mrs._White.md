---
title: Mrs. White
short: The character who reads the players, not the cards
categories: Characters
redirects: White, Mrs White
kind: stub
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
[[Accusation threshold]] | {{code:preset.White.accuse_threshold}}
[[Bluff rate]] | {{code:preset.White.bluff_rate}}
[[Curiosity]] | {{code:preset.White.curiosity}}
[[Secrecy]] | {{code:preset.White.secrecy}}
[[Temperature]] | {{code:preset.White.temperature}}
= Record on the Classic board
Games won | {{fact:arena.grid.White.win}}% of {{fact:arena.grid.White.games}}
Wrong accusations | {{fact:arena.grid.White.wrong}}%
}}

**Mrs. White** is one of the six suspects of [[Clue]] and, in [[clude]], the [[Category:Characters|character]] who reads the players instead of the cards. Her method is a [[Markov chain]] fitted to each opponent's run of [[suggestion|suggestions]]: a player who keeps naming a card they have named before has, she reasons, not yet been shown it, and a card nobody can be shown may well be in [[the envelope]]. Her persona calls her "the housekeeper, dry, watchful, and unimpressed by everyone's airs, including her own".[^persona]

On the [[Classic board]] hers was the best belief of the six for most of a game, ahead of the [[uniform baseline]] at every checkpoint.[^glossary] She [[bluffing|bluffs]] more than any other character and did not accuse wrongly in the arena reported here.[^arena]

## References

{{references}}

[^persona]: {{cite:clude_llm/personas/White.md|the character's persona}}
[^glossary]: {{cite:docs/strategy-glossary.md|White -- Markov model over suggestion sequences}}
[^arena]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}

{{navbox:clude}}
