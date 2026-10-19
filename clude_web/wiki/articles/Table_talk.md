---
title: Table talk
short: Conversation alongside the formal decisions of a game
categories: Personality
redirects: Talk, Chat, Chattiness, Reaction queue
dyk: ... that until 15 October 2026 a coin flip threw away {{fact:talk.gate.dropped}} of the {{fact:talk.gate.written}} lines of [[Table talk|table talk]] two games had paid for, and that the flip is gone?
---
**Table talk** is conversation at a [[clude]] table alongside movement, suggestions, card shows and accusations. Human players type. A model-piloted character writes a line with its decision, or answers an event or another player's remark off its turn. Its [[persona]] supplies the voice and the interests, the web table's reaction queue decides when an off-turn line may be asked for, and the shared rules tell it that the conversation is part of the evening rather than a cost of playing.[^rules][^wrapper]

Conversation is not checked against the hidden cards. A player can hint, bluff, joke or make a mistake, and listeners decide what to believe. Formal disproof is different: the engine requires a matching card from the first player able to answer, and a spoken refusal cannot stand in for it. Spoken claims do not become [[deduction floor|floor]] facts.

Since October 2026 the characters are written as people who also play Clue, and told to listen and reply rather than announce. The settled view, carried in their [[Persona|scripts]] and now in their [[logbook|logbooks]], is that holding back a decisive inference can be shrewd, but an evening spent in silence is not thereby better played.[^phase13]

## At the table

After Mustard shows a card privately to Plum, White might comment on Plum's repeated questions. Everybody hears the line, but the line does not reveal the private card through the engine. If Plum says 'That settles the Rope', listeners may interpret the claim without treating it as a certified card location.

Speech can nevertheless affect a model's later choices, because recent talk appears in its prompt. This makes it part of the model's information context, even though it is outside the logical evidence used by the numerical methods. It can also be about anything: in the live logbooks the characters record an exchange about ledgers and currencies, a wager of a dinner on which card a player held, and a conversation the game ended underneath.[^live]

## What the characters are told

The shared rules allow any subject, including past games in a logbook, films, politics, religion, news and weather, with the reservation that a reading habit is background and supplies no current headline. A line is one short remark in the character's voice, to the other players, without stage directions, narration or recited numbers. Restating a point already made is discouraged; a callback is welcome when it adds something or its meaning has changed; and silence is 'a welcome part of the company' when there is nothing to add.[^rules]

The rules ask for listening. An answer, a disagreement, a concession, a question or a quiet joke can develop what someone else said, and a character need not supply a parallel monologue or end every line with a question. A decision is made from the supplied evidence and the allowed menu; the conversation may pause for it and return. Each decision prompt repeats the point in one sentence and shows the last {{code:llm.recent_remarks}} remarks.[^prompt]

