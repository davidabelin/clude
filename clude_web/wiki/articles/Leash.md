---
title: Leash
short: How far a language model may stray from its character's own choice
categories: Personality
redirects: The leash
kind: stub
---
The **leash** is the limit on a language model playing a character's seat. For each decision the character's own [[Category:Methods|method]] scores every option; the model is then offered only those options that score within the leash of the best, and chooses among them. At a leash of 0 it may pick only what the character would have picked; at 1 it may pick anything legal. The preset is 0.25 for every character.[^wrapper]

If only one option is within the leash the model is not asked at all, and if its answer is anything but one of the options offered, the character's own choice is played instead. The leash is why a model can give a character a voice without changing who the character is.

## References

{{references}}

[^wrapper]: {{cite:docs/llm-wrapper.md|What happens on one decision}}

{{navbox:clude}}
