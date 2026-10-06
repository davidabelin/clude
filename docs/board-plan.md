# Board plan: replacing the ring (historical)

Built 2026-09-15. The ring made movement unlike Classic Clue and invalidated conclusions about travel/parking. The replacement uses Board A (`docs/ux/sample_board_A.png`), measured as 24 columns by 25 rows. [Board](board.md) owns map/door provenance and current rules; [Phase 8.0](phase8.0-plan.md) owns re-measurement.

## 6. Decisions (David, 2026-09-15)

One die; use the full roll unless entering a room. Stay only after being summoned by another suggestion, or when no legal move exists. Do not re-enter the room just left. Reference-image edge cells determine playable topology; cellar is impassable. Keep ring-era records readable. Draw the UI from this map with fresh ornament and a central logo.

## 8. As implemented (2026-09-15)

- Square(row, col) replaced HallwayCell for new corridor positions; room positions remain names.
- BOARD_MAP parses room/corridor/cellar/start geometry; DOORS explicitly records facing where adjacency is ambiguous. There are 17 doors, two passages and six starts.
- Reachability uses simple paths, full-roll corridor endings, terminal room entry and occupancy. Engine tracks summoned tokens and moves named suspects during suggestions.
- Feature distances and JSON codecs accept grid positions. Record version 3 identifies the grid; versions 1/2 still decode ring cells.
- Seeded goldens/LLM recordings were deliberately refreshed; old measurements stayed dated rather than silently reused.

Phase 8.0.4 subsequently changed landing scores for rooms located in another seat's hand; that changed the policy, not the topology.
