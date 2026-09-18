"""What the replay screen needs from a stored game, in two halves.

The halves are split by cost, because that is the only thing that
matters here (`docs/phase8.1-plan.md` 2):

- **Cheap, per request.** `event_frames` folds the event log once, giving
  the board after every event and the line that describes it. This is
  the scrubber's spine, and a fold over a few hundred events costs
  nothing.
- **Slow, cached once.** `trace_document` asks every seat's own method
  what it believed after every suggestion. Measured on the grid records:
  a 4-seat, 28-suggestion game takes 8.7 s and a 3-seat game with Plum
  in it 11.9 s -- far too slow for a request, though not the minute the
  plan first estimated. It is computed once and stored beside the record
  as ``traces/<run_id>/<index>.json``; served, that is 10.4 s on the
  first open of a replay and 0.04 s on every one after.

One honest limitation, to be shown on the screen rather than hidden: a
trace calls `select_action` on a fresh agent and never `observe`, so for
White and Green, who learn from what they see, the replayed bar is a
stateless reading of the evidence rather than exactly what they believed
live. Fixing that is out of scope for 8.1.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import clude_constraints
from clude_agents import AGENT_SPECS, build_agent
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

TRACE_VERSION = 1
"""Bumped when the cached document's shape changes, so a stale cache is
rebuilt rather than misread."""

TRACE_LIMITATION = (
    "White's and Green's bars are a stateless reading of the evidence, not "
    "exactly what they believed live: a trace never replays what they learned "
    "along the way."
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
    """

    index: int
    turn: int
    kind: str
    text: str
    positions: dict
    k: int


def suggestion_line(suggestion, suspects) -> str:
    """One suggestion as a sentence, refutation included.

    `clude_agents.explain.describe_suggestion` says the same thing as
    ``White/Rope/Lounge -- Scarlett showed White``, which is right for a
    terminal column and wrong for a line of prose under a board. The
    audience differs, so the wording does; the facts are identical.

    A record is omniscient, so the card shown is named. That is the point
    of a post-game replay -- live, only the two seats involved saw it.
    """
    line = (
        f"{suspects[suggestion.suggester]} suggests {suggestion.suspect} "
        f"with the {suggestion.weapon} in the {suggestion.room}."
    )
    if suggestion.refuter is None:
        return f"{line} Nobody could disprove it."
    refuter = suspects[suggestion.refuter]
    if suggestion.card_shown:
        return f"{line} {refuter} showed {suggestion.card_shown}."
    return f"{line} {refuter} disproved it."


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
    frames = []
    k = 0

    for index, event in enumerate(record.events):
        kind, text = "", ""
        if isinstance(event, MoveEvent):
            positions[suspects[event.player]] = event.destination
            kind = "move"
            where = event.destination
            where = where if isinstance(where, str) else "the corridor"
            by = " by the secret passage" if event.used_secret_passage else ""
            text = f"{suspects[event.player]} moves to {where}{by}."
        elif isinstance(event, SuggestionEvent):
            suggestion = event.suggestion
            k += 1
            if suggestion.suspect in positions:
                positions[suggestion.suspect] = suggestion.room
            kind = "suggestion"
            text = suggestion_line(suggestion, suspects)
        elif isinstance(event, AccusationEvent):
            accusation = event.accusation
            kind = "accusation"
            verdict = "and is right" if accusation.correct else "and is wrong"
            text = (
                f"{suspects[accusation.accuser]} accuses {accusation.suspect} "
                f"with the {accusation.weapon} in the {accusation.room}, {verdict}."
            )
        elif isinstance(event, RemarkEvent):
            kind = "remark"
            text = f"{suspects[event.seat]}: “{event.text}”"
        elif isinstance(event, GameOverEvent):
            kind = "over"
            suspect, weapon, room = event.solution
            who = suspects[event.winner] if event.winner is not None else None
            text = (
                f"{who} wins. " if who else "Nobody wins. "
            ) + f"It was {suspect} with the {weapon} in the {room}."
        else:  # a new event type should show up, not vanish
            kind = "other"
            text = type(event).__name__

        frames.append(
            EventFrame(
                index=index,
                turn=getattr(event, "turn", 0),
                kind=kind,
                text=text,
                positions=dict(positions),
                k=k,
            )
        )
    return frames


def seat_method(label: str) -> str:
    """The human name of the method behind a seat, for its block's
    subtitle. A bot seat has none."""
    spec = AGENT_SPECS.get(label)
    return getattr(spec, "description", "") if spec else ""


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
        return document
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
