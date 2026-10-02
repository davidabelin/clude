---
title: What a game costs
short: Metered model calls, game budgets and recorded spending
categories: The app
redirects: Game cost, Model cost
---
**What a game costs** in [[clude]] depends on whether its seats call a language model, how many decisions and remarks they request, and whether they write [[debrief|debriefs]]. The server prices token usage and records spending for each table and model seat. Headless play makes no model calls; the ledger is not a measure of hosting costs or an external chat client's bill.[^cost]

## Calls and token prices

A model-piloted character can request a choice and remark during its turn, join off-turn [[table talk]], and write a narrative debrief after the game. Input, output and eligible cached input tokens have separate prices. The cost estimator uses the model price table configured in the implementation; historical dollar values belong to the model and usage recorded at the time.[^prices]

A short game can therefore cost more than a longer one if it opens more menus or writes longer responses. A decision with one allowed option need not call the model, and a fallback can occur before any call. Calls, decisions and game turns are different denominators.

## Spending limits

The table has a model budget, normally {{code:llm.table_budget}} US dollars unless configured otherwise. The service also has a daily cap, normally {{code:llm.daily_cap}} dollars. Before calling, the metered backend checks both and refuses an unpriced model. At a reached limit the numerical character takes over; the game can continue.

Usage is added after the response, so a completed call can take the recorded total past a cap. The budget is not a reservation of the largest possible next response. The daily ledger uses UTC days, while the table's accumulated spending persists across midnight. Changing the date does not replenish its game budget.

## Debriefs belong to the game

The finish can leave remembering LLM seats writing their logbook entries. These are paid calls too, and the game's cost is final only when they finish or wrapping is ended. In the recorded first {{fact:cost.web.games}} web games with model seats, debriefs accounted for {{fact:cost.web.debrief.share}}% of the model bill: {{fact:cost.web.debrief.total}} US dollars out of {{fact:cost.web.total}}. This was a small historical sample, not a fixed overhead for every game.[^sample]

## Where spending appears

Developer shows cost details on tables and saved-game lists. Case-file light and Gaslight dark omit them from their playing interface. A non-spending seat's share is zero; a saved game's missing cost may instead mean that cost was not recorded or the game had no model seat.

The ledger keeps a daily total and a table total with per-seat shares. Final values are copied into the game record and run summary. Older web games can be priced from daily ledgers through [[Maintainer CLI]], without inventing a seat split that was not recorded.

Characters are not told their cost in prompts or logbooks. The ledger records the service's model usage for the maintainer and the Developer view; it is not part of the character's playing incentives. [[Arena|Arena]] model statistics and the [[measurement record]] supply the conditions behind experimental costs.


## See also

[[LLM wrapper]] · [[The debrief]] · [[Looks]] · [[Game records]]

## References

{{references}}

[^cost]: {{cite:clude_llm/metered.py|`Ledger` and `MeteredBackend`}}
[^prices]: {{cite:clude_llm/anthropic_backend.py|`PRICES_PER_MTOK` and `estimate_cost`}}
[^sample]: {{cite:docs/web.md|A table}}

{{navbox:clude}}
