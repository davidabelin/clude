---
title: Leash
short: The score cutoff governing a model-piloted character’s discretion
categories: Personality
redirects: The leash
dyk: ...that a zero [[leash]] can still leave a tied choice for the model?
---
The **leash** limits the choices available to a model-piloted character. Ordinary scored options remain available when their score is at least $(1-l)$ times the best score, where $l$ is the leash setting. At 0 only top-scoring options remain, including ties; at 1 all options in that scored menu pass the cutoff. Bluffing and accusation have additional rules.[^menu]

The preset is {{code:neutral.leash}}. The model can choose within the resulting menu and speak in its [[persona|voice]], but cannot widen the menu through conversation or [[logbook|memory]]. A malformed or disallowed reply falls back to the numerical character's own decision.

## A scored menu

{{figure:leash-band|wide|A constructed menu evaluated by the actual leash rule. At leash 0.25, the cutoff is 0.60, admitting A and B but excluding C.}}

Consider three movement scores: A at 0.80, B at 0.65 and C at 0.50. With leash 0.25, the cutoff is $0.75\times0.80=0.60$. A and B are available; C is hidden from the model's allowed choices. The setting measures a relative score gap, not a probability of ignoring the method or a distance in board squares.

At leash 0, A alone remains in this example and the model is not called. If A and B both scored 0.80, both would remain and the model could be asked to break the tie even at zero leash. If every score is zero, every option ties for best and passes the ordinary cutoff.

## How the rule works

For option $i$, let $S_i$ be its score and $S_{\max}$ the best score. The rule is

$$ S_i\geq(1-l)S_{\max}. $$

The implementation allows a small floating-point tolerance at the boundary. It sorts scored options best first, assigns letter labels and caps large menus. Thus 'all options at leash 1' refers to the generated menu, not an unbounded catalogue of routes or hypothetical questions.[^menu]

Movement uses the character's shared [[curiosity]] blend. Card-showing uses [[secrecy]] scores. Suspect and weapon menus use the character's card probabilities for candidates outside its hand. [[Temperature]] samples a headless decision; it does not set the leash cutoff.

## Bluff options

Held suspect and weapon cards have zero-score entries labelled as bluffs. They are allowed when **both leash and bluff rate are positive**, even if the ordinary score cutoff would exclude them. At zero leash they are closed, and at zero bluff rate they stay closed even with full leash.[^menu]

An accepted model reply chooses from these options rather than reproducing the headless bluff coin flip. This is why a model-piloted character's own-card naming can differ from its twin at the same [[personality dials]]. The compulsory room remains outside these two menus.

## Accusation and waiting

Let $p$ be the character's best-triple confidence score and $t$ its [[accusation threshold]]. Accusation becomes available when

$$ p\geq(1-l)t. $$

Waiting is available whenever $p<t$ **or any positive leash remains**. The implementation therefore has an early-accusation boundary but no upper confidence boundary that forces accusation at positive leash. The model can keep waiting above its headless threshold, including at a score of 1.[^menu]

For Plum's threshold {{code:preset.Plum.accuse_threshold}} and leash 0.25, accusation opens at $0.75\times0.9=0.675$. At confidence 0.70 both accusation and waiting are available; at 0.95 they are also both available. At zero leash, 0.70 forces waiting and 0.95 forces accusation. The confidence itself remains the character's product approximation, not an independently verified chance of success.

## Accepted choices and fallback

The [[LLM wrapper]] checks the returned letter against the allowed options. A backend error, refusal, timeout, invalid JSON, budget exhaustion or disallowed letter invokes the underlying headless decision. A one-option menu also skips a model call. Fallback uses the character's existing random stream at the point where its headless sampling would have occurred.[^wrapper]

Zero leash does not generally make a working model identical to the headless twin: the headless character can sample lower-scoring options at positive temperature or select held cards through its bluff rate, whereas the zero-leash menu enforces top scores and closes held-card bluffs. The tested identical-twin control is a backend that always falls back, not merely a zero leash.

## Measurement and limits

[[Twin comparison|Twin comparisons]] and [[dial sweeps|leash sweeps]] measure outcomes and departures from the top-scoring option. A higher setting creates more opportunity to depart, but does not oblige the model to use it. A departure statistic is also distinct from a model-call statistic: a model can be called to choose a tie and make no scored departure.

Historical passage loops showed another limit. When the useful move was excluded by the score cutoff, a persona or remembered instruction could not choose it. The [[landing rule]] changed the scores instead. The leash constrains discretion within the current scoring policy; it is not a proof that those scores rank actions well.


## See also

[[LLM wrapper]] · [[Personality dials]] · [[Twin comparison]] · [[Landing rule]]

## References

{{references}}

[^menu]: {{cite:clude_llm/menu.py|`within_leash`, `suggestion_menu`, `accusation_menu` and `_build`}}
[^wrapper]: {{cite:clude_llm/player.py|decision validation and fallback}}

{{navbox:clude}}
