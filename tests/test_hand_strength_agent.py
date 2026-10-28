import dataclasses
import random
import pytest
from game import Action
from hand_strength_agent import HandStrengthAgent, chen_score, hand_strength
from random_agent import RandomAgent
from simulation import Simulation
from conftest import LOOK, cards, view_at

FOLD = (Action.FOLD, 0)
CHECK = (Action.CHECK, 0)
CALL = (Action.CALL, 0)

# Like the default three-handed deck, but C holds 9S 8S, so it flops middle pair on A 9 4.
C_SUITED_CONNECTORS = "AS KS 9S AH KH 8S 3D AD 9C 4S 5D JH 6D 8C"


def decide(chips, actions, deck=None, **settings):
    """Asks a seeded agent what it would do at the LOOK marker."""
    view = view_at(chips, actions, deck) if deck else view_at(chips, actions)
    return HandStrengthAgent(random.Random(0), **settings)(view)


@pytest.mark.parametrize("hand, expected", [
    ("AS AH", 20),
    ("KS KH", 16),
    ("2S 2H", 5),
    ("AS KS", 12),
    ("AS KH", 10),
    ("JS 10S", 9),
    ("5S 4S", 6),
    ("QS 9H", 5),
    ("7S 2H", -1),
])
def test_chen_score(hand, expected):
    assert chen_score(cards(hand)) == expected


def test_hand_strength_is_certain_with_an_unbeatable_hand():
    assert hand_strength(cards("AS AH"), cards("AD AC 4S"), 3, 50, random.Random(0)) == 1


def test_hand_strength_counts_ties_as_half():
    # Everyone plays the royal flush on the board.
    assert hand_strength(cards("2C 3D"), cards("AS KS QS JS 10S"), 2, 50, random.Random(0)) == 0.5


def test_hand_strength_drops_with_more_opponents():
    one = hand_strength(cards("QS QH"), cards("2D 7C 8S"), 1, 200, random.Random(0))
    three = hand_strength(cards("QS QH"), cards("2D 7C 8S"), 3, 200, random.Random(0))
    assert one > three


def test_raises_a_strong_hand_by_the_pot():
    # A has aces and acts first: the pot is 15 and calling costs 10, so a pot raise is to 35.
    assert decide([100, 100, 100], [LOOK]) == (Action.RAISE, 35)


def test_folds_a_weak_hand_to_a_raise():
    # C has 7-2.
    assert decide([100, 100, 100], [(Action.RAISE, 30), CALL, LOOK]) == FOLD


def test_checks_a_weak_hand_when_it_is_free():
    # Everyone limps, so C, the big blind, can check 7-2.
    assert decide([100, 100, 100], [CALL, CALL, LOOK]) == CHECK


def test_calls_a_medium_hand_preflop():
    # C has 9-8 suited, a Chen score of 8: good enough to call, not to raise.
    assert decide([100, 100, 100], [(Action.RAISE, 30), CALL, LOOK], C_SUITED_CONNECTORS) == CALL


def test_calls_a_strong_hand_when_raising_is_not_allowed():
    # B has kings but only 15 chips, short of a raise over A's 30, so it calls all-in.
    assert decide([100, 15, 100], [(Action.RAISE, 30), LOOK]) == CALL


def test_raise_is_capped_at_all_in():
    # A has aces and 20 chips: a pot raise to 35 is more than it has.
    assert decide([20, 100, 100], [LOOK]) == (Action.RAISE, 20)


def test_raise_is_at_least_the_minimum():
    # Real pots are never this small, but a pot raise should still never fall below the
    # minimum raise to 20.
    view = dataclasses.replace(view_at([100, 100, 100], [LOOK]), pot=0)
    assert HandStrengthAgent(random.Random(0))._pot_sized_raise(view) == 20


def test_raises_after_the_flop_with_a_strong_hand():
    # A flops a set of aces after B checks. The pot is 70 and A has 70 left, so it bets it all.
    actions = [(Action.RAISE, 30), CALL, FOLD, CHECK, LOOK]
    assert decide([100, 100, 100], actions) == (Action.RAISE, 70)


def test_calls_after_the_flop_when_the_price_is_right():
    # Everyone limps. On A 9 4, B bets 30 into 30: C needs a better than 1 in 3 chance to call,
    # and middle pair against two random hands is well above that, but short of raising.
    actions = [CALL, CALL, CHECK, (Action.RAISE, 30), LOOK]
    assert decide([100, 100, 100], actions, C_SUITED_CONNECTORS) == CALL


def test_folds_after_the_flop_when_the_price_is_wrong():
    # Same spot, but C has 7-2 and almost never has the best hand.
    actions = [CALL, CALL, CHECK, (Action.RAISE, 30), LOOK]
    assert decide([100, 100, 100], actions) == FOLD


def test_folded_players_do_not_count_as_opponents(monkeypatch):
    counts = []
    monkeypatch.setattr("hand_strength_agent.hand_strength",
                        lambda hand, board, opponents, samples, rng: counts.append(opponents) or 0)
    # A raises, B calls and C folds, so on the flop B faces one opponent.
    decide([100, 100, 100], [(Action.RAISE, 30), CALL, FOLD, LOOK])
    assert counts == [1]


def test_settings_change_the_thresholds():
    # With a call threshold of 9, 9-8 suited (a Chen score of 8) folds to the raise instead.
    actions = [(Action.RAISE, 30), CALL, LOOK]
    assert decide([100, 100, 100], actions, C_SUITED_CONNECTORS, preflop_call=9) == FOLD


def test_beats_random_agents_heads_up():
    seats = [("Strength", HandStrengthAgent(random.Random(1), samples=30)),
             ("Random", RandomAgent(random.Random(2)))]
    results = Simulation(seats, 50, 1, 2, max_hands=300, rng=random.Random(0)).run(40)
    assert results.records["Strength"].wins > results.records["Random"].wins


def test_uses_its_own_random_source_by_default():
    assert isinstance(HandStrengthAgent()._rng, random.Random)
