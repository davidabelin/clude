"""Lightweight entry point for Plum training.

On Windows, multiprocessing spawn re-executes this file in every rollout
worker as ``__mp_main__``. Keep that path free of PyTorch imports: workers run
the importable ``clude_training.rollout._play_task`` function and do not need
the training network or CUDA libraries.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ != "__mp_main__":
    from clude_training.plum_trainer import *  # noqa: F401,F403
    from clude_training.plum_trainer import main as _main


if __name__ == "__main__":
    _main()
