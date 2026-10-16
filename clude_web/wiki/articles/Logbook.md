---
title: Logbook
short: Persistent narrative entries, lessons and opponent dossiers
categories: Memory
redirects: Logbooks, The logbook, Memory, Debrief
dyk: ...that memory depth 0 still reads the condensed [[logbook]]?
dyk: ... that a live audit of every [[logbook]] entry on 14 October 2026 found no film, broadcast or personal detail in any of them, and that the next two games' entries record a wager of a dinner on a card?
---
A **logbook** stores a character's narrative memory between games. With remembering enabled, a model-piloted seat receives the revealed deal after play and writes an entry in its [[persona|voice]]: the game, and since October 2026 the evening as an occasion, who was good company and what the character would return to. A condensed head maintains the outcome tally, standing instructions and opponent dossiers, each dossier a read of the person as well as the player. Before a later game, the [[memory dial]] controls how much is read back.[^logbooks]

The logbook is distinct from the immutable game record and from numerical [[method memory]]. Headless seats do not write narrative entries. [[Colonel Mustard]], [[Mrs. White]] and [[Mr. Green]] can retain method memory in either headless or model-piloted play; Scarlett, Plum and Peacock have no persistent numerical method state.

## From a game to a later decision

After a game in which Plum wasted questions in a cleared room, a [[The debrief|debrief]] might save a lesson about moving on sooner. At the next table, Plum's memory block can include that standing instruction. The model may then use it when choosing among allowed moves.

This is a possible memory path, not a claim about a particular stored entry. The instruction cannot add a move excluded by the [[leash]], and it cannot tell Plum where the next game's room card was dealt. Memory concerns past play rather than privileged knowledge of a new deal. It also concerns past company: the same block carries Plum's read of each opponent at the table, as a person as well as a player, and a line that someone said and he would return to.

## Three kinds of stored information

| Tier | Stored information | Use |
|---|---|---|
| Game record | Actual deal, events, settings and outcome | Replay, measurement and learning inputs |
| [[Method memory]] | Numeric training rows, opponent counts or arm parameters | Method-specific reasoning in later games |
| Narrative memory | Entries, instructions and dossiers | Context for later model choices and speech |

These tiers have different access rules. The finished record is face-up data for analysis; a live seat still sees only its private observation. A narrative entry is written by the model and may contain an interpretation or error rather than a verified inference.[^tiers]

## Entries and the head

Code supplies an entry's identity, serial number, date, game id, token, table, outcome and model. The model supplies a title, a summary of at most {{code:logbook.summary_words}} words, two to {{code:logbook.flags}} flags for the patterns that connect the game to others in the play or in the company, what happened, an evaluation of each opponent as a player and as company, insights, lessons, the result in its own words, the whole list of its standing instructions rewritten, at most {{code:logbook.instructions}}, and revised dossiers of at most {{code:logbook.read_words}} words each. Flags and lists are normalised and capped, and opponent fields are restricted to identities present at that table.[^entries]

The head combines a computed tally with the latest standing instructions and revised dossiers. Its tally counts games **with narrative entries**, not necessarily every game the character ever played. A failed debrief writes no entry, so the tally can omit an otherwise completed game.

A logbook belongs to the roster identity rather than the coloured token. A character can keep its logbook when playing a different token, and opponent dossiers can follow a human account across token changes.

## The evening as well as the game

Until 14 October 2026 the debrief asked for patterns of play, how opponents played and what gave them away, and offered nowhere to record an evening. A live audit of all {{fact:audit.entries}} entries then in the store found no film, broadcast, publication, interest or personal detail in any of them, conversational opponents recorded as weak, and {{fact:audit.clauses}} clauses in four characters' standing instructions that generalised from keeping a decisive inference quiet to not talking at all. The characters had drawn a reasonable conclusion from the fields they were given, and because every debrief rewrites the standing instructions in full, an edit to that list by hand was undone by the next game.[^audit]

