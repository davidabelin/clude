"""Every number a Wikiclude article quotes, in one place.

Two kinds, and an article may use no other:

``{{fact:key}}`` -- a **measured** number. Each is copied here once from
the doc that records it, with the heading it sits under and the text it
appears in, and `tests/test_wiki.py` checks every one against that doc.
When something is re-measured, the line here changes and every article
follows. `docs/` is not in the Cloud Run image, so the values live here
and the docs are read only by the test.

``{{code:key}}`` -- a **constant or a computed example**, read from the
live modules when the wiki is built: Scarlett's boost, Plum's budgets,
a preset's dials, and the worked examples the articles walk through,
which are run through the real agents so an article cannot disagree
with the code it describes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from math import comb, factorial

GLOSSARY = "docs/strategy-glossary.md"


@dataclass(frozen=True)
class Fact:
    """One measured number: how the article prints it, and where it is
    from. `find` is the text that must appear under `heading` in `doc`
    (the value itself when empty)."""

    value: str
    doc: str
    heading: str
    find: str = ""


@dataclass(frozen=True)
class Table:
    """One measured table. `rows` maps a row key to ``(label, literal)``:
    the label as an article shows it (wiki markup allowed) and the row
    exactly as the doc has it, which is both the data and what the test
    looks for. `keys` names the columns after the first for
    ``{{fact:table.row.key}}``; `columns` heads them in an article."""

    doc: str
    heading: str
    columns: tuple
    keys: tuple
    rows: dict

    def cells(self, row: str) -> list:
        """The row's values after its label, as the doc prints them."""
        literal = self.rows[row][1]
        return [c.strip().replace("**", "") for c in literal.strip().strip("|").split("|")][1:]


_SUSPECT_LABELS = {
    "Scarlett": "[[Miss Scarlett|Scarlett]]", "Mustard": "[[Colonel Mustard|Mustard]]",
    "White": "[[Mrs. White|White]]", "Green": "[[Mr. Green|Green]]",
    "Peacock": "[[Mrs. Peacock|Peacock]]",
    "uniform": "[[Uniform baseline|uniform (baseline)]]",
}
"""Row labels for the measured tables. Plum appears only in the Phase 14
tables, whose rows name him in their literals; the pre-Phase-12
enumeration agent's rows were removed from the public corpus on
2026-11-01 and stay in the glossary."""

_PLUM = "[[Professor Plum|Plum]]"
DEEPNASH_PLAN = "docs/deepnash-plan.md"
_PHASE14_PLUM = "Phase 14 Run 3, the current Plum (2026-10-18)"
_SIX = "Six-method belief benchmark (2026-11-01)"
_SIX_ARENA = "Six-character arena (2026-11-01)"
_PACING = "Reaction-queue pacing (2026-11-01)"
_TWIN = "Plum twin comparison at his three-seat table (2026-11-01)"
_PHASE14_DIALS = "Phase 14 dial recalibration (2026-10-18)"
_PHASE14_METHODS = "Phase 14 adaptive-method validation (2026-10-17)"
_RUN1 = "The first long run, `run150a` (2026-10-06)"
_RUN2 = "The second run, `run2`, and the export (2026-10-06)"

# The glossary headings the facts below are found under, named once.
_BENCH_GRID = "Belief benchmark on the grid (Stage 1a)"
_PHASE4 = "Phase 4 benchmark results (RandomBot regime, historical)"
_MEMORY = "Phase 7: memory (2026-09-14)"
_LANDING = "The landing rule (Phase 8.0.4, 2026-09-18)"
_SELF_PLAY = "Self-play regimes: `RandomBot` and `FloorBot` (Phase 5b)"

TABLES: dict = {
    # The six methods' beliefs scored on the Classic board, 2026-09-15.
    "bench.grid": Table(
        GLOSSARY, "Belief benchmark on the grid (Stage 1a)",
        ("Method", "25%", "50%", "75%", "100%", "Top-1 at 100%", "ms per call at 50%"),
        ("25", "50", "75", "100", "top1", "ms"),
        {
            "White": (_SUSPECT_LABELS["White"], "| White | 1.54 | 1.28 | 0.91 | 0.23 | 0.91 | 0.1 |"),
            "Mustard": (_SUSPECT_LABELS["Mustard"], "| Mustard | 1.57 | 1.34 | 0.99 | 0.19 | 0.93 | 0.2 |"),
            "Green": (_SUSPECT_LABELS["Green"], "| Green | 1.55 | 1.38 | 0.97 | 0.20 | 0.93 | 524 |"),
            "uniform": (_SUSPECT_LABELS["uniform"], "| uniform (baseline) | 1.57 | 1.35 | 1.01 | 0.29 | 0.83 | - |"),
            "Scarlett": (_SUSPECT_LABELS["Scarlett"], "| Scarlett | 1.62 | 1.48 | 1.18 | 0.30 | 0.87 | 0.1 |"),
            "Peacock": (_SUSPECT_LABELS["Peacock"], "| Peacock | 1.63 | 1.46 | 1.13 | 0.31 | 0.83 | 0.2 |"),
        },
    ),
}

# Candidate-selection losses use each method's own comparison state, not a
# common final six-method benchmark. Green's candidate starts fresh; its
# comparator is the frozen pre-training live posterior.
_METHOD_LOSS_ROWS = {
    "mustard.former": (_SUSPECT_LABELS["Mustard"], "| Mustard | Former | 1.3385 | 1.0747 | 0.7932 | 0.2308 |"),
    "mustard.rebuilt": (_SUSPECT_LABELS["Mustard"], "| Mustard | Rebuilt | 1.3073 | 1.0638 | 0.7283 | 0.2152 |"),
    "white.former": (_SUSPECT_LABELS["White"], "| White | Former | 1.3801 | 1.1464 | 0.7569 | 0.3233 |"),
    "white.rebuilt": (_SUSPECT_LABELS["White"], "| White | Rebuilt | 1.3792 | 1.1487 | 0.7598 | 0.3246 |"),
    "green.former": (_SUSPECT_LABELS["Green"], "| Green | Former | 1.3243 | 1.2190 | 0.7963 | 0.2985 |"),
    "green.rebuilt": (_SUSPECT_LABELS["Green"], "| Green | Rebuilt | 1.2262 | 1.0500 | 0.6790 | 0.3114 |"),
}
for _method in ("loss", "mustard", "white", "green"):
    TABLES[f"methods.phase14.{_method}"] = Table(
        GLOSSARY, _PHASE14_METHODS,
        ("Method", "State", "25%", "50%", "75%", "100%"),
        ("state", "25", "50", "75", "100"),
        {key: row for key, row in _METHOD_LOSS_ROWS.items()
         if _method == "loss" or key.startswith(f"{_method}.")},
    )

