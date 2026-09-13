"""Menus: the scored, leashed list of legal options for one decision
(Phase 6b).

A menu is built from the wrapped `Character`'s own numbers, never from
`GameState`: the legal `MoveChoice`s the engine offered, scored by the
character's `movement_scores`; the honest suggestion candidates and
their belief; the refutation candidates the engine computed from ground
truth, scored by `secrecy`; the accusation test. Building one draws
nothing from any RNG, so a wrapper that falls back to the character's
sampled decision leaves the character's RNG stream exactly where the
headless character would have had it.

The leash: an option is `allowed` when its score is at least
``(1 - leash)`` of the best score, so `leash = 0` admits only the
character's best (and its ties) and `leash = 1` admits every legal
option. Two exceptions, both from docs/phase6-plan.md: own-hand cards
are listed in the suggestion menu as bluff options and allowed whenever
the character has any rope and any `bluff_rate` at all; and the
accusation menu applies the leash symmetrically around
`accuse_threshold` (see `accusation_menu`).

Options come best first, labelled ``A``, ``B``, ... (`schema.LABELS`),
and capped at `MAX_OPTIONS`. A Phase 8 human seat is meant to be shown
this same object.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from clude_agents.character import Character, cards_exposed, show_scores, suggestion_candidates
from clude_agents.features import ChoiceFeatures
from clude_constraints import ENVELOPE
from clude_core.board import HallwayCell
from clude_core.domain import SUSPECTS, WEAPONS
from clude_core.state import ClueObservation

from .schema import LABELS, MAX_OPTIONS

KINDS = ("move", "suggest", "accuse", "show")
EPS = 1e-12


@dataclass(frozen=True)
class Option:
    """One legal option: its `label`, the `action` to hand the engine
    (a `MoveChoice`, a card name, an accusation triple, or None for a
    pass), the character's `score` for it, a one-line `text`, a `note`
    with the numbers behind it, and whether the leash `allowed` it."""

    label: str
    action: Any
    score: float
    text: str
    note: str = ""
    allowed: bool = True

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "text": self.text,
            "score": round(self.score, 4),
            "note": self.note,
            "allowed": self.allowed,
        }


@dataclass(frozen=True)
class Menu:
    """The options for one decision, best first. `top` is the option the
    headless character would take greedily (for the accusation menu, its
    threshold answer)."""

    kind: str
    title: str
    options: tuple
    top: Option
    leash: float

    def allowed(self) -> tuple:
        return tuple(o for o in self.options if o.allowed)

    def single(self) -> Optional[Option]:
        """The sole allowed option, if exactly one is; else None."""
        allowed = self.allowed()
        return allowed[0] if len(allowed) == 1 else None

    def option(self, label: str) -> Optional[Option]:
        for candidate in self.options:
            if candidate.label == label:
                return candidate
        return None

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "title": self.title,
            "leash": self.leash,
            "top": self.top.label,
            "options": [o.to_dict() for o in self.options],
        }


@dataclass(frozen=True)
class SuggestionMenu:
    """The suggestion's two menus, one per slot the character picks (the
    room is the engine's)."""

    suspect: Menu
    weapon: Menu
    kind: str = "suggest"

    def single(self) -> Optional[tuple]:
        """Both slots' sole allowed options, if each has exactly one."""
        s, w = self.suspect.single(), self.weapon.single()
        return (s, w) if s is not None and w is not None else None

    def to_dict(self) -> dict:
        return {"kind": self.kind, "suspect": self.suspect.to_dict(), "weapon": self.weapon.to_dict()}


def within_leash(scores: list, leash: float) -> list:
    """Which of `scores` are at least ``(1 - leash)`` of the best."""
    cutoff = (1.0 - leash) * max(scores)
    return [s >= cutoff - EPS for s in scores]


def _require_mask(obs: ClueObservation) -> None:
    if obs.mask is None:
        raise ValueError(
            "an LLM menu needs a masked observation: run the game with "
            "`observer=clude_constraints.observe`"
        )


def _build(kind: str, title: str, entries: list, leash: float) -> Menu:
    """Rank unlabelled entries best first (stable, so ties keep their
    input order), label them, cap at `MAX_OPTIONS`."""
    ranked = sorted(entries, key=lambda o: -o.score)
    options = tuple(
        Option(LABELS[i], o.action, o.score, o.text, o.note, o.allowed)
        for i, o in enumerate(ranked[:MAX_OPTIONS])
    )
    return Menu(kind, title, options, options[0], leash)


def _leash_of(character: Character, leash: Optional[float]) -> float:
    return character.profile.leash if leash is None else leash


# -- movement ----------------------------------------------------------------


def _node_text(node) -> str:
    if isinstance(node, HallwayCell):
        return f"the hallway between the {node.room_a} and the {node.room_b}"
    return f"the {node}"


