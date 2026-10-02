---
title: The debrief
short: A post-game reflection that can become a narrative logbook entry
categories: Memory
redirects: Post-game reflection
---
**The debrief** is the post-game model request that writes a character's narrative [[logbook]] entry. It reveals the finished deal, compares the character's decisions and beliefs with the result, and asks for lessons, instructions and opponent evaluations in the character's [[persona|voice]]. It occurs after play and cannot change the completed game's outcome.[^debrief]

A debrief requires a model-piloted seat with an attached logbook and the debrief setting enabled. Failure or malformed output writes no entry. Its observations may influence later allowed choices when the logbook is read back; they are not a retraining step for the numerical method.

## What is revealed

During play, the model receives only its seat's observation. At debrief, it is told the envelope and the entire face-up deal, alongside the seat's original private history. A claim about what an opponent held can now be checked against the actual hand.[^prompt]

The prompt also contains the outcome, table talk, the model's decision audit, final beliefs against truth, and earlier logbook material. Repeated decision runs are collapsed so a stall is visible as a pattern rather than a long sequence of identical descriptions.

Suppose Plum repeatedly asked a question that Mustard could answer with Hall. The debrief can distinguish whether the model chose those questions or whether a one-option menu never asked it. That distinction matters for a useful lesson: changing the model's intention cannot repair an option excluded by the leash.

## What is written

The reply supplies narrative fields: a title, short summary, keyword flags, what happened, opponent evaluations, insights, lessons, a final-outcome account, revised standing instructions and dossiers. The structured schema and entry builder check the shape and normalise bounded fields.[^schema]

Code computes identity, date, game id, token, table, outcome and model metadata. These factual fields are not left to the model's memory. Opponent names are resolved to roster identities, and evaluations are retained only for players actually present.

A successful entry updates the rolling head. Dossiers for absent opponents remain as they were; revised instructions replace the previous list when a new list is supplied. The model's prose remains an interpretation and can still contain a mistaken causal explanation.

## Request and failure

The debrief has separate effort, response-room and timeout settings from an ordinary game decision. Current defaults give it {{code:llm.debrief_max_tokens}} output tokens of room and {{code:llm.debrief_timeout}} seconds. The wrapper records its status and accounts for its usage with the completed game.[^settings]

An error, refusal or malformed response leaves the logbook unchanged for that entry and records a reason. The game record remains available even without a narrative entry. Consequently, a logbook tally is a count of successfully written entries rather than a complete independent participation ledger.

## What a lesson can do

A later [[memory dial|memory block]] can include the new summary or full entry and the head's instructions. It can steer the model among options the current leash allows. It cannot widen a menu, revise the hidden deal or certify an opponent's current cards.

The historical [[Logbook#Recorded experiment|Plum experiment]] found fewer stalls alongside accumulating narrative memory when the escape move was available. That evidence concerns a particular ring-board run and does not establish that reflection always improves winning. The later [[landing rule]] addressed the scoring mechanism directly.

## Separation from method learning

[[Method memory]] is updated through numerical contributions from records or live arm feedback. A headless character can use that mechanism without a debrief. A model-written lesson about 'trusting Mustard less' does not directly alter Green's Beta parameters; those parameters change through the arm update rule.

Keeping these paths separate makes their effects interpretable: a narrative comparison changes the model's context, while a method-memory comparison changes the numerical estimator's state.


## See also

[[Logbook]] · [[Memory dial]] · [[Method memory]] · [[LLM wrapper]]

## References

{{references}}

[^debrief]: {{cite:docs/logbooks.md|The debrief}}
[^prompt]: {{cite:clude_llm/logbook.py|`debrief_prompt` and opponent resolution}}
[^schema]: {{cite:clude_llm/schema.py|`LOGBOOK_SCHEMA`}}
[^settings]: {{cite:clude_llm/player.py|`LLMSettings` and `debrief`}}

{{navbox:clude}}