# Current Phase 14 measurements and retained method evidence.
TABLES.update({
    # Phase 14: the current Run 3 weights, selected on 2026-10-18.
    "plum.phase14.tournament": Table(
        GLOSSARY, _PHASE14_PLUM,
        ("Network", "Games", "Wins", "Win %", "Wrong accusations"),
        ("games", "wins", "win", "wrong"),
        {
            "incumbent": ("Former incumbent", "| Former incumbent | 1,920 | 352 | 18.3 | 11 |"),
            "run1": ("Run 1", "| Run 1 | 1,920 | 423 | 22.0 | 8 |"),
            "run2": ("Run 2", "| Run 2 | 1,920 | 417 | 21.7 | 5 |"),
            "run3": ("Run 3", "| **Run 3** | **1,920** | **440** | **22.9** | **7** |"),
        },
    ),
    "plum.phase14.sizes": Table(
        GLOSSARY, _PHASE14_PLUM,
        ("Seats", "Games", "Run 3 wins", "Run 3 win %"),
        ("games", "wins", "win"),
        {
            "3": ("3", "| 3 | 480 | 171 | 35.6 |"),
            "4": ("4", "| 4 | 480 | 105 | 21.9 |"),
            "5": ("5", "| 5 | 480 | 83 | 17.3 |"),
            "6": ("6", "| 6 | 480 | 81 | 16.9 |"),
        },
    ),
    "plum.phase14.benchmark": Table(
        GLOSSARY, _PHASE14_PLUM,
        ("Network", "25%", "50%", "75%", "100%", "Top-1 at 100%", "ms per call at 50%"),
        ("25", "50", "75", "100", "top1", "ms"),
        {
            "incumbent": ("Former incumbent", "| Former incumbent | 1.442 | 1.137 | 0.761 | 0.222 | 0.928 | 0.245 |"),
            "run3": ("Run 3", "| **Run 3** | **1.459** | **1.157** | **0.755** | **0.220** | **0.927** | **0.234** |"),
            "uniform": ("Uniform floor baseline", "| Uniform floor baseline | 1.570 | 1.322 | 0.983 | 0.356 | 0.789 | - |"),
        },
    ),
    "arena.phase14": Table(
        GLOSSARY, _PHASE14_DIALS,
        ("Character", "Seat-games", "Won %", "Accused wrongly %", "First accusation (turn)",
         "Never accused %", "Own cards shown", "Own cards named", "Re-shown %"),
        ("games", "win", "wrong", "first", "never", "leaked", "named", "reshow"),
        {
            "Scarlett": (_SUSPECT_LABELS["Scarlett"], "| Scarlett | 40 | 20.0 | 35.0 | 43.0 | 45.0 | 3.23 | 1.05 | 39.1 |"),
            "Mustard": (_SUSPECT_LABELS["Mustard"], "| Mustard | 40 | 22.5 | 0.0 | 46.7 | 77.5 | 3.10 | 1.68 | 34.9 |"),
            "White": (_SUSPECT_LABELS["White"], "| White | 40 | 25.0 | 2.5 | 38.5 | 72.5 | 2.70 | 2.98 | 48.7 |"),
            "Green": (_SUSPECT_LABELS["Green"], "| Green | 40 | 15.0 | 2.5 | 40.7 | 82.5 | 2.70 | 0.93 | 43.2 |"),
            "Peacock": (_SUSPECT_LABELS["Peacock"], "| Peacock | 40 | 22.5 | 0.0 | 38.4 | 77.5 | 2.30 | 0.75 | 35.3 |"),
            "Plum": (_PLUM, "| Plum | 40 | 20.0 | 0.0 | 31.8 | 80.0 | 2.62 | 1.57 | 50.0 |"),
        },
    ),
    "sweep.phase14.accuse_threshold": Table(
        GLOSSARY, _PHASE14_DIALS,
        ("Accusation threshold", "Seat-games", "Won %", "Wrong %", "First accusation", "Never accused %", "Mean turns"),
        ("games", "win", "wrong", "first", "never", "turns"),
        {
            "0.2": ("0.2", "| 0.2 | 500 | 18.6 | 38.6 | 33.14 | 42.8 | 36.00 |"),
            "0.4": ("0.4", "| 0.4 | 500 | 22.4 | 15.6 | 37.84 | 62.0 | 38.47 |"),
            "0.6": ("0.6", "| 0.6 | 500 | 22.8 | 4.4 | 38.79 | 72.8 | 39.28 |"),
            "0.8": ("0.8", "| 0.8 | 500 | 19.6 | 1.0 | 39.50 | 79.4 | 39.82 |"),
            "1.0": ("1.0", "| 1.0 | 500 | 19.8 | 0.0 | 38.56 | 80.2 | 40.06 |"),
        },
    ),
    "sweep.phase14.bluff_rate": Table(
        GLOSSARY, _PHASE14_DIALS,
        ("Bluff rate", "Seat-games", "Won %", "Wrong %", "Never accused %", "Own cards named", "Mean turns"),
        ("games", "win", "wrong", "never", "named", "turns"),
        {
            "0": ("0", "| 0 | 500 | 21.4 | 3.4 | 75.2 | 1.04 | 41.16 |"),
            "0.25": ("0.25", "| 0.25 | 500 | 18.6 | 4.8 | 76.6 | 1.82 | 38.73 |"),
            "0.5": ("0.5", "| 0.5 | 500 | 17.6 | 8.0 | 74.4 | 2.76 | 41.28 |"),
            "1.0": ("1.0", "| 1.0 | 500 | 5.4 | 10.8 | 83.8 | 4.28 | 48.74 |"),
        },
    ),
    "sweep.phase14.curiosity": Table(
        GLOSSARY, _PHASE14_DIALS,
        ("Curiosity", "Seat-games", "Won %", "Wrong %", "Never accused %", "Suggestions", "Mean turns"),
        ("games", "win", "wrong", "never", "suggestions", "turns"),
        {
            "0": ("0", "| 0 | 418 | 24.2 | 6.5 | 69.4 | 4.25 | 38.70 |"),
            "0.5": ("0.5", "| 0.5 | 418 | 17.5 | 6.9 | 75.6 | 3.55 | 40.97 |"),
            "1.0": ("1.0", "| 1.0 | 418 | 11.0 | 4.3 | 84.7 | 1.81 | 49.06 |"),
        },
    ),
    "sweep.phase14.secrecy": Table(
        GLOSSARY, _PHASE14_DIALS,
        ("Secrecy", "Seat-games", "Won %", "Wrong %", "Own cards shown", "Re-shown %", "Mean turns"),
        ("games", "win", "wrong", "leaked", "reshow", "turns"),
        {
            "0": ("0", "| 0 | 500 | 21.2 | 6.6 | 2.84 | 31.5 | 41.47 |"),
            "0.5": ("0.5", "| 0.5 | 500 | 22.2 | 5.2 | 2.75 | 39.5 | 39.70 |"),
            "1.0": ("1.0", "| 1.0 | 500 | 20.8 | 4.6 | 2.76 | 44.4 | 38.94 |"),
        },
    ),
    "sweep.phase14.temperature": Table(
        GLOSSARY, _PHASE14_DIALS,
        ("Temperature", "Seat-games", "Won %", "Wrong %", "Never accused %", "Suggestions", "Mean turns"),
        ("games", "win", "wrong", "never", "suggestions", "turns"),
        {
            "0": ("0", "| 0 | 500 | 23.6 | 6.4 | 70.0 | 4.53 | 34.30 |"),
            "0.05": ("0.05", "| 0.05 | 500 | 24.0 | 5.8 | 70.2 | 4.37 | 35.13 |"),
            "0.1": ("0.1", "| 0.1 | 500 | 19.6 | 5.6 | 74.8 | 3.97 | 37.33 |"),
            "0.2": ("0.2", "| 0.2 | 500 | 15.8 | 4.0 | 80.2 | 3.25 | 44.52 |"),
            "0.5": ("0.5", "| 0.5 | 500 | 5.8 | 3.6 | 90.6 | 2.00 | 51.73 |"),
            "2.0": ("2.0", "| 2.0 | 500 | 3.4 | 2.4 | 94.2 | 1.43 | 53.77 |"),
        },
    ),
    "paid.phase14.leash": Table(
        GLOSSARY, _PHASE14_DIALS,
        ("Character and leash", "Games", "Won %", "Wrong %", "Model calls", "List-price cost"),
        ("games", "win", "wrong", "calls", "cost"),
        {
            "Scarlett 0": ("Scarlett, 0", "| Scarlett, 0 | 8 | 12.5 | 25.0 | 45 | $0.3643 |"),
            "Scarlett 0.25": ("Scarlett, 0.25 (preset)", "| Scarlett, 0.25 (preset) | 8 | 12.5 | 25.0 | 63 | $0.5741 |"),
            "Scarlett 0.5": ("Scarlett, 0.5", "| Scarlett, 0.5 | 8 | 0.0 | 50.0 | 108 | $1.0493 |"),
            "Scarlett 1": ("Scarlett, 1", "| Scarlett, 1 | 8 | 25.0 | 37.5 | 198 | $2.0394 |"),
            "Mustard 0": ("Mustard, 0", "| Mustard, 0 | 8 | 62.5 | 0.0 | 42 | $0.3375 |"),
            "Mustard 0.25": ("Mustard, 0.25 (preset)", "| Mustard, 0.25 (preset) | 8 | 87.5 | 0.0 | 74 | $0.6860 |"),
            "Mustard 0.5": ("Mustard, 0.5", "| Mustard, 0.5 | 8 | 50.0 | 0.0 | 87 | $0.8270 |"),
            "Mustard 1": ("Mustard, 1", "| Mustard, 1 | 8 | 75.0 | 0.0 | 206 | $2.1955 |"),
            "White 0": ("White, 0", "| White, 0 | 8 | 62.5 | 0.0 | 34 | $0.3021 |"),
            "White 0.25": ("White, 0.25 (preset)", "| White, 0.25 (preset) | 8 | 75.0 | 0.0 | 60 | $0.5678 |"),
            "White 0.5": ("White, 0.5", "| White, 0.5 | 8 | 100.0 | 0.0 | 96 | $0.9789 |"),
            "White 1": ("White, 1", "| White, 1 | 8 | 100.0 | 0.0 | 165 | $1.7100 |"),
            "Green 0": ("Green, 0", "| Green, 0 | 8 | 0.0 | 0.0 | 15 | $0.1193 |"),
            "Green 0.25": ("Green, 0.25 (preset)", "| Green, 0.25 (preset) | 8 | 37.5 | 0.0 | 49 | $0.4471 |"),
            "Green 0.5": ("Green, 0.5", "| Green, 0.5 | 8 | 50.0 | 0.0 | 92 | $0.9455 |"),
            "Green 1": ("Green, 1", "| Green, 1 | 8 | 87.5 | 0.0 | 125 | $1.2635 |"),
            "Peacock 0": ("Peacock, 0", "| Peacock, 0 | 8 | 25.0 | 0.0 | 38 | $0.3513 |"),
            "Peacock 0.25": ("Peacock, 0.25 (preset)", "| Peacock, 0.25 (preset) | 8 | 0.0 | 0.0 | 57 | $0.5531 |"),
            "Peacock 0.5": ("Peacock, 0.5", "| Peacock, 0.5 | 8 | 25.0 | 0.0 | 111 | $1.2008 |"),
            "Peacock 1": ("Peacock, 1", "| Peacock, 1 | 8 | 0.0 | 0.0 | 212 | $2.4147 |"),
            "Plum 0": ("Plum, 0", "| Plum, 0 | 8 | 12.5 | 0.0 | 18 | $0.1419 |"),
            "Plum 0.35": ("Plum, 0.35 (preset)", "| Plum, 0.35 (preset) | 8 | 12.5 | 0.0 | 87 | $0.9441 |"),
            "Plum 0.6": ("Plum, 0.6", "| Plum, 0.6 | 8 | 50.0 | 0.0 | 115 | $1.3070 |"),
            "Plum 1": ("Plum, 1", "| Plum, 1 | 8 | 37.5 | 0.0 | 212 | $2.5089 |"),
        },
    ),
    "paid.phase14.chattiness": Table(
        GLOSSARY, _PHASE14_DIALS,
        ("Chattiness", "Games", "Opportunities", "Off-turn calls", "Spoken lines", "List-price cost"),
        ("games", "opportunities", "calls", "spoken", "cost"),
        {
            "0": ("0", "| 0 | 8 | 183 | 0 | 0 | $0.0000 |"),
            "0.25": ("0.25", "| 0.25 | 8 | 183 | 90 | 90 | $0.6506 |"),
            "0.5": ("0.5 (preset)", "| 0.5 (preset) | 8 | 183 | 210 | 210 | $1.6490 |"),
            "0.75": ("0.75", "| 0.75 | 8 | 183 | 275 | 275 | $2.1923 |"),
            "1": ("1", "| 1 | 8 | 183 | 288 | 288 | $2.2687 |"),
        },
    ),
    "paid.phase14.memory": Table(
        GLOSSARY, _PHASE14_DIALS,
        ("Memory depth", "Games", "Seat-games", "Wins", "Wrong accusations", "Model calls", "List-price cost"),
        ("games", "seat_games", "wins", "wrong", "calls", "cost"),
        {
            "0": ("0", "| 0 | 8 | 32 | 8 | 1 | 297 | $3.4689 |"),
            "0.25": ("0.25", "| 0.25 | 8 | 32 | 8 | 0 | 292 | $3.6626 |"),
            "0.5": ("0.5", "| 0.5 | 8 | 32 | 8 | 0 | 298 | $3.7503 |"),
            "0.75": ("0.75", "| 0.75 | 8 | 32 | 8 | 2 | 386 | $6.7857 |"),
            "1": ("1", "| 1 | 8 | 32 | 8 | 1 | 303 | $5.0502 |"),
        },
    ),
    # The six released characters against one another, headless, 2026-11-01.
    "arena.six": Table(
        GLOSSARY, _SIX_ARENA,
        ("Character", "Seat-games", "Won %", "Accused wrongly %", "First accusation (turn)",
         "Never accused %", "Own cards shown", "Own cards named", "Re-shown %"),
        ("games", "win", "wrong", "first", "never", "leaked", "named", "reshow"),
        {
            "Scarlett": (_SUSPECT_LABELS["Scarlett"], '| Scarlett | 400 | 15.5 | 26.2 | 46.1 | 58.2 | 2.74 | 1.10 | 50.1 |'),
            "Mustard": (_SUSPECT_LABELS["Mustard"], '| Mustard | 320 | 21.2 | 5.9 | 46.2 | 72.8 | 2.39 | 1.47 | 40.5 |'),
            "White": (_SUSPECT_LABELS["White"], '| White | 400 | 31.8 | 0.5 | 47.9 | 67.8 | 2.38 | 3.07 | 45.9 |'),
            "Green": (_SUSPECT_LABELS["Green"], '| Green | 320 | 19.1 | 2.8 | 49.8 | 78.1 | 2.37 | 1.43 | 35.9 |'),
            "Peacock": (_SUSPECT_LABELS["Peacock"], '| Peacock | 400 | 26.2 | 0.0 | 47.9 | 73.8 | 2.03 | 1.18 | 46.7 |'),
            "Plum": (_PLUM, '| Plum | 320 | 17.8 | 0.3 | 42.9 | 81.9 | 2.08 | 1.73 | 28.1 |'),
        },
    ),
    # The six released methods on the Run 3 snapshots, 2026-11-01.
    "bench.six": Table(
        GLOSSARY, _SIX,
        ("Method", "25%", "50%", "75%", "100%", "Top-1 at 100%", "ms per call at 50%"),
        ("25", "50", "75", "100", "top1", "ms"),
        {
            "Mustard": (_SUSPECT_LABELS["Mustard"], "| Mustard | 1.472 | 1.149 | 0.840 | 0.192 | 0.932 | 0.114 |"),
            "Green": (_SUSPECT_LABELS["Green"], "| Green | 1.450 | 1.117 | 0.773 | 0.205 | 0.927 | 0.660 |"),
            "Plum": (_PLUM, "| Plum | 1.459 | 1.157 | 0.755 | 0.220 | 0.927 | 0.302 |"),
            "White": (_SUSPECT_LABELS["White"], "| White | 1.523 | 1.244 | 0.869 | 0.274 | 0.905 | 0.064 |"),
            "uniform": (_SUSPECT_LABELS["uniform"], "| uniform (baseline) | 1.570 | 1.322 | 0.983 | 0.356 | 0.789 | - |"),
            "Peacock": (_SUSPECT_LABELS["Peacock"], "| Peacock | 1.646 | 1.430 | 1.043 | 0.375 | 0.790 | 0.140 |"),
            "Scarlett": (_SUSPECT_LABELS["Scarlett"], "| Scarlett | 1.650 | 1.473 | 1.175 | 0.403 | 0.829 | 0.028 |"),
        },
    ),
    # The reaction queue replayed offline, 2026-11-01.
    "pacing.harness": Table(
        GLOSSARY, _PACING,
        ("Inputs, chattiness", "Games", "Opportunities", "Draws", "Joined and served", "Turns at three",
         "Full at a trigger", "Skipped by the break", "Stale drops", "Games at the cap", "Projected cost"),
        ("games", "opportunities", "draws", "served", "three", "full", "skipped", "stale", "cap", "cost"),
        {
            "web2.presets": ("Real tables (`web-2`), current presets", "| web-2, presets | 15 | 626 | 1,281 | 388 | 42 | 8 | 106 | 82 | 6 | $3.05 |"),
            "web2.one": ("Real tables (`web-2`), chattiness 1.0", "| web-2, 1.0 | 15 | 471 | 579 | 579 | 130 | 20 | 276 | 153 | 12 | $4.55 |"),
            "preflight.presets": ("Arena games, current presets", "| preflight, presets | 8 | 272 | 726 | 190 | 20 | 0 | 38 | 0 | 1 | $1.49 |"),
            "preflight.one": ("Arena games, chattiness 1.0", "| preflight, 1.0 | 8 | 207 | 314 | 314 | 100 | 0 | 207 | 0 | 7 | $2.47 |"),
        },
    ),
    "twin.phase14": Table(
        GLOSSARY, _TWIN,
        ("Leg", "Games", "Wins", "Won %", "Wrong accusations", "Mean turns", "Model calls", "List-price cost"),
        ("games", "wins", "win", "wrong", "turns", "calls", "cost"),
        {
            "headless": ("Headless", '| Headless | 24 | 7 | 29.2 | 1 | 47.62 | - | $0.0000 |'),
            "model": ("With the model, no logbook", '| Model, no logbook | 24 | 6 | 25.0 | 1 | 46.88 | 426 | $5.3430 |'),
            "memory": ("With the model and his logbook at memory 1", '| Model, logbook at memory 1 | 24 | 16 | 66.7 | 0 | 41.62 | 406 | $6.7333 |'),
        },
    ),
    "pacing.seat": Table(
        GLOSSARY, _PACING,
        ("Position in the scan", "Eligible", "Drew", "Joined and served", "Never reached"),
        ("eligible", "drew", "served", "skipped"),
        {
            "1": ("1st", "| 1st | 406 | 406 | 158 | 0 |"),
            "2": ("2nd", "| 2nd | 409 | 405 | 103 | 4 |"),
            "3": ("3rd", "| 3rd | 304 | 287 | 87 | 17 |"),
            "4": ("4th", "| 4th | 165 | 131 | 31 | 34 |"),
            "5": ("5th", "| 5th | 68 | 36 | 8 | 32 |"),
            "6": ("6th", "| 6th | 35 | 16 | 1 | 19 |"),
        },
    ),
    "paid.phase14.plum_leash_confirm": Table(
        GLOSSARY, _PHASE14_DIALS,
        ("Plum leash", "Games", "Wins", "Won %", "Wrong accusations", "Mean turns", "Model calls", "List-price cost"),
        ("games", "wins", "win", "wrong", "turns", "calls", "cost"),
        {
            "0.35": ("0.35 (preset)", "| 0.35 (preset) | 24 | 9 | 37.5 | 0 | 33.46 | 327 | $3.5642 |"),
            "0.6": ("0.60 (candidate)", "| 0.60 (candidate) | 24 | 6 | 25.0 | 0 | 35.79 | 432 | $5.0363 |"),
        },
    ),
})

