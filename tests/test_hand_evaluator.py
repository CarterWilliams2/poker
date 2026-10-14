import pytest
from hand_evaluator import HandRank, evaluate, hand_name, score_five
from conftest import cards


@pytest.mark.parametrize("hand, expected", [
    ("AS KS QS JS 10S", (HandRank.STRAIGHT_FLUSH, 14)),
    ("5D 4D 3D 2D AD", (HandRank.STRAIGHT_FLUSH, 5)),
    ("9C 9D 9H 9S 2C", (HandRank.FOUR_OF_A_KIND, 9, 2)),
    ("3C 3D 3H KS KC", (HandRank.FULL_HOUSE, 3, 13)),
    ("AH 10H 7H 4H 2H", (HandRank.FLUSH, 14, 10, 7, 4, 2)),
    ("9C 8D 7H 6S 5C", (HandRank.STRAIGHT, 9)),
    ("AC 2D 3H 4S 5C", (HandRank.STRAIGHT, 5)),
    ("7C 7D 7H KS 2C", (HandRank.THREE_OF_A_KIND, 7, 13, 2)),
    ("JC JD 4H 4S AC", (HandRank.TWO_PAIR, 11, 4, 14)),
    ("QC QD 9H 4S 2C", (HandRank.PAIR, 12, 9, 4, 2)),
    ("AC QD 9H 4S 2C", (HandRank.HIGH_CARD, 14, 12, 9, 4, 2)),
    ("AC KD QH JS 9C", (HandRank.HIGH_CARD, 14, 13, 12, 11, 9)),
])
def test_score_five(hand, expected):
    assert score_five(cards(hand)) == expected


def test_higher_kicker_wins():
    assert score_five(cards("QC QD AH 4S 2C")) > score_five(cards("QH QS KH 4D 2D"))


def test_evaluate_picks_the_best_five_of_seven():
    score = evaluate(cards("2C 3D 4H 5S 6C KD KH"))
    assert score == (HandRank.STRAIGHT, 6)


@pytest.mark.parametrize("rank, name", [
    (HandRank.STRAIGHT_FLUSH, "Straight Flush"),
    (HandRank.HIGH_CARD, "High Card"),
])
def test_hand_name(rank, name):
    assert hand_name((rank, 14)) == name
