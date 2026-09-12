"""Board topology: room graph, hallway cells, secret passages, movement.

See `docs/board.md` for where this topology came from and what is a
documented simplification (hallway cell counts) versus sourced fact (room
adjacency, secret passages, starting positions).
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Union

from .domain import ROOMS

HALLWAY_LENGTH = 4  # generic single-occupancy cells per room-to-room edge

# Consecutive pairs in ROOMS, cyclically -- the 9-room perimeter ring.
EDGES: list[tuple[str, str]] = [
    (ROOMS[i], ROOMS[(i + 1) % len(ROOMS)]) for i in range(len(ROOMS))
]

SECRET_PASSAGES: dict[str, str] = {
    "Kitchen": "Study",
    "Study": "Kitchen",
    "Conservatory": "Lounge",
    "Lounge": "Conservatory",
}


@dataclass(frozen=True)
class HallwayCell:
    """One generic hallway square on the edge between `room_a` and `room_b`.

    `k` counts from 1 (adjacent to `room_a`) to `HALLWAY_LENGTH` (adjacent
    to `room_b`), per the edge's fixed orientation in `EDGES`.
    """

    room_a: str
    room_b: str
    k: int


Node = Union[str, HallwayCell]  # str is a room name

# Starting position for each suspect: (edge index into EDGES, k). See
# docs/board.md for sourcing and the flagged uncertainty.
START_POSITIONS: dict[str, tuple[int, int]] = {
    "White": (0, 1),      # Kitchen-Ballroom, near Kitchen
    "Green": (1, 1),      # Ballroom-Conservatory, near Ballroom
    "Peacock": (2, 1),    # Conservatory-Billiard, near Conservatory
    "Plum": (4, HALLWAY_LENGTH),  # Library-Study, near Study
    "Scarlett": (6, 1),   # Hall-Lounge, near Hall
    "Mustard": (7, 1),    # Lounge-Dining, near Lounge
}


def _room_edges() -> dict[str, list[int]]:
    edges: dict[str, list[int]] = {room: [] for room in ROOMS}
    for i, (a, b) in enumerate(EDGES):
        edges[a].append(i)
        edges[b].append(i)
    return edges


ROOM_EDGES = _room_edges()


def start_position(suspect: str) -> Node:
    """Return the starting `Node` for a suspect's token."""
    edge_index, k = START_POSITIONS[suspect]
    a, b = EDGES[edge_index]
    return HallwayCell(a, b, k)


def neighbors(node: Node) -> list[Node]:
    """Adjacent nodes one step away (excludes secret passages -- those are
    a separate move type, not a graph edge, since they bypass the hallway
    entirely and end movement instantly)."""
    if isinstance(node, str):  # room
        result: list[Node] = []
        for edge_index in ROOM_EDGES[node]:
            a, b = EDGES[edge_index]
            if node == a:
                result.append(HallwayCell(a, b, 1))
            else:
                result.append(HallwayCell(a, b, HALLWAY_LENGTH))
        return result

    result = []
    if node.k > 1:
        result.append(HallwayCell(node.room_a, node.room_b, node.k - 1))
    else:
        result.append(node.room_a)
    if node.k < HALLWAY_LENGTH:
        result.append(HallwayCell(node.room_a, node.room_b, node.k + 1))
    else:
        result.append(node.room_b)
    return result


def reachable(start: Node, roll: int, occupied: frozenset[HallwayCell]) -> set[Node]:
    """Nodes reachable from `start` in at most `roll` steps.

    A hallway cell in `occupied` blocks passage past it. Reaching a room
    ends that path (a token can't move through a room and out the other
    side in one turn), but a room reached in fewer than `roll` steps is
    still a valid destination -- movement is "up to" the roll, not exact.
    The *starting* node is always expanded, room or not: a token leaves
    the room it stands in through either of its doors. (Through Phase 4
    it could not -- the start room was treated as terminal too, so a
    token could only ever leave a room by secret passage. Fixed in
    Phase 5b once FloorBot games exposed the resulting pile-ups.)

    Parameters
    ----------
    start : Node
        Current position. Not included in the result.
    roll : int
        Die roll (1-6) bounding path length.
    occupied : frozenset[HallwayCell]
        Hallway cells currently holding another player's token.

    Returns
    -------
    set[Node]
        All reachable stopping points, rooms and hallway cells alike.
    """
    visited: set[Node] = {start}
    frontier: set[Node] = {start}
    result: set[Node] = set()
    for _ in range(roll):
        next_frontier: set[Node] = set()
        for node in frontier:
            if isinstance(node, str) and node != start:
                continue  # rooms reached this turn are terminal
            for nb in neighbors(node):
                if nb in visited:
                    continue
                if isinstance(nb, HallwayCell) and nb in occupied:
                    continue
                visited.add(nb)
                next_frontier.add(nb)
                result.add(nb)
        frontier = next_frontier
        if not frontier:
            break
    return result


def room_of(node: Node) -> str | None:
    """The room a node represents, or None if it's a hallway cell."""
    return node if isinstance(node, str) else None


@lru_cache(maxsize=None)
def room_distances(node: Node) -> dict[str, int]:
    """Steps from `node` to every room, by breadth-first search over
    hallway cells, rooms (passed through) and secret passages (one
    step), ignoring other tokens and the per-turn rule that entering a
    room ends movement. A proximity measure, not a turn count.

    Parameters
    ----------
    node : Node
        A room name or `HallwayCell` (both hashable, so results cache).

    Returns
    -------
    dict[str, int]
        Room -> steps; 0 for `node` itself when it is a room.
    """
    dist: dict[Node, int] = {node: 0}
    frontier: list[Node] = [node]
    while frontier:
        next_frontier: list[Node] = []
        for n in frontier:
            neighbours = list(neighbors(n))
            if isinstance(n, str) and n in SECRET_PASSAGES:
                neighbours.append(SECRET_PASSAGES[n])
            for nb in neighbours:
                if nb not in dist:
                    dist[nb] = dist[n] + 1
                    next_frontier.append(nb)
        frontier = next_frontier
    return {room: dist[room] for room in ROOMS}


def node_sort_key(node: Node) -> tuple:
    """A total order over `Node` that does not depend on Python's
    per-process string-hash randomization.

    `reachable` returns a `set`, whose iteration order is otherwise
    hash-dependent -- fine for the set's own contents (reachability is
    order-independent), but not for a caller that turns it into a list
    and indexes into it with a seeded RNG (`RandomBot.choose_movement`).
    Without this, an identical `seed` produced a different game on every
    process run despite `random.Random(seed)` itself being deterministic
    -- the RNG index was reproducible, but which `Node` sat at that index
    in the list wasn't. Sort by this key before choosing from any
    collection of `Node`s.
    """
    if isinstance(node, str):
        return (0, node, "", 0)
    return (1, node.room_a, node.room_b, node.k)
