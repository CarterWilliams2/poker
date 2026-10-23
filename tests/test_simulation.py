import random
import pytest
from game import Action
from random_agent import RandomAgent
from simulation import AgentRecord, Simulation, SimulationResults

FOLD = (Action.FOLD, 0)
CHECK = (Action.CHECK, 0)
CALL = (Action.CALL, 0)


def random_seats(count, seed=0):
    return [(f"Bot {i}", RandomAgent(random.Random(seed + i))) for i in range(count)]


def shover(player, game):
    """Goes all-in whenever it can, otherwise calls."""
    all_in_total = player.committed_this_round + player.chips
    if game.is_legal(player, Action.RAISE, all_in_total):
        return Action.RAISE, all_in_total
    return CALL


def folder(player, game):
    return CHECK if game.current_bet == player.committed_this_round else FOLD


def test_checks_the_seats_up_front():
    with pytest.raises(ValueError, match="2 to 8"):
        Simulation(random_seats(9), 100, 1, 2)


def test_every_game_has_exactly_one_winner_when_played_out():
    results = Simulation(random_seats(4), 50, 1, 2).run(20)
    assert results.games == 20
    assert results.draws == 0
    assert sum(r.wins for r in results.records.values()) == 20
    assert all(r.games == 20 for r in results.records.values())
    assert sorted(place for r in results.records.values() for place in r.places) == \
        sorted(list(range(1, 5)) * 20)
    assert results.hands > 0


def test_the_better_agent_wins_every_game():
    # The folder gives up its blind every hand it can't check, so the shover always ends up with it all.
    results = Simulation([("Shover", shover), ("Folder", folder)], 20, 1, 2).run(6)
    assert results.records["Shover"].wins == 6
    assert results.records["Folder"].wins == 0
    assert results.records["Shover"].average_place == 1
    assert results.records["Folder"].average_place == 2
    assert [name for name, _ in results.ranked()] == ["Shover", "Folder"]


def test_seating_rotates_each_game():
    first_seat = []

    def on_game(number, match):
        first_seat.append(match.players[0].name)

    Simulation(random_seats(3), 20, 1, 2).run(4, on_game)
    assert first_seat == ["Bot 0", "Bot 1", "Bot 2", "Bot 0"]


def test_max_hands_gives_the_game_to_the_chip_leader():
    # Whoever has the button, the folder folds the only hand, so the shover leads after it.
    results = Simulation([("Shover", shover), ("Folder", folder)], 1000, 1, 2,
                         max_hands=1).run(2)
    assert results.hands == 2
    assert results.draws == 0
    assert results.records["Shover"].wins == 2


def test_a_tied_chip_lead_is_a_draw():
    # Two folders just trade blinds, so after two hands they're level.
    results = Simulation([("A", folder), ("B", folder)], 100, 1, 2, max_hands=2).run(3)
    assert results.draws == 3
    assert all(r.wins == 0 for r in results.records.values())


def test_records_with_no_games_are_zero():
    record = AgentRecord()
    assert record.win_rate == 0
    assert record.average_place == 0
    assert SimulationResults({"A": record}).ranked() == [("A", record)]