FACTS: dict = {
    "cost.web.games": Fact("9", "docs/web.md", "A table", "first nine web games with model seats"),
    "cost.web.debrief.share": Fact("38", "docs/web.md", "A table", "38% of"),
    "cost.web.debrief.total": Fact("1.69", "docs/web.md", "A table", "$1.69 of $4.40"),
    "cost.web.total": Fact("4.40", "docs/web.md", "A table", "$1.69 of $4.40"),
    "bench.grid.snapshots": Fact("1,080", GLOSSARY, "Belief benchmark on the grid (Stage 1a)", "1080 snapshots"),
    "bench.grid.games": Fact("60", GLOSSARY, "Belief benchmark on the grid (Stage 1a)", "benchmark --games 60 --seed 4004"),
    "bench.zero_cost": Fact("20.7", GLOSSARY, "Belief benchmark, FloorBot regime (Phase 5)", "a hard 0 on the true card would cost 20.7"),
    "plum.fallback.calls": Fact("490", GLOSSARY, "Belief benchmark on the grid (Stage 1a)", "490 of 1080 calls"),
    "plum.landing.passage": Fact("0.50", GLOSSARY, _LANDING, "scored 0.50 at curiosity 0.5 against 0.29"),
    "plum.landing.walk": Fact("0.29", GLOSSARY, _LANDING, "scored 0.50 at curiosity 0.5 against 0.29"),
    "landing.turns.before": Fact("53.9", GLOSSARY, _LANDING, "| `arena-grid-tuned-24` (3-6 seats, baseline) | 53.9 | 29.0 | 229 | 600 / 597 |"),
    "landing.turns.after": Fact("45.9", GLOSSARY, _LANDING, "| `arena-grid-prox2-24` (kept) | **45.9** | 18.4 | 127 | 390 / 660 |"),
    "landing.suggestions.before": Fact("29.0", GLOSSARY, _LANDING, "| `arena-grid-tuned-24` (3-6 seats, baseline) | 53.9 | 29.0 | 229 | 600 / 597 |"),
    "landing.suggestions.after": Fact("18.4", GLOSSARY, _LANDING, "| `arena-grid-prox2-24` (kept) | **45.9** | 18.4 | 127 | 390 / 660 |"),
    # The benchmarks' sizes, and the historical one.
    "phase4.games": Fact("60", GLOSSARY, _PHASE4, "60 `RandomBot` games"),
    "scarlett.phase4": Fact("0.49", GLOSSARY, _PHASE4, "Scarlett 0.49"),
    "peacock.phase4": Fact("0.53", GLOSSARY, _PHASE4, "Peacock 0.53"),
    "uniform.phase4": Fact("0.47", GLOSSARY, _PHASE4, "uniform 0.47"),
    "green.phase4": Fact("0.60", GLOSSARY, _PHASE4, "Green 0.60"),
    "mustard.phase4": Fact("0.91", GLOSSARY, _PHASE4, "Mustard 0.91"),
    "white.phase4": Fact("1.73", GLOSSARY, _PHASE4, "White 1.73 log-loss"),
    "mustard.phase4.zeros": Fact("69", GLOSSARY, _PHASE4, "69% and 79% of their log-loss"),
    "white.phase4.zeros": Fact("79", GLOSSARY, _PHASE4, "69% and 79% of their log-loss"),
    "phase4.zero_categories": Fact("5-7", GLOSSARY, _PHASE4, "the 5-7% of categories"),
    # The floor's own games.
    "floor.suggestions": Fact("12-23", "docs/architecture.md", _SELF_PLAY, "FloorBot games end in about 12-23 suggestions"),
    "floor.solved": Fact("a third", "docs/architecture.md", _SELF_PLAY, "a third of viewers holding a proven envelope at the end"),
    "random.suggestions": Fact("80-180", "docs/architecture.md", _SELF_PLAY, "the old regime ran 80-180 suggestions"),
    # Arenas: how long a game ran.
    # Method memory, Phase 7.
    "mustard.memory.games": Fact("193", GLOSSARY, _MEMORY, "193 stored ladder games (10,703 rows)"),
    "mustard.memory.rows": Fact("10,703", GLOSSARY, _MEMORY, "193 stored ladder games (10,703 rows)"),
    "mustard.memory.held_out": Fact("8", GLOSSARY, _MEMORY, "scored on 8 held-out FloorBot games"),
    "mustard.memory.mid.before": Fact("1.50", GLOSSARY, _MEMORY, "mid-game log-loss 1.50 to 1.15"),
    "mustard.memory.mid.after": Fact("1.15", GLOSSARY, _MEMORY, "mid-game log-loss 1.50 to 1.15"),
    "mustard.memory.end.before": Fact("0.11", GLOSSARY, _MEMORY, "the end checkpoint 0.11 to 0.15 log-loss"),
    "mustard.memory.end.after": Fact("0.15", GLOSSARY, _MEMORY, "the end checkpoint 0.11 to 0.15 log-loss"),
    "mustard.memory.top1.before": Fact("0.99", GLOSSARY, _MEMORY, "0.99 to 0.94 top-1"),
    "mustard.memory.top1.after": Fact("0.94", GLOSSARY, _MEMORY, "0.99 to 0.94 top-1"),
    # Phase 12: the trained Plum.
    "policy.run.games": Fact("76,800", DEEPNASH_PLAN, _RUN1, "76,800 games"),
    "policy.run.minutes": Fact("40", DEEPNASH_PLAN, _RUN1, "under 40 minutes"),
    "policy.smoke.memorise": Fact("3.6", DEEPNASH_PLAN, "What the smoke runs taught", "midpoint log-loss to 3.6"),
    # Phase 14: the current Run 3 network.
    "phase14.plum.per_run": Fact("153,600", GLOSSARY, _PHASE14_PLUM, "153,600 games per network"),
    "phase14.plum.rollouts": Fact("460,800", GLOSSARY, _PHASE14_PLUM, "460,800 rollouts in all"),
    "phase14.plum.setups": Fact("230,400", GLOSSARY, _PHASE14_PLUM, "230,400 distinct seeded deal and line-up"),
    "phase14.plum.confirm.delta": Fact("4.9", GLOSSARY, _PHASE14_PLUM, "4.9 percentage points"),
    "phase14.plum.confirm.low": Fact("1.5", GLOSSARY, _PHASE14_PLUM, "from 1.5 to 8.3"),
    "phase14.plum.confirm.high": Fact("8.3", GLOSSARY, _PHASE14_PLUM, "from 1.5 to 8.3"),
    "phase14.plum.fixture.cost": Fact("0.0348", GLOSSARY, _PHASE14_PLUM, "for $0.0348"),
    "phase14.bench.games": Fact("120", GLOSSARY, _PHASE14_PLUM, "120-game, 2,160-snapshot"),
    "phase14.bench.snapshots": Fact("2,160", GLOSSARY, _PHASE14_PLUM, "120-game, 2,160-snapshot"),
    # The six released methods together, and the reaction queue's pacing (2026-11-01).
    "six.games": Fact("120", GLOSSARY, _SIX, "120 games, 2,160 snapshots"),
    "arena.six.games": Fact("480", GLOSSARY, _SIX_ARENA, "480 games at seed"),
    "arena.six.turns": Fact("46.75", GLOSSARY, _SIX_ARENA, "averaged 46.75 turns"),
    "six.snapshots": Fact("2,160", GLOSSARY, _SIX, "120 games, 2,160 snapshots"),
    "pacing.asplayed.reactions": Fact("403", GLOSSARY, _PACING, "403 off-turn lines"),
    "pacing.asplayed.three": Fact("56", GLOSSARY, _PACING, "47 carried one, 94 two and 56 three"),
    "pacing.overshoot": Fact("41", GLOSSARY, _PACING, "three, and\na game 41"),
    "pacing.depth.presets": Fact("60", GLOSSARY, _PACING, "328/60 at the presets"),
    "pacing.games_at_cap": Fact("six", GLOSSARY, _PACING, "binds in six of fifteen real games"),
    # Plum's paired legs (2026-11-01).
    "twin.phase14.model.delta": Fact("4.2", GLOSSARY, _TWIN, 'the model lost 4.2 paired win-rate points (95% interval -29.2 to +20.8)'),
    "twin.phase14.model.low": Fact("-29.2", GLOSSARY, _TWIN, 'the model lost 4.2 paired win-rate points (95% interval -29.2 to +20.8)'),
    "twin.phase14.model.high": Fact("+20.8", GLOSSARY, _TWIN, 'the model lost 4.2 paired win-rate points (95% interval -29.2 to +20.8)'),
    "twin.phase14.memory.delta": Fact("41.7", GLOSSARY, _TWIN, 'the logbook gained 41.7 paired win-rate points (95% interval +16.7 to +62.5)'),
    "twin.phase14.memory.low": Fact("+16.7", GLOSSARY, _TWIN, 'the logbook gained 41.7 paired win-rate points (95% interval +16.7 to +62.5)'),
    "twin.phase14.memory.high": Fact("+62.5", GLOSSARY, _TWIN, 'the logbook gained 41.7 paired win-rate points (95% interval +16.7 to +62.5)'),
    "twin.phase14.cost": Fact("12.0763", GLOSSARY, _TWIN, "$12.0763 at list price"),
}


