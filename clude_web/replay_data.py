"""Build event/board frames and cached reconstructed belief traces.

Event folding is cheap; fresh-agent belief analysis is cached by trace
version/checkpoint interval. Traces do not restore live method memory or
Green's outcome feedback and use current weights; limitation accompanies
the payload. Player visibility is handled separately by table/MCP views.
Board decoration, certainty and sound metadata derive from the same events.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from datetime import datetime, timezone

import clude_constraints
from clude_agents import AGENT_SPECS, build_agent
from clude_agents.base import mask_and_normalize
from clude_agents.character import certainty
from clude_core import board
from clude_core.domain import ALL_CARDS, ROOMS, SUSPECTS, WEAPONS
from clude_core.events import (
    AccusationEvent,
    GameOverEvent,
    MoveEvent,
    RemarkEvent,
    SuggestionEvent,
)
from clude_training.replay import state_from_record
from clude_training.self_play import truncate_state

TRACE_VERSION = 2
"""Bumped when the cached document's shape changes, so a stale cache is
rebuilt rather than misread. 2 added each seat's `certainty` per frame
(Phase 9h)."""

TRACE_LIMITATION = (
    "These bars are reconstructed estimates: replay does not restore starting "
    "method memory or Green's outcome-feedback updates. White's current-game "
    "chain is rebuilt from the recorded suggestions."
)


def trace_key(run_id: str, game_index: int) -> str:
    """Where a game's cached trace lives, beside its record."""
    return f"traces/{run_id}/{int(game_index):05d}.json"


@dataclass
class EventFrame:
    """The game as it stood right after one event.

    Parameters
    ----------
    index : int
        Position in the record's event log.
    turn : int
        The engine turn this event belongs to.
    kind : str
        ``"move"``, ``"suggestion"``, ``"accusation"``, ``"remark"`` or
        ``"over"``.
    text : str
        The line the screen shows for this step.
    positions : dict
        Suspect name -> the node its token stands on, ready for
        `board_svg.board_svg`.
    k : int
        How many suggestions have resolved by now, which is the index
        into the belief frames -- the join between the two halves, since
        tokens move per event but beliefs only change per suggestion.
    cue : str or None
        The sound the step makes when Play reaches it (`event_cue`,
        Phase 10g).
    door : int or None
        For a move into a room through a door, that door's index in
        `board.DOORS` (`entry_doors`, 2026-10-01): the one the board
        swings open as the token goes in.
    passage : str or None
        For a move by secret passage, the room it came out in.
    """

    index: int
    turn: int
    kind: str
    text: str
    positions: dict
    k: int
    cue: str | None = None
    door: int | None = None
    passage: str | None = None


def suggestion_line(suggestion, suspects, reveal: bool = True) -> str:
    """One suggestion as a sentence, refutation included.

    `clude_agents.explain.describe_suggestion` says the same thing as
    ``White/Rope/Lounge -- Scarlett showed White``, which is right for a
    terminal column and wrong for a line of prose under a board. The
    audience differs, so the wording does; the facts are identical.

    With `reveal`, the card shown is named: a record is omniscient, and
    that is the point of a post-game replay. Without it -- a game still
    being watched -- the line says only *who* disproved it, which is all
    anyone but the two seats involved learns at a real table.
    """
    line = (
        f"{suspects[suggestion.suggester]} suggests {suggestion.suspect} "
        f"with the {suggestion.weapon} in the {suggestion.room}."
    )
    if suggestion.refuter is None:
        return f"{line} Nobody could disprove it."
    refuter = suspects[suggestion.refuter]
    if reveal and suggestion.card_shown:
        return f"{line} {refuter} showed {suggestion.card_shown}."
    return f"{line} {refuter} disproved it."


def describe_event(event, suspects, reveal: bool = True) -> tuple:
    """``(kind, text)`` for one event: the line the screen shows for it.

    `reveal` is `suggestion_line`'s: False keeps the card shown private,
    for a game still in progress. The replay and the Watch screen both
    read their lines from here, so they cannot describe a turn two ways.
    """
    if isinstance(event, MoveEvent):
        where = event.destination
        where = where if isinstance(where, str) else "the corridor"
        by = " by the secret passage" if event.used_secret_passage else ""
        return "move", f"{suspects[event.player]} moves to {where}{by}."
    if isinstance(event, SuggestionEvent):
        return "suggestion", suggestion_line(event.suggestion, suspects, reveal)
    if isinstance(event, AccusationEvent):
        accusation = event.accusation
        verdict = "and is right" if accusation.correct else "and is wrong"
        return "accusation", (
            f"{suspects[accusation.accuser]} accuses {accusation.suspect} "
            f"with the {accusation.weapon} in the {accusation.room}, {verdict}."
        )
    if isinstance(event, RemarkEvent):
        return "remark", f"{suspects[event.seat]}: “{event.text}”"
    if isinstance(event, GameOverEvent):
        suspect, weapon, room = event.solution
        who = suspects[event.winner] if event.winner is not None else None
        return "over", (
            f"{who} wins. " if who else "Nobody wins. "
        ) + f"It was {suspect} with the {weapon} in the {room}."
    return "other", type(event).__name__  # a new event type shows up, not vanishes


