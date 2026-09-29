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
    """Phase 10f (plan 8). Dressed, the board gains the four floor
    patterns, a brass line inside every wall, a rivet at each end of
    every door, an initial on every token where the token stands, and
    the logo in the cellar in place of the wordmark -- every shape
    classed, none coloured, the whole still well-formed."""
    tokens = {"Scarlett": "Hall", "Plum": Square(7, 4), "Peacock": "Hall"}
    plain = board_svg.board_svg(tokens)
    dressed = board_svg.board_svg(tokens, dressed=True)
    ET.fromstring(dressed)

    for pattern in ("tone-parquet", "tone-tile", "tone-boards", "tone-rug"):
        assert f'id="{pattern}"' in dressed and pattern not in plain
    walls = plain.count('class="board-wall"')
    assert dressed.count('class="board-wall"') == walls == dressed.count('class="board-wall-inner"')
    assert dressed.count('class="board-rivet"') == 2 * len(board.DOORS)
    assert 'class="board-mark"' not in dressed and 'class="board-logo"' in dressed
    assert "board-engraved" in dressed and "board-engraved" not in plain
    assert not re.search(r'(fill|stroke)="(?!none)', dressed.replace('fill="none"', "")), "a colour in the drawing"

    points = board_svg.token_points(tokens)
    for suspect, (x, y) in points.items():
        letter = board_svg.INITIALS[suspect]
        assert f'data-suspect="{suspect}" x="0" y="0" style="transform: translate({x}px, {y}px)" aria-hidden="true">{letter}</text>' in dressed
    assert board_svg.INITIALS["Peacock"] != board_svg.INITIALS["Plum"], "two P's told apart"
    # Undressed, the board is exactly the one Legacy was frozen with.
    for extra in ("board-initial", "board-rivet", "board-wall-inner", "<defs>", "board-logo", "logo-"):
        assert extra not in plain


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


def test_legacy_stays_on_the_list_and_every_face_is_served():
    """Phase 10b. Legacy is never removed (David, 2026-09-28); Engraved
    is the default from 10e (D7), as the device has it or fixed light or
    dark by name (David, 2026-09-29), all three on one sheet; and every
    font file that sheet names exists under static/fonts/."""
    from clude_web import styles

    assert list(styles.STYLES) == ["engraved", "casefile", "gaslight", "legacy"]
    assert styles.DEFAULT_STYLE == "engraved"
    assert [styles.STYLES[k].theme for k in ("engraved", "casefile", "gaslight")] == ["", "light", "dark"]
    assert {styles.STYLES[k].stylesheet for k in ("engraved", "casefile", "gaslight")} == {"styles/engraved.css"}
    assert not styles.STYLES["legacy"].engraved and styles.STYLES["legacy"].stylesheet == "styles/legacy.css"
    static = Path(__file__).resolve().parents[1] / "clude_web" / "static"
    css = (static / styles.STYLES["engraved"].stylesheet).read_text(encoding="utf-8")
    faces = re.findall(r"url\(\.\./fonts/([^)]+)\)", css)
    assert len(faces) == 8, faces
    for name in faces:
        assert (static / "fonts" / name).is_file(), f"{name} is named by the sheet but missing"


def test_a_fixed_theme_gets_the_same_dark_tokens_as_the_device():
    """The dark tokens are written twice -- once for a device that asks
    for dark, once for the "Gaslight dark" look -- because CSS cannot
    share one block between a media query and a selector. They must not
    drift apart; and a fixed light look must be exempt from the query."""
    css = _stylesheet("engraved")
    by_device = re.search(r':root:not\(\[data-theme="light"\]\) \{(.*?)\n  \}', css, re.S)
    by_name = re.search(r':root\[data-theme="dark"\] \{(.*?)\n\}', css, re.S)
    assert by_device and by_name

    def tokens(block):
        return sorted(line.strip() for line in block.group(1).splitlines() if line.strip())

    assert tokens(by_device) == tokens(by_name)
    assert "--alarm:" in by_name.group(1), "the clock's last-ten-seconds red has a dark twin"


def test_engraved_names_no_duration_outside_its_tokens():
    """Phase 10b (plan section 5.4). Every duration is a token in
    `:root`, so `body[data-motion="off"]` and reduced motion can zero
    them all: a literal `120ms` on a rule would keep animating under a
    screenshot, which is the bug that cost a day in 8.1."""
    from clude_web import styles

    static = Path(__file__).resolve().parents[1] / "clude_web" / "static"
    css = (static / styles.STYLES["engraved"].stylesheet).read_text(encoding="utf-8")
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
    assert [f.cue for f in frames] == [replay_data.event_cue(e) for e in record.events]
    assert {f.cue for f in frames if f.kind == "move"} == {"tick"}
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
