"""The board drawing and the replay data behind the scrubber (step 3).

Both are pure: no Flask, no network. The board is generated from
`clude_core.board`, so these tests are really asking whether the drawing
still agrees with the board the engine plays -- the drift worth catching,
since a replay showing a token somewhere the rules forbid is worse than
no picture.
"""
from __future__ import annotations

import re

import pytest
import xml.etree.ElementTree as ET
from pathlib import Path

import clude_constraints
from clude_agents import build_character
from clude_constraints import FloorBot
from clude_constraints.propagator import ENVELOPE
from clude_core import board, engine
from clude_core.board import Square
from clude_core.domain import ALL_CARDS
from clude_storage import GameRecord, LocalStore, SeatRecord
from clude_web import board_svg, replay_data


def record_of(state, events, labels, kind, run_id="screen-test", index=0, seed=5):
    return GameRecord.from_game(
        run_id=run_id,
        game_index=index,
        seed=seed,
        state=state,
        events=events,
        seats=[
            SeatRecord(
                seat=p,
                suspect=state.suspects_in_play[p],
                label=labels[p],
                kind=kind,
            )
            for p in range(state.n_players)
        ],
    )


def play(n_players=3, seed=5, max_turns=40):
    """A short real game, recorded exactly as the arena records one."""
    bots = {p: FloorBot() for p in range(n_players)}
    state, events = engine.run_game(
        n_players, bots, seed=seed, max_turns=max_turns,
        observer=clude_constraints.observe,
    )
    return record_of(state, events, ["floor"] * n_players, "floor", seed=seed)


# --- the board --------------------------------------------------------


def test_the_board_draws_every_room_door_and_start_square():
    svg = board_svg.board_svg()

    assert svg.count('class="board-room"') == 9
    assert svg.count('class="board-door"') == 17
    assert svg.count('class="board-start') == 6
    for room in board.ROOM_CELLS:
        assert f'data-room="{room}"' in svg


def test_the_board_covers_the_whole_grid():
    """Every walkable cell is drawn, and a void rect sits behind the lot
    so the cells nobody can stand on read as off-board rather than as the
    page showing through."""
    svg = board_svg.board_svg()
    width = board.N_COLS * board_svg.CELL
    height = board.N_ROWS * board_svg.CELL
    cells = (
        len(board.CORRIDOR)
        + len(board.CELLAR)
        + sum(len(room) for room in board.ROOM_CELLS.values())
    )

    assert f'viewBox="0 0 {width} {height}"' in svg
    assert f'class="board-void" x="0" y="0" width="{width}" height="{height}"' in svg
    # every cell, the void behind them, and a start marker per suspect
    assert svg.count("<rect") == cells + 1 + len(board.START_SQUARES)


