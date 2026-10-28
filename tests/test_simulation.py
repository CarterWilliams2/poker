import random
import pytest
from game import Action
from random_agent import RandomAgent
from simulation import (AgentRecord, CashResults, CashSimulation, ChipRecord, Simulation,
                        SimulationResults)

FOLD = (Action.FOLD, 0)
CHECK = (Action.CHECK, 0)
CALL = (Action.CALL, 0)


def random_seats(count, seed=0):
    return [(f"Bot {i}", RandomAgent(random.Random(seed + i))) for i in range(count)]


def shover(view):
    """Goes all-in whenever it can, otherwise calls."""
    if view.legal.can_raise:
        return Action.RAISE, view.legal.max_raise_to
    return CALL


def folder(view):
    return CHECK if view.legal.can_check else FOLD


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


def test_the_same_seed_plays_the_same_games():
    def standings(seed):
        places = []
        Simulation(random_seats(3), 20, 1, 2, rng=random.Random(seed)).run(
            3, lambda number, match: places.append([p.name for p in match.standings()]))
        return places

    assert standings(5) == standings(5)


def test_cash_hands_start_from_fresh_stacks():
    # The shover takes the folder's blind every hand. Fresh stacks mean the folder never busts,
    # so every hand counts the same.
    results = CashSimulation([("Shover", shover), ("Folder", folder)], 20, 1, 2,
                             duplicate=False).run(10)
    assert results.hands == 10
    # Each hand the folder either folds its small blind (0.5 big blinds) or, in the big blind,
    # faces the shove and folds 1 big blind. Seats alternate, so that averages to 0.75.
    assert results.records["Shover"].bb_per_100 == pytest.approx(75)
    assert results.records["Folder"].bb_per_100 == pytest.approx(-75)
    assert [name for name, _ in results.ranked()] == ["Shover", "Folder"]


def test_duplicate_deals_are_played_once_from_every_seat():
    seen = set()

    def watcher(view):
        seen.add((view.name, " ".join(f"{card.value}{card.suit}" for card in view.hand)))
        return shover(view)

    seats = [("A", watcher), ("B", watcher), ("C", watcher)]
    results = CashSimulation(seats, 20, 1, 2, rng=random.Random(3)).run(1)
    assert results.hands == 3
    assert all(len(record.deals) == 1 for record in results.records.values())
    # The three replays hand out the same three sets of cards, and each agent gets each one.
    hands = {hand for _, hand in seen}
    assert len(hands) == 3
    assert seen == {(name, hand) for name in "ABC" for hand in hands}


def test_duplicate_deals_cancel_out_the_cards_between_equal_agents():
    # The same deterministic agent in every seat plays each seat once, so everyone breaks even.
    results = CashSimulation([("A", shover), ("B", shover), ("C", shover)], 20, 1, 2,
                             rng=random.Random(4)).run(20)
    assert all(record.bb_per_100 == pytest.approx(0) for record in results.records.values())
    assert all(record.margin == pytest.approx(0) for record in results.records.values())


def test_cash_progress_is_reported_after_each_deal():
    numbers = []
    CashSimulation(random_seats(2), 20, 1, 2).run(3, numbers.append)
    assert numbers == [1, 2, 3]


def test_cash_simulation_checks_the_seats_up_front():
    with pytest.raises(ValueError, match="2 to 8"):
        CashSimulation(random_seats(1), 100, 1, 2)


def test_the_margin_shrinks_as_deals_add_up():
    assert ChipRecord([1.0]).margin == float("inf")
    assert ChipRecord([1.0, -1.0] * 2).margin > ChipRecord([1.0, -1.0] * 50).margin
    assert ChipRecord([0.5, 1.5]).bb_per_100 == 100


def test_chip_records_with_no_deals_are_zero():
    record = ChipRecord()
    assert record.bb_per_100 == 0
    assert record.margin == float("inf")
    assert CashResults({"A": record}).ranked() == [("A", record)]
