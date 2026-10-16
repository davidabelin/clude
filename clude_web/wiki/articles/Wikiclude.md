---
title: Wikiclude
short: The house encyclopaedia, public to readers and read by the model seats
categories: The app
redirects: The encyclopaedia, House encyclopaedia, Canon, The canon, Wiki
dyk: ... that [[Wikiclude]] is read by the characters at the table, and that Colonel Mustard has never opened it?
---
**Wikiclude** is [[clude]]'s own encyclopaedia: one article per subject, on the rules of play and the board, the six characters and their methods, the mathematics, the measurements and the app itself, written for family and friends at every level of expertise at once, in Wikipedia's organisation and clude's looks. It is public, under `/wiki`, and needs no account.[^web]

It is also the house reference the model seats read. A character played by a language model carries the index of its articles and two lookup tools, and a chat seat over MCP has the same two tools without a login. Since 15 October 2026 the prompts call it fallible: better than a model's own memory of Clue on how this house plays, and otherwise an encyclopaedia to be trusted about as far as Wikipedia is.[^rules][^canon]

## What it holds

The articles fall into ten categories: the characters, their methods, what they share, the game, personality, memory, mathematics, measurement, the app, and a classwork archive, with a set of short algorithm entries kept deliberately as stubs. A method or concept article is layered in a fixed order, so that a reader can stop at any heading with a complete answer at that depth: what it is and why it matters at the table; a worked example from a real seeded game; how it works, with small numbers; the mathematics, every symbol defined; the implementation; what the measurements found; and where the method has a flaw that is the character. A character article is a biography.[^design]

The furniture is Wikipedia's: a Main Page with a featured article and 'Did you know', categories, navboxes, redirects, All pages, Random article, What links here and a search. Links come in three kinds, told apart by more than colour: an in-app link in the red thread, a link out to Wikipedia in its own blue with a small mark, and a numbered reference to the document, module, book or paper the statement came from.[^design]

## Who reads it

People reach it from the header bar's wooden question mark and the footer, and the same question mark is every wiki page's logo.[^web]

A model-piloted character, the [[LLM wrapper]] in a seat, carries a cached system block naming every article, about five hundred tokens, and two tools on every decision, remark and debrief request: `wiki_search`, which returns up to {{code:canon.search_limit}} matching articles with a line and an excerpt each, and `wiki_read`, which hands over a short article whole, otherwise its lead and section list and then one section at a time, never more than {{code:canon.read_limit}} characters. The backend answers a lookup inside the same call, up to {{code:llm.max_lookups_per_call}} rounds a call and {{code:llm.max_lookups_per_game}} a game, and the model still answers in the decision's schema. Every lookup is audited with the decision and counted by the [[arena]]; a recording keeps the lookups and replays them without touching the wiki.[^canon][^wrapper]

A chat seat has `clude_wiki_search` and `clude_wiki_read`, and the server's instructions send a seat new to clude's tables to [[Rules of play]] before its first game ([[A seat over MCP]]).[^mcp]

How often a character actually looks something up is a matter of its [[persona]], measured after the fact rather than set by a dial. When the lookup was accepted, in {{fact:canon.calls}} ordinary calls at low effort no character found a question of fact to look up, though a lookup asked for explicitly succeeded; a routine move or suggestion raises none. The article pass that followed Phase 13 was written on the assumption that a character can read its own biography, so nothing here should contradict what the character was told.[^acceptance][^w8]

## How far to trust it

The shared rules, the two tools' descriptions and the MCP instructions all draw the same three-way line, settled by David in Phase 13.[^rules][^step5]

- **On how this house plays**, the board, movement, how a suggestion is disproved and what a wrong accusation costs, the encyclopaedia is the better source than a model's own recollection of [[Clue]], which differs from clude in places. This was never authority over the characters; it was always about a chatbot's memory of a different game, and it is kept.
- **On everything else**, a biography, a method description, a reputation, an article about the character itself, it is an encyclopaedia written up by people, and may be trusted about as far as Wikipedia: useful, usually right, sometimes out of date, open to doubt. An article about a character may be thin or wrong, and the character is entitled to say so. Nothing in it outranks a card a character was shown or what it watched someone do at the table.
- **What is legal** is settled by the engine, in the menu a seat is given. No article decides it.