def seat_names(record) -> list:
    """Suspect per seat, in seat order."""
    seats = sorted(record.seats, key=lambda s: s.seat)
    if len(seats) == record.n_players:
        return [s.suspect for s in seats]
    return list(SUSPECTS[: record.n_players])


def event_frames(record) -> list:
    """The board and a line for every event, in order.

    Folds exactly as `clude_training.replay.state_from_record` does --
    a move places its player, a suggestion also drags the named suspect's
    token into the room, a wrong accusation eliminates its accuser --
    but keeps every intermediate board instead of only the last.
    """
    suspects = seat_names(record)
    positions = {s: board.start_position(s) for s in suspects}
    doors = entry_doors(record.events, suspects)
    frames = []
    k = 0

    for index, event in enumerate(record.events):
        if isinstance(event, MoveEvent):
            positions[suspects[event.player]] = event.destination
        elif isinstance(event, SuggestionEvent):
            k += 1
            if event.suggestion.suspect in positions:
                positions[event.suggestion.suspect] = event.suggestion.room
        kind, text = describe_event(event, suspects)

        frames.append(
            EventFrame(
                index=index,
                turn=getattr(event, "turn", 0),
                kind=kind,
                text=text,
                positions=dict(positions),
                k=k,
                cue=event_cue(event, doors[index]),
                door=doors[index],
                passage=event.destination if isinstance(event, MoveEvent) and event.used_secret_passage else None,
            )
        )
    return frames


@lru_cache(maxsize=None)
def _corridor_steps(start) -> dict:
    """Corridor square -> steps from `start` (a square, or a room left by
    any of its doors), walking corridor squares only."""
    dist = {}
    frontier = list(board.neighbors(start)) if isinstance(start, str) else [start]
    frontier = [n for n in frontier if not isinstance(n, str)]
    for node in frontier:
        dist[node] = 0 if node == start else 1
    while frontier:
        nxt = []
        for node in frontier:
            for nb in board.neighbors(node):
                if not isinstance(nb, str) and nb not in dist:
                    dist[nb] = dist[node] + 1
                    nxt.append(nb)
        frontier = nxt
    return dist


def nearest_door(start, room: str):
    """The index in `board.DOORS` of the door of `room` nearest `start`:
    the one a token from there walked in by, since the engine keeps no
    path and a move is the whole roll along some shortest way. Ties go
    to the door listed first. None when `start` is not a node of this
    board (a ring-era record)."""
    try:
        steps = _corridor_steps(start)
    except TypeError:
        return None
    best = None
    for index, (door_room, _cell, square) in enumerate(board.DOORS):
        if door_room != room or square not in steps:
            continue
        if best is None or steps[square] < steps[board.DOORS[best][2]]:
            best = index
    return best


def entry_doors(events, suspects) -> list:
    """For every event, the door a move came into a room through, as an
    index in `board.DOORS`, or None (2026-10-01): None for anything but a
    move, a move that ends in the corridor, by secret passage, or that
    stays put. `suspects` is the seat -> token list. Folds the tokens'
    places as `event_frames` does, a suggestion's summons included, since
    the door depends on where the token stood before."""
    positions = {s: board.start_position(s) for s in suspects}
    out = []
    for event in events:
        door = None
        if isinstance(event, MoveEvent):
            who = suspects[event.player]
            before, after = positions.get(who), event.destination
            if isinstance(after, str) and not event.used_secret_passage and before != after:
                door = nearest_door(before, after)
            positions[who] = after
        elif isinstance(event, SuggestionEvent) and event.suggestion.suspect in positions:
            positions[event.suggestion.suspect] = event.suggestion.room
        out.append(door)
    return out


def seat_method(label: str) -> str:
    """The human name of the method behind a seat, for its block's
    subtitle. A bot seat has none."""
    spec = AGENT_SPECS.get(label)
    return getattr(spec, "description", "") if spec else ""


