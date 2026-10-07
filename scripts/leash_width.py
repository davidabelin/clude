"""How much rope a leash gives: menu widths for Plum and PlumOG (Phase 12 N5).

The leash admits every option scoring at least ``(1 - leash)`` of the best
(`clude_llm.menu.within_leash`), so the same value opens a different number
of options for a method whose scores spread differently. This plays headless
games with Plum seated (the network, or PlumOG's enumeration with his old
dials) and, at each of his move and suggestion decisions with more than one
honest option, counts the options each leash value would allow. Bluff
options are left out: they do not depend on the method. The new Plum's
candidate leash is the value whose mean width matches PlumOG's at 0.25
(docs/deepnash-plan.md section 5, "the equal-rope match").

    python scripts/leash_width.py --games 24 --seed 7007 --json data/plum-eval/leash-width.json

PlumOG is slow (about a second a call on the grid): a few minutes a game.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from random import Random

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import clude_constraints  # noqa: E402
from clude_agents import build_character  # noqa: E402
from clude_agents.character import Character  # noqa: E402
from clude_agents.exact_enum import ExactEnumAgent  # noqa: E402
from clude_agents.personality import PLUM_OG  # noqa: E402
from clude_core import engine  # noqa: E402
from clude_core.domain import SUSPECTS, WEAPONS  # noqa: E402
from clude_llm.menu import within_leash  # noqa: E402
from clude_training.arena import fill_seed, lineup_for_game, seat_lineup  # noqa: E402

LEASHES = (0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5)
KINDS = ("move", "suspect", "weapon")


class _Measured:
    """A character that, before each move and suggestion, counts what
    every leash would allow, then plays exactly as the character does."""

    def __init__(self, character: Character, leashes: tuple) -> None:
        self.character = character
        self.leashes = leashes
        self.widths = {kind: [] for kind in KINDS}  # kind -> [(n_options, [allowed per leash])]

    def __getattr__(self, name):
        return getattr(self.character, name)

    def _count(self, kind: str, scores: list) -> None:
        if len(scores) > 1:
            self.widths[kind].append(
                (len(scores), [sum(within_leash(scores, leash)) for leash in self.leashes])
            )

    def choose_movement(self, obs, choices, rng):
        _features, scores = self.character.movement_scores(obs, choices)
        self._count("move", list(scores))
        return self.character.choose_movement(obs, choices, rng)

    def choose_suggestion(self, obs, room, rng):
        for kind, category in (("suspect", SUSPECTS), ("weapon", WEAPONS)):
            _candidates, scores = self.character.suggestion_scores(obs, category)
            self._count(kind, list(scores))
        return self.character.choose_suggestion(obs, room, rng)


def _plum(method: str) -> Character:
    if method == "PlumOG":
        return Character(ExactEnumAgent(), profile=PLUM_OG)
    return build_character("Plum")


def measure(method: str, roster: tuple, n_players: int, n_games: int, seed: int, leashes: tuple) -> dict:
    """Play `n_games` as the arena would (same seats, seeds and fill bots)
    with `method` in Plum's seat, and summarise his menu widths."""
    characters = {label: build_character(label) for label in roster if label != "Plum"}
    measured = _Measured(_plum(method), leashes)
    characters["Plum"] = measured
    for label, character in characters.items():
        (character.character if label == "Plum" else character).reset(seed)
    started = time.perf_counter()
    for g in range(n_games):
        lineup, suspects = seat_lineup(lineup_for_game(roster, g, n_players))
        game_seed = seed + g
        players = {}
        for seat, label in enumerate(lineup):
            if label in characters:
                players[seat] = characters[label]
                characters[label].new_game(lineup)
            else:
                players[seat] = clude_constraints.FloorBot(rng=Random(fill_seed(game_seed, seat)))
        engine.run_game(
            n_players, players, seed=game_seed, observer=clude_constraints.observe, suspects=suspects,
        )
    summary = {"method": method, "games": n_games, "seconds": time.perf_counter() - started, "kinds": {}}
    for kind in KINDS + ("all",):
        rows = (
            [row for k in KINDS for row in measured.widths[k]] if kind == "all" else measured.widths[kind]
        )
        if not rows:
            continue
        summary["kinds"][kind] = {
            "menus": len(rows),
            "mean_options": sum(n for n, _ in rows) / len(rows),
            "mean_allowed": {
                f"{leash:.2f}": sum(a[i] for _, a in rows) / len(rows) for i, leash in enumerate(leashes)
            },
            "multi_allowed": {
                f"{leash:.2f}": sum(a[i] > 1 for _, a in rows) / len(rows) for i, leash in enumerate(leashes)
            },
        }
    return summary


def _print(summary: dict, leashes: tuple) -> None:
    print(f"\n{summary['method']}: {summary['games']} games, {summary['seconds']:.0f}s")
    head = f"{'kind':<9}{'menus':>7}{'options':>9}" + "".join(f"{leash:>7.2f}" for leash in leashes)
    print(head + "   (mean options allowed)")
    for kind, row in summary["kinds"].items():
        cells = "".join(f"{row['mean_allowed'][f'{leash:.2f}']:>7.2f}" for leash in leashes)
        print(f"{kind:<9}{row['menus']:>7}{row['mean_options']:>9.2f}{cells}")
    print(f"{'':<25}" + "".join(f"{leash:>7.2f}" for leash in leashes) + "   (share with 2+ allowed)")
    for kind, row in summary["kinds"].items():
        cells = "".join(f"{row['multi_allowed'][f'{leash:.2f}']:>7.2f}" for leash in leashes)
        print(f"{kind:<25}{cells}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--games", type=int, default=24)
    parser.add_argument("--seed", type=int, default=7007)
    parser.add_argument("--roster", default="Plum,Mustard,Green")
    parser.add_argument("--players", type=int, default=3)
    parser.add_argument("--methods", default="Plum,PlumOG", help="Which of Plum and PlumOG to measure.")
    parser.add_argument("--json", default="", help="Also write both summaries to this JSON path.")
    args = parser.parse_args(argv)
    roster = tuple(args.roster.split(","))
    if "Plum" not in roster:
        raise SystemExit("the roster must seat Plum")
    results = []
    for method in args.methods.split(","):
        summary = measure(method, roster, args.players, args.games, args.seed, LEASHES)
        _print(summary, LEASHES)
        results.append(summary)
        if args.json:  # after each method, so a long PlumOG run leaves the first behind
            Path(args.json).parent.mkdir(parents=True, exist_ok=True)
            Path(args.json).write_text(json.dumps(results, indent=2), encoding="utf-8")
    if len(results) == 2:
        og = results[1]["kinds"]["all"]["mean_allowed"]["0.25"]
        new = results[0]["kinds"]["all"]["mean_allowed"]
        match = min(new, key=lambda leash: abs(new[leash] - og))
        print(f"\nPlumOG at 0.25 allows {og:.2f} options a menu; Plum's nearest is leash {match} ({new[match]:.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
