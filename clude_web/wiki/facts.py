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
    "Peacock": "[[Mrs. Peacock|Peacock]]", "Plum": "[[Professor Plum|Plum]]",
    "uniform": "[[Uniform baseline|uniform (baseline)]]",
}

# The glossary headings the facts below are found under, named once.
_BENCH_RING = "Belief benchmark, FloorBot regime (Phase 5)"
_BENCH_GRID = "Belief benchmark on the grid (Stage 1a)"
_PHASE4 = "Phase 4 benchmark results (RandomBot regime, historical)"
_TUNED_RING = "Tuned presets"
_TUNED_GRID = "Tuned presets on the grid (Stage 1e, 2026-09-15)"
_ARENA_GRID = "Arena on the grid, tuned presets (Stage 1f, re-run)"
_ARENA_GRID_FIRST = "Arena on the grid, presets as tuned on the ring (Stage 1f)"
_TWIN_RING = "Twin comparison (2026-09-13)"
_TWIN_GRID = "Twin comparison on the grid (Stage 2a, 2026-09-16)"
_LADDER_MUSTARD = "Mustard"
_MEMORY = "Phase 7: memory (2026-09-14)"
_LANDING = "The landing rule (Phase 8.0.4, 2026-09-18)"
_LOGBOOK = "Plum's logbook at leash 0.5 (2026-09-14)"
_PLUM_CLAUDE = "Plum with Claude on the grid (Stage 2b, 2026-09-16)"
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
            "Plum": (_SUSPECT_LABELS["Plum"], "| Plum | 1.64 | 1.75 | 1.15 | 0.22 | 0.91 | 530 |"),
            "uniform": (_SUSPECT_LABELS["uniform"], "| uniform (baseline) | 1.57 | 1.35 | 1.01 | 0.29 | 0.83 | - |"),
            "Scarlett": (_SUSPECT_LABELS["Scarlett"], "| Scarlett | 1.62 | 1.48 | 1.18 | 0.30 | 0.87 | 0.1 |"),
            "Peacock": (_SUSPECT_LABELS["Peacock"], "| Peacock | 1.63 | 1.46 | 1.13 | 0.31 | 0.83 | 0.2 |"),
        },
    ),
    # The same benchmark on the ring board, Phase 5.
    "bench.ring": Table(
        GLOSSARY, "Belief benchmark, FloorBot regime (Phase 5)",
        ("Method", "25%", "50%", "75%", "100%", "Top-1 at 100%", "ms per call at 50%"),
        ("25", "50", "75", "100", "top1", "ms"),
        {
            "Plum": (_SUSPECT_LABELS["Plum"], "| Plum | 1.55 | 1.49 | 0.95 | 0.23 | 0.93 | 375 |"),
            "Green": (_SUSPECT_LABELS["Green"], "| Green | 1.54 | 1.38 | 0.99 | 0.23 | 0.94 | 380 |"),
            "Mustard": (_SUSPECT_LABELS["Mustard"], "| Mustard | 1.52 | 1.50 | 1.19 | 0.22 | 0.93 | 0.1 |"),
            "White": (_SUSPECT_LABELS["White"], "| White | 1.53 | 1.28 | 0.94 | 0.32 | 0.88 | 0.1 |"),
            "uniform": (_SUSPECT_LABELS["uniform"], "| uniform (baseline) | 1.60 | 1.36 | 1.03 | 0.40 | 0.77 | - |"),
            "Scarlett": (_SUSPECT_LABELS["Scarlett"], "| Scarlett | 1.69 | 1.49 | 1.20 | 0.41 | 0.84 | 0.0 |"),
            "Peacock": (_SUSPECT_LABELS["Peacock"], "| Peacock | 1.68 | 1.45 | 1.10 | 0.41 | 0.78 | 0.2 |"),
        },
    ),
    # Plum's enumeration at four budgets, 2026-09-15.
    "budget.grid": Table(
        GLOSSARY, "Tuned presets on the grid (Stage 1e, 2026-09-15)",
        ("Search nodes / samples", "25%", "50%", "75%", "100%", "Calls that fell back", "ms per call at 50%"),
        ("25", "50", "75", "100", "fallback", "ms"),
        {
            "200k-2k": ("200,000 / 2,000 (until 15 September 2026)", "| 200k / 2k (until today) | 1.64 | 1.75 | 1.15 | 0.22 | 490 | 289 |"),
            "200k-10k": ("**200,000 / 10,000 (adopted)**", "| 200k / 10k (adopted) | 1.52 | 1.44 | 1.00 | 0.22 | 490 | 669 |"),
            "1M-2k": ("1,000,000 / 2,000", "| 1M / 2k | 1.56 | 1.66 | 1.03 | 0.22 | 384 | 740 |"),
            "1M-10k": ("1,000,000 / 10,000", "| 1M / 10k | 1.51 | 1.41 | 0.93 | 0.22 | 384 | 1113 |"),
            "uniform": (_SUSPECT_LABELS["uniform"], "| uniform (baseline) | 1.57 | 1.35 | 1.01 | 0.29 | -- | -- |"),
        },
    ),
    # Who wins, at the presets as retuned on the Classic board.
    "arena.grid": Table(
        GLOSSARY, "Arena on the grid, tuned presets (Stage 1f, re-run)",
        ("Character", "Games", "Won %", "Accused wrongly %", "First accusation (turn)", "Never accused %", "Own cards shown", "Own cards named", "Re-shown %"),
        ("games", "win", "wrong", "first", "never", "leaked", "named", "reshow"),
        {
            "Scarlett": (_SUSPECT_LABELS["Scarlett"], "| Scarlett (threshold 0.3) | 20 | 25 | 20 | 60.4 | 55 | 2.50 | 1.95 | 31.2 |"),
            "Mustard": (_SUSPECT_LABELS["Mustard"], "| Mustard (0.8) | 16 | 19 | 6 | 43.2 | 75 | 2.56 | 1.56 | 46.2 |"),
            "White": (_SUSPECT_LABELS["White"], "| White (0.8) | 20 | 10 | 0 | 37.5 | 90 | 2.60 | 4.15 | 56.0 |"),
            "Green": (_SUSPECT_LABELS["Green"], "| Green (0.75) | 16 | 19 | 6 | 35.8 | 75 | 2.12 | 2.00 | 72.7 |"),
            "Peacock": (_SUSPECT_LABELS["Peacock"], "| Peacock (0.7 on Belief) | 20 | 30 | 0 | 63.8 | 70 | 2.10 | 1.45 | 50.0 |"),
            "Plum": (_SUSPECT_LABELS["Plum"], "| Plum (0.9, curiosity 0.5) | 16 | 31 | 0 | 58.0 | 69 | 2.19 | 2.25 | 53.8 |"),
        },
    ),
    # Every character with and without Claude, four seats, 2026-09-16.
    "twin.grid": Table(
        GLOSSARY, "Twin comparison on the grid (Stage 2a, 2026-09-16)",
        ("Character", "Won, alone", "Won, with Claude", "Games lost / gained", "Wrong, alone", "Wrong, with Claude",
         "First accusation, alone", "First accusation, with Claude", "Never accused, alone", "Never accused, with Claude"),
        ("win_base", "win_llm", "swing", "wrong_base", "wrong_llm", "first_base", "first_llm", "never_base", "never_llm"),
        {
            "Scarlett": (_SUSPECT_LABELS["Scarlett"], "| Scarlett | 6.2 | 6.2 | 1 / 1 | 25.0 | 31.2 | 41.0 | 38.2 | 68.8 | 62.5 |"),
            "Mustard": (_SUSPECT_LABELS["Mustard"], "| Mustard | 12.5 | **31.2** | 1 / 4 | 31.2 | **6.2** | 39.1 | 34.2 | 56.2 | 62.5 |"),
            "White": (_SUSPECT_LABELS["White"], "| White | 50.0 | 50.0 | 5 / 5 | 0.0 | 0.0 | 53.4 | 35.8 | 50.0 | 50.0 |"),
            "Green": (_SUSPECT_LABELS["Green"], "| Green | 31.2 | 25.0 | 4 / 3 | 0.0 | 6.2 | 39.8 | 34.4 | 68.8 | 68.8 |"),
            "Peacock": (_SUSPECT_LABELS["Peacock"], "| Peacock | 12.5 | 31.2 | 2 / 5 | 0.0 | 0.0 | 56.5 | 33.2 | 87.5 | 68.8 |"),
            "Plum": (_SUSPECT_LABELS["Plum"], "| Plum | **37.5** | **6.2** | 6 / 1 | 0.0 | 0.0 | 29.0 | 40.0 | 62.5 | 93.8 |"),
        },
    ),
    # Plum alone with Claude at a three-seat table, 2026-09-16.
    "plum.claude": Table(
        GLOSSARY, "Plum with Claude on the grid (Stage 2b, 2026-09-16)",
        ("Run", "Won", "+/-", "Accused wrongly", "First accusation (turn)", "Never accused", "Mean turns"),
        ("win", "std", "wrong", "first", "never", "turns"),
        {
            "base": ("Plum alone (`grid-plum-base-24`)", "| `grid-plum-base-24` (headless) | 37.5 | 9.9 | 0 | 31.0 | 62.5 | 31.9 |"),
            "llm": ("Plum with Claude (`grid-plum-llm-24`)", "| `grid-plum-llm-24` (with Claude) | 54.2 | 10.2 | 0 | 34.8 | 45.8 | 42.6 |"),
        },
    ),
    # Scarlett's accusation threshold on the Classic board, 2026-09-15.
    "scarlett.threshold": Table(
        GLOSSARY, "Scarlett's threshold on the grid (Stage 1d)",
        ("Accusation threshold", "Won", "Accused wrongly", "Accused in", "First accusation (turn)"),
        ("win", "wrong", "accused", "first"),
        {
            "0.3": ("**0.3 (adopted)**", "| 0.3 | 30 | 30 | 60% | 52.8 |"),
            "0.2": ("0.2", "| 0.2 | 15 | 50 | 65% | 42.2 |"),
            "0.15": ("0.15 (the ring-era preset)", "| 0.15 | 10 | 40 | 50% | 40.3 |"),
        },
    ),
    # Plum with Claude, with and without his own logbook, 2026-09-14 (ring).
    "plum.logbook": Table(
        GLOSSARY, "Plum's logbook at leash 0.5 (2026-09-14)",
        ("", "Won", "Accused wrongly", "First accusation (turn)", "Never accused", "Mean turns"),
        ("win", "wrong", "first", "never", "turns"),
        {
            "off": ("Without a logbook", "| logbook off | 54.2 | 0.0 | 20.5 | 45.8 | 25.6 | 478 | 40 | 5.2% | 6.54 | 31,689 |"),
            "on": ("With his logbook", "| logbook on | 50.0 | 8.3 | 21.7 | 41.7 | 20.6 | 353 | 52 | 8.8% | 5.67 | 28,480 |"),
        },
    ),
    # How the bluff-rate dial moves a game, pooled over the six, Phase 5 (ring).
    "sweep.bluff": Table(
        GLOSSARY, "Dial sweeps",
        ("Bluff rate", "Won", "Accused wrongly", "Never accused", "Own cards named per game", "Mean turns"),
        ("win", "wrong", "never", "named", "turns"),
        {
            "0": ("0 (never)", "| 0.0 | 19.2 | 8.3 | 73 | 0.62 | 26.8 |"),
            "0.25": ("0.25", "| 0.25 | 20.0 | 7.5 | 73 | 1.91 | 26.0 |"),
            "0.5": ("0.5", "| 0.5 | 17.5 | 5.0 | 78 | 2.90 | 25.4 |"),
            "1": ("1 (always)", "| 1.0 | 6.7 | 12.5 | 81 | 4.77 | 31.2 |"),
        },
    ),
    # Green's accusation threshold moved alone, 2026-09-15.
    "green.threshold": Table(
        GLOSSARY, _TUNED_GRID,
        ("Green's accusation threshold", "Won %", "Accused wrongly %", "Never accused %", "First accusation (turn)"),
        ("win", "wrong", "never", "first"),
        {
            "0.75": ("**0.75 (the preset)**", "| 0.75 (preset, `arena-grid-24`) | 0 | 6 | 94 | 28.0 |"),
            "0.6": ("0.6", "| 0.6 | 6 | 0 | 94 | 35.0 |"),
            "0.5": ("0.5", "| 0.5 | 6 | 12 | 81 | 50.0 |"),
        },
    ),
    # Curiosity moved alone for the three high-curiosity presets, 2026-09-15.
    "curiosity.grid": Table(
        GLOSSARY, _TUNED_GRID,
        ("Curiosity", "Plum (preset 0.8)", "Scarlett (preset 0.7)", "Peacock (preset 0.6)"),
        ("plum", "scarlett", "peacock"),
        {
            "preset": ("At the preset", "| preset | 44 / 0 / 56 | 10 / 40 / 50 | 30 / 0 / 70 |"),
            "0.5": ("0.5", "| 0.5 | 50 / 0 / 50 | 5 / 55 / 40 | 30 / 0 / 70 |"),
            "0.3": ("0.3", "| 0.3 | 38 / 0 / 62 | 15 / 65 / 20 | 30 / 0 / 70 |"),
        },
    ),
    # The ring board's first arena, at the first-pass presets, Phase 5.
    "arena.ring.first": Table(
        GLOSSARY, "Arena, first pass (untuned presets)",
        ("Character", "Games", "Won %", "Accused wrongly %", "First accusation (turn)", "Never accused %", "Own cards shown", "Own cards named"),
        ("games", "win", "wrong", "first", "never", "leaked", "named"),
        {
            "Scarlett": (_SUSPECT_LABELS["Scarlett"] + " (threshold 0.5)", "| Scarlett (threshold 0.5) | 20 | 0 | 5 | 10.0 | 95 | 2.30 | 1.40 |"),
            "Mustard": (_SUSPECT_LABELS["Mustard"] + " (0.8)", "| Mustard (0.8) | 16 | 19 | 38 | 21.6 | 44 | 2.81 | 1.38 |"),
            "White": (_SUSPECT_LABELS["White"] + " (0.8)", "| White (0.8) | 20 | 30 | 0 | 31.8 | 70 | 2.65 | 3.50 |"),
            "Green": (_SUSPECT_LABELS["Green"] + " (0.75)", "| Green (0.75) | 16 | 13 | 13 | 20.8 | 75 | 2.62 | 1.62 |"),
            "Peacock": (_SUSPECT_LABELS["Peacock"] + " (0.7 on Belief)", "| Peacock (0.7 on Belief) | 20 | 40 | 0 | 32.1 | 60 | 2.65 | 1.15 |"),
            "Plum": (_SUSPECT_LABELS["Plum"] + " (0.95)", "| Plum (0.95) | 16 | 31 | 6 | 19.8 | 63 | 2.31 | 0.31 |"),
        },
    ),
    # The ring board's arena at the tuned presets, Phase 5.
    "arena.ring": Table(
        GLOSSARY, "Arena, tuned presets",
        ("Character", "Games", "Won %", "Accused wrongly %", "First accusation (turn)", "Never accused %", "Own cards shown", "Own cards named", "Re-shown %"),
        ("games", "win", "wrong", "first", "never", "leaked", "named", "reshow"),
        {
            "Scarlett": (_SUSPECT_LABELS["Scarlett"] + " (threshold 0.15)", "| Scarlett (threshold 0.15) | 20 | 10 | 45 | 23.8 | 45 | 2.05 | 1.25 | 37.5 |"),
            "Mustard": (_SUSPECT_LABELS["Mustard"], "| Mustard (0.8) | 16 | 25 | 25 | 20.1 | 50 | 2.81 | 1.31 | 33.3 |"),
            "White": (_SUSPECT_LABELS["White"], "| White (0.8) | 20 | 30 | 0 | 31.0 | 70 | 2.25 | 3.05 | 23.1 |"),
            "Green": (_SUSPECT_LABELS["Green"], "| Green (0.75) | 16 | 19 | 13 | 36.0 | 69 | 2.38 | 1.44 | 72.7 |"),
            "Peacock": (_SUSPECT_LABELS["Peacock"], "| Peacock (0.7 on Belief) | 20 | 15 | 0 | 21.7 | 85 | 2.40 | 1.65 | 42.9 |"),
            "Plum": (_SUSPECT_LABELS["Plum"] + " (0.9)", "| Plum (0.9) | 16 | 38 | 0 | 26.7 | 63 | 2.44 | 0.81 | 12.5 |"),
        },
    ),
    # The Classic board's first arena, before the presets were retuned, 2026-09-15.
    "arena.grid.first": Table(
        GLOSSARY, _ARENA_GRID_FIRST,
        ("Character", "Games", "Won %", "Accused wrongly %", "First accusation (turn)", "Never accused %", "Own cards shown", "Own cards named", "Re-shown %"),
        ("games", "win", "wrong", "first", "never", "leaked", "named", "reshow"),
        {
            "Scarlett": (_SUSPECT_LABELS["Scarlett"] + " (threshold 0.15)", "| Scarlett (threshold 0.15) | 20 | 10 | 40 | 40.3 | 50 | 2.55 | 1.40 | 66.7 |"),
            "Mustard": (_SUSPECT_LABELS["Mustard"], "| Mustard (0.8) | 16 | 25 | 6 | 58.6 | 69 | 2.19 | 1.44 | 38.5 |"),
            "White": (_SUSPECT_LABELS["White"], "| White (0.8) | 20 | 25 | 0 | 35.0 | 75 | 2.40 | 3.15 | 28.6 |"),
            "Green": (_SUSPECT_LABELS["Green"], "| Green (0.75) | 16 | 0 | 6 | 28.0 | 94 | 2.00 | 0.69 | 30.0 |"),
            "Peacock": (_SUSPECT_LABELS["Peacock"], "| Peacock (0.7 on Belief) | 20 | 30 | 0 | 32.3 | 70 | 1.80 | 0.90 | 50.0 |"),
            "Plum": (_SUSPECT_LABELS["Plum"] + " (curiosity 0.8)", "| Plum (0.9) | 16 | 44 | 0 | 42.6 | 56 | 2.12 | 0.56 | 71.4 |"),
        },
    ),
    # The ring board's twin comparison, Phase 6, 2026-09-13.
    "twin.ring": Table(
        GLOSSARY, _TWIN_RING,
        ("Character", "Won, alone", "Won, with Claude", "Wrong, alone", "Wrong, with Claude", "First accusation, alone", "First accusation, with Claude"),
        ("win_base", "win_llm", "wrong_base", "wrong_llm", "first_base", "first_llm"),
        {
            "Scarlett": (_SUSPECT_LABELS["Scarlett"], "| Scarlett | 12.5 | 12.5 | 37.5 | 31.2 | 23.4 | 19.3 |"),
            "Mustard": (_SUSPECT_LABELS["Mustard"], "| Mustard | 12.5 | **37.5** | 37.5 | **6.2** | 22.2 | 18.1 |"),
            "White": (_SUSPECT_LABELS["White"], "| White | 12.5 | 25.0 | 0.0 | 0.0 | 29.5 | 22.5 |"),
            "Green": (_SUSPECT_LABELS["Green"], "| Green | 25.0 | 31.2 | 6.2 | 6.2 | 30.0 | 17.3 |"),
            "Peacock": (_SUSPECT_LABELS["Peacock"], "| Peacock | 12.5 | 12.5 | 0.0 | 0.0 | 24.0 | 18.5 |"),
            "Plum": (_SUSPECT_LABELS["Plum"], "| Plum | **75.0** | **31.2** | 0.0 | 0.0 | 27.8 | 26.2 |"),
        },
    ),
    # Mustard alone with Claude at four leashes, the ring, 2026-09-13.
    "ladder.mustard": Table(
        GLOSSARY, _LADDER_MUSTARD,
        ("Leash", "Won %", "Accused wrongly %", "First accusation (turn)", "Never accused %", "Own cards named", "Mean turns", "Choices played", "Departures", "Per decision"),
        ("win", "wrong", "first", "never", "named", "turns", "played", "devs", "dev"),
        {
            "headless": ("By his numbers alone", "| headless | 25.0 | 25.0 | 16.9 | 50.0 | 2.08 | 24.0 | -- | -- | -- |"),
            "0": ("Leash 0", "| leash 0 | 25.0 | 16.7 | 16.2 | 58.3 | 2.04 | 21.3 | 148 | 0 | 0.0% |"),
            "0.25": ("**Leash 0.25 (the preset)**", "| leash 0.25 | 33.3 | 41.7 | 16.7 | 25.0 | 0.75 | 21.6 | 254 | 2 | 0.4% |"),
            "0.5": ("Leash 0.5", "| leash 0.5 | 29.2 | 25.0 | 15.7 | 45.8 | 1.21 | 22.0 | 347 | 10 | 1.7% |"),
            "1": ("Leash 1", "| leash 1 | 33.3 | 25.0 | 15.4 | 41.7 | 0.83 | 19.1 | 427 | 10 | 2.0% |"),
        },
    ),
    # Exact repeats of a seat's own earlier suggestion, before and after the landing rule.
    "landing.repeats": Table(
        GLOSSARY, _LANDING,
        ("Character", "Tables of three to six", "Tables of four", "Plum's table of three"),
        ("mixed", "four", "three"),
        {
            "Plum": (_SUSPECT_LABELS["Plum"], "| Plum | 66 of 154 (43%) to 5 of 84 (6%) | 15 of 104 (14%) to 8 of 70 (11%) | 47 of 187 (25%) to 6 of 138 (4%) |"),
            "Mustard": (_SUSPECT_LABELS["Mustard"], "| Mustard | 10 (12%) to 4 (6%) | 7 (10%) to 0 | 8 (7%) to 1 (1%) |"),
            "Peacock": (_SUSPECT_LABELS["Peacock"], "| Peacock | 37 (25%) to 3 (3%) | 15 (15%) to 5 (8%) | -- |"),
            "White": (_SUSPECT_LABELS["White"], "| White | 26 (17%) to 11 (9%) | 13 (11%) to 3 (4%) | -- |"),
            "Scarlett": (_SUSPECT_LABELS["Scarlett"], "| Scarlett | 14 (15%) to 0 | 0 to 1 | -- |"),
            "Green": (_SUSPECT_LABELS["Green"], "| Green | 4 (6%) to 0 | 8 (12%) to 0 | 2 (2%) to 1 (1%) |"),
        },
    ),
}

