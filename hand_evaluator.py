from collections import Counter
from enum import IntEnum
from itertools import combinations
from card import Card

VALUE_RANKS = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
               "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14}

class HandRank(IntEnum):
    HIGH_CARD = 0
    PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8

def _straight_high(values: list[int]):
    ranks = sorted(set(values), reverse=True)
    if len(ranks) != 5:
        return None
    if ranks[0] - ranks[4] == 4:
        return ranks[0]
    if ranks == [14, 5, 4, 3, 2]:
        return 5
    return None

def score_five(cards: list[Card]) -> tuple:
    values = [VALUE_RANKS[card.value] for card in cards]
    counts = Counter(values)
    grouped = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    tiebreak = tuple(value for value, _ in grouped)
    shape = sorted(counts.values(), reverse=True)
    is_flush = len({card.suit for card in cards}) == 1
    straight_high = _straight_high(values)

    if straight_high is not None and is_flush:
        return (HandRank.STRAIGHT_FLUSH, straight_high)
    if shape == [4, 1]:
        return (HandRank.FOUR_OF_A_KIND, *tiebreak)
    if shape == [3, 2]:
        return (HandRank.FULL_HOUSE, *tiebreak)
    if is_flush:
        return (HandRank.FLUSH, *tiebreak)
    if straight_high is not None:
        return (HandRank.STRAIGHT, straight_high)
    if shape == [3, 1, 1]:
        return (HandRank.THREE_OF_A_KIND, *tiebreak)
    if shape == [2, 2, 1]:
        return (HandRank.TWO_PAIR, *tiebreak)
    if shape == [2, 1, 1, 1]:
        return (HandRank.PAIR, *tiebreak)
    return (HandRank.HIGH_CARD, *tiebreak)

def evaluate(cards: list[Card]) -> tuple:
    return max(score_five(list(combo)) for combo in combinations(cards, 5))

def hand_name(score: tuple):
    return HandRank(score[0]).name.replace("_", " ").title()
