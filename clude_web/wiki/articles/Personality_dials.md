---
title: Personality dials
short: The settings that turn numerical beliefs into playing choices
categories: Personality
redirects: Dials, Personality, Presets, Accusation threshold, Accuse threshold, Bluff rate, Curiosity, Secrecy, Temperature
dyk: ... that [[secrecy]] cannot change which card is shown when only one matches a suggestion?
---
The **personality dials** are numerical settings that govern how a character uses its [[belief]] to play. Five control headless decisions: accusation timing, held-card suggestions, movement priorities, disclosure preferences and randomness. Three further settings control a model-piloted seat's discretion, conversation and narrative-memory depth.[^profile]

The dials do not change the six [[Category:Methods|belief methods]]. Two characters with identical card estimates can make different decisions because their settings differ. A [[persona]] supplies a model's voice and can influence choices within the allowed [[leash]]; a dial supplies an explicit numerical rule.

## At the table

Suppose two characters both give their best accusation a score of 0.6. A character with threshold 0.5 accuses; one with threshold 0.9 waits. If both can show Rope or Hall, the secrecy setting may favour a card already shown rather than a fresh disclosure. These decisions can change the later game without changing how either method interpreted the current cards.

The controls act at different stages. [[Curiosity]] changes movement scores, [[temperature]] changes how scores are sampled, and [[leash]] limits what a model may select from a scored menu. A more random headless choice and a wider model menu are different mechanisms.

## The five decision dials