A character may hint, bluff, tease or side-bet about its own hand, and must keep cards shown to it privately out of its talk. It may also mention, quote or argue with [[Wikiclude]], where the earlier rules had it know the encyclopaedia without ever citing it; [[Wikiclude#How far to trust it|the article on the encyclopaedia]] gives the line the rules draw.[^rules]

## On-turn speech

The reply to a decision carries a `say` field beside the choice letters. A non-empty line is published as written, after the formal event it accompanied, as a `RemarkEvent`; a refuter can speak after showing a card on somebody else's turn.[^engine] A character that would rather say nothing answers with an empty string, which the prompt offers it.

Until 15 October 2026 the wrapper drew against `chattiness` before publishing an on-turn line, and discarded the line on a miss. The line arrives in the same reply as the decision, so the draw saved nothing and cost the exchange: across the two games of 14 October it discarded {{fact:talk.gate.dropped}} of the {{fact:talk.gate.written}} lines the seats had written and paid for, speaking {{fact:talk.gate.spoken}}. The gate was removed by David's decision, so about twice the on-turn talk is expected at the same cost.[^gate]

A valid choice with an empty line still takes effect. A failed choice falls back to the numerical character and publishes no line, since the reply that carried one was not accepted.

## Off-turn reactions

The web table's reaction queue opens the floor after a typed line, an on-turn remark, a resolved suggestion or an accusation. Every model seat but the one that acted draws whether to join, at its chattiness raised to the power of one more than the reply's depth: a first reply at chattiness, a reply to that reply at chattiness squared, and so on. The seats are considered in seat order, at most {{code:chat.max_queued}} reactions are queued at a time, and a queued reaction waits {{code:chat.delay}} seconds, drawn uniformly, before it is due.[^chat]

A served line is said at the table as a `reaction` and opens the floor again one level deeper. The caps are {{code:chat.per_turn}} off-turn lines in a turn and {{code:chat.per_game}} in a game, and a reaction the game has moved past is dropped unserved. A seat whose backend refused its last call, the table's model budget being spent, is not asked. The request is for speech only: it cannot move a token, make a suggestion or show a card, and an empty reply or a failed call leaves the seat silent.[^chat][^wrapper]

The prompt for a reaction shows the seat's own observation, the recent talk and what just happened, and asks the character to answer the person rather than echo the topic, to let an answered point rest, and never to reveal a card it was shown.[^prompt] Reactions are audited and counted against the same per-game call and token budget as decisions.

## Chattiness

The profile default is {{code:neutral.chattiness}}, and none of the six presets changes it. Since 15 October 2026 the dial governs the off-turn draws alone; it no longer touches a line written with a decision. At the default a seat joins a fresh opportunity half the time, replies to a reply a quarter of the time and goes a third level deep about one time in eight.[^wrapper]

Phase 14 tested five values over the same 183 off-turn opportunities in eight paired four-seat games per value:

{{table:paid.phase14.chattiness|Current paid chattiness screen. Calls and spoken lines are off-turn reactions; the on-turn line attached to a decision is outside this gate.}}

The footprint is clear and begins to saturate above 0.5. The current setting produced 210 lines, against 275 at 0.75 and 288 at 1, while preserving silence on a missed draw. It remains the useful elbow rather than a claimed universal optimum.[^current]

Expected remarks per game depend on game length, successful calls and how many events open the floor. The setting is not a fixed number of remarks or a token budget. Headless characters do not chat whatever the dial says.

## Cleaning

Every line a model writes is cleaned as a person's typed line is: control characters out, white space collapsed, and anything past {{code:llm.max_line}} characters trimmed on a word boundary. A person's bad line is refused; a model's is mended, since a stray newline must not reach the record, a replay fixture or the next debrief prompt, where one remark is one line.[^clean]

## Stored talk and memory

Remarks appear in the game's event history and in replay, and recent lines are shown in later decision prompts. The [[The debrief|debrief]] shows the whole transcript with the character's own lines marked, and asks for the evening as an occasion as well as a game: what was said, who was good company and what the character would return to. Under the earlier debrief, four of the five characters with logbooks had written themselves a rule against talking; under the present one no live head carries such a rule, and five of the six lists close on a licence to converse.[^live]

The engine distinguishes speech from card shows in the record. A spectator's access to remarks does not entitle them to another player's private disproof, and a dossier that says an opponent likes to bluff is an interpretation from earlier games, not proof about that opponent's current hand.


## See also

[[Persona]] · [[Bluffing]] · [[LLM wrapper]] · [[Logbook]] · [[Wikiclude]]

## References

{{references}}

[^rules]: {{cite:clude_llm/personas/rules.md|The company and the parts}}
[^wrapper]: {{cite:docs/llm-wrapper.md|What happens on one decision}}
[^phase13]: {{cite:docs/phase13-plan.md|1. Brief and settled decisions}}
[^live]: {{cite:docs/phase13-plan.md|2026-10-15: step 4 accepted live, and a debrief lost to its token cap}}
[^prompt]: {{cite:clude_llm/prompt.py|`user_prompt` and `remark_prompt`}}
[^engine]: {{cite:clude_core/engine.py|`SpeakingPlayer` and `_append_remarks`}}
[^gate]: {{cite:docs/phase13-plan.md|2026-10-15: the rehearsal completed, and step 6's naming and pacing}}
[^chat]: {{cite:clude_web/chat.py|`Reactions.opportunity`, `due` and `serve`}}
[^current]: {{cite:docs/strategy-glossary.md|Phase 14 dial recalibration (2026-10-18)}}
[^clean]: {{cite:clude_llm/player.py|`clean_remark`}}

{{navbox:clude}}