def _move_text(f: ChoiceFeatures) -> str:
    choice = f.choice
    if choice.kind == "stay":
        return f"stay in {_node_text(choice.destination)}" if f.room else "stay put (boxed in)"
    if choice.kind == "secret_passage":
        return f"take the secret passage to the {choice.destination}"
    if f.room:
        return f"enter the {f.room}"
    steps = f.steps_to_target
    plural = "s" if steps != 1 else ""
    return f"move to {_node_text(choice.destination)}, {steps} step{plural} from the {f.target}"


def _move_note(f: ChoiceFeatures, belief) -> str:
    p = belief.probabilities.get(f.target, 0.0)
    where = "a suggestion there this turn" if f.room else f"heading for the {f.target}"
    return f"{where}; P(envelope room = {f.target}) {p:.2f}"


def movement_menu(
    character: Character, obs: ClueObservation, choices: list, leash: Optional[float] = None
) -> Menu:
    """The legal moves, scored by the character's curiosity blend."""
    _require_mask(obs)
    leash = _leash_of(character, leash)
    features, scores = character.movement_scores(obs, choices)
    belief = character.select_action(obs)
    entries = [
        Option("", f.choice, s, _move_text(f), _move_note(f, belief), a)
        for f, s, a in zip(features, scores, within_leash(scores, leash))
    ]
    return _build("move", "where to move", entries, leash)


# -- suggestion --------------------------------------------------------------


def _card_note(card: str, obs: ClueObservation, belief) -> str:
    holder = obs.mask.holder_of(card)
    if holder == ENVELOPE:
        return "proven to be in the envelope"
    if holder is not None:
        return f"located: held by P{holder}"
    return f"P(envelope) {belief.probabilities[card]:.2f}"


def suggestion_menu(
    character: Character, obs: ClueObservation, leash: Optional[float] = None
) -> SuggestionMenu:
    """Suspect and weapon menus: the honest candidates scored by belief,
    plus the character's own cards as bluff options (allowed only with
    some rope and a nonzero `bluff_rate`)."""
    _require_mask(obs)
    leash = _leash_of(character, leash)
    belief = character.select_action(obs)
    bluffs_open = leash > 0.0 and character.profile.bluff_rate > 0.0
    menus = []
    for category, title in ((SUSPECTS, "the suspect to name"), (WEAPONS, "the weapon to name")):
        candidates, scores = suggestion_candidates(obs, belief, category)
        entries = [
            Option("", c, s, f"name {c}", _card_note(c, obs, belief), a)
            for c, s, a in zip(candidates, scores, within_leash(scores, leash))
        ]
        for card in category:
            if card in obs.own_hand:
                entries.append(
                    Option("", card, 0.0, f"name {card}", "in your own hand: naming it is a bluff", bluffs_open)
                )
        menus.append(_build("suggest", title, entries, leash))
    return SuggestionMenu(menus[0], menus[1])


# -- accusation --------------------------------------------------------------


def accusation_menu(character: Character, obs: ClueObservation, leash: Optional[float] = None) -> Menu:
    """``[accuse the best triple, pass]`` under the symmetric leash of
    docs/phase6-plan.md: accusing is allowed once P(correct) reaches
    ``(1 - leash) * accuse_threshold``, passing whenever P is below the
    threshold or there is any rope at all. At `leash = 0` exactly the
    headless answer is allowed."""
    _require_mask(obs)
    leash = _leash_of(character, leash)
    triple, p = character.accusation_test(obs)
    threshold = character.profile.accuse_threshold
    suspect, weapon, room = triple
    accuse = Option(
        "A", triple, p,
        f"accuse {suspect} with the {weapon} in the {room}",
        f"your P(correct) {p:.2f} against your threshold {threshold:.2f}",
        p >= (1.0 - leash) * threshold - EPS,
    )
    pass_ = Option("B", None, 0.0, "accuse no one this turn", "", p < threshold or leash > 0.0)
    top = accuse if p >= threshold else pass_
    return Menu("accuse", "whether to accuse", (accuse, pass_), top, leash)


# -- card to show ------------------------------------------------------------


def show_menu(
    character: Character,
    obs: ClueObservation,
    candidates: list,
    shown_to: int,
    leash: Optional[float] = None,
) -> Menu:
    """The cards the engine says this seat may show, scored by `secrecy`.
    `candidates` is the engine's ground-truth list; nothing outside it
    can ever be an option, which is the reveal-integrity rule."""
    leash = _leash_of(character, leash)
    shown_to_this, shown_to_anyone = cards_exposed(obs, shown_to)
    scores = show_scores(candidates, shown_to_this, shown_to_anyone, character.profile.secrecy)

    def note(card: str) -> str:
        if card in shown_to_this:
            return "already shown to this player"
        if card in shown_to_anyone:
            return "already shown to someone else"
        return "never shown to anyone"

    entries = [
        Option("", c, s, f"show {c}", note(c), a)
        for c, s, a in zip(candidates, scores, within_leash(scores, leash))
    ]
    return _build("show", f"which card to show P{shown_to}", entries, leash)
