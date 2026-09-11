"""CLI: play one headless game with uniform-random dumb bots.

Usage
-----
    python scripts/play_game.py --players 4 --seed 1 [--verbose]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from clude_core.bots import RandomBot
from clude_core.engine import run_game
from clude_core.events import AccusationEvent, GameOverEvent, MoveEvent, SuggestionEvent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--players", type=int, default=4)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-turns", type=int, default=300)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    bots = {p: RandomBot() for p in range(args.players)}
    state, events = run_game(args.players, bots, seed=args.seed, max_turns=args.max_turns)

    if args.verbose:
        for event in events:
            if isinstance(event, MoveEvent):
                tag = " (secret passage)" if event.used_secret_passage else ""
                print(f"turn {event.turn}: player {event.player} -> {event.destination}{tag}")
            elif isinstance(event, SuggestionEvent):
                s = event.suggestion
                outcome = (
                    f"refuted by {s.refuter}" if s.refuter is not None else "no refutation"
                )
                print(f"turn {event.turn}: player {s.suggester} suggests "
                      f"{s.suspect}/{s.weapon}/{s.room} -- {outcome}")
            elif isinstance(event, AccusationEvent):
                a = event.accusation
                print(f"turn {event.turn}: player {a.accuser} accuses "
                      f"{a.suspect}/{a.weapon}/{a.room} -- "
                      f"{'CORRECT' if a.correct else 'wrong'}")

    final = events[-1]
    assert isinstance(final, GameOverEvent)
    print(f"\nEnvelope: {final.solution}")
    print(f"Turns played: {state.turn}")
    if final.winner is not None:
        suspect = state.suspects_in_play[final.winner]
        print(f"Winner: player {final.winner} ({suspect})")
    else:
        print("No winner -- every player accused incorrectly.")


if __name__ == "__main__":
    main()
