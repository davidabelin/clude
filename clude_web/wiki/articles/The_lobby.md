---
title: The lobby
short: Game setup, open tables and stored-game folders
categories: The app
redirects: Lobby
---
**The lobby** is [[clude]]'s signed-in home page. It starts games, lists unfinished tables, offers [[Watch|headless games to watch]] and leads to saved games. Its seat choices specify who controls each suspect; they do not change that suspect's cards or the [[rules of play]].[^lobby]

## Choosing the seats

The Play form has one row per suspect, with choices in this order:

| Choice | Occupant |
|---|---|
| empty | The token is left out of the game |
| open | A seat reserved for another person |
| floorbot | A player using the shared deduction floor |
| me | The signed-in person |
| X (LLM) | That suspect's numerical character, with the model choosing and speaking |
| X (headless) | That suspect's numerical character, choosing without a model |

Here X is the character's name. Three to six seats must be occupied or reserved. The model choices remain visible but are disabled when the service has no model key. A person playing Plum does not thereby use Plum's numerical method: the method belongs to the character seat, not the token.

An optional [[determinism and seeds|seed]] fixes the engine's deal and dice. The characters always remember; only the [[Looks|Developer look]] shows a checkbox to opt out, and the table's model budget (by default $2). An LLM seat has a [[memory dial|memory-depth control]] while remembering is on; a headless seat can use supported numerical [[method memory]] but has no model-written voice or narrative read-back.

## Dealing and joining

Deal starts immediately when no seat is open. Otherwise the setup becomes a waiting table. Another signed-in person takes an open seat; the game can be dealt only after every reservation is filled, by someone seated at it. [[The table]] then provides each person's own hand and choices.

The Tables list contains unfinished games and waiting setups. Closing a tab leaves the table available. Returning to it resumes the same game; rebuilding after a process restart uses the saved setup and accepted answers. End table, available to a seated person or its creator, ends an unfinished table and drops its game rather than saving it as a completed record.

## Watching and finding games

Watch starts numerical characters and cannot call a language model. Its characters remember too (the Developer look has its own checkbox), and it has controls for advancing the game.

Stored games has four folders. **Practice set one** and **practice set two** contain completed games from tables and Watch: set one the store's `web` run, closed on 2026-10-07, and set two every game since. **Development phase one** and **phase two** contain other runs, arenas, sweeps, leash ladders and fixtures, before and since the [[Professor Plum|new Plum]]. A run lists seats, winner, turns and suggestions, with links to [[replay]]. Wall time is present when it was recorded; [[what a game costs|cost]] appears in the Developer look. A missing value is not a zero.[^records]


## See also

[[The table]] · [[Watch]] · [[Game records]] · [[Looks]]

## References

{{references}}

[^lobby]: {{cite:docs/web.md|The lobby}}
[^records]: {{cite:clude_web/views.py|`PRACTICE`, `DEVELOPMENT` and `run_page`}}

{{navbox:clude}}
