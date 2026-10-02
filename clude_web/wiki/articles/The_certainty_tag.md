---
title: The certainty tag
short: A public confidence colour on a logarithmic scale
categories: The app
redirects: Certainty colour
dyk: ...that halfway on [[the certainty tag]] is about one envelope in eighteen, rather than a one-in-two chance?
---
**The certainty tag** is the colour behind each seat's name in [[clude]]. It runs from blue through white to red, representing a single measure of confidence in the seat's best envelope guess. Everyone at a live table can see the tags. They are an experimental indicator of confidence, rather than proof that a player knows the answer or an estimate of its chance of winning.[^tag]

## Reading the colour

Blue represents a uniform guess over all {{code:certainty.triples}} possible envelopes. White is halfway along the information scale, and red represents certainty. Halfway does not mean a one-in-two chance of being right: it corresponds to about one triple in {{code:certainty.half.one_in}}. The scale transforms a confidence estimate logarithmically, as explained in [[entropy and bits]]. It does not calculate the entropy of the full belief distribution.

A character supplies its confidence in the leading suspect, weapon and room. The shared calculation multiplies those three category confidences. For Peacock it uses her lower-bound confidence; a person or [[floor player]] is read through the floor's uniform distribution over remaining candidates. A human tag therefore describes the automatic floor, rather than that person's private judgement.[^code]

## Calculation

Let $p$ be the product of the three leading category confidences, and $N$ the number of possible envelopes before any evidence. Here $N={{code:certainty.triples}}$. The tag is

$$ c=\operatorname{clip}_{[0,1]}\left(\frac{\log(Np)}{\log N}\right). $$

The function clips the result to the range from zero to one. With $p=1/N$ it gives zero; with $p=1$ it gives one. At $c=1/2$, $p=1/\sqrt N$. Taking logs turns multiplicative changes in confidence into equal steps in the tag.

This $p$ uses the common approximation described in [[belief]]. It is not generally an exact joint envelope probability, even when each individual card estimate is exact. Hidden-card constraints create dependencies between categories. The tag also omits whether the chosen cards are the true ones: a wrong leading candidate can receive a high-confidence colour.

## Public information and reconstructed views

The tag intentionally reveals a little about every seat's progress during play, without naming its candidate cards. It is visible to players as well as spectators. Fresh numerical readings supply the display without consuming the playing agents' random streams; readings are cached between changes in evidence.

[[Replay]] derives its tags from the reconstructed trace. The trace does not restore starting method memory or reproduce Green's learning-hook updates. White rebuilds her current-game chain from the recorded suggestions rather than through that hook. The historical decision to display the tags publicly superseded the earlier policy that a seated person saw no indication of other seats' reasoning.


## See also

[[Belief]] · [[Entropy and bits]] · [[The table]] · [[Replay]]

## References

{{references}}

[^tag]: {{cite:docs/web.md|A table}}
[^code]: {{cite:clude_agents/character.py|`certainty`}}

{{navbox:clude}}