def fact(key: str) -> str:
    """The printed value of a measured number.

    Raises
    ------
    KeyError
        If no fact or table cell has that key.
    """
    if key in FACTS:
        return FACTS[key].value
    for name, table in TABLES.items():
        if key.startswith(name + "."):
            row, _, column = key[len(name) + 1 :].rpartition(".")
            if row in table.rows and column in table.keys:
                return table.cells(row)[table.keys.index(column)]
    raise KeyError(key)


# --- constants and worked examples, from the live modules -------------------


def _trim(number: float, places: int = 3) -> str:
    """A float as an article prints it: no trailing zeros."""
    text = f"{number:.{places}f}".rstrip("0").rstrip(".")
    return text or "0"


ROPE_CARDS = ("White", "Peacock", "Rope", "Wrench")
"""The four cards the Rope question leaves open, in category order."""

ROPE_SEATS = {"me": 0, "holder": 1, "third": 2}
"""Who is who in the Rope question: the viewer, the seat that showed a
card (Colonel Mustard in the articles), and the seat that asked (Mr.
Green)."""

ROPE_ROOM = "Study"
"""The room the Rope question's floor has already proved."""

ROPE_TRUTH = ("White", "Wrench", ROPE_ROOM)
"""The envelope the articles reveal at the end of the Rope question, so
that Mr. Green's arms can be scored on it."""


