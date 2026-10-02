---
title: Logbook
short: Persistent narrative entries, lessons and opponent dossiers
categories: Memory
redirects: Logbooks, The logbook, Memory, Debrief
dyk: ...that memory depth 0 still reads the condensed [[logbook]]?
---
A **logbook** stores a character's narrative memory between games. With remembering enabled, a model-piloted seat receives the revealed deal after play and writes an entry in its [[persona|voice]]. A condensed head maintains the outcome tally, standing instructions and opponent dossiers. Before a later game, the [[memory dial]] controls how much is read back.[^logbooks]

The logbook is distinct from the immutable game record and from numerical [[method memory]]. Headless seats do not write narrative entries. [[Colonel Mustard]], [[Mrs. White]] and [[Mr. Green]] can retain method memory in either headless or model-piloted play; Scarlett, Plum and Peacock have no persistent numerical method state.

## From a game to a later decision

After a game in which Plum wasted questions in a cleared room, a [[The debrief|debrief]] might save a lesson about moving on sooner. At the next table, Plum's memory block can include that standing instruction. The model may then use it when choosing among allowed moves.

This is a possible memory path, not a claim about a particular stored entry. The instruction cannot add a move excluded by the [[leash]], and it cannot tell Plum where the next game's room card was dealt. Memory concerns past play rather than privileged knowledge of a new deal.

## Three kinds of stored information

| Tier | Stored information | Use |
|---|---|---|
| Game record | Actual deal, events, settings and outcome | Replay, measurement and learning inputs |
| [[Method memory]] | Numeric training rows, opponent counts or arm parameters | Method-specific reasoning in later games |
| Narrative memory | Entries, instructions and dossiers | Context for later model choices and speech |

These tiers have different access rules. The finished record is face-up data for analysis; a live seat still sees only its private observation. A narrative entry is written by the model and may contain an interpretation or error rather than a verified inference.[^tiers]

## Entries and the head

Code supplies an entry's identity, serial number, date, game id, token, table, outcome and model. The model supplies a title, summary, flags, narrative, opponent evaluations, insights, lessons, revised instructions and dossiers. Flags and lists are normalised and capped, and opponent fields are restricted to identities present at that table.[^entries]

The head combines a computed tally with the latest standing instructions and revised dossiers. Its tally counts games **with narrative entries**, not necessarily every game the character ever played. A failed debrief writes no entry, so the tally can omit an otherwise completed game.

A logbook belongs to the roster identity rather than the coloured token. A character can keep its logbook when playing a different token, and opponent dossiers can follow a human account across token changes.

## Reading and writing

New web tables remember by default, with a separate opt-out. Existing tables keep their saved setting. New LLM seats on the lobby form start at full memory depth; the profile and bare driver default to condensed depth. Remembering off disables cross-game reading and updating rather than setting the depth to zero.[^tiers]

The CLI opts in with `--logbook`. A read-only logbook supplies a fixed memory state for comparison without allowing the run to change it. Normal remembered play updates after each game, so an arena can become a learning sequence rather than a collection of independent seat-games.

## Recorded experiment

On the ring board, a 14 September 2026 experiment compared {{fact:plum.logbook.games}} paired games of model-piloted Plum with and without an accumulating logbook, at leash 0.5. Recorded stalls fell from {{fact:plum.logbook.stalls.off}} to {{fact:plum.logbook.stalls.on}}; in the last quarter they fell from {{fact:plum.logbook.last.off}} to {{fact:plum.logbook.last.on}}. The outcome table also recorded wrong accusations with memory.[^experiment]

{{table:plum.logbook|Historical ring-board Plum comparison at leash 0.5. Outcome percentages are per game; the on leg accumulated its logbook during the run.}}

The result supports a narrow interpretation: these saved lessons accompanied fewer stalls when the menu allowed an escape. It does not establish that more memory always improves winning, and it predates the Classic-board [[landing rule]]. That rule later changed the scores responsible for the passage loop.

## Maintenance and limits

Narrative heads can be rebuilt from stored entries. Mustard and White's method contributions can be rebuilt from eligible game records, with version filtering to avoid mixing board eras. Green's live arm predictions are absent from those records, so his accumulated arm state cannot be reconstructed in the same way.[^maintenance]

More narrative depth increases context and can preserve useful detail, but can also carry stale lessons, repetition or mistaken opponent reads. The [[memory dial]] changes the supplied material, not its truth or the engine's legal actions.


## See also

[[Method memory]] · [[The debrief]] · [[Memory dial]] · [[Persona]]

## References

{{references}}

[^logbooks]: {{cite:docs/logbooks.md|Tier 2: the entry and the head}}
[^tiers]: {{cite:docs/logbooks.md|Three tiers}}
[^entries]: {{cite:clude_storage/logbooks.py|`LogbookEntry.build` and `LogbookHead`}}
[^experiment]: {{cite:docs/strategy-glossary.md|Plum's logbook at leash 0.5 (2026-09-14)}}
[^maintenance]: {{cite:docs/logbooks.md|Running it}}

{{navbox:clude}}
