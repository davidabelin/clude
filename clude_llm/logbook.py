"""Render post-game debrief and condensing prompts; resolve opponent identities.

Debrief deliberately sees the whole deal face up plus the seat's live-view
history, audits and prior memory. It writes narrative schema fields, not
code-computed facts. Opponent names map back to persistent roster labels.
Condensing shows a character its digest and the entries since, to fold into
a new digest. See docs/logbooks.md; model calls/validation live in player.py.
"""
from __future__ import annotations

from typing import Optional, Sequence

from clude_agents.explain import describe_suggestion, format_belief, seat_label, seat_labels
from clude_core.events import AccusationEvent, RemarkEvent
from clude_storage import GameRecord, LogbookDigest, LogbookHead
from clude_storage.logbooks import (
    LESSON_WORDS,
    MAX_FLAGS,
    MAX_STANDING_INSTRUCTIONS,
    MAX_THEMES,
    OVERVIEW_WORDS,
    READ_WORDS,
    SUMMARY_WORDS,
    entry_outcome,
    outcome_phrase,
    render_digest,
    render_entry,
    render_head,
    render_index_line,
)
from clude_training.replay import seat_view

from .persona import DISPLAY_NAMES

MAX_AUDIT_LINES = 60
"""Decision lines listed in the debrief before the rest are summarised (a run
of identical decisions is one line)."""


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


AUDIT_KINDS = (
    ("move", "Moves"), ("suggest", "Suggestions"), ("show", "Cards shown"), ("accuse", "Accusation calls"),
)
"""The decision kinds in the order the audit lists them, with headings."""


def _option_notes(decision) -> str:
    """The menu note(s) beside the option(s) the model chose, joined:
    what the model was told about them at the time."""
    options = {o.get("label"): o for o in (getattr(decision, "menu", None) or {}).get("options", [])}
    notes = []
    for label in str(getattr(decision, "chosen", "") or "").split("/"):
        note = (options.get(label) or {}).get("note")
        if note:
            notes.append(note)
    return "; ".join(notes)


def _audit_lines(decisions: Sequence) -> list:
    """The decisions the model was asked, grouped by kind, each with the
    note the menu showed beside the chosen option, and a run of the same
    decision collapsed into one line ("turns 28-98, 37 times running")
    so a stall reads as a stall. What the character said is in the
    table talk and not repeated here."""
    asked = [d for d in decisions if getattr(d, "called", False)]
    singles = sum(1 for d in decisions if not getattr(d, "called", False) and not d.fallback)
    fallbacks = sum(1 for d in decisions if d.fallback)
    lines = []
    if not asked:
        lines.append("  (none: every decision had one option or was your method's alone)")
    runs: list = []  # [kind, text, first turn, last turn, count]
    for d in asked:
        if d.fallback:
            tail = f" -- fell back to your method ({d.fallback})"
        elif d.deviated:
            tail = " -- below your method's top option"
        else:
            tail = ""
        note = _option_notes(d)
        text = f"{d.action or 'your method decided'}{f' [{note}]' if note else ''}{tail}"
        last = next((r for r in reversed(runs) if r[0] == d.kind), None)
        if last is not None and last[1] == text:
            last[3] = d.turn
            last[4] += 1
        else:
            runs.append([d.kind, text, d.turn, d.turn, 1])
    shown = 0
    for kind, heading in AUDIT_KINDS:
        of_kind = [r for r in runs if r[0] == kind]
        if not of_kind or shown >= MAX_AUDIT_LINES:
            continue
        lines.append(f"  {heading}:")
        for _, text, first, last_turn, count in of_kind:
            if shown >= MAX_AUDIT_LINES:
                break
            when = f"turn {first}" if count == 1 else f"turns {first}-{last_turn}, {count} times running"
            lines.append(f"    {when}: {text}")
            shown += 1
    if len(runs) > MAX_AUDIT_LINES:
        lines.append(f"  ... and {len(runs) - MAX_AUDIT_LINES} more.")
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
    digest: Optional[LogbookDigest] = None,
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
        Every earlier entry, ascending; their summaries and flags are shown
        (with a digest, only those after it).
    digest : LogbookDigest or None
        The condensed logbook, shown in place of the entries it folds in.
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
        "The decisions put to you this game, by kind, with what the menu said beside "
        "the option you chose (a repeated decision is one line):",
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
    if digest is not None:
        lines.extend(f"  {line}" for line in render_digest(digest, head))
        entries = [entry for entry in entries if entry.serial > digest.through]
    if entries:
        heading = "Entries since your digest" if digest is not None else "Earlier entries"
        lines.append(f"{heading}, most recent last (summary and flags):")
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
        f"- flags: two to {MAX_FLAGS} short lowercase keywords for the patterns of play that "
        "connect this game to others (not the result or the table size, which the entry "
        "records already); reuse your existing flags where they fit and coin a new one "
        "only for something new.",
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


