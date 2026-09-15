"""The debrief (Phase 7c): after a game, an LLM-piloted character writes
its own logbook entry.

`debrief_prompt` renders what the character is told, in the same voice
as the in-game prompt but with the game over: the outcome, its hand,
the whole deal face up (David's decision 1: a post-mortem with cards on
the table, so a tell can be checked against the truth), the
suggestions as it saw them live, the table talk, the decisions the
model was asked to make (with deviations and fallbacks marked), its
final belief against the envelope, its logbook so far (the head and an
index of earlier entries, so flags get reused and entries connect), and
the instructions for each field of `LOGBOOK_SCHEMA` with the bounds
`clude_storage.logbooks` enforces. The system prompt is the character's
persona + rules block unchanged, so the API cache hits; the request
carries no memory block, since the logbook is in the prompt itself.

`resolve_opponents` maps whatever the model called an opponent ("Mrs.
Peacock", "the Scarlett token", ``P2 White (Green)``) to the roster
label the logbook keys dossiers by. `LLMCharacter.debrief` does the
call and the write.

This module sits above `clude_training.replay` (for the seat's live
view); `clude_training.arena` sits above both.
"""
from __future__ import annotations

from typing import Optional, Sequence

from clude_agents.explain import describe_suggestion, format_belief, seat_label, seat_labels
from clude_core.events import AccusationEvent, RemarkEvent
from clude_storage import GameRecord, LogbookHead
from clude_storage.logbooks import (
    MAX_FLAGS,
    MAX_STANDING_INSTRUCTIONS,
    READ_WORDS,
    SUMMARY_WORDS,
    entry_outcome,
    outcome_phrase,
    render_head,
    render_index_line,
)
from clude_training.replay import seat_view

from .persona import DISPLAY_NAMES

MAX_AUDIT_LINES = 60
"""Decisions listed in the debrief before the rest are summarised."""


def _table_names(record: GameRecord) -> list:
    seats = sorted(record.seats, key=lambda s: s.seat)
    return seat_labels([s.suspect for s in seats], [s.label for s in seats])


def opponent_aliases(record: GameRecord, seat: int) -> dict:
    """Every way the model might name an opponent, lower-cased, mapped to
    the roster label the logbook uses: the label, its display name, the
    token it played and that token's display name, and the seat label."""
    aliases: dict = {}
    seats = sorted(record.seats, key=lambda s: s.seat)
    suspects = [s.suspect for s in seats]
    labels = [s.label for s in seats]
    for s in seats:
        if s.seat == seat:
            continue
        names = {
            s.label,
            DISPLAY_NAMES.get(s.label, ""),
            s.suspect,
            DISPLAY_NAMES.get(s.suspect, ""),
            f"P{s.seat}",
            f"P{s.seat} {s.suspect}",
            seat_label(suspects, s.seat, labels),
        }
        for name in names:
            if name:
                aliases.setdefault(name.strip().lower(), s.label)
    return aliases


def resolve_opponents(written: dict, record: GameRecord, seat: int) -> dict:
    """A copy of the model's JSON with every ``opponent`` field in
    `evaluations` and `dossiers` resolved to a roster label where an
    alias matches; unknown names are left as written (and dropped by
    `LogbookEntry.build`)."""
    aliases = opponent_aliases(record, seat)
    out = dict(written or {})
    for field in ("evaluations", "dossiers"):
        items = []
        for item in out.get(field) or []:
            if isinstance(item, dict):
                item = dict(item)
                name = item.get("opponent")
                if isinstance(name, str):
                    item["opponent"] = aliases.get(name.strip().lower(), name.strip())
            items.append(item)
        out[field] = items
    return out


def _deal_lines(record: GameRecord, seat: int, names: Sequence[str]) -> list:
    lines = []
    for other in range(record.n_players):
        if other == seat:
            continue
        cards = sorted(record.hands.get(other, []))
        lines.append(f"  {names[other]} held: {', '.join(cards) if cards else 'nothing'}.")
    return lines


def _audit_lines(decisions: Sequence) -> list:
    asked = [d for d in decisions if getattr(d, "called", False)]
    singles = sum(1 for d in decisions if not getattr(d, "called", False) and not d.fallback)
    fallbacks = sum(1 for d in decisions if d.fallback)
    lines = []
    if not asked:
        lines.append("  (none: every decision had one option or was your method's alone)")
    for d in asked[:MAX_AUDIT_LINES]:
        if d.fallback:
            tail = f" -- fell back to your method ({d.fallback})"
        elif d.deviated:
            tail = " -- below your method's top option"
        else:
            tail = ""
        said = f' and said "{d.said}"' if d.spoke and d.said else ""
        lines.append(f"  turn {d.turn} {d.kind}: {d.action or 'your method decided'}{tail}{said}")
    if len(asked) > MAX_AUDIT_LINES:
        lines.append(f"  ... and {len(asked) - MAX_AUDIT_LINES} more.")
    lines.append(
        f"  ({len(decisions)} decisions in all: {singles} with a single option, "
        f"{len(asked)} put to you, {fallbacks} decided by your method after a fallback.)"
    )
    return lines


