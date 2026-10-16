---
title: The debrief
short: A post-game reflection that can become a narrative logbook entry
categories: Memory
redirects: Post-game reflection
dyk: ... that [[The debrief|the debrief]] now tells a character not to write itself a rule against speaking, after four of them had?
---
**The debrief** is the post-game model request that writes a character's narrative [[logbook]] entry. It reveals the finished deal, compares the character's decisions and beliefs with the result, and asks for the evening as an occasion as well as a game: lessons, instructions and a read of each opponent as a player and as company, in the character's [[persona|voice]]. It occurs after play and cannot change the completed game's outcome.[^debrief]

A debrief requires a model-piloted seat with an attached logbook and the debrief setting enabled. Failure or malformed output writes no entry. Its observations may influence later allowed choices when the logbook is read back; they are not a retraining step for the numerical method.

## What is revealed

During play, the model receives only its seat's observation. At debrief, it is told the envelope and the entire face-up deal, alongside the seat's original private history. A claim about what an opponent held can now be checked against the actual hand.[^prompt]

The prompt also contains the outcome, the whole of the table talk with the character's own lines marked, the model's decision audit, final beliefs against truth, and earlier logbook material. Repeated decision runs are collapsed so a stall is visible as a pattern rather than a long sequence of identical descriptions. Each seat is called what the table called it all evening, the token and a person's display name after it; the prompt still names the roster labels the dossiers are keyed on, so a character is not left to guess a key from a display name.[^names]

Suppose Plum repeatedly asked a question that Mustard could answer with Hall. The debrief can distinguish whether the model chose those questions or whether a one-option menu never asked it. That distinction matters for a useful lesson: changing the model's intention cannot repair an option excluded by the leash.

## What is written

The reply supplies narrative fields: a title, a short summary, keyword flags, what happened, opponent evaluations, insights, lessons, a final-outcome account, revised standing instructions and dossiers. The structured schema and entry builder check the shape and normalise bounded fields.[^schema]

Since 14 October 2026 the instructions for those fields ask for the evening as well as the play. What happened is the evening as the character experienced it, 'the game, and whatever else made it worth sitting down for'; an evaluation says what an opponent was like to play with as well as how they played; a flag may name a pattern in the company; a dossier reads the person as well as the player. The standing instructions, rewritten in full every time, carry one sentence that settles an earlier failure: keeping a decisive inference to oneself can be shrewd, but a quiet evening is not thereby a better played one, and the character is not to write itself a rule against speaking or against the company. The schema did not change; the existing fields were asked for differently.[^prompt][^step4]

Code computes identity, date, game id, token, table, outcome and model metadata. These factual fields are not left to the model's memory. Opponent names are resolved to roster identities, and evaluations are retained only for players actually present.

A successful entry updates the rolling head. Dossiers for absent opponents remain as they were; revised instructions replace the previous list when a new list is supplied. The model's prose remains an interpretation and can still contain a mistaken causal explanation.

## Request and failure

The debrief has separate effort, response-room and timeout settings from an ordinary game decision. Current defaults give it {{code:llm.debrief_max_tokens}} output tokens of room and {{code:llm.debrief_timeout}} seconds, and the room covers the model's thinking and its reply together. The wrapper records its status and accounts for its usage with the completed game.[^settings]

The room was 4,096 tokens until 15 October 2026, when the broadened entries no longer fitted beside a long think. Plum's reply for one six-seat game was cut off in the middle of a string and lost, and the table recorded it as malformed JSON; the re-run that replaced it, from the retained record, needed {{fact:debrief.plum.out}} output tokens for the entry alone, at \${{fact:debrief.plum.cost}} without a warm cache. The cap was doubled, and a reply stopped at it is now reported as truncation rather than as bad JSON.[^cap]

An error, refusal, truncation or malformed response leaves the logbook unchanged for that entry and records a reason. The game record remains available even without a narrative entry. Consequently, a logbook tally is a count of successfully written entries rather than a complete independent participation ledger.

## What a lesson can do

A later [[memory dial|memory block]] can include the new summary or full entry and the head's instructions. It can steer the model among options the current leash allows. It cannot widen a menu, revise the hidden deal or certify an opponent's current cards.

The historical [[Logbook#Recorded experiment|Plum experiment]] found fewer stalls alongside accumulating narrative memory when the escape move was available. That evidence concerns one run on the earlier board and does not establish that reflection always improves winning. The later [[landing rule]] addressed the scoring mechanism directly.

What a debrief writes about the company can also do something: a character that remembers who was good to play with, and a line it would return to, has somewhere to start the next evening's conversation. The two games played on the day the broadened instructions were deployed produced entries that do, and no standing instruction against talking.[^live]

## Separation from method learning

[[Method memory]] is updated through numerical contributions from records or live arm feedback. A headless character can use that mechanism without a debrief. A model-written lesson about 'trusting Mustard less' does not directly alter Green's Beta parameters; those parameters change through the arm update rule.

Keeping these paths separate makes their effects interpretable: a narrative comparison changes the model's context, while a method-memory comparison changes the numerical estimator's state.


## See also

[[Logbook]] · [[Memory dial]] · [[Method memory]] · [[LLM wrapper]] · [[Table talk]]

## References

{{references}}

[^debrief]: {{cite:docs/logbooks.md|The debrief}}
[^prompt]: {{cite:clude_llm/logbook.py|`debrief_prompt` and opponent resolution}}
[^names]: {{cite:docs/phase13-plan.md|2026-10-15: the rehearsal completed, and step 6's naming and pacing}}
[^schema]: {{cite:clude_llm/schema.py|`LOGBOOK_SCHEMA`}}
[^step4]: {{cite:docs/phase13-plan.md|2026-10-14: steps 3 and 4 implemented, retirement staged}}
[^settings]: {{cite:clude_llm/player.py|`LLMSettings` and `debrief`}}
[^cap]: {{cite:docs/phase13-plan.md|2026-10-15: step 4 accepted live, and a debrief lost to its token cap}}
[^live]: {{cite:docs/phase13-plan.md|2026-10-15: step 4 accepted live, and a debrief lost to its token cap}}

{{navbox:clude}}
