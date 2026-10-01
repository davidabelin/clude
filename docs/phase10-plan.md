# Phase 10 Plan: the shippable look \-- "engraved, not brass-plated"

Status: **proposed 2026-09-20; David's answers recorded 2026-09-21; 10a drawn 2026-09-27 and revised after his review on 2026-09-28; 10b-10c built 2026-09-28; 10d-10g built 2026-09-29, and David's fourth round the same day (section 17).** David's brief is section 3; D1-D20 are in section 13, where the second round (D7-D14) reverses D3 and D6 and adds sub-phases 10h and 10i, the third (D15-D16, 2026-09-29) makes the two themes choosable by name, and the fourth (D17-D20, the same afternoon) cuts the looks to three, splits Stored games into two folders, adds the footer, and turns 10i into Wikiclude. D5 is settled: candidate E. Written in the shape of the other phase plans: context, what the code dictates, design, sub-phases, files, decisions, out of scope, and an "as implemented" section once the work lands.

## 1\. Context

Phases 8.1 and 8.2 put the screens up deliberately plain: the colour system is already a token layer (`static/style.css`, every colour a variable, light and dark), `board_svg.py` sets no colour at all, and `scripts/clude_shots.py` plus `tests/test_browser.py` can look at the result in both themes at both widths. Phase 10 spends that groundwork: typography, ornament, the decorated board and its logo, motion, the six-seat layouts, the case-file styling, and sound effects in 10g. No music.

Phase 10 also does the first half of the scrub `CLAUDE.md` wants before any public release. Every step away from the Classic game's own art and toward a house style is a step out of the IP thicket \-- the names stay for now, the look stops being Hasbro's.

Three screens carry the whole app: **the table** (play), **the replay** (post-game), **the lobby**. Watch shares the table's parts.

## 2\. What the code dictates

**Seat setup baseline (2026-09-21).** Keep the lobby options in this
order: **empty**, **open**, **floorbot**, **me (signed-in name)**,
**X (LLM)**, **X (headless)**. X is the seat's named character. LLM seats
use Claude for leashed decisions and chat; headless seats use only the
numerical method and never chat. New Play and Watch tables remember by
default, with a checkbox to opt out. Remembering LLM seats expose a saved
memory-depth dial (0 = condensed head, 0.5 = summaries, 1 = full entries);
method memory belongs to Mustard, White and Green in either mode.
LLM seats are visible but disabled without a service key.

Read off the modules, not guessed. Each of these is a fence the design has to live inside.

- **No build step, no framework.** One stylesheet, a few vanilla JS files (`docs/phase8.1-plan.md` 3.1). So: web fonts are `@font-face` files served from `static/fonts/`, not a CDN link; there is no preprocessor, so the token layer is CSS custom properties and nothing else; there is no component library, so every "component" below is a class name and a block of CSS.  
- **`board_svg.py` sets no colour, and a test fails on any class with no rule.** Ornament may therefore add *shapes* to the generator, never paint. The trick that keeps this true for patterned floors is in 8.3.  
- **The payload is in the page.** The table and replay screens embed their whole state as JSON in a `<script>` block. **Anything hidden with CSS is still in view-source**, so the secrecy rule in 3.2 is a change to `view_payload`, not a stylesheet rule.  
- **Nothing runs between requests.** The page polls every 2 s while busy, 5 s while waiting on a person, 10 s on the viewer's own turn, and fires one unit of bot work at a time, no sooner than 1.5 s after the last; off-turn chat is staggered 2-8 s. **That beat is the animation budget**: a transition longer than about 400 ms will still be running when the next poll lands, and a "thinking" state is an inference from the poll, never a push.  
- **A transition on `cx`/`cy` lies to a screenshot** (8.1 step 4 amended). Motion needs an off switch that `clude_shots.py` and `tests/test_browser.py` set, or Phase 10 reintroduces the bug that cost a day.  
- **`RemarkEvent(turn, seat, text, about)` is already distinct** from every action event, and `about` is `"chat"` or `"reaction"`. The talk/record split in 3.3 is therefore a filter over the event list and costs the driver nothing.  
- **`describe_for(event, ..., viewer)` already enforces the reveal rule**: a shown card is named only to the suggester and the refuter. The design must not route around it \-- in particular the record panel renders the per-viewer line, never the omniscient one.  
- **Six seats is the hard case.** Three fit a phone comfortably; the seat rail, the balloons and the replay's blocks all have to survive six.

## 3\. The brief, as three rules

David, 2026-09-20. Everything below is downstream of these.

### 3.1 The loudest thing is the biggest thing

> "What's most *interesting* is what's most *visible* at all times."

This is not a layout, it is a **rule that chooses the layout**, moment by moment. The screen has one **stage** and one **rail**; what holds the stage is whatever currently matters most, and everything else collapses into the rail with a badge.

The ladder, highest first. The server computes `focus` in `view_payload`, so it is testable in plain Python; the client only applies the beat's decay timer.

| Rank | `focus` | When | Stage holds |
| :---- | :---- | :---- | :---- |
| 1 | `show` | A `card_to_show` request is the viewer's | The suggestion, spelled out, and one button per candidate card |
| 2 | `end` | The game is over, or an accusation just resolved | The envelope, the winner, the impact frame |
| 3 | `move` | A movement request is the viewer's | The board, large, destinations lit; choices docked beneath |
| 4 | `decide` | A suggestion or accusation request is the viewer's | The form; the board shrinks to a strip |
| 5 | `beat` | Within 2.2 s of a suggestion or refutation | The narration caption, set large, over a dimmed board |
| 6 | `talk` | A chat line arrived in the last 6 s and nothing above applies | The last two balloons; board behind them |
| 7 | `board` | Otherwise | The board, with the seat now thinking marked |

Two things make this work rather than thrash. **The stage never changes under the viewer's hand**: while a decision of theirs is pending, ranks 5-7 are locked out entirely, so a chat line cannot steal the buttons you are reaching for. And **the rail always shows what it is holding back** \-- a count on Talk, a dot on Record, so demoting something is never the same as hiding it.

Implementation: `data-focus` on `main.table`, one `grid-template-areas` per value, one `focusFor(payload, now)` in `table.js` that does nothing but read `payload.focus` and decay the beat.

### 3.2 Play is blind; the replay is omniscient

During a normal game, a normal player is told **nothing about what any other seat knows or believes**. The compact bars that 8.2 put on the table screen come off it, as confirmed in D2. For these games, they are the replay's payoff, where the game is over and the truth is already on screen.

Because the payload is in the page, this is a server change: `view_payload` stops emitting `readings` for a table with a human seat, and a test asserts the key is absent \-- not merely unrendered.

| A player sees, during play | Only in the replay |
| :---- | :---- |
| Each seat's token, colour and character name | Its method (Bayes, Dempster-Shafer, ...) |
| Human or character; a human's login name | Cards it has placed |
| Whose turn; in, out, or on autopilot | Its confidence per category |
| "Mustard is thinking", "Peacock is writing" | Its belief bars and the red truth mark |
| How many cards each seat holds (public from the deal) | What any other seat has proven |
| Their own hand, their own notes, their own log | The card shown at any refutation they were not party to |
| **Each seat's certainty tag** (9h, David's one exception: the poker face, shown to everyone) | |
| **Each model seat's share of the table's spend** (9g) | |

**Watch keeps the bars** (D1, confirmed). Watch is characters only \-- there is nobody at the table to gain from the information, and the six methods racing each other is the entire point of the screen. The bars remain in Watch and the replay; they are removed from normal play.

**A character's method is hidden during normal play**, named in the replay, and visible on the lobby form to whoever sets the table up (D3, confirmed).

*Amended 2026-09-27 (10a):* the two rows in bold were added to the left column for what 9g and 9h put on the seat rail after this section was written; the artboards draw them and nothing else about another seat.

### 3.3 Talk and record are two panels, never one

They are two different kinds of sentence and they get two different typesettings.