@lru_cache(maxsize=4)
def rope_observation(times: int = 1):
    """The Rope question as one seat's `ClueObservation`, with the
    suggestion made `times` times (0 is the position before it).

    Late in a three-seat game, from seat 0's chair: every card is placed
    except two suspects (White, Peacock) and two weapons (Rope, Wrench).
    One of each is in the envelope; the other of each is in seat 1's
    hand, which has exactly two cards unplaced. Seat 2 then suggests
    Peacock with the Rope in the Hall, a room seat 2 holds; seat 0
    cannot answer, and seat 1 shows seat 2 a card seat 0 does not see:
    so seat 1 holds Peacock or the Rope, or both.
    """
    from clude_constraints import ENVELOPE, ConstraintResult
    from clude_core.domain import ROOMS, SUSPECTS, WEAPONS, Suggestion
    from clude_core.state import ClueObservation

    me, holder, third = ROPE_SEATS["me"], ROPE_SEATS["holder"], ROPE_SEATS["third"]
    hands = {
        me: ["Scarlett", "Mustard", "Candlestick", "Knife", "Kitchen", "Ballroom"],
        holder: ["Green", "Lead_Pipe", "Conservatory", "Billiard"],  # and two of the open cards
        third: ["Plum", "Revolver", "Library", "Hall", "Lounge", "Dining"],
    }
    possible = {card: frozenset({holder, ENVELOPE}) for card in ROPE_CARDS}
    possible[ROPE_ROOM] = frozenset({ENVELOPE})
    for seat, cards in hands.items():
        for card in cards:
            possible[card] = frozenset({seat})
    assert set(possible) == set(SUSPECTS + WEAPONS + ROOMS)
    asked = Suggestion(suggester=third, suspect="Peacock", weapon="Rope", room="Hall",
                       refuter=holder, shown_to=third, card_shown=None)
    mask = ConstraintResult(
        possible_holders=possible,
        or_constraints=((frozenset({"Peacock", "Rope"}), holder),) if times else (),
        hand_sizes={me: 6, holder: 6, third: 6},
    )
    return ClueObservation(
        n_players=3, my_index=me, own_hand=frozenset(hands[me]), active_players=(True, True, True),
        hand_sizes={me: 6, holder: 6, third: 6}, suggestion_log=(asked,) * times, accusation_log=(),
        turn=30, mask=mask, suspects_in_play=("Scarlett", "Mustard", "Green"),
    )


@lru_cache(maxsize=1)
def rope_question() -> dict:
    """The worked example the method articles share, run on the real
    code: every method's answer to one piece of evidence
    (`rope_observation`).

    Returns
    -------
    dict
        ``deals``: the consistent deals Plum's search finds, and
        ``nodes`` the steps it took; ``plum``: his exact envelope
        probabilities for the four open cards; ``scarlett``: hers after
        the suggestion has been made once, twice and three times
        (``scarlett[n]``); ``uniform``: the floor's own, before the
        suggestion; ``peacock``, ``peacock_belief`` and
        ``peacock_plausibility``: her single number and her two bounds;
        ``mustard``, with ``mustard_path`` (the questions his tree asked
        about the card the suggestion named, each as a dict with
        ``feature``, ``threshold``, ``value``, ``yes`` and ``n``) and
        ``mustard_leaf`` (the leaf's value and its training rows);
        ``white`` and ``white_repeat``, the chain's reading of the one
        opponent who has spoken; ``green_losses`` and ``green_arms``,
        every arm's log-loss against `ROPE_TRUTH` and the Beta
        posterior (alpha, beta, mean) each has after that one lesson;
        ``policy`` and ``policy_value``: the network's answer (today's
        Plum, the committed weights) and its value head's estimate;
        ``mask``, the floor's own view of the position.
    """
    from clude_agents.bandit import BanditAgent, RevealedOutcome, log_loss
    from clude_agents.base import mask_and_normalize
    from clude_agents.decision_tree import FEATURE_NAMES, DecisionTreeAgent, _features
    from clude_agents.deep_nash import DeepNashAgent
    from clude_agents.dempster_shafer import DempsterShaferAgent
    from clude_agents.exact_enum import ExactEnumAgent
    from clude_agents.markov import MarkovAgent
    from clude_agents.naive_bayes import NaiveBayesAgent
    from clude_core.domain import SUSPECTS

    obs = rope_observation(1)
    plum = ExactEnumAgent()
    plum.reset(0)
    exact = plum.select_action(obs)
    assert exact.extra["method"] == "exact"
    scarlett = NaiveBayesAgent()
    peacock = DempsterShaferAgent()
    peacock.reset(0)
    bounds = peacock.select_action(obs)
    mustard = DecisionTreeAgent()
    mustard.reset(0)
    tree = mustard.select_action(obs)
    white = MarkovAgent()
    white.reset(0)
    chain = white.select_action(obs)
    policy = DeepNashAgent()
    policy.reset(0)
    network = policy.select_action(obs)

    # The questions Mustard's tree asks about the card the suggestion named.
    features = _features(obs, obs.mask, "Peacock", list(SUSPECTS))
    node, path = mustard.tree, []
    while not node.is_leaf:
        value = features[node.feature_index]
        yes = value <= node.threshold
        path.append({"feature": FEATURE_NAMES[node.feature_index], "threshold": node.threshold,
                     "value": value, "yes": yes, "n": node.n_samples})
        node = node.left if yes else node.right

    # Green: every arm answers, the envelope is revealed, every arm is ranked.
    green = BanditAgent()
    green.reset(0)
    green.select_action(obs)
    losses = {name: log_loss(belief, ROPE_TRUTH) for name, belief in green._last_predictions.items()}
    green.observe(RevealedOutcome(envelope=ROPE_TRUTH))

    return {
        "deals": exact.extra["completions"],
        "nodes": exact.extra["nodes"],
        "plum": {c: exact.probabilities[c] for c in ROPE_CARDS},
        "scarlett": {n: {c: scarlett.select_action(rope_observation(n)).probabilities[c] for c in ROPE_CARDS} for n in (1, 2, 3)},
        "uniform": {c: mask_and_normalize({}, rope_observation(0).mask)[c] for c in ROPE_CARDS},
        "peacock": {c: bounds.probabilities[c] for c in ROPE_CARDS},
        "peacock_belief": {c: bounds.extra["belief"][c] for c in ROPE_CARDS},
        "peacock_plausibility": {c: bounds.extra["plausibility"][c] for c in ROPE_CARDS},
        "mustard": {c: tree.probabilities[c] for c in ROPE_CARDS},
        "mustard_path": path,
        "mustard_leaf": (node.prediction, node.n_samples),
        "white": {c: chain.probabilities[c] for c in ROPE_CARDS},
        "white_repeat": chain.extra["repeat_probability"][ROPE_SEATS["third"]],
        "policy": {c: network.probabilities[c] for c in ROPE_CARDS},
        "policy_value": network.extra["value"],
        "green_losses": losses,
        "green_arms": {name: (c.alpha, c.beta, c.mean) for name, c in green.candidates.items()},
        "mask": obs.mask,
    }


@lru_cache(maxsize=1)
def plum_search() -> dict:
    """Plum's search on the Rope question, traced step by step through
    the real `_Search`, for the article's figure.

    Returns
    -------
    dict
        ``order``: the cards in the order the search places them;
        ``tree``: the search as nested dicts, each node a ``card``, a
        ``holder``, a ``status`` (``open``, ``deal``, or why it was a
        dead end: ``hand`` for a full hand, ``category`` for a category
        that already has its envelope card, ``contradiction`` for a
        placing that leaves the shown card nowhere to be) and its
        ``children``; ``nodes`` and ``deals``, the counts, which agree
        with `rope_question`.
    """
    from clude_agents.exact_enum import ENVELOPE, _Search

    obs = rope_observation(1)

    class Traced(_Search):
        def __init__(self):
            super().__init__(obs, obs.mask)
            self.root = {"card": None, "holder": None, "status": "root", "children": []}
            self.stack = [self.root]

        def backtrack(self, index, node_budget):
            if index == len(self.unresolved):
                self.completions += 1
                self.stack[-1]["status"] = "deal"
                self.stack[-1]["deal"] = dict(self.assignment)
                for card, holder in self.assignment.items():
                    if holder == ENVELOPE:
                        self.envelope_counts[card] += 1
                return True
            card = self.unresolved[index]
            for holder in self.domains[card]:
                self.nodes += 1
                node = {"card": card, "holder": holder, "status": "open", "children": []}
                self.stack[-1]["children"].append(node)
                if not self.can_place(card, holder):
                    node["status"] = "category" if holder == ENVELOPE else "hand"
                    continue
                self.place(card, holder)
                if all(self.constraint_satisfiable(cards, h) for cards, h in self.or_constraints):
                    self.stack.append(node)
                    self.backtrack(index + 1, node_budget)
                    self.stack.pop()
                else:
                    node["status"] = "contradiction"
                self.unplace(card, holder)
            return True

    search = Traced()
    search.backtrack(0, 10 ** 6)
    return {"order": list(search.unresolved), "tree": search.root, "nodes": search.nodes, "deals": search.completions}