# Full historical dial sweeps and the remaining leash tables (W6).
TABLES.update({
    "sweep.ring.accuse_threshold": Table(
        GLOSSARY, 'Dial sweeps',
        ('Accusation threshold', 'Won %', 'Wrong %', 'First accusation (turn)', 'Never accused %', 'Mean turns'),
        ('win', 'wrong', 'first', 'never', 'turns'),
        {
            '0.2': ('0.2', '| 0.2 | 18.3 | 33.3 | 18.1 | 48 | 22.8 |'),
            '0.4': ('0.4', '| 0.4 | 23.3 | 21.7 | 22.5 | 55 | 25.2 |'),
            '0.6': ('0.6', '| 0.6 | 24.2 | 11.7 | 24.4 | 64 | 24.5 |'),
            '0.8': ('0.8', '| 0.8 | 23.3 | 4.2 | 19.6 | 73 | 24.3 |'),
            '1.0': ('1.0', '| 1.0 | 20.8 | 0.0 | 22.2 | 79 | 27.5 |'),
        },
    ),
    "sweep.ring.curiosity": Table(
        GLOSSARY, 'Dial sweeps',
        ('Curiosity', 'Won %', 'Wrong %', 'First accusation (turn)', 'Never accused %', 'Own cards named', 'Mean turns'),
        ('win', 'wrong', 'first', 'never', 'named', 'turns'),
        {
            '0.0': ('0.0', '| 0.0 | 23.3 | 6.7 | 22.8 | 70 | 1.86 | 24.0 |'),
            '0.5': ('0.5', '| 0.5 | 25.8 | 4.2 | 23.5 | 70 | 1.51 | 23.9 |'),
            '1.0': ('1.0', '| 1.0 | 18.3 | 4.2 | 26.5 | 78 | 0.88 | 28.6 |'),
        },
    ),
    "sweep.ring.secrecy": Table(
        GLOSSARY, 'Dial sweeps',
        ('Secrecy', 'Won %', 'Wrong %', 'Never accused %', 'Own cards shown', 'Re-shown %', 'Mean turns'),
        ('win', 'wrong', 'never', 'leaked', 'reshow', 'turns'),
        {
            '0.0': ('0.0', '| 0.0 | 29.2 | 6.7 | 64 | 2.64 | 30.4 | 24.1 |'),
            '0.5': ('0.5', '| 0.5 | 20.0 | 8.3 | 72 | 2.90 | 38.1 | 26.6 |'),
            '1.0': ('1.0', '| 1.0 | 25.0 | 6.7 | 68 | 2.68 | 40.8 | 24.4 |'),
        },
    ),
    "sweep.ring.temperature": Table(
        GLOSSARY, 'Dial sweeps',
        ('Temperature', 'Won %', 'Wrong %', 'First accusation (turn)', 'Never accused %', 'Own cards shown', 'Own cards named', 'Re-shown %', 'Mean turns'),
        ('win', 'wrong', 'first', 'never', 'leaked', 'named', 'reshow', 'turns'),
        {
            '0.0': ('0.0', '| 0.0 | 28.3 | 10.8 | 18.7 | 61 | 2.50 | 1.13 | 44.2 | 19.7 |'),
            '0.1': ('0.1', '| 0.1 | 27.5 | 6.7 | 23.5 | 66 | 2.76 | 1.46 | 45.1 | 25.9 |'),
            '0.5': ('0.5', '| 0.5 | 9.2 | 5.8 | 19.3 | 85 | 2.78 | 0.97 | 30.9 | 29.5 |'),
            '2.0': ('2.0', '| 2.0 | 4.2 | 8.3 | 25.3 | 88 | 3.10 | 0.97 | 33.0 | 34.2 |'),
        },
    ),
    "sweep.grid.accuse_threshold": Table(
        GLOSSARY, 'Dial sweeps on the grid (Stage 1c)',
        ('Accusation threshold', 'Won %', 'Wrong %', 'First accusation (turn)', 'Never accused %', 'Mean turns'),
        ('win', 'wrong', 'first', 'never', 'turns'),
        {
            '0.2': ('0.2', '| 0.2 | 22.5 | 45.0 | 31.3 | 33 | 37.2 |'),
            '0.4': ('0.4', '| 0.4 | 23.3 | 11.7 | 38.9 | 65 | 39.5 |'),
            '0.6': ('0.6', '| 0.6 | 20.8 | 6.7 | 37.4 | 73 | 38.1 |'),
            '0.8': ('0.8', '| 0.8 | 23.3 | 2.5 | 37.1 | 74 | 39.5 |'),
            '1.0': ('1.0', '| 1.0 | 20.8 | 0.8 | 32.2 | 78 | 39.7 |'),
        },
    ),
    "sweep.grid.bluff_rate": Table(
        GLOSSARY, 'Dial sweeps on the grid (Stage 1c)',
        ('Bluff rate', 'Won %', 'Wrong %', 'Never accused %', 'Own cards named', 'Mean turns'),
        ('win', 'wrong', 'never', 'named', 'turns'),
        {
            '0.0': ('0.0', '| 0.0 | 25.0 | 12.5 | 63 | 0.69 | 37.5 |'),
            '0.25': ('0.25', '| 0.25 | 22.5 | 11.7 | 66 | 1.84 | 40.8 |'),
            '0.5': ('0.5', '| 0.5 | 20.0 | 10.0 | 70 | 3.04 | 43.5 |'),
            '1.0': ('1.0', '| 1.0 | 5.0 | 17.5 | 78 | 4.97 | 51.9 |'),
        },
    ),
    "sweep.grid.curiosity": Table(
        GLOSSARY, 'Dial sweeps on the grid (Stage 1c)',
        ('Curiosity', 'Won %', 'Wrong %', 'First accusation (turn)', 'Never accused %', 'Own cards named', 'Mean turns'),
        ('win', 'wrong', 'first', 'never', 'named', 'turns'),
        {
            '0.0': ('0.0', '| 0.0 | 20.0 | 10.8 | 34.7 | 69 | 2.25 | 39.8 |'),
            '0.5': ('0.5', '| 0.5 | 19.2 | 8.3 | 41.3 | 73 | 1.43 | 41.2 |'),
            '1.0': ('1.0', '| 1.0 | 13.3 | 5.8 | 50.1 | 81 | 0.48 | 46.2 |'),
        },
    ),
    "sweep.grid.secrecy": Table(
        GLOSSARY, 'Dial sweeps on the grid (Stage 1c)',
        ('Secrecy', 'Won %', 'Wrong %', 'Never accused %', 'Own cards shown', 'Re-shown %', 'Mean turns'),
        ('win', 'wrong', 'never', 'leaked', 'reshow', 'turns'),
        {
            '0.0': ('0.0', '| 0.0 | 20.8 | 8.3 | 71 | 2.75 | 29.0 | 37.6 |'),
            '0.5': ('0.5', '| 0.5 | 17.5 | 10.8 | 72 | 2.84 | 42.9 | 40.3 |'),
            '1.0': ('1.0', '| 1.0 | 20.8 | 9.2 | 70 | 2.71 | 48.0 | 40.5 |'),
        },
    ),
    "sweep.grid.temperature": Table(
        GLOSSARY, 'Dial sweeps on the grid (Stage 1c)',
        ('Temperature', 'Won %', 'Wrong %', 'First accusation (turn)', 'Never accused %', 'Own cards shown', 'Own cards named', 'Re-shown %', 'Mean turns'),
        ('win', 'wrong', 'first', 'never', 'leaked', 'named', 'reshow', 'turns'),
        {
            '0.0': ('0.0', '| 0.0 | 25.0 | 11.7 | 30.7 | 63 | 2.80 | 1.88 | 51.1 | 35.0 |'),
            '0.1': ('0.1', '| 0.1 | 20.8 | 10.8 | 36.1 | 68 | 2.75 | 1.71 | 43.5 | 39.3 |'),
            '0.5': ('0.5', '| 0.5 | 7.5 | 8.3 | 48.4 | 84 | 2.92 | 0.79 | 31.2 | 49.8 |'),
            '2.0': ('2.0', '| 2.0 | 1.7 | 4.2 | 63.4 | 94 | 3.24 | 0.72 | 25.2 | 58.5 |'),
        },
    ),
    'leash.pooled': Table(
        GLOSSARY, 'Leash sweep (2026-09-13)',
        ('Leash', 'Wrong %', 'Reported +/-', 'First accusation (turn)', 'Never accused %', 'Own cards named', 'Mean turns', 'Departures per accepted choice %', 'Remarks per game'),
        ('wrong', 'std', 'first', 'never', 'named', 'turns', 'dev', 'talk'),
        {
            '0': ('0', '| 0 | 25.0 | 8.8 | 41.1 | 41.7 | 6.42 | 50.4 | 0.0 | 4.92 |'),
            '0.25': ('0.25', '| 0.25 | 16.7 | 7.6 | 24.2 | 50.0 | 1.46 | 26.9 | 1.7 | 6.21 |'),
            '0.5': ('0.5', '| 0.5 | 0.0 | 0.0 | 19.1 | 66.7 | 0.46 | 19.1 | 11.1 | 6.08 |'),
            '1.0': ('1.0', '| 1.0 | 8.3 | 5.6 | 20.1 | 58.3 | 0.96 | 21.4 | 4.1 | 8.88 |'),
        },
    ),
    'ladder.plum': Table(
        GLOSSARY, 'Plum',
        ('Leash', 'Won %', 'Wrong %', 'First accusation (turn)', 'Never accused %', 'Own cards named', 'Mean turns', 'Choices played', 'Departures', 'Departures per decision'),
        ('win', 'wrong', 'first', 'never', 'named', 'turns', 'played', 'devs', 'dev'),
        {
            'headless': ('headless', '| headless | 62.5 | 0.0 | 25.9 | 37.5 | 0.88 | 24.0 | -- | -- | -- |'),
            'leash 0.25': ('leash 0.25', '| leash 0.25 | 58.3 | 0.0 | 35.1 | 41.7 | 1.33 | 30.3 | 380 | 26 | 3.0% |'),
            'leash 0.5': ('leash 0.5', '| leash 0.5 | 45.8 | 0.0 | 40.3 | 54.2 | 0.88 | 29.8 | 515 | 44 | 5.2% |'),
            'leash 1': ('leash 1', '| leash 1 | 58.3 | 4.2 | 37.2 | 37.5 | 1.25 | 32.8 | 817 | 81 | 8.8% |'),
        },
    ),
})