A character may mention, quote or argue with the encyclopaedia as the occasion suggests; knowing a thing without parade remains the better style, but the earlier prohibition on citing it aloud is gone. It describes how everyone thinks in general and knows nothing of the deal in play.[^rules]

Until 15 October 2026 the rules had named it the canon, to be trusted over a character's recollection and over anything said at the table, and never cited. That brief is superseded; the access, the tools and the caps it introduced are unchanged.[^step5][^canon-plan]

## What the characters make of it

Each persona says how readily its character consults the encyclopaedia, and the six differ as their temperaments do.[^personas]

| Character | Reads it |
|---|---|
| [[Professor Plum]] | Has read every article and consults it by reflex, on a rule, a method or another player's record; would rather the knowledge seemed his own, cites it when it settles a point, and is the first to notice an article that is thin, dated or wrong about him |
| [[Mrs. Peacock]] | Does not guess at a rule or a reputation; when the proper form or another player's method is in doubt, looks it up before she speaks |
| [[Mrs. White]] | Reads the biographies, not the mathematics: what it says of people is worth knowing, and worth weighing against what she sees |
| [[Mr. Green]] | Reads up on whoever he is borrowing from, since their article says how they think and where they go wrong |
| [[Miss Scarlett]] | Skimmed it once and rarely opens it again; her own numbers are faster |
| [[Colonel Mustard]] | Has never read it and does not intend to start, unless someone quotes it against him |

## Keeping it true

Every measured number an article quotes comes from one table in the code, each entry naming the document and heading it was copied from, and a test checks each against that document; when something is re-measured, one line changes and every article follows. Constants and worked examples are read from the live modules when the wiki is built, so an article cannot disagree with the code it describes. Everything is rendered once, when the app starts, and a malformed article fails the start and a test rather than a reader.[^true][^web] One consequence of the index block: a recorded model exchange is keyed on the whole request, titles included, so adding an article moves the replay fixtures as a persona edit does, and this article did.[^fixtures]

An article is a Markdown file in the repository, edited like any other file. The characters cannot edit it: a character editing the encyclopaedia is a possibility the project has deferred, since it would need its own design for attribution, review and the difference between an opinion and a change to the documented rules.[^deferred]


## See also

[[clude]] · [[LLM wrapper]] · [[A seat over MCP]] · [[Persona]] · [[Rules of play]]

## References

{{references}}

[^web]: {{cite:docs/web.md|Wikiclude}}
[^rules]: {{cite:clude_llm/personas/rules.md|The encyclopaedia}}
[^canon]: {{cite:clude_llm/canon.py|`WIKI_TOOLS`, `index_block` and `WikiCanon`}}
[^design]: {{cite:docs/wikiclude-plan.md|3.2 One article, every reader}}
[^wrapper]: {{cite:docs/llm-wrapper.md|The canon}}
[^mcp]: {{cite:clude_web/mcp.py|`INSTRUCTIONS`, `clude_wiki_search` and `clude_wiki_read`}}
[^acceptance]: {{cite:docs/canon-plan.md|7.3 Acceptance (2026-10-09, approved by David the same day)}}
[^w8]: {{cite:docs/wikiclude-plan.md|14. W8: the Phase 13 alignment pass}}
[^step5]: {{cite:docs/phase13-plan.md|2026-10-15: step 5's prompts, and the coordination minimum in the wiki}}
[^canon-plan]: {{cite:docs/canon-plan.md|3.2 Innate, not announced}} The superseded brief, kept as dated history.
[^personas]: {{cite:clude_llm/personas/Plum.md}} and the other five scripts in the same folder.
[^true]: {{cite:docs/wikiclude-plan.md|3.6 Keeping it true}}
[^deferred]: {{cite:docs/phase13-plan.md|7. Step 5: fallible Wikiclude and reference material}}
[^fixtures]: {{cite:docs/wikiclude-plan.md|15.2 Where it departs from the brief}}

{{navbox:clude}}
