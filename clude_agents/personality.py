"""Personality profiles: the numeric dials that turn a character's
belief into choices (Phase 5c), the two Phase 6 dials that govern how
an LLM pilots the same character, and the Phase 7 dial that sets how
much of its own logbook it reads back before a game.

A `Profile` is all-numeric and slider-ready. Each dial owns exactly one
engine decision and is meant to move exactly one arena metric
(docs/phase5-plan.md, section 3); a dial that fails to move its metric
monotonically in a sweep gets cut, not tuned.

| Dial | Decision | Meaning | Metric it should move |
|---|---|---|---|
| `accuse_threshold` | accusation | accuse once P(correct) reaches this | wrong-accusation rate, turn of first accusation |
| `bluff_rate` | suggestion | P(naming one of my own cards instead of an honest pick) | own cards named in suggestions |
| `curiosity` | movement | 1 = chase the most probable room, 0 = enter the nearest room | (with the rest) win rate |
| `secrecy` | card to show | 1 = re-show what this player has already seen, 0 = indifferent | own cards leaked |
| `temperature` | all three sampled decisions | softmax temperature over scores in [0, 1]; 0 = greedy | win rate (down as it rises) |
| `leash` | every LLM-piloted decision (Phase 6) | how far below its method's best-scored option an LLM character may pick: 0 = only the headless pick, 1 = any legal option; also widens the accusation window symmetrically around `accuse_threshold` | deviation rate; wrong-accusation rate against the headless twin |
| `chattiness` | table talk (Phase 6) | P(a line the LLM offered is actually said) | remarks per game |
| `memory` | logbook read-back (Phase 7) | how much of its own logbook an LLM-piloted character reads before a game: 0 = the head only (standing instructions, dossiers on the opponents present, tally), 0.5 = plus every entry's summary and flags, 1 = every entry in full | tokens per game; win rate against depth |

How the first five are consumed is in `clude_agents.character`; the
headless `Character` ignores `leash`, `chattiness` and `memory`, which
only `clude_llm.LLMCharacter` reads (docs/phase6-plan.md,
docs/phase7-plan.md). The six presets
below are the intended flavors from CLAUDE.md as a first pass, tuned in
Phase 5e against the arena (`docs/strategy-glossary.md`); the two Phase 6
dials start at their defaults for everyone until 6d's sweep. Mustard and
White stay on the neutral `accuse_threshold` deliberately, so that any
wrong accusation of theirs is attributable to their belief method, not
to a dial (the "don't encode the flaw twice" rule).
"""
from __future__ import annotations

from dataclasses import dataclass, replace

DIALS: tuple = (
    "accuse_threshold", "bluff_rate", "curiosity", "secrecy", "temperature", "leash", "chattiness",
    "memory",
)
UNIT_DIALS: tuple = (
    "accuse_threshold", "bluff_rate", "curiosity", "secrecy", "leash", "chattiness", "memory",
)


@dataclass(frozen=True)
class Profile:
    """One character's dial settings. All fields are floats; the seven in
    `UNIT_DIALS` must lie in [0, 1], `temperature` must be >= 0.

    Raises
    ------
    ValueError
        On construction, if any dial is out of range.
    """

    accuse_threshold: float = 0.8
    bluff_rate: float = 0.1
    curiosity: float = 0.5
    secrecy: float = 0.5
    temperature: float = 0.1
    leash: float = 0.25
    chattiness: float = 0.5
    memory: float = 0.0

    def __post_init__(self) -> None:
        for name in UNIT_DIALS:
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {value!r}")
        if self.temperature < 0.0:
            raise ValueError(f"temperature must be >= 0, got {self.temperature!r}")

    def with_dials(self, **changes: float) -> "Profile":
        """A copy with the named dials changed (validated like a new one).

        Raises
        ------
        ValueError
            If a name is not a dial, or a value is out of range.
        """
        unknown = set(changes) - set(DIALS)
        if unknown:
            raise ValueError(f"not a dial: {sorted(unknown)}; dials are {DIALS}")
        return replace(self, **changes)

    def to_dict(self) -> dict:
        """JSON-ready dial values, keyed by dial name."""
        return {name: float(getattr(self, name)) for name in DIALS}

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        """Inverse of `to_dict`. Missing dials take their defaults.

        Raises
        ------
        ValueError
            On an unknown key or an out-of-range value.
        """
        unknown = set(data) - set(DIALS)
        if unknown:
            raise ValueError(f"not a dial: {sorted(unknown)}; dials are {DIALS}")
        return cls(**{name: float(value) for name, value in data.items()})


NEUTRAL = Profile()
"""Every dial at its default -- the reference point sweeps vary from."""

PRESETS: dict = {
    # Overconfident, accuses early: a low bar for P(correct), a little
    # bluffing, and a taste for the room she already suspects. 0.15 is
    # the tuned value: at 0.5 she never reached it before somebody else
    # proved the envelope, at 0.3 only in games that had already run
    # long; 0.15 has her accusing by turn 24 in over half her games,
    # wrong more often than right (docs/strategy-glossary.md).
    "Scarlett": Profile(
        accuse_threshold=0.15, bluff_rate=0.2, curiosity=0.7, secrecy=0.4, temperature=0.15
    ),
    # Correct but slow: near-certainty before accusing, no bluffing to
    # speak of, single-minded about the most informative room. Tuned
    # off the losing extremes (0.95 and 0.9) the sweeps found.
    "Plum": Profile(
        accuse_threshold=0.9, bluff_rate=0.05, curiosity=0.8, secrecy=0.7, temperature=0.05
    ),
    # Cautious: her threshold applies to the Dempster-Shafer *belief*
    # (a lower bound), not the pignistic probability -- see
    # `clude_agents.character.ds_belief_confidence` -- so 0.7 there is
    # far stricter than 0.7 would be for anyone else.
    "Peacock": Profile(
        accuse_threshold=0.7, bluff_rate=0.05, curiosity=0.6, secrecy=0.9, temperature=0.1
    ),
    # Blusters into the nearest room and shows whatever; neutral on
    # accusing so his tree, not a dial, owns his wrong accusations.
    "Mustard": Profile(
        accuse_threshold=NEUTRAL.accuse_threshold,
        bluff_rate=0.1, curiosity=0.3, secrecy=0.3, temperature=0.2,
    ),
    # Opportunistic: middling everything, a bit noisy.
    "Green": Profile(
        accuse_threshold=0.75, bluff_rate=0.2, curiosity=0.5, secrecy=0.5, temperature=0.2
    ),
    # Reads people and plays them: bluffs the most, gives away the
    # least; neutral on accusing for the same reason as Mustard.
    "White": Profile(
        accuse_threshold=NEUTRAL.accuse_threshold,
        bluff_rate=0.3, curiosity=0.4, secrecy=0.8, temperature=0.1,
    ),
}


def preset(name: str) -> Profile:
    """The preset `Profile` for a suspect name.

    Raises
    ------
    KeyError
        If `name` has no preset.
    """
    if name not in PRESETS:
        raise KeyError(f"no personality preset for {name!r}; presets: {sorted(PRESETS)}")
    return PRESETS[name]
