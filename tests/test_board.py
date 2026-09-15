from pathlib import Path

import pytest

from clude_core import board
from clude_core.board import Square
from clude_core.domain import ROOMS, SUSPECTS


def test_map_matches_the_human_copy_in_docs():
    human = Path(__file__).resolve().parents[1] / "docs" / "ux" / "board_map.txt"
    ours = [line.rstrip() for line in board.BOARD_MAP.splitlines()]
    theirs = [line.rstrip() for line in human.read_text(encoding="utf-8").splitlines()]
    assert ours == theirs


def test_map_dimensions_and_counts():
    assert len(board.CORRIDOR) == 182 + 6  # corridor squares plus the six start squares
    assert sum(len(cells) for cells in board.ROOM_CELLS.values()) == 345
    assert len(board.CELLAR) == 35  # 7 rows x 5 columns
    assert len(board.DOORS) == 17
    per_room = {room: len(board.EXITS[room]) for room in ROOMS}
    assert per_room == {
        "Kitchen": 1, "Ballroom": 4, "Conservatory": 1, "Dining": 2, "Billiard": 2,
        "Library": 2, "Lounge": 1, "Hall": 3, "Study": 1,
    }


def test_cells_are_disjoint():
    seen: set[Square] = set()
    for cells in list(board.ROOM_CELLS.values()) + [board.CELLAR, board.CORRIDOR]:
        assert not (seen & cells)
        seen |= cells


def test_every_door_opens_onto_a_corridor_square_and_serves_one_room():
    for room, cell, square in board.DOORS:
        assert cell in board.ROOM_CELLS[room]
        assert square in board.CORRIDOR
        assert abs(cell.row - square.row) + abs(cell.col - square.col) == 1
    assert len(board.ENTRANCES) == 17  # no corridor square serves two doors


def test_the_three_doors_beside_two_squares_face_the_right_way():
    assert board.ENTRANCES[Square(5, 18)] == "Conservatory"
    assert Square(4, 17) not in board.ENTRANCES
    assert board.ENTRANCES[Square(18, 6)] == "Lounge"
    assert Square(19, 7) not in board.ENTRANCES
    assert board.ENTRANCES[Square(20, 17)] == "Study"
    assert Square(21, 16) not in board.ENTRANCES


def test_secret_passages_are_symmetric_and_connect_corners():
    assert board.SECRET_PASSAGES["Kitchen"] == "Study"
    assert board.SECRET_PASSAGES["Study"] == "Kitchen"
    assert board.SECRET_PASSAGES["Conservatory"] == "Lounge"
    assert board.SECRET_PASSAGES["Lounge"] == "Conservatory"


def test_start_squares_cover_all_six_suspects_and_touch_the_corridor():
    assert set(board.START_SQUARES) == set(SUSPECTS)
    assert board.start_position("Mustard") == Square(17, 0)
    assert board.start_position("White") == Square(0, 9)
    for suspect in SUSPECTS:
        start = board.start_position(suspect)
        assert start in board.CORRIDOR
        assert any(isinstance(nb, Square) for nb in board.neighbors(start))


def test_neighbors_of_room_are_the_squares_outside_its_doors():
    assert board.neighbors("Kitchen") == [Square(7, 4)]
    assert set(board.neighbors("Hall")) == {Square(17, 11), Square(17, 12), Square(20, 15)}


def test_neighbors_of_squares_are_reciprocal_and_never_the_cellar():
    for sq in board.CORRIDOR:
        for nb in board.neighbors(sq):
            if isinstance(nb, Square):
                assert sq in board.neighbors(nb)
                assert nb not in board.CELLAR
            else:
                assert sq in board.neighbors(nb)
    assert Square(10, 10) not in board.CORRIDOR


def test_reachable_from_a_room_leaves_by_a_door_and_cannot_return():
    assert board.reachable("Kitchen", roll=1, occupied=frozenset()) == {Square(7, 4)}
    two = board.reachable("Kitchen", roll=2, occupied=frozenset())
    assert two == {Square(7, 3), Square(7, 5), Square(8, 4)}
    six = board.reachable("Kitchen", roll=6, occupied=frozenset())
    assert "Kitchen" not in six
    assert Square(5, 7) in six  # outside the Ballroom's west door, six steps exactly
    assert "Ballroom" not in six  # the door itself would be a seventh step
    assert "Study" not in six  # the secret passage is a separate move type


def test_reachable_uses_the_whole_roll_unless_a_room_is_entered():
    start = Square(7, 4)
    assert board.reachable(start, roll=1, occupied=frozenset()) == {
        "Kitchen", Square(7, 3), Square(7, 5), Square(8, 4)
    }
    two = board.reachable(start, roll=2, occupied=frozenset())
    assert "Kitchen" in two  # a room one step away still ends a move
    assert Square(7, 3) not in two  # one step short of the roll is not a stop
    assert start not in two
    assert Square(7, 3) in board.reachable(start, roll=3, occupied=frozenset())  # via (8,4),(8,3)


def test_reachable_never_revisits_a_square_in_one_move():
    # From a dead-end-ish spot, an even roll cannot bounce back to the start's neighbour.
    start = Square(24, 16)  # the single square between the Hall and the Study
    one = board.reachable(start, roll=1, occupied=frozenset())
    assert one == {Square(23, 16)}
    two = board.reachable(start, roll=2, occupied=frozenset())
    assert start not in two and Square(23, 16) not in two


def test_reachable_is_blocked_by_occupied_squares_but_may_go_round():
    start = Square(7, 4)
    blocker = frozenset({Square(7, 5)})
    assert Square(7, 5) not in board.reachable(start, roll=1, occupied=blocker)
    assert Square(7, 6) not in board.reachable(start, roll=2, occupied=blocker)
    assert Square(7, 6) in board.reachable(start, roll=4, occupied=blocker)  # round by row 8


def test_room_left_forbids_reentry_from_a_square():
    assert "Kitchen" in board.reachable(Square(7, 4), roll=1, occupied=frozenset())
    assert "Kitchen" not in board.reachable(Square(7, 4), roll=1, occupied=frozenset(), room_left="Kitchen")


def test_room_distances_count_passages_as_one_step():
    d = board.room_distances("Kitchen")
    assert d["Kitchen"] == 0 and d["Study"] == 1
    assert board.room_distances("Lounge")["Conservatory"] == 1
    hall = board.room_distances("Hall")
    assert hall["Lounge"] < hall["Conservatory"]
    from_square = board.room_distances(Square(7, 4))
    assert from_square["Kitchen"] == 1
    assert all(isinstance(v, int) and v >= 0 for v in from_square.values())


def test_node_sort_key_orders_rooms_then_squares_then_legacy_cells():
    nodes = [Square(3, 2), "Hall", board.HallwayCell("Kitchen", "Ballroom", 1), Square(1, 9), "Ballroom"]
    assert sorted(nodes, key=board.node_sort_key) == [
        "Ballroom", "Hall", Square(1, 9), Square(3, 2), board.HallwayCell("Kitchen", "Ballroom", 1)
    ]


def test_legacy_hallway_cell_is_a_position_only_for_room_of():
    cell = board.HallwayCell("Kitchen", "Ballroom", 2)
    assert board.room_of(cell) is None
    with pytest.raises(TypeError):
        board.neighbors(cell)
    with pytest.raises(TypeError):
        board.reachable(cell, roll=1, occupied=frozenset())
