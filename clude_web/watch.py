"""Watching a headless game being played, a turn at a time.

Since Phase 8.2 a watched game is a table with nobody human at it
(`clude_web.tables`): the same driver, registry and documents as a game
people play, advanced by the Watch screen's two buttons instead of by
polling. What this module keeps is the shape the Watch screen and its
tests speak: a `WatchSetup` (a roster, a table size and a seed, the
lobby's all-bot form), `WatchGame` (a `WebGame` built from one, with
`advance`) and `WatchRegistry` (the one registry).

**What a spectator may see.** The hands and the envelope stay hidden
until the game is over (`docs/phase8.1-plan.md` 3.2). That rules out the
replay's per-card bars here, and not only for the obvious reason: every
seat's own hand is proven to that seat from the first turn, and all the
hands together are exactly the eighteen cards that are *not* the answer.
So a seat's block here is Direction D's compact bar -- how many cards it
has placed, and how sure it is in each category -- naming no card. A
refutation is described as *who* disproved it, never *what* they showed.
When the game ends it is saved as an ordinary record and opens as a
replay, where everything is laid face up.

Nothing here spends money: every seat is headless.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass

from clude_agents import AGENT_SPECS
from clude_core import engine
from clude_training.arena import parse_roster
from clude_training.table import MAX_TURNS, TableSetup

from .tables import WEB_RUN, TableRegistry, WebGame, remember_from_form


@dataclass(frozen=True)
class WatchSetup:
    """The lobby's headless form, with method memory enabled by default.

    Stored memory snapshots, the setup and a turn count reproduce a game.
    ``remember=False`` opts out of learning across games.
    """

    roster: tuple
    n_players: int
    seed: int
    max_turns: int = MAX_TURNS
    remember: bool = True

    def to_table_setup(self) -> TableSetup:
        """The same table as `arena.headless_table` seats for this
        roster, size and seed; the web registry also applies method memory
        when remembering is enabled."""
        return TableSetup.from_roster(
            self.roster, self.n_players, self.seed, max_turns=self.max_turns, remember=self.remember,
        )

    def to_dict(self) -> dict:
        return {
            "roster": list(self.roster),
            "n_players": self.n_players,
            "seed": self.seed,
            "max_turns": self.max_turns,
            "remember": self.remember,
        }


def parse_setup(form) -> WatchSetup:
    """A `WatchSetup` from the lobby's all-bot form.

    The roster is the characters ticked, each at most once; the seats
    they leave empty are filled with `floor` bots, as `play` fills them.
    Characters are seat-locked (CLAUDE.md), so each plays its own token.
    Method memory defaults on; ``remember=0`` opts out.

    Raises
    ------
    ValueError
        With a message fit to show on the form: no character ticked, more
        characters than seats, a table size outside 3-6, or a seed that
        is not a whole number.
    """
    chosen = [name for name in form.getlist("characters") if name in AGENT_SPECS]
    if not chosen:
        raise ValueError("Pick at least one character to watch.")
    try:
        n_players = int(form.get("n_players", "") or 0)
    except ValueError:
        raise ValueError("The table size must be a number from 3 to 6.") from None
    if not engine.MIN_PLAYERS <= n_players <= engine.MAX_PLAYERS:
        raise ValueError("The table size must be from 3 to 6.")
    if len(chosen) > n_players:
        raise ValueError(
            f"{len(chosen)} characters will not fit at a table of {n_players}. "
            "Untick some, or make the table bigger."
        )
    raw_seed = (form.get("seed") or "").strip()
    if raw_seed:
        try:
            seed = int(raw_seed)
        except ValueError:
            raise ValueError("The seed must be a whole number, or left blank.") from None
    else:
        seed = secrets.randbelow(1_000_000)
    roster = tuple(parse_roster(chosen))
    return WatchSetup(roster=roster, n_players=n_players, seed=seed, remember=remember_from_form(form))


class WatchGame(WebGame):
    """A `WebGame` for a `WatchSetup` (a `TableSetup` is accepted too):
    every seat played by its own object, so the generator only ever
    pauses at the end of a turn and `advance` plays the next one."""

    def __init__(self, setup, prepare=None, llm_backend=None) -> None:
        if isinstance(setup, WatchSetup):
            setup = setup.to_table_setup()
        super().__init__(setup, prepare, llm_backend)


WatchRegistry = TableRegistry
"""One registry for watched and played games alike."""

__all__ = ["WEB_RUN", "WatchGame", "WatchRegistry", "WatchSetup", "parse_setup"]
