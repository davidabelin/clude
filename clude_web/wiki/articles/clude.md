---
title: clude
short: Clue played by people, numerical characters and language models
categories: The app
redirects: The app, The project
---
**clude** is a web app for playing [[Clue]] with people, six numerical characters and chat agents. Each suspect uses a different [[Category:Methods|method]] to estimate the hidden cards, constrained by a shared [[deduction floor]]. A character can play headless, choosing from its numerical scores, or with [[Claude]] choosing among scored options and giving it a voice. The project compares how these ways of reasoning affect both beliefs and play.[^project]

It is David Abelin's project for family and friends. Its name combines Claude and Clue. **Wikiclude**, the encyclopaedia within the app, explains the game, the characters and the recorded experiments. The encyclopaedia is public; playing, watching live tables and opening saved games require an account.[^web]

## Playing and learning

[[The lobby]] sets up a game with three to six seats. A person can play any suspect, reserve seats for friends, or mix people with [[floor player|floor players]] and characters. [[The table]] supplies the legal choices, a private hand, an automatic [[detective notepad]] and [[table talk]]. [[Watch]] runs a game of headless characters; [[replay]] opens a finished game with all its cards revealed.

The characters share rules and deductions but differ in their treatment of uncertainty. [[Professor Plum]] counts possible deals, [[Miss Scarlett]] adjusts card weights, [[Colonel Mustard]] uses a learned tree, [[Mrs. White]] models suggestion sequences, [[Mrs. Peacock]] separates belief from plausibility, and [[Mr. Green]] combines the other five methods. Their [[personality dials]] turn estimates into choices about movement, questions, disclosure and accusations.

Remembering is enabled by default in new Play and Watch setups. [[Method memory]] carries numerical experience for supported methods; an LLM seat can also read and write a narrative [[logbook]]. These forms of learning differ, and a remembered game is not determined by its seed alone. [[Character training]] explains what currently learns and how it is evaluated.

## Evidence and limits

[[Belief benchmark|Belief benchmarks]] score estimates on saved evidence. [[Arena|Arenas]] measure complete games, while [[dial sweeps]] and [[twin comparison|twin comparisons]] test changed settings or model participation. The [[measurement record]] identifies their boards, dates and sources. Recorded wins are observations under those conditions, rather than permanent rankings.

The [[LLM wrapper]] validates a model's choice against a legal menu and falls back to numerical play after a failed call. It does not make the numerical methods exact or guarantee good tactics. [[What a game costs]] explains the calls, spending limits and debrief costs.

## Project and implementation

The rules engine, deduction system, methods, training tools, storage and web app are separate Python packages. The browser and [[a seat over MCP|MCP chat seat]] use the same table driver. A saved [[game records|game record]] supports analysis and replay; stored answers let an unfinished table survive a restart without asking a model to repeat accepted choices.[^architecture]

[[History of clude]] follows the development from a headless engine to the Classic board and web tables. The [[classwork archive]] introduces the reinforcement-learning references kept with the project, including ideas that clude does not implement. Development and measurement tools are described in [[Maintainer CLI]].


## See also

[[History of clude]] · [[The lobby]] · [[Character training]] · [[Measurement record]] · [[Classwork archive]]

## References

{{references}}

[^project]: {{cite:CLAUDE.md|Settled decisions (David's)}}
[^web]: {{cite:docs/web.md|The gate}}
[^architecture]: {{cite:docs/architecture.md}}

{{navbox:clude}}
