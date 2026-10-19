---
title: LLM wrapper
short: How a language model pilots a numerical character
categories: Personality
redirects: The LLM wrapper, Model-piloted character
---
The **LLM wrapper** lets a language model choose and speak for a numerical [[clude]] character. It builds scored options from that character's [[belief]] and [[personality dials]], applies the [[leash]], and asks the model to select allowed letters. The numerical method remains the source of its card estimates; the model supplies discretion and voice.[^wrapper]

Failures return to the underlying headless character. The wrapper therefore permits a game to continue through invalid replies or unavailable model service. Its audit records distinguish accepted model choices, skipped calls and fallbacks. A chat agent taking an independent seat is a different arrangement, described in [[Claude]].

## One decision

{{figure:decision-pathway|One of a character's decisions, end to end. With a model in the seat the menu is built from the character's own scores, and a failed call falls back to the headless pick.}}

Suppose the engine asks Plum where to move. His network scores every legal destination itself (for the other characters, the decision layer combines room probabilities with proximity). The wrapper ranks the legal destinations by those same scores, applies the leash and labels the allowed options. If two remain, the model receives their descriptions and scores, together with Plum's own view of the game.

A valid reply selects a letter and may supply a short line of [[table talk]], which is published as written: it arrives in the same reply as the decision, so the draw that used to discard it saved nothing and was removed on 15 October 2026, and a character that prefers silence answers with an empty string. Every line a model writes is cleaned as a person's is, to {{code:llm.max_line}} characters at most. The wrapper plays the corresponding action. If the letter is outside the menu, it instead calls Plum's headless movement decision. The model does not send a new route for the engine to improvise.

| Engine decision | Model choice |
|---|---|
| Movement | One allowed destination |
| Suggestion | One suspect letter and one weapon letter; room supplied by the engine |
| Accusation | The character's selected triple or a pass |
| Show a card | One of the matching cards supplied by the engine |

The [[leash]] article describes the special rules for held-card bluffs and accusation timing. The engine still enforces matching-card disclosures and legal movement.

## What the model sees

The user prompt is built from a `ClueObservation` for the deciding seat. It includes that seat's hand, public roster and positions, the floor's deductions, the method's card estimates and diagnostics, the best accusation score, suggestion history with unseen cards hidden, recent conversation and the allowed menu.[^prompt]

The system prompt supplies the [[persona]] and shared rules, including what the character has been told about itself ([[Persona#The parts]]). When remembering is enabled and a logbook exists, a second system block supplies the selected [[memory dial|memory depth]]. That block remains stable during the game.

A web table gives the wrapper one set of participant names for the whole evening, the token and a person's display name after it, and the on-turn prompt, the off-turn reply prompt and the debrief all use it. Before 15 October 2026 the on-turn prompt fell back to bare suspect tokens, so a character could call one person 'Mr. Green' on its turn and by their name off it. Without the call, in a headless arena or the CLI, the prompts use seat labels.[^names]

Different seats have different private evidence. The common [[deduction floor]] is a shared algorithm, not a shared omniscient notepad. A model prompt cannot acquire another player's privately shown card merely because the application stores it for replay. After the game, the [[The debrief|debrief]] deliberately receives a revealed deal and is a separate request.

## Fallback and audit

The wrapper accepts only a reply matching the decision's JSON schema and allowed menu. Backend errors, timeouts, refusals, malformed replies and exhausted budgets invoke the headless choice. When only one allowed choice remains, it skips the call and uses that same fallback path.[^wrapper]

Menu construction draws no random numbers. A backend that never supplies an accepted choice therefore preserves the headless character's decision stream; recorded tests compare complete game events under this control. Accepted choices can change later observations and decisions, so a partially working model is not expected to preserve the same game.

Each decision records its menu, selected letter, whether a call occurred, the reason for fallback, any departure from the top option, supplied speech, usage and latency. The [[arena]] aggregates these fields. A single-option decision is not an API call, and a call ending in fallback is not a successful model choice.

## Closing remarks

At an external table the wrapper can request one optional final comment after the result, subject to the shared 30-second window and the remaining model budget. This is a separate call, not a legal-move decision or a debrief. An empty or failed reply supplies no line; accepted lines are public and enter the saved record and the later debrief. [[The table]] describes the closing sequence.[^wrapper]

## Backends and reproduction

The backend interface supports the live provider, an always-failing null control, recorded exchanges and replayed exchanges. Replay keys depend on the request contents. A missing request raises a replay miss rather than silently supplying a plausible response.[^backends]

Recorded replies can reproduce a run without another paid model call. A seed alone cannot fix live model replies, which can vary even when the numerical menus are reproducible. [[Determinism and seeds]] separates these forms of reproduction.

## The canon

Since October 2026 a wrapped character also carries [[Wikiclude]] as its standing reference.[^canon] A third cached system block lists every article's title, and two tools, `wiki_search` and `wiki_read`, go on each decision, remark and [[The debrief|debrief]] request. The backend answers a tool call inside the same request, up to {{code:llm.max_lookups_per_call}} lookups a call and {{code:llm.max_lookups_per_game}} a game, and the model still answers in the decision's schema. A read hands over a short article whole, otherwise its lead and section list and then one section at a time, never more than {{code:canon.read_limit}} characters.

The shared rules distinguish two cases. On how this house plays -- the board, movement, how a suggestion is disproved, what a wrong accusation costs -- the encyclopaedia is the better source than a model's own recollection of Clue, and legality is settled by the engine's menu in any case. On everything else, including an article about the character itself, it may be doubted and disputed roughly as Wikipedia may be, and nothing in it outranks a card the character was shown or what it watched someone do at the table. Mentioning or quoting it is allowed; knowing a thing without parade remains the usual style. How readily a character consults it at all is a matter of its [[persona]]: Professor Plum and Mrs. Peacock look things up by reflex, Colonel Mustard not at all. The lookups are audited with each decision and counted by the [[arena]], so the propensity is measured rather than set by a [[personality dials|dial]]. The canon describes how every character thinks in general and knows nothing of the deal in play. A chat seat has the same encyclopaedia through [[A seat over MCP|two MCP tools]].

## Limits

The wrapper does not retrain the numerical method or turn a model's prose into verified card evidence. A confident explanation can accompany a poor allowed choice. Conversely, a useful strategy mentioned in conversation cannot be played if its option is outside the leash.

[[Twin comparison|Paired comparisons]] test the resulting behaviour, with outcomes depending on the board, roster, menus, model settings and memory state. They support conclusions about recorded runs rather than a general claim that adding a language model improves every character.


## See also

[[Leash]] · [[Persona]] · [[Table talk]] · [[Logbook]] · [[Twin comparison]]

## References

{{references}}

[^wrapper]: {{cite:clude_llm/player.py|`LLMCharacter`}}
[^prompt]: {{cite:docs/llm-wrapper.md|What the model is shown, and what it is not}}
[^backends]: {{cite:docs/llm-wrapper.md|Backends}}
[^names]: {{cite:docs/phase13-plan.md|2026-10-15: the rehearsal completed, and step 6's naming and pacing}}
[^canon]: {{cite:docs/llm-wrapper.md|The canon}}

{{navbox:clude}}
