"""Unified maintainer CLI: play, trace, inspect, benchmark, train, and
run the arena for clude's headless pieces from the terminal.

Every subcommand is headless and deterministic for a given ``--seed``,
so anything printed here can be reproduced exactly and pasted into a doc
or a bug report. Mirrors ``rps/scripts/rps_cli.py``'s subcommand shape.
See docs/cli.md for what each command shows and how to read it.

Usage
-----
    python scripts/clude_cli.py --help
    python scripts/clude_cli.py agents
    python scripts/clude_cli.py play --players 4 --seed 1 --verbose --hands
    python scripts/clude_cli.py play --roster Scarlett,Plum,Peacock,floor --verbose
    python scripts/clude_cli.py trace --seed 1 --viewer 0 --agents Plum,Scarlett
    python scripts/clude_cli.py floor --seed 1 --viewer 0 --at 10
    python scripts/clude_cli.py floor --seed 1 --convergence
    python scripts/clude_cli.py benchmark --games 20 --show-green --json data/exports/bench.json
    python scripts/clude_cli.py train-mustard --games 50 --max-depth 8 --render
    python scripts/clude_cli.py snapshots --games 40 --bot floor
    python scripts/clude_cli.py arena --games 24 --store data
    python scripts/clude_cli.py sweep --dial accuse_threshold --values 0.3 0.6 0.9
    python scripts/clude_cli.py store --uri data --list
    python scripts/clude_cli.py store copy --uri data/llm --to gs://clude-game-data/llm --dry-run
    python scripts/clude_cli.py play --roster Plum,Mustard,Green --store data/llm
    python scripts/clude_cli.py logbook list --uri data/llm
    python scripts/clude_cli.py logbook show --uri data/llm --identity Plum --memory 0.5
"""
from __future__ import annotations

import argparse
import dataclasses
import getpass
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import clude_constraints
from clude_agents import AGENT_SPECS, build_agent, build_character, list_agent_specs
from clude_agents.character import best_triple, ds_belief_confidence
from clude_agents.decision_tree import (
    DEFAULT_CHECKPOINTS as MUSTARD_CHECKPOINTS,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MIN_SAMPLES_LEAF,
    DEFAULT_N_TRAINING_GAMES,
    DEFAULT_SMOOTHING_M,
    DEFAULT_TRAINING_BOT,
    DEFAULT_TRAINING_SEED,
    FEATURE_NAMES,
    DecisionTreeAgent,
    render_tree,
    summarize_tree,
    training_rows,
)
from clude_agents.explain import (
    describe_suggestion,
    format_accusation_test,
    format_belief,
    format_extra,
    format_mask,
    seat_label,
    seat_labels,
)
from clude_agents.personality import DIALS, preset
from clude_core import board, engine
from clude_core.bots import RandomBot
from clude_core.domain import ALL_CARDS, ROOMS, SUSPECTS, WEAPONS
from clude_core.events import AccusationEvent, GameOverEvent, MoveEvent, RemarkEvent, SuggestionEvent
from clude_core.state import ClueObservation
from clude_llm import (
    DEFAULT_MODEL,
    LLMCharacter,
    LLMSettings,
    NullBackend,
    accusation_menu,
    movement_menu,
    open_backend,
    show_menu,
    suggestion_menu,
    user_prompt,
)
from clude_llm.anthropic_backend import estimate_cost
from clude_storage import GameRecord, Logbook, SeatRecord, list_logbooks, open_store, render_entry
from clude_storage.records import GRID_RECORD_VERSION
from clude_storage.mirror import LOGBOOK_PREFIX, TRACE_PREFIX, copy_docs, plan_mirror
from clude_training import memory as method_memory
from clude_training.table import TableError, TableGame, TableSetup, describe_request
from clude_training.arena import (
    BOT_LABELS,
    DEFAULT_MAX_TURNS as ARENA_MAX_TURNS,
    DEFAULT_N_GAMES as ARENA_N_GAMES,
    DEFAULT_ROSTER,
    DEFAULT_SEED as ARENA_SEED,
    GameSummary,
    fill_seed,
    lineup_for_game,
    seat_lineup,
    parse_roster,
    run_arena,
)
from clude_training.benchmark import DEFAULT_N_GAMES, DEFAULT_SEED, run_benchmark
from clude_training.self_play import (
    BOT_KINDS,
    DEFAULT_BOT,
    DEFAULT_CHECKPOINTS,
    DEFAULT_MAX_TURNS,
    DEFAULT_PLAYER_COUNTS,
    generate_snapshots,
    truncate_state,
)
from clude_training.sweep import sweep_dial
from clude_training.trace import belief_trace, floor_convergence, resolved_count

DEFAULT_STORE = "data"

WEB_STORE = "data/llm"
"""Where the `users` subcommand puts accounts: the store the web app
reads, which is not the CLI's `DEFAULT_STORE`. Kept as a literal rather
than imported so that the CLI still runs without Flask installed;
`tests/test_web.py` pins it equal to `clude_web.config.DEFAULT_STORE`."""


# ---------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------


def _player_label(state, player: int, labels=None) -> str:
    """``P2 White``, or ``P2 White (Plum)`` when a different character
    occupies the White token."""
    return seat_label(state.suspects_in_play, player, labels)


def _node_label(node) -> str:
    """A room name, ``(7,4)`` for a corridor square, or
    ``Kitchen~Ballroom[2]`` for a ring-era cell from an old record."""
    if isinstance(node, board.Square):
        return f"({node.row},{node.col})"
    if isinstance(node, board.HallwayCell):
        return f"{node.room_a}~{node.room_b}[{node.k}]"
    return str(node)


def _add_game_args(parser: argparse.ArgumentParser) -> None:
    """The knobs every one-game command shares."""
    parser.add_argument("--players", type=int, default=4, help="Table size, 3-6 (default 4).")
    parser.add_argument(
        "--seed", type=int, default=1,
        help="Seed for the deal, the dice, and every player (default 1, so runs are reproducible).",
    )
    parser.add_argument(
        "--max-turns", type=int, default=300,
        help="Turn cap if nobody accuses correctly (default 300).",
    )
    parser.add_argument(
        "--roster", default="random",
        help="Who plays: 'random' (RandomBots), 'floor' (FloorBots), or a comma-separated "
        "lineup of suspect names and 'floor' fill seats, seated in that order.",
    )


def _add_llm_args(parser: argparse.ArgumentParser) -> None:
    """The Phase 6 flags: pilot the roster's characters with an LLM."""
    parser.add_argument(
        "--llm", action="store_true",
        help="Wrap every character seat in an LLMCharacter (docs/phase6-plan.md).",
    )
    parser.add_argument(
        "--llm-backend", default="anthropic",
        help="'anthropic', 'null' (never answers: the headless twin), 'record:PATH' or 'replay:PATH'.",
    )
    parser.add_argument("--llm-model", default=DEFAULT_MODEL, help="Model id for the anthropic backend.")
    parser.add_argument(
        "--llm-characters", default="",
        help="Comma-separated subset of the roster's characters to wrap (default: all of them).",
    )


def _open_llm_backend(args):
    """`open_backend` for the CLI flags, with `LLMSettings`' defaults for
    the Anthropic backend's knobs."""
    settings = LLMSettings(model=args.llm_model)
    try:
        return open_backend(
            args.llm_backend, model=settings.model, effort=settings.effort,
            max_tokens=settings.max_tokens, timeout=settings.timeout,
            server_fallbacks=settings.server_fallbacks,
        )
    except (ValueError, FileNotFoundError, ImportError) as exc:
        raise SystemExit(f"--llm-backend {args.llm_backend!r}: {exc}") from exc


def _llm_kwargs(args) -> dict:
    """`run_arena` / `sweep_dial` keyword arguments for the ``--llm`` flags;
    empty without ``--llm``."""
    if not getattr(args, "llm", False):
        return {}
    wanted = [name.strip() for name in args.llm_characters.split(",") if name.strip()]
    unknown = [name for name in wanted if name not in AGENT_SPECS]
    if unknown:
        raise SystemExit(f"--llm-characters: unknown {unknown}; run `agents` for the names")
    return {
        "llm_backend": _open_llm_backend(args),
        "llm_settings": LLMSettings(model=args.llm_model),
        "llm_characters": wanted or None,
    }


def _add_logbook_args(parser: argparse.ArgumentParser) -> None:
    """The Phase 7 flags: give every character its logbook."""
    parser.add_argument(
        "--logbook", nargs="?", const="", default=None, metavar="URI",
        help="Give every character its logbook from this store (with no URI, the --store "
        "location): method memory read before each game and written after it (docs/phase7-plan.md).",
    )
    parser.add_argument(
        "--logbook-readonly", action="store_true",
        help="Read the logbooks but write nothing to them (a fair comparison against a fixed memory).",
    )
    parser.add_argument(
        "--logbook-characters", default="",
        help="Comma-separated subset of the roster's characters that get a logbook (default: all of "
        "them); the rest play exactly as they do without memory.",
    )


def _logbook_store(args):
    """The logbook store for the ``--logbook`` flags, or None."""
    uri = getattr(args, "logbook", None)
    if uri is None:
        return None
    uri = uri or getattr(args, "store", "")
    if not uri:
        raise SystemExit("--logbook needs a store: give it a URI, or pass --store as well")
    return open_store(uri)