CHAIN_SEQUENCE = (0, 0, 1, 1, 1, 0, 1, 1)
"""The Markov chain article's example: one opponent's suggestions as
White reads them, 0 for all-new cards and 1 for a repeat."""


@lru_cache(maxsize=1)
def chain_example() -> dict:
    """Mrs. White's chain fitted to `CHAIN_SEQUENCE` through the real
    module: the transition counts, the prior's cells, the two transition
    probabilities as exact fractions and the stationary P(repeat), which
    is checked against `_stationary_repeat_probability`."""
    from clude_agents.markov import TRANSITION_KEYS, _stationary_repeat_probability, prior_cells, transition_counts

    symbols = list(CHAIN_SEQUENCE)
    counts = transition_counts(symbols)
    cells = prior_cells()
    totals = {key: Fraction(cells[(int(key[0]), int(key[1]))]).limit_denominator(1000) + counts[key] for key in TRANSITION_KEYS}
    p01 = totals["01"] / (totals["00"] + totals["01"])
    p10 = totals["10"] / (totals["10"] + totals["11"])
    stationary = p01 / (p01 + p10)
    assert abs(float(stationary) - _stationary_repeat_probability(symbols, cells)) < 1e-12
    return {"sequence": symbols, "counts": counts, "totals": totals, "p01": p01, "p10": p10, "stationary": stationary}


@lru_cache(maxsize=1)
def mustard_tree() -> dict:
    """Colonel Mustard's default tree as it is trained when the wiki is
    built: the training set's size and base rate, and the tree's
    `TreeSummary`."""
    from clude_agents.decision_tree import (
        DEFAULT_CHECKPOINTS, DEFAULT_N_TRAINING_GAMES, DEFAULT_TRAINING_BOT, DEFAULT_TRAINING_SEED,
        DecisionTreeAgent, summarize_tree, training_rows,
    )

    rows = training_rows(DEFAULT_N_TRAINING_GAMES, DEFAULT_TRAINING_SEED, DEFAULT_CHECKPOINTS, DEFAULT_TRAINING_BOT)
    positives = sum(label for _, label in rows)
    return {"rows": len(rows), "positives": positives, "base_rate": positives / len(rows),
            "summary": summarize_tree(DecisionTreeAgent().tree)}


def _deals(seats: int, hand: tuple = (2, 2, 2)) -> int:
    """How many deals a player cannot tell apart on the first turn: the
    envelopes their own hand leaves open, times the ways the cards they
    cannot see fall into the other hands. `hand` is how many suspects,
    weapons and rooms they hold."""
    sizes = {3: [6, 6, 6], 4: [5, 5, 4, 4], 5: [4, 4, 4, 3, 3], 6: [3, 3, 3, 3, 3, 3]}[seats]
    mine = sum(hand)
    others = sorted(sizes, reverse=True)
    others.remove(mine)
    envelopes = (6 - hand[0]) * (6 - hand[1]) * (9 - hand[2])
    ways, left = 1, 18 - mine
    for size in others:
        ways *= comb(left, size)
        left -= size
    return envelopes * ways


def _preset(name: str, dial: str) -> str:
    from clude_agents.personality import PRESETS

    return _trim(getattr(PRESETS[name], dial))


def _certainty_at(p: float) -> str:
    """The certainty tag's reading for a seat whose P(correct) is `p`:
    one card at `p`, the other two certain."""
    from clude_agents.character import certainty

    return _trim(certainty({"Scarlett": p, "Candlestick": 1.0, "Kitchen": 1.0}), 2)


def _fraction(value: float, places: int = 100) -> str:
    return str(Fraction(value).limit_denominator(places))


