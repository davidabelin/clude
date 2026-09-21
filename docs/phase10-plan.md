# Phase 10 Plan: the shippable look \-- "engraved, not brass-plated"

Status: **proposed 2026-09-20; David's answers recorded 2026-09-21.** David's brief is section 3; D1-D4 and D6 are settled in section 13\. D5 remains open until David sees the three logo alternates in 10a. Written in the shape of the other phase plans: context, what the code dictates, design, sub-phases, files, decisions, out of scope, and an "as implemented" section once the work lands.

## 1\. Context

Phases 8.1 and 8.2 put the screens up deliberately plain: the colour system is already a token layer (`static/style.css`, every colour a variable, light and dark), `board_svg.py` sets no colour at all, and `scripts/clude_shots.py` plus `tests/test_browser.py` can look at the result in both themes at both widths. Phase 10 spends that groundwork: typography, ornament, the decorated board and its logo, motion, the six-seat layouts, the case-file styling, and sound effects in 10g. No music.

Phase 10 also does the first half of the scrub `CLAUDE.md` wants before any public release. Every step away from the Classic game's own art and toward a house style is a step out of the IP thicket \-- the names stay for now, the look stops being Hasbro's.

Three screens carry the whole app: **the table** (play), **the replay** (post-game), **the lobby**. Watch shares the table's parts.

## 2\. What the code dictates

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

**Watch keeps the bars** (D1, confirmed). Watch is characters only \-- there is nobody at the table to gain from the information, and the six methods racing each other is the entire point of the screen. The bars remain in Watch and the replay; they are removed from normal play.

**A character's method is hidden during normal play**, named in the replay, and visible on the lobby form to whoever sets the table up (D3, confirmed).

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

Answers recorded 2026-09-21. D1-D4 and D6 are settled; D5 remains unanswered until David reviews the alternates.

- **D1. Watch keeps the bars?** My proposal: yes \-- nobody is at the table, and the six methods racing is what Watch is for. Play loses them, the replay keeps them.

  **Answer:** Yes, of course.

- **D2. Did I read 3.2 right?** Your sentence was "no information about other players should be shown (as it is the way it stands now)". I have read that as *the seat bars now on the table screen must come off*. If you meant the opposite \-- that today's screen is already correct \-- say so and section 3.2 shrinks to a test that keeps it correct.

  **Answer:** You read me correctly. I want the change.

- **D3. Is a character's method public during play?** It is a real tell: knowing Scarlett accuses early is worth something. My proposal: hidden during play, named in the replay, and visible on the lobby form to whoever sets the table up.

  **Answer:** Proceed as proposed.

- **D4. Display face**: Bodoni Moda or Playfair Display. Bodoni is sharper and colder, Playfair warmer and more legible small. I lean Bodoni for the wordmark and Playfair for captions if we can afford both; if three faces is the cap, Playfair does both jobs.

  **Answer:** Bodoni for the wordmark and Playfair for captions.

- **D5. Logo**: is the plate wordmark plus the keyhole-c the direction, or do you want the three alternates drawn first?

  **Answer:** Unanswered. Let me see the alternates first.

- **D6. Light or dark as the default** when a device states no preference. Case-file light is the better first impression; gaslight dark is the better game.

  **Answer:** Gaslight dark is default.

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

Rough size: 10a a day, 10b-10f a day each; estimate 10g after selecting the cues and assets.

## 15\. Files

`static/style.css` (rewritten in place, same variable names), `static/fonts/` (new), `board_svg.py` (defs, rivets, initials, the cellar mark), `replay_data.py` and `tables.py` (`focus`, `readings` removed), `templates/table.html`, `templates/replay.html`, `templates/base.html`, `static/table.js`, `static/replay.js`, `scripts/clude_shots.py`, `tests/test_browser.py`, `tests/test_web_tables.py`, `docs/ux/table/`, `docs/ux/logo/`, `docs/web.md`, `CLAUDE.md`.

10g also adds `static/sounds/` (sound-effect assets) and `static/sound.js` (shared playback and preferences), with controls and event hooks in the templates and table/replay scripts above.

## 16\. Out of scope

- Any change to the engine, the six methods, the personality dials or the prompts. Phase 10 covers visual and audio presentation.  
- Translation. The layout must not block it; nothing is translated.  
- A native app, a service worker, or offline play.  
- Music. Sound effects are included in 10g.  
- The IP scrub proper (renaming the characters and rooms). Phase 10 moves the *look* off the Classic game's; the names are Phase 11's question.  
- Anything that needs a build step.
