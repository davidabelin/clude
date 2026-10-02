---
title: Arena
short: Evaluation of playing behaviour in complete seeded games
categories: Measurement
redirects: The arena, Arenas
---
The **arena** evaluates [[clude]] characters by playing complete games and recording their outcomes and decisions. It measures wins, wrong accusations, accusation timing, disclosure and held-card questions, alongside numerical and model-call costs. Unlike the [[belief benchmark]], the arena lets a character's choices change the evidence available later.[^arena]

Seeded runs support paired comparisons with matching deals and dice when decision randomness is kept separate from the engine stream. Results depend on the board, roster, settings and memory state. Small arenas provide useful observations but uncertain estimates of long-run strength.

## At the table

Suppose Scarlett and Plum both have reasonable card estimates. Scarlett's lower threshold lets her accuse first, but a wrong guess eliminates her. Plum can lose despite accurate estimates if he walks too far for his next question or waits while another player solves the game. The arena records these outcomes rather than deciding success from a saved probability vector.

Changing Scarlett's threshold can also change Plum's results. If she remains active longer, she makes different suggestions and shows cards at different times. An unchanged opponent's win-rate swing is therefore not automatically sampling noise: the opponent faced changed play.

## Seats and runs

The arena rotates roster entries and can cycle table sizes or fix one. Missing seats are filled with [[floor player|floor players]]. Characters retain their own suspect tokens; floor seats take available tokens. The rotation changes seat order and participation, not which character identity its method represents.[^arena]

A character can consequently play fewer seat-games than the run contains deals. In the recorded mixed-size {{fact:arena.grid.games}}-game arena, individual characters played sixteen or twenty games. Their percentages use those participation counts, not the common deal count.

Private character and filler streams preserve the engine's dice sequence across changed profiles on the same seeds. [[Random bot|Random-bot]] entries are an exception because they consume the engine stream for decisions. Live model replies introduce another uncontrolled source; [[twin comparison]] explains the interpretation.

## Metrics

| Metric | Definition and denominator |
|---|---|
| Win rate | Wins divided by seat-games played |
| Wrong-accusation rate | Seat-games containing a wrong accusation divided by seat-games played |
| First accusation | Mean game turn among seat-games where that player accused |
| Never accused | Seat-games without an accusation divided by seat-games played |
| Own cards shown | Distinct held cards shown to any opponent, per seat-game |
| Own cards named | Suggestions naming at least one held card, per seat-game |
| Re-show rate | Previously exposed card selected, among refutations with several matching cards |

Wrong-accusation rate is not errors divided by accusations. A player that waits in most games can have a low per-game error rate despite being unreliable when it does accuse. First-accusation time omits never-accused games and should be read alongside that rate.[^metrics]

Own cards shown counts distinct cards rather than how many recipients saw each one. Re-show can mean a card shown previously to any player, while the scoring preference prioritises one already shown to this particular suggester. These related measures are not identical.

## Recorded tuned-grid arena

{{figure:arena-rates|wide|Wins and wrong accusations in the historical tuned-grid arena. Each character's denominator was sixteen or twenty seat-games.}}

{{table:arena.grid|The recorded `arena-grid-tuned-24` run: Classic board, seed 7007, 24 games cycling three to six seats, 15 September 2026. Percentages use each row's Games count.}}

Every game in this run ended in a correct accusation. Mean length was {{fact:arena.grid.turns}} game turns. Plum and Peacock had the highest recorded win rates, and neither made a wrong accusation in its own sample. That absence is a run observation, not a guarantee of future accuracy.[^record]

This table predates the [[landing rule]] adopted on 18 September. The preserved values do not silently become a current ranking when the implementation changes.

## Uncertainty

For $k$ successes in $n$ seat-games, the rate estimate is $\hat p=k/n$. The arena prints the plug-in binomial standard deviation

$$ \sqrt{\frac{\hat p(1-\hat p)}{n}}. $$

This gives a rough sampling scale under independent Bernoulli trials. It is not a confidence interval, and it reports zero at observed rates of 0 or 1, where uncertainty plainly remains with a small sample. Roster dependence, paired games and accumulated learning further limit a literal independent-trial interpretation.[^metrics]

A paired analysis can inspect which deals were lost and gained rather than comparing only two aggregate rates. More games and a separate confirmation run provide stronger evidence than repeatedly tuning against one small result.

## Model and memory records

For model-piloted seats, the arena records decisions, calls, fallbacks, departures from top options, remarks, usage and latency. Fallback rate divides by decisions with more than one allowed option, including those whose call was prevented by a budget limit. Departure rate divides by accepted model choices. Neither uses all turns as its denominator.[^metrics]

[[Method memory]] and [[logbook|narrative memory]] can accumulate during a remembered run. Fixed-state comparisons require the same starting memories, read-only, while a learning run deliberately updates them. Green also receives revealed-outcome arm feedback within an ordinary run. The seed is only part of the experimental state.


## See also

[[Belief benchmark]] · [[Dial sweeps]] · [[Twin comparison]] · [[Determinism and seeds]]

## References

{{references}}

[^arena]: {{cite:clude_training/arena.py|`run_arena`, `seat_lineup` and private random streams}}
[^metrics]: {{cite:clude_training/arena.py|`PlayerStats`, `SeatOutcome` and `binomial_std`}}
[^record]: {{cite:docs/strategy-glossary.md|Arena on the grid, tuned presets (Stage 1f, re-run)}}

{{navbox:clude}}