METHOD_SHORT = {
    "Scarlett": "Naive Bayes",
    "Mustard": "Decision tree",
    "White": "Markov chain",
    "Green": "Bandit ensemble",
    "Peacock": "Dempster-Shafer",
    "Plum": "Self-play policy",
}
"""`seat_method` cut to fit a phone's seat chip (10a's artboards, Phase
10e): six chips across 390 px cannot carry the one-liner, which stays
the chip's tooltip and the wide layout's text."""


def seat_method_short(label: str) -> str:
    """The short form of a seat's method, or empty for a seat with none."""
    return METHOD_SHORT.get(label, "") if label in AGENT_SPECS else ""


def event_actor(event):
    """The seat an event belongs to -- who moved, suggested, accused or
    spoke, or who won -- or None (a game nobody won)."""
    if isinstance(event, MoveEvent):
        return event.player
    if isinstance(event, SuggestionEvent):
        return event.suggestion.suggester
    if isinstance(event, AccusationEvent):
        return event.accusation.accuser
    if isinstance(event, RemarkEvent):
        return event.seat
    if isinstance(event, GameOverEvent):
        return event.winner
    return None


def event_cue(event, door=None):
    """The sound an event makes (Phase 10g, plan 11.1), or None: a tick
    for a move and for a suggestion nobody could disprove, the
    refutation cue for one somebody did, the accent for an accusation
    and for the end. Talk is silent. Made from the event alone, never
    from who saw which card, so a cue tells nobody more than the line
    it goes with. Since 2026-10-01 a move into a room makes the door
    (`door`, from `entry_doors`, says it came through one) or the
    passage's own sound."""
    if isinstance(event, MoveEvent):
        if event.used_secret_passage:
            return "passage"
        return "door" if door is not None else "tick"
    if isinstance(event, SuggestionEvent):
        return "refute" if event.suggestion.refuter is not None else "tick"
    if isinstance(event, (AccusationEvent, GameOverEvent)):
        return "accent"
    return None


CUE_RANK = {"tick": 0, "door": 1, "passage": 1, "turn": 2, "refute": 3, "accent": 4}
"""Which cue wins when several land at once (`static/sound.js` ranks
them the same way): the accent over a refutation over the turn cue
over a door or a passage over a tick. The table plays a door or a
passage beside the batch's loudest rather than under it."""


def loudest_cue(cues):
    """The one cue a batch of events makes, or None if none makes any:
    several at once would be noise (plan 11.1)."""
    heard = [cue for cue in cues if cue in CUE_RANK]
    return max(heard, key=CUE_RANK.__getitem__) if heard else None


def seat_certainty(label: str, belief, obs) -> float:
    """One seat's certainty, 0 to 1 (`clude_agents.character.certainty`,
    Phase 9h): from `belief` through the character's own confidence
    (Peacock's lower bound, everyone else's probabilities) when `label`
    is a character's, and otherwise from the floor alone -- uniform over
    whatever `obs`'s mask has not ruled out, which is what a person or
    the floor bot has to go on."""
    spec = AGENT_SPECS.get(label)
    if spec is not None and belief is not None:
        confidence = spec.confidence_fn(belief)
    else:
        confidence = mask_and_normalize({}, obs.mask)
    return round(certainty(confidence), 4)


def _proven(obs) -> dict:
    """Card -> who is proven to hold it, or None, from the floor mask.

    This is what makes a bar solid rather than pale: not what a method
    guesses, but what the shared deduction floor has established. Every
    seat's own hand is proven to that seat, which is why a block's own
    cards read as settled from the first frame.

    A holder is a seat index **or** `ENVELOPE`, the string ``"envelope"``.
    That second case is the interesting one for the screen: a card proven
    to be the envelope's is the strongest thing a seat can know, and it
    is how a block shows it has solved part of the murder -- not the same
    statement as "nobody at the table has shown it".
    """
    return {card: obs.mask.holder_of(card) for card in ALL_CARDS}