def test_a_room_centre_lands_inside_that_room():
    """The label and every token in a room are placed at this point, so
    it had better be in the room."""
    for room, cells in board.ROOM_CELLS.items():
        x, y = board_svg.room_centre(room)
        cell = Square(int(y // board_svg.CELL), int(x // board_svg.CELL))
        assert cell in cells, f"{room}'s centre fell outside it"


def test_tokens_are_drawn_where_they_stand():
    svg = board_svg.board_svg({"Scarlett": "Kitchen", "Plum": Square(7, 4)})

    assert svg.count('class="board-token') == 2
    assert 'data-suspect="Scarlett"' in svg
    x, y = board_svg.node_centre(Square(7, 4))
    assert f'cx="{x}" cy="{y}"' in svg


def test_tokens_sharing_a_room_do_not_sit_on_top_of_each_other():
    crowded = board_svg.board_svg({s: "Hall" for s in ["Scarlett", "Plum", "Green"]})
    centres = {
        line.split('cx="')[1].split('"')[0]
        for line in crowded.splitlines()
        if 'class="board-token' in line
    }

    assert len(centres) == 3, "three tokens in one room drew at one point"


def test_a_doorway_is_a_door_and_not_a_wall():
    """Every door leaves a gap in its room's outline, or a token would
    appear to walk through a wall."""
    svg = board_svg.board_svg()
    walls = {line for line in svg.splitlines() if 'class="board-wall"' in line}

    for room, cell, square in board.DOORS:
        assert f'class="board-door" data-room="{room}" ' in svg
        threshold = board_svg._door_marker(room, cell, square)
        coords = threshold.split("x1=")[1]
        assert not any(
            wall.split("x1=")[1] == coords for wall in walls
        ), f"{room}'s doorway was also walled off"


def test_the_drawing_escapes_what_it_is_given():
    svg = board_svg.board_svg(title='<script>"x"')

    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg


def test_the_board_is_well_formed_xml():
    """It is pasted into a page as raw markup, so a stray quote would
    break the whole document rather than one shape."""
    root = ET.fromstring(board_svg.board_svg({"Plum": "Hall"}))

    assert root.tag.endswith("svg")


def test_a_dressed_board_adds_shapes_and_still_no_paint():
    """Phase 10f (plan 8). Dressed, the board gains a floor pattern per
    room (nine, none alike, since 2026-10-01), a brass line inside every
    wall, every door a closed leaf that can swing (2026-10-01; a brass
    bar and two rivets before), a secret passage's marker, an initial on every token where the token
    stands, and the logo in the cellar in place of the wordmark -- every
    shape classed, none coloured, the whole still well-formed."""
    tokens = {"Scarlett": "Hall", "Plum": Square(7, 4), "Peacock": "Hall"}
    plain = board_svg.board_svg(tokens)
    dressed = board_svg.board_svg(tokens, dressed=True)
    ET.fromstring(dressed)

    patterns = re.findall(r'<pattern id="([^"]+)".*?</pattern>', dressed)
    assert sorted(patterns) == sorted(f"floor-{board_svg.room_slug(room)}" for room in board.ROOM_CELLS)
    bodies = [body.split(">", 1)[1] for body in re.findall(r"<pattern [^>]*>.*?</pattern>", dressed)]
    assert len(set(bodies)) == len(board.ROOM_CELLS), "two rooms share a floor"
    walls = plain.count('class="board-wall"')
    assert dressed.count('class="board-wall"') == walls == dressed.count('class="board-wall-inner"')
    assert dressed.count('class="board-door board-door-leaf"') == len(board.DOORS)
    assert 'class="board-door"' not in dressed and "board-rivet" not in dressed
    assert 'class="board-mark"' not in dressed and 'class="board-logo"' in dressed
    assert "board-engraved" in dressed and "board-engraved" not in plain
    assert not re.search(r'(fill|stroke)="(?!none)', dressed.replace('fill="none"', "")), "a colour in the drawing"

    points = board_svg.token_points(tokens)
    for suspect, (x, y) in points.items():
        letter = board_svg.INITIALS[suspect]
        assert f'data-suspect="{suspect}" x="0" y="0" style="transform: translate({x}px, {y}px)" aria-hidden="true">{letter}</text>' in dressed
    assert board_svg.INITIALS["Peacock"] != board_svg.INITIALS["Plum"], "two P's told apart"
    # Undressed, the board is exactly the one Legacy was frozen with.
    for extra in ("board-initial", "board-door-leaf", "board-passage", "board-wall-inner", "<defs>", "board-logo", "logo-", "floor-"):
        assert extra not in plain


def test_every_room_has_its_own_tint_in_both_themes():
    """Nine floors, each on its own pale tint (2026-10-01), defined for
    Case-file light and Gaslight dark alike, and no two rooms the same
    colour in either."""
    css = _stylesheet("casefile")
    light, dark = css.split(':root[data-theme="dark"]', 1)
    for block in (light, dark.split("}", 1)[0]):
        tints = {room: re.search(rf"--room-{board_svg.room_slug(room)}:\s*(#[0-9A-Fa-f]{{6}});", block) for room in board.ROOM_CELLS}
        assert all(tints.values()), f"a room with no tint: {[r for r, m in tints.items() if not m]}"
        assert len({m.group(1).lower() for m in tints.values()}) == len(board.ROOM_CELLS)
    for room in board.ROOM_CELLS:
        assert f'.board-room[data-room="{room}"] rect {{ fill: url(#floor-{board_svg.room_slug(room)}); }}' in css


def test_a_move_into_a_room_names_the_door_it_came_through():
    """2026-10-01: the door a token walked in by is the one of that room
    nearest where it stood (the engine keeps no path); a move by secret
    passage, one ending in the corridor, or a stay has none. A
    suggestion's summons moves a token without a door, and the next move
    starts from the room it was summoned to."""
    from clude_core.domain import Suggestion
    from clude_core.events import MoveEvent, SuggestionEvent

    suspects = ["Scarlett", "Mustard", "White"]
    mustard = board.start_position("Mustard")
    events = [
        MoveEvent(1, 1, "Dining", False),          # Mustard walks in
        MoveEvent(2, 1, "Dining", False),          # and stays
        MoveEvent(3, 1, Square(16, 6), False),     # out to the corridor
        MoveEvent(4, 0, "Lounge", False),
        SuggestionEvent(4, Suggestion(0, "White", "Rope", "Lounge", None, 0, None)),
        MoveEvent(5, 2, "Conservatory", True),     # White, summoned, takes the passage
    ]
    doors = replay_data.entry_doors(events, suspects)
    assert doors[0] == replay_data.nearest_door(mustard, "Dining")
    assert board.DOORS[doors[0]][0] == "Dining"
    assert doors[1:3] == [None, None] and doors[5] is None
    assert board.DOORS[doors[3]][0] == "Lounge"
    assert [replay_data.event_cue(e, d) for e, d in zip(events, doors)] == [
        "door", "tick", "tick", "door", "tick", "passage"
    ]
    # From the square outside a door, that door.
    for index, (room, _cell, square) in enumerate(board.DOORS):
        assert replay_data.nearest_door(square, room) == index


def test_a_closed_door_swings_into_its_room_and_passages_are_marked():
    """2026-10-01: dressed, a door is a closed leaf across its doorway,
    hinged at a jamb (the Hall's pair at their outer ends), whose
    quarter turn `--swing` opens it into the room; and each room a
    secret passage leaves from has its marker in its outer corner."""
    dressed = board_svg.board_svg(dressed=True)
    leaves = [line for line in dressed.splitlines() if "board-door-leaf" in line]
    assert len(leaves) == len(board.DOORS)
    for index, ((room, cell, square), leaf) in enumerate(zip(board.DOORS, leaves)):
        assert f'data-door="{index}" data-room="{room}"' in leaf
        x1, y1, x2, y2 = (float(leaf.split(f'{n}="')[1].split('"')[0]) for n in ("x1", "y1", "x2", "y2"))
        origin = leaf.split("transform-origin: ")[1].split(";")[0]
        assert origin == f"{x1:g}px {y1:g}px", "the hinge is the leaf's first end"
        swing = int(leaf.split("--swing: ")[1].split("deg")[0])
        # The leaf turned by `swing` must point into the room.
        vx, vy = x2 - x1, y2 - y1
        turned = (-vy, vx) if swing == 90 else (vy, -vx)
        assert turned == ((cell.col - square.col) * board_svg.CELL, (cell.row - square.row) * board_svg.CELL), room
    hall = [leaf for leaf in leaves if 'data-room="Hall"' in leaf]
    hinges = [leaf.split("transform-origin: ")[1].split(";")[0] for leaf in hall]
    assert "288px 432px" not in hinges, "the Hall's pair hinged on the jamb they share"
    for room, to in board.SECRET_PASSAGES.items():
        assert f'class="board-passage" data-room="{room}" data-to="{to}"' in dressed
        assert f"Secret passage to the {to}" in dressed
        assert board_svg.passage_cell(room) in board.ROOM_CELLS[room]
    plain = board_svg.board_svg()
    assert "board-door-leaf" not in plain and "board-passage" not in plain


def test_the_logo_is_the_keyhole_question_mark_in_every_place_it_goes():
    """D5, candidate E (David, 2026-09-29): the keyhole with a "?"
    keyway, above the cartouche wordmark in the cellar; the keyhole
    alone in the header bar and the favicon. Uncoloured except the
    favicon, which has no stylesheet, and whose file is the one
    `logo.favicon_svg` writes."""
    from clude_web import logo

    cellar = logo.cellar(120, 168)
    assert ">?</text>" in cellar and ">clude</text>" in cellar and "ellipse" in cellar
    mark = logo.mark_svg(22)
    ET.fromstring(mark)
    assert ">?</text>" in mark and "clude" not in mark and 'aria-hidden="true"' in mark
    assert "fill=" not in cellar + mark and "#" not in cellar + mark
    favicon = Path(__file__).resolve().parents[1] / "clude_web" / "static" / "favicon.svg"
    assert favicon.read_text(encoding="utf-8") == logo.favicon_svg(), (
        "regenerate static/favicon.svg from clude_web.logo.favicon_svg()"
    )
    ET.fromstring(logo.favicon_svg())


def _style_keys() -> list:
    """Every look on the list (Phase 9h): the tests below hold for each,
    not just the first. Keys only: a parameter holding the stylesheet's
    text put 32 KB into the test id, and Windows refuses an environment
    variable (pytest's PYTEST_CURRENT_TEST) that long."""
    from clude_web import styles

    return list(styles.STYLES)


def _stylesheet(key: str) -> str:
    """The text of one look's stylesheet."""
    from clude_web import styles

    static = Path(__file__).resolve().parents[1] / "clude_web" / "static"
    return (static / styles.STYLES[key].stylesheet).read_text(encoding="utf-8")


@pytest.mark.parametrize("key", _style_keys())
def test_every_class_the_board_uses_is_styled(key):
    """board_svg.py sets no colour, so a class with no rule is an
    invisible shape -- on the board each look actually gets, dressed for
    an Engraved one (Phase 10f). The stylesheet must also stay ASCII: a
    Devanagari digit once made it into a hex colour, which CSS silently
    ignores."""
    from clude_web import styles

    css = _stylesheet(key)
    svg = board_svg.board_svg(
        {"Scarlett": "Hall", "Plum": Square(7, 4)}, dressed=styles.STYLES[key].engraved
    )
    used = {
        name
        for group in re.findall(r'class="([^"]+)"', svg)
        for name in group.split()
    }

    assert css.isascii(), f"a non-ASCII character got into the {key} stylesheet"
    unstyled = sorted(name for name in used if f".{name}" not in css)
    assert not unstyled, f"classes with no rule in {key}: {unstyled}"


@pytest.mark.parametrize("key", _style_keys())
def test_the_stylesheet_has_no_broken_colours(key):
    """CSS fails silently: a malformed value is dropped and the shape
    renders with whatever it inherited, which is exactly how `#b4a
    territory` and a Devanagari digit both got as far as a screenshot."""
    css = _stylesheet(key)
    malformed = re.findall(r"--[a-z-]+:\s*#[0-9a-fA-F]*[^0-9a-fA-F;\s][^;]*;", css)
    assert not malformed, f"malformed colour values in {key}: {malformed}"

    defined = set(re.findall(r"(--[a-z-]+)\s*:", css))
    used = set(re.findall(r"var\((--[a-z-]+)\)", css))
    assert not used - defined, f"variables used but never defined in {key}: {sorted(used - defined)}"


def test_three_looks_and_every_face_is_served():
    """David, 2026-09-29 (D17): Case-file light (the default) and
    Gaslight dark on one sheet, each fixing its theme, and Developer,
    which was Legacy, on the sheet frozen in 9h and the only look that
    shows costs; every font file the Engraved sheet names exists under
    static/fonts/."""
    from clude_web import styles

    assert list(styles.STYLES) == ["casefile", "gaslight", "developer"]
    assert [styles.STYLES[k].title for k in styles.STYLES] == ["Case-file light", "Gaslight dark", "Developer"]
    assert styles.DEFAULT_STYLE == "casefile"
    assert [styles.STYLES[k].theme for k in ("casefile", "gaslight")] == ["light", "dark"]
    assert {styles.STYLES[k].stylesheet for k in ("casefile", "gaslight")} == {"styles/engraved.css"}
    developer = styles.STYLES["developer"]
    assert not developer.engraved and developer.stylesheet == "styles/legacy.css" and developer.costs
    assert not any(styles.STYLES[k].costs for k in ("casefile", "gaslight"))
    assert styles.style_named("legacy") is developer and styles.style_named("engraved").key == "gaslight"
    static = Path(__file__).resolve().parents[1] / "clude_web" / "static"
    css = (static / styles.STYLES["casefile"].stylesheet).read_text(encoding="utf-8")
    faces = re.findall(r"url\(\.\./fonts/([^)]+)\)", css)
    assert len(faces) == 8, faces
    for name in faces:
        assert (static / "fonts" / name).is_file(), f"{name} is named by the sheet but missing"


def test_gaslight_dark_redefines_only_tokens_the_light_theme_has():
    """Every Engraved look fixes its theme, so the sheet has one dark
    block, under ``data-theme="dark"``, and no device preference (the
    auto look it served is gone, D17). A token only the dark block
    defines would be missing from Case-file light."""
    css = _stylesheet("casefile")
    assert "prefers-color-scheme" not in css
    root = re.search(r"^:root \{(.*?)^\}", css, re.S | re.M).group(1)
    dark = re.search(r':root\[data-theme="dark"\] \{(.*?)\n\}', css, re.S).group(1)
    light_tokens = set(re.findall(r"(--[a-z-]+)\s*:", root))
    dark_tokens = set(re.findall(r"(--[a-z-]+)\s*:", dark))
    assert dark_tokens and not dark_tokens - light_tokens, sorted(dark_tokens - light_tokens)
    assert "--alarm" in dark_tokens, "the clock's last-ten-seconds red has a dark twin"


def test_the_shared_chrome_uses_only_tokens_every_look_defines():
    """The header's wooden question mark and the footer (2026-09-29) are
    dressed by chrome.css, loaded after whichever look's sheet; it may
    only use tokens every sheet defines, and like them stays ASCII."""
    from clude_web import styles

    static = Path(__file__).resolve().parents[1] / "clude_web" / "static"
    chrome = (static / "styles" / "chrome.css").read_text(encoding="utf-8")
    assert chrome.isascii()
    used = set(re.findall(r"var\((--[a-z-]+)\)", chrome))
    assert used
    for key in styles.STYLES:
        defined = set(re.findall(r"(--[a-z-]+)\s*:", _stylesheet(key)))
        assert not used - defined, f"{key} lacks {sorted(used - defined)}"
    assert not re.search(r"(?:animation|transition):", chrome)


def test_engraved_names_no_duration_outside_its_tokens():
    """Phase 10b (plan section 5.4). Every duration is a token in
    `:root`, so `body[data-motion="off"]` and reduced motion can zero
    them all: a literal `120ms` on a rule would keep animating under a
    screenshot, which is the bug that cost a day in 8.1."""
    from clude_web import styles

    static = Path(__file__).resolve().parents[1] / "clude_web" / "static"
    css = (static / styles.STYLES["casefile"].stylesheet).read_text(encoding="utf-8")
    root = re.search(r"^:root \{(.*?)^\}", css, re.S | re.M).group(1)
    outside = css.replace(root, "")
    literal = [m for m in re.findall(r"\b\d*\.?\d+m?s\b", outside) if m != "0s"]
    assert not literal, f"durations outside :root in engraved.css: {literal}"
    assert re.search(r"--dur-move:\s*\d+ms", root), "the move duration is a token"
    assert 'body[data-motion="off"]' in css and "prefers-reduced-motion" in css
    # Every animation and transition runs on a token (10e-10f): the panel
    # cut, the impact frame, the lit squares' pulse, a token's glide.
    for rule in re.findall(r"(?:animation|transition):[^;]+;", outside):
        assert "var(--dur-" in rule, f"a motion without a duration token: {rule}"


# --- the event frames -------------------------------------------------


def test_every_event_gets_a_frame_with_a_line_and_a_board():
    record = play()
    frames = replay_data.event_frames(record)

    assert len(frames) == len(record.events)
    assert all(frame.text for frame in frames)
    assert all(frame.positions for frame in frames)
    assert [f.index for f in frames] == list(range(len(frames)))
    # Each step names the sound Play makes on reaching it (Phase 10g),
    # the same cue the table gives the same event.
    doors = replay_data.entry_doors(record.events, replay_data.seat_names(record))
    assert [f.cue for f in frames] == [replay_data.event_cue(e, d) for e, d in zip(record.events, doors)]
    assert [f.door for f in frames] == doors
    assert {f.cue for f in frames if f.kind == "move"} <= {"tick", "door", "passage"}
    assert {f.cue for f in frames if f.kind == "move"} >= {"tick", "door"}
    assert {f.cue for f in frames if f.kind in ("over", "accusation")} <= {"accent"}


def test_the_last_frame_matches_the_finished_game():
    """The fold here must land where `state_from_record`'s does, or the
    scrubber's end and the stored game would disagree."""
    from clude_training.replay import state_from_record

    record = play()
    frames = replay_data.event_frames(record)
    final = state_from_record(record)

    by_suspect = {
        final.suspects_in_play[seat]: node for seat, node in final.positions.items()
    }
    assert frames[-1].positions == by_suspect


def test_a_suggestion_drags_the_named_token_into_the_room():
    """The engine moves the named suspect without a move event of its
    own, so the fold has to do it too or tokens drift."""
    record = play()
    frames = replay_data.event_frames(record)
    suggested = [e.suggestion for e in record.events if hasattr(e, "suggestion")]
    frames_of = [f for f in frames if f.kind == "suggestion"]

    assert suggested, "the sample game made no suggestions"
    assert len(frames_of) == len(suggested)
    in_play = set(replay_data.seat_names(record))
    checked = 0
    for frame, suggestion in zip(frames_of, suggested):
        # A three-handed game can name a suspect with no token on the
        # board; only the ones actually seated get dragged.
        if suggestion.suspect in in_play:
            assert frame.positions[suggestion.suspect] == suggestion.room
            checked += 1
    assert checked, "no suggestion named a suspect in play"


def test_suggesting_an_absent_suspect_moves_nothing():
    """At a three-handed table most suspects have no token. Naming one
    must not invent a position for it."""
    record = play()
    in_play = set(replay_data.seat_names(record))

    for frame in replay_data.event_frames(record):
        assert set(frame.positions) == in_play


def test_a_suggestion_line_names_the_refutation():
    """A post-game replay is omniscient, so it says which card was shown
    -- live, only the two seats involved saw it."""
    record = play()
    lines = [
        f.text for f in replay_data.event_frames(record) if f.kind == "suggestion"
    ]
    suggestions = [e.suggestion for e in record.events if hasattr(e, "suggestion")]

    assert lines
    for line, suggestion in zip(lines, suggestions):
        assert suggestion.suspect in line and suggestion.weapon in line
        assert suggestion.room in line
        if suggestion.refuter is None:
            assert "Nobody could disprove" in line
        else:
            assert suggestion.card_shown in line


def test_the_suggestion_count_climbs_once_per_suggestion():
    record = play()
    frames = replay_data.event_frames(record)

    suggestions = sum(1 for f in frames if f.kind == "suggestion")
    assert frames[-1].k == suggestions
    assert all(a.k <= b.k for a, b in zip(frames, frames[1:])), "k went backwards"


# --- the trace --------------------------------------------------------


def test_a_trace_has_one_frame_per_suggestion_and_the_truth():
    record = play()
    document = replay_data.trace_document(record)

    n_suggestions = len(
        [e for e in record.events if hasattr(e, "suggestion")]
    )
    assert document["ks"] == list(range(n_suggestions + 1))
    assert len(document["frames"]) == len(document["ks"])
    assert document["envelope"] == list(record.envelope)
    assert document["limitation"]


def test_every_seat_reports_what_its_floor_has_proven():
    record = play()
    document = replay_data.trace_document(record)

    for frame in document["frames"]:
        assert len(frame["seats"]) == record.n_players
        for seat in frame["seats"]:
            assert set(seat["proven"]) == set(ALL_CARDS)
    first = document["frames"][0]["seats"][0]
    own_hand = document["seats"][0]["hand"]
    assert own_hand, "a seat was dealt nothing"
    assert all(first["proven"][card] == 0 for card in own_hand), (
        "a seat should have its own hand proven from the first frame"
    )


def test_what_the_floor_proves_never_contradicts_the_deal():
    """Whatever a seat has proven must be true: a card proven to a seat
    is in that seat's hand, and a card proven to the envelope is in the
    envelope. The floor is the one thing on the screen that claims
    certainty, so it had better never be wrong."""
    record = play()
    document = replay_data.trace_document(record)
    hands = {int(seat): set(cards) for seat, cards in record.hands.items()}
    envelope = set(record.envelope)

    for frame in document["frames"]:
        for seat in frame["seats"]:
            for card, holder in seat["proven"].items():
                if holder is None:
                    continue
                if holder == ENVELOPE:
                    assert card in envelope, f"{card} wrongly proven to the envelope"
                else:
                    assert card in hands[holder], f"{card} proven to the wrong seat"


def test_solving_the_envelope_shows_up_as_proven():
    """The strongest thing a seat can know, and what the screen has to be
    able to draw: a card proven to be the envelope's."""
    record = play()
    document = replay_data.trace_document(record)

    last = document["frames"][-1]
    proven_envelope = {
        card
        for seat in last["seats"]
        for card, holder in seat["proven"].items()
        if holder == ENVELOPE
    }
    assert proven_envelope <= set(record.envelope)


def test_a_seat_with_a_method_reports_probabilities_and_a_bot_does_not():
    record = play()  # every seat is a FloorBot, which has no belief method
    document = replay_data.trace_document(record)

    assert all(
        seat["probabilities"] == {} for seat in document["frames"][0]["seats"]
    )
    assert all(seat["method"] == "" for seat in document["seats"])


def test_a_character_seat_reports_a_belief_over_every_card():
    labels = ["Scarlett", "Peacock", "Mustard"]
    bots = {p: build_character(labels[p]) for p in range(3)}
    state, events = engine.run_game(
        3, bots, seed=3, max_turns=30, observer=clude_constraints.observe
    )
    record = record_of(state, events, labels, "character", index=1, seed=3)

    document = replay_data.trace_document(record)

    for seat in document["frames"][-1]["seats"]:
        assert set(seat["probabilities"]) == set(ALL_CARDS)
        total = sum(seat["probabilities"][c] for c in document["categories"]["rooms"])
        assert abs(total - 1.0) < 1e-6, "a category's probabilities should sum to 1"
    assert all(seat["method"] for seat in document["seats"])


# --- the cache --------------------------------------------------------


def test_a_trace_is_computed_once_and_read_back(tmp_path):
    store = LocalStore(str(tmp_path))
    record = play()

    first = replay_data.cached_trace(store, record)
    second = replay_data.cached_trace(store, record)

    assert first == second
    assert store.get_doc(replay_data.trace_key(record.run_id, record.game_index))
    assert first["built"] == second["built"], "the trace was rebuilt instead of read"


def test_every_seat_has_a_certainty_in_every_frame_and_the_floor_s_only_rises():
    """Phase 9h. A seat with no method is measured from its floor alone,
    which only ever tightens, so its certainty never falls along the
    game; a character's comes from its own confidence. Both are in
    [0, 1] and reach the screen payload."""
    record = play()
    document = replay_data.trace_document(record)
    assert document["version"] == 2
    for seat in range(record.n_players):
        values = [frame["seats"][seat]["certainty"] for frame in document["frames"]]
        assert all(0.0 <= v <= 1.0 for v in values)
        assert values == sorted(values), f"seat {seat}'s floor certainty fell"
        assert values[0] > 0.0, "a seat's own hand already narrows the field"
    winner = record.winner
    if winner is not None:
        assert abs(document["frames"][-1]["seats"][winner]["certainty"] - 1.0) < 1e-3
    payload = replay_data.screen_payload(record, document)
    assert all("certainty" in seat for belief in payload["beliefs"] for seat in belief["seats"])

    # A character's certainty is its own confidence, Peacock's her lower bound.
    from clude_agents import build_agent
    from clude_agents.character import certainty, ds_belief_confidence
    from clude_training.replay import state_from_record
    state = state_from_record(record)
    obs = clude_constraints.observe(state, 0)
    peacock = build_agent("Peacock")
    peacock.reset(record.seed)
    belief = peacock.select_action(obs)
    assert replay_data.seat_certainty("Peacock", belief, obs) == round(certainty(ds_belief_confidence(belief)), 4)


def test_a_stale_trace_is_rebuilt_rather_than_trusted(tmp_path):
    store = LocalStore(str(tmp_path))
    record = play()
    key = replay_data.trace_key(record.run_id, record.game_index)
    store.put_doc(key, {"version": replay_data.TRACE_VERSION - 1, "every": 1})

    document = replay_data.cached_trace(store, record)

    assert document["version"] == replay_data.TRACE_VERSION
    assert document["frames"]


def test_belief_at_holds_the_last_frame_before_a_gap():
    document = {"frames": [{"k": 0, "seats": []}, {"k": 4, "seats": []}]}

    assert replay_data.belief_at(document, 0)["k"] == 0
    assert replay_data.belief_at(document, 3)["k"] == 0
    assert replay_data.belief_at(document, 4)["k"] == 4
    assert replay_data.belief_at(document, 99)["k"] == 4
