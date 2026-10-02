---
title: Twin comparison
short: Comparing headless and model-piloted play on paired deals
categories: Measurement
redirects: Headless twin, Twin, Paired comparison
---
A **twin comparison** runs a numerical character headless and model-piloted on the same deal seeds and dice schedule. It measures what the model's discretion and conversation changed in complete games, including wins, wrong accusations, timing and departures from the top-scoring option.[^wrapper]

The pair shares a numerical method and configured dials, but accepted model choices can alter later evidence. Live replies are not fixed by the seed. A comparison with several model-piloted opponents measures their interaction as a table, not an isolated effect on just one character.

## A paired deal

Suppose Plum wins a headless game but loses its model-piloted counterpart after repeatedly choosing a corner passage. The shared initial deal makes that pair informative: the difference did not begin with a new envelope. The decision audit can then identify whether the model selected the move, whether a menu offered a useful alternative, or whether a single-option fallback never asked it.

A run can also exchange wins in both directions and finish with the same aggregate win rate. Lost and gained pairs reveal this churn. Identical percentages do not imply identical choices or identical winners on each deal.

## The controls

Each leg needs the same seeds, roster, board, non-model settings and starting memory state. Character and filler random streams remain separate from the engine stream to preserve deals and dice. A [[random bot]] drawing decision randomness from the engine breaks the latter control.[^arena]

Fixed-state [[logbook]] and [[method memory]] comparisons use read-only state. An accumulating-memory leg answers a different question: how behaviour develops during that sequence. Model name, request settings and whether calls fell back must also be recorded.

An always-failing backend supplies a strong control: it reproduces headless events because every decision falls back. Zero leash alone is weaker. Ties can still request a reply, and the zero-leash menu can close held-card bluffs or lower-scoring softmax choices that headless sampling would otherwise make.

## Recorded grid comparison

The 16 September 2026 Classic-board experiment paired 24 four-seat games, seed 7007, with the default six-character roster. Rotation gave each character sixteen seat-games. `grid-twin-base-24` was headless; `grid-twin-llm-24` piloted every seated character through Claude at the recorded presets.[^grid]

{{table:twin.grid|Historical grid twin: outcome percentages per character's sixteen seat-games. Lost/gained reports paired wins exchanged between the two legs.}}

Mustard's win rate rose and his wrong-accusation rate fell in this sample. Peacock also won more, while Plum won fewer. White had the same aggregate win rate but exchanged several individual wins. These results do not support a single direction of effect for every character.

The model leg made {{fact:twin.grid.calls}} calls without a fallback in the recorded run. Mean game length changed from {{fact:twin.grid.turns.base}} turns headless to {{fact:twin.grid.turns.llm}} with the model. The recorded costs and timings belong to that run and its provider settings, not a current pricing guarantee.

## Diagnosing a result

The audit separates choices played from calls made and records lower-score departures. Model choices can have a low departure rate yet change play through tied options, bluff selections or threshold decisions. Likewise, a long passage loop may mostly consist of single-option menus and be caused by the scoring policy rather than repeated model intervention.[^wrapper]

Plum's separate three-seat grid experiment produced a different win-rate direction from the four-seat twin. Its narrative and audit helped identify passage repeats, and the later [[landing rule]] changed their numerical incentives. Board and roster context explain why one table's result should not be made universal.

## Uncertainty and scope

Sixteen seat-games leave substantial uncertainty. A few exchanged wins can move a percentage sharply, and changing all model seats alters opponents as well as the character being summarised. Paired outcomes help locate differences, but are not by themselves evidence of a stable ranking.

This experiment also predates the landing-rule change. A current comparison should preserve the historical table and report a new identified run rather than reinterpret it as a measurement of today's scores. Exact live-model reproduction requires recorded requests and replies in addition to the numerical seed.


## See also

[[LLM wrapper]] · [[Leash]] · [[Arena]] · [[Landing rule]] · [[Determinism and seeds]]

## References

{{references}}

[^wrapper]: {{cite:docs/llm-wrapper.md|Measuring it}}
[^arena]: {{cite:clude_training/arena.py|paired random streams and LLM statistics}}
[^grid]: {{cite:docs/strategy-glossary.md|Twin comparison on the grid (Stage 2a, 2026-09-16)}}

{{navbox:clude}}
