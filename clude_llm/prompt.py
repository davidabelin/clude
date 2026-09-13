"""Prompt text for one decision (Phase 6b).

`system_prompt` is the stable prefix (persona + standing rules), meant
to be cached by the API; `user_prompt` is the per-turn part. The user
prompt is a function of the seat's `ClueObservation`, its `ClueBelief`,
its `Character` (profile and confidence), the `Menu`, and the table talk
it has heard -- never of `GameState` -- so nothing a seat cannot know can
reach the model. The text pieces come from `clude_agents.explain`, the
same lines the maintainer CLI prints.
"""
from __future__ import annotations

from typing import Optional, Sequence

from clude_agents.character import Character
from clude_agents.explain import describe_suggestion, format_belief, format_extra, seat_labels
from clude_constraints import ENVELOPE
from clude_core.domain import ALL_CARDS, SUSPECTS
from clude_core.state import ClueObservation

from .menu import Menu, SuggestionMenu
from .persona import DISPLAY_NAMES, Persona

ANSWER_SHAPES: dict = {
    "suggest": (
        '{"suspect": "<letter>", "weapon": "<letter>", '
        '"say": "<one short line in your voice, or an empty string>"}'
    ),
    "choice": '{"choice": "<letter>", "say": "<one short line in your voice, or an empty string>"}',
}


def system_prompt(persona: Persona, rules: str) -> str:
    """Persona prose, then the standing rules. Byte-stable per character,
    which is what makes it cacheable."""
    return f"{persona.text.strip()}\n\n{rules.strip()}\n"


def _floor_lines(obs: ClueObservation, names: Sequence[str]) -> list:
    mask = obs.mask
    proven = [c for c in ALL_CARDS if mask.holder_of(c) == ENVELOPE]
    located: dict = {}
    unlocated = 0
    for card in ALL_CARDS:
        holder = mask.holder_of(card)
        if holder is None:
            unlocated += 1
        elif holder != ENVELOPE and holder != obs.my_index:
            located.setdefault(holder, []).append(card)
    lines = [f"  Proven in the envelope: {', '.join(proven) if proven else 'nothing yet'}."]
    for holder in sorted(located):
        lines.append(f"  Held by {names[holder]}: {', '.join(located[holder])}.")
    lines.append(f"  Still unlocated: {unlocated} card{'s' if unlocated != 1 else ''}.")
    return lines


def _option_lines(menu: Menu, with_score: bool = True) -> list:
    lines = []
    for option in menu.options:
        if not option.allowed:
            continue
        tail = []
        if with_score:
            tail.append(f"score {option.score:.2f}")
        if option.note:
            tail.append(option.note)
        suffix = f" -- {'; '.join(tail)}" if tail else ""
        lines.append(f"  {option.label}. {option.text}{suffix}")
    return lines


def _menu_lines(menu) -> list:
    if isinstance(menu, SuggestionMenu):
        return [
            "Suspect options (best first by your method's score; choose one letter):",
            *_option_lines(menu.suspect),
            "Weapon options (best first; choose one letter):",
            *_option_lines(menu.weapon),
        ]
    if menu.kind == "accuse":
        return ["Options (choose one letter):", *_option_lines(menu, with_score=False)]
    return ["Options (best first by your method's score; choose one letter):", *_option_lines(menu)]


def user_prompt(
    obs: ClueObservation,
    belief,
    character: Character,
    menu,
    remarks: Sequence = (),
    names: Optional[Sequence[str]] = None,
    recent_remarks: int = 8,
) -> str:
    """The per-turn prompt for one decision.

    Parameters
    ----------
    obs : ClueObservation
        The deciding seat's masked view (`clude_constraints.observe`).
    belief : ClueBelief
        That seat's belief for `obs` (`character.select_action(obs)`).
    character : Character
        For the display name, the accusation test and the bluff rate.
    menu : Menu or SuggestionMenu
    remarks : Sequence[tuple[int, str]]
        ``(seat, text)`` table talk so far, oldest first; the last
        `recent_remarks` are shown.
    names : Sequence[str] or None
        A label per seat; default the suspect tokens (`seat_labels`).

    Raises
    ------
    ValueError
        If `obs.mask` is None.
    """
    if obs.mask is None:
        raise ValueError(
            "the LLM prompt needs a masked observation: run the game with "
            "`observer=clude_constraints.observe`"
        )
    names = list(names) if names is not None else seat_labels(SUSPECTS[: obs.n_players])
    me = names[obs.my_index]
    display = DISPLAY_NAMES.get(character.name, character.name)
    token = SUSPECTS[obs.my_index]
    who = (
        f"You are {display}, seat {me}."
        if token == character.name
        else f"You are {display}, playing the {token} token as seat {me}."
    )
    table = ", ".join(n + ("" if active else " (out)") for n, active in zip(names, obs.active_players))
    triple, p = character.accusation_test(obs)
    threshold = character.profile.accuse_threshold

    lines = [
        f"{who} Turn {obs.turn}.",
        f"At the table: {table}.",
        f"Your hand: {', '.join(sorted(obs.own_hand))}.",
        "",
        "What is certain (the shared deduction floor):",
        *_floor_lines(obs, names),
        "",
        "What your method believes (top cards per category; * = proven):",
        f"  {format_belief(belief.probabilities, obs.mask, top=3)}",
    ]
    extra = format_extra(belief)
    if extra:
        lines.append(f"  {extra}")
    if p > 0.0:
        best = f"{'/'.join(triple)} with P(correct) {p:.2f}"
    else:
        best = "nothing stands out yet (P(correct) 0.00)"  # a zero product's triple is a tie-break, not a view
    lines.append(f"  Best accusation by your numbers: {best}; your accusation threshold is {threshold:.2f}.")
    lines.append("")
    if obs.suggestion_log:
        lines.append("Suggestions so far, as you saw them:")
        for k, suggestion in enumerate(obs.suggestion_log, start=1):
            lines.append(f"  {k}. {describe_suggestion(suggestion, names)}")
    else:
        lines.append("No suggestions have been made yet.")
    if obs.accusation_log:
        lines.append("Accusations so far:")
        for accusation in obs.accusation_log:
            verdict = "correct" if accusation.correct else "wrong, out of the game"
            lines.append(
                f"  {names[accusation.accuser]} accused "
                f"{accusation.suspect}/{accusation.weapon}/{accusation.room}: {verdict}"
            )
    if remarks:
        lines.append("")
        lines.append("Table talk, most recent last:")
        for seat, text in list(remarks)[-recent_remarks:]:
            lines.append(f'  {names[seat]}: "{text}"')
    if isinstance(menu, SuggestionMenu):
        title = f"{menu.suspect.title} and {menu.weapon.title}"
    else:
        title = menu.title
    lines.append("")
    lines.append(f"Decision: {title}.")
    lines.extend(_menu_lines(menu))
    if isinstance(menu, SuggestionMenu) and any(
        o.allowed and o.note.startswith("in your own hand")
        for o in (*menu.suspect.options, *menu.weapon.options)
    ):
        lines.append(
            f"Your bluff rate is {character.profile.bluff_rate:.2f}: how often you name a card "
            "from your own hand."
        )
    shape = ANSWER_SHAPES["suggest" if isinstance(menu, SuggestionMenu) else "choice"]
    lines.append(f"Answer with JSON only: {shape}")
    return "\n".join(lines) + "\n"
