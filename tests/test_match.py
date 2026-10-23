import random
import pytest
from conftest import stack_deck
from game import Action
from match import IllegalActionError, Match
from random_agent import RandomAgent

FOLD = (Action.FOLD, 0)


def always(action):
    return lambda player, game: action


def random_seats(count, seed=0):
    return [(f"Bot {i}", RandomAgent(random.Random(seed + i))) for i in range(count)]


@pytest.mark.parametrize("count", [1, 9])
def test_needs_two_to_eight_players(count):
    with pytest.raises(ValueError, match="2 to 8"):
        Match(random_seats(count), 100, 1, 2)


def test_names_must_be_different():
    with pytest.raises(ValueError, match="different name"):
        Match([("A", always(FOLD)), ("A", always(FOLD))], 100, 1, 2)


def test_each_seat_is_driven_by_its_own_agent():
    asked = []

    def agent(name, action):
        def act(player, game):
            asked.append((name, player.name))
            return action
        return act

    # Three-handed, A is on the button and acts first preflop: A folds, B folds, C wins.
    match = Match([("A", agent("a", FOLD)), ("B", agent("b", FOLD)), ("C", agent("c", FOLD))],
                  100, 1, 2)
    results = match.play_hand()
    assert asked == [("a", "A"), ("b", "B")]
    assert results == [(3, [match.players[2]])]
    assert match.hands_played == 1


def test_illegal_action_raises_instead_of_asking_forever():
    match = Match([("A", always((Action.CHECK, 0))), ("B", always(FOLD))], 100, 1, 2)
    with pytest.raises(IllegalActionError, match="A tried to check 0"):
        match.play_hand()


def test_on_action_sees_every_decision():
    seen = []
    match = Match([("A", always(FOLD)), ("B", always(FOLD))], 100, 1, 2,
                  on_action=lambda player, action, amount, game: seen.append((player.name, action)))
    match.play_hand()
    assert seen == [("A", Action.FOLD)]


@pytest.mark.parametrize("count", range(2, 9))
def test_random_bots_play_until_one_has_every_chip(count):
    match = Match(random_seats(count), 100, 1, 2)
    hands = []
    standings = match.run(on_hand=lambda number, results: hands.append(number))
    assert match.is_over()
    assert hands == list(range(1, match.hands_played + 1))
    assert standings[0].chips == 100 * count
    assert all(p.chips == 0 for p in standings[1:])
    assert standings[1:] == match.eliminated[::-1]


def test_max_hands_stops_early_and_ranks_by_chips():
    match = Match(random_seats(8), 1000, 1, 2)
    standings = match.run(max_hands=3)
    assert match.hands_played == 3
    alive = [p for p in standings if p.chips > 0]
    assert [p.chips for p in alive] == sorted((p.chips for p in alive), reverse=True)
    assert sum(p.chips for p in match.players) == 8000


def test_players_busted_in_the_same_hand_rank_by_starting_stack():
    # A and B both shove and C calls with the best hand; B started bigger, so B places higher.
    match = Match([("A", always((Action.RAISE, 10))), ("B", always((Action.RAISE, 20))),
                   ("C", always((Action.CALL, 0)))], 20, 1, 2)
    match.players[0]._chips = 10
    # Dealt A B C A B C, then burn + flop, burn + turn, burn + river.
    stack_deck(match.game, "2C 3D AS 7H 8S AH 4D KC KD QS 5S JC 6S 9H")
    match.play_hand()
    assert match.eliminated == [match.players[0], match.players[1]]
    assert match.standings() == [match.players[2], match.players[1], match.players[0]]
