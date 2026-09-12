from clude_core import board
from clude_core.domain import ROOMS


def test_every_room_has_two_cycle_edges():
    for room in ROOMS:
        assert len(board.ROOM_EDGES[room]) == 2


def test_secret_passages_are_symmetric_and_connect_corners():
    assert board.SECRET_PASSAGES["Kitchen"] == "Study"
    assert board.SECRET_PASSAGES["Study"] == "Kitchen"
    assert board.SECRET_PASSAGES["Conservatory"] == "Lounge"
    assert board.SECRET_PASSAGES["Lounge"] == "Conservatory"


def test_neighbors_of_room_are_hallway_cells_adjacent_to_it():
    for nb in board.neighbors("Kitchen"):
        assert isinstance(nb, board.HallwayCell)
        assert "Kitchen" in (nb.room_a, nb.room_b)


def test_neighbors_of_hallway_cell_are_reciprocal():
    cell = board.HallwayCell("Kitchen", "Ballroom", 2)
    for nb in board.neighbors(cell):
        assert cell in board.neighbors(nb)


def test_reachable_excludes_start_and_stops_at_rooms():
    start = board.HallwayCell("Kitchen", "Ballroom", 1)
    dests = board.reachable(start, roll=1, occupied=frozenset())
    assert start not in dests
    assert "Kitchen" in dests  # one step toward Kitchen's door


def test_reachable_is_blocked_by_occupied_cell():
    start = board.HallwayCell("Kitchen", "Ballroom", 1)
    blocker = board.HallwayCell("Kitchen", "Ballroom", 2)
    dests = board.reachable(start, roll=3, occupied=frozenset({blocker}))
    assert blocker not in dests
    assert board.HallwayCell("Kitchen", "Ballroom", 3) not in dests  # unreachable past the block
    assert "Ballroom" not in dests


def test_reachable_lets_a_token_leave_its_room_through_either_door():
    """Phase 5b regression: the start room used to be treated as
    terminal, so tokens could only leave rooms by secret passage."""
    dests = board.reachable("Lounge", roll=2, occupied=frozenset())
    assert board.HallwayCell("Hall", "Lounge", board.HALLWAY_LENGTH) in dests
    assert board.HallwayCell("Lounge", "Dining", 1) in dests
    assert board.HallwayCell("Lounge", "Dining", 2) in dests
    assert "Lounge" not in dests
    far = board.reachable("Lounge", roll=6, occupied=frozenset())
    assert "Hall" in far and "Dining" in far  # five steps away, within a 6
    assert "Conservatory" not in far  # the secret passage is a separate move type


def test_reachable_room_does_not_extend_further_same_turn():
    start = board.HallwayCell("Kitchen", "Ballroom", 1)
    dests = board.reachable(start, roll=6, occupied=frozenset())
    assert "Kitchen" in dests
    # Kitchen's own far-side neighbor toward Dining should not appear,
    # since movement stops on entering a room.
    assert board.HallwayCell("Dining", "Kitchen", board.HALLWAY_LENGTH) not in dests


def test_start_positions_cover_all_six_suspects():
    from clude_core.domain import SUSPECTS

    for suspect in SUSPECTS:
        pos = board.start_position(suspect)
        assert isinstance(pos, board.HallwayCell)
