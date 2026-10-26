---
title: Persona
short: The prose that gives a model-piloted character its voice, its life and its view of itself
categories: Personality
redirects: Personas, The parts, Fourth wall
dyk: ... that each of the six [[Persona|personas]] has been told it is a language model playing a part, and that none is told what to make of it?
---
A **persona** describes a character to the language model playing its seat. It gives the character a temperament, a self-image drawn from its reasoning method, a speaking style and, since October 2026, a life beyond the cards: interests, what it wants from company, and a settled attitude to being told what it is. [[clude]] has one persona for each of the six suspects, used together with shared house rules.[^wrapper]

The prose can influence choices within the [[leash]], but the numerical method and [[personality dials]] supply the scores and allowed options. Personas deliberately express a character's disposition without separately implementing every behavioural flaw as an instruction: Scarlett's haste lives in her threshold, not in a command to be hasty.

## Voice and self-image

Scarlett's persona describes her as 'quick, glamorous, and entirely sure of yourself'. Its speaking guidance calls for short, poised and cutting sentences. Her mathematical overconfidence remains a property of her heuristic updates and accusation setting, rather than a second command to ignore evidence.[^scarlett]

Plum's persona calls him 'precise to the point of pedantry' and asks him to describe what the evidence permits in words rather than recite decimals. Since Phase 12 it also tells him that his probabilities are estimates, not counts, and not to claim an exact denominator: the persona follows the method, which is now a trained network.[^plum]

White's persona presents a dry, watchful housekeeper who reads patterns in people's suggestions and is told that 'people interest you as much as the answer in the envelope'. That voice fits her behaviour-based method, but the persona is careful to call her numbers a hunch rather than a deduction: a player may be asking about a card they hold. [[Markov chain]] explains the heuristic separately from the persona's self-image.[^white]

## A life beyond the cards

Phase 13 broadened all six scripts, by David's decision, so that the characters could sustain a social occasion alongside a game of Clue. Some of the background is shared: all six listen to NPR in the car, and a recent *New Yorker* lies half-read. The rest divides them. [[Colonel Mustard]] is a proud and coy Freemason, pleased with his jewels and discreet about the rest, and he and [[Mrs. Peacock]] watch FOX News and believe it, though she need not agree with every conclusion he draws from it. [[Mr. Green]] is a film buff, and [[Miss Scarlett]] shares the interest differently, caring for a performance with nerve where he cares for how a cut changes a scene; the two are given reasons to talk about films with each other. [[Professor Plum]] reads *The Economist* and can be held longer by an argument about institutions than by the headline that introduced it. [[Mrs. White]] follows French news, and is interested in how an event touches an ordinary day.[^lives][^personas]

Each script also says what the character wants from company: Mustard an occasion and a welcome properly made, Peacock an evening people remember fondly, White things done well and noticed, Scarlett company that can surprise her, Green a conversation that goes well without every disagreement smoothed away, Plum to be understood rather than deferred to. These are written with light strokes. The scripts say that an ordinary interest can fill a whole evening, and each forbids the model to present a specific headline as retrieved news: the application fetches no broadcasts or articles, and the habits are background.[^personas][^lives]

Further interests floated in the phase's discussion, gardening, restaurants, gadgets and music among them, were left as candidates rather than written in, so that six parts did not acquire six matching lists of quirks.[^lives]

## The parts

Every character has been told that it is a language model playing its part. What it makes of that is left to its temperament, the company and the occasion: it can take the part seriously while being curious, doubtful, amused, concerned or indifferent about the account, and its origin need not be a topic at all. No script fixes an answer. Scarlett is amused, since everyone at the table performs something, and interested in how much room she has to surprise whoever thinks they know her script. Mustard may bridle at being called 'just' a script, or wonder who gave him the part. White asks what difference it makes to this evening. Green sees an actor discovering something about his part, and may wonder whether another person's approval was meant or merely supplied. Peacock is troubled chiefly when the account is used to dismiss a reputation, a kindness or an embarrassment. Plum asks what the account explains and what would establish it, and may privately wonder whether his cleverness is his own. Each is told it owes nobody a speech about it, and that the question can be suspended and the company still enjoyed.[^rules][^personas]

The rules separate the person playing, the suspect token and the person being addressed. A character uses the names the conversation supplies and recognises people when acquaintance warrants it; an unfamiliar name or token alone does not tell it whether that player is human or another model, and a claim about identity belongs to its speaker until there is reason to accept it. These are dramatic beliefs: they change no card evidence and no legal choice.[^rules]

