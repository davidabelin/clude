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
"""
from __future__ import annotations

import argparse
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
from clude_agents.personality import DIALS, preset
from clude_constraints import ENVELOPE
from clude_core import board, engine
from clude_core.bots import RandomBot
from clude_core.domain import ALL_CARDS, ROOMS, SUSPECTS, WEAPONS
from clude_core.events import AccusationEvent, GameOverEvent, MoveEvent, SuggestionEvent
from clude_core.state import ClueObservation
from clude_storage import open_store
from clude_training.arena import (
    DEFAULT_MAX_TURNS as ARENA_MAX_TURNS,
    DEFAULT_N_GAMES as ARENA_N_GAMES,
    DEFAULT_ROSTER,
    DEFAULT_SEED as ARENA_SEED,
    fill_seed,
    lineup_for_game,
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

CATEGORY_TAGS = (("S", SUSPECTS), ("W", WEAPONS), ("R", ROOMS))
DEFAULT_STORE = "data"


# ---------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------


def _player_label(state, player: int, labels=None) -> str:
    """``P2 White``, or ``P2 White (Plum)`` when a different character
    occupies the White token."""
    text = f"P{player} {state.suspects_in_play[player]}"
    if labels is not None and labels[player] != state.suspects_in_play[player]:
        text += f" ({labels[player]})"
    return text


def _node_label(node) -> str:
    """A room name, or ``Kitchen~Ballroom[2]`` for a hallway cell."""
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


def _play_game(args):
    """One finished game from the shared game args: ``(state, events,
    labels)`` where `labels` names each seat's occupant."""
    n = args.players
    roster = args.roster.strip()
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
            labels = lineup_for_game(parse_roster(roster.split(",")), 0, n)
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
        observer = clude_constraints.observe
    state, events = engine.run_game(
        n, players, seed=args.seed, max_turns=args.max_turns, observer=observer
    )
    return state, events, labels


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


def _describe_suggestion(state, suggestion, turn=None, labels=None) -> str:
    """One line for a suggestion as a given observer sees it: the card
    shown is named only if `suggestion.card_shown` was left visible."""
    who = _player_label(state, suggestion.suggester, labels)
    cards = f"{suggestion.suspect}/{suggestion.weapon}/{suggestion.room}"
    if suggestion.refuter is None:
        outcome = "nobody could refute"
    elif suggestion.card_shown is not None:
        outcome = f"{_player_label(state, suggestion.refuter, labels)} showed {suggestion.card_shown}"
    else:
        outcome = f"{_player_label(state, suggestion.refuter, labels)} showed a card (hidden)"
    prefix = f"turn {turn}: " if turn is not None else ""
    return f"{prefix}{who} suggests {cards} -- {outcome}"


def _format_belief(probabilities: dict, mask, top: int, all_cards: bool) -> str:
    """Per category: the still-possible cards by descending probability
    (top `top` unless `all_cards`), or ``Card*`` once the floor has
    proven that category."""
    parts = []
    for tag, category in CATEGORY_TAGS:
        proven = next((c for c in category if mask.holder_of(c) == ENVELOPE), None)
        if proven is not None:
            parts.append(f"{tag}: {proven}*")
            continue
        ranked = sorted(
            (c for c in category if mask.is_possible(c, ENVELOPE)),
            key=lambda c: -probabilities[c],
        )
        if not all_cards:
            ranked = ranked[:top]
        parts.append(f"{tag}: " + " ".join(f"{c} {probabilities[c]:.2f}" for c in ranked))
    return "  |  ".join(parts)


def _format_extra(belief) -> str:
    """The method-specific diagnostics an agent put in `ClueBelief.extra`,
    compactly: Plum's exact/sampled path, Green's chosen arm, Peacock's
    belief/plausibility bounds for her top card per category."""
    extra = belief.extra
    if "method" in extra:
        if extra["method"] == "exact":
            return f"[exact: {extra['completions']} deals, {extra['nodes']} nodes]"
        if extra["method"] == "sampled":
            return (
                f"[sampled: {extra['valid_samples']} valid samples, "
                f"budget hit at {extra['nodes']} nodes]"
            )
        return "[resolved]"
    if "selected_arm" in extra:
        return f"[arm: {extra['selected_arm']}]"
    if "belief" in extra and "plausibility" in extra:
        pieces = []
        for tag, category in CATEGORY_TAGS:
            top_card = max(category, key=lambda c: belief.probabilities[c])
            if top_card in extra["belief"]:
                pieces.append(
                    f"{tag} {extra['belief'][top_card]:.2f}/{extra['plausibility'][top_card]:.2f}"
                )
        return "[bel/pl of top: " + " ".join(pieces) + "]" if pieces else ""
    return ""


def _format_accusation_test(character, belief) -> str:
    """``[P(correct)=0.42 <0.90]``: the character's confidence in its
    best triple against its accusation threshold; ``>=`` means it would
    accuse here."""
    _triple, confidence = best_triple(character.confidence_fn(belief))
    threshold = character.profile.accuse_threshold
    op = ">=" if confidence >= threshold else "<"
    return f"[P(correct)={confidence:.2f} {op}{threshold:.2f}]"


