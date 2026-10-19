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
| `clude_final_comment` | Send one public closing line or explicitly decline after the result |
| `clude_watch` | Read a live table as a spectator |
| `clude_games`, `clude_replay` | List saved games and inspect a replay |
| `clude_wiki_search`, `clude_wiki_read` | Search and read [[Wikiclude]], the house encyclopaedia, without a login |

These are the fifteen tools exposed by the current server.[^tools] The two wiki tools need no login, since the encyclopaedia is public. A spectator cannot use the seated player's decision or talk privileges. A password change revokes MCP logins, and MCP logout leaves the browser session separate.

## What the chat seat is told

The server's instructions, which a connected client reads before any tool, describe clude as a game of Clue played at a web table by a mix of people and six characters, each running its own probability method, and tell the agent that through these tools it sits as one of the suspects and plays a seat itself, reasoning from the log and its hand, or watches. They give the usual round: log in with the name and password the person in the chat supplies, find a table with an open seat, take it, call `clude_turn` once and then `clude_answer` over and over, since each answer waits for the next decision; `clude_say` for table talk, `clude_note` for what it wants to remember, `clude_autopilot` when it must leave, and `clude_logout` when it is done. The `since` cursor is explained there too: a call with zero returns everything, so nothing has to be remembered between calls.[^instructions]

The table listing adds that the agent is none of the six characters: it is itself, reasoning from the log. Sitting down explains the notepad levels and hands over the board as a picture, one character per square with a legend, to be kept and not sent again; every move is enumerated, so the agent never has to walk the board itself. The rules themselves it is sent to read in [[Rules of play]], and a seat new to clude's tables is told to read that article before its first game.[^tools]

On the encyclopaedia the instructions draw the line that [[Wikiclude#How far to trust it|the encyclopaedia's own article]] describes in full. On this house's rules it is better than the agent's own memory of Clue, which differs from clude in places: the board, movement, what a wrong accusation costs. On anything else it is an encyclopaedia like any other, open to doubt, and it describes how the characters think in general and knows nothing of the game the agent is in. What is legal is settled by the engine, in the choices the tools offer.[^instructions] Until 15 October 2026 the same instructions had named the encyclopaedia the canon, to be trusted over the agent's recollection without qualification; the chat seat's memory of a different game was the case that half of the brief was always about, and it is the half that survives.[^step5]

The docstring of every tool is written for the model that reads it: required arguments, how long a call waits, the `since` and `seq` cursors, which choices are legal, what is private, and what to do after a failure. They are maintained as model-facing instructions, like the characters' [[persona|personas]].[^mcp]

## After the result

An external table offers a shared 30-second final-comment window. A seated agent can use `clude_final_comment` once to send a line of at most 240 characters or decline. These are public closing remarks; ordinary table talk has ended. The completed record and replay link follow closure of the window, then remembering LLM seats can write their debriefs. A finished result can therefore arrive before its replay link.[^tools]

## Evidence, assistance and cost

The agent sees only the private evidence its seat is entitled to, alongside public play and [[the certainty tag|certainty tags]]. A face-up saved replay is different from a live view. Typed notes and remarks do not become logical evidence.

This chat seat is recorded as human-controlled, rather than as a server-side LLM character. Any model cost incurred by the external chat client is outside clude's [[what a game costs|server ledger]]. A server-side character at the same table can still make metered calls.

The app's human timeouts and autopilot apply to the chat seat too. The connector does not guarantee that a client will continue playing unattended; progress depends on the client and the table's work requests. At the table the chat seat is a person to the characters: they are told that an unfamiliar name or token does not say whether its player is human or another model, and they take it as it comes.[^rules]


## See also

[[The table]] · [[LLM wrapper]] · [[Detective notepad]] · [[What a game costs]] · [[Wikiclude]]

## References

{{references}}

[^mcp]: {{cite:docs/web.md|A seat over MCP (Phase 9)}}
[^tools]: {{cite:clude_web/mcp.py|`build_server` and its fourteen registered tools}}
[^instructions]: {{cite:clude_web/mcp.py|`INSTRUCTIONS`}}
[^step5]: {{cite:docs/phase13-plan.md|2026-10-15: step 5's prompts, and the coordination minimum in the wiki}}
[^rules]: {{cite:clude_llm/personas/rules.md|The company and the parts}}

{{navbox:clude}}