{{figure:decision-pathway|Where the dials act: between the method's belief and the action, for every decision a character makes.}}

| Dial | Decision | Main effect |
|---|---|---|
| Accusation threshold | Accuse | Minimum confidence score for a headless accusation |
| Bluff rate | Suggest | Probability of selecting a held suspect or weapon |
| Curiosity | Move | Blend of room probability and proximity |
| Secrecy | Show a card | Preference for repeating previous disclosures |
| Temperature | Move, suggest, show | Randomness when sampling the scored options |

All except temperature lie between 0 and 1. Temperature is non-negative and has no fixed upper bound. An accusation is a threshold test, not a temperature sample.[^profile]

### Accusation threshold

The headless character accuses once its confidence score reaches the threshold. A lower setting permits earlier commitment; a higher one requires stronger evidence but may let an opponent finish first. The score usually multiplies the largest suspect, weapon and room probabilities. That product approximates a joint probability and can be miscalibrated even when individual card estimates are accurate.[^character]

[[Mrs. Peacock]] supplies Dempster–Shafer belief bounds instead of her displayed decision probabilities. Her threshold therefore operates on a different kind of number. Equal thresholds across characters are not equal guarantees of a correct accusation. [[Floor player|The floor player]] has no threshold dial and waits for a proven envelope.

### Bluff rate

For each suspect and weapon slot, the headless character selects a held card with the dial's probability when it has one available. Otherwise it samples from cards outside its hand. A rate of 0 excludes held cards from those two slots; 1 selects held cards whenever available. The room is fixed and may be held at any setting.

[[Bluffing]] can isolate an unknown card or obscure the purpose of a question. The rate is a coin-flip parameter, not a target proportion of complete suggestions: hand composition and the compulsory room affect the observed proportion. Model-piloted suggestions expose bluff options when the rate and leash are positive, rather than enforce this headless frequency.

### Curiosity

Let $c$ be curiosity, $I$ the movement option's information score and $Q$ its proximity score. The shared movement score is

$$ S=cI+(1-c)Q. $$

$I$ uses the method's probability for a target room, discounted by {{code:movement.discount}} for each remaining step when the option ends in a corridor. $Q$ favours nearby rooms, with the [[landing rule]] reducing the value of a room an opponent can routinely disprove with its room card.[^features]

For two constructed options, entering a room might give $I=0.2,Q=1$, while moving towards another gives $I=0.6,Q=0.25$. At $c=0.25$, their scores are 0.8 and 0.3375, so entry ranks higher. At $c=0.9$, their scores are 0.28 and 0.565, so the corridor option ranks higher. These feature values illustrate the blend; they are not a claimed route from a seeded board position.

The name 'information' is the implementation's label for a room-probability proxy. It is not calculated expected [[entropy and bits|information gain]]. The distance estimate includes passages and ignores token obstructions; the engine separately ensures the offered move itself is legal.

### Secrecy

Matching cards receive scores of $s$, $s/2$ or 0, where $s$ is secrecy: the first for a card already shown to this suggester, the second for one shown to somebody else, and the third for a fresh card. With positive temperature, raising secrecy makes previous disclosures more strongly preferred. At zero secrecy all scores tie.[^character]

Only refutations with several matching cards offer discretion. Showing the only matching card is mandatory whatever the dial. At zero temperature, any positive secrecy produces the same ranking, so increasing it further need not change a choice. The setting is a preference, not permission to withhold a required card.

### Temperature

{{main:Softmax and temperature}}

Positive temperature samples options through a softmax: higher scores remain more likely, but lower ones can be chosen. Near zero, the implementation chooses among the top scores, breaking ties uniformly. Higher temperature flattens the probabilities towards a uniform choice. It does not make illegal actions available.

Because the scores use a common scale, a temperature can be applied to movement, suspect and weapon selection, and card showing. Its practical effect still depends on the score gaps in that particular menu.

## Presets

| Character | Accusation threshold | Bluff rate | Curiosity | Secrecy | Temperature |
|---|---|---|---|---|---|
| [[Miss Scarlett]] | {{code:preset.Scarlett.accuse_threshold}} | {{code:preset.Scarlett.bluff_rate}} | {{code:preset.Scarlett.curiosity}} | {{code:preset.Scarlett.secrecy}} | {{code:preset.Scarlett.temperature}} |
| [[Colonel Mustard]] | {{code:preset.Mustard.accuse_threshold}} | {{code:preset.Mustard.bluff_rate}} | {{code:preset.Mustard.curiosity}} | {{code:preset.Mustard.secrecy}} | {{code:preset.Mustard.temperature}} |
| [[Mrs. White]] | {{code:preset.White.accuse_threshold}} | {{code:preset.White.bluff_rate}} | {{code:preset.White.curiosity}} | {{code:preset.White.secrecy}} | {{code:preset.White.temperature}} |
| [[Mr. Green]] | {{code:preset.Green.accuse_threshold}} | {{code:preset.Green.bluff_rate}} | {{code:preset.Green.curiosity}} | {{code:preset.Green.secrecy}} | {{code:preset.Green.temperature}} |
| [[Mrs. Peacock]] | {{code:preset.Peacock.accuse_threshold}} | {{code:preset.Peacock.bluff_rate}} | {{code:preset.Peacock.curiosity}} | {{code:preset.Peacock.secrecy}} | {{code:preset.Peacock.temperature}} |
| [[Professor Plum]] | {{code:preset.Plum.accuse_threshold}} | {{code:preset.Plum.bluff_rate}} | {{code:preset.Plum.curiosity}} | {{code:preset.Plum.secrecy}} | {{code:preset.Plum.temperature}} |

These values are read from the current implementation. The neutral profile used as a comparison point is a separate set of defaults, not the average of the six presets. Mustard and White retain its accusation threshold deliberately: their method's mistakes should not also be programmed through an unusually reckless threshold.[^profile]

[[Dial sweeps]] informed the presets on the ring board and later on the Classic board. The chosen values express playing styles supported by those experiments; they are not universally optimal settings. Changed opponents can change a character's results even when its own settings stay fixed.[^tuning]

## Model and memory dials

| Setting | Role | Profile default |
|---|---|---|
| [[Leash]] | Which scored choices the model may make | {{code:neutral.leash}} |
| [[Chattiness]] | How often model remarks are requested or published | {{code:neutral.chattiness}} |
| [[Memory dial]] | How much narrative logbook is read before a game | {{code:neutral.memory}} |

The headless character ignores these three settings. A memory value of 0 means the condensed logbook head, not memory disabled. New web LLM seats start at full narrative depth; remembering is a separate table setting. [[Method memory]] can also apply to headless seats when remembering is enabled.

## Limits

The dials operate on a character's own estimates and shared scoring rules. They cannot repair every mistaken inference or make an unavailable route legal. Their effects also interact: secrecy changes score gaps, while temperature changes sensitivity to those gaps. A one-dial sweep measures an effect under the other settings held in that run, not under every possible combination.


## See also

[[Persona]] · [[Leash]] · [[Bluffing]] · [[Dial sweeps]] · [[Memory dial]]

## References

{{references}}

[^profile]: {{cite:clude_agents/personality.py|`Profile`, `NEUTRAL` and `PRESETS`}}
[^character]: {{cite:clude_agents/character.py|`best_triple`, `show_scores` and decision sampling}}
[^features]: {{cite:clude_agents/features.py|`room_features`, `score_choices` and `sample_softmax`}}
[^tuning]: {{cite:docs/strategy-glossary.md|Tuned presets on the grid (Stage 1e, 2026-09-15)}}

{{navbox:clude}}
