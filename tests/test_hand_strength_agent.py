import dataclasses
import random
import pytest
from game import Action
from hand_strength_agent import TUNED_SETTINGS, HandStrengthAgent, chen_score, equity
from random_agent import RandomAgent
from simulation import CashSimulation
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


def test_equity_is_certain_with_an_unbeatable_hand():
    # Four aces on the turn: only a straight flush could beat them, and no card left makes one.
    assert equity(cards("AS AH"), cards("AD AC 4S 9H"), 3, 50, random.Random(0)) == 1


def test_equity_counts_ties_as_half():
    # Everyone plays the royal flush on the board.
    assert equity(cards("2C 3D"), cards("AS KS QS JS 10S"), 2, 50, random.Random(0)) == 0.5


def test_equity_drops_with_more_opponents():
    one = equity(cards("QS QH"), cards("2D 7C 8S"), 1, 200, random.Random(0))
    three = equity(cards("QS QH"), cards("2D 7C 8S"), 3, 200, random.Random(0))
    assert one > three


def test_equity_counts_draws():
    # Nine high with four hearts is behind almost every hand right now, but makes a flush on
    # about a third of turns and rivers, so its equity heads-up is well over that.
    assert equity(cards("9H 8H"), cards("2H 5H KC"), 1, 400, random.Random(0)) > 0.45


def test_a_missed_draw_is_worth_little_on_the_river():
    # The same draw once the turn and river have missed: just nine high, with nothing to come.
    river = cards("2H 5H KC JS 3D")
    assert equity(cards("9H 8H"), river, 1, 400, random.Random(0)) < 0.2


def test_a_raiser_with_a_strong_range_beats_an_overpair_far_more_often():
    # Queens on a low board are well ahead of random cards, but a raiser who only holds kings
    # or aces (a Chen score of 16 or more) has them crushed.
    board = cards("2D 7C 8S")
    anyone = equity(cards("QS QH"), board, 1, 300, random.Random(0))
    raiser = equity(cards("QS QH"), board, 1, 300, random.Random(0), raisers=1, raiser_floor=16)
    assert anyone > 0.75
    assert raiser < 0.25


def test_a_floor_of_minus_one_deals_raisers_anything():
    board = cards("2D 7C 8S")
    assert (equity(cards("QS QH"), board, 2, 100, random.Random(0), raisers=2, raiser_floor=-1)
            == equity(cards("QS QH"), board, 2, 100, random.Random(0)))


def test_a_raiser_gets_random_cards_once_its_range_runs_out():
    # Only aces score 20, and the four left make just two pairs of aces, so the third raiser
    # can never be dealt one and gets random cards instead. Kings rarely beat two pairs of aces.
    hand, board = cards("KS KH"), cards("2D 7C 8S")
    assert equity(hand, board, 3, 100, random.Random(0), raisers=3, raiser_floor=20) < 0.15
    assert equity(hand, board, 3, 100, random.Random(0)) > 0.5


def test_a_range_with_no_hands_left_deals_random_cards():
    # Three aces are out, so nobody can hold two: the raiser is dealt anything.
    hand, board = cards("AS AH"), cards("AD 7C 8S")
    assert (equity(hand, board, 1, 100, random.Random(0), raisers=1, raiser_floor=20)
            == equity(hand, board, 1, 100, random.Random(0)))


@pytest.mark.parametrize("actions, expected", [
    # Everyone limps, so nobody raised.
    ([CALL, CALL, CHECK, LOOK], 0),
    # A raises and B calls: A raised.
    ([(Action.RAISE, 30), CALL, FOLD, LOOK], 1),
    # B re-raises A and A calls. B is the one asking, so only A counts.
    ([(Action.RAISE, 30), (Action.RAISE, 90), FOLD, CALL, LOOK], 1),
    # A raises, C re-raises and A folds: a raiser who folded doesn't count.
    ([(Action.RAISE, 30), CALL, (Action.RAISE, 90), FOLD, CALL, LOOK], 1),
    # A and C both raise and both stay in.
    ([(Action.RAISE, 30), CALL, (Action.RAISE, 90), CALL, CALL, LOOK], 2),
])
def test_counts_opponents_still_in_who_raised_before_the_flop(monkeypatch, actions, expected):
    calls = []
    monkeypatch.setattr("hand_strength_agent.equity",
                        lambda *args: calls.append(args[5:]) or 0)
    decide([200, 200, 200], actions, raiser_floor=9)
    assert calls == [(expected, 9)]


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
    assert HandStrengthAgent(random.Random(0))._raise_to(view) == 20


def test_raise_size_scales_the_raise():
    # Half the pot after calling is 12.5, which rounds to 12 on top of the 10 to call.
    assert decide([100, 100, 100], [LOOK], raise_size=0.5) == (Action.RAISE, 22)


def test_raises_after_the_flop_with_a_strong_hand():
    # A flops a set of aces after B checks. The pot is 70 and A has 70 left, so it bets it all.
    actions = [(Action.RAISE, 30), CALL, FOLD, CHECK, LOOK]
    assert decide([100, 100, 100], actions) == (Action.RAISE, 70)


def test_calls_after_the_flop_when_the_price_is_right():
    # Everyone limps. On A 9 4, B bets 30 into 30: C needs a better than 1 in 3 chance to call,
    # and middle pair against two random hands is well above that, but short of raising.
    actions = [CALL, CALL, CHECK, (Action.RAISE, 30), LOOK]
    assert decide([100, 100, 100], actions, C_SUITED_CONNECTORS) == CALL


def test_call_margin_demands_a_better_price():
    # Middle pair's chance here is about 55%. Asking for 30 points more than the 1 in 3 price
    # turns the call into a fold.
    actions = [CALL, CALL, CHECK, (Action.RAISE, 30), LOOK]
    assert decide([100, 100, 100], actions, C_SUITED_CONNECTORS, call_margin=0.3) == FOLD


def test_folds_after_the_flop_when_the_price_is_wrong():
    # Same spot, but C has 7-2 and almost never has the best hand.
    actions = [CALL, CALL, CHECK, (Action.RAISE, 30), LOOK]
    assert decide([100, 100, 100], actions) == FOLD


def test_folded_players_do_not_count_as_opponents(monkeypatch):
    counts = []
    monkeypatch.setattr("hand_strength_agent.equity",
                        lambda hand, board, opponents, *rest: counts.append(opponents) or 0)
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
    record = CashSimulation(seats, 100, 1, 2, rng=random.Random(0)).run(80).records["Strength"]
    # Ahead by more than the margin of error, not just ahead.
    assert record.bb_per_100 - record.margin > 0


def test_uses_its_own_random_source_by_default():
    assert isinstance(HandStrengthAgent()._rng, random.Random)


def test_tuned_settings_build_an_agent():
    agent = HandStrengthAgent(random.Random(0), **TUNED_SETTINGS)
    assert agent._call_margin == TUNED_SETTINGS["call_margin"]
    assert agent._raise_size == TUNED_SETTINGS["raise_size"]