def _logbook_characters(args):
    """The ``--logbook-characters`` names as a list, or None for all."""
    raw = getattr(args, "logbook_characters", "") or ""
    wanted = [name.strip() for name in raw.split(",") if name.strip()]
    unknown = [name for name in wanted if name not in AGENT_SPECS]
    if unknown:
        raise SystemExit(f"--logbook-characters: unknown {unknown}; run `agents` for the names")
    return wanted or None


def _has_logbook(args, label: str) -> bool:
    """Whether `label`'s seat gets a logbook under the ``--logbook`` flags."""
    wanted = _logbook_characters(args)
    return label in AGENT_SPECS and (wanted is None or label in wanted)


def _logbook_kwargs(args) -> dict:
    """`run_arena` keyword arguments for the ``--logbook`` flags."""
    store = _logbook_store(args)
    if store is None:
        return {}
    return {
        "logbook_store": store,
        "logbooks_readonly": bool(getattr(args, "logbook_readonly", False)),
        "logbook_characters": _logbook_characters(args),
    }


def _print_llm_cost(per_player: dict, model: str, n_games: int) -> None:
    stats = [s for s in per_player.values() if s.llm_decisions]
    if not stats:
        return
    cost = estimate_cost(
        model,
        sum(s.llm_input_tokens for s in stats),
        sum(s.llm_output_tokens for s in stats),
        sum(s.llm_cached_tokens for s in stats),
    )
    if cost is not None:
        print(f"estimated LLM cost at list prices: ${cost:.4f} for {n_games} games")


def _wrap_llm_seats(args, players: dict, labels: list) -> dict:
    """Replace the chosen character seats with `LLMCharacter`s sharing one
    backend; returns ``{seat: wrapper}``."""
    wanted = {name.strip() for name in args.llm_characters.split(",") if name.strip()}
    unknown = wanted - set(AGENT_SPECS)
    if unknown:
        raise SystemExit(f"--llm-characters: unknown {sorted(unknown)}; run `agents` for the names")
    backend = _open_llm_backend(args)
    settings = LLMSettings(model=args.llm_model)
    wrapped = {}
    for seat, label in enumerate(labels):
        if label in AGENT_SPECS and (not wanted or label in wanted):
            wrapper = LLMCharacter(players[seat], backend, settings=settings)
            wrapper.reset(args.seed)
            players[seat] = wrapped[seat] = wrapper
    return wrapped


def _play_game(args, llm_seats: dict = None, players_out: dict = None):
    """One finished game from the shared game args: ``(state, events,
    labels)`` where `labels` names each seat's occupant. With ``--llm``
    the character seats are wrapped first and, if `llm_seats` is given,
    recorded in it as ``{seat: LLMCharacter}``; `players_out`, if given,
    receives every seat's player as ``{seat: player}``."""
    n = args.players
    roster = args.roster.strip()
    suspects = None
    if roster == "random":
        players = {p: RandomBot() for p in range(n)}
        labels = ["random"] * n
        observer = ClueObservation.for_player
    elif roster == "floor":
        players = {p: clude_constraints.FloorBot() for p in range(n)}
        labels = ["floor"] * n
        observer = clude_constraints.observe
    else:
        try:
            labels, suspects = seat_lineup(lineup_for_game(parse_roster(roster.split(",")), 0, n))
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        players = {}
        for seat, label in enumerate(labels):
            if label in AGENT_SPECS:
                character = build_character(label)
                character.reset(args.seed)
                players[seat] = character
            elif label == "floor":
                players[seat] = clude_constraints.FloorBot(rng=random.Random(fill_seed(args.seed, seat)))
            else:
                players[seat] = RandomBot()
        if getattr(args, "llm", False):
            wrapped = _wrap_llm_seats(args, players, labels)
            if llm_seats is not None:
                llm_seats.update(wrapped)
        logbook_store = _logbook_store(args)
        for seat, label in enumerate(labels):
            if label in AGENT_SPECS:
                if logbook_store is not None and _has_logbook(args, label):
                    logbook = Logbook(logbook_store, label)
                    method_memory.load_into(players[seat], logbook)
                    if hasattr(players[seat], "attach_logbook"):
                        players[seat].attach_logbook(logbook)
                players[seat].new_game(labels)
        observer = clude_constraints.observe
    if players_out is not None:
        players_out.update(players)
    state, events = engine.run_game(
        n, players, seed=args.seed, max_turns=args.max_turns, observer=observer, suspects=suspects
    )
    return state, events, labels


def _seat_records(state, labels: list, players: dict, llm_seats: dict, model: str) -> list:
    """`SeatRecord`s for one `_play_game` table, the arena's way: kind
    from the occupant, the character's dials, the model behind an LLM
    seat."""
    seats = []
    for seat, label in enumerate(labels):
        if seat in llm_seats:
            kind = "llm"
        elif label in AGENT_SPECS:
            kind = "character"
        else:
            kind = label
        profile = players[seat].profile.to_dict() if kind in ("llm", "character") else None
        seats.append(
            SeatRecord(
                seat=seat,
                suspect=state.suspects_in_play[seat],
                label=label,
                kind=kind,
                profile=profile,
                model=model if kind == "llm" else None,
            )
        )
    return seats


def _play_record(args, state, events, labels: list, players: dict, llm_seats: dict) -> GameRecord:
    """The `GameRecord` of one `play` game, as game 0 of a run named by
    ``--run-id`` (default ``play-<seed>-<UTC timestamp>``); written to
    ``--store`` with a one-game run summary when that flag is given."""
    run_id = args.run_id or f"play-{args.seed}-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}"
    llm_log = {seat: [d.to_dict() for d in wrapper.decisions] for seat, wrapper in llm_seats.items()}
    seats = _seat_records(state, labels, players, llm_seats, getattr(args, "llm_model", DEFAULT_MODEL))
    record = GameRecord.from_game(run_id, 0, args.seed, state, events, seats, llm_log=llm_log or None)
    if not getattr(args, "store", ""):
        return record
    store = open_store(args.store)
    store.put_game(run_id, 0, record.to_dict())
    # A one-game run summary in the arena's shape, so `store` lists it.
    llm = {}
    if llm_seats:
        first = next(iter(llm_seats.values())).summary()
        llm = {
            "backend": first["backend"], "model": first["model"],
            "characters": sorted(labels[seat] for seat in llm_seats),
        }
    summary = GameSummary(
        game_index=0, seed=args.seed, n_players=state.n_players, labels=tuple(labels),
        winner_label=labels[record.winner] if record.winner is not None else None,
        turns=state.turn, n_suggestions=len(state.suggestion_log),
        n_accusations=len(state.accusation_log),
        hit_cap=record.winner is None and any(state.active),
    )
    store.put_run(run_id, {
        "run_id": run_id, "kind": "play", "n_games": 1, "seed": args.seed,
        "roster": list(labels), "player_counts": [state.n_players], "max_turns": args.max_turns,
        "profiles": {s.label: s.profile for s in seats if s.profile is not None},
        "llm": llm, "per_player": {}, "games": [summary.to_dict()],
        "mean_turns": float(state.turn), "decided_rate": 0.0 if record.winner is None else 1.0,
        "seconds": 0.0,
    })
    print(f"\nrecord: run {run_id} game 0 in {store.describe()}")
    return record


def _update_logbooks(args, record: GameRecord, labels: list, players: dict, llm_seats: dict) -> None:
    """After a `play` game with ``--logbook``: fold the record into every
    character's method memory and have each LLM seat write its entry,
    unless read-only."""
    logbook_store = _logbook_store(args)
    if logbook_store is None:
        return
    if getattr(args, "logbook_readonly", False):
        print(f"logbooks: read-only, nothing written to {logbook_store.describe()}")
        return
    updated = [
        label for seat, label in enumerate(labels)
        if _has_logbook(args, label)
        and method_memory.update(Logbook(logbook_store, label), record, players[seat])
    ]
    print(f"logbooks: method memory updated for {', '.join(updated) or 'nobody'} in {logbook_store.describe()}")
    for seat, wrapper in sorted(llm_seats.items()):
        if not _has_logbook(args, labels[seat]):
            continue
        entry = wrapper.debrief(record, seat)
        if entry is not None:
            print(f"  {labels[seat]} wrote entry #{entry.serial:04d}: {entry.title or '(untitled)'}")
        else:
            reason = wrapper.last_debrief.get("fallback", "unknown")
            print(f"  {labels[seat]} wrote no entry ({reason})")


def _parse_agent_names(raw: str) -> list:
    """Comma-separated suspect names -> validated list; empty means all six."""
    available = [spec.name for spec in list_agent_specs()]
    if not raw.strip():
        return available
    names = [part.strip() for part in raw.split(",") if part.strip()]
    unknown = [name for name in names if name not in available]
    if unknown:
        raise SystemExit(
            f"Unknown agent(s): {', '.join(unknown)}. Run `agents` to list the registered names."
        )
    return names


def _build_characters(names: list, seed: int) -> dict:
    """Preset characters by name, each reset with `seed`. A `Character`
    exposes `select_action`, so the trace can query it like an agent and
    still read its accusation test."""
    characters = {}
    for name in names:
        character = build_character(name)
        character.reset(seed)
        characters[name] = character
    return characters


def _parse_dial_settings(items) -> dict:
    """``Label.dial=value`` strings -> ``{label: Profile}`` overrides,
    starting from each character's preset."""
    profiles: dict = {}
    for item in items or []:
        try:
            target, value = item.split("=", 1)
            label, dial = target.split(".", 1)
            profiles[label] = profiles.get(label, preset(label)).with_dials(**{dial: float(value)})
        except (ValueError, KeyError) as exc:
            raise SystemExit(
                f"bad --set {item!r} ({exc}); expected Label.dial=value with a dial in {DIALS}"
            ) from exc
    return profiles


