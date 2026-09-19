"""Phase 5d: the arena -- N full games among characters and/or dumb
bots, with the metrics that make a personality dial's effect visible.

Where the Phase 4 benchmark scores *beliefs* on shared snapshots, the
arena plays whole games through `engine.run_game` with
`clude_constraints.observe` as the observer, so every decision a
`Character` makes is one it made live. Per roster entry it reports:

- **win rate** -- games won / games played, with a binomial std so a
  sweep's claim is honest (docs/phase5-plan.md, 4.5);
- **wrong-accusation rate** -- games in which the player accused
  wrongly (and was eliminated) / games played;
- **turn of first accusation** -- mean game turn of the player's first
  accusation, over games where it made one, plus the never-accused rate;
- **own cards leaked** -- distinct own cards shown to opponents;
- **own cards named** -- suggestions that named one of the player's
  own cards (the bluff dial's footprint);
- **re-show rate** -- of the refutations where the player held two or
  more of the named cards and so had a choice, the fraction in which it
  showed a card it had already shown to somebody (the secrecy dial's
  footprint; the choice itself is rare, which is why "cards leaked"
  barely moves with the dial);
- **ms/call** -- mean wall-clock per `select_action`, like the benchmark;
- for LLM-piloted seats (Phase 6, `llm_backend`): decisions, how many
  were the model's to make (not single-option menus), fallback and
  deviation rates, remarks and tokens per game, ms per model call, and
  (Phase 7, with a `logbook_store`) logbook entries written.

Seats rotate: game `g` seats the roster rotated by `g`, truncated to
the table size, so every entry moves first equally often and sits out
equally often at small tables; the table size cycles like
`generate_snapshots`. Missing seats are filled with `FloorBot`s, which
is also the "does a character beat a purely logical player" baseline.
Characters are built once per run and reset once, so Green's bandit
posteriors persist across games and his `observe` at each game's end
is what "learns across games" means.

Every character draws from its own RNG and each fill `FloorBot` gets a
private one, so a game's deal *and* dice depend only on ``seed + g``:
two arena runs with the same seed but different profiles play the same
deals with the same rolls -- a paired comparison. A ``"random"`` roster
entry (`RandomBot`) breaks that, since it draws from the engine RNG.

With a `logbook_store` (Phase 7) every character reads its method
memory from its logbook before each game and, unless
`logbooks_readonly`, writes to it after (`clude_training.memory`), so a
run becomes a learning curve rather than independent games: the
comparison to make is then between runs on one seed with the logbooks
in the same state, read-only.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from random import Random
from typing import Optional

import clude_constraints
from clude_agents import AGENT_SPECS, build_character
from clude_agents.bandit import RevealedOutcome
from clude_core.domain import SUSPECTS
from clude_core import engine
from clude_core.bots import RandomBot
from clude_core.events import AccusationEvent, GameOverEvent
from clude_llm import LLMCharacter, LLMSettings
from clude_storage.logbooks import Logbook
from clude_storage.records import GameRecord, SeatRecord
from clude_training import memory as method_memory
from clude_training.self_play import DEFAULT_PLAYER_COUNTS

DEFAULT_N_GAMES = 24
DEFAULT_SEED = 7007
DEFAULT_MAX_TURNS = 200
FILL_LABEL = "floor"
BOT_LABELS: tuple = ("floor", "random")
DEFAULT_ROSTER: tuple = ("Scarlett", "Mustard", "White", "Green", "Peacock", "Plum")


def binomial_std(successes: int, trials: int) -> float:
    """Standard deviation of a rate estimate, ``sqrt(p (1 - p) / n)``;
    NaN with no trials."""
    if trials <= 0:
        return float("nan")
    p = successes / trials
    return math.sqrt(p * (1.0 - p) / trials)


def _mean(values: list) -> float:
    return sum(values) / len(values) if values else float("nan")


@dataclass(frozen=True)
class SeatOutcome:
    """What one seat did in one game, extracted from the final state."""

    label: str
    kind: str
    seat: int
    suspect: str
    won: bool
    accused: bool
    wrong_accusation: bool
    first_accusation_turn: Optional[int]
    cards_leaked: int
    own_cards_named: int
    suggestions: int
    reshow_choices: int = 0
    reshows: int = 0


@dataclass
class PlayerStats:
    """Accumulated outcomes for one roster label across games."""

    label: str
    kind: str
    games: int = 0
    wins: int = 0
    games_with_accusation: int = 0
    games_with_wrong_accusation: int = 0
    first_accusation_turns: list = field(default_factory=list)
    cards_leaked: list = field(default_factory=list)
    own_cards_named: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)
    reshow_choices: int = 0
    reshows: int = 0
    n_calls: int = 0
    seconds: float = 0.0
    llm_decisions: int = 0
    llm_singles: int = 0
    llm_calls: int = 0
    llm_played: int = 0
    llm_fallbacks: int = 0
    llm_deviations: int = 0
    llm_remarks: int = 0
    llm_entries: int = 0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    llm_cached_tokens: int = 0
    llm_seconds: float = 0.0

    def record(
        self, outcome: SeatOutcome, n_calls: int = 0, seconds: float = 0.0, llm: Optional[dict] = None
    ) -> None:
        """Fold one game's outcome (and that game's belief-call cost) in;
        `llm` is that game's slice of `LLMCharacter.summary()` for an
        LLM-piloted seat (`LLM_SUMMARY_KEYS`)."""
        self.games += 1
        self.wins += int(outcome.won)
        self.games_with_accusation += int(outcome.accused)
        self.games_with_wrong_accusation += int(outcome.wrong_accusation)
        if outcome.first_accusation_turn is not None:
            self.first_accusation_turns.append(outcome.first_accusation_turn)
        self.cards_leaked.append(outcome.cards_leaked)
        self.own_cards_named.append(outcome.own_cards_named)
        self.suggestions.append(outcome.suggestions)
        self.reshow_choices += outcome.reshow_choices
        self.reshows += outcome.reshows
        self.n_calls += n_calls
        self.seconds += seconds
        for key, attr in _LLM_FIELDS.items():
            setattr(self, attr, getattr(self, attr) + (llm or {}).get(key, 0))

    def merge(self, other: "PlayerStats") -> None:
        """Pool another label's counts into this one (sweeps pool the
        swept characters)."""
        self.games += other.games
        self.wins += other.wins
        self.games_with_accusation += other.games_with_accusation
        self.games_with_wrong_accusation += other.games_with_wrong_accusation
        self.first_accusation_turns.extend(other.first_accusation_turns)
        self.cards_leaked.extend(other.cards_leaked)
        self.own_cards_named.extend(other.own_cards_named)
        self.suggestions.extend(other.suggestions)
        self.reshow_choices += other.reshow_choices
        self.reshows += other.reshows
        self.n_calls += other.n_calls
        self.seconds += other.seconds
        for attr in _LLM_FIELDS.values():
            setattr(self, attr, getattr(self, attr) + getattr(other, attr))

    @property
    def reshow_rate(self) -> float:
        """Re-shows over refutations where there was a choice; NaN if
        the player never had one."""
        return self.reshows / self.reshow_choices if self.reshow_choices else float("nan")

    @property
    def win_rate(self) -> float:
        return self.wins / self.games if self.games else float("nan")

    @property
    def win_rate_std(self) -> float:
        return binomial_std(self.wins, self.games)

    @property
    def wrong_accusation_rate(self) -> float:
        return self.games_with_wrong_accusation / self.games if self.games else float("nan")

    @property
    def wrong_accusation_std(self) -> float:
        return binomial_std(self.games_with_wrong_accusation, self.games)

    @property
    def never_accused_rate(self) -> float:
        if not self.games:
            return float("nan")
        return 1.0 - self.games_with_accusation / self.games

    @property
    def mean_first_accusation_turn(self) -> float:
        return _mean(self.first_accusation_turns)

    @property
    def mean_cards_leaked(self) -> float:
        return _mean(self.cards_leaked)

    @property
    def mean_own_cards_named(self) -> float:
        return _mean(self.own_cards_named)

    @property
    def mean_suggestions(self) -> float:
        return _mean(self.suggestions)

    @property
    def ms_per_call(self) -> float:
        return 1000.0 * self.seconds / self.n_calls if self.n_calls else float("nan")

    # -- LLM-piloted seats (Phase 6) --

    @property
    def llm_asked(self) -> int:
        """Decisions that were the model's to make: all but single-option menus."""
        return self.llm_decisions - self.llm_singles

    @property
    def fallback_rate(self) -> float:
        """Of the decisions asked of the model, the share that fell back."""
        return self.llm_fallbacks / self.llm_asked if self.llm_asked else float("nan")

    @property
    def deviation_rate(self) -> float:
        """Of the model's played choices, the share below the character's top option."""
        return self.llm_deviations / self.llm_played if self.llm_played else float("nan")

    @property
    def remarks_per_game(self) -> float:
        return self.llm_remarks / self.games if self.games else float("nan")

    @property
    def tokens_per_game(self) -> float:
        total = self.llm_input_tokens + self.llm_output_tokens
        return total / self.games if self.games else float("nan")

    @property
    def llm_ms_per_call(self) -> float:
        return 1000.0 * self.llm_seconds / self.llm_calls if self.llm_calls else float("nan")

    def to_dict(self) -> dict:
        """JSON-ready metrics, each rate beside its n and std."""
        return {
            "label": self.label,
            "kind": self.kind,
            "games": self.games,
            "wins": self.wins,
            "win_rate": self.win_rate,
            "win_rate_std": self.win_rate_std,
            "games_with_accusation": self.games_with_accusation,
            "games_with_wrong_accusation": self.games_with_wrong_accusation,
            "wrong_accusation_rate": self.wrong_accusation_rate,
            "wrong_accusation_std": self.wrong_accusation_std,
            "never_accused_rate": self.never_accused_rate,
            "mean_first_accusation_turn": self.mean_first_accusation_turn,
            "mean_cards_leaked": self.mean_cards_leaked,
            "mean_own_cards_named": self.mean_own_cards_named,
            "mean_suggestions": self.mean_suggestions,
            "reshow_choices": self.reshow_choices,
            "reshows": self.reshows,
            "reshow_rate": self.reshow_rate,
            "n_calls": self.n_calls,
            "ms_per_call": self.ms_per_call,
            "llm_decisions": self.llm_decisions,
            "llm_asked": self.llm_asked,
            "llm_calls": self.llm_calls,
            "llm_played": self.llm_played,
            "llm_fallbacks": self.llm_fallbacks,
            "llm_deviations": self.llm_deviations,
            "llm_remarks": self.llm_remarks,
            "llm_entries": self.llm_entries,
            "fallback_rate": self.fallback_rate,
            "deviation_rate": self.deviation_rate,
            "remarks_per_game": self.remarks_per_game,
            "tokens_per_game": self.tokens_per_game,
            "llm_ms_per_call": self.llm_ms_per_call,
            "llm_seconds": self.llm_seconds,
        }


