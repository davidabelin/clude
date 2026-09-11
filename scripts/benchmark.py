"""CLI: run the Phase 4 belief-quality benchmark and print a table.

Usage
-----
    python scripts/benchmark.py --games 60 --seed 4004
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from clude_training.benchmark import DEFAULT_CHECKPOINTS, DEFAULT_N_GAMES, DEFAULT_SEED, run_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=DEFAULT_N_GAMES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--checkpoints", type=float, nargs="+", default=list(DEFAULT_CHECKPOINTS),
        help="Fractions of each game's suggestions to snapshot at (e.g. 0.5 1.0).",
    )
    args = parser.parse_args()

    result = run_benchmark(n_games=args.games, seed=args.seed, checkpoints=tuple(args.checkpoints))
    print(result.summary_table())


if __name__ == "__main__":
    main()
