---
title: A seat over MCP
short: A chat agent playing through the same live table as a browser
categories: The app
redirects: MCP, MCP seat, Chat seat
---
**A seat over MCP** lets a chat agent play one of [[clude]]'s human seats through the [[w:Model Context Protocol|Model Context Protocol]] (MCP). The tools use the same live table registry as the browser. The chat agent receives its seat's hand, evidence and legal options, then submits decisions and table talk. It is distinct from an [[LLM wrapper|LLM character]], whose numerical method and persona are supplied by clude.[^mcp]

## Joining and playing

An owner configures a connector to the service's MCP endpoint. The client signs in with an app account using `clude_login`, lists tables with `clude_tables`, and takes an open token with `clude_sit`. Connector access and account login are separate: possessing the endpoint does not itself occupy a seat.

`clude_turn` returns the current situation. `clude_answer` submits a legal choice, optionally queuing an accusation or pass for the next accusation question. A movement target can name a room through `toward`, letting the server select a representative legal move. A chat seat chooses for itself; no character persona advises it simply because it occupies that suspect's token.

The tools can wait for progress and return only events after a `since` cursor. Compact responses keep a long game from repeatedly filling the chat context with unchanged evidence. An account chooses a full automatic notepad when sitting, or the harder view without that assistance. The hard view also omits its own certainty reading, while other seats' public tags remain visible.

## The tools

| Tool | Purpose |
|---|---|
| `clude_login`, `clude_logout` | Start a login or revoke that account's MCP logins |
| `clude_tables`, `clude_sit` | List tables and take an open seat |
| `clude_turn`, `clude_answer` | Read the game and answer a pending decision |
| `clude_say`, `clude_note` | Speak at the table or keep private notes |
| `clude_autopilot` | Hand control to the stand-in or take it back |
| `clude_watch` | Read a live table as a spectator |
| `clude_games`, `clude_replay` | List saved games and inspect a replay |

These are the twelve tools exposed by the current server.[^tools] A spectator cannot use the seated player's decision or talk privileges. A password change revokes MCP logins, and MCP logout leaves the browser session separate.

## Evidence, assistance and cost

The agent sees only the private evidence its seat is entitled to, alongside public play and [[the certainty tag|certainty tags]]. A face-up saved replay is different from a live view. Typed notes and remarks do not become logical evidence.

This chat seat is recorded as human-controlled, rather than as a server-side LLM character. Any model cost incurred by the external chat client is outside clude's [[what a game costs|server ledger]]. A server-side character at the same table can still make metered calls.

The app's human timeouts and autopilot apply to the chat seat too. The connector does not guarantee that a client will continue playing unattended; progress depends on the client and the table's work requests.


## See also

[[The table]] · [[LLM wrapper]] · [[Detective notepad]] · [[What a game costs]]

## References

{{references}}

[^mcp]: {{cite:docs/web.md|A seat over MCP (Phase 9)}}
[^tools]: {{cite:clude_web/mcp.py|`build_server` and its twelve registered tools}}

{{navbox:clude}}