@dataclass(frozen=True)
class GameSummary:
    """One line per game for the run summary."""

    game_index: int
    seed: int
    n_players: int
    labels: tuple
    winner_label: Optional[str]
    turns: int
    n_suggestions: int
    n_accusations: int
    hit_cap: bool

    def to_dict(self) -> dict:
        return {
            "game_index": self.game_index,
            "seed": self.seed,
            "n_players": self.n_players,
            "labels": list(self.labels),
            "winner_label": self.winner_label,
            "turns": self.turns,
            "n_suggestions": self.n_suggestions,
            "n_accusations": self.n_accusations,
            "hit_cap": self.hit_cap,
        }


@dataclass
class ArenaResult:
    """Everything one `run_arena` call produced."""

    run_id: str
    n_games: int
    seed: int
    roster: tuple
    player_counts: tuple
    max_turns: int
    profiles: dict = field(default_factory=dict)  # label -> Profile.to_dict()
    per_player: dict = field(default_factory=dict)  # label -> PlayerStats
    games: list = field(default_factory=list)  # GameSummary
    seconds: float = 0.0
    llm: dict = field(default_factory=dict)  # backend, model, wrapped characters (Phase 6)
    memory: dict = field(default_factory=dict)  # logbook store, readonly, who has one, who loaded (Phase 7)

    @property
    def mean_turns(self) -> float:
        return _mean([g.turns for g in self.games])

    @property
    def decided_rate(self) -> float:
        """Fraction of games somebody won."""
        if not self.games:
            return float("nan")
        return sum(1 for g in self.games if g.winner_label is not None) / len(self.games)

    def summary_table(self) -> str:
        """One row per roster label, in roster order then fill seats."""
        header = (
            f"{'player':<10}{'games':>6}{'win%':>7}{'+-':>5}{'wrong%':>8}{'+-':>5}"
            f"{'1st_acc':>9}{'never%':>8}{'leaked':>8}{'named':>7}{'reshow%':>9}{'ms/call':>9}"
        )
        lines = [header, "-" * len(header)]
        for label in dict.fromkeys(list(self.roster) + [FILL_LABEL]):
            if label not in self.per_player:
                continue
            s = self.per_player[label]
            first = f"{s.mean_first_accusation_turn:>9.1f}" if s.first_accusation_turns else f"{'-':>9}"
            reshow = f"{100 * s.reshow_rate:>9.1f}" if s.reshow_choices else f"{'-':>9}"
            ms = f"{s.ms_per_call:>9.1f}" if s.n_calls else f"{'-':>9}"
            lines.append(
                f"{label:<10}{s.games:>6}{100 * s.win_rate:>7.1f}{100 * s.win_rate_std:>5.1f}"
                f"{100 * s.wrong_accusation_rate:>8.1f}{100 * s.wrong_accusation_std:>5.1f}"
                f"{first}{100 * s.never_accused_rate:>8.1f}{s.mean_cards_leaked:>8.2f}"
                f"{s.mean_own_cards_named:>7.2f}{reshow}{ms}"
            )
        table = "\n".join(lines)
        if any(s.llm_decisions for s in self.per_player.values()):
            table += "\n\nLLM seats:\n" + self.llm_table()
        return table

    def llm_table(self) -> str:
        """One row per LLM-piloted label: decisions, of them asked of the
        model, fallback and deviation rates, remarks and tokens per game,
        ms per model call."""
        header = (
            f"{'player':<10}{'games':>6}{'decis':>7}{'asked':>7}{'fallb%':>8}{'deviate%':>10}"
            f"{'talk/g':>8}{'entries':>8}{'tok/g':>9}{'llm ms':>8}"
        )
        lines = [header, "-" * len(header)]
        for label in dict.fromkeys(list(self.roster) + [FILL_LABEL]):
            s = self.per_player.get(label)
            if s is None or not s.llm_decisions:
                continue
            fallback = f"{100 * s.fallback_rate:>8.1f}" if s.llm_asked else f"{'-':>8}"
            deviate = f"{100 * s.deviation_rate:>10.1f}" if s.llm_played else f"{'-':>10}"
            ms = f"{s.llm_ms_per_call:>8.0f}" if s.llm_calls else f"{'-':>8}"
            lines.append(
                f"{label:<10}{s.games:>6}{s.llm_decisions:>7}{s.llm_asked:>7}{fallback}{deviate}"
                f"{s.remarks_per_game:>8.2f}{s.llm_entries:>8}{s.tokens_per_game:>9.0f}{ms}"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """JSON-ready run summary: settings, per-player metrics, per-game lines."""
        return {
            "run_id": self.run_id,
            "n_games": self.n_games,
            "seed": self.seed,
            "roster": list(self.roster),
            "player_counts": list(self.player_counts),
            "max_turns": self.max_turns,
            "profiles": dict(self.profiles),
            "llm": dict(self.llm),
            "memory": dict(self.memory),
            "per_player": {label: s.to_dict() for label, s in self.per_player.items()},
            "games": [g.to_dict() for g in self.games],
            "mean_turns": self.mean_turns,
            "decided_rate": self.decided_rate,
            "seconds": self.seconds,
        }


def parse_roster(items) -> tuple:
    """Validate roster entries: character names (each at most once) and
    bot labels from `BOT_LABELS` (any number of times).

    Raises
    ------
    ValueError
        On an unknown entry or a repeated character.
    """
    roster = tuple(str(item).strip() for item in items if str(item).strip())
    if not roster:
        raise ValueError("roster is empty")
    seen = set()
    for label in roster:
        if label in AGENT_SPECS:
            if label in seen:
                raise ValueError(f"character {label!r} listed twice; a character sits once per game")
            seen.add(label)
        elif label not in BOT_LABELS:
            raise ValueError(
                f"unknown roster entry {label!r}: expected a suspect name "
                f"({', '.join(sorted(AGENT_SPECS))}) or one of {BOT_LABELS}"
            )
    return roster


def lineup_for_game(roster: tuple, game_index: int, n_players: int) -> list:
    """Who plays game `game_index`: the roster rotated by the game index
    (so who sits out varies when the roster is larger than the table),
    truncated to `n_players`, padded with `FILL_LABEL`. Not yet seated:
    `seat_lineup` puts each player on a token."""
    shift = game_index % len(roster)
    rotated = list(roster[shift:]) + list(roster[:shift])
    lineup = rotated[:n_players]
    while len(lineup) < n_players:
        lineup.append(FILL_LABEL)
    return lineup


def seat_lineup(lineup) -> tuple:
    """Seat a game's players by token: a character plays its own
    suspect's token, every other player (a fill bot, later a human)
    takes the lowest unused token, and seats run in the board's suspect
    order, which is the turn order. Returns ``(labels, suspects)``, both
    in seat order. A character never plays another suspect's token
    (David, 2026-09-14): Plum is always Plum, whoever else is at the
    table.
    """
    lineup = list(lineup)
    taken = {label for label in lineup if label in SUSPECTS}
    free = [s for s in SUSPECTS if s not in taken]
    seated = []
    for label in lineup:
        seated.append((label, label) if label in SUSPECTS else (label, free.pop(0)))
    seated.sort(key=lambda pair: SUSPECTS.index(pair[1]))
    return [label for label, _ in seated], [suspect for _, suspect in seated]


def seat_outcome(state, events, seat: int, label: str, kind: str) -> SeatOutcome:
    """Extract one seat's `SeatOutcome` from a finished game."""
    final = events[-1]
    won = isinstance(final, GameOverEvent) and final.winner == seat
    own_accusations = [
        e for e in events if isinstance(e, AccusationEvent) and e.accusation.accuser == seat
    ]
    hand = state.hands[seat]
    leaked = {s.card_shown for s in state.suggestion_log if s.refuter == seat and s.card_shown}
    own_named = sum(
        1 for s in state.suggestion_log
        if s.suggester == seat and any(c in hand for c in s.cards())
    )
    shown_before: set = set()
    reshow_choices = 0
    reshows = 0
    for s in state.suggestion_log:
        if s.refuter != seat or s.card_shown is None:
            continue
        if len(set(s.cards()) & hand) >= 2:
            reshow_choices += 1
            reshows += int(s.card_shown in shown_before)
        shown_before.add(s.card_shown)
    return SeatOutcome(
        label=label,
        kind=kind,
        seat=seat,
        suspect=state.suspects_in_play[seat],
        won=won,
        accused=bool(own_accusations),
        wrong_accusation=any(not e.accusation.correct for e in own_accusations),
        first_accusation_turn=own_accusations[0].turn if own_accusations else None,
        cards_leaked=len(leaked),
        own_cards_named=own_named,
        suggestions=sum(1 for s in state.suggestion_log if s.suggester == seat),
        reshow_choices=reshow_choices,
        reshows=reshows,
    )


_LLM_FIELDS: dict = {
    "decisions": "llm_decisions", "singles": "llm_singles", "llm_calls": "llm_calls",
    "played": "llm_played", "fallbacks": "llm_fallbacks", "deviations": "llm_deviations",
    "remarks": "llm_remarks", "entries": "llm_entries", "input_tokens": "llm_input_tokens",
    "output_tokens": "llm_output_tokens", "cached_tokens": "llm_cached_tokens",
    "llm_seconds": "llm_seconds",
}
"""`LLMCharacter.summary()` key -> `PlayerStats` attribute."""


def _kind_of(label: str) -> str:
    return "character" if label in AGENT_SPECS else label


def fill_seed(game_seed: int, seat: int) -> int:
    """Seed for a fill `FloorBot`'s private RNG: distinct per game and
    seat, and never the engine seed itself."""
    return game_seed * 1009 + seat + 1


@dataclass
class Table:
    """One game's seated players, ready for `engine.run_game` or
    `engine.game_steps`.

    Parameters
    ----------
    players : dict[int, PlayerProtocol]
        Seat -> the player object in it.
    labels : list[str]
        Seat -> its occupant's roster label (a character, or a bot kind).
    suspects : list[str]
        Seat -> the token it plays, from `seat_lineup`.
    observer : Callable
        What builds each seat's view: `clude_constraints.observe`, which
        every character needs.
    kinds : list[str]
        Seat -> what occupies it (`clude_training.table.SEAT_KINDS`),
        which is what `SeatRecord.kind` holds; a human seat's label is a
        person's name, so the kind can no longer be read off the label.
        Empty for a table built before Phase 8.2, which `seat_kind`
        still covers.
    wrappers : dict[int, LLMCharacter]
        Seat -> the LLM wrapper piloting an ``llm`` seat from outside the
        engine (Phase 8.3a); such a seat is external and absent from
        `players`. Empty when the table was built without a backend.
    """

    players: dict
    labels: list
    suspects: list
    observer: object
    kinds: list = field(default_factory=list)
    wrappers: dict = field(default_factory=dict)


def headless_table(roster, n_players: int, seed: int) -> Table:
    """The table ``clude_cli.py play`` seats for `roster` and `seed`,
    without its LLM and logbook layers.

    Each character is built with its preset dials and reset with the game
    seed, each fill `FloorBot` gets a private RNG seeded apart from the
    engine (`fill_seed`), and every character is told who it is sitting
    with. The web app's Watch screen plays from this (Phase 8.1), and a
    test pins a game played here to the one `play` produces for the same
    roster and seed, so the two cannot drift apart unnoticed.

    Since Phase 8.2 this is `clude_training.table.build_table` over
    `TableSetup.from_roster` with no humans, so a watched game, a game
    with people at the table and `play`'s game are one code path. The
    import is deferred because `table` imports this module's seating
    helpers.

    Raises
    ------
    ValueError
        From `parse_roster`, on an empty roster, an unknown label or a
        character listed twice.
    """
    from .table import TableSetup, build_table  # noqa: PLC0415 -- `table` imports this module

    table, _external = build_table(TableSetup.from_roster(roster, n_players, seed))
    return table


def seat_kind(label: str) -> str:
    """``"character"`` for a character, else the bot kind it names; what
    `SeatRecord.kind` holds for a headless seat."""
    return _kind_of(label)


LLM_SUMMARY_KEYS: tuple = (
    "decisions", "singles", "llm_calls", "played", "fallbacks", "deviations", "remarks",
    "entries", "input_tokens", "output_tokens", "cached_tokens", "llm_seconds",
)
"""The numeric keys of `LLMCharacter.summary()`, diffed per game."""


def run_arena(
    n_games: int = DEFAULT_N_GAMES,
    seed: int = DEFAULT_SEED,
    roster=DEFAULT_ROSTER,
    player_counts: tuple = DEFAULT_PLAYER_COUNTS,
    max_turns: int = DEFAULT_MAX_TURNS,
    profiles: Optional[dict] = None,
    store=None,
    run_id: Optional[str] = None,
    llm_backend=None,
    llm_settings: Optional[LLMSettings] = None,
    llm_characters=None,
    logbook_store=None,
    logbooks_readonly: bool = False,
    logbook_characters=None,
) -> ArenaResult:
    """Play `n_games` games and accumulate per-player metrics.

    Parameters
    ----------
    n_games : int
    seed : int
        Game `g` uses engine seed ``seed + g``; characters are reset
        with `seed` once, at the start.
    roster : iterable of str
        Character names and/or bot labels; see `parse_roster`.
    player_counts : tuple[int, ...]
        Table size cycles through these across games.
    max_turns : int
        Turn cap per game.
    profiles : dict[str, Profile] or None
        Per-character overrides of the preset profiles.
    store : RecordStore or None
        If given, every game's `GameRecord` and the run summary are
        written to it under `run_id`.
    run_id : str or None
        Defaults to ``arena-<seed>-<n_games>``, or ``llm-<seed>-<n_games>``
        with a backend.
    llm_backend : LLMBackend or None
        If given, the roster's characters (or just `llm_characters`) are
        wrapped in `LLMCharacter`s sharing this backend (Phase 6): their
        `kind` is ``"llm"``, each gets `new_game` before every game, and
        the LLM columns fill in. `clude_llm.NullBackend` is the control:
        it plays the headless game exactly, so two runs on one seed with
        and without a backend are a paired comparison.
    llm_settings : LLMSettings or None
        Default `LLMSettings()`.
    llm_characters : iterable of str or None
        Which roster characters to wrap; default all of them.
    logbook_store : RecordStore or None
        If given, each character's logbook in it (keyed by its label)
        supplies its method memory before every game (Phase 7,
        `clude_training.memory.load_into`) and, unless
        `logbooks_readonly`, absorbs the game after it; every game's
        record is built for that whether or not `store` is given.
    logbooks_readonly : bool
        Read the logbooks but write nothing: what a fair sweep needs.
    logbook_characters : iterable of str or None
        Which roster characters get a logbook; default every character
        in the roster. The rest play exactly as they do without memory,
        so a run can isolate one character's logbook against a baseline.

    Returns
    -------
    ArenaResult

    Raises
    ------
    ValueError
        On a bad roster, or an `llm_characters` or `logbook_characters`
        name that is not a character in it.
    """
    roster = parse_roster(roster)
    profiles = dict(profiles or {})
    wrapped: set = set()
    if llm_backend is not None:
        llm_settings = llm_settings or LLMSettings()
        wrapped = set(llm_characters) if llm_characters else {l for l in roster if l in AGENT_SPECS}
        bad = sorted(name for name in wrapped if name not in AGENT_SPECS or name not in roster)
        if bad:
            raise ValueError(f"llm_characters {bad} are not characters in the roster {roster}")
    if run_id is None:
        run_id = f"llm-{seed}-{n_games}" if llm_backend is not None else f"arena-{seed}-{n_games}"
    started = time.perf_counter()

    characters = {}
    for label in roster:
        if label in AGENT_SPECS:
            character = build_character(label, profiles.get(label))
            if label in wrapped:
                character = LLMCharacter(character, llm_backend, settings=llm_settings)
            character.reset(seed)
            characters[label] = character

    logbooks: dict = {}
    loaded: list = []
    stale: set = set()  # labels whose memory changed since it was last loaded
    if logbook_store is not None:
        remembering = set(logbook_characters) if logbook_characters else set(characters)
        bad = sorted(name for name in remembering if name not in characters)
        if bad:
            raise ValueError(f"logbook_characters {bad} are not characters in the roster {roster}")
        logbooks = {label: Logbook(logbook_store, label) for label in characters if label in remembering}
        loaded = sorted(
            label for label, logbook in logbooks.items() if method_memory.load_into(characters[label], logbook)
        )
        for label in wrapped & set(logbooks):
            characters[label].attach_logbook(logbooks[label])

    labels = list(dict.fromkeys(list(roster) + [FILL_LABEL]))
    result = ArenaResult(
        run_id=run_id,
        n_games=n_games,
        seed=seed,
        roster=roster,
        player_counts=tuple(player_counts),
        max_turns=max_turns,
        profiles={label: ch.profile.to_dict() for label, ch in characters.items()},
        per_player={
            label: PlayerStats(label, "llm" if label in wrapped else _kind_of(label)) for label in labels
        },
        llm=(
            {"backend": llm_backend.name, "model": llm_settings.model, "characters": sorted(wrapped)}
            if llm_backend is not None else {}
        ),
        memory=(
            {
                "store": logbook_store.describe(), "readonly": bool(logbooks_readonly),
                "characters": sorted(logbooks), "loaded": loaded,
            }
            if logbook_store is not None else {}
        ),
    )

    for g in range(n_games):
        n_players = player_counts[g % len(player_counts)]
        lineup, suspects = seat_lineup(lineup_for_game(roster, g, n_players))
        game_seed = seed + g
        players = {}
        for seat, label in enumerate(lineup):
            if label in characters:
                players[seat] = characters[label]
            elif label == "floor":
                players[seat] = clude_constraints.FloorBot(rng=Random(fill_seed(game_seed, seat)))
            else:
                players[seat] = RandomBot()
        for label in set(lineup) & stale:
            method_memory.load_into(characters[label], logbooks[label])
            stale.discard(label)
        for label in set(lineup) & set(characters):
            characters[label].new_game(lineup)
        cost_before = {label: (ch.n_calls, ch.seconds) for label, ch in characters.items()}
        llm_before = {label: characters[label].summary() for label in wrapped}

        state, events = engine.run_game(
            n_players, players, seed=game_seed, max_turns=max_turns,
            observer=clude_constraints.observe, suspects=suspects,
        )

        for label in set(lineup) & set(characters):
            characters[label].observe(RevealedOutcome(envelope=state.envelope))

        seats = []
        llm_log: dict = {}
        for seat, label in enumerate(lineup):
            if label in wrapped:
                llm_log[seat] = [d.to_dict() for d in characters[label].decisions]
            seats.append(
                SeatRecord(
                    seat=seat,
                    suspect=state.suspects_in_play[seat],
                    label=label,
                    kind="llm" if label in wrapped else _kind_of(label),
                    profile=characters[label].profile.to_dict() if label in characters else None,
                    model=llm_settings.model if label in wrapped else None,
                )
            )

        if store is not None or logbook_store is not None:
            record = GameRecord.from_game(
                run_id, g, game_seed, state, events, seats, llm_log=llm_log or None
            )
            if store is not None:
                store.put_game(run_id, g, record.to_dict())
            if logbook_store is not None and not logbooks_readonly:
                # Each character writes to its logbook: method memory for the
                # three that have it, and the model's entry for an LLM seat.
                # The debrief comes before the stats below so its tokens land
                # in this game's slice.
                for seat, label in enumerate(lineup):
                    if label not in logbooks:
                        continue
                    if method_memory.update(logbooks[label], record, characters[label]):
                        stale.add(label)
                    if label in wrapped:
                        characters[label].debrief(record, seat)

        for seat, label in enumerate(lineup):
            kind = "llm" if label in wrapped else _kind_of(label)
            outcome = seat_outcome(state, events, seat, label, kind)
            if label in characters:
                calls, secs = cost_before[label]
                ch = characters[label]
                llm_delta = None
                if label in wrapped:
                    after = ch.summary()
                    llm_delta = {key: after[key] - llm_before[label][key] for key in LLM_SUMMARY_KEYS}
                result.per_player[label].record(outcome, ch.n_calls - calls, ch.seconds - secs, llm_delta)
            else:
                result.per_player[label].record(outcome)

        final = events[-1]
        winner = final.winner if isinstance(final, GameOverEvent) else None
        result.games.append(
            GameSummary(
                game_index=g,
                seed=game_seed,
                n_players=n_players,
                labels=tuple(lineup),
                winner_label=lineup[winner] if winner is not None else None,
                turns=state.turn,
                n_suggestions=len(state.suggestion_log),
                n_accusations=len(state.accusation_log),
                hit_cap=winner is None and any(state.active),
            )
        )
    result.per_player = {
        label: stats for label, stats in result.per_player.items() if stats.games > 0
    }
    result.seconds = time.perf_counter() - started
    if store is not None:
        store.put_run(run_id, result.to_dict())
    return result
