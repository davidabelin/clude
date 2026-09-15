"""Tier 1 of Phase 7's memory: the numeric, method-level kind, fed from
stored game records and kept as the ``method.json`` document of a
character's logbook (`clude_storage.logbooks`). No model is involved;
this is what "learns across games" means for the three methods that
have anything numeric to learn:

- **Mustard** (`kind == "rows"`): `decision_tree.rows_from_view` rows
  from every seat's view of every stored game at Mustard's training
  checkpoints, appended to his self-play base before the tree is
  trained (`DecisionTreeAgent.set_extra_rows`). He learns from games
  he did not sit in too: the rows are the same kind of evidence, and
  the tree wants volume.
- **White** (`kind == "counts"`): `markov.transition_counts` of every
  seat's suggestion sequence in every stored game, summed per roster
  label, so his chain for a known opponent starts from how that
  opponent actually plays (`MarkovAgent.set_priors` + `set_table`).
- **Green** (`kind == "state"`): his Beta posteriors, saved after every
  game and restored after `reset` (`BanditAgent.state_dict` /
  `load_state`). Only accumulated live: they depend on what his arms
  predicted, which no record holds, so `rebuild` cannot recompute them.

The other three methods (Scarlett, Plum, Peacock) are memoryless by
construction; their memory is the narrative tier only.

Documents are keyed by game id (``<run_id>/<index>``) so an incremental
`update` and a `rebuild` from the whole store agree, and updating twice
with one game changes nothing. With no logbook, or an empty one,
`load_into` leaves a character exactly as built, which is what keeps the
golden games golden.
"""
from __future__ import annotations

from typing import Optional

from clude_agents.decision_tree import DEFAULT_CHECKPOINTS as MUSTARD_CHECKPOINTS, rows_from_view
from clude_agents.markov import TRANSITION_KEYS, suggestion_patterns, transition_counts
from clude_storage import GameRecord, Logbook
from clude_training.replay import snapshots_from_record, state_from_record

MEMORY_VERSION = 1
ROW_DECIMALS = 6
MEMORY_KINDS: dict = {"Mustard": "rows", "White": "counts", "Green": "state"}
"""Identity -> the shape of its method memory; absent means memoryless."""


def game_id_of(record: GameRecord) -> str:
    """``<run_id>/<index>``, the key a game's contribution is stored under."""
    return f"{record.run_id}/{record.game_index:05d}"


def kind_for(identity: str) -> Optional[str]:
    """The memory kind for a roster label, or None for a memoryless one."""
    return MEMORY_KINDS.get(identity)


def kind_of(agent) -> Optional[str]:
    """The memory kind an agent can take, by what it implements."""
    if hasattr(agent, "set_extra_rows"):
        return "rows"
    if hasattr(agent, "set_priors"):
        return "counts"
    if hasattr(agent, "load_state"):
        return "state"
    return None


# ---------------------------------------------------------------------
# What one record contributes
# ---------------------------------------------------------------------


def mustard_rows(record: GameRecord, checkpoints: tuple = MUSTARD_CHECKPOINTS) -> list:
    """Mustard's rows from every seat's view of `record` at `checkpoints`,
    as JSON-ready ``[f1, ..., f8, label]`` lists."""
    rows: list = []
    for snap in snapshots_from_record(record, checkpoints):
        for features, label in rows_from_view(snap.obs, snap.envelope):
            rows.append([round(float(f), ROW_DECIMALS) for f in features] + [int(label)])
    return rows


def white_counts(record: GameRecord) -> dict:
    """Every seat's `transition_counts` in `record`, summed per roster
    label; seats with fewer than two suggestions contribute nothing."""
    state = state_from_record(record)
    seats = list(range(state.n_players))
    _named, symbols, _evidence = suggestion_patterns(state.suggestion_log, seats)
    labels = {s.seat: s.label for s in record.seats}
    out: dict = {}
    for seat in seats:
        counts = transition_counts(symbols[seat])
        if not any(counts.values()):
            continue
        bucket = out.setdefault(labels.get(seat, f"seat{seat}"), {key: 0 for key in TRANSITION_KEYS})
        for key, n in counts.items():
            bucket[key] += n
    return out


# ---------------------------------------------------------------------
# The memory document
# ---------------------------------------------------------------------


def empty_memory(kind: str) -> dict:
    """A fresh document of `kind`.

    Raises
    ------
    ValueError
        On an unknown kind.
    """
    if kind == "state":
        return {"version": MEMORY_VERSION, "kind": kind, "games": 0, "arms": {}}
    if kind in ("rows", "counts"):
        return {"version": MEMORY_VERSION, "kind": kind, "games": {}}
    raise ValueError(f"unknown memory kind {kind!r}")


