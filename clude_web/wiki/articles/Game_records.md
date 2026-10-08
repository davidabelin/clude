---
title: Game records
short: Saved events, setups, seat identities and run summaries
categories: The app
redirects: Game record, Stored games, Development games, Practice games
dyk: ...that [[replay]] reveals the cards to its viewer while rebuilding each seat's beliefs from masked evidence?
---
**Game records** are the stored accounts of completed [[clude]] games. A record contains the setup, seats, hands, envelope and events needed for [[replay]] and analysis, with model audits and costs when available. Records are grouped into runs. An unfinished table's saved working state is a separate document, allowing play to resume before a final record exists.[^records]

## What is recorded

The structured log includes moves, suggestions, refutations, accusations and the outcome. Each seat has a token, occupant label and kind. The label distinguishes a person's identity from the suspect they play, so [[method memory|opponent memory]] can follow that person across tokens.

The completed record contains hidden information for analysis. During a live game, the table's seat view masks hands and shown cards. Being able to open a saved replay after the finish does not imply those cards were public during play.

An LLM seat's audit can record the menu, reply, accepted choice, fallback, usage and remarks. The audit explains how a decision was obtained, while the engine event log records what actually happened. A model's proposed illegal action is not a legal move merely because it appears in the audit.

## Runs and summaries

Practice set one contains the `web` run, closed on 2026-10-07, and practice set two the `web-2` run that has taken every game since; development phase one and phase two list the other run identifiers, before and since the new Plum. An arena or sweep can retain games under its own identifiers, while a fixture can provide a known record for tests. Run summaries list seats, winners, turn and suggestion counts without opening every full record.[^folders]

Newer web summaries can include elapsed wall time from deal to finish. Older records and arena records can leave it blank. Recorded model costs are shown only in Developer. A summary is an index into the evidence, not the full evidence itself; the replay exposes the events behind a row.

## Storage and reproducibility

The storage interface supports local files and a cloud object store. The same logical record format is used by the CLI and web app. [[Maintainer CLI]] can list, inspect and copy records between stores.[^storage]

Keeping the seed helps reproduce a numerical game, but the board, roster, profiles, implementation and starting memory also matter. Live model replies are not fixed by the engine seed. Unfinished-table rebuilding instead reuses accepted answers and saved starting memory. Historical records remain useful when a later implementation would play the deal differently: they preserve the observed events rather than silently replacing them.


## See also

[[Replay]] · [[Determinism and seeds]] · [[Measurement record]] · [[Maintainer CLI]]

## References

{{references}}

[^records]: {{cite:docs/architecture.md}}
[^folders]: {{cite:docs/web.md|The lobby}}
[^storage]: {{cite:docs/cli.md|`store`}}

{{navbox:clude}}
