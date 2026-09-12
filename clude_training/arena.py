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
- **ms/call** -- mean wall-clock per `select_action`, like the benchmark.

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
from clude_core import engine
from clude_core.bots import RandomBot
from clude_core.events import AccusationEvent, GameOverEvent
from clude_storage.records import GameRecord, SeatRecord
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

    def record(self, outcome: SeatOutcome, n_calls: int = 0, seconds: float = 0.0) -> None:
        """Fold one game's outcome (and that game's belief-call cost) in."""
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
    """Seat labels for game `game_index`: the roster rotated by the game
    index, truncated to `n_players`, padded with `FILL_LABEL`."""
    shift = game_index % len(roster)
    rotated = list(roster[shift:]) + list(roster[:shift])
    lineup = rotated[:n_players]
    while len(lineup) < n_players:
        lineup.append(FILL_LABEL)
    return lineup


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


def _kind_of(label: str) -> str:
    return "character" if label in AGENT_SPECS else label


def fill_seed(game_seed: int, seat: int) -> int:
    """Seed for a fill `FloorBot`'s private RNG: distinct per game and
    seat, and never the engine seed itself."""
    return game_seed * 1009 + seat + 1


def run_arena(
    n_games: int = DEFAULT_N_GAMES,
    seed: int = DEFAULT_SEED,
    roster=DEFAULT_ROSTER,
    player_counts: tuple = DEFAULT_PLAYER_COUNTS,
    max_turns: int = DEFAULT_MAX_TURNS,
    profiles: Optional[dict] = None,
    store=None,
    run_id: Optional[str] = None,
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
        Defaults to ``arena-<seed>-<n_games>``.

    Returns
    -------
    ArenaResult
    """
    roster = parse_roster(roster)
    profiles = dict(profiles or {})
    run_id = run_id or f"arena-{seed}-{n_games}"
    started = time.perf_counter()

    characters = {}
    for label in roster:
        if label in AGENT_SPECS:
            character = build_character(label, profiles.get(label))
            character.reset(seed)
            characters[label] = character

    labels = list(dict.fromkeys(list(roster) + [FILL_LABEL]))
    result = ArenaResult(
        run_id=run_id,
        n_games=n_games,
        seed=seed,
        roster=roster,
        player_counts=tuple(player_counts),
        max_turns=max_turns,
        profiles={label: ch.profile.to_dict() for label, ch in characters.items()},
        per_player={label: PlayerStats(label, _kind_of(label)) for label in labels},
    )

    for g in range(n_games):
        n_players = player_counts[g % len(player_counts)]
        lineup = lineup_for_game(roster, g, n_players)
        game_seed = seed + g
        players = {}
        for seat, label in enumerate(lineup):
            if label in characters:
                players[seat] = characters[label]
            elif label == "floor":
                players[seat] = clude_constraints.FloorBot(rng=Random(fill_seed(game_seed, seat)))
            else:
                players[seat] = RandomBot()
        cost_before = {label: (ch.n_calls, ch.seconds) for label, ch in characters.items()}

        state, events = engine.run_game(
            n_players, players, seed=game_seed, max_turns=max_turns,
            observer=clude_constraints.observe,
        )

        for label in set(lineup) & set(characters):
            characters[label].observe(RevealedOutcome(envelope=state.envelope))

        seats = []
        for seat, label in enumerate(lineup):
            kind = _kind_of(label)
            outcome = seat_outcome(state, events, seat, label, kind)
            if label in characters:
                calls, secs = cost_before[label]
                ch = characters[label]
                result.per_player[label].record(outcome, ch.n_calls - calls, ch.seconds - secs)
            else:
                result.per_player[label].record(outcome)
            seats.append(
                SeatRecord(
                    seat=seat,
                    suspect=state.suspects_in_play[seat],
                    label=label,
                    kind=kind,
                    profile=characters[label].profile.to_dict() if label in characters else None,
                )
            )

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
        if store is not None:
            record = GameRecord.from_game(run_id, g, game_seed, state, events, seats)
            store.put_game(run_id, g, record.to_dict())

    result.per_player = {
        label: stats for label, stats in result.per_player.items() if stats.games > 0
    }
    result.seconds = time.perf_counter() - started
    if store is not None:
        store.put_run(run_id, result.to_dict())
    return result
