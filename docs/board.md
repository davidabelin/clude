# Board

David chose full board movement for Phase 1 (grid/graph of rooms and
hallways, dice rolls, secret passages, hallway blocking) over abstracting
movement away. This documents where the topology came from and what is a
deliberate simplification.

## Source

Room grid positions and secret-passage pairs are reconstructed from a
published redrawing of the classic board: *"Redrawing of the classic Cluedo
board"* by CMG Lee, CC BY-SA 4.0, Wikimedia Commons,
[File:Cluedo_board.svg](https://commons.wikimedia.org/wiki/File:Cluedo_board.svg).
The SVG places each room icon and each character's start marker with
explicit `translate(x,y)` coordinates, which is a more reliable source than
recalled trivia. Two facts were cross-checked against independent sources
and agree with the SVG:

- Secret passages connect **Kitchen <-> Study** and **Conservatory <->
  Lounge** (confirmed via web search of the general Cluedo rules, and via
  the SVG's own paired "tunnel" trapdoor markers, color-coded so each
  passage's two ends match).
- The four corner rooms (Kitchen, Conservatory, Lounge, Study) are exactly
  the four rooms with secret passages, and the SVG's room coordinates place
  them at the four diagonal corners, consistent with "each corner room
  connects to the opposite corner."

The resulting room adjacency is a 9-room cycle, matching (and confirming)
the order `legacy/domain.py` already used for `ROOMS`:

```
Kitchen - Ballroom - Conservatory - Billiard - Library - Study - Hall - Lounge - Dining - (back to Kitchen)
```

plus the two secret-passage chords (Kitchen-Study, Conservatory-Lounge).

## Character starting positions

Reconstructed from the SVG's six starting-marker coordinates by nearest
adjacent room (token color -> character via standard Clue token colors:
red=Scarlett, mustard-yellow=Mustard, white=White, green=Green,
blue=Peacock, purple=Plum):

| Character | Starts near |
|---|---|
| Scarlett | Hall (Hall-Lounge edge) |
| Mustard | Lounge (Lounge-Dining edge) |
| White | Kitchen (Kitchen-Ballroom edge) |
| Green | Ballroom (Ballroom-Conservatory edge) |
| Peacock | Conservatory (Conservatory-Billiard edge) |
| Plum | Study (Library-Study edge) |

**Flagged uncertainty:** a web search for this same fact returned a
different mapping (Scarlett/Study, Mustard/Library, White/Billiard,
Green/Conservatory, Peacock/Dining, Plum/Hall) from an unverifiable summary,
which could reflect a different edition of the board. The table above is
the one grounded directly in measured coordinates from a single citable
source, so it's what's implemented. If David has a physical board to check
against, `clude_core/board.py`'s `START_POSITIONS` is the one place to fix.

## Simplification: hallway cell counts are not pixel-exact

Each room-to-room edge in the graph is modeled as a fixed chain of 4 generic
single-occupancy hallway cells (`HALLWAY_LENGTH = 4` in `board.py`), not a
recreation of the real board's exact per-corridor square count. This
preserves every mechanic that matters for the rules engine -- dice-roll
movement range, hallway blocking (a cell can hold only one token), secret
passages ending movement instantly, and "must stop on entering a room" --
without requiring pixel-exact square counts, which would only matter for a
literal visual board rendering (a Phase 8 UI concern, not engine logic).

## Movement rules implemented

- Roll 1d6 (engine-controlled RNG, not a player choice).
- From a hallway cell, move up to the roll in either direction along the
  chain; a cell occupied by another token blocks passage past it (you stop
  at the last free cell, you don't forfeit the rest of your turn for
  future turns -- just this move truncates there).
- Reaching a room ends movement immediately, even with roll remaining.
- From a room, you leave through either of its two doors into the
  adjoining hallway chain, again up to the roll (an adjacent room is five
  steps away, so it takes a 5 or a 6 to cross in one turn). Through
  Phase 4 the engine got this wrong -- the starting room was treated as
  terminal too, so a token could only ever leave a room by secret
  passage -- which is why every early self-play game piled up in one
  room; fixed in Phase 5b (`board.reachable`).
- From a room, you may also stay without moving, or -- if that room has a
  secret passage -- take it instead of rolling, moving instantly to the
  connected room and ending movement there.
- A hallway token boxed in by other tokens on both sides has no move and
  simply stays put that turn (`engine.legal_moves` offers only ``stay``).
- A suggestion may only name the room the suggesting player currently
  occupies. Making a suggestion moves the named suspect's token into that
  room (official rule), which can reposition another character ahead of
  their own turn.
- An accusation may be made on a player's turn regardless of location.