def absorb(memory: dict, record: GameRecord) -> bool:
    """Add `record`'s contribution to a ``rows`` or ``counts`` document;
    False if the game is already in it (or the kind takes no records)."""
    kind = memory.get("kind")
    if kind not in ("rows", "counts"):
        return False
    game_id = game_id_of(record)
    games = memory.setdefault("games", {})
    if game_id in games:
        return False
    games[game_id] = mustard_rows(record) if kind == "rows" else white_counts(record)
    return True


def extra_rows(memory: dict) -> list:
    """Mustard's memory rows as ``(features, label)`` tuples, in game-id
    order so training is deterministic for a given document."""
    rows: list = []
    for game_id in sorted(memory.get("games", {})):
        for row in memory["games"][game_id]:
            rows.append((tuple(float(f) for f in row[:-1]), int(row[-1])))
    return rows


def priors(memory: dict) -> dict:
    """White's per-label transition counts summed over the document's
    games."""
    out: dict = {}
    for game_id in sorted(memory.get("games", {})):
        for label, counts in memory["games"][game_id].items():
            bucket = out.setdefault(label, {key: 0 for key in TRANSITION_KEYS})
            for key in TRANSITION_KEYS:
                bucket[key] += int(counts.get(key, 0))
    return out


def n_games(memory: Optional[dict]) -> int:
    """How many games a document has absorbed (of either shape)."""
    if not memory:
        return 0
    games = memory.get("games", 0)
    return len(games) if isinstance(games, dict) else int(games)


def describe_memory(memory: Optional[dict]) -> str:
    """One line for the CLI: what a document holds."""
    if not memory:
        return "no method memory"
    kind = memory.get("kind")
    if kind == "rows":
        games = memory.get("games", {})
        return f"Mustard's tree: {sum(len(v) for v in games.values())} rows from {len(games)} stored games"
    if kind == "counts":
        summed = priors(memory)
        per_label = ", ".join(
            f"{label} {sum(counts.values())}" for label, counts in sorted(summed.items())
        )
        return (
            f"White's chains: {n_games(memory)} stored games; transitions per opponent: "
            f"{per_label or 'none'}"
        )
    if kind == "state":
        arms = memory.get("arms", {})
        means = ", ".join(
            f"{name} {a / (a + b):.2f}" for name, (a, b) in sorted(arms.items()) if a + b > 0
        )
        return f"Green's posteriors after {n_games(memory)} games: {means or 'none'}"
    return f"unknown memory kind {kind!r}"


# ---------------------------------------------------------------------
# Wiring a character to its logbook
# ---------------------------------------------------------------------


def load_into(character, logbook: Logbook) -> bool:
    """Give `character`'s agent its stored memory, if it has one and the
    document matches its kind. Call after `reset`, which for Green wipes
    the posteriors. Returns whether anything was loaded; a memoryless
    character, an empty logbook, or an empty document leave the agent
    exactly as built."""
    agent = character.agent
    kind = kind_of(agent)
    if kind is None:
        return False
    memory = logbook.method()
    if memory is None or memory.get("kind") != kind:
        return False
    if kind == "rows":
        rows = extra_rows(memory)
        agent.set_extra_rows(rows)
        return bool(rows)
    if kind == "counts":
        counts = priors(memory)
        agent.set_priors(counts)
        return bool(counts)
    return agent.load_state(memory) > 0


def update(logbook: Logbook, record: GameRecord, character) -> bool:
    """After a game: fold `record` into `character`'s method memory in
    `logbook` (Mustard, White), or save its live state (Green). Returns
    whether the document changed; a game already absorbed, or a
    memoryless character, changes nothing."""
    agent = character.agent
    kind = kind_of(agent)
    if kind is None:
        return False
    memory = logbook.method()
    if memory is None or memory.get("kind") != kind:
        memory = empty_memory(kind)
    if kind == "state":
        memory.update(agent.state_dict())
        memory["games"] = n_games(memory) + 1
    elif not absorb(memory, record):
        return False
    logbook.save_method(memory)
    return True


def rebuild(logbook: Logbook, store, kind: str) -> int:
    """Recompute a ``rows`` or ``counts`` document from every game record
    in `store` (every run folder under ``games/``, summaries or not) and
    store it. Returns how many games it absorbed.

    Raises
    ------
    ValueError
        For the ``state`` kind, which no record can rebuild.
    """
    if kind == "state":
        raise ValueError("Green's posteriors are accumulated live; records cannot rebuild them")
    memory = empty_memory(kind)
    absorbed = 0
    for run_id in store.list_folders("games"):
        for index in store.list_games(run_id):
            record = GameRecord.from_dict(store.get_game(run_id, index))
            absorbed += int(absorb(memory, record))
    logbook.save_method(memory)
    return absorbed