def debrief_prompt(
    record: GameRecord,
    seat: int,
    character,
    decisions: Sequence,
    head: LogbookHead,
    entries: Sequence,
) -> str:
    """The debrief's user prompt for `seat`'s character.

    Parameters
    ----------
    record : GameRecord
        The finished game, omniscient.
    seat : int
        The character's seat.
    character : Character
        The headless character, for its name, final belief and threshold.
    decisions : Sequence[Decision]
        The wrapper's audit of this game.
    head : LogbookHead
        The logbook's current head.
    entries : Sequence[LogbookEntry]
        Every earlier entry, ascending; their summaries and flags are shown.
    """
    seats = sorted(record.seats, key=lambda s: s.seat)
    names = _table_names(record)
    me = names[seat]
    label = seats[seat].label
    token = seats[seat].suspect
    display = DISPLAY_NAMES.get(character.name, character.name)
    opponents: list = []
    for s in seats:
        if s.seat != seat and s.label not in opponents:
            opponents.append(s.label)
    view = seat_view(record, seat)
    belief = character.select_action(view)
    triple, p = character.accusation_test(view)
    envelope = "/".join(record.envelope)
    outcome = entry_outcome(record, seat)
    game_id = f"{record.run_id}/{record.game_index:05d}"
    date = record.created_at[:10] if record.created_at else "today"

    lines = [
        f"The game is over. This is your debrief, {display}: write your logbook entry.",
        f"You played the {token} token as seat {me}, in game {game_id} on {date}.",
        f"At the table: {', '.join(names)}. Name opponents by their roster label: "
        f"{', '.join(opponents)}.",
        f"Outcome: you {outcome_phrase(outcome)}. The envelope was {envelope}.",
    ]
    if outcome.get("accused"):
        verdict = "correct" if outcome.get("accusation_correct") else "wrong"
        lines.append(f"You accused {'/'.join(outcome['accusation'])}: {verdict}.")
    lines += [
        "",
        f"Your hand: {', '.join(sorted(record.hands.get(seat, [])))}.",
        "The deal, face up now that the game is over (nothing here carries into the next "
        "deal; what people said about their hands can now be checked):",
        *_deal_lines(record, seat, names),
        "",
    ]
    if view.suggestion_log:
        lines.append("Suggestions, as you saw them during the game:")
        for k, suggestion in enumerate(view.suggestion_log, start=1):
            lines.append(f"  {k}. {describe_suggestion(suggestion, names)}")
    else:
        lines.append("No suggestions were made.")
    accusations = [e.accusation for e in record.events if isinstance(e, AccusationEvent)]
    if accusations:
        lines.append("Accusations:")
        for a in accusations:
            lines.append(
                f"  {names[a.accuser]} accused {a.suspect}/{a.weapon}/{a.room}: "
                f"{'correct' if a.correct else 'wrong, out of the game'}"
            )
    remarks = [e for e in record.events if isinstance(e, RemarkEvent)]
    lines.append("")
    if remarks:
        lines.append("Table talk, in order (your own lines marked):")
        for r in remarks:
            you = " (you)" if r.seat == seat else ""
            lines.append(f'  turn {r.turn} {names[r.seat]}{you}: "{r.text}"')
    else:
        lines.append("Nobody spoke at the table.")
    lines += [
        "",
        "The decisions put to you this game:",
        *_audit_lines(decisions),
        "",
        "Your final belief against the truth:",
        f"  {format_belief(belief.probabilities, view.mask, top=3)}",
        f"  Best triple by your numbers: {'/'.join(triple)} with P(correct) {p:.2f} against your "
        f"threshold {character.profile.accuse_threshold:.2f}; the envelope was {envelope}.",
        "",
        "Your logbook so far:",
    ]
    head_lines = render_head(head, opponents)
    if head_lines:
        lines.extend(f"  {line}" for line in head_lines)
    else:
        lines.append("  Empty: this is your first entry.")
    if entries:
        lines.append("Earlier entries, most recent last (summary and flags):")
        lines.extend(f"  {render_index_line(entry)}" for entry in entries)
    if head.flags:
        used = ", ".join(
            f"{flag} ({len(serials)})"
            for flag, serials in sorted(head.flags.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        )
        lines.append(f"Flags you have used: {used}.")
    lines += [
        "",
        "Write the entry as JSON with these fields, in your own voice, as notes to yourself "
        "and not to the table:",
        "- title: a short title for this game.",
        f"- summary: one or two sentences, at most {SUMMARY_WORDS} words, on what to remember "
        "of it.",
        f"- flags: two to {MAX_FLAGS} short lowercase keywords that connect this game to "
        "others; reuse your existing flags where they fit and coin a new one only for "
        "something new.",
        "- what_happened: the game as you experienced it, in a paragraph.",
        "- evaluations: one per opponent at the table, with an evaluation of how they played "
        "and notes on what gave them away, if anything, now that you can check their claims "
        "against the deal.",
        "- key_insights and lessons_learned: short lists, specific to what happened.",
        "- final_outcome: the result in your words.",
        f"- standing_instructions: your standing instructions to yourself, the whole list "
        f"rewritten, at most {MAX_STANDING_INSTRUCTIONS}, each one sentence: carry forward what "
        "still holds, drop what did not, add what this game taught.",
        f"- dossiers: for each opponent whose read you want to revise, their label and your "
        f"read of them in at most {READ_WORDS} words; leave an opponent out to keep the read "
        "you have.",
        f"Your identity in the logbook is {label}. Answer with JSON only.",
    ]
    return "\n".join(lines) + "\n"


def opponents_of(table: Sequence[str], identity: str) -> Optional[list]:
    """The other labels at a table, de-duplicated in seat order; None
    for no table (every dossier is then shown)."""
    if not table:
        return None
    seen: list = []
    for label in table:
        if label != identity and label not in seen:
            seen.append(label)
    return seen