|  | The Record (narration) | Table talk (chat) |
| :---- | :---- | :---- |
| Content | Every non-`RemarkEvent`, as prose from this seat's view | Every `RemarkEvent`: human lines, on-turn remarks, off-turn reactions |
| Voice | Third person, past, terse. "Mustard crossed to the Hall and put it to the room: White, the Rope, the Lounge. Green disproved it." | First person, present, theirs |
| Type | Case-file: `--font-gauge` turn numbers in the margin, `--font-ui` body, a hairline rule between turns | Balloons: `--font-ui`, speaker's colour on the tail, yours right-aligned |
| Scroll | Anchored to the newest, jumps to top on a scrubber move | Anchored to the newest |
| Input | None | The 240-character box, only for a seated human |

The cross-reference matters: a chat line carries the turn it was said on, and a record beat that provoked talk gets a small speech pip you can tap to jump. That is the only coupling between them.

## 4\. Direction: engraved, not brass-plated

The failure mode of steampunk is decoration: cogs that turn nothing, sepia everything, brass gradients, a goggles-and-rivets font. The failure mode of manga styling is costume: speed lines on a settings screen. Both are cheap and both read as a theme, not a product.

What we take instead:

**From steampunk, the materials and the mechanisms.** Ink printed on laid paper. Brass as a hairline and a fitting \-- door thresholds, the scrubber's track, the rivets at a plate's corners \-- never as a fill. Instruments rather than widgets: the scrubber is machined, counters are engraved, numbers are set in a monospace that reads as a gauge face. Victorian job printing for the display face: high contrast, tight, a didone.

**From graphic novels and manga, the grammar.** The stage is a panel and transitions between focus states are panel cuts, not fades. Screentone does the work that gradients would: a pale belief is a dot tone, not an opacity. Heavy ink rules; solid offset shadows, never blur. The narration caption is a caption box. Speech is a balloon with a real tail. One impact frame in the whole app, spent on the accusation.

**Refused, explicitly:** gears as ornament anywhere; a brass gradient on any surface larger than a 2 px rule; sepia photographs; a display face on body text; cog spinners; speed lines outside the accusation; drop shadows with blur; more than four typefaces. D4 replaces the original three-face limit with separate wordmark and caption faces alongside the UI and gauge faces.

The one-line test for a new element: *would this look at home printed on paper in 1898, or drawn in ink in 1988?* If it only looks at home in a 2020s web app, it is wrong.

## 5\. Design tokens

All of this replaces the `:root` block in `static/style.css`. Names already in use keep their names, so nothing downstream moves.

### 5.1 Colour \-- light, "the case file"

Use these values for the light theme when a light preference is stated. Gaslight dark is the default when no preference is stated (D6).

| Token | Value | Usage |
| :---- | :---- | :---- |
| `--page` | `#E9E2D3` | The paper behind everything |
| `--panel` | `#F5F0E4` | Panels, the stage |
| `--panel-sunk` | `#DED6C4` | Wells: the chat box, the notepad, the log |
| `--edge` | `#C3B7A0` | Hairlines |
| `--edge-strong` | `#6B5D49` | The ink rule around a panel |
| `--ink` | `#14110D` | Body |
| `--ink-soft` | `#5A4F40` | Secondary |
| `--ink-faint` | `#8A7D6A` | Disabled, placeholders, tone |
| `--brass` | `#A97B2C` | Fittings, rules, the active scrubber |
| `--brass-bright` | `#C79A45` | Hover and focus on a fitting |
| `--brass-dim` | `#7A5A21` | Pressed |
| `--accent` | `#7A2230` | The red thread: your turn, the truth mark, the wordmark |
| `--accent-ink` | `#F5F0E4` | On accent |
| `--warn` | `#9B2226` | Accusation, errors |
| `--proof` | `#14110D` | A proven card: solid ink |
| `--tone` | `#8A7D6A` | Screentone dots |
| `--tone-size` | `3px` | Screentone pitch |

### 5.2 Colour \-- dark, "gaslight"

**Default theme (D6): gaslight dark.** Use these values for a dark preference and when the device states no preference. Keep the light theme in 5.1 available for a light preference.

