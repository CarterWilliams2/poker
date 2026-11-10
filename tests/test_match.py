import dataclasses
import random
import pytest
from conftest import THREE_HANDED_DECK, stack_deck
from game import Action, Street
from match import IllegalActionError, Match
from random_agent import RandomAgent
from table_view import ActionRecord, PotResult, SeatView

FOLD = (Action.FOLD, 0)


def always(action):
    return lambda view: action


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
        def act(view):
            asked.append((name, view.name))
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


class Recorder:
    """Plays a fixed action and keeps every HandResult it's given."""

    def __init__(self, action):
        self.action = action
        self.results = []

    def __call__(self, view):
        return self.action(view) if callable(self.action) else self.action

    def hand_over(self, result):
        self.results.append(result)


def names(cards):
    return " ".join(card.value + card.suit for card in cards)


def passive(view):
    return (Action.CALL, 0) if view.legal.can_call else (Action.CHECK, 0)


def test_hand_over_tells_every_player_dealt_in_how_a_folded_out_hand_went():
    # A is on the button and folds, B folds the small blind, and C wins without acting.
    agents = [Recorder(FOLD), Recorder(FOLD), Recorder(FOLD)]
    match = Match(list(zip("ABC", agents)), 100, 1, 2)
    match.play_hand()
    results = [agent.results for agent in agents]
    assert all(len(told) == 1 for told in results)
    assert [told[0].name for told in results] == ["A", "B", "C"]
    result = results[2][0]
    assert result.community_cards == ()
    assert result.seats == (SeatView("A", 100, 0, 0, True), SeatView("B", 99, 1, 1, True),
                            SeatView("C", 101, 2, 2, False))
    assert result.history == (ActionRecord("A", Street.PREFLOP, Action.FOLD, 0),
                              ActionRecord("B", Street.PREFLOP, Action.FOLD, 0))
    assert result.pots == (PotResult(3, ("C",)),)
    # Nobody called, so C never has to show.
    assert result.shown == {}
    assert result.won == {"A": 0, "B": -1, "C": 1}
    # Only the name changes from one player's result to the next.
    assert results[0][0] == dataclasses.replace(result, name="A")


def test_hand_over_shows_the_cards_of_everyone_still_in_at_the_showdown():
    # A folds, B completes the small blind, C checks, and both check down. B's kings beat C.
    agents = [Recorder(FOLD), Recorder(passive), Recorder(passive)]
    match = Match(list(zip("ABC", agents)), 100, 1, 2)
    stack_deck(match.game, THREE_HANDED_DECK)
    match.play_hand()
    result = agents[0].results[0]
    assert names(result.community_cards) == "AD 9C 4S JH 8C"
    # A folded, so A's aces stay hidden even at the showdown.
    assert {name: names(hand) for name, hand in result.shown.items()} == {"B": "KS KH",
                                                                         "C": "2C 7D"}
    assert result.pots == (PotResult(4, ("B",)),)
    assert result.won == {"A": 0, "B": 2, "C": -2}
    assert [seat.chips for seat in result.seats] == [100, 102, 98]


def test_hand_over_only_goes_to_players_dealt_in():
    agents = [Recorder(FOLD), Recorder(FOLD), Recorder(FOLD)]
    match = Match(list(zip("ABC", agents)), 100, 1, 2)
    match.players[0]._chips = 0
    match.play_hand()
    assert [len(agent.results) for agent in agents] == [0, 1, 1]
    assert [seat.name for seat in agents[1].results[0].seats] == ["B", "C"]


def test_hand_over_comes_once_per_hand_and_agents_without_it_still_play():
    recorder = Recorder(passive)
    match = Match([("A", recorder), ("B", RandomAgent(random.Random(1)))], 100, 1, 2,
                  rng=random.Random(2))
    match.run(max_hands=5)
    assert len(recorder.results) == match.hands_played
    # Every chip won is a chip someone else lost.
    assert all(sum(result.won.values()) == 0 for result in recorder.results)


def test_hand_over_lists_a_split_pots_winners_with_the_odd_chip_first():
    # A limps, B folds the small blind and C checks, so the pot is 5. The board is a royal flush
    # both play, and C, first left of the button, takes the odd chip.
    agents = [Recorder(passive), Recorder(FOLD), Recorder(passive)]
    match = Match(list(zip("ABC", agents)), 100, 1, 2)
    stack_deck(match.game, "2C 4C 6C 3D 5D 7D 8H AS KS QS 9H JS 8D 10S")
    match.play_hand()
    result = agents[0].results[0]
    assert result.pots == (PotResult(5, ("C", "A")),)
    assert result.won == {"A": 0, "B": -1, "C": 1}