def trace_document(record, every: int = 1) -> dict:
    """Every seat's belief after every suggestion, as a stored document.

    Slow on purpose: this is the whole point of caching. Each seat with a
    method of its own is asked at each `k`; a seat played by a bot with no
    belief method (``floor``, ``random``) contributes its proven cards but
    no probabilities, so its block shows what it knows and claims nothing
    more.

    Parameters
    ----------
    record : GameRecord
    every : int
        Sample after every `every`-th suggestion, as `trace.belief_trace`
        means it. 1 is every suggestion.
    """
    state = state_from_record(record)
    suspects = seat_names(record)
    seats = sorted(record.seats, key=lambda s: s.seat)
    total = len(state.suggestion_log)
    ks = sorted({0, total} | {k for k in range(1, total) if k % every == 0})

    agents = {}
    for seat in seats:
        if seat.label in AGENT_SPECS:
            agent = build_agent(seat.label)
            agent.reset(record.seed)
            agents[seat.seat] = agent

    frames = []
    for k in ks:
        cut = truncate_state(state, k)
        per_seat = []
        for seat in seats:
            obs = clude_constraints.observe(cut, seat.seat)
            agent = agents.get(seat.seat)
            belief = agent.select_action(obs) if agent is not None else None
            per_seat.append(
                {
                    "seat": seat.seat,
                    "probabilities": dict(belief.probabilities) if belief else {},
                    "proven": _proven(obs),
                    "certainty": seat_certainty(seat.label, belief, obs),
                }
            )
        frames.append({"k": k, "seats": per_seat})

    return {
        "version": TRACE_VERSION,
        "run_id": record.run_id,
        "game_index": record.game_index,
        "built": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "every": every,
        "ks": ks,
        "frames": frames,
        "seats": [
            {
                "seat": s.seat,
                "suspect": s.suspect,
                "label": s.label,
                "kind": s.kind,
                "method": seat_method(s.label),
                "hand": sorted(record.hands.get(s.seat, record.hands.get(str(s.seat), []))),
            }
            for s in seats
        ],
        "suspects": suspects,
        "envelope": list(record.envelope),
        "categories": {"suspects": list(SUSPECTS), "weapons": list(WEAPONS), "rooms": list(ROOMS)},
        "limitation": TRACE_LIMITATION,
    }


def cached_trace(store, record, every: int = 1) -> dict:
    """The game's trace, from the store if it is there and current, else
    computed once and written beside the record.

    A document from an older `TRACE_VERSION`, or built with a different
    `every`, is rebuilt rather than trusted.
    """
    key = trace_key(record.run_id, record.game_index)
    try:
        document = store.get_doc(key)
    except (KeyError, ValueError):
        document = None
    if (
        document is not None
        and document.get("version") == TRACE_VERSION
        and document.get("every") == every
    ):
        # Explanatory copy can change without invalidating expensive frames.
        return dict(document, limitation=TRACE_LIMITATION)
    document = trace_document(record, every=every)
    store.put_doc(key, document)
    return document


def screen_payload(record, trace: dict) -> dict:
    """Everything the replay screen needs, in one JSON-ready object.

    The scrubber moves per event and a round trip per step would be both
    slow and pointless, so the whole game goes to the page once and the
    JavaScript redraws from it.

    Token positions are sent as SVG coordinates rather than as rooms and
    squares, which is why this module imports `board_svg`. The
    alternative -- sending nodes and mapping them in JavaScript -- would
    put the board's geometry in a second place, and keeping the drawing
    and the rules in one place is the whole point of generating the board
    from `clude_core.board`.

    Probabilities are rounded and proven entries with no holder are
    dropped, which roughly halves the payload and costs nothing: a bar is
    a few pixels wide.
    """
    from . import board_svg

    frames = event_frames(record)
    return {
        "frames": [
            {
                "i": frame.index,
                "turn": frame.turn,
                "kind": frame.kind,
                "text": frame.text,
                "k": frame.k,
                "cue": frame.cue,
                "door": frame.door,
                "passage": frame.passage,
                "tokens": {
                    suspect: [round(v, 2) for v in point]
                    for suspect, point in board_svg.token_points(frame.positions).items()
                },
            }
            for frame in frames
        ],
        "beliefs": [
            {
                "k": belief["k"],
                "seats": [
                    {
                        "seat": seat["seat"],
                        "p": {
                            card: round(value, 4)
                            for card, value in seat["probabilities"].items()
                        },
                        "proven": {
                            card: holder
                            for card, holder in seat["proven"].items()
                            if holder is not None
                        },
                        "certainty": seat.get("certainty", 0.0),
                    }
                    for seat in belief["seats"]
                ],
            }
            for belief in trace["frames"]
        ],
        "seats": trace["seats"],
        "envelope": trace["envelope"],
        "categories": trace["categories"],
        "limitation": trace["limitation"],
    }


def belief_at(document: dict, k: int) -> dict:
    """The frame at or just before `k`, since a trace may be sampled
    coarsely (`every` > 1) and the scrubber moves per event."""
    frames = document.get("frames") or []
    if not frames:
        return {"k": 0, "seats": []}
    best = frames[0]
    for frame in frames:
        if frame["k"] <= k:
            best = frame
        else:
            break
    return best