FACTS: dict = {
    "bench.grid.snapshots": Fact("1,080", GLOSSARY, "Belief benchmark on the grid (Stage 1a)", "1080 snapshots"),
    "bench.grid.games": Fact("60", GLOSSARY, "Belief benchmark on the grid (Stage 1a)", "benchmark --games 60 --seed 4004"),
    "bench.zero_cost": Fact("20.7", GLOSSARY, "Belief benchmark, FloorBot regime (Phase 5)", "a hard 0 on the true card would cost 20.7"),
    "plum.fallback.calls": Fact("490", GLOSSARY, "Belief benchmark on the grid (Stage 1a)", "490 of 1080 calls"),
    "plum.fallback.samples": Fact("1,485", GLOSSARY, "Belief benchmark on the grid (Stage 1a)", "1485 samples"),
    "plum.ring.ms": Fact("450", GLOSSARY, "Plum -- Exact posterior enumeration", "about 450 ms per call"),
    "plum.suite.before": Fact("95", GLOSSARY, "Tuned presets on the grid (Stage 1e, 2026-09-15)", "from about 95 s to about 220 s"),
    "plum.suite.after": Fact("220", GLOSSARY, "Tuned presets on the grid (Stage 1e, 2026-09-15)", "from about 95 s to about 220 s"),
    "plum.twin.sigma": Fact("2.3", GLOSSARY, "Twin comparison on the grid (Stage 2a, 2026-09-16)", "Plum's -31 is about 2.3 sigma"),
    "plum.claude.lost": Fact("5", GLOSSARY, "Plum with Claude on the grid (Stage 2b, 2026-09-16)", "Plum lost 5 and gained 9"),
    "plum.claude.gained": Fact("9", GLOSSARY, "Plum with Claude on the grid (Stage 2b, 2026-09-16)", "Plum lost 5 and gained 9"),
    "plum.loop.before": Fact("66 of 154", GLOSSARY, _LANDING, "| Plum | 66 of 154 (43%) to 5 of 84 (6%)"),
    "plum.loop.before.pct": Fact("43", GLOSSARY, _LANDING, "| Plum | 66 of 154 (43%) to 5 of 84 (6%)"),
    "plum.loop.after": Fact("5 of 84", GLOSSARY, _LANDING, "| Plum | 66 of 154 (43%) to 5 of 84 (6%)"),
    "plum.loop.after.pct": Fact("6", GLOSSARY, _LANDING, "| Plum | 66 of 154 (43%) to 5 of 84 (6%)"),
    "plum.landing.passage": Fact("0.50", GLOSSARY, _LANDING, "scored 0.50 at curiosity 0.5 against 0.29"),
    "plum.landing.walk": Fact("0.29", GLOSSARY, _LANDING, "scored 0.50 at curiosity 0.5 against 0.29"),
    "plum.loop.claude": Fact("148 of 291", GLOSSARY, _PLUM_CLAUDE, "| grid with Claude, `grid-plum-llm-24` | 54 / 149 | 40 / 108 | 148 of 291 (51%)"),
    "plum.loop.claude.pct": Fact("51", GLOSSARY, _PLUM_CLAUDE, "148 of 291 (51%)"),
    "plum.loop.alone": Fact("47 of 187", GLOSSARY, _PLUM_CLAUDE, "| grid headless, `grid-plum-base-24` | -- | -- | 47 of 187 (25%)"),
    "plum.loop.alone.pct": Fact("25", GLOSSARY, _PLUM_CLAUDE, "47 of 187 (25%)"),
    "plum.loop.game.from": Fact("72", GLOSSARY, _PLUM_CLAUDE, "From turn 72 to 121 he did nothing else, twenty suggestions"),
    "plum.loop.game.to": Fact("121", GLOSSARY, _PLUM_CLAUDE, "From turn 72 to 121 he did nothing else, twenty suggestions"),
    "plum.loop.game.won": Fact("122", GLOSSARY, _PLUM_CLAUDE, "Green won on turn 122 (headless, turn 45)"),
    "plum.loop.unasked": Fact("108 of 148", GLOSSARY, _PLUM_CLAUDE, "(108 of 148)"),
    "plum.logbook.stalls.off": Fact("97", GLOSSARY, _LOGBOOK, "his stalls fall from 97 to 40 over the run"),
    "plum.logbook.stalls.on": Fact("40", GLOSSARY, _LOGBOOK, "his stalls fall from 97 to 40 over the run"),
    "plum.logbook.last.off": Fact("37", GLOSSARY, _LOGBOOK, "in the last quarter from 37 to 3"),
    "plum.logbook.last.on": Fact("3", GLOSSARY, _LOGBOOK, "in the last quarter from 37 to 3"),
    "plum.logbook.games": Fact("24", GLOSSARY, _LOGBOOK, "24 paired games"),
    "landing.turns.before": Fact("53.9", GLOSSARY, _LANDING, "| `arena-grid-tuned-24` (3-6 seats, baseline) | 53.9 | 29.0 | 229 | 600 / 597 |"),
    "landing.turns.after": Fact("45.9", GLOSSARY, _LANDING, "| `arena-grid-prox2-24` (kept) | **45.9** | 18.4 | 127 | 390 / 660 |"),
    "landing.suggestions.before": Fact("29.0", GLOSSARY, _LANDING, "| `arena-grid-tuned-24` (3-6 seats, baseline) | 53.9 | 29.0 | 229 | 600 / 597 |"),
    "landing.suggestions.after": Fact("18.4", GLOSSARY, _LANDING, "| `arena-grid-prox2-24` (kept) | **45.9** | 18.4 | 127 | 390 / 660 |"),
    "arena.grid.turns": Fact("53.9", GLOSSARY, "Arena on the grid, tuned presets (Stage 1f, re-run)", "mean 53.9 turns"),
    "arena.grid.games": Fact("24", GLOSSARY, "Arena on the grid, tuned presets (Stage 1f, re-run)", "arena --games 24 --seed 7007"),
    "arena.noise": Fact("8-12", GLOSSARY, "Tuned presets on the grid (Stage 1e, 2026-09-15)", "the binomial std on a win% is 8-12 points"),
    "scarlett.ring.threshold": Fact("0.15", GLOSSARY, "Tuned presets on the grid (Stage 1e, 2026-09-15)", "**1. Scarlett's threshold: 0.15 to 0.3.**"),
    "cost.seat_game.plum": Fact("0.25", "docs/llm-wrapper.md", "Cost", "his seat-game is about $0.25"),
    "cost.seat_game.others": Fact("0.07-0.11", "docs/llm-wrapper.md", "Cost", "$0.07-0.11 per LLM seat-game"),
    # The benchmarks' sizes, and the historical one.
    "bench.ring.snapshots": Fact("1,080", GLOSSARY, _BENCH_RING, "1080 snapshots"),
    "bench.ring.seconds": Fact("573", GLOSSARY, _BENCH_RING, "573 s"),
    "bench.grid.seconds": Fact("799", GLOSSARY, _BENCH_GRID, "799 s"),
    "phase4.games": Fact("60", GLOSSARY, _PHASE4, "60 `RandomBot` games"),
    "plum.phase4": Fact("0.45", GLOSSARY, _PHASE4, "Plum 0.45"),
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
    "arena.ring.turns": Fact("27.5", GLOSSARY, "Arena, tuned presets", "mean 27.5 turns"),
    "arena.grid.first.turns": Fact("40.4", GLOSSARY, _ARENA_GRID_FIRST, "mean 40.4 turns"),
    "scarlett.ring.accused_in": Fact("4 of 20", GLOSSARY, _TUNED_RING, "she accused in only 4 of 20"),
    "green.swing": Fact("0, 6, 6, 12, 25, 0, 12, 31 and 6", GLOSSARY, _TUNED_GRID, "won 0, 6, 6, 12, 25, 0, 12, 31 and 6 percent of his games"),
    "green.confirm.win": Fact("18.8", GLOSSARY, _TUNED_GRID, "he won 18.8% of the same 24 deals in the confirmation arena"),
    # The twin comparisons.
    "twin.ring.turns.base": Fact("26.8", GLOSSARY, _TWIN_RING, "Mean game length fell from 26.8 turns to 20.3"),
    "twin.ring.turns.llm": Fact("20.3", GLOSSARY, _TWIN_RING, "Mean game length fell from 26.8 turns to 20.3"),
    "twin.ring.calls": Fact("807", GLOSSARY, _TWIN_RING, "807 calls across 1801 decisions"),
    "twin.ring.cost": Fact("6.98", GLOSSARY, _TWIN_RING, "$6.98 at list prices"),
    "twin.ring.bluff.white.base": Fact("3.69", GLOSSARY, _TWIN_RING, "White 3.69 to 0.25"),
    "twin.ring.bluff.white.llm": Fact("0.25", GLOSSARY, _TWIN_RING, "White 3.69 to 0.25"),
    "twin.ring.bluff.mustard.base": Fact("2.44", GLOSSARY, _TWIN_RING, "Mustard 2.44 to 0.31"),
    "twin.ring.bluff.mustard.llm": Fact("0.31", GLOSSARY, _TWIN_RING, "Mustard 2.44 to 0.31"),
    "twin.ring.bluff.scarlett.base": Fact("1.50", GLOSSARY, _TWIN_RING, "Scarlett 1.50 to 0.44"),
    "twin.ring.bluff.scarlett.llm": Fact("0.44", GLOSSARY, _TWIN_RING, "Scarlett 1.50 to 0.44"),
    "twin.grid.turns.base": Fact("41.9", GLOSSARY, _TWIN_GRID, "Mean game length 41.9 turns headless, 37.1 with Claude"),
    "twin.grid.turns.llm": Fact("37.1", GLOSSARY, _TWIN_GRID, "Mean game length 41.9 turns headless, 37.1 with Claude"),
    "twin.grid.calls": Fact("1,018", GLOSSARY, _TWIN_GRID, "1018 calls across 2794 decisions"),
    "twin.grid.cost": Fact("9.36", GLOSSARY, _TWIN_GRID, "**$9.36**"),
    "twin.grid.sigma.mustard": Fact("1.9", GLOSSARY, _TWIN_GRID, "Mustard's wrong% -25 about 1.9"),
    "twin.grid.sigma.peacock": Fact("1.3", GLOSSARY, _TWIN_GRID, "his win% +19 and Peacock's +19 about 1.3 each"),
    "twin.grid.bluff.white.base": Fact("4.06", GLOSSARY, _TWIN_GRID, "White 4.06 to 0.44"),
    "twin.grid.bluff.white.llm": Fact("0.44", GLOSSARY, _TWIN_GRID, "White 4.06 to 0.44"),
    "twin.grid.bluff.scarlett.base": Fact("1.94", GLOSSARY, _TWIN_GRID, "Scarlett 1.94 to 0.56"),
    "twin.grid.bluff.scarlett.llm": Fact("0.56", GLOSSARY, _TWIN_GRID, "Scarlett 1.94 to 0.56"),
    "twin.grid.bluff.peacock.base": Fact("1.56", GLOSSARY, _TWIN_GRID, "Peacock 1.56 to 0.62"),
    "twin.grid.bluff.peacock.llm": Fact("0.62", GLOSSARY, _TWIN_GRID, "Peacock 1.56 to 0.62"),
    "twin.grid.bluff.green.base": Fact("1.38", GLOSSARY, _TWIN_GRID, "Green 1.38 to 0.62"),
    "twin.grid.bluff.green.llm": Fact("0.62", GLOSSARY, _TWIN_GRID, "Green 1.38 to 0.62"),
    "twin.grid.bluff.mustard.base": Fact("1.62", GLOSSARY, _TWIN_GRID, "Mustard (1.62 to 1.75)"),
    "twin.grid.bluff.mustard.llm": Fact("1.75", GLOSSARY, _TWIN_GRID, "Mustard (1.62 to 1.75)"),
    "mustard.loop.claude.pct": Fact("34", GLOSSARY, _TWIN_GRID, "34% of his suggestions repeat (10% headless)"),
    "mustard.loop.alone.pct": Fact("10", GLOSSARY, _TWIN_GRID, "34% of his suggestions repeat (10% headless)"),
    "mustard.loop.trips": Fact("31", GLOSSARY, _TWIN_GRID, "31 wasted trips, 17 of them asked"),
    # Mustard alone with Claude, the ring.
    "mustard.ladder.cost": Fact("8.94", GLOSSARY, _LADDER_MUSTARD, "3013 s, $8.94, no fallbacks in 1176 calls"),
    "mustard.ladder.calls": Fact("1,176", GLOSSARY, _LADDER_MUSTARD, "no fallbacks in 1176 calls"),
    "mustard.ladder.talk.low": Fact("2.75", GLOSSARY, _LADDER_MUSTARD, "(2.75 to 7.62)"),
    "mustard.ladder.talk.high": Fact("7.62", GLOSSARY, _LADDER_MUSTARD, "(2.75 to 7.62)"),
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
    "white.memory.green": Fact("902", GLOSSARY, _MEMORY, "902 / 985 / 1,211 transitions for Green / Mustard / Plum"),
    "white.memory.mustard": Fact("985", GLOSSARY, _MEMORY, "902 / 985 / 1,211 transitions for Green / Mustard / Plum"),
    "white.memory.plum": Fact("1,211", GLOSSARY, _MEMORY, "902 / 985 / 1,211 transitions for Green / Mustard / Plum"),
    # Green's arms, as the two benchmarks left them.
    "green.arms.spread": Fact("0.4", GLOSSARY, "Green -- Bandit ensemble over the other five", "his arms separate by about 0.4 in posterior mean over 60 games"),
    "green.arms.ring.plum": Fact("0.71", GLOSSARY, "Green -- Bandit ensemble over the other five", "Plum and Mustard (0.71, 0.69) over White (0.46), Peacock (0.35) and Scarlett (0.29)"),
    "green.arms.ring.mustard": Fact("0.69", GLOSSARY, "Green -- Bandit ensemble over the other five", "Plum and Mustard (0.71, 0.69)"),
    "green.arms.ring.white": Fact("0.46", GLOSSARY, "Green -- Bandit ensemble over the other five", "White (0.46)"),
    "green.arms.ring.peacock": Fact("0.35", GLOSSARY, "Green -- Bandit ensemble over the other five", "Peacock (0.35)"),
    "green.arms.ring.scarlett": Fact("0.29", GLOSSARY, "Green -- Bandit ensemble over the other five", "Scarlett (0.29)"),
    "green.arms.grid.mustard": Fact("0.72", GLOSSARY, _BENCH_GRID, "lean on Mustard (0.72) and Plum (0.57) and away from Peacock (0.31) and Scarlett (0.37)"),
    "green.arms.grid.plum": Fact("0.57", GLOSSARY, _BENCH_GRID, "Plum (0.57)"),
    "green.arms.grid.peacock": Fact("0.31", GLOSSARY, _BENCH_GRID, "Peacock (0.31)"),
    "green.arms.grid.scarlett": Fact("0.37", GLOSSARY, _BENCH_GRID, "Scarlett (0.37)"),
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
        ``mask``, the floor's own view of the position.
    """
    from clude_agents.bandit import BanditAgent, RevealedOutcome, log_loss
    from clude_agents.base import mask_and_normalize
    from clude_agents.decision_tree import FEATURE_NAMES, DecisionTreeAgent, _features
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
    assert abs(float(stationary) - _stationary_repeat_probability(symbols)) < 1e-12
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

    from clude_agents import bandit, decision_tree, exact_enum, markov, naive_bayes
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
        for dial in ("accuse_threshold", "bluff_rate", "curiosity", "secrecy", "temperature"):
            table[f"preset.{name}.{dial}"] = lambda n=name, d=dial: _preset(n, d)

    # The other four methods on the same question (W2).
    table["example.plum.nodes"] = lambda: str(rope_question()["nodes"])
    for card in ROPE_CARDS:
        table[f"example.peacock.{card}"] = lambda c=card: _trim(rope_question()["peacock"][c], 2)
        table[f"example.peacock.{card}.bel"] = lambda c=card: _trim(rope_question()["peacock_belief"][c], 2)
        table[f"example.peacock.{card}.pl"] = lambda c=card: _trim(rope_question()["peacock_plausibility"][c], 2)
        table[f"example.mustard.{card}"] = lambda c=card: _trim(rope_question()["mustard"][c], 2)
        table[f"example.white.{card}"] = lambda c=card: _trim(rope_question()["white"][c], 2)
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
    for name in ("debrief_max_tokens", "debrief_timeout"):
        table[f"llm.{name}"] = lambda n=name: _trim(getattr(LLMSettings(), n))
    for depth in (0, 0.25, 0.5, 0.75, 1):
        for index, label in enumerate(("index", "full")):
            table[f"memory.{depth}.{label}"] = lambda d=depth, i=index: str(memory_counts(10, d)[i])
    return table


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