def _print_hands(state, labels=None) -> None:
    print("\ndealt hands (omniscient, never visible to an agent):")
    for p in range(state.n_players):
        print(f"  {_player_label(state, p, labels)}: {', '.join(sorted(state.hands[p]))}")


def _print_seats(state, labels) -> None:
    print("seats: " + ", ".join(_player_label(state, p, labels) for p in range(state.n_players)))


def _write_json(path_text: str, data: dict) -> None:
    path = Path(path_text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"\nSaved: {path}")


# ---------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------


def cmd_agents(args) -> int:
    """Print the registered suspect agents, their methods, and their
    preset personality dials."""
    print("Registered agents (suspect: method; preset dials):")
    for spec in list_agent_specs():
        print(f"- {spec.name}: {spec.description}")
        dials = " ".join(f"{name}={value:.2f}" for name, value in spec.profile.to_dict().items())
        confidence = "DS belief" if spec.confidence_fn is ds_belief_confidence else "probabilities"
        print(f"    {dials}  (accuses on {confidence})")
    return 0


def _event_line(event, state, labels, names) -> str:
    """One terminal line per event, or an empty string for an event
    that prints nothing (the game-over line is printed separately)."""
    if isinstance(event, RemarkEvent):
        return f'turn {event.turn}: {names[event.seat]} says: "{event.text}"'
    if isinstance(event, MoveEvent):
        tag = " (secret passage)" if event.used_secret_passage else ""
        return (
            f"turn {event.turn}: {_player_label(state, event.player, labels)} -> "
            f"{_node_label(event.destination)}{tag}"
        )
    if isinstance(event, SuggestionEvent):
        return describe_suggestion(event.suggestion, names, event.turn)
    if isinstance(event, AccusationEvent):
        a = event.accusation
        verdict = "CORRECT" if a.correct else "wrong, eliminated"
        return (
            f"turn {event.turn}: {_player_label(state, a.accuser, labels)} accuses "
            f"{a.suspect}/{a.weapon}/{a.room} -- {verdict}"
        )
    return ""


LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _read_line(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError as exc:
        raise SystemExit("stdin closed; the game is abandoned") from exc


def _pick(prompt: str, n: int, extra=()) -> "int | str":
    """A letter among the first `n`, or one of `extra` words, from stdin;
    asks again on anything else."""
    while True:
        text = _read_line(prompt).upper()
        if text.lower() in extra:
            return text.lower()
        if len(text) == 1 and text in LETTERS[:n]:
            return LETTERS.index(text)
        print(f"  type a letter A-{LETTERS[n - 1]}" + (f" or {'/'.join(extra)}" if extra else ""))


def _pick_cards(prompt: str, categories: list, extra=()) -> "list | str":
    """One letter per category on one line (``A C``), or an `extra` word."""
    while True:
        text = _read_line(prompt)
        if text.lower() in extra:
            return text.lower()
        parts = text.upper().split()
        if len(parts) == len(categories) and all(
            len(part) == 1 and part in LETTERS[: len(cat)] for part, cat in zip(parts, categories)
        ):
            return [cat[LETTERS.index(part)] for part, cat in zip(parts, categories)]
        print("  type one letter per list, e.g. " + " ".join("A" for _ in categories)
              + (f", or {'/'.join(extra)}" if extra else ""))


def _lettered(items, text=lambda item: item) -> None:
    for letter, item in zip(LETTERS, items):
        print(f"  {letter}. {text(item)}")


def _option_text(option: dict) -> str:
    if option["move"] == "stay":
        return "stay where you are"
    if option["move"] == "secret_passage":
        return f"take the secret passage to the {option['to']}"
    node = option["to"]
    if isinstance(node, str):
        return f"enter the {node}"
    return f"corridor square row {node['row']}, column {node['col']}"


def _answer_from_terminal(game: TableGame, names: list) -> None:
    """Put the pending decision to the person at the keyboard and send
    their answer in. ``?`` prints the floor's grid for that seat."""
    request = game.pending
    obs = request.obs
    me = names[request.seat]
    print(f"\n-- {me}, your hand: {', '.join(sorted(obs.own_hand))}  (type ? for your notes)")
    while True:
        if request.kind == "movement":
            options = describe_request(request)["options"]
            print("Where to?")
            _lettered(options, _option_text)
            pick = _pick("move> ", len(options), extra=("?",))
            if pick == "?":
                print(format_mask(obs.mask, obs.n_players))
                continue
            data = options[pick]
        elif request.kind == "suggestion":
            print(f"You are in the {request.room}. Suggest a suspect and a weapon (two letters), or 'pass'.")
            print("Suspects:"); _lettered(SUSPECTS)
            print("Weapons:"); _lettered(WEAPONS)
            pick = _pick_cards("suggest> ", [SUSPECTS, WEAPONS], extra=("pass", "?"))
            if pick == "?":
                print(format_mask(obs.mask, obs.n_players))
                continue
            data = None if pick == "pass" else {"suspect": pick[0], "weapon": pick[1]}
        elif request.kind == "accusation":
            print("Accuse? Three letters (suspect, weapon, room), or 'pass'. A wrong accusation puts you out.")
            print("Suspects:"); _lettered(SUSPECTS)
            print("Weapons:"); _lettered(WEAPONS)
            print("Rooms:"); _lettered(ROOMS)
            pick = _pick_cards("accuse> ", [SUSPECTS, WEAPONS, ROOMS], extra=("pass", "?"))
            if pick == "?":
                print(format_mask(obs.mask, obs.n_players))
                continue
            if pick == "pass":
                data = None
            else:
                if _read_line(f"Accuse {pick[0]} with the {pick[1]} in the {pick[2]}? Type YES to confirm: ") != "YES":
                    continue
                data = {"suspect": pick[0], "weapon": pick[1], "room": pick[2]}
        else:
            print(f"{names[request.shown_to]} named cards you hold. Which do you show?")
            _lettered(request.candidates)
            pick = _pick("show> ", len(request.candidates), extra=("?",))
            if pick == "?":
                print(format_mask(obs.mask, obs.n_players))
                continue
            data = {"card": request.candidates[pick]}
        try:
            game.answer(request.seat, game.seq, data)
        except TableError as exc:
            print(f"  {exc}")
            continue
        return


def _for_viewer(event, my_seats: set):
    """The event as the people at the keyboard may see it: a card shown
    between two other seats is hidden, as `ClueObservation.for_player`
    hides it."""
    if isinstance(event, SuggestionEvent):
        s = event.suggestion
        if s.card_shown is not None and s.suggester not in my_seats and s.refuter not in my_seats:
            return dataclasses.replace(event, suggestion=dataclasses.replace(s, card_shown=None))
    return event


def _play_human(args) -> int:
    """A person at the table from the terminal (Phase 8.2): the driver the
    web app uses, with each decision put to the keyboard and the rest of
    the table headless. No record, model or logbook yet."""
    if getattr(args, "llm", False) or getattr(args, "store", "") or getattr(args, "logbook", None) is not None:
        raise SystemExit("--human plays a plain table: --llm, --store and --logbook are not combined with it yet")
    tokens = [t.strip() for t in args.human.split(",") if t.strip()]
    base = (args.name or getpass.getuser()).strip().lower() or "you"
    humans = {token: (base if i == 0 else f"{base}-{i + 1}") for i, token in enumerate(tokens)}
    roster = args.roster.strip()
    n_bots = args.players - len(tokens)
    entries = [roster] * n_bots if roster in BOT_LABELS else roster.split(",")
    try:
        setup = TableSetup.from_roster(entries, args.players, args.seed, humans=humans, max_turns=args.max_turns)
        game = TableGame(setup)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    names = seat_labels(game.suspects, game.labels)
    my_seats = set(game.external)
    print(f"seed={args.seed} players={args.players} roster={args.roster} you={','.join(humans.values())}")
    _print_seats(game.state, game.labels)
    print()
    shown = 0
    while not game.finished:
        if game.pending is None:
            game.run(1)
        else:
            _answer_from_terminal(game, names)
        for event in game.events[shown:]:
            line = _event_line(_for_viewer(event, my_seats), game.state, game.labels, names)
            if line:
                print(line)
        shown = len(game.events)
    state = game.state
    final = game.events[-1]
    print(f"\nEnvelope: {'/'.join(final.solution)}")
    print(
        f"Turns played: {state.turn}; suggestions: {len(state.suggestion_log)}; "
        f"accusations: {len(state.accusation_log)}"
    )
    if final.winner is not None:
        print(f"Winner: {_player_label(state, final.winner, game.labels)}")
    elif not any(state.active):
        print("No winner -- every player accused incorrectly.")
    else:
        print(f"No winner -- hit the {args.max_turns}-turn cap.")
    return 0


def cmd_play(args) -> int:
    """Play one game and print the outcome (and event log); with
    ``--human`` a person plays a seat from the keyboard."""
    if getattr(args, "human", ""):
        return _play_human(args)
    llm_seats: dict = {}
    players: dict = {}
    state, events, labels = _play_game(args, llm_seats, players)
    print(f"seed={args.seed} players={args.players} roster={args.roster}")
    _print_seats(state, labels)
    if args.verbose:
        print()
        names = seat_labels(state.suspects_in_play, labels)
        for event in events:
            line = _event_line(event, state, labels, names)
            if line:
                print(line)
    final = events[-1]
    assert isinstance(final, GameOverEvent)
    print(f"\nEnvelope: {'/'.join(final.solution)}")
    print(
        f"Turns played: {state.turn}; suggestions: {len(state.suggestion_log)}; "
        f"accusations: {len(state.accusation_log)}"
    )
    if final.winner is not None:
        print(f"Winner: {_player_label(state, final.winner, labels)}")
    elif not any(state.active):
        print("No winner -- every player accused incorrectly.")
    else:
        print(f"No winner -- hit the {args.max_turns}-turn cap.")
    if args.hands:
        _print_hands(state, labels)
    if getattr(args, "store", "") or getattr(args, "logbook", None) is not None:
        record = _play_record(args, state, events, labels, players, llm_seats)
        _update_logbooks(args, record, labels, players, llm_seats)
    if llm_seats:
        print("\nLLM seats:")
        for seat, wrapper in sorted(llm_seats.items()):
            s = wrapper.summary()
            print(
                f"  {_player_label(state, seat, labels)}: {s['decisions']} decisions, "
                f"{s['llm_calls']} calls, {s['fallbacks']} fallbacks, {s['deviations']} deviations, "
                f"{s['remarks']} remarks; tokens in/out/cached "
                f"{s['input_tokens']}/{s['output_tokens']}/{s['cached_tokens']}; "
                f"{s['llm_seconds']:.1f}s; backend {s['backend']}, model {s['model']}"
            )
        totals = [wrapper.summary() for wrapper in llm_seats.values()]
        cost = estimate_cost(
            args.llm_model,
            sum(s["input_tokens"] for s in totals),
            sum(s["output_tokens"] for s in totals),
            sum(s["cached_tokens"] for s in totals),
        )
        if cost is not None:
            print(f"  estimated cost at list prices: ${cost:.4f}")
    return 0


def cmd_prompt(args) -> int:
    """Print exactly what one seat's LLM would be sent for one decision at
    one point in a game. No call is made; positions are the game's final
    ones, so ``--decision move`` uses them with ``--roll``."""
    state, _events, labels = _play_game(args)
    if not 0 <= args.viewer < state.n_players:
        raise SystemExit(f"--viewer must be in 0..{state.n_players - 1} for {state.n_players} players")
    total = len(state.suggestion_log)
    k = total if args.at is None else args.at
    if not 0 <= k <= total:
        raise SystemExit(f"--at must be in 0..{total} (this game has {total} suggestions)")
    name = args.agent.strip() or (labels[args.viewer] if labels[args.viewer] in AGENT_SPECS else "")
    if name not in AGENT_SPECS:
        raise SystemExit(
            f"seat {args.viewer} is occupied by {labels[args.viewer]!r}; pass --agent NAME to render a "
            "character's prompt for it"
        )
    profile = preset(name).with_dials(memory=args.memory) if args.memory is not None else None
    character = build_character(name, profile)
    character.reset(args.seed)
    truncated = truncate_state(state, k)
    obs = clude_constraints.observe(truncated, args.viewer)
    if args.decision == "move":
        choices = engine.legal_moves(truncated, args.viewer, args.roll)
        menu = movement_menu(character, obs, choices)
    elif args.decision == "suggest":
        menu = suggestion_menu(character, obs)
    elif args.decision == "accuse":
        menu = accusation_menu(character, obs)
    else:
        hand = sorted(obs.own_hand)
        menu = show_menu(character, obs, hand[:2] or hand, (args.viewer + 1) % state.n_players)
    wrapper = LLMCharacter(character, NullBackend())
    if args.logbook:
        wrapper.attach_logbook(Logbook(open_store(args.logbook), name))
        wrapper.new_game(labels)
    system = wrapper.system_prompt()
    user = user_prompt(obs, character.select_action(obs), character, menu, [])
    print(f"=== system ({len(system.split())} words; persona {wrapper.persona.source}) ===")
    print(system)
    if wrapper.memory_block:
        print(
            f"=== memory ({len(wrapper.memory_block.split())} words; the logbook at memory "
            f"{character.profile.memory:.2f}, a second cached system block) ==="
        )
        print(wrapper.memory_block)
    elif args.logbook:
        print(f"=== memory: {name} has nothing to read back from {args.logbook} ===")
    print(f"=== user ({len(user.split())} words; seat P{args.viewer}, after k={k} of {total} suggestions) ===")
    print(user)
    return 0


def cmd_trace(args) -> int:
    """Replay one game from one viewer's seat, printing the floor's
    progress, each character's belief after every k-th suggestion, and
    whether it would accuse on it."""
    state, events, labels = _play_game(args)
    if not 0 <= args.viewer < state.n_players:
        raise SystemExit(f"--viewer must be in 0..{state.n_players - 1} for {state.n_players} players")
    characters = _build_characters(_parse_agent_names(args.agents), args.seed)
    suggestion_turns = [e.turn for e in events if isinstance(e, SuggestionEvent)]

    print(
        f"seed={args.seed} players={args.players} roster={args.roster} "
        f"viewer={_player_label(state, args.viewer, labels)}"
    )
    print(f"viewer's hand: {', '.join(sorted(state.hands[args.viewer]))}")
    print(f"truth (hidden from every agent): envelope = {'/'.join(state.envelope)}")
    print(
        "belief columns: S/W/R = suspect/weapon/room; Card* = proven by the floor; "
        "P(correct) = confidence in the best triple vs the character's accuse_threshold"
    )

    started = time.perf_counter()
    steps = belief_trace(state, args.viewer, characters, every=args.every)
    elapsed = time.perf_counter() - started

    width = max(len(name) for name in characters) + 2
    names = seat_labels(state.suspects_in_play, labels)
    for step in steps:
        print()
        if step.suggestion is None:
            print("--- k=0: the deal, no suggestions yet")
        else:
            print(
                f"--- k={step.k}: "
                f"{describe_suggestion(step.suggestion, names, suggestion_turns[step.k - 1])}"
            )
        mask = step.obs.mask
        solution = mask.solution()
        floor_line = f"floor: {resolved_count(step.obs)}/21 cards located"
        if solution is not None:
            floor_line += f"; envelope proven: {'/'.join(solution)}"
        elif mask.or_constraints:
            floor_line += f"; {len(mask.or_constraints)} open or-constraint(s)"
        print(floor_line)
        for name, belief in step.beliefs.items():
            line = f"{name:<{width}}{format_belief(belief.probabilities, mask, args.top, args.all_cards)}"
            extra = format_extra(belief)
            if extra:
                line += f"  {extra}"
            line += f"  {format_accusation_test(characters[name], belief)}"
            print(line)

    print(f"\n{len(steps)} steps x {len(characters)} agents in {elapsed:.1f}s")
    return 0


def cmd_floor(args) -> int:
    """Show the deduction floor: the card x holder grid for one viewer at
    one point in a game, or every viewer's convergence over the game."""
    state, _events, labels = _play_game(args)
    total = len(state.suggestion_log)

    if args.convergence:
        points = floor_convergence(state)
        head = f"{'k':>4}" + "".join(f"{'P' + str(p):>6}" for p in range(state.n_players))
        print(f"seed={args.seed} players={args.players} roster={args.roster}")
        _print_seats(state, labels)
        print(
            "cards located (of 21) per viewer after k suggestions; * = envelope proven; "
            "rows where nothing changed are skipped\n"
        )
        print(head)
        last_row = None
        for i, point in enumerate(points):
            row = tuple((point.resolved[p], point.solved[p]) for p in range(state.n_players))
            if row == last_row and i < len(points) - 1:
                continue
            last_row = row
            cells = "".join(f"{str(n) + ('*' if solved else ''):>6}" for n, solved in row)
            print(f"{point.k:>4}{cells}")
        firsts = []
        for p in range(state.n_players):
            k = next((pt.k for pt in points if pt.solved[p]), None)
            firsts.append(f"P{p}={'never' if k is None else k}")
        print(f"\nfirst k with the envelope proven: {', '.join(firsts)}")
        print(f"truth: envelope = {'/'.join(state.envelope)}")
        return 0

    if not 0 <= args.viewer < state.n_players:
        raise SystemExit(f"--viewer must be in 0..{state.n_players - 1} for {state.n_players} players")
    k = total if args.at is None else args.at
    if not 0 <= k <= total:
        raise SystemExit(f"--at must be in 0..{total} (this game has {total} suggestions)")
    obs = clude_constraints.observe(truncate_state(state, k), args.viewer)
    mask = obs.mask

    print(
        f"seed={args.seed} players={args.players} roster={args.roster} "
        f"viewer={_player_label(state, args.viewer, labels)} after k={k} of {total} suggestions"
    )
    print(f"viewer's hand: {', '.join(sorted(state.hands[args.viewer]))}\n")
    print(format_mask(mask, state.n_players))
    print("\n# = located holder, x = still possible, . = ruled out")
    if mask.or_constraints:
        print("\nopen or-constraints (holder has at least one of):")
        for cards, holder in mask.or_constraints:
            print(f"  {_player_label(state, holder, labels)}: {', '.join(sorted(cards))}")
    solution = mask.solution()
    print(
        f"\nenvelope proven: {'/'.join(solution) if solution else 'not yet'} "
        f"({resolved_count(obs)}/21 cards located)"
    )
    print(f"truth: envelope = {'/'.join(state.envelope)}")
    if args.hands:
        _print_hands(state, labels)
    return 0


def cmd_benchmark(args) -> int:
    """Run the Phase 4 belief-quality benchmark and print its table."""
    agents = {name: build_agent(name) for name in _parse_agent_names(args.agents)}
    player_counts = (args.players,) if args.players else DEFAULT_PLAYER_COUNTS
    checkpoints = tuple(args.checkpoints)

    started = time.perf_counter()
    result = run_benchmark(
        n_games=args.games,
        seed=args.seed,
        checkpoints=checkpoints,
        agents=agents,
        player_counts=player_counts,
        max_turns=args.max_turns,
        bot=args.bot,
    )
    elapsed = time.perf_counter() - started

    print(result.summary_table())
    print(
        f"\n{args.games} {args.bot}-bot games, seed {args.seed}, table sizes {list(player_counts)}, "
        f"{result.n_snapshots} snapshots, {elapsed:.1f}s"
    )
    if "Plum" in result.per_agent:
        cells = result.per_agent["Plum"].values()
        sampled = sum(c.sampled_calls for c in cells)
        calls = sum(c.n_calls for c in cells)
        print(f"Plum fell back to sampling in {sampled}/{calls} calls")
    if args.show_green and "Green" in result.agents:
        green = result.agents["Green"]
        print("\nGreen's Beta posteriors after the run:")
        print(f"  {'arm':<10}{'alpha':>8}{'beta':>8}{'mean':>8}{'evidence':>10}")
        for name, c in green.candidates.items():
            print(
                f"  {name:<10}{c.alpha:>8.2f}{c.beta:>8.2f}"
                f"{c.alpha / (c.alpha + c.beta):>8.3f}{c.alpha + c.beta - 2.0:>10.2f}"
            )
    if args.json:
        _write_json(args.json, result.to_dict())
    return 0


def cmd_train_mustard(args) -> int:
    """Train Mustard's tree with explicit hyperparameters, describe it,
    and score it on held-out self-play."""
    checkpoints = tuple(args.checkpoints)
    extra_rows: list = []
    memory_note = ""
    if getattr(args, "logbook", ""):
        document = Logbook(open_store(args.logbook), "Mustard").method()
        if document is None or document.get("kind") != "rows":
            raise SystemExit(
                f"no Mustard method memory in {args.logbook}; play with --logbook or run "
                "`logbook rebuild --identity Mustard` first"
            )
        extra_rows = method_memory.extra_rows(document)
        memory_note = (
            f", plus {len(extra_rows)} memory rows from {method_memory.n_games(document)} "
            f"stored games in {args.logbook}"
        )
    agent = DecisionTreeAgent(
        n_training_games=args.games,
        training_seed=args.seed,
        checkpoints=checkpoints,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        training_bot=args.bot,
        smoothing_m=args.smoothing_m,
        extra_rows=extra_rows,
    )
    started = time.perf_counter()
    tree = agent.tree
    elapsed = time.perf_counter() - started
    rows = training_rows(args.games, args.seed, checkpoints, args.bot)
    if not rows:
        raise SystemExit("no training rows -- every game ended before a single suggestion?")
    all_rows = rows + extra_rows
    positives = sum(label for _features, label in all_rows)
    summary = summarize_tree(tree)

    print(
        f"training set: {len(rows)} rows from {args.games} {args.bot}-bot games "
        f"(seeds {args.seed}..{args.seed + args.games - 1}) at checkpoints {list(checkpoints)}"
        f"{memory_note}"
    )
    print(
        f"  one row per (viewer, checkpoint, card the floor hadn't located); "
        f"{positives} positive = {positives / len(all_rows):.3f} (the card was the envelope's)"
    )
    cached = "" if extra_rows else " (rows and tree are cached per settings within a process)"
    print(f"trained in {elapsed:.1f}s{cached}")
    print(
        f"tree: {summary.n_nodes} nodes, {summary.n_leaves} leaves, depth {summary.depth} "
        f"(--max-depth {args.max_depth}, --min-samples-leaf {args.min_samples_leaf}, "
        f"--smoothing-m {args.smoothing_m})"
    )
    print("splits per feature:")
    for name in FEATURE_NAMES:
        print(f"  {name:<28}{summary.feature_use.get(name, 0):>4}")
    leaves = summary.leaf_predictions
    print(
        f"leaf predictions: min {leaves[0]:.3f}, median {leaves[len(leaves) // 2]:.3f}, "
        f"max {leaves[-1]:.3f}"
    )
    if args.render:
        print("\n" + render_tree(tree))

    if args.eval_games > 0:
        eval_seeds = set(range(args.eval_seed, args.eval_seed + args.eval_games))
        train_seeds = set(range(args.seed, args.seed + args.games))
        overlap = len(eval_seeds & train_seeds)
        print(
            f"\nheld-out evaluation: {args.eval_games} {args.bot}-bot games from seed {args.eval_seed}"
        )
        if overlap:
            print(f"  WARNING: {overlap} evaluation seed(s) overlap the training seeds -- not held out")
        result = run_benchmark(
            n_games=args.eval_games,
            seed=args.eval_seed,
            checkpoints=checkpoints,
            agents={"Mustard": agent},
            bot=args.bot,
        )
        print(result.summary_table())
    return 0


def cmd_snapshots(args) -> int:
    """Describe the self-play snapshot distribution Mustard trains on
    and the benchmark scores against."""
    checkpoints = tuple(args.checkpoints)
    player_counts = (args.players,) if args.players else DEFAULT_PLAYER_COUNTS
    cells: dict = defaultdict(
        lambda: {"n": 0, "k": 0, "unresolved": 0, "positives": 0, "solved": 0}
    )
    games: dict = {}  # game_index -> (n_players, max k seen)
    n_snapshots = 0

    started = time.perf_counter()
    for snap in generate_snapshots(
        args.games, args.seed, checkpoints=checkpoints,
        max_turns=args.max_turns, player_counts=player_counts, bot=args.bot,
    ):
        n_snapshots += 1
        n_players = snap.obs.n_players
        k = len(snap.obs.suggestion_log)
        unresolved = [c for c in ALL_CARDS if snap.obs.mask.holder_of(c) is None]
        cell = cells[(snap.checkpoint, n_players)]
        cell["n"] += 1
        cell["k"] += k
        cell["unresolved"] += len(unresolved)
        cell["positives"] += sum(1 for c in unresolved if c in snap.envelope)
        cell["solved"] += int(snap.obs.mask.solution() is not None)
        previous = games.get(snap.game_index, (n_players, 0))[1]
        games[snap.game_index] = (n_players, max(previous, k))
    elapsed = time.perf_counter() - started

    print(
        f"{args.games} {args.bot}-bot games, seed {args.seed}, checkpoints {list(checkpoints)}, "
        f"table sizes {list(player_counts)}: {n_snapshots} snapshots in {elapsed:.1f}s"
    )
    print("\ngames per table size, and suggestions per game at the last checkpoint:")
    for size in sorted({size for size, _k in games.values()}):
        ks = [k for s, k in games.values() if s == size]
        print(
            f"  {size} players: {len(ks)} games, suggestions min/mean/max "
            f"{min(ks)}/{sum(ks) / len(ks):.1f}/{max(ks)}"
        )

    head = (
        f"{'checkpoint':>10}{'players':>8}{'snaps':>7}{'mean_k':>8}"
        f"{'unresolved':>11}{'label_rate':>11}{'solved':>8}"
    )
    print("\n" + head)
    print("-" * len(head))
    for (checkpoint, n_players) in sorted(cells):
        c = cells[(checkpoint, n_players)]
        label_rate = c["positives"] / c["unresolved"] if c["unresolved"] else float("nan")
        print(
            f"{checkpoint:>10.2f}{n_players:>8}{c['n']:>7}{c['k'] / c['n']:>8.1f}"
            f"{c['unresolved'] / c['n']:>11.1f}{label_rate:>11.3f}{c['solved'] / c['n']:>8.2f}"
        )
    print(
        "\nunresolved = cards the floor hasn't located (Mustard's training rows are exactly "
        "these); label_rate = fraction of them that are the envelope's; solved = fraction of "
        "snapshots whose viewer already has the envelope proven"
    )
    return 0


def _print_arena_footer(result, player_counts, store) -> None:
    print(
        f"\n{result.n_games} games, seed {result.seed}, table sizes {list(player_counts)}, "
        f"{result.seconds:.1f}s; mean {result.mean_turns:.1f} turns; "
        f"{100 * result.decided_rate:.0f}% decided by a correct accusation"
    )
    print(
        "win%/wrong% = games won / games with a wrong accusation, per game, +- binomial std; "
        "1st_acc = mean turn of the first accusation; never% = games without one; "
        "leaked = distinct own cards shown; named = suggestions naming an own card"
    )
    if store is not None:
        print(f"records: run {result.run_id} in {store.describe()}")
    if result.memory:
        mode = "read-only" if result.memory.get("readonly") else "read and written"
        loaded = ", ".join(result.memory.get("loaded", [])) or "nobody"
        who = ", ".join(result.memory.get("characters", [])) or "nobody"
        print(
            f"logbooks: {result.memory['store']} ({mode}) for {who}; "
            f"memory loaded at the start for {loaded}"
        )


def cmd_arena(args) -> int:
    """Play N games among characters and bots and print per-player metrics."""
    try:
        roster = parse_roster(args.roster.split(","))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    profiles = _parse_dial_settings(args.set)
    player_counts = (args.players,) if args.players else DEFAULT_PLAYER_COUNTS
    store = open_store(args.store) if args.store else None

    try:
        result = run_arena(
            n_games=args.games,
            seed=args.seed,
            roster=roster,
            player_counts=player_counts,
            max_turns=args.max_turns,
            profiles=profiles,
            store=store,
            run_id=args.run_id,
            **_llm_kwargs(args),
            **_logbook_kwargs(args),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(result.summary_table())
    _print_arena_footer(result, player_counts, store)
    if args.llm:
        _print_llm_cost(result.per_player, args.llm_model, args.games)
    if args.json:
        _write_json(args.json, result.to_dict())
    return 0


def cmd_sweep(args) -> int:
    """Run the arena once per value of one dial and print the pooled
    metrics per value, with a monotonicity verdict."""
    try:
        roster = parse_roster(args.roster.split(","))
        characters = [c.strip() for c in args.characters.split(",") if c.strip()] or None
        player_counts = (args.players,) if args.players else DEFAULT_PLAYER_COUNTS
        store = open_store(args.store) if args.store else None
        sweep = sweep_dial(
            args.dial,
            args.values,
            n_games=args.games,
            seed=args.seed,
            roster=roster,
            characters=characters,
            player_counts=player_counts,
            max_turns=args.max_turns,
            store=store,
            run_id=args.run_id,
            logbook_store=_logbook_store(args),
            logbook_characters=_logbook_characters(args),
            **_llm_kwargs(args),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(
        f"sweep of {args.dial} on {', '.join(sweep.characters)} "
        f"(others at preset); {args.games} paired games per value, seed {args.seed}, "
        f"table sizes {list(player_counts)}\n"
    )
    print(sweep.summary_table())
    total = sum(r.seconds for r in sweep.results)
    print(f"\n{len(sweep.values)} values x {args.games} games in {total:.1f}s")
    if store is not None:
        print(f"records: runs {sweep.results[0].run_id} .. {sweep.results[-1].run_id} in {store.describe()}")
    if args.llm:
        pooled = {row.value: row.stats for row in sweep.rows}
        _print_llm_cost(pooled, args.llm_model, args.games * len(sweep.values))
    if args.json:
        _write_json(args.json, sweep.to_dict())
    return 0


def cmd_store_copy(args) -> int:
    """Mirror a store's grid-era runs, their traces and the logbooks into
    another (`clude_storage.mirror`); how the cloud store is filled."""
    if not args.to:
        print("store copy needs --to URI", file=sys.stderr)
        return 2
    source, dest = open_store(args.uri), open_store(args.to)
    if source.describe() == dest.describe():
        print("store copy: --uri and --to are the same store", file=sys.stderr)
        return 2
    plan = plan_mirror(source, min_version=args.min_version)
    n_games = sum(1 for key in plan.keys if key.startswith("games/"))
    n_traces = sum(1 for key in plan.keys if key.startswith(f"{TRACE_PREFIX}/"))
    n_logbook = sum(1 for key in plan.keys if key.startswith(f"{LOGBOOK_PREFIX}/"))
    print(f"from: {source.describe()}")
    print(f"to:   {dest.describe()}")
    print(
        f"{len(plan.runs)} runs ({n_games} game records, {n_traces} traces), "
        f"{n_logbook} logbook documents: {len(plan.keys)} documents"
    )
    if plan.skipped_runs:
        print(
            f"left behind, a record older than version {args.min_version}: "
            f"{len(plan.skipped_runs)} runs ({', '.join(plan.skipped_runs)})"
        )
    if args.dry_run:
        print("dry run: nothing copied")
        return 0
    start = time.perf_counter()
    copied = copy_docs(source, dest, plan.keys, workers=args.workers)
    print(f"copied {copied} documents in {time.perf_counter() - start:.1f}s")
    return 0


def cmd_store(args) -> int:
    """List the runs in a record store, print one run's summary, or copy
    it into another (`cmd_store_copy`)."""
    if getattr(args, "action", "list") == "copy":
        return cmd_store_copy(args)
    store = open_store(args.uri)
    print(f"store: {store.describe()}")
    if args.run:
        summary = store.get_run(args.run)
        print(
            f"run {args.run}: {summary['n_games']} games, seed {summary['seed']}, "
            f"roster {', '.join(summary['roster'])}, {len(store.list_games(args.run))} records"
        )
        head = f"{'player':<10}{'games':>6}{'win%':>7}{'wrong%':>8}{'leaked':>8}{'named':>7}"
        print(head)
        print("-" * len(head))
        for label, stats in summary["per_player"].items():
            print(
                f"{label:<10}{stats['games']:>6}{100 * stats['win_rate']:>7.1f}"
                f"{100 * stats['wrong_accusation_rate']:>8.1f}{stats['mean_cards_leaked']:>8.2f}"
                f"{stats['mean_own_cards_named']:>7.2f}"
            )
        return 0
    runs = store.list_runs()
    if not runs:
        print("no runs stored")
        return 0
    for run_id in runs:
        print(f"  {run_id}: {len(store.list_games(run_id))} game records")
    return 0


def _tally_line(head) -> str:
    t = head.tally
    return (
        f"{t.get('games', 0)} games: won {t.get('won', 0)}, "
        f"{t.get('wrong_accusations', 0)} wrong accusations, never accused in {t.get('never_accused', 0)}"
    )


def cmd_logbook_list(args) -> int:
    """List every logbook in a store with its tally."""
    store = open_store(args.uri)
    print(f"store: {store.describe()}")
    identities = list_logbooks(store)
    if not identities:
        print("no logbooks")
        return 0
    for identity in identities:
        logbook = Logbook(store, identity)
        head = logbook.head()
        n_entries = len(logbook.serials())
        print(
            f"  {identity}: {n_entries} entries; {_tally_line(head)}; "
            f"{len(head.dossiers)} dossiers; {len(head.flags)} flags; "
            f"{method_memory.describe_memory(logbook.method())}"
        )
    return 0


def cmd_logbook_show(args) -> int:
    """Show one logbook: its head and index, one entry, or the memory
    block a character would read at a given depth."""
    store = open_store(args.uri)
    logbook = Logbook(store, args.identity)
    if not logbook.exists():
        print(f"no logbook for {args.identity} in {store.describe()}")
        return 0
    if args.entry is not None:
        try:
            entry = logbook.entry(args.entry)
        except KeyError:
            raise SystemExit(f"{args.identity} has no entry #{args.entry}")
        print(json.dumps(entry.to_dict(), indent=2) if args.raw else render_entry(entry, full=True))
        return 0
    if args.memory is not None:
        try:
            text = logbook.memory(args.memory)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print(text if text else f"(empty: {args.identity} has nothing to read back)")
        return 0
    head = logbook.head()
    if args.raw:
        print(json.dumps(head.to_dict(), indent=2))
        return 0
    print(f"logbook: {args.identity} in {store.describe()}")
    print(f"head: serial {head.serial}; {_tally_line(head)}")
    text = logbook.memory(0.0)
    if text:
        print(text.rstrip())
    entries = logbook.entries()
    if entries:
        print(f"entries ({len(entries)}):")
        for entry in entries:
            title = f" {entry.title}" if entry.title else ""
            print(f"  #{entry.serial:04d} {entry.date} {entry.game_id}:{title}")
    print(f"method memory: {method_memory.describe_memory(logbook.method())}")
    return 0


def cmd_logbook_reset(args) -> int:
    """Forget a logbook: head and method memory, and the entries too
    unless --keep-entries."""
    store = open_store(args.uri)
    logbook = Logbook(store, args.identity)
    removed = logbook.reset(keep_entries=args.keep_entries)
    kept = " (entries kept)" if args.keep_entries else ""
    print(f"reset {args.identity} in {store.describe()}: {removed} documents removed{kept}")
    return 0


def cmd_logbook_rebuild(args) -> int:
    """Recompute a logbook's head from its entries and its method memory
    from every game record in a store."""
    store = open_store(args.uri)
    source = open_store(args.from_uri) if args.from_uri else store
    logbook = Logbook(store, args.identity)
    head = logbook.rebuild_head()
    print(f"head: rebuilt from {len(logbook.serials())} entries (serial {head.serial}; {_tally_line(head)})")
    kind = method_memory.kind_for(args.identity)
    if kind is None:
        print(f"method memory: {args.identity}'s method is memoryless; nothing to rebuild")
    elif kind == "state":
        print("method memory: Green's posteriors are accumulated live; records cannot rebuild them")
    else:
        absorbed, skipped = method_memory.rebuild(logbook, source, kind, min_version=args.min_version)
        older = f" ({skipped} older than version {args.min_version} skipped)" if skipped else ""
        print(
            f"method memory: rebuilt from {absorbed} game records in {source.describe()}{older}: "
            f"{method_memory.describe_memory(logbook.method())}"
        )
    return 0


# ---------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------


def _add_bot_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--bot", choices=BOT_KINDS, default=DEFAULT_BOT,
        help="Self-play regime: 'floor' (FloorBots, games end by deduction) or 'random'.",
    )


def _add_arena_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--games", type=int, default=ARENA_N_GAMES)
    parser.add_argument("--seed", type=int, default=ARENA_SEED)
    parser.add_argument(
        "--roster", default=",".join(DEFAULT_ROSTER),
        help="Comma-separated suspect names and/or 'floor'/'random' bot seats.",
    )
    parser.add_argument(
        "--players", type=int, default=None,
        help="Fix the table size instead of cycling 3..6 across games.",
    )
    parser.add_argument("--max-turns", type=int, default=ARENA_MAX_TURNS)
    parser.add_argument(
        "--store", default="",
        help="Save every game record and the run summary here: a directory or gs://bucket/prefix.",
    )
    parser.add_argument("--run-id", default=None, help="Run id for the store (default derived).")
    parser.add_argument("--json", default="", help="Also write the result to this JSON path.")


def cmd_tables_list(args) -> int:
    """Every table in the lobby of a store: id, status, turns, seats."""
    from clude_web.tables import TableRegistry

    store = open_store(args.uri)
    print(f"store: {store.describe()}")
    documents = TableRegistry(store).in_progress()
    if not documents:
        print("no tables in progress")
        return 0
    for document in documents:
        seats = ", ".join(
            f"{s['token']} ({s['label'] or s['kind']})" for s in document["setup"]["seats"]
        )
        print(
            f"  {document['id']}  {document.get('status', 'playing'):<8} turn {document.get('turns', 0):<3} "
            f"started by {document.get('started_by') or '?'}  {seats}"
        )
    return 0


def cmd_tables_abandon(args) -> int:
    """End a table for good, from outside the app: it leaves the lobby
    and is never recorded. The maintainer's way to kill a stuck table
    (David, 2026-09-21); in the app, anyone seated or whoever started
    it has an "End table" button."""
    from clude_training.table import TableError
    from clude_web.tables import TableRegistry

    store = open_store(args.uri)
    try:
        document = TableRegistry(store).abandon(args.table_id)
    except TableError as exc:
        print(f"cannot end {args.table_id}: {exc}")
        return 1
    print(f"ended table {document['id']} (was at turn {document.get('turns', 0)})")
    return 0


def cmd_tables_costs(args) -> int:
    """What each finished web game with model seats cost (Phase 9g), and
    for one recorded before costs were, the cost filled in from the
    daily spend ledgers: into its record, the web run's line for it
    (the lobby's list of games) and its table document. Prints what it
    would do unless `--write`. A game still writing its logbook entries
    is left for the app to settle when the last one is in."""
    from clude_web.tables import TABLES_PREFIX, TableRegistry

    store = open_store(args.uri)
    print(f"store: {store.describe()}")
    registry = TableRegistry(store)
    found = 0
    for table_id in store.list_docs(TABLES_PREFIX):
        row = registry.backfill_cost(table_id, write=args.write)
        if row is None:
            continue
        found += 1
        split = "by seat" if row["seats"] else "no split by seat"
        state = {
            "recorded": "already recorded",
            "writing": "still writing its logbook entries; left alone",
            "missing": "not recorded; --write records it",
            "written": "recorded now",
        }[row["state"]]
        print(f"  {row['table']}  {row['record']:<12} ${row['total']:.4f}  ({split})  {state}")
    if not found:
        print("no finished web games with model seats")
    return 0


def cmd_users_add(args) -> int:
    """Create an app account (Phase 8.1; docs/phase8.1-plan.md 3.4).

    No prompt: the password defaults to `users.DEFAULT_PASSWORD` unless
    one is given, and it is printed so it can be passed on (David,
    2026-09-17 -- convenience over secrecy for this project).
    """
    from clude_web import users as web_users

    store = open_store(args.uri)
    password = args.password or web_users.DEFAULT_PASSWORD
    document = web_users.add_user(store, args.name, password)
    print(f"store: {store.describe()}")
    print(f"added {document['name']} (key {document['key']})")
    print(f"password: {password}")
    print("They are offered a change once, after their first login.")
    return 0


def cmd_users_list(args) -> int:
    """Every account in a store, with no hash printed."""
    from clude_web import users as web_users

    store = open_store(args.uri)
    print(f"store: {store.describe()}")
    accounts = web_users.list_users(store)
    if not accounts:
        print("no users")
        return 0
    for document in accounts:
        print(f"  {document['name']:<20} created {document.get('created', '?')}")
    return 0


def cmd_users_passwd(args) -> int:
    """Replace an account's password.

    Once a player has answered the one-time offer in the app, this is the
    only way their password changes -- by asking David.
    """
    from clude_web import users as web_users

    store = open_store(args.uri)
    password = args.password or input(f"new password for {args.name}: ")
    web_users.set_password(store, args.name, password)
    print(f"password for {args.name} is now: {password}")
    return 0


def cmd_users_remove(args) -> int:
    """Delete an account. Its records and logbook are left alone."""
    from clude_web import users as web_users

    store = open_store(args.uri)
    if not web_users.remove_user(store, args.name):
        print(f"no such user: {args.name}")
        return 1
    print(f"removed {args.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level parser and its subcommand tree."""
    parser = argparse.ArgumentParser(
        description="clude maintainer CLI: play, trace, inspect, benchmark, train, arena.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    agents_p = sub.add_parser("agents", help="List the six registered agents and their presets.")
    agents_p.set_defaults(fn=cmd_agents)

    play_p = sub.add_parser(
        "play", help="Play one game; --verbose prints the event log.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _add_game_args(play_p)
    play_p.add_argument("--verbose", action="store_true", help="Print every move/suggestion/accusation.")
    play_p.add_argument("--hands", action="store_true", help="Also print the dealt hands.")
    play_p.add_argument(
        "--human", default="",
        help="Play a seat yourself from the keyboard: the token to take (e.g. Scarlett), or several "
        "comma-separated for a hot-seat game. The roster fills the other seats (Phase 8.2).",
    )
    play_p.add_argument(
        "--name", default="",
        help="Your name for --human, the label the game records you under (default: your login name).",
    )
    play_p.add_argument(
        "--store", default="",
        help="Save the game record here (a directory or gs://bucket/prefix) as game 0 of a run.",
    )
    play_p.add_argument(
        "--run-id", default=None, help="Run id for --store (default play-<seed>-<timestamp>).",
    )
    _add_llm_args(play_p)
    _add_logbook_args(play_p)
    play_p.set_defaults(fn=cmd_play)

    prompt_p = sub.add_parser(
        "prompt", help="Print the LLM prompt one seat would be sent for one decision; no call is made.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _add_game_args(prompt_p)
    prompt_p.add_argument("--viewer", type=int, default=0, help="Whose seat to render.")
    prompt_p.add_argument(
        "--at", type=int, default=None,
        help="After this many suggestions (default: the whole game).",
    )
    prompt_p.add_argument(
        "--decision", choices=("move", "suggest", "accuse", "show"), default="suggest",
        help="Which of the four decisions to render the menu for.",
    )
    prompt_p.add_argument(
        "--agent", default="",
        help="Character to render for the seat (default: its roster occupant).",
    )
    prompt_p.add_argument("--roll", type=int, default=6, help="Die roll for --decision move.")
    prompt_p.add_argument(
        "--logbook", default=None, metavar="URI",
        help="Also render the character's memory block from its logbook in this store (Phase 7).",
    )
    prompt_p.add_argument(
        "--memory", type=float, default=None,
        help="Override the character's `memory` dial for the block (0..1; default its preset).",
    )
    prompt_p.set_defaults(fn=cmd_prompt)

    trace_p = sub.add_parser(
        "trace", help="Replay one game's belief trace from one viewer's seat.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _add_game_args(trace_p)
    trace_p.add_argument("--viewer", type=int, default=0, help="Whose seat to replay from.")
    trace_p.add_argument(
        "--agents", default="",
        help="Comma-separated suspect names to query (default: all six).",
    )
    trace_p.add_argument(
        "--every", type=int, default=1,
        help="Print after every N-th suggestion (k=0 and the end are always printed).",
    )
    trace_p.add_argument("--top", type=int, default=3, help="Cards to show per category.")
    trace_p.add_argument(
        "--all-cards", action="store_true", help="Show every still-possible card, not just --top.",
    )
    trace_p.set_defaults(fn=cmd_trace)

    floor_p = sub.add_parser(
        "floor", help="Show the deduction floor for one viewer, or its convergence for all.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _add_game_args(floor_p)
    floor_p.add_argument("--viewer", type=int, default=0, help="Whose perspective to show.")
    floor_p.add_argument(
        "--at", type=int, default=None,
        help="Show the floor after this many suggestions (default: the whole game).",
    )
    floor_p.add_argument(
        "--convergence", action="store_true",
        help="Instead of one grid, print every viewer's located-card count after each suggestion.",
    )
    floor_p.add_argument("--hands", action="store_true", help="Also print the dealt hands.")
    floor_p.set_defaults(fn=cmd_floor)

    bench_p = sub.add_parser(
        "benchmark", help="Score every agent's belief quality on shared self-play snapshots.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    bench_p.add_argument("--games", type=int, default=DEFAULT_N_GAMES)
    bench_p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    bench_p.add_argument(
        "--checkpoints", type=float, nargs="+", default=list(DEFAULT_CHECKPOINTS),
        help="Fractions of each game's suggestions to snapshot at.",
    )
    bench_p.add_argument(
        "--agents", default="", help="Comma-separated suspect names (default: all six).",
    )
    bench_p.add_argument(
        "--players", type=int, default=None,
        help="Fix the table size instead of cycling 3..6 across games.",
    )
    bench_p.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
    _add_bot_arg(bench_p)
    bench_p.add_argument(
        "--show-green", action="store_true", help="Print Green's per-arm Beta posteriors after the run.",
    )
    bench_p.add_argument("--json", default="", help="Also write the full result to this JSON path.")
    bench_p.set_defaults(fn=cmd_benchmark)

    mustard_p = sub.add_parser(
        "train-mustard", help="Train Mustard's tree with explicit hyperparameters and inspect it.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    mustard_p.add_argument("--games", type=int, default=DEFAULT_N_TRAINING_GAMES, help="Training games.")
    mustard_p.add_argument("--seed", type=int, default=DEFAULT_TRAINING_SEED, help="Training seed.")
    mustard_p.add_argument(
        "--checkpoints", type=float, nargs="+", default=list(MUSTARD_CHECKPOINTS),
        help="Snapshot fractions per training game.",
    )
    mustard_p.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    mustard_p.add_argument("--min-samples-leaf", type=int, default=DEFAULT_MIN_SAMPLES_LEAF)
    mustard_p.add_argument(
        "--smoothing-m", type=float, default=DEFAULT_SMOOTHING_M,
        help="m-estimate weight for leaf values (0 = plain means, hard zeros possible).",
    )
    mustard_p.add_argument(
        "--bot", choices=BOT_KINDS, default=DEFAULT_TRAINING_BOT,
        help="Self-play regime for training and evaluation games.",
    )
    mustard_p.add_argument("--render", action="store_true", help="Print the whole tree.")
    mustard_p.add_argument(
        "--eval-games", type=int, default=20,
        help="Held-out benchmark games to score the tree on (0 to skip).",
    )
    mustard_p.add_argument("--eval-seed", type=int, default=DEFAULT_SEED, help="Held-out seed.")
    mustard_p.add_argument(
        "--logbook", default="", metavar="URI",
        help="Also train on Mustard's method memory in this store (Phase 7), to see what it changes.",
    )
    mustard_p.set_defaults(fn=cmd_train_mustard)

    snaps_p = sub.add_parser(
        "snapshots", help="Describe the self-play snapshot distribution (Mustard's training data).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    snaps_p.add_argument("--games", type=int, default=40)
    snaps_p.add_argument("--seed", type=int, default=DEFAULT_TRAINING_SEED)
    snaps_p.add_argument(
        "--checkpoints", type=float, nargs="+", default=list(DEFAULT_CHECKPOINTS),
    )
    snaps_p.add_argument(
        "--players", type=int, default=None, help="Fix the table size instead of cycling 3..6.",
    )
    snaps_p.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
    _add_bot_arg(snaps_p)
    snaps_p.set_defaults(fn=cmd_snapshots)

    arena_p = sub.add_parser(
        "arena", help="Play N games among characters/bots and report win and accusation metrics.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _add_arena_args(arena_p)
    arena_p.add_argument(
        "--set", action="append", default=[], metavar="LABEL.DIAL=VALUE",
        help="Override one preset dial, e.g. Scarlett.accuse_threshold=0.3 (repeatable).",
    )
    _add_llm_args(arena_p)
    _add_logbook_args(arena_p)
    arena_p.set_defaults(fn=cmd_arena)

    sweep_p = sub.add_parser(
        "sweep", help="Run the arena once per value of one dial, on the same deals each time.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sweep_p.add_argument("--dial", required=True, choices=DIALS)
    sweep_p.add_argument("--values", type=float, nargs="+", required=True)
    sweep_p.add_argument(
        "--characters", default="",
        help="Comma-separated characters to set the dial on (default: every character in the roster).",
    )
    _add_arena_args(sweep_p)
    _add_llm_args(sweep_p)
    sweep_p.add_argument(
        "--logbook", nargs="?", const="", default=None, metavar="URI",
        help="Read every character's logbook from this store (default: the --store location) at "
        "every value, writing nothing, so the sweep stays paired; how the `memory` dial is swept.",
    )
    sweep_p.set_defaults(fn=cmd_sweep)

    store_p = sub.add_parser(
        "store",
        help="List the runs in a record store (a directory or gs://bucket/prefix), or copy "
        "its grid-era runs, traces and logbooks into another (`store copy --to URI`).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    store_p.add_argument(
        "action", nargs="?", choices=("list", "copy"), default="list",
        help="`list` the runs, or `copy` them into --to (docs/web.md, \"Deploying\").",
    )
    store_p.add_argument("--uri", default=DEFAULT_STORE, help="Store location (the source, for copy).")
    store_p.add_argument("--run", default="", help="Print this run's stored summary.")
    store_p.add_argument("--list", action="store_true", help="List runs (the default action).")
    store_p.add_argument("--to", default="", help="copy: the destination store.")
    store_p.add_argument(
        "--min-version", type=int, default=GRID_RECORD_VERSION,
        help="copy: take only runs whose every record is at least this version (3 = grid-era).",
    )
    store_p.add_argument(
        "--workers", type=int, default=10,
        help="copy: parallel writes (10 is the storage client's connection pool).",
    )
    store_p.add_argument("--dry-run", action="store_true", help="copy: say what would go, copy nothing.")
    store_p.set_defaults(fn=cmd_store)

    logbook_p = sub.add_parser(
        "logbook", help="List, show or reset the logbooks in a store (Phase 7).",
    )
    logbook_sub = logbook_p.add_subparsers(dest="action", required=True)
    lb_list = logbook_sub.add_parser(
        "list", help="Every logbook in the store with its tally.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    lb_list.add_argument("--uri", default=DEFAULT_STORE, help="Store location.")
    lb_list.set_defaults(fn=cmd_logbook_list)
    lb_show = logbook_sub.add_parser(
        "show", help="One logbook's head and index, one entry, or its memory block at a depth.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    lb_show.add_argument("--uri", default=DEFAULT_STORE, help="Store location.")
    lb_show.add_argument("--identity", required=True, help="Whose logbook (a roster label).")
    lb_show.add_argument("--entry", type=int, default=None, help="Print this entry by serial.")
    lb_show.add_argument(
        "--memory", type=float, default=None,
        help="Print the memory block a character with this `memory` dial would read (0..1).",
    )
    lb_show.add_argument("--raw", action="store_true", help="Print JSON instead of text.")
    lb_show.set_defaults(fn=cmd_logbook_show)
    lb_reset = logbook_sub.add_parser(
        "reset", help="Forget a logbook (the fairness control).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    lb_reset.add_argument("--uri", default=DEFAULT_STORE, help="Store location.")
    lb_reset.add_argument("--identity", required=True, help="Whose logbook to reset.")
    lb_reset.add_argument(
        "--keep-entries", action="store_true",
        help="Remove only the head and method memory; keep the entries as an archive.",
    )
    lb_reset.set_defaults(fn=cmd_logbook_reset)
    lb_rebuild = logbook_sub.add_parser(
        "rebuild", help="Recompute a logbook's head from its entries and its method memory from records.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    lb_rebuild.add_argument("--uri", default=DEFAULT_STORE, help="Store holding the logbook.")
    lb_rebuild.add_argument("--identity", required=True, help="Whose logbook to rebuild.")
    lb_rebuild.add_argument(
        "--from", dest="from_uri", default="",
        help="Store whose game records to absorb (default: the logbook's own store).",
    )
    lb_rebuild.add_argument(
        "--min-version", type=int, default=GRID_RECORD_VERSION,
        help="Skip records older than this version. 1 and 2 are ring-era, 3 the first on the Classic grid.",
    )
    lb_rebuild.set_defaults(fn=cmd_logbook_rebuild)

    tables_p = sub.add_parser(
        "tables",
        help="The web app's tables: list the lobby, end a table that should not go on, or list what games cost.",
    )
    tables_sub = tables_p.add_subparsers(dest="action", required=True)
    t_list = tables_sub.add_parser(
        "list", help="Every table in the lobby.", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    t_list.add_argument("--uri", default=WEB_STORE, help="Store location: the one the web app reads.")
    t_list.set_defaults(fn=cmd_tables_list)
    t_end = tables_sub.add_parser(
        "abandon", help="End a table for good; it leaves the lobby and is not recorded.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    t_end.add_argument("table_id", help="The table's id, as the lobby's address shows it.")
    t_end.add_argument("--uri", default=WEB_STORE, help="Store location: the one the web app reads.")
    t_end.set_defaults(fn=cmd_tables_abandon)
    t_costs = tables_sub.add_parser(
        "costs",
        help="What each finished web game with model seats cost; with --write, fill in the games "
        "recorded before costs were, from the daily spend ledgers.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    t_costs.add_argument("--uri", default=WEB_STORE, help="Store location: the one the web app reads.")
    t_costs.add_argument("--write", action="store_true", help="Record the missing costs; without it, only print.")
    t_costs.set_defaults(fn=cmd_tables_costs)

    users_p = sub.add_parser(
        "users",
        help="Manage the web app's accounts (Phase 8.1). There is no sign-up page: "
        "an account can only be made here.",
    )
    users_sub = users_p.add_subparsers(dest="action", required=True)
    for action, fn, blurb in (
        ("add", cmd_users_add, "Create an account; prompts for the password."),
        ("list", cmd_users_list, "Every account in the store."),
        ("passwd", cmd_users_passwd, "Change an account's password."),
        ("remove", cmd_users_remove, "Delete an account."),
    ):
        p = users_sub.add_parser(
            action, help=blurb, formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        p.add_argument(
            "--uri", default=WEB_STORE,
            help="Store location. Defaults to the store the web app reads, not the CLI's, "
            "so an account lands where the app will look for it.",
        )
        if action != "list":
            p.add_argument("name", help="The login name, which is also the player identity.")
        if action in {"add", "passwd"}:
            p.add_argument(
                "password", nargs="?", default="",
                help="The password, in plain sight. `add` defaults to 'password'; "
                "`passwd` asks for one if it is left off.",
            )
        p.set_defaults(fn=fn)

    return parser


def main(argv=None) -> int:
    """Parse `argv` (default: `sys.argv[1:]`) and dispatch the subcommand."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
