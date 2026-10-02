---
title: Looks
short: Case-file light, Gaslight dark and Developer presentation styles
categories: The app
redirects: Styles, Case-file light, Gaslight dark, Developer look
---
**Looks** are [[clude]]'s three presentation styles: **Case-file light**, **Gaslight dark** and **Developer**. An account's choice applies across the app and Wikiclude. They share the game and article content, with one deliberate content difference: Developer displays model costs that the other looks keep out of the playing interface.[^looks]

## The three choices

| Look | Theme and presentation |
|---|---|
| Case-file light | Fixed light theme; the default for new accounts and signed-out wiki pages |
| Gaslight dark | Fixed dark theme; the same stage and rail layout as Case-file light |
| Developer | Earlier panel layout; follows the device's light or dark preference and displays cost details |

Case-file and Gaslight share the engraved stylesheet and its locally served typefaces. Their table has a board and decision stage with a rail for Talk, Record, Hand and Notes. Developer preserves the earlier stylesheet and screen structure. The [[Classic board|board geometry]] comes from the engine for every look; the styles dress its shapes rather than define another map.

## Changing the look

A signed-in person can choose a look in the header, including during a game. The choice is stored on the account. Changing it does not redeal cards, change a legal action or alter a character's method. A signed-out visitor to Wikiclude receives Case-file light.

Earlier account values remain readable: Legacy maps to Developer, and Engraved maps to Gaslight dark. Engraved previously followed the device preference; its automatic choice was retired when the fixed light and dark looks were named.[^styles]

## Accessibility and sound

The layout adapts to a phone width, and wiki tables and long equations can scroll within their own panels. Reduced-motion preferences and the app's motion control limit transitions. Colour supports distinctions also expressed in labels, numbers and proof states.

Sound effects are a separate optional control, initially off for a viewer. They indicate game events rather than change the rules, and the app has no background music. Choosing a dark look does not turn sound on.[^sound]


## See also

[[The table]] · [[Replay]] · [[What a game costs]]

## References

{{references}}

[^looks]: {{cite:docs/web.md|Looks}}
[^styles]: {{cite:clude_web/styles.py|`STYLES`, `DEFAULT_STYLE` and `RENAMED`}}
[^sound]: {{cite:docs/web.md|Sound}}

{{navbox:clude}}
