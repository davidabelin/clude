"""Seeded play must not depend on the Python process: same seed, same
game, whatever PYTHONHASHSEED is. The engine's golden fingerprints cover
RandomBot games; this covers the one agent that iterates holder sets,
Plum's enumeration, on the path where it matters -- the sampling
fallback a 6-player opening always takes."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

PLUM_OPENING = """
import json, random
from clude_agents import build_agent
from clude_constraints import observe
from clude_core import engine

state = engine.setup(6, random.Random(3))
obs = observe(state, 0)
agent = build_agent("Plum")
agent.reset(11)
belief = agent.select_action(obs)
print(json.dumps({
    "probabilities": {c: round(p, 12) for c, p in sorted(belief.probabilities.items())},
    "extra": belief.extra,
}, default=str, sort_keys=True))
"""


def _run_under_hash_seed(script: str, hash_seed: str) -> dict:
    env = dict(os.environ, PYTHONHASHSEED=hash_seed, PYTHONPATH=str(REPO))
    proc = subprocess.run(
        [sys.executable, "-c", script], env=env, cwd=REPO, capture_output=True, text=True, timeout=300,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_plum_sampled_belief_is_identical_across_hash_seeds():
    a = _run_under_hash_seed(PLUM_OPENING, "1")
    b = _run_under_hash_seed(PLUM_OPENING, "2")
    assert "sampled" in json.dumps(a["extra"]), a["extra"]  # the path that iterates holder sets
    assert a == b