The field instructions were revised rather than the schema. The narrative now asks for the evening as the character experienced it and whatever else made it worth sitting down for; the evaluations for what an opponent was like to play with as well as how they played; the flags for patterns in the company as well as in the play; the dossiers for the person as well as the player. The standing instructions carry the sentence that settles the audit's finding: keeping a decisive inference to oneself can be shrewd, but a quiet evening is not thereby a better played one, and the character is told not to write itself a rule against speaking or against the company. Condensing's overview and themes admit what the company has come to be like.[^prompt][^step4]

Two games on the evening the change was deployed rewrote every head under the new instructions. None reissued a rule against talking, and five of the six characters' lists now close on a licence to converse; the one digest theme that carried the old conclusion was edited by hand, since a digest is not rewritten by play. The entries keep the evening: a figure two characters sustained about ledgers and currencies, a conversation the game ended underneath, a line judged the best of the night, and an opponent's talk called 'the best part of my evening and the worst part of my game'.[^live]

## Reading and writing

New web tables always remember; only the Developer look offers an opt-out. Existing tables keep their saved setting. New LLM seats on the lobby form start at full memory depth; the profile and bare driver default to condensed depth. Remembering off disables cross-game reading and updating rather than setting the depth to zero.[^tiers]

The CLI opts in with `--logbook`. A read-only logbook supplies a fixed memory state for comparison without allowing the run to change it. Normal remembered play updates after each game, so an arena can become a learning sequence rather than a collection of independent seat-games.

## Recorded experiment

A 14 September 2026 experiment, on the earlier board, compared {{fact:plum.logbook.games}} paired games of model-piloted Plum with and without an accumulating logbook, at leash 0.5. Recorded stalls fell from {{fact:plum.logbook.stalls.off}} to {{fact:plum.logbook.stalls.on}}; in the last quarter they fell from {{fact:plum.logbook.last.off}} to {{fact:plum.logbook.last.on}}. The outcome table also recorded wrong accusations with memory.[^experiment]

{{table:plum.logbook|Historical Plum comparison at leash 0.5 on the earlier board. Outcome percentages are per game; the on leg accumulated its logbook during the run.}}

The result supports a narrow interpretation: these saved lessons accompanied fewer stalls when the menu allowed an escape. It does not establish that more memory always improves winning, and it predates the Classic-board [[landing rule]]. That rule later changed the scores responsible for the passage loop.

## Maintenance and limits

Narrative heads can be rebuilt from stored entries. Mustard and White's method contributions can be rebuilt from eligible game records, with version filtering to avoid mixing board eras. Green's live arm predictions are absent from those records, so his accumulated arm state cannot be reconstructed in the same way.[^maintenance]

More narrative depth increases context and can preserve useful detail, but can also carry stale lessons, repetition or mistaken opponent reads. The [[memory dial]] changes the supplied material, not its truth or the engine's legal actions. A dossier is a character's evolving impression of someone, not a diagnosis: the live logbooks show a read revised upward in one entry and marked 'a game out of date' in another.


## See also

[[Method memory]] · [[The debrief]] · [[Memory dial]] · [[Persona]] · [[Table talk]]

## References

{{references}}

[^logbooks]: {{cite:docs/logbooks.md|Tier 2: the entry and the head}}
[^tiers]: {{cite:docs/logbooks.md|Three tiers}}
[^entries]: {{cite:clude_storage/logbooks.py|`LogbookEntry.build` and `LogbookHead`}}
[^audit]: {{cite:docs/phase13-plan.md|2026-10-14: live memory audit and pathway revision}}
[^prompt]: {{cite:clude_llm/logbook.py|`debrief_prompt` and `condense_prompt`}}
[^step4]: {{cite:docs/phase13-plan.md|2026-10-14: steps 3 and 4 implemented, retirement staged}}
[^live]: {{cite:docs/phase13-plan.md|2026-10-15: step 4 accepted live, and a debrief lost to its token cap}}
[^experiment]: {{cite:docs/strategy-glossary.md|Plum's logbook at leash 0.5 (2026-09-14)}}
[^maintenance]: {{cite:docs/logbooks.md|Running it}}

{{navbox:clude}}
