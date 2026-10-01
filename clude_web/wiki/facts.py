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
}

_LANDING = "The landing rule (Phase 8.0.4, 2026-09-18)"
_LOGBOOK = "Plum's logbook at leash 0.5 (2026-09-14)"
_PLUM_CLAUDE = "Plum with Claude on the grid (Stage 2b, 2026-09-16)"

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


@lru_cache(maxsize=1)
def rope_question() -> dict:
    """The worked example the method articles share, run on the real code.

    Late in a three-seat game, from seat 0's chair: every card is placed
    except two suspects (White, Peacock) and two weapons (Rope, Wrench).
    One of each is in the envelope; the other of each is in seat 1's
    hand, which has exactly two cards unplaced. Seat 2 then suggests
    Peacock with the Rope in the Hall, a room seat 2 holds; seat 0
    cannot answer, and seat 1 shows seat 2 a card seat 0 does not see:
    so seat 1 holds Peacock or the Rope, or both.

    Returns
    -------
    dict
        ``deals``: the consistent deals Plum's search finds; ``plum``:
        his exact envelope probabilities for the four open cards;
        ``scarlett``: hers after the suggestion has been made once,
        twice and three times (``scarlett[n]``); ``uniform``: the
        floor's own, before the suggestion.
    """
    from clude_agents.base import mask_and_normalize
    from clude_agents.exact_enum import ExactEnumAgent
    from clude_agents.naive_bayes import NaiveBayesAgent
    from clude_constraints import ENVELOPE, ConstraintResult
    from clude_core.domain import ROOMS, SUSPECTS, WEAPONS, Suggestion
    from clude_core.state import ClueObservation

    me, holder, third = 0, 1, 2
    open_cards = ("White", "Peacock", "Rope", "Wrench")
    envelope_room = "Study"
    hands = {
        me: ["Scarlett", "Mustard", "Candlestick", "Knife", "Kitchen", "Ballroom"],
        holder: ["Green", "Lead_Pipe", "Conservatory", "Billiard"],  # and two of the open cards
        third: ["Plum", "Revolver", "Library", "Hall", "Lounge", "Dining"],
    }
    possible = {card: frozenset({holder, ENVELOPE}) for card in open_cards}
    possible[envelope_room] = frozenset({ENVELOPE})
    for seat, cards in hands.items():
        for card in cards:
            possible[card] = frozenset({seat})
    assert set(possible) == set(SUSPECTS + WEAPONS + ROOMS)

    asked = Suggestion(suggester=third, suspect="Peacock", weapon="Rope", room="Hall",
                       refuter=holder, shown_to=third, card_shown=None)

    def observation(times: int) -> ClueObservation:
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

    plum = ExactEnumAgent()
    plum.reset(0)
    exact = plum.select_action(observation(1))
    assert exact.extra["method"] == "exact"
    scarlett = NaiveBayesAgent()
    return {
        "deals": exact.extra["completions"],
        "plum": {c: exact.probabilities[c] for c in open_cards},
        "scarlett": {n: {c: scarlett.select_action(observation(n)).probabilities[c] for c in open_cards} for n in (1, 2, 3)},
        "uniform": {c: mask_and_normalize({}, observation(0).mask)[c] for c in open_cards},
    }


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


def _code() -> dict:
    from clude_agents import exact_enum, naive_bayes
    from clude_core.domain import ALL_CARDS, ROOMS, SUSPECTS, WEAPONS

    table: dict = {
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
        table[f"example.uniform.{card}"] = lambda c=card: str(Fraction(rope_question()["uniform"][c]).limit_denominator(100))
        for n in (1, 2, 3):
            table[f"example.scarlett.{n}.{card}"] = lambda c=card, n=n: _trim(rope_question()["scarlett"][n][c], 2)
            table[f"example.scarlett.{n}.{card}.pct"] = lambda c=card, n=n: f"{rope_question()['scarlett'][n][c] * 100:.0f}"
    table["example.plum.pair"] = lambda: _trim(rope_question()["plum"]["White"] * rope_question()["plum"]["Wrench"], 2)
    table["example.scarlett.3.pair"] = lambda: _trim(rope_question()["scarlett"][3]["White"] * rope_question()["scarlett"][3]["Wrench"], 2)
    for name in ("Scarlett", "Mustard", "White", "Green", "Peacock", "Plum"):
        for dial in ("accuse_threshold", "bluff_rate", "curiosity", "secrecy", "temperature"):
            table[f"preset.{name}.{dial}"] = lambda n=name, d=dial: _preset(n, d)
    return table


CODE: dict = _code()
"""Every ``{{code:key}}``: a name and how to compute it. Evaluated when
an article is rendered, not at import."""


def code(key: str) -> str:
    """The printed value of a constant or computed example.

    Raises
    ------
    KeyError
        If nothing has that key.
    """
    return CODE[key]()
