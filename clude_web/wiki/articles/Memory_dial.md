---
title: Memory dial
short: How much of a narrative logbook is read before a game
categories: Memory
redirects: The memory dial, Memory depth
---
The **memory dial** selects how much of a character's narrative [[logbook]] is supplied to the model before a game. At 0 it reads the condensed head; at 0.5 it adds an index of all entries; at 1 it includes every entry in full. Intermediate values select recent entries in stages.[^depth]

Zero does **not** mean remembering off. The table's remembering setting separately enables or disables cross-game memory. The dial does not change numerical [[method memory]] and has no effect on a headless character's decisions.

## A ten-entry example

Consider a logbook with ten entries, in chronological order. The head always supplies its tally, standing instructions and dossiers for opponents at the current table. The dial then adds the following material:

| Depth | Indexed summaries | Full entries |
|---|---|---|
| 0 | {{code:memory.0.index}} | {{code:memory.0.full}} |
| 0.25 | {{code:memory.0.25.index}} most recent | {{code:memory.0.25.full}} |
| 0.5 | {{code:memory.0.5.index}} | {{code:memory.0.5.full}} |
| 0.75 | {{code:memory.0.75.index}} | {{code:memory.0.75.full}} most recent |
| 1 | {{code:memory.1.index}} | {{code:memory.1.full}} |

These counts come from the implementation's `memory_counts`. An indexed entry contains its serial, date, table, outcome, summary and flags. A full entry adds its narrative, evaluations, insights and lessons. Recent subsets remain in chronological order.[^counts]

## The selection rule

Let $n$ be the entry count and $m$ the depth. For $0<m\leq0.5$, the number indexed is

$$ \left\lceil\frac{nm}{0.5}\right\rceil, $$

where the ceiling brackets mean round upwards to the next integer. No full entries are included in that range. For $0.5<m\leq1$, the whole index is included and the full-entry count is

$$ \left\lceil\frac{n(m-0.5)}{0.5}\right\rceil. $$

The upward rounding means even a small positive depth can add one entry. It also makes context size change in steps rather than perfectly continuously as the slider moves. These are counts of entries, not fractions of tokens: entries differ in length.

## Defaults and remembering

The profile default is {{code:neutral.memory}}, the head-only setting. A new web lobby LLM seat starts at depth 1, while the bare driver and CLI default to the profile setting. Existing tables preserve their saved depth. Remembering off prevents reading and updating the cross-game state regardless of the saved slider value.[^depth]

An empty logbook sends no memory block. Increasing its dial cannot supply entries that do not exist. The characters' dossiers are selected for identities present at the next game rather than indiscriminately listing every past opponent.

## How it reaches a decision

The selected text is rendered once before the game and travels as a second system block after the stable [[persona]] and house rules. It remains unchanged during that game. The changing hand, suggestion history and menu belong to the decision prompt instead.[^wrapper]

This arrangement allows context caching, but does not make the remembered prose authoritative. A model can treat a lesson as advice only within its allowed [[leash]]. More depth does not bypass the numerical scores or legal-move checks.

## Evaluation and limits

A [[dial sweeps|memory-depth sweep]] should use one fixed logbook state read-only across values. Otherwise a deeper setting might also receive later, different entries, confounding depth with accumulated experience. A normal remembered arena intentionally learns across games and answers a different question.

Greater depth can preserve useful details but also increases prompt length and carries more stale or repetitive narrative. No monotonic improvement in win rate follows from the selection formula. [[Logbook#Recorded experiment|Recorded Plum results]] concern a particular accumulating-memory run, not an exhaustive test of every depth.


## See also

[[Logbook]] · [[The debrief]] · [[Method memory]] · [[Dial sweeps]]

## References

{{references}}

[^depth]: {{cite:docs/logbooks.md|The `memory` dial: what a character reads back}}
[^counts]: {{cite:clude_storage/logbooks.py|`memory_counts` and `render_memory`}}
[^wrapper]: {{cite:docs/llm-wrapper.md|Memory (Phase 7)}}

{{navbox:clude}}