def _code() -> dict:
    from math import sqrt

    from math import prod

    from clude_agents import bandit, decision_tree, deep_nash, exact_enum, markov, naive_bayes
    from clude_agents.character import N_TRIPLES
    from clude_agents.personality import PRESETS
    from clude_core.domain import ALL_CARDS, ROOMS, SUSPECTS, WEAPONS
    from clude_web.tables import LLMConfig, SHOW_TIMEOUT, SPEED_TIMEOUT, STRIKES, TURN_TIMEOUT

    table: dict = {
        "table.timeout": lambda: _trim(TURN_TIMEOUT),
        "table.speed_timeout": lambda: _trim(SPEED_TIMEOUT),
        "table.show_timeout": lambda: _trim(SHOW_TIMEOUT),
        "table.strikes": lambda: str(STRIKES),
        "llm.table_budget": lambda: _trim(LLMConfig.__dataclass_fields__["budget"].default),
        "llm.daily_cap": lambda: _trim(LLMConfig.__dataclass_fields__["daily_cap"].default),
        "scarlett.boost": lambda: _trim(naive_bayes.UNREFUTED_BOOST),
        "scarlett.decay": lambda: _trim(naive_bayes.REFUTED_UNKNOWN_DECAY),
        "scarlett.decay.divisor": lambda: _trim(1 / naive_bayes.REFUTED_UNKNOWN_DECAY),
        "scarlett.decay.twice": lambda: _trim(naive_bayes.REFUTED_UNKNOWN_DECAY ** 2),
        "scarlett.decay.thrice": lambda: _trim(naive_bayes.REFUTED_UNKNOWN_DECAY ** 3),
        "plum.node_budget": lambda: f"{exact_enum.DEFAULT_NODE_BUDGET:,}",
        "net.state": lambda: str(deep_nash.STATE_SIZE),
        "net.card_features": lambda: str(deep_nash.CARD_FEATURES),
        "net.hidden": lambda: str(deep_nash.HIDDEN),
        "net.choice": lambda: str(deep_nash.CHOICE_SIZE),
        "net.move_hidden": lambda: str(deep_nash.MOVE_HIDDEN),
        "net.move_in": lambda: str(deep_nash.HIDDEN + deep_nash.CHOICE_SIZE),
        "net.params": lambda: f"{sum(prod(shape) for shape in deep_nash.WEIGHT_SHAPES.values()):,}",
        "plum.sample_budget": lambda: f"{exact_enum.DEFAULT_SAMPLE_BUDGET:,}",
        "cards.total": lambda: str(len(ALL_CARDS)),
        "cards.suspects": lambda: str(len(SUSPECTS)),
        "cards.weapons": lambda: str(len(WEAPONS)),
        "cards.rooms": lambda: str(len(ROOMS)),
        "cards.dealt": lambda: str(len(ALL_CARDS) - 3),
        "envelopes": lambda: str(len(SUSPECTS) * len(WEAPONS) * len(ROOMS)),
        "deals.3": lambda: f"{_deals(3):,}",
        "deals.6": lambda: f"{_deals(6, (1, 1, 1)):,}",
        "deals.6.hands": lambda: f"{factorial(15) // factorial(3) ** 5:,}",
        "example.deals": lambda: str(rope_question()["deals"]),
    }
    for card in ("White", "Peacock", "Rope", "Wrench"):
        table[f"example.plum.{card}"] = lambda c=card: str(Fraction(rope_question()["plum"][c]).limit_denominator(100))
        table[f"example.plum.{card}.pct"] = lambda c=card: f"{rope_question()['plum'][c] * 100:.0f}"
        table[f"example.plum.{card}.dec"] = lambda c=card: _trim(rope_question()["plum"][c], 2)
        table[f"example.uniform.{card}"] = lambda c=card: str(Fraction(rope_question()["uniform"][c]).limit_denominator(100))
        table[f"example.uniform.{card}.dec"] = lambda c=card: _trim(rope_question()["uniform"][c], 2)
        for n in (1, 2, 3):
            table[f"example.scarlett.{n}.{card}"] = lambda c=card, n=n: _trim(rope_question()["scarlett"][n][c], 2)
            table[f"example.scarlett.{n}.{card}.pct"] = lambda c=card, n=n: f"{rope_question()['scarlett'][n][c] * 100:.0f}"
    table["example.plum.pair"] = lambda: _trim(rope_question()["plum"]["White"] * rope_question()["plum"]["Wrench"], 2)
    table["example.scarlett.3.pair"] = lambda: _trim(rope_question()["scarlett"][3]["White"] * rope_question()["scarlett"][3]["Wrench"], 2)
    for name in ("Scarlett", "Mustard", "White", "Green", "Peacock", "Plum"):
        for dial in ("accuse_threshold", "bluff_rate", "curiosity", "secrecy", "temperature", "leash", "chattiness"):
            table[f"preset.{name}.{dial}"] = lambda n=name, d=dial: _preset(n, d)

    # The other four methods on the same question (W2).
    table["example.plum.nodes"] = lambda: str(rope_question()["nodes"])
    for card in ROPE_CARDS:
        table[f"example.peacock.{card}"] = lambda c=card: _trim(rope_question()["peacock"][c], 2)
        table[f"example.peacock.{card}.bel"] = lambda c=card: _trim(rope_question()["peacock_belief"][c], 2)
        table[f"example.peacock.{card}.pl"] = lambda c=card: _trim(rope_question()["peacock_plausibility"][c], 2)
        table[f"example.mustard.{card}"] = lambda c=card: _trim(rope_question()["mustard"][c], 2)
        table[f"example.white.{card}"] = lambda c=card: _trim(rope_question()["white"][c], 2)
        table[f"example.policy.{card}"] = lambda c=card: _trim(rope_question()["policy"][c], 2)
    table["example.peacock.pair"] = lambda: _trim(rope_question()["peacock_belief"]["White"] * rope_question()["peacock_belief"]["Wrench"], 2)
    table["example.peacock.betp.pair"] = lambda: _trim(rope_question()["peacock"]["White"] * rope_question()["peacock"]["Wrench"], 2)
    table["example.ds.share"] = lambda: _fraction(1 / len(("Peacock", "Rope")))
    table["example.mustard.leaf"] = lambda: _trim(rope_question()["mustard_leaf"][0], 3)
    table["example.mustard.leaf.n"] = lambda: str(rope_question()["mustard_leaf"][1])
    table["example.mustard.questions"] = lambda: str(len(rope_question()["mustard_path"]))

    table["example.white.repeat"] = lambda: _trim(rope_question()["white_repeat"], 2)
    for arm in ("Scarlett", "Plum", "Peacock", "Mustard", "White"):
        table[f"example.green.loss.{arm}"] = lambda a=arm: _trim(rope_question()["green_losses"][a], 2)
        table[f"example.green.mean.{arm}"] = lambda a=arm: _trim(rope_question()["green_arms"][a][2], 3)
        table[f"example.green.alpha.{arm}"] = lambda a=arm: _trim(rope_question()["green_arms"][a][0], 2)
        table[f"example.green.beta.{arm}"] = lambda a=arm: _trim(rope_question()["green_arms"][a][1], 2)
    table["example.green.best"] = lambda: min(rope_question()["green_losses"], key=rope_question()["green_losses"].get)
    table["example.green.worst"] = lambda: max(rope_question()["green_losses"], key=rope_question()["green_losses"].get)

    # Dempster's rule on two pieces of evidence that pull apart, computed by the module.
    white, peacock, both = frozenset({"White"}), frozenset({"Peacock"}), frozenset({"White", "Peacock"})
    first, second = {white: 0.5, both: 0.5}, {peacock: 0.5, both: 0.5}

    def combined() -> dict:
        from clude_agents.dempster_shafer import _combine

        return _combine(first, second)

    table["example.ds.two.white"] = lambda: _fraction(combined()[white])
    table["example.ds.two.peacock"] = lambda: _fraction(combined()[peacock])
    table["example.ds.two.both"] = lambda: _fraction(combined()[both])
    table["example.ds.two.conflict"] = lambda: _fraction(sum(ma * mb for a, ma in first.items() for b, mb in second.items() if not (a & b)))
    table["example.ds.two.white.pl"] = lambda: _fraction(combined()[white] + combined()[both])
    table["example.ds.two.white.betp"] = lambda: _fraction(combined()[white] + combined()[both] / 2)

    # White's chain on the article's sequence.
    table["example.chain.sequence"] = lambda: ", ".join("repeat" if s else "new" for s in chain_example()["sequence"])
    table["example.chain.length"] = lambda: str(len(chain_example()["sequence"]))
    table["example.chain.steps"] = lambda: str(len(chain_example()["sequence"]) - 1)
    for key in ("00", "01", "10", "11"):
        table[f"example.chain.counts.{key}"] = lambda k=key: str(chain_example()["counts"][k])
        table[f"example.chain.totals.{key}"] = lambda k=key: str(chain_example()["totals"][k])
    table["example.chain.p01"] = lambda: str(chain_example()["p01"])
    table["example.chain.p01.dec"] = lambda: _trim(float(chain_example()["p01"]), 2)
    table["example.chain.p10"] = lambda: str(chain_example()["p10"])
    table["example.chain.p10.dec"] = lambda: _trim(float(chain_example()["p10"]), 2)
    table["example.chain.stay.new"] = lambda: str(1 - chain_example()["p01"])
    table["example.chain.stay.repeat"] = lambda: str(1 - chain_example()["p10"])
    table["example.chain.stationary"] = lambda: str(chain_example()["stationary"])
    table["example.chain.stationary.dec"] = lambda: _trim(float(chain_example()["stationary"]), 2)
    table["white.prior_mass"] = lambda: _trim(markov.PRIOR_MASS)
    table["white.prior_cell"] = lambda: _trim(markov.PRIOR_MASS / 4)
    table["white.closeness_half"] = lambda: _trim(markov._CLOSENESS_HALF)
    table["white.base_score"] = lambda: _trim(markov._BASE_SCORE)

    # Mustard's tree, as trained.
    table["mustard.tree.games"] = lambda: str(decision_tree.DEFAULT_N_TRAINING_GAMES)
    table["mustard.tree.seed"] = lambda: str(decision_tree.DEFAULT_TRAINING_SEED)
    table["mustard.tree.max_depth"] = lambda: str(decision_tree.DEFAULT_MAX_DEPTH)
    table["mustard.tree.min_leaf"] = lambda: str(decision_tree.DEFAULT_MIN_SAMPLES_LEAF)
    table["mustard.tree.smoothing"] = lambda: _trim(decision_tree.DEFAULT_SMOOTHING_M)
    table["mustard.tree.turn_scale"] = lambda: _trim(decision_tree.MAX_TURN_FOR_NORMALIZATION)
    table["mustard.tree.features"] = lambda: str(len(decision_tree.FEATURE_NAMES))
    table["mustard.tree.checkpoints"] = lambda: " and ".join(f"{int(c * 100)}%" for c in decision_tree.DEFAULT_CHECKPOINTS)
    table["mustard.tree.rows"] = lambda: f"{mustard_tree()['rows']:,}"
    table["mustard.tree.positives"] = lambda: str(mustard_tree()["positives"])
    table["mustard.tree.base_rate.pct"] = lambda: f"{mustard_tree()['base_rate'] * 100:.0f}"
    table["mustard.tree.base_rate"] = lambda: _trim(mustard_tree()["base_rate"], 2)
    table["mustard.tree.nodes"] = lambda: str(mustard_tree()["summary"].n_nodes)
    table["mustard.tree.leaves"] = lambda: str(mustard_tree()["summary"].n_leaves)
    table["mustard.tree.depth"] = lambda: str(mustard_tree()["summary"].depth)
    table["mustard.tree.leaf.min"] = lambda: _trim(min(mustard_tree()["summary"].leaf_predictions), 3)
    table["mustard.tree.leaf.max"] = lambda: _trim(max(mustard_tree()["summary"].leaf_predictions), 2)
    table["mustard.tree.features.used"] = lambda: str(len(mustard_tree()["summary"].feature_use))
    for feature in decision_tree.FEATURE_NAMES:
        table[f"mustard.tree.splits.{feature}"] = lambda f=feature: str(mustard_tree()["summary"].feature_use.get(f, 0))

    # Green's bandit.
    table["green.step_size"] = lambda: _trim(bandit.BanditAgent().step_size)
    table["green.decay"] = lambda: _trim(bandit.BanditAgent().decay_rate)
    table["green.arms"] = lambda: str(len(bandit._build_arms()))

    # The certainty tag (Phase 9h): bits gained, on the 324 triples.
    table["certainty.triples"] = lambda: str(N_TRIPLES)
    table["certainty.half.one_in"] = lambda: str(round(sqrt(N_TRIPLES)))
    table["certainty.scarlett"] = lambda: _certainty_at(PRESETS["Scarlett"].accuse_threshold)
    table["certainty.peacock"] = lambda: _certainty_at(PRESETS["Peacock"].accuse_threshold)
    table["certainty.plum"] = lambda: _certainty_at(PRESETS["Plum"].accuse_threshold)
    table["certainty.even"] = lambda: _certainty_at(0.5)
    return table


CODE: dict = _code()
"""Every ``{{code:key}}``: a name and how to compute it. Evaluated when
an article is rendered, not at import."""


