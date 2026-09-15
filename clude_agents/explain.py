"""Plain-text views of what one seat knows and believes (Phase 6a).

Every function here is a pure function of a `ClueObservation`, a
`ClueBelief`, a `Character`, a `ConstraintResult`, or a list of seat
labels -- never of `GameState` -- so the same text can be printed by the
maintainer CLI (`trace`, `floor`, `play --verbose`), put in front of an
LLM (`clude_llm`, which must never be shown anything its seat cannot
see), and later shown to a human player. Lifted out of
`scripts/clude_cli.py`, where these started as private helpers.

Seat labels are plain strings, one per seat index, built with
`seat_labels`: ``P1 Mustard``, or ``P1 Mustard (Plum)`` when Plum's
method is piloting the Mustard token. `ClueObservation.suspects` names
the token in each seat, so a caller with only an observation can build
them.
"""
from __future__ import annotations

from typing import Optional, Sequence

from clude_constraints import ENVELOPE
from clude_core.domain import ROOMS, SUSPECTS, WEAPONS, Suggestion

from .base import ClueBelief
from .character import Character, best_triple

CATEGORY_TAGS = (("S", SUSPECTS), ("W", WEAPONS), ("R", ROOMS))
"""One-letter tags for the three categories, in the order text shows them."""


def seat_label(suspects: Sequence[str], seat: int, labels: Optional[Sequence[str]] = None) -> str:
    """``P2 White``, or ``P2 White (Plum)`` when a different occupant
    (`labels[seat]`) is piloting the White token."""
    text = f"P{seat} {suspects[seat]}"
    if labels is not None and labels[seat] != suspects[seat]:
        text += f" ({labels[seat]})"
    return text


def seat_labels(suspects: Sequence[str], labels: Optional[Sequence[str]] = None) -> list:
    """`seat_label` for every seat, in seat order."""
    return [seat_label(suspects, seat, labels) for seat in range(len(suspects))]


def describe_suggestion(suggestion: Suggestion, names: Sequence[str], turn: Optional[int] = None) -> str:
    """One line for a suggestion, as whoever's observation it came from
    sees it: the card shown is named only if `suggestion.card_shown`
    was left visible for that viewer.

    Parameters
    ----------
    suggestion : Suggestion
    names : Sequence[str]
        A label per seat index (`seat_labels`).
    turn : int or None
        Prefixes ``turn N:`` when given.
    """
    who = names[suggestion.suggester]
    cards = f"{suggestion.suspect}/{suggestion.weapon}/{suggestion.room}"
    if suggestion.refuter is None:
        outcome = "nobody could refute"
    elif suggestion.card_shown is not None:
        outcome = f"{names[suggestion.refuter]} showed {suggestion.card_shown}"
    else:
        outcome = f"{names[suggestion.refuter]} showed a card (hidden)"
    prefix = f"turn {turn}: " if turn is not None else ""
    return f"{prefix}{who} suggests {cards} -- {outcome}"


def format_belief(probabilities: dict, mask, top: int = 3, all_cards: bool = False) -> str:
    """Per category: the still-possible cards by descending probability
    (the `top` of them unless `all_cards`), or ``Card*`` once the floor
    has proven that category's envelope card."""
    parts = []
    for tag, category in CATEGORY_TAGS:
        proven = next((c for c in category if mask.holder_of(c) == ENVELOPE), None)
        if proven is not None:
            parts.append(f"{tag}: {proven}*")
            continue
        ranked = sorted(
            (c for c in category if mask.is_possible(c, ENVELOPE)),
            key=lambda c: -probabilities[c],
        )
        if not all_cards:
            ranked = ranked[:top]
        parts.append(f"{tag}: " + " ".join(f"{c} {probabilities[c]:.2f}" for c in ranked))
    return "  |  ".join(parts)


def format_extra(belief: ClueBelief) -> str:
    """The method-specific diagnostics an agent put in `ClueBelief.extra`,
    compactly: Plum's exact/sampled path, Green's chosen arm, Peacock's
    belief/plausibility bounds for her top card per category. Empty for
    methods that report nothing extra."""
    extra = belief.extra
    if "method" in extra:
        if extra["method"] == "exact":
            return f"[exact: {extra['completions']} deals, {extra['nodes']} nodes]"
        if extra["method"] == "sampled":
            return (
                f"[sampled: {extra['valid_samples']} valid samples, "
                f"budget hit at {extra['nodes']} nodes]"
            )
        return "[resolved]"
    if "selected_arm" in extra:
        return f"[arm: {extra['selected_arm']}]"
    if "belief" in extra and "plausibility" in extra:
        pieces = []
        for tag, category in CATEGORY_TAGS:
            top_card = max(category, key=lambda c: belief.probabilities[c])
            if top_card in extra["belief"]:
                pieces.append(
                    f"{tag} {extra['belief'][top_card]:.2f}/{extra['plausibility'][top_card]:.2f}"
                )
        return "[bel/pl of top: " + " ".join(pieces) + "]" if pieces else ""
    return ""


def format_accusation_test(character: Character, belief: ClueBelief) -> str:
    """``[P(correct)=0.42 <0.90]``: the character's confidence in its
    best triple against its accusation threshold; ``>=`` means it would
    accuse here."""
    _triple, confidence = best_triple(character.confidence_fn(belief))
    threshold = character.profile.accuse_threshold
    op = ">=" if confidence >= threshold else "<"
    return f"[P(correct)={confidence:.2f} {op}{threshold:.2f}]"


def format_mask(mask, n_players: int) -> str:
    """The floor's card x holder grid: ``#`` located, ``x`` still
    possible, ``.`` ruled out; one column per seat plus ``Env``."""
    holders = list(range(n_players)) + [ENVELOPE]
    head = f"{'card':<14}" + "".join(
        f"{('Env' if h == ENVELOPE else 'P' + str(h)):>5}" for h in holders
    )
    lines = [head]
    for _tag, category in CATEGORY_TAGS:
        for card in category:
            located = mask.holder_of(card)
            cells = []
            for h in holders:
                if located is not None:
                    cells.append("#" if h == located else ".")
                else:
                    cells.append("x" if mask.is_possible(card, h) else ".")
            lines.append(f"{card:<14}" + "".join(f"{cell:>5}" for cell in cells))
    return "\n".join(lines)