def _format_mask(mask, state) -> str:
    """Card x holder grid: ``#`` located, ``x`` still possible, ``.`` ruled out."""
    holders = list(range(state.n_players)) + [ENVELOPE]
    head = f"{'card':<14}" + "".join(
        f"{('Env' if h == ENVELOPE else 'P' + str(h)):>5}" for h in holders
    )
    lines = [head]
    for _tag, category in CATEGORY_TAGS:
        for card in category:
            located = mask.holder_of(card)
            cells = []
            for h in holders:
                if located is not None:
                    cells.append("#" if h == located else ".")
                else:
                    cells.append("x" if mask.is_possible(card, h) else ".")
            lines.append(f"{card:<14}" + "".join(f"{cell:>5}" for cell in cells))
    return "\n".join(lines)


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


def cmd_play(args) -> int:
    """Play one game and print the outcome (and event log)."""
    state, events, labels = _play_game(args)
    print(f"seed={args.seed} players={args.players} roster={args.roster}")
    _print_seats(state, labels)
    if args.verbose:
        print()
        for event in events:
            if isinstance(event, MoveEvent):
                tag = " (secret passage)" if event.used_secret_passage else ""
                print(
                    f"turn {event.turn}: {_player_label(state, event.player, labels)} -> "
                    f"{_node_label(event.destination)}{tag}"
                )
            elif isinstance(event, SuggestionEvent):
                print(_describe_suggestion(state, event.suggestion, event.turn, labels))
            elif isinstance(event, AccusationEvent):
                a = event.accusation
                verdict = "CORRECT" if a.correct else "wrong, eliminated"
                print(
                    f"turn {event.turn}: {_player_label(state, a.accuser, labels)} accuses "
                    f"{a.suspect}/{a.weapon}/{a.room} -- {verdict}"
                )
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
    for step in steps:
        print()
        if step.suggestion is None:
            print("--- k=0: the deal, no suggestions yet")
        else:
            print(
                f"--- k={step.k}: "
                f"{_describe_suggestion(state, step.suggestion, suggestion_turns[step.k - 1], labels)}"
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
            line = f"{name:<{width}}{_format_belief(belief.probabilities, mask, args.top, args.all_cards)}"
            extra = _format_extra(belief)
            if extra:
                line += f"  {extra}"
            line += f"  {_format_accusation_test(characters[name], belief)}"
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
    print(_format_mask(mask, state))
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
    agent = DecisionTreeAgent(
        n_training_games=args.games,
        training_seed=args.seed,
        checkpoints=checkpoints,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        training_bot=args.bot,
        smoothing_m=args.smoothing_m,
    )
    started = time.perf_counter()
    tree = agent.tree
    elapsed = time.perf_counter() - started
    rows = training_rows(args.games, args.seed, checkpoints, args.bot)
    if not rows:
        raise SystemExit("no training rows -- every game ended before a single suggestion?")
    positives = sum(label for _features, label in rows)
    summary = summarize_tree(tree)

    print(
        f"training set: {len(rows)} rows from {args.games} {args.bot}-bot games "
        f"(seeds {args.seed}..{args.seed + args.games - 1}) at checkpoints {list(checkpoints)}"
    )
    print(
        f"  one row per (viewer, checkpoint, card the floor hadn't located); "
        f"{positives} positive = {positives / len(rows):.3f} (the card was the envelope's)"
    )
    print(f"trained in {elapsed:.1f}s (rows and tree are cached per settings within a process)")
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


def cmd_arena(args) -> int:
    """Play N games among characters and bots and print per-player metrics."""
    try:
        roster = parse_roster(args.roster.split(","))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    profiles = _parse_dial_settings(args.set)
    player_counts = (args.players,) if args.players else DEFAULT_PLAYER_COUNTS
    store = open_store(args.store) if args.store else None

    result = run_arena(
        n_games=args.games,
        seed=args.seed,
        roster=roster,
        player_counts=player_counts,
        max_turns=args.max_turns,
        profiles=profiles,
        store=store,
        run_id=args.run_id,
    )
    print(result.summary_table())
    _print_arena_footer(result, player_counts, store)
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
    if args.json:
        _write_json(args.json, sweep.to_dict())
    return 0


def cmd_store(args) -> int:
    """List the runs in a record store, or print one run's summary."""
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
    play_p.set_defaults(fn=cmd_play)

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
    sweep_p.set_defaults(fn=cmd_sweep)

    store_p = sub.add_parser(
        "store", help="List the runs in a record store (a directory or gs://bucket/prefix).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    store_p.add_argument("--uri", default=DEFAULT_STORE, help="Store location.")
    store_p.add_argument("--run", default="", help="Print this run's stored summary.")
    store_p.add_argument("--list", action="store_true", help="List runs (the default action).")
    store_p.set_defaults(fn=cmd_store)

    return parser


def main(argv=None) -> int:
    """Parse `argv` (default: `sys.argv[1:]`) and dispatch the subcommand."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