| Token | Value |
| :---- | :---- |
| `--page` | `#121013` |
| `--panel` | `#1B181C` |
| `--panel-sunk` | `#0D0B0E` |
| `--edge` | `#332E33` |
| `--edge-strong` | `#9A9186` |
| `--ink` | `#EDE6D8` |
| `--ink-soft` | `#A9A090` |
| `--ink-faint` | `#7A7263` |
| `--brass` | `#D6A75A` (already the board's door) |
| `--brass-bright` | `#F0C67E` |
| `--brass-dim` | `#8A6A2E` |
| `--accent` | `#C2596A` |
| `--warn` | `#F08A8A` |
| `--proof` | `#EDE6D8` |
| `--tone` | `#7A7263` |

**The six suspect colours do not change.** They are tested, they are on the board, and they are the app's only reliable identity channel. Each gains `--suspect-<name>-ink`, the colour text takes when sitting on that token, so White's problem (a near-white pip on a near-white panel) cannot recur.

### 5.3 Type

Four faces, self-hosted as woff2 in `static/fonts/`, subset to Latin. D4 selects Bodoni Moda for the wordmark and Playfair Display for captions; Inter and IBM Plex Mono retain their UI and gauge roles.

| Token | Face | Used for |
| :---- | :---- | :---- |
| `--font-wordmark` | Bodoni Moda | Wordmark |
| `--font-display` | Playfair Display | Screen titles, the narration caption, the accusation, room labels on the board |
| `--font-ui` | Inter | Everything the hand touches: buttons, forms, balloons, the record's body |
| `--font-gauge` | IBM Plex Mono | Numbers, seeds, turn numbers, counters, card counts. `font-variant-numeric: tabular-nums` always |

Scale, mobile first, 16 px base. Wide screens multiply `beat`, `title` and `hero` by 1.2 and nothing else.

| Token | Size / line | Face |
| :---- | :---- | :---- |
| `--type-gauge` | 0.72rem / 1.2 | gauge |
| `--type-sm` | 0.85rem / 1.4 | ui |
| `--type-body` | 1rem / 1.5 | ui |
| `--type-beat` | 1.15rem / 1.35, italic | display |
| `--type-title` | 1.4rem / 1.2 | display |
| `--type-hero` | 2rem / 1.05 | display |

### 5.4 Space, edge, elevation, motion

| Token | Value | Usage |
| :---- | :---- | :---- |
| `--space-1` .. `--space-7` | 4, 8, 12, 16, 24, 32, 48 px | The only spacings permitted |
| `--gap` | `var(--space-4)` | Kept: existing rules read it |
| `--radius` | `2px` | Machined, not rounded. Replaces today's 6px |
| `--radius-chip` | `999px` | Card chips and pips only |
| `--rule` | `1px solid var(--edge)` | Hairline |
| `--rule-ink` | `2px solid var(--edge-strong)` | A panel's edge |
| `--lift` | `2px 2px 0 var(--edge-strong)` | The printed shadow. **No blur anywhere** |
| `--dur-tick` | `90ms` | State on a control |
| `--dur-cut` | `140ms` | A panel cut |
| `--dur-move` | `220ms` | A token crossing the board |
| `--dur-impact` | `420ms` | The accusation, once per game |
| `--ease-snap` | `cubic-bezier(.2,.8,.2,1)` | Controls |
| `--ease-panel` | `cubic-bezier(.4,0,.2,1)` | Panels and tokens |

**The motion kill switch.** `body[data-motion="off"]` sets every duration token to `0s`. `clude_shots.py` and `tests/test_browser.py` set it; so does `@media (prefers-reduced-motion: reduce)`. No element may hard-code a duration \-- a test greps the stylesheet for `ms` outside the `:root` block.

## 6\. Layout

Mobile first, `min-width` queries from here on. Two breakpoints beyond the phone.

| Breakpoint | Layout |
| :---- | :---- |
| Phone, \< 36rem (target 390 x 844\) | One column. Stage on top, rail beneath as a tab strip: Talk / Record / Hand / Notes. The board fills the width, capped at 58vh so the rail is never pushed off |
| Tablet, 36-62rem | Two columns, 5:4. Stage left and sticky; the rail becomes a stack of open panels on the right; Talk and Record both visible |
| Wide, \>= 62rem | Three columns, 6:4:3. Board, then Record and the decision, then Talk full height. Nothing collapses; `data-focus` changes emphasis (a border, a scale of 1.02) rather than the grid |

The phone is the priority. The rules that follow from it:

- **The thumb owns the bottom third.** Every choice button lives there. Minimum target 44 x 44 px, minimum 8 px apart.  
- **Never two scrolls in one column.** The stage does not scroll; the active rail panel does.  
- **The board is never below the fold when `focus` is `board` or `move`.**  
- Safe areas: `viewport-fit=cover` plus `env(safe-area-inset-*)` padding on `:root`, and the tab strip adds the bottom inset to its own padding.

## 7\. Components

Classes extend what exists; nothing already named is renamed.

| Component | Class | Variants | States | Notes |
| :---- | :---- | :---- | :---- | :---- |
| Stage | `.stage` | per `data-focus` | \-- | One grid area; contents swapped by focus |
| Narration caption | `.beat` | `suggestion`, `refutation`, `accusation`, `over` | entering, resting | Caption box: ink rule, `--type-beat`, the speaker's colour as a left rule |
| Board | `.board` | `play`, `replay`, `watch` | idle, lit (destinations), dimmed (behind a beat) | Section 8 |
| Decision | `.decision` | `move`, `suggest`, `accuse`, `show` | idle, submitting, refused | One form at a time, from `pending`. `accuse` keeps its confirm |
| Choice button | `.choice` | `default`, `passage`, `stay`, `warn` | default, hover, active, focus-visible, disabled, busy | Brass hairline; `--lift` printed shadow; pressed removes the lift and offsets 2 px |
| Hand | `.hand` / `.card-chip` | \-- | default, played-out | Chips, `--radius-chip`; a card you have shown is ticked, not removed |
| Notes | `.notepad` | \-- | empty, partial, solved row | The floor from your seat. Proven holder \= solid ink; possible \= screentone dot |
| Seat rail | `.seats` / `.seat.compact` | `character`, `human`, `me` | waiting, acting, thinking, out, autopilot | **Public facts only** during play (3.2) |
| Talk | `.talk` / `.balloon` | `theirs`, `mine`, `reaction` | arriving, settled | Tail in the speaker's colour; 240-char cap enforced server-side |
| Talk input | `.say` | \-- | idle, focused, over-length, sending, refused | Counter appears past 200 characters |
| Record | `.record` / `.turn-lines` | \-- | empty, live, ended | Turn number in the margin, `--font-gauge` |
| Status | `.status` | `yours`, `waiting`, `warn` | \-- | Already `aria-live="polite"`; keep it |
| Scrubber | `.scrubber` | \-- | idle, dragging, at-start, at-end | Replay only. Machined track in brass, the thumb an engraved plate |
| Seat block | `.seat` \+ `.gauge` | \-- | \-- | **Replay and Watch only** |
| Plate | `.plate` | `small`, `hero` | \-- | The riveted frame: 4 rivets, `--rule-ink`, used for the wordmark and the game-over card |

## 8\. The board, decorated

The generator gains shapes and keeps its promise not to paint.

- **Patterned floors without colour in the generator.** `board_svg` emits a `<defs>` block of `<pattern>` elements whose children carry classes and no fill. The stylesheet does both halves: it picks the pattern per room (`.board-room[data-room="Library"] rect { fill: url(#tone-boards); }`) and colours the pattern's children. CSS can reference a paint server by id inside the same inline SVG, so the existing "every class has a rule" test stays green and the decorated board is still a stylesheet change.  
- **Four floor patterns, reused across nine rooms**: parquet (Library, Study, Hall), tile (Kitchen, Conservatory), boards (Billiard, Dining), rug (Lounge, Ballroom). Pitch 6-8 px so it survives a phone.  
- **Walls** become a double rule: `--rule-ink` outside, a 1 px brass hairline inside, which is what makes it read engraved rather than drawn.  
- **Doors** become a threshold plate: the brass bar that exists now, plus a rivet at each end.  
- **The cellar** carries the logo in place of today's wordmark text.  
- **Tokens** gain a 1 px ink ring and the character's initial in `--suspect-*-ink`, so the six are distinguishable without colour. Movement animates `cx`/`cy` at `--dur-move`, and only under `body:not([data-motion="off"])`.  
- **Lit destinations** are an overlay `<g class="board-lit">` of squares at server-side coordinates \-- the geometry stays in one place, as it does now. Lit squares pulse once on arrival, then rest.  
- **Six seats** never stack: `token_points` already fans a room, and it stays the only thing that decides where a token goes.

## 9\. Logo

**Direction remains open (D5).** David wants to see the three alternates in 10a before choosing. The plate wordmark and keyhole-c below are the proposed direction, pending that review.

**Proposed lead: the plate wordmark.** `clude` set lowercase in Bodoni Moda (`--font-wordmark`, D4), letter-spaced 0.08em, on a brass plate with four rivets, sitting in the cellar. It scales from the board's middle down to the nav bar's `.mark` unchanged, which is the whole reason to pick a wordmark over a picture.

**Proposed mark, for the favicon and the phone icon: the keyhole-c.** A Victorian escutcheon whose keyway is a lowercase `c`. Reads at 16 px, says "mystery" without a magnifying glass, and is nobody's trade dress.

Both drawn as SVG, both uncoloured, both classed \-- the mark inherits the theme like everything else. Three alternates come as artboards in 10a.

## 10\. Content, edge cases and empty states

| Case | Behaviour |
| :---- | :---- |
| Chat line | Server cap 240 characters (already), counter past 200, hard stop at 240, control characters stripped |
| Long card names | `Lead_Pipe` renders "Lead Pipe" everywhere. No truncation anywhere in a decision: buttons wrap to two lines rather than ellipsis |
| Room labels at six seats | The label sits above the crowd (`label_anchor`, already) and keeps its halo |
| Empty: no talk yet | "Nobody has said anything yet." in `--ink-faint`; the input stays live |
| Empty: record before the deal | The roster and "Waiting to deal." |
| Empty: lobby, no games | The wordmark plate and one "Deal a game" button |
| Loading: first paint | Board skeleton as ruled cells with no tokens, plus the status line. No spinner |
| Loading: bot thinking | The seat's rail entry gets an animated three-dot; the status line names it |
| Loading: cold rebuild | "Restoring the table" with the plate, up to 95 s; the poll keeps its cadence |
| Error: refused answer | The decision shakes 2 px once, `.error` shows the server's message, buttons re-enable |
| Error: session expired | The client already reloads on a redirect; the reload lands on login |
| Error: budget spent | "Plum's budget is spent \-- he is playing on his own from here." in the record, once |
| Slow connection | The poll backs off as it does now; nothing in the design depends on a poll arriving on time |
| International text | Nothing is sized to an English string; every button wraps. Not translated in Phase 10, but no layout blocks it |

## 11\. Motion and sound

| Element | Trigger | Animation | Duration | Easing |
| :---- | :---- | :---- | :---- | :---- |
| Stage | `data-focus` changes | Panel cut: the outgoing clips away left, the incoming clips in from right. No crossfade | `--dur-cut` | `--ease-panel` |
| Token | Position changes | `cx`/`cy` interpolate | `--dur-move` | `--ease-panel` |
| Lit square | Becomes legal | One pulse of the brass hairline, then rest | `--dur-tick` x2 | `--ease-snap` |
| Balloon | Arrives | Rises 6 px and inks in | `--dur-cut` | `--ease-snap` |
| Caption | A beat starts | Snaps in at 1.0 scale from 0.98, holds 2.2 s | `--dur-cut` | `--ease-snap` |
| Choice button | Press | Lift removed, offset 2 px | `--dur-tick` | `--ease-snap` |
| Accusation | Resolved | The one impact frame: the board flashes to ink for 80 ms, the caption lands in `--type-hero` | `--dur-impact` | `--ease-panel` |
| Scrubber thumb | Drag | None (follows the finger); the board follows at `--dur-move` | \-- | \-- |
| Card chip | Shown to someone | Ticks and dims; it does not leave the hand | `--dur-tick` | `--ease-snap` |

Everything above is `0s` under `[data-motion="off"]` and reduced motion, except the accusation, which becomes a plain 80 ms flash to opacity rather than nothing \-- the event still has to register.

### 11.1 Sound effects (10g)

Short, restrained effects support the table's actions: a turn-ready cue, a movement or card-action tick, a refutation cue, and an accusation or game-over accent. Use the same cues in Watch and during replay playback. **No music.** The sound should fit the engraved, mechanical direction without becoming a continuous background layer.

- **Player control:** sound starts muted until enabled by the user; provide an accessible sound toggle and volume control, and remember the preference. If audio is unavailable or blocked, play continues normally.
- **No extra information:** cues follow only events already visible to that viewer. They never reveal a hidden card, another seat's beliefs, or a character's method.
- **One cue per event:** repeated polls must not replay an effect. Initial load, reload, and replay scrubbing stay silent; playback cues resume only for newly played events. Keep rapid events from producing overlapping noise.
- **Visual parity:** every audible cue has an existing visible counterpart. Sound is optional and never the only way to notice a turn, action, or result.
- **Delivery and checks:** self-host the effects in `static/sounds/` and share playback logic in `static/sound.js`. Automated browser and screenshot runs stay muted. Check cue timing by listening in play, Watch, and replay, alongside automated checks for mute, preference persistence, event deduplication, and viewer visibility.

## 12\. Accessibility

- **Focus order on the table**: status, decision (its buttons in the engine's own order), talk input, rail tabs, hand, notes, seat rail, nav. The board is one element in the order, not 828\.  
- **The board** is `role="img"` with a live `aria-label` that names each token's room \-- "Mustard in the Hall, Plum in the Study, you in the corridor" \-- regenerated per frame. The lit destinations are duplicated as the choice buttons, which is why the board itself need not be keyboard-walkable.  
- **Live regions**: `.status` stays `aria-live="polite"`; the newest record beat is `aria-live="polite"`; incoming chat is `aria-live="polite"` and never `assertive`, so six talking bots cannot drown out the status. The accusation is the one `assertive`.  
- **Keyboard**: the scrubber's arrow keys, Home and End already work and stay. Add `Esc` to dismiss a beat early and `Enter` to send a chat line.  
- **Colour is never the only channel.** Every token carries its initial, every proven cell carries a mark as well as a fill, every seat's state is a word as well as a colour. White's invisible pip is the precedent.  
- **Contrast**: 4.5:1 for body, 3:1 for the hairlines that carry meaning, in both themes. A check script over the token table, run in 10a, not a per-element audit.  
- Targets 44 x 44 px minimum, 8 px apart.

## 13\. David's decisions

Answers recorded 2026-09-21. D1-D4 and D6 were settled then; D5 waited for the alternates and was settled on 2026-09-29 (E).

- **D1. Watch keeps the bars?** My proposal: yes \-- nobody is at the table, and the six methods racing is what Watch is for. Play loses them, the replay keeps them.

  **Answer:** Yes, of course.

- **D2. Did I read 3.2 right?** Your sentence was "no information about other players should be shown (as it is the way it stands now)". I have read that as *the seat bars now on the table screen must come off*. If you meant the opposite \-- that today's screen is already correct \-- say so and section 3.2 shrinks to a test that keeps it correct.

  **Answer:** You read me correctly. I want the change.

- **D3. Is a character's method public during play?** It is a real tell: knowing Scarlett accuses early is worth something. My proposal: hidden during play, named in the replay, and visible on the lobby form to whoever sets the table up.

  **Answer:** Proceed as proposed. *Reversed for the table screen on 2026-09-28 (D8): every agent seat's one-liner is shown.*

- **D4. Display face**: Bodoni Moda or Playfair Display. Bodoni is sharper and colder, Playfair warmer and more legible small. I lean Bodoni for the wordmark and Playfair for captions if we can afford both; if three faces is the cap, Playfair does both jobs.

  **Answer:** Bodoni for the wordmark and Playfair for captions.

- **D5. Logo**: is the plate wordmark plus the keyhole-c the direction, or do you want the three alternates drawn first?

  **Answer:** Unanswered. Let me see the alternates first. *Narrowed to E or F on 2026-09-28 (D11); **E** on 2026-09-29, the cartouche with the keyhole-? mark, built in 10f.*

- **D6. Light or dark as the default** when a device states no preference. Case-file light is the better first impression; gaslight dark is the better game.

  **Answer:** Gaslight dark is default. *Reversed on 2026-09-28 (D10): case-file light is the default, dark on a device's preference.*

### Second round (2026-09-28), after David reviewed the 10a artboards

D3 and D6 are **reversed** by D8 and D10 below; D5 is narrowed by D11.

- **D7. Go-live.** Engraved appears in the Look picker after 10b, marked beta; it becomes every account's default after 10e. Legacy stays fully functional and selectable from here on (David's first point).
- **D8. Method one-liners return to the table.** Every agent seat, headless or LLM, shows its method under its name on the seat rail, in both looks (`replay_data.seat_method`); a person and the floor bot show none. Reverses D3 for the table screen; the lobby form and the replay already named them.
- **D9. No cost bar in the Phase 10 look.** Only the per-seat cost bar is hidden under Engraved; the table's model-spend line and the lobby and run Cost columns stay in both looks, and Legacy keeps the bar.
- **D10. Case-file light is the default**; gaslight dark follows a device's dark preference; one Look entry, nothing to set. Reverses D6: "it makes a better first impression".
- **D11. Logo.** A "?" in or around a keyhole, a c optional, in the cartouche style: candidates A-C dropped, E (the cartouche wordmark with a keyhole-? mark) and F (the same, the c as the question mark's dot) drawn beside D. David picks E or F; 10f builds it.
- **D12. Contact and privacy.** The contact page links the repo's GitHub issues. The privacy page states what is kept (accounts as name and hash; game records, chat lines and costs, indefinitely; table talk and game state sent to Anthropic when a model seat plays; hosted on Google Cloud us-central1; a session cookie only, no analytics; fonts self-hosted from 10b) and that `users remove` deletes an account on request. Both public, outside the login gate; drafted in 10h, shipped in Phase 11.
- **D13. Help before 1.0.0.** Two new sub-phases: **10h the help layer** (a Help link in the header bar; tooltips on every control, the notepad, the certainty tag and the seat rail; a first-login welcome card; a "How to play" page; the privacy and contact drafts) and **10i the two explainers** ("How the characters think" at high-school level, for high-schoolers and octogenarians alike; "The methods" as a Wikipedia featured article for the nerds, built from `docs/strategy-glossary.md` and the six modules with the measured numbers).
- **D14. Sound (10g) stays before 1.0.0.**

### Third round (2026-09-29), before 10d

- **D5 settled: E**, the cartouche wordmark under the keyhole with a "?" keyway.
- **D15. The two themes are choosable by name.** The Look picker offers "Case file light" and "Gaslight dark" beside Engraved as the device has it, and Legacy. Amends D10, which had one Engraved entry and nothing to set; D10's default (light, dark on a device's preference) is the automatic entry's behaviour and still every unchosen account's look.
- **D16. Two cosmetic points in the red thread** (the colour of the wordmark and Accuse): the time-out clock's seconds, bright red for the last ten; and the Notes panel's category headings, Suspects, Weapons and Rooms.

### Fourth round (2026-09-29), after 10d-10g

- **D17. Three looks.** "Engraved (auto)" and "Gaslight dark" could not be told apart on a dark device, so they are one, called Gaslight dark. Legacy is renamed **Developer**, and will differ in content as well as style (a game's cost is shown only there). The default is **Case-file light**, with the hyphen. So the Look picker offers Case-file light, Gaslight dark, Developer. Amends D7, D10 and D15.
- **D18. Stored games in two folders.** The `web` run is shown as **practice**; every other run (arenas, sweeps, ladders, fixtures) goes under **development**. Below them, the table of games as a run shows it now, with the columns Game / Seats / Winner / Turns / Suggestions / Wall time / Cost: wall time new, blank where it was not recorded; Cost only in the Developer look.
- **D19. A header and footer** with links to privacy, contact and the wiki. A wooden remake of `static/questionmark.png`, lit the same way with the same push-button feel, links to the wiki pages -- on trial there, not *the* logo. `static/copyleft.svg` marks everything "2026 AIX Laboratories".
- **D20. Wikiclude**, not started ("be ready"): an interlinked set of Wikipedia-style pages built mostly from the documentation we already have -- the LLM personalities, the ML and heuristic methods, everything in the docs, and later the ML classwork archive in the AIX repo. One article serves both audiences 10i was to split between (the high-schoolers and grandparents, the senior engineers and scientists). Replaces D13's two explainers.

### Fifth round (2026-10-01), after playing the fourth round live

- **D21. Pass up top.** The accusation's Pass and the suggestion's "No suggestion" also sit in the status line above the board, so neither needs a scroll; the decision panel keeps its own, and the Accuse panel stays where it is.
- **D22. One narration line, above the board.** Narration was in three places on a phone (the status line, a caption laid over the board, the Record). It is now in two: a line above the board and the Record. The caption over the board (the beat) goes.
- **D23. Dice narrated, never recorded.** "You rolled a six" / "Mustard rolled a two" in the narration line; not in the Record, not in the replay, not over MCP.
- **D24. Costs in Developer only**, everywhere: the table's spend line and seat bars too, and the chat seat's `cost` line follows its account's look.
- **D25. An MCP logout.**
- **D26. Doors drawn as a floor plan draws them**, a leaf and its swing, in the red thread; and **every room its own floor**, nine patterns on nine pale tints.
- **D27. Showing a card has 30 s at most**, at any table.
- **D28. The board's size on a phone** fixed where it drew small inside its pane.
- To discuss, not decided: narrating the floor's reasoning behind changes to Your notes.

## 14\. Sub-phases

Each leaves the suite green and is a working system on its own, per `CLAUDE.md`.

| Step | Deliverable | Check |
| :---- | :---- | :---- |
| 10a | Artboards in `docs/ux/table/` and `docs/ux/logo/` at 390 x 844, the way `docs/ux/replay/` was done: the table in all seven focus states, the replay, the lobby, three logo alternates | D1-D4 and D6 reflected in the artboards; David reviews the alternates and settles D5 |
| 10b | The token layer: `:root` rewritten with gaslight dark as the default, light-preference overrides, all four fonts self-hosted, the motion kill switch, `data-motion` wired into `clude_shots.py` and `tests/test_browser.py` | Every screen still renders in both themes at both widths; no preference uses gaslight dark; Bodoni wordmark and Playfair captions verified; the `ms`\-outside-`:root` test passes |
| 10c | 3.2: `readings` out of the human table payload, character methods hidden during normal play and named in the replay and setup form, the seat rail rebuilt on public facts, the notepad and hand restyled | A test asserts `readings` is absent from a human table's payload; Watch and replay keep the bars; method visibility follows D3; the two-account web test still passes |
| 10d | 3.3: Record and Talk split into two panels, balloons, the 240-char box, the turn-number margin, the speech pip | A scripted table's chat and record contain disjoint event sets; a hostile line still runs no script |
| 10e | 3.1: `focus` in `view_payload`, `data-focus` on the table, the grid per state, the beat caption, the panel cut | Focus ladder unit-tested in Python; a browser test walks all seven states |
| 10f | The decorated board and the logo David selects in 10a: patterns, engraved walls, threshold plates, the cellar mark, token initials | The no-colour test and the token-position tests still pass; screenshots looked at |
| 10g | Sound effects for play, Watch, and replay (11.1): self-hosted cues, shared playback, remembered mute and volume controls. No music | Cues heard and timed against visible events; mute and preferences work; polls and replay scrubbing do not repeat cues; no private information leaks; the app remains usable without audio |
| 10h | The help layer (D13): a Help link in the header bar; tooltips on every control, the notepad, the certainty tag and the seat rail; a first-login welcome card; a "How to play" page; the privacy and contact pages drafted (D12) | Every tooltip's text comes from one table so a test can read it; the welcome card shows once per account; the pages render under both looks |
| 10i | *Replaced by Wikiclude (D20), not yet started.* Was: the two explainers (D13): "How the characters think" at high-school level, and "The methods", a featured-article treatment of the math, CS and ML built from the glossary and the six modules, numbers included | Both pages linked from Help; the featured article's numbers match `docs/strategy-glossary.md`; both render under both looks and at 390 px |

Rough size: 10a a day, 10b-10f a day each; estimate 10g after selecting the cues and assets; 10h a day; 10i two days, most of it writing.

*Amended 2026-09-28 (the second round):* 10b's `:root` is case-file light with gaslight dark on a dark preference (D10), and Engraved goes into the picker as an opt-in beta, becoming the default only after 10e (D7); 10c shows every agent seat's method one-liner (D8) and hides only the cost bar (D9); 10f builds the keyhole-? candidate David picks (D11); 10h and 10i are new.

## 15\. Files

`static/style.css` (rewritten in place, same variable names), `static/fonts/` (new), `board_svg.py` (defs, rivets, initials, the cellar mark), `replay_data.py` and `tables.py` (`focus`, `readings` removed), `templates/table.html`, `templates/replay.html`, `templates/base.html`, `static/table.js`, `static/replay.js`, `scripts/clude_shots.py`, `tests/test_browser.py`, `tests/test_web_tables.py`, `docs/ux/table/`, `docs/ux/logo/`, `docs/web.md`, `CLAUDE.md`.

10g also adds `static/sounds/` (sound-effect assets) and `static/sound.js` (shared playback and preferences), with controls and event hooks in the templates and table/replay scripts above.

### Amendment (2026-09-26, Phase 9h)

Phase 9h froze the look of Phases 8.1 to 9h as the *Legacy* style
(`clude_web/styles.py`, `static/styles/legacy.css`) and made the look a
per-account setting. So `style.css` is no longer "rewritten in place":
10b writes `static/styles/engraved.css` beside Legacy, adds it to
`STYLES`, makes it `DEFAULT_STYLE`, and leaves Legacy on the list. The
variable names stay the same across the two files, so the templates and
scripts need not know which is linked; a rule that must differ by look
can key on `<html data-style="...">`. `scripts/clude_shots.py` gains a
loop over styles then, and the two stylesheet tests already run over
every entry.

## 16\. Out of scope

- Any change to the engine, the six methods, the personality dials or the prompts. Phase 10 covers visual and audio presentation.  
- Translation. The layout must not block it; nothing is translated.  
- A native app, a service worker, or offline play.  
- Music. Sound effects are included in 10g.  
- The IP scrub proper (renaming the characters and rooms). Phase 10 moves the *look* off the Classic game's; the names are Phase 11's question.  
- Anything that needs a build step.

## 17\. As implemented

### 10a: the artboards (2026-09-27)

Drawn, not coded: nothing under `clude_web/` changed. David chose to
view them as a contact sheet in the browser rather than through a
canvas tool, and asked for all three extras (a light twin, a wide
board, the open table).

**What was drawn.** `docs/ux/table/`: twelve `.dc.html` artboards at
390 x 844 in gaslight dark unless stated -- the seven focus states of
3.1 (`Show`, `End`, `Move`, `Decide`, `Beat`, `Talk`, `Board`), the
same board moment in case-file light with Notes open (`BoardLight`),
the three-column layout of section 6 at 1280 px (`Wide`), the open
table before the deal (`Waiting`), the lobby (`Lobby`) and the
omniscient replay (`Replay`). `docs/ux/logo/`: five -- the proposed
plate wordmark with the keyhole-c (`A-Plate`), the three alternates
(`B-Seal`, `C-Plan`, `D-Cartouche`), each at the cellar, the header
bar and the favicon in both themes, and all four in the cellar of the
real board at phone size (`Compare`). Each folder has a `canvas.json`
in the shape of `docs/ux/replay/` (a brief, one note per board, a
launch board) and an `index.html` that lays the boards out with their
notes in iframes, so a double-click shows the whole canvas.

**How.** `docs/ux/build_sketches.py` writes every file from
`docs/ux/sketch_parts.py`, which plays seed 7007 with David at
Scarlett and the five characters through `TableGame` exactly as a web
table is, stops after fourteen turns and again at the end (70 turns;
Green won; the envelope Peacock, the Rope, the Study), and keeps every
request she was asked with the board as it stood. Her hand, her
notepad, every seat's certainty on the 9h scale, the narration from her
seat (`tables.describe_for`) and the movement options with their
distance lines are the game's own. The table talk is the one invented
thing, since no model plays in a sketch; the notes say so. Rebuild with
`python docs/ux/build_sketches.py` from the venv; the parts are
deterministic per seed. `docs/ux/table/engraved-sketch.css` is section
5 verbatim as CSS custom properties -- gaslight dark on `:root`, the
case-file light under `[data-theme="light"]`, the six suspect colours
unchanged from `legacy.css` with an `-ink` twin each, the four faces
(from a Google Fonts link in the sketches), the type scale, the
spacings, `--radius` 2 px, `--lift`, the duration and easing tokens and
the `[data-motion="off"]` switch -- plus the components of section 7 as
far as the boards need them. It is 10b's `engraved.css` in draft; 10b
adds the `prefers-color-scheme` query, self-hosts the fonts and removes
the sketch-only rules.

**The board.** `board_svg.board_svg` as it is today, then
`sketch_parts.decorate` dresses it as section 8 says 10f will, with
classed, uncoloured shapes: a `<defs>` of four floor patterns (parquet,
tile, boards, rug) each holding a background rect, since a pattern is
transparent where it does not draw; walls as a double rule; rivets at
both ends of every door; an initial on every token; the logo in the
cellar in place of the wordmark text; lit destinations as an overlay
of squares at the request's coordinates; a dashed ring around the seat
now thinking. Findings for 10f: the cellar is 5 x 7 cells (35), about
75 x 105 px on a phone, which is the box every logo candidate was
drawn to; Peacock and Plum share an initial, so those two tokens carry
two letters (`Pe`, `Pl`); the double wall was drawn as a 3 px ink line
with a 0.8 px brass line over it rather than an offset inner line,
which reads engraved and needs no geometry; the floor patterns need a
tone about two steps from the room colour to survive a phone in the
dark theme; the room label's halo must be the pattern's background
colour.

**Reconciliation with 9g-9j**, which the plan predates: the seat rail
during play shows public facts plus the certainty tag and the cost
bar, and nothing else about another seat (3.2's table amended above);
the Accuse panel that a player sets up on any turn stays reachable
under `decide`; the per-turn clock sits at the right of the status
line; "so-and-so is typing" is a line under Talk; "Watching: Ann" is
the rail's foot; the Look picker stays in the header bar with two
entries; `end` shows the debrief progress in the status line and the
replay as the one primary choice.

**Departures from the sections above.** A six on the corridor gives
seventeen options, so the corridor squares are a compact row-column
grid under the room buttons rather than "Corridor, row 9, column 8"
each; six replay blocks of 21 rows do not fit a phone, so the blocks
collapse to their tag, method, hand and three mini gauges with the
winner's rows open; at 1280 px the seat rail runs across the top under
the header; a show-a-card with one matching card is one button, which
is the honest case for this deal.

**Sizes.** The table canvas is about 0.8 MB and the logo canvas 1.4 MB,
almost all of it the inline board (about 60 KB each, and the logo
boards carry four); the cropped cellar views are trimmed by
`sketch_parts.crop_svg`.

**D5.** Narrowed on 2026-09-28 (D11): E or F, David's pick pending.

### 10a, second round (2026-09-28)

David reviewed both canvases and liked them; his seven points are
D7-D14 in section 13. The artboards were revised the same day, still
from the same seeded game:

- Case-file light is every board's default (D10); the one dark twin is
  `BoardDark` (Notes open). The sketch stylesheet's `:root` is now the
  light block and `[data-theme="dark"]` the dark one.
- Every character seat on the rail carries its method (D8): the short
  form on the chip (`sketch_parts.METHOD_SHORT`: "Naive Bayes",
  "Decision tree", "Markov chain", "Bandit ensemble", "Dempster-Shafer",
  "Enumeration"), the full one-liner as its tooltip and in the wide
  layout. Six chips across a phone cannot carry the full line, which is
  a finding for 10c: chip short, tooltip long.
- The cost bar is gone from the rail (D9); the model-spend line is
  drawn under the board on `Board`, `BoardDark` and `Wide`.
- The logo canvas is D, E and F (D11): `E-Keyhole` puts an escutcheon
  plate with a "?" keyway on the cartouche; `F-Keyhole-c` draws the
  question mark as a hook whose dot is a c (a small raised c inside the
  bowl, tried first, vanished at every size). E is drawn into every
  table board's cellar and header bar meanwhile. A-C's files are
  deleted; their notes stay in git history.
- Sizes: the table canvas is still about 0.8 MB; the logo canvas is
  now about 1 MB.

### 10b: the token layer (2026-09-28)

`static/styles/engraved.css`, beside `legacy.css` and never touching
it, in `STYLES` as "Engraved (beta)" with Legacy still the default (D7).
Built with the suite green; deployed with 10c as `clude-00016-65z` on
2026-09-28.

- **The tokens** are section 5 as it stands after the second round:
  case-file light on `:root`, gaslight dark under
  `@media (prefers-color-scheme: dark)` (D10; no attribute to set), the
  six suspect colours unchanged with an `-ink` twin each, the board's
  dressing under legacy.css's names, the certainty tag's stops, the
  four faces, the type scale, the spacings, `--radius` 2 px, the
  hairline and ink rules, the printed shadow, and the duration and
  easing tokens. Lifted from the artboards' `engraved-sketch.css`, which
  stays in `docs/ux/table/` as the sketches' sheet.
- **The faces** are served from `static/fonts/`: eight Latin-subset
  woff2 files (289 KB in all) fetched from Google Fonts and declared
  with `@font-face`, so the app makes no third-party request; the
  licences and sources are in `static/fonts/README.md`. Google Fonts
  serves IBM Plex Mono as static weights, so it is three files; the
  other three are variable.
- **The motion kill switch:** `body[data-motion="off"]` and a
  reduced-motion preference both zero every duration token; no rule
  names a duration except through a token, and
  `test_engraved_names_no_duration_outside_its_tokens` refuses one.
  `clude_shots.py` and the browser tests' context ask for reduced
  motion and set the attribute on every page.
- **The screens as they are** are dressed class for class with
  legacy.css, since 10c-10e have not moved them yet: panels with the
  ink rule and the lift, solid-ink primary buttons and hairline quiet
  ones, the display face on headings and the step line, the gauge face
  on numbers, beliefs as a dot tone rather than an opacity, the status
  line's brass rule, the wordmark in Bodoni. The cost bar is hidden
  under this look (D9; the gauge is still built, and `clude_shots.py`
  now waits for it to exist rather than to be visible).
- **`clude_shots.py`** shoots every look on the list (`--look KEY` to
  narrow), picking each from the header bar after signing in; the file
  names carry the look.
- **Tests:** the two stylesheet tests already ran over every look; new
  are the duration rule, Legacy pinned on the list with its faces
  present on disk, the web test choosing Engraved and fetching its sheet
  and a font, and the browser test switching to Engraved, checking the
  fonts loaded, the switch zeroed `--dur-move`, and the board painted.
- Departure from the plan: the sheet does not restyle the templates'
  structure (no two panels, no focus ladder, no decorated board): those
  are 10c-10f, and the beta label says so.

### 10c: play is blind (2026-09-28)

Section 3.2 as amended by D8 and D9, in both looks. Built with the
suite green (523 passed, 27 skipped) and deployed with 10b as
`clude-00016-65z` on 2026-09-28; the stylesheet and a font were
fetched from the service afterwards, and `clude_shots.py` shot every
screen in both looks before the deploy.

- **`readings` is absent** from a seated player's payload, not null:
  `view_payload` adds the key only for a spectator, and the test that
  used to assert `None` now asserts the key is not in the poll and the
  string `"readings"` is not in the page. The bars were already off a
  seated player's screen since 2026-09-22; this closes the view-source
  gap the plan named. Spectators and Watch keep them (D1).
- **The seat rail on public facts.** Every seat in the payload now
  carries `method` (the one-liner from `replay_data.seat_method` for a
  character or LLM seat, empty for a person or the floor bot; D8) and
  `cards` (its hand size, public from the deal). `renderRoster` in
  `table.js` draws the name, the method, the card count, out or
  autopilot or the time-out strikes, and marks the seat the table waits
  on ("deciding", or "your decision", with an `acting` class the
  Engraved sheet gives a brass rule and the lift). Nothing of what a
  seat has proven or believes, and a test asserts no such key is sent.
- **The hand:** `me.shown` maps each card the viewer has shown to the
  seat it was last shown to, from the suggestion log; a shown chip gets
  the `shown` class and a tooltip, and in Engraved a dashed edge and a
  brass tick. It is never removed (7).
- **The notepad** keeps its markup (a square glyph for a proven holder,
  a dot for a possible one, which Legacy colours as before); Engraved
  hides the glyph and draws the cell's own mark, solid ink for a proof,
  a screentone dot for a possibility, the envelope column in the red
  thread, a solved row in the accent. `legacy.css` is untouched.
- Nothing changed for the lobby form or the replay: both already named
  the methods (D3 as amended).
- A test fix found by the full suite: the two stylesheet tests in
  `tests/test_replay_screen.py` were parametrised on each sheet's text,
  which put the 32 KB of `engraved.css` into the test id; on Windows
  pytest then failed to set `PYTEST_CURRENT_TEST`, an environment
  variable capped at 32767 characters. They now parametrise on the
  look's key and read the sheet inside the test.

### 10d-10g, with David's third round (2026-09-29)

Built in one day with the suite green (537 passed, 31 skipped; the 29
browser tests pass under `CLUDE_WEB_BROWSER=1`), not yet deployed. Two
things shape all four sub-phases:

- **Two markups, one script.** `legacy.css` is never edited, so Legacy
  cannot style anything new. `table.html` therefore has an Engraved
  branch (the stage and the rail) and keeps the markup Legacy was frozen
  with in the other; `board_svg` dresses the board only when asked; and
  `table.js` gates each Phase 10 behaviour on `<html data-style>` not
  being `legacy`. Each `Style` in `clude_web.styles` now says whether it
  is `engraved` and which `theme` it fixes. Legacy's screens are as they
  were, plus the favicon and the sound control, which work in both.
- **The looks (D15).** `STYLES` is Engraved (auto), Case file light,
  Gaslight dark and Legacy, the first three on one sheet; a fixed theme
  sets `<html data-theme>`, and `engraved.css` carries the dark tokens
  twice, under the device's preference unless the look fixes light, and
  under `:root[data-theme="dark"]` (a test keeps the two blocks
  identical). **Engraved is the default (D7)**: `DEFAULT_STYLE` is
  `engraved`. Version 3 accounts had `legacy` written into them unasked,
  so `users` version 4 records `style_chosen`, a stored `legacy` without
  it reads as no choice, and `add_user` writes no look at all; the
  session key is renamed (`style` to `look`) so a session from before
  falls through to the new default. Someone who had deliberately picked
  Legacy from the bar before today reads as unchosen and gets Engraved;
  they can pick it again.

**D16, the red thread.** The status line's clock is now its own element
(`.clock`), in `--accent`, and `--alarm` (a brighter red, with a dark
twin) for the last ten seconds; only the clock is rewritten each
second. The notepad's category headings are `--accent`, capitalised by
the sheet. An envelope row is marked `solved` and no longer struck
through.

**10d, the Record and Talk (3.3).** `view_payload` decides the split:
every event carries `panel` (`talk` for every `RemarkEvent`, `record`
for the rest), `seat` (whose event it is, `replay_data.event_actor`)
and, for a remark, `line`, the words without the speaker in front. The
Record prints each turn's number once in the gauge-face margin (CSS
`attr(data-turn)` on a turn's first line, so a line's text is
unchanged), with a hairline between turns; Talk is balloons, yours on
the right, the speaker's colour on the edge and tail (the name stays in
ink: Mustard's and White's colours are illegible as text on paper, and
White's colour becomes the soft ink); a record line on a turn with talk
gets the speech pip, which opens Talk there and flashes the balloon.
The say box counts from 200 characters and stops at 240. Tests: the two
panels hold disjoint events whose union is the log, remarks only in
Talk; a hostile line is data in the page, never markup.

**10e, the focus ladder (3.1).** `tables.focus_for(pending, finished)`
ranks what the server can see (`show`, `end`, `move`, `decide`,
`board`) and the payload carries it as `focus`; `table.js` lays the two
it cannot see over `board`: `beat` for 2.2 s after a suggestion or an
accusation arrives, `talk` for 6 s after a line. A decision of the
viewer's locks both out, except the accusation's impact frame (rank 2).
The stage is one panel with an overlay: the caption box (the speaker's
colour as its rule, the accusation in the hero size and
`aria-live="assertive"`), the last two balloons, or the riveted end
plate (the envelope, the winner). A focus change is a panel cut, a
clip from the right at `--dur-cut`; the accusation flashes the stage to
ink at `--dur-impact`, and with motion off it is still an 80 ms flash
to opacity (`--dur-flash`, the one duration the switch leaves alone).
Esc ends a beat or talk early. The layout is section 6's: on a phone one
column (status, stage, the decision under the thumb, the seat chips,
the tab strip Talk / Record / Hand / Notes with one panel open, each tab
showing what it holds back -- a count on Talk, a dot on Record, the
hand's size on Hand), the empty "Not your decision" panel dropped and
the board shrunk to a strip under `decide`; from 36rem two columns with
the stage sticky and every panel open; from 62rem the seats across the
top and the Record and Talk side by side. The seat chips carry the
pip with the initial, the name on its certainty, the method's short
form (`replay_data.METHOD_SHORT`, the one-liner on hover), one word of
state and the card count; the board marks the seat now thinking with a
dashed ring, and says where every token is in its `aria-label`
(`where` in the payload). A refused answer shakes the decision once.
Tests: the ladder in Python, and a browser test that plays seed 11 and
sees all seven states.

**10f, the decorated board and the logo (8, 9).** `board_svg(...,
dressed=True)` adds a `<defs>` of the four floor patterns (the sheet
picks one per room and colours it), a brass hairline over every wall, a
rivet at each end of every door, an initial on every token (`Pe` and
`Pl` for the two P's), and the logo in the cellar; undressed it is
byte for byte the old board. The views ask for it through the viewer's
look. The logo is candidate E, ported from `docs/ux/sketch_parts.py`
into `clude_web/logo.py`: the cellar's cartouche, the header bar's mark
beside the wordmark under Engraved, and `static/favicon.svg` (the one
drawing with its own colours, since a tab has no stylesheet; a test
keeps the file equal to `logo.favicon_svg()`). Tokens glide at
`--dur-move`; an initial moves by a CSS transform, since a text
element's x and y cannot be transitioned. Lit destinations are squares
at the server's coordinates, a room's larger and dashed (`size` in each
movement option), pulsing once; they stay one per button.

**10g, sound (11.1).** Four cues synthesised by `scripts/make_sounds.py`
from sines and a seeded noise, standard library only, 108 KB in all:
`tick` (a relay's click: a move, or a suggestion nobody disproved),
`turn` (a desk bell: a decision just became yours), `refute` (a card
snapped down) and `accent` (a struck plate: an accusation, the end). No
music. `static/sound.js` plays them: muted until turned on from the
header bar's Sound button (with a volume slider once on), both
remembered on the device; one cue per batch of new events, the loudest;
a cue within 150 ms of another dropped unless it outranks it. The cue is
made from the event alone (`replay_data.event_cue`), so every viewer
hears the same one for the same line. The table cues only what is new
since its last paint (so no poll, reload or first paint makes a sound;
talk is silent); the replay only when Play reaches a step, never the
scrubber; Watch plays its turn's loudest cue once when the page arrives
from Next turn, not on a reload (`data-cue` and a key in session
storage). The cues were checked by measurement (length, level, decay,
pitch), not yet by ear. Tests: the files are short mono WAVs, the
default is off, the preference survives a reload, and the silences
above hold in a browser (`window.cludeSound.played`).

**Found on the way.** Five browser tests had been failing since Phase
9j, expecting `browser` where names are now shown capitalised; fixed.
The first tab-badge code matched the wrong badge, because `#screen`
carries a `data-tab` too; the phone test caught it. The Record's turn
number once printed twice when a batch held two lines of one turn.

**Departures.** The replay keeps its layout (the collapsible seat
blocks of the 10a artboard are not built) and gains only the dressed
board and sound; the `show` caption names the asker and the cards you
hold, since the request does not carry the suggestion itself; on a
phone the header bar wraps to two rows with the Sound button in it.

### David's fourth round (2026-09-29): three looks, two folders, the footer

Built the same afternoon as D17-D20 were given, with the suite green
(539 passed, 31 skipped; the 29 browser tests pass under
`CLUDE_WEB_BROWSER=1`), not yet deployed.

**The looks (D17).** `STYLES` is `casefile` ("Case-file light", the
default), `gaslight` ("Gaslight dark") and `developer` ("Developer",
on `legacy.css`, never edited). Both Engraved looks fix `data-theme`,
so `engraved.css` lost its device-preference dark block, and the test
that kept the two dark blocks equal became one that keeps the dark
block to tokens the light `:root` defines. Keys changed without a new
account version: `styles.RENAMED` reads a stored or session `legacy` as
`developer` and `engraved` as `gaslight` (a version 3 `legacy` written
in unasked still reads as no choice), and the bar accepts only the new
keys. `table.js` gates on `data-style` not being `developer`. A new
`Style.costs`, true only for Developer, is the one content difference
so far.

**Stored games (D18).** Display only: the store's keys are unchanged,
so the `web` run, every replay URL and the MCP tools' `run_id` still
work. The lobby lists two folders, **practice** (`/practice`, the `web`
run's table under that name; `/runs/web` shows the same) and
**development** (`/development`, the run listing the lobby used to
show, less `web`); a run's crumbs and a replay's heading name the
folder. The lobby now reads one summary, practice's, and only counts the
rest. The games table's columns are David's; the Cost column, the run's
total and the folder's total in the lobby show in the Developer look
only. **Wall time** is new: `_deal` stamps `dealt` on the table
document, and the finish writes `wall_seconds` (deal to finish) on the
game's summary line; tables dealt before, and every arena run, leave it
blank.

**The header and footer (D19).** `static/styles/chrome.css`, loaded
after any look's sheet and using only tokens both define (a test checks
it against each), dresses the header bar's wooden question mark (the
last thing in the bar, 32 px, linking to `/wiki`) and a footer on every
page: Privacy, Contact, Wikiclude and the copyleft mark with "2026 AIX
Laboratories". The mark is `copyleft.svg` used as a CSS mask, so it
takes the text's colour in either theme. The wooden button is made by
`scripts/make_wood_button.py` from `questionmark.png`: each pixel keeps
its brightness relative to its part (face, bezel, glyph) and shades a
procedural grain -- honey oak on the face, walnut on the bezel, a
boxwood inlay for the "?" -- in a browser canvas through Playwright,
since there is no imaging library here; the source's faint square
shadow is dropped. **Privacy** is D12's page, drafted now rather than
in 10h: public like the login page (the gate test exempts it), stating
what is kept, who else sees it, the one cookie and how to leave.
**Contact** links the repo's GitHub issues, which only people with
access to the repository can open if it is private. **Wikiclude** is a
placeholder page behind the login.

**Not done.** Wikiclude itself (D20). The phone's header bar wraps the
wooden button onto its own row on pages without the Sound button.

### The fifth round (2026-10-01)

D21-D28, built in one sweep with the suite green (545 passed, 32
skipped; the 30 browser tests pass under `CLUDE_WEB_BROWSER=1`), not
yet deployed. The fourth round itself went live as `clude-00019-9x5` on
2026-09-29, which the status lines here and in `CLAUDE.md` had not
caught up with.

**Pass up top (D21).** `table.js` `passButton` adds "Pass" (the
accusation question) or "No suggestion" (entering a room) to the status
line after the clock, `#status-pass`, every look; the same `answer(null)`
as the panel's. The Accuse hint now says "or Pass above the board".

**The narration line (D22, D23).** `#narration`, between the status
line and the stage in both templates (Developer's above its board,
unstyled), tells the turn in play: its roll, then the turn's suggestion
and accusation in the Record's own words, starting again with the next
roll; the turn number is a CSS kicker. The beat is gone: no `#beat`, no
caption over the board for a suggestion, an accusation or a card to
show (the status line says that one), and `FOCUS_RANKS` loses `beat`,
so the ladder is show, end, move, decide, talk, board. Kept: the
accusation's impact flash, the Talk overlay and the end plate. The
decision panel no longer repeats the status line when the decision is
not yours. **The roll** is `LiveGame.rolls`, `(turn, seat, roll)`
appended by `game_steps` as each turn starts, beside the event log and
never in it, so no record, golden or fixture moved; `TableSnapshot.roll`
carries the latest and `view_payload` sends it as `roll`. A cold rebuild
replays the generator and finds the same rolls.

**Costs (D24).** The table's spend line is in the page only when the
look has `Style.costs`; `costBar` builds nothing outside Developer
(10b-D17 built it and hid it with CSS). Over MCP, `seat_view` and
`watch_view` take `costs`, which the tools set from the account's look
(`mcp.shows_costs`); a chatbot's account is Case-file light unless
someone picks Developer for it. The lobby's budget field stays: a
setting, not a spend.

**Logout (D25).** `clude_logout(login)`, the eleventh tool, bumps
`mcp_epoch` on the account document (`users.end_mcp_logins`); every
login carries the epoch it was issued under (`ep`) and `check_login`
refuses a mismatch. Every MCP login the account holds ends together --
nothing is stored per login -- and a login issued before there was a
logout has no epoch, reads as 0, and stays good until one is asked
for. The browser session is untouched.

**The board (D26).** Dressed only; Developer's board is unchanged byte
for byte. Each door is `<path class="board-door board-door-swing">`:
hinged at one jamb, the leaf one cell into the room, the arc back to
the other jamb, the swept quarter shaded at 14% of the red thread; the
hinge is the end no other door of the room shares, so the Hall's pair
opens as a double door. The rivets are gone. The floors are
`FLOORS`, one per room -- Kitchen checker tile, Ballroom chevron
parquet, Conservatory trellis, Billiard stippled baize, Library
panelling, Study hatch, Hall staggered flagstones, Lounge rosettes,
Dining staggered planks -- as `floor-<room>` patterns, each on its own
`--room-<room>` tint in both themes, which the label's halo follows.

**Showing a card (D27).** `tables.SHOW_TIMEOUT` (30 s) and
`decision_timeout(document, kind)`, the table's time-out but never more
than that for a card to show; used by `work`'s time-out, the `work`
flag, and `waiting.timeout`, which the page's clock and the chat seat's
waiting line read (`payload.timeout` stays the table's). A show that
times out is still a strike. The table's header says "90 s a decision,
30 s to show a card".

**The board's size (D28).** Two causes, both fixed. On a phone the
decide focus shrank the board to 26vh inside a full-width pane: now only
the suggestion form shrinks it (the accusation's Pass is up top) and the
stage hugs the strip. In two columns (a phone held sideways, a tablet)
the board was `width: 100%` under a 58vh cap, so it drew small in a wide
pane: now the main column is a size container and the board is as wide
as the column or 58vh allows, the stage hugging it; from 62rem it fills
the column as before. `clude_shots.py` waits for the cost bar only in
Developer.