def condense_prompt(
    identity: str,
    head: LogbookHead,
    digest: Optional[LogbookDigest],
    entries: Sequence,
) -> str:
    """The user prompt that asks `identity`'s model to condense its
    logbook: the previous digest if any, the logbook's standing part as
    context, the entries to fold in whole, the flags in use, and the
    digest's fields.

    Parameters
    ----------
    identity : str
        The character whose logbook this is.
    head : LogbookHead
        The logbook's current head.
    digest : LogbookDigest or None
        The previous digest; `entries` are those after it.
    entries : Sequence[LogbookEntry]
        The entries to fold in, ascending; at least one.
    """
    display = DISPLAY_NAMES.get(identity, identity)
    first, last = entries[0].serial, entries[-1].serial
    lines = [
        f"No game is on. This is a quiet hour with your logbook, {display}: condense it.",
        "You read your logbook back before every game, and it has grown long. Fold entries "
        f"#{first:04d} to #{last:04d} into a digest that will stand in for every entry up to "
        f"#{last:04d}. The entries stay in your archive, but from now on you read the digest in "
        "their place, followed only by the entries written after it.",
        "",
    ]
    if digest is not None:
        lines.append("Your digest so far, which these entries extend:")
        lines.extend(f"  {line}" for line in render_digest(digest, head))
    else:
        lines.append("You have no digest yet: this is your first.")
    head_lines = render_head(head)
    if head_lines:
        lines += [
            "",
            "Shown for context (your standing instructions and your reads on opponents are kept "
            "as they are):",
            *(f"  {line}" for line in head_lines),
        ]
    lines += ["", f"The entries to fold in, #{first:04d} to #{last:04d}:", ""]
    for entry in entries:
        lines += [render_entry(entry), ""]
    if head.flags:
        used = ", ".join(
            f"{flag} ({len(serials)})"
            for flag, serials in sorted(head.flags.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        )
        lines += [f"Flags you have used, with how many entries carry each: {used}.", ""]
    fold = ", folding in your previous overview" if digest is not None else ""
    carry = " from your digest so far and from these entries" if digest is not None else ""
    lines += [
        "Write the digest as JSON with these fields, in your own voice, as notes to yourself:",
        f"- overview: the arc of these games{fold}, in at most {OVERVIEW_WORDS} words: what kind "
        "of player you have been at this table, what has worked and what has cost you.",
        '- flag_map: flags that name the same pattern in different words, each as {"flag": an '
        'old flag exactly as listed above, "into": the flag to keep}. Merge only true '
        "near-duplicates, never two different patterns; an empty list is fine. Merged flags are "
        "rewritten in every entry and in your index, and your later entries reuse the ones you keep.",
        f"- themes: at most {MAX_THEMES}, the patterns that matter most, each headed by one flag "
        f"you keep and carrying one lesson in at most {LESSON_WORDS} words: what to do or avoid, "
        f"and the evidence that taught it. Carry forward what still holds{carry}; drop what did not.",
        f"Your identity in the logbook is {identity}. Answer with JSON only.",
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
