# Phase 9h: five tweaks in one sweep

Planned and built 2026-09-26, on fake backends, the suite green. Not
deployed: it goes out with 9f and 9g on David's word.

## 1. Context

David listed seven scatter-shot points on 2026-09-26, to be built as
one phase before Phase 10 starts on the look. They fold into five
items:

1. **"So-and-so is typing…"** in the Table Talk panel, cycling through
   everyone who is.
2. **A turn time-out**: a player who does not act within 90 s (chat does
   not count) has the floor bot play *that turn only*; the seat stays
   theirs. **Speed mode** sets it to 30 s.
3. **A certainty tag**, experimental: each seat's name-tag coloured by a
   0..1 certainty, blue (clueless) through white (half a clue) to red
   (certain).
4. **Animate the replay**: Play/Pause and a slower-faster slider.
5. **Save the current look as the "Legacy" style**, a per-account setting
   any player can change at any time, the only option for now. Built
   last, so the other four are part of what it saves.

The naming follows 9a-9g; this doc follows `phase8.0-plan.md` and
`phase8.1-plan.md` in having a file of its own, since `phase9-plan.md`
was already 900 lines.

## 2. What the code dictates

- **The 3-minute hand-over never fired on a browser-only table.** The
  hand-over lived in `TableRegistry.work`, but `view_payload["work"]`
  was false while a person's decision was pending, so browsers only
  polled and `work` was never called. Only the MCP seat's `await_turn`,
  which calls `work` each second, ever triggered it; the three live
  chat games are the only tables where it could have. Item 2 fixes
  this: the payload says work is due once the deadline passes, and
  `table.js` wakes at the deadline.
- The clock (`_pending_since`, per table, in memory) is reset by any
  answer or bot turn and not by `say`, so chat already did not count.
- The one-decision stand-in answer already existed:
  `TableGame.autopilot()` records an entry `by="autopilot"`, and
  `rebuild` passes `by` through, so `"timeout"` needed no replay change.
  Permanent autopilot is only `document["autopilot"][seat]`.
- Presence had a pattern to copy: the spectator gallery (`_watchers`,
  in memory, monotonic timestamps, expired on read).
