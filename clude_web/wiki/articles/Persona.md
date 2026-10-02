---
title: Persona
short: The prose describing a model-piloted character’s voice and self-image
categories: Personality
redirects: Personas
---
A **persona** describes a character to the language model playing its seat. It gives the character a temperament, a self-image based on its reasoning method, and a speaking style. [[clude]] has one persona for each of the six suspects, used together with shared house rules.[^wrapper]

The prose can influence choices within the [[leash]], but the numerical method and [[personality dials]] supply the scores and allowed options. Personas deliberately express a character's disposition without separately implementing every behavioural flaw as an instruction.

## Voice and self-image

Scarlett's persona describes her as 'quick, glamorous, and entirely sure of yourself'. Its speaking guidance calls for short, poised and cutting sentences. Her mathematical overconfidence remains a property of her heuristic updates and accusation setting, rather than a second command to ignore evidence.[^scarlett]

Plum's persona calls him 'precise to the point of pedantry' and asks him to describe what the count permits in words rather than recite decimals. These descriptions are fictional character instructions, not technical guarantees that he always enumerates exactly. His method can fall back to sampling.[^plum]

White's persona presents a dry, watchful housekeeper who reads people. That voice fits her behaviour-based method, but statements such as a repeated question indicating a card not held are interpretations, not rules of [[Clue]]. [[Markov chain]] explains the heuristic separately from the persona's self-image.[^white]

## Shared house rules

Every persona is followed by the same rules text. It explains the hand, floor deductions, numerical beliefs, allowed options and JSON reply format. Speech should be brief and in character, with an empty line permitted when there is nothing useful to add. It discourages repeating remarks already heard at the table.[^rules]

The shared rules also distinguish conversation from formal disproof. Characters may hint, tease or mislead in speech, but cannot refuse to show a matching card. The engine determines who must answer from the actual hands. A character's voice cannot override that requirement.

## How the text is used

`load_persona` reads the suspect's Markdown file, and the [[LLM wrapper]] combines it with the rules as a stable system prompt. The decision's user prompt supplies the changing seat observation and menu. Keeping the persona stable allows the provider to reuse a cached prefix; it does not freeze the model's choices.[^prompt]

When a [[logbook]] is attached, selected memory is supplied separately after this prefix. A remembered lesson can steer the model's interpretation, while the same persona supplies its voice. Neither text widens the menu.

## Personality and behaviour

The numerical characters still make distinct decisions in headless play, where the persona is never sent to a model. Their methods and dials account for that behaviour. The model-piloted versions can add further differences by choosing among allowed alternatives and by reacting to conversation.

Changing a persona can therefore change more than wording. It can alter when a model waits, which question it asks, or which allowed move it favours. [[Twin comparison]] and recorded decision audits are needed to assess those effects; a lively transcript alone does not demonstrate stronger play.


## See also

[[Category:Characters|The characters]] · [[Personality dials]] · [[LLM wrapper]] · [[Table talk]]

## References

{{references}}

[^wrapper]: {{cite:docs/llm-wrapper.md|Personas}}
[^scarlett]: {{cite:clude_llm/personas/Scarlett.md}}
[^plum]: {{cite:clude_llm/personas/Plum.md}}
[^white]: {{cite:clude_llm/personas/White.md}}
[^rules]: {{cite:clude_llm/personas/rules.md}}
[^prompt]: {{cite:clude_llm/prompt.py|`system_prompt`}}

{{navbox:clude}}