def _publishing_values() -> dict:
    """Live constants and computed illustrations for W3-W5 articles."""
    from clude_agents.features import DISTANCE_DISCOUNT
    from clude_agents.character import N_TRIPLES
    from clude_agents.personality import NEUTRAL
    from clude_core import board, engine
    from clude_core.bots import ACCUSE_PROBABILITY, SUGGEST_PROBABILITY
    from clude_llm.player import LLMSettings
    from clude_storage.logbooks import memory_counts
    from clude_training.benchmark import EPS
    from clude_training.self_play import DEFAULT_CHECKPOINTS
    from math import log, log2

    table = {
        "board.columns": lambda: str(board.N_COLS),
        "board.rows": lambda: str(board.N_ROWS),
        "board.doors": lambda: str(len(board.DOORS)),
        "random.suggest": lambda: _trim(SUGGEST_PROBABILITY),
        "random.accuse": lambda: _trim(ACCUSE_PROBABILITY),
        "movement.discount": lambda: _trim(DISTANCE_DISCOUNT),
        "benchmark.epsilon": lambda: f"{EPS:g}",
        "benchmark.checkpoints": lambda: ", ".join(f"{c * 100:g}%" for c in DEFAULT_CHECKPOINTS),
        "loss.half": lambda: _trim(-log(0.5), 2),
        "loss.sixth": lambda: _trim(log(6), 2),
        "loss.tenth": lambda: _trim(log(10), 2),
        "entropy.envelopes": lambda: _trim(log2(N_TRIPLES), 2),
    }
    for temperature in (0.1, 0.5):
        table[f"softmax.{temperature}"] = lambda t=temperature: f"{softmax_example(t) * 100:.1f}%"
    dealt = len(engine.ALL_CARDS) - 3
    for n in range(engine.MIN_PLAYERS, engine.MAX_PLAYERS + 1):
        table[f"deal.hands.{n}"] = lambda n=n: ", ".join(
            str(divmod(dealt, n)[0] + (i < dealt % n)) for i in range(n)
        )
    for dial in NEUTRAL.to_dict():
        table[f"neutral.{dial}"] = lambda d=dial: _trim(getattr(NEUTRAL, d))
    for name in ("debrief_max_tokens", "debrief_timeout", "max_lookups_per_call", "max_lookups_per_game"):
        table[f"llm.{name}"] = lambda n=name: _trim(getattr(LLMSettings(), n))
    table.update(_talk_values())
    for depth in (0, 0.25, 0.5, 0.75, 1):
        for index, label in enumerate(("index", "full")):
            table[f"memory.{depth}.{label}"] = lambda d=depth, i=index: str(memory_counts(10, d)[i])
    table["canon.read_limit"] = lambda: f"{_canon_limit('READ_LIMIT'):,}"
    table["canon.search_limit"] = lambda: str(_canon_limit("SEARCH_LIMIT"))
    return table


def _talk_values() -> dict:
    """The talk and logbook constants the Personality and Memory articles
    quote (Phase 13 / W8): the reaction queue's caps and delay, the length a
    model's line is cut to, the talk window a prompt shows, and the caps
    on what a debrief or a digest may write."""
    from inspect import signature

    from clude_llm import prompt as llm_prompt
    from clude_llm.player import MAX_LINE
    from clude_storage import logbooks
    from clude_web import chat

    return {
        "chat.max_queued": lambda: str(chat.MAX_QUEUED),
        "chat.per_turn": lambda: str(chat.PER_TURN),
        "chat.per_game": lambda: str(chat.PER_GAME),
        "chat.delay": lambda: f"{chat.DELAY[0]:g} to {chat.DELAY[1]:g}",
        "llm.max_line": lambda: str(MAX_LINE),
        "llm.recent_remarks": lambda: str(signature(llm_prompt.user_prompt).parameters["recent_remarks"].default),
        "logbook.instructions": lambda: str(logbooks.MAX_STANDING_INSTRUCTIONS),
        "logbook.flags": lambda: str(logbooks.MAX_FLAGS),
        "logbook.summary_words": lambda: str(logbooks.SUMMARY_WORDS),
        "logbook.read_words": lambda: str(logbooks.READ_WORDS),
        "logbook.overview_words": lambda: str(logbooks.OVERVIEW_WORDS),
        "logbook.lesson_words": lambda: str(logbooks.LESSON_WORDS),
        "logbook.themes": lambda: str(logbooks.MAX_THEMES),
    }


def _canon_limit(name: str) -> int:
    """A limit of the canon's reads (`index.READ_LIMIT`, `index.SEARCH_LIMIT`),
    imported late: `index` imports `render`, which imports this module."""
    from . import index as wiki_index  # noqa: PLC0415

    return int(getattr(wiki_index, name))


def softmax_example(temperature: float) -> float:
    """Read the real sampler's weights for the illustrated 0.8/0.6 menu."""
    from clude_agents.features import sample_softmax

    class WeightReader:
        def choices(self, population, weights, k):
            self.weights = weights
            return [population[0]]

    reader = WeightReader()
    sample_softmax([0.8, 0.6], temperature, reader)
    return reader.weights[0] / sum(reader.weights)


CODE.update(_publishing_values())

PHASE13_PLAN = "docs/phase13-plan.md"
CANON_PLAN = "docs/canon-plan.md"
_P13_NAMING = "2026-10-15: the rehearsal completed, and step 6's naming and pacing"
_P13_TAPER = "2026-10-15: the taper left alone, the fixtures refreshed, step 0 closed out"
_P13_LIVE = "2026-10-15: step 4 accepted live, and a debrief lost to its token cap"
_P13_AUDIT = "2026-10-14: live memory audit and pathway revision"
_P13_REHEARSAL2 = "2026-11-01: the rehearsal re-run with the characters hearing one another"
_REHEARSAL = "seven scenes, 42 lines, 39 free of game terms (93%), $0.2817"

FACTS.update({
    # Phase 13: what the talk gate cost, and how the reaction queue paced two games (W8).
    "talk.gate.written": Fact("81", PHASE13_PLAN, _P13_NAMING, "81 on-turn lines written, 39 spoken"),
    "talk.gate.spoken": Fact("39", PHASE13_PLAN, _P13_NAMING, "81 on-turn lines written, 39 spoken"),
    "talk.gate.dropped": Fact("42", PHASE13_PLAN, _P13_NAMING, "**42 paid for and thrown away**"),
    "talk.reactions.three": Fact("22", PHASE13_PLAN, _P13_TAPER, "22 reaction lines over 37 turns"),
    "talk.reactions.three.turns": Fact("37", PHASE13_PLAN, _P13_TAPER, "22 reaction lines over 37 turns"),
    "talk.reactions.six": Fact("41", PHASE13_PLAN, _P13_TAPER, "41 over 57"),
    "talk.reactions.six.turns": Fact("57", PHASE13_PLAN, _P13_TAPER, "41 over 57"),
    "talk.reactions.runs": Fact("twelve", PHASE13_PLAN, _P13_TAPER, "twelve runs of three"),
    "rehearsal.lines": Fact("42", PHASE13_PLAN, _P13_REHEARSAL2, _REHEARSAL),
    "rehearsal.free": Fact("39", PHASE13_PLAN, _P13_REHEARSAL2, _REHEARSAL),
    "rehearsal.pct": Fact("93", PHASE13_PLAN, _P13_REHEARSAL2, _REHEARSAL),
    "rehearsal.cost": Fact("0.2817", PHASE13_PLAN, _P13_REHEARSAL2, _REHEARSAL),
    "rehearsal.scenes": Fact("seven", PHASE13_PLAN, _P13_REHEARSAL2, _REHEARSAL),
    "rehearsal.lookups": Fact("0", PHASE13_PLAN, _P13_REHEARSAL2, "no lookup in 42 calls"),
    "continuity.cost": Fact("0.9586", PHASE13_PLAN, _P13_REHEARSAL2, "continuity $0.9586"),
    "debrief.plum.out": Fact("3,407", PHASE13_PLAN, _P13_LIVE, "Those 3,407 output tokens confirm the diagnosis"),
    "debrief.plum.cost": Fact("0.1281", PHASE13_PLAN, _P13_LIVE, "$0.1281 for 8,580 in and 3,407 out"),
    "audit.entries": Fact("78", PHASE13_PLAN, _P13_AUDIT, "(78 in all)"),
    "audit.clauses": Fact("six", PHASE13_PLAN, _P13_AUDIT, "six clauses in four characters qualify"),
    "canon.calls": Fact("41", CANON_PLAN, "7.3 Acceptance (2026-10-09, approved by David the same day)",
                        "in 41 ordinary calls at low effort no character found a question of fact to look up"),
})


_STEP = re.compile(r"example\.mustard\.step\.(\d+)\.(threshold|value|answer|feature)$")


def _mustard_step(index: int, field: str) -> str:
    """One question on Mustard's path through his tree on the Rope
    question, 1-based (``example.mustard.step.3.threshold``). A step the
    path does not have is a KeyError, so prose that narrates a path the
    regrown tree no longer takes fails at load, not in front of a reader."""
    path = rope_question()["mustard_path"]
    if not 1 <= index <= len(path):
        raise KeyError(f"example.mustard.step.{index}.{field}")
    here = path[index - 1]
    if field == "threshold":
        return _trim(here["threshold"], 2)
    if field == "value":
        return _trim(here["value"], 2)
    if field == "answer":
        return "yes" if here["yes"] else "no"
    return here["feature"]


def code(key: str) -> str:
    """The printed value of a constant or computed example.

    Raises
    ------
    KeyError
        If nothing has that key.
    """
    if key in CODE:
        return CODE[key]()
    match = _STEP.fullmatch(key)
    if match:
        return _mustard_step(int(match.group(1)), match.group(2))
    raise KeyError(key)
