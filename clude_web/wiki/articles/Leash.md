---
title: Leash
short: How far a language model may stray from its character's own choice
categories: Personality
redirects: The leash
kind: stub
---
The **leash** limits the choices available to a model-piloted character. For movement, suggestions and showing a card, options are scored by the numerical character and allowed when their score is at least $(1 - \text{leash})$ times the best score. At 0, only the highest-scoring options remain, including ties; at 1, every option on the legal menu is allowed. The preset is 0.25. For [[accusation|accusations]], the leash instead opens a window around the character's threshold, allowing an earlier accusation or a decision to wait.[^wrapper]

If only one option remains, the model is not called. An invalid reply, backend error or budget limit falls back to the headless character's choice. The leash permits discretion while retaining constraints supplied by the method and [[personality dials]].

## References

{{references}}

[^wrapper]: {{cite:docs/llm-wrapper.md|What happens on one decision}}

{{navbox:clude}}
