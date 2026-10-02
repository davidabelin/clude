---
title: Table talk
short: Conversation alongside the formal decisions of a game
categories: Personality
redirects: Talk, Chat, Chattiness
---
**Table talk** is conversation at a [[clude]] table alongside movement, suggestions, card shows and accusations. Human players can type messages. Model-piloted characters may supply a line with a decision or react to an event or another player's remark. Their [[persona|personas]] shape the voice, while chattiness controls opportunities to speak.[^wrapper]

Conversation is not checked against the hidden cards. A player can hint, bluff, joke or make a mistake, and listeners decide what to believe. Formal disproof is different: the engine requires a matching card from the first player able to answer. Spoken claims do not become [[deduction floor|floor]] facts.

## At the table

After Mustard shows a card privately to Plum, White might comment on Plum's repeated questions. Everybody hears the line, but the line does not reveal the private card through the engine. If Plum says 'That settles the Rope', listeners may interpret the claim without treating it as a certified card location.

Speech can nevertheless affect a model's later choices because recent talk appears in its prompt. This makes it part of the model's information context, even though it is outside the logical evidence used by the numerical methods.

## On-turn speech

The reply schema for a model decision includes a `say` field as well as the choice letters. The wrapper can buffer a non-empty line, and the engine appends it as a `RemarkEvent` after the relevant formal event. A refuter can speak after showing a card on somebody else's turn.[^engine]

The line is subject to chattiness and the wrapper's speech setting. A valid model choice with no published line still takes effect. A failed choice falls back to the numerical character and does not justify pretending an accompanying invented reply was accepted.

## Off-turn reactions

The web reaction queue can request a remark after a typed line, a resolved suggestion or an accusation. The prompt contains the seat's own observation, recent conversation and the trigger. This separate request chooses speech only; it does not grant an extra movement, suggestion or accusation.[^chat]

A reaction may return an empty string. Backend failure leaves the character silent. These calls are audited and counted against the same game budget, so a highly conversational table can spend calls without increasing the number of game decisions.

## Chattiness

The profile default is {{code:neutral.chattiness}}. On-turn, this setting is the probability of publishing a line the model offered. Off-turn, the caller uses it to decide whether to request a reaction. A value of 1 does not guarantee a line on every occasion: the model may return nothing, the menu may need no call, or a request may fail.[^wrapper]

Expected remarks per game also depend on game length, successful calls and how many events trigger reactions. The setting is therefore not a fixed number of remarks or a direct token budget. Headless characters do not chat regardless of the dial.

## Stored talk and memory

Remarks appear in the game's event history and in replay. Recent lines can be shown in later decision prompts. A post-game [[The debrief|debrief]] can reflect on the transcript and save observations in the [[logbook]]. These are different time spans: the immediate conversation is current-game context; the logbook is persistent narrative memory.

The engine distinguishes speech from card shows in the record. A spectator's access to remarks does not entitle them to another player's private disproof. Similarly, a dossier that says an opponent likes to bluff is an interpretation from earlier games, not proof about that opponent's current hand.


## See also

[[Persona]] · [[Bluffing]] · [[LLM wrapper]] · [[Logbook]]

## References

{{references}}

[^wrapper]: {{cite:docs/llm-wrapper.md|What happens on one decision}}
[^engine]: {{cite:clude_core/engine.py|`SpeakingPlayer` and `_append_remarks`}}
[^chat]: {{cite:clude_web/chat.py|reaction queue}}

{{navbox:clude}}
