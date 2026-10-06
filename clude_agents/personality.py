"""Eight numeric Profile dials and the six suspect presets.

accuse_threshold, bluff_rate, curiosity, secrecy and temperature govern
Character decisions. leash/chattiness/memory govern LLM discretion, talk
and narrative depth. Curiosity is inert for Plum's policy movement hook.
Unit dials lie in [0, 1]; temperature is nonnegative. Defaults/presets are
code configuration; dated tuning evidence belongs in the strategy glossary.
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
    # bluffing, and a taste for the room she already suspects. 0.15 was
    # the ring-era value (at 0.3 she reached the bar only in games that
    # had already run long, and never won); on the Classic grid games
    # run forty turns and 0.3 wins three times as often as 0.15 at the
    # same wrong rate, so 0.3 is the preset since 2026-09-15. She still
    # accuses by turn 50 in three games of five, wrong half the time
    # (docs/strategy-glossary.md, "Tuned presets on the grid").
    "Scarlett": Profile(
        accuse_threshold=0.3, bluff_rate=0.2, curiosity=0.7, secrecy=0.4, temperature=0.15
    ),
    # PlumOG's dials, unchanged (Phase 12, 2026-10-05: the new Plum
    # starts from exactly these; `PLUM_OG` below keeps them under his
    # name). Near-certainty before accusing, no bluffing to speak of.
    # Threshold tuned off the losing extreme (0.95) the ring sweeps
    # found. Curiosity was 0.8 on the ring; on the grid chasing the
    # most probable room is a long walk and every corridor turn is a
    # turn without a suggestion, so 0.5 (2026-09-15) won more than 0.8
    # or 0.3 did with only his dial moved. For the new Plum curiosity is
    # inert: his move head owns the destination (`deep_nash`), and the
    # dial stays here for the record. `accuse_threshold` and `leash`
    # are to be re-measured for him (`docs/deepnash-plan.md` 5).
    "Plum": Profile(
        accuse_threshold=0.9, bluff_rate=0.05, curiosity=0.5, secrecy=0.7, temperature=0.05
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


PLUM_OG: Profile = PRESETS["Plum"]
"""The dials PlumOG played with, archived 2026-10-05 (Phase 12): the
same `Profile` the new Plum starts from. Not a preset: PlumOG is in no
registry."""


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
