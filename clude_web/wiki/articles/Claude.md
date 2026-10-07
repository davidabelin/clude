---
title: Claude
short: The model service behind character voices and the independent chat-seat role
categories: The app
redirects: Claude (language model), The model, LLM
---
**Claude** is the [[w:Claude (language model)|language model]] from [[w:Anthropic|Anthropic]] used for [[clude]]'s model-piloted character voices. The name clude combines the game's name with Claude. Within the project, a model can either pilot a numerical character through the [[LLM wrapper]] or take an independent chat seat through MCP, the Model Context Protocol.[^wrapper]

Those roles have different reasoning inputs. A wrapped character receives its method's estimates and a leashed menu. An independent chat seat receives its own game evidence and legal choices and reasons without a numerical character method behind it. Neither role is shown the current hidden deal during play.

## A model-piloted character

In a seat labelled X (LLM), the X character supplies a [[belief]], [[personality dials]] and a [[persona]]. The wrapper asks the model to choose allowed options and optionally provide [[table talk]]. A valid model choice can change the action within the leash; a failure invokes the underlying headless choice.[^wrapper]

For example, Plum's network can rate two destinations closely enough that both are allowed. Claude may select one in Plum's voice. This does not mean Claude ran the network or replaced Plum's card probabilities. It chose using the estimates and contextual information the wrapper supplied.

The application's backend configuration identifies the actual model used. Recorded runs preserve their model and call settings; 'with Claude' is a role description, not evidence that every historical run used an identical provider configuration.

## An independent chat seat

MCP exposes a game seat to a chat agent. The agent can inspect its own hand, the visible history, floor deductions and legal decision requests, then submit answers. Its table row has no numerical character method or persona-derived belief. The automatic notepad still provides the common logical deductions.[^mcp]

This seat is useful when a person is playing through conversation with a model client. The client mediates the game actions, and its reasoning can differ from the six characters. The same disclosure rules apply: an unseen card stays hidden, and the engine checks what the seat must show.

MCP is the transport for that interaction rather than another inference method. Client prompts and conversation can influence its decisions, but the character's leash and presets do not govern an independent chat seat.

## Evidence, talk and memory

The wrapped model sees only the observation allowed to its seat. Recent [[table talk]] is included as conversation, not certified card ownership. When remembering is enabled, the [[memory dial]] chooses a stable logbook block supplied during the game. Headless seats may have [[method memory]] but do not make these narrative model calls.[^memory]

After a finished game, the [[The debrief|debrief]] reveals the deal and asks the model to reflect. Post-game knowledge can support lessons for later games, but it says nothing directly about a new shuffled hand. A remembered read on an opponent remains a behavioural interpretation.

## Evaluation and limits

The [[twin comparison]] measures complete headless and model-piloted games on the same deals and dice. Recorded results varied by character and table. A model can improve an allowed choice, postpone a good accusation, or repeatedly select an unhelpful option. Its speech and its playing success require separate assessment.

A seed reproduces the numerical setup but does not guarantee identical live model replies. Recorded backend exchanges supply the stronger control when exact replay is needed. Invalid replies and service errors are visible as fallbacks in the decision audit rather than evidence of accepted model play.


## See also

[[LLM wrapper]] · [[Persona]] · [[Leash]] · [[Twin comparison]] · [[Determinism and seeds]]

## References

{{references}}

[^wrapper]: {{cite:docs/llm-wrapper.md|What happens on one decision}}
[^mcp]: {{cite:docs/web.md|A seat over MCP (Phase 9)}}
[^memory]: {{cite:docs/logbooks.md|Three tiers}}

{{navbox:clude}}
