import random
from itertools import combinations
import pytest
from card import Card
from hand_evaluator import HandRank, VALUE_RANKS, evaluate, hand_name, score_five
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


@pytest.mark.parametrize("hand, expected", [
    # A flush and a straight in different cards aren't a straight flush.
    ("2H 5H 9H JH KH 10C QD", (HandRank.FLUSH, 13, 11, 9, 5, 2)),
    ("AH 2H 3H 4H 5H 6H KC", (HandRank.STRAIGHT_FLUSH, 6)),
    ("AD 2D 3D 4D 5D KC QC", (HandRank.STRAIGHT_FLUSH, 5)),
    # The best kicker for quads can come from a pair.
    ("9C 9D 9H 9S KC KD 2C", (HandRank.FOUR_OF_A_KIND, 9, 13)),
    # Two sets make a full house with the lower set as the pair.
    ("7C 7D 7H 4S 4C 4D AC", (HandRank.FULL_HOUSE, 7, 4)),
    ("7C 7D 7H 4S 4C KD KC", (HandRank.FULL_HOUSE, 7, 13)),
    # With three pairs, the third pair's rank can be the kicker.
    ("JC JD 8H 8S 5C 5D 2C", (HandRank.TWO_PAIR, 11, 8, 5)),
    ("AC KD QH JS 10C 9D 8H", (HandRank.STRAIGHT, 14)),
    ("AC 2D 3H 4S 5C KD KH", (HandRank.STRAIGHT, 5)),
    ("7C 7D 7H KS 2C 4D 9H", (HandRank.THREE_OF_A_KIND, 7, 13, 9)),
    ("QC QD 9H 4S 2C JD 3H", (HandRank.PAIR, 12, 11, 9, 4)),
    ("AC QD 9H 4S 2C 7D 3H", (HandRank.HIGH_CARD, 14, 12, 9, 7, 4)),
])
def test_evaluate_seven_cards(hand, expected):
    assert evaluate(cards(hand)) == expected


def test_evaluate_matches_scoring_every_five_card_combination():
    # Drawing from a few ranks and suits at a time makes rare hands like quads, straight
    # flushes and two sets common enough to check.
    rng = random.Random(0)
    for _ in range(3000):
        ranks = rng.sample(list(VALUE_RANKS), rng.randint(2, 13))
        suits = rng.sample("HDCS", rng.randint(1, 4))
        pool = [Card(value, suit) for value in ranks for suit in suits]
        if len(pool) < 5:
            continue
        hand = rng.sample(pool, rng.randint(5, min(7, len(pool))))
        best = max(score_five(list(combo)) for combo in combinations(hand, 5))
        assert evaluate(hand) == best


@pytest.mark.parametrize("rank, name", [
    (HandRank.STRAIGHT_FLUSH, "Straight Flush"),
    (HandRank.HIGH_CARD, "High Card"),
])
def test_hand_name(rank, name):
    assert hand_name((rank, 14)) == name
