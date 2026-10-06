# Phase 9h: five tweaks in one sweep

Built and deployed 2026-09-26. Condensed historical record; [Web](web.md) owns current timeout, replay and style behavior.

## 1. Context

Typing, per-turn timeout/speed mode, certainty tags, replay animation and a saved Legacy look were built together before Phase 10's visual pass.

## 2. What the code dictates

The old three-minute handover lived in work, but browser payloads said no work was due while a human decision was pending. Browser-only tables never triggered it. The fix must make deadline expiry schedule work, not merely change the timeout constant. The deadline is process-local and resets on cold rebuild.

## 3. David's decisions (2026-09-26)

Everyone sees certainty, overriding the otherwise blind seated roster for this one number. The scale is bits gained, 0 at 1/324 and 1 at certainty, not relative to accusation threshold. Timeout plays one turn while retaining ownership; three consecutive strikes hand over. Speed is chosen at table creation, not changed live.

## 4. As implemented

- Typing is expiring presence, refreshed while text is entered and cleared by send/emptying. Model reactions queued to speak also appear; the typist does not see their own marker.
- A 90 s decision timeout (30 s speed) schedules FloorBot to finish the turn. An answer clears the consecutive-strike run; talk does not count as acting. Owner-only autopilot can be reclaimed.
- Certainty is generated server-side using the character confidence function or floor belief, including humans; replay traces gained it and cache version 2.
- Replay gained Play/Pause/speed; manual stepping pauses. The look preference is saved on the account/session; old documents fall back to default.
- Legacy's stylesheet was frozen as a selectable style so Phase 10 could add a sibling stylesheet.

Later amendments: card shows have at most 30 s, Legacy is named Developer, Case-file light is default, and costs appear only in Developer. These supersede original "only Legacy for now" wording.

## 5. Out of scope

No live speed switch, no method/preset/persona changes in this phase. Browser checks validated typing, deadline work, seat retention/three strikes, certainty colors, replay controls and look selection. Tests/screenshot counts at the time were historical, not current acceptance totals.