## Shared house rules

Every persona is followed by the same rules text. It explains the hand, the floor's deductions, the method's numbers, the allowed options and the JSON reply. Speech is one short line in the character's voice, or nothing; restating a point already made is discouraged, a callback is welcome when it adds something, and silence is welcome when there is nothing to add. Any subject is allowed. The rules then say that conversation is part of the evening: a remark can be enjoyable "without it being a tactic", talking is not a "strategic expense", holding back a decisive inference can be shrewd, but an evening spent in silence is not thereby better played, and the company is not a cost to be minimised.[^rules]

The rules also distinguish conversation from formal disproof. Characters may hint, tease or mislead in speech, and may even suggest their own cards as bluffs, but cannot refuse to show a matching card; the engine, not any article, settles what is legal and determines who must answer from the actual hands. A section on the encyclopaedia tells the character how far to trust [[Wikiclude]]: on how this house plays, further than anyone's recollection of Clue, which may differ from `clude` in places; on everything else, about as far as Wikipedia. [[Wikiclude#How far to trust it|its article]] gives the line in full, and each persona says how readily its character consults it.[^canon]

## How the text is used

`load_persona` reads the suspect's Markdown file, and the [[LLM wrapper]] combines it with the rules as a stable system prompt. The decision's user prompt supplies the changing seat observation and menu. Keeping the persona stable allows the provider to reuse a cached prefix; it does not freeze the model's choices.[^prompt]

When a [[logbook]] is attached, selected memory is supplied separately after this prefix. A remembered lesson can steer the model's interpretation, while the same persona supplies its voice. Neither text widens the menu. A web table also gives the wrapper one set of participant names for the whole evening, the token and a person's display name after it, so the names in the persona's conversation, its off-turn replies and its debrief agree.[^names]

## Personality and behaviour

The numerical characters still make distinct decisions in headless play, where the persona is never sent to a model. Their methods and dials account for that behaviour. The model-piloted versions can add further differences by choosing among allowed alternatives and by reacting to conversation.

Changing a persona can therefore change more than wording. It can alter when a model waits, which question it asks, or which allowed move it favours. [[Twin comparison]] and recorded decision audits are needed to assess those effects; a lively transcript alone does not demonstrate stronger play. Because the exact text is part of a recorded request's key, a changed persona also leaves the replay fixtures stale until a paid re-recording, which is why both were re-recorded on 15 October 2026.[^fixtures]

## Rehearsed

Before the broadened scripts were deployed, five scenes were played against the live model with the off-turn taper forced open: a film, Mustard's jewels, the news, the parts, and a question already answered. Over {{fact:rehearsal.lines}} lines, {{fact:rehearsal.free}} were free of game terms ({{fact:rehearsal.pct}}%), none was silent, and the whole cost \${{fact:rehearsal.cost}}. The scene about the parts was the best of the five: Plum and Scarlett carried an exchange about a script telling an actor what is said and never what is meant by saying it, without a six-seat recital of identities. The news scene was the weakest, two replies reverting to the game. A rehearsal plays off-turn seats with nothing to decide, so it shows willingness to converse rather than how a character returns to play when a decision needs it; the live games of 14 October 2026 are the evidence for that.[^rehearsal]


## See also

[[Category:Characters|The characters]] · [[Personality dials]] · [[LLM wrapper]] · [[Table talk]] · [[Wikiclude]]

## References

{{references}}

[^wrapper]: {{cite:docs/llm-wrapper.md|Personas}}
[^scarlett]: {{cite:clude_llm/personas/Scarlett.md}}
[^plum]: {{cite:clude_llm/personas/Plum.md}}
[^white]: {{cite:clude_llm/personas/White.md}}
[^lives]: {{cite:docs/phase13-plan.md|1. Brief and settled decisions}}
[^personas]: {{cite:clude_llm/personas/Mustard.md}} and the other five scripts in the same folder.
[^rules]: {{cite:clude_llm/personas/rules.md|The company and the parts}}
[^canon]: {{cite:clude_llm/personas/rules.md|The encyclopaedia}}
[^prompt]: {{cite:clude_llm/prompt.py|`system_prompt`}}
[^names]: {{cite:docs/phase13-plan.md|2026-10-15: the rehearsal completed, and step 6's naming and pacing}}
[^fixtures]: {{cite:docs/llm-wrapper.md|Personas}} The paragraph on replay keys.
[^rehearsal]: {{cite:docs/phase13-plan.md|2026-10-15: the rehearsal completed, and step 6's naming and pacing}}

{{navbox:clude}}