- Certainty had its inputs: `best_triple` gives P(best triple), each
  `AgentSpec` its `confidence_fn` (Peacock's lower bound), and
  `mask_and_normalize({}, mask)` the floor's uniform belief for a seat
  with no method. `WebGame.readings()` already built a fresh belief per
  character seat, cached per event count. The trace stored nothing for
  a human seat, so certainty had to go into the trace server-side.
- One stylesheet, linked from `base.html`; no per-user preference;
  accounts with a "missing key reads as default" convention; the
  session caching `password_offer` at login. Two tests read the
  stylesheet by a hard-coded path. Phase 10's plan said `style.css` is
  "rewritten in place": the Legacy snapshot pre-empts that.
- "Legacy" already names `legacy/`, the old code. The style's key is
  `legacy`; prose says "the Legacy style".

## 3. David's decisions (2026-09-26)

Asked while planning; answered before a line was written.

1. **Everyone sees every seat's colour**, players included. It overrides
   the 2026-09-22 rule that a seated player learns nothing of the other
   seats, for this one number: the poker face, a tell you can watch.
2. **The time-out is per turn, then three strikes**: the seat stays the
   person's, and three timed-out turns in a row put it on autopilot as
   the old rule did, since someone who has gone should not cost the
   table a whole time-out every turn.
3. **The scale is bits gained**, 0 at 1/324, 1 at certain, the same for
   people and characters, raw rather than relative to any accuse
   threshold: Scarlett goes pink, not red, when she jumps.
4. **Speed mode is a lobby checkbox**, stored on the table.

## 4. As implemented

### 9h.1 "So-and-so is typing…"

`clude_web/tables.py`: `TYPING_FOR` (8 s), `TableRegistry._typing`
(table -> seat -> monotonic), `seen_typing(table_id, seat, on)` and
`typing(table_id, game)`: the human seats marked within `TYPING_FOR`,
plus every seat with a reaction queued for this turn
(`game.reactions.queue`), which is a model seat about to speak or to
decide not to. `say` drops the seat's mark. `view_payload` gets
`typing=` and sends `typing`, the names of every such seat but the
viewer's own, to everyone, spectators included.

`clude_web/views.py`: `POST /tables/<id>/typing` (`on=1|0`), seated
only, answering `{"ok": true}`: a heartbeat, not a view. `table.js`
pings it on `input` in the say box, at most every 4 s while the box
holds text and once more when it is emptied; sending the line clears
it server-side. `renderTyping` writes "Ann is typing…" under the talk,
one name at a time, cycling every 2 s when several are on the way, and
the poll drops to 3 s while anyone is. The MCP seat never types: its
line lands whole.

### 9h.2 The turn time-out, three strikes, speed mode

`clude_web/tables.py`: `TURN_TIMEOUT` 90 s, `SPEED_TIMEOUT` 30 s,
`STRIKES` 3; `AUTOPILOT_AFTER` gone. `timeout_for(document)` reads the
table's `timeout` (older documents read 90). `create(..., speed=)`
writes `timeout` and `strikes` on the document. In `work`, `time_out()`
replaces `hand_over_if_stalled`: a human seat not on autopilot whose
time on the pending decision is up has every decision of that turn
answered by `game.autopilot(by="timeout")` until the game moves to
another seat (movement, suggestion and accusation in one turn; a lone
card to show), a strike is counted, and at `STRIKES` in a row the
autopilot flag is set as before. `work` returns `"timeout"`. A seat's
own `answer` resets its strikes. `TableGame.autopilot` takes `by`.

**The bug fix.** `view_payload["work"]` is also true when the table
waits on a human seat past the deadline, and `table.js` wakes at the
deadline (`untilDeadline`: the server's `waiting.seconds` plus the time
since the payload, against `timeout`), so whichever page sees the time
run out -- the stalling player's own included -- posts `/work`. Before
this nothing did. The payload carries `timeout`, `seats[].strikes` and
`me.strikes`; `offer_autopilot` is gone (no script read it), and the
autopilot route is the seat's owner's alone, since the "anyone seated
after three minutes" branch is unreachable now.

What people see: the status line ticks "N s left" once a second
client-side ("Your move. 90 s left before the floor bot moves for
you."); the hand panel says how many turns the floor bot has played for
you after the time-out and what three in a row means; the roster marks
"timed out ×N"; the table's header line says "90 s a decision" or
"speed mode, 30 s a decision"; the lobby form has the checkbox and its
table list says "speed mode".

`clude_web/mcp.py`: the waiting line says "the floor bot plays this
turn at 90 s"; `clude_turn` and `clude_autopilot` describe the per-turn
rule and the three strikes, and warn that a speed table's 30 s is tight
for a chat seat; `clude_tables` lists each table's `timeout`.
`POLL_SECONDS` stays 60: at most two idle replies a turn now.

### 9h.3 The certainty tag

`clude_agents/character.py`: `N_TRIPLES` (324) and
`certainty(confidence)`: with P the product `best_triple` gives, the
fraction of the bits gained, `ln(P * 324) / ln(324)`, clamped to
[0, 1]: 0 at a uniform guess over the 324 triples, 0.5 at about one
triple in 18, 1 when the triple is certain.

`clude_web/replay_data.py`: `seat_certainty(label, belief, obs)`: a
character's through its own `confidence_fn` (Peacock's lower bound),
anyone else's from the floor alone, `mask_and_normalize({}, obs.mask)`.
`trace_document` stores `certainty` per seat per frame and
`TRACE_VERSION` is 2, so every cached trace is rebuilt on its next open
(the bucket's nine web games and the arena runs alike; a Plum trace
takes its ten seconds once more). `screen_payload` passes it through.

`clude_web/tables.py`: `WebGame.beliefs()` caches the fresh belief per
seat per event count; `readings()` and the new `certainties()` share
it, so a seated viewer's poll costs one Plum reading per event, not per
page. Readings carry `certainty` (the Watch page), and
`view_payload` gives every viewer `seats[].certainty`.

Rendering: the seat heading (`.seat h2`) takes class `tag` and
`--certainty` inline, set by `table.js` for the roster and the readings,
by Jinja on the Watch page, and per frame by `replay.js`; a `title`
gives the percentage. The stylesheet defines `--certainty: 0` and the
three stops (`--certain-cold`, `--certain-mid`, `--certain-hot`, light
and dark, pale so the ink stays readable) and mixes them in two
`color-mix` steps: cold to white over the first half, white to hot over
the second. Each screen's key sentence says what the colour is.

The chat seat reads it too: each line of `seats` in the MCP view ends
with "certainty N%", and `clude_turn` explains the scale (David,
2026-09-26, "fair's fair"; a first cut left it out as a screen thing).

### 9h.4 Play and speed on the replay

`replay.html`: `#play` before the step buttons and `#speed` (0-100,
default 50) after the counter; `replay.js`: one step per tick on a log
scale from 2 s a step to 60 ms, about 350 ms in the middle, re-read at
every step so the slider takes at once. The end pauses; Play at the
end starts over; any hand on the scrubber or the keys pauses; Space
toggles. `scrub.value` stays the one source of truth. The scrubber
wraps at phone width.

### 9h.5 The Legacy style

`clude_web/styles.py`: `Style(key, title, stylesheet)`, `STYLES`
(`legacy` only), `DEFAULT_STYLE`, `style_named` (unknown -> default),
`is_style`. `static/style.css` moved to `static/styles/legacy.css`
(`git mv`) with a header saying it is frozen: Phase 10's look is a
second file beside it and the new default, and Legacy stays on the
list. `users.py`: `DOCUMENT_VERSION` 3, `style` on a new account,
`style_of` (missing or unknown -> default) and `set_style`. `auth.py`:
`SESSION_STYLE` set at login, `current_style()`, and `POST /style`
(`style`, `next`), which writes the account, updates the session and
redirects to `next` if it is a path on this site, else the lobby.
`base.html`: `<html data-style="...">`, the chosen sheet linked, and a
"Look" form in the header bar on every signed-in page, a table
mid-game included; on a phone the bar wraps and the word "Look" is for
screen readers only.

### Docs and the phase-10 amendment

`docs/web.md` (a table, the replay, "Looks", the MCP section, the
layout table), `docs/phase-plan.md` row 9, `CLAUDE.md`, and
`docs/phase10-plan.md` §15: 10b adds `static/styles/engraved.css`
beside Legacy and makes it the default; `style.css` is no longer
"rewritten in place".

### Tests

Suite 503 passed and 27 skipped, from 495 and 22 (the five new browser
tests skip without the flag); with `CLUDE_WEB_BROWSER=1`, all 25
browser tests pass. New or rewritten:

- `tests/test_web_tables.py`: typing seen by the other seat and the
  gallery and not the typist, cleared by `say`, by emptying the box and
  by expiry, two typists in seat order; a timed-out turn played whole
  with the seat still the person's, chat not counting, the poll past
  the deadline saying work is due (the bug's regression test), the own
  answer clearing the strike; three strikes handing the seat over; the
  speed checkbox, the header line, an older document reading 90, the
  autopilot route owner-only; every seat's certainty for a player and a
  spectator, a person's only rising.
- `tests/test_web_llm.py`: a model seat with a reaction queued reads as
  typing. `tests/test_web_debrief.py`: reactions made immediate, since
  on a fast machine `play_out`'s 4,000 in-memory steps passed before a
  2-8 s reaction was due and all three tests failed before any change
  (they pass on Orbit by being slower).
- `tests/test_character.py`: the certainty scale. `tests/test_replay_screen.py`:
  certainty in every frame, the floor's only rising, the winner's 1 at
  the end, Peacock's from her lower bound, version 2; the two
  stylesheet tests now parametrised over every style. `tests/test_web_watch.py`:
  the reading's shape, the tag on the Watch page.
- `tests/test_web.py`: the replay's Play and speed ids; the look linked
  and named on every page, `/style` refusing a bad key and a foreign
  `next`, the account and session updated, older and unknown keys
  reading as the default, the login page styled with no picker.
- `tests/test_mcp.py`, `tests/test_table.py`: the new wording and `by`.
- `tests/test_browser.py`: typing across two browsers; a 2 s time-out
  turn played from the stalling player's own page with the note shown
  and the seat kept; the tag painted on every seat and the winner
  certain at the end of the replay; Play stepping, Pause holding, a key
  pausing; the Look form bringing the same page back.

Screenshots looked at in both themes at both widths
(`scripts/clude_shots.py` against a throwaway arena store): the tags,
the countdown, the Play controls and the Look picker; the phone bar
crowded the mark until it was let wrap.

## 5. Out of scope

A live switch for speed mode (David: leave it out); a `users style`
CLI command (David: not until Phase 10, if then); screenshots per style while there is one;
any change to a method, dial, preset, persona or `rules.md`; the deploy
itself.
