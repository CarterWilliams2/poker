from collections import Counter
from enum import IntEnum
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

def _best_straight_high(ranks: set[int]):
    """The top card of the highest straight among these ranks, or None. An ace also plays low."""
    if 14 in ranks:
        ranks = ranks | {1}
    for high in range(14, 4, -1):
        if all(rank in ranks for rank in range(high - 4, high + 1)):
            return high
    return None

def evaluate(cards: list[Card]) -> tuple:
    """Scores the best five-card hand among five to seven cards, the same as score_five would
    score it. Bigger scores are better hands.

    It works from rank counts and suits instead of scoring every five-card combination, which is
    many times faster. Hand strength estimates call it thousands of times a decision.
    """
    counts: dict[int, int] = {}
    by_suit: dict[str, list[int]] = {}
    for card in cards:
        value = VALUE_RANKS[card.value]
        counts[value] = counts.get(value, 0) + 1
        by_suit.setdefault(card.suit, []).append(value)

    flush = next((values for values in by_suit.values() if len(values) >= 5), None)
    if flush:
        high = _best_straight_high(set(flush))
        if high is not None:
            return (HandRank.STRAIGHT_FLUSH, high)

    # Ranks from the most copies to the fewest, then from high to low. Five cards always hold at
    # least two ranks.
    groups = sorted(counts, key=lambda value: (counts[value], value), reverse=True)
    top, top_count = groups[0], counts[groups[0]]
    second_count = counts[groups[1]]
    if top_count == 4:
        return (HandRank.FOUR_OF_A_KIND, top, max(groups[1:]))
    if top_count == 3 and second_count >= 2:
        return (HandRank.FULL_HOUSE, top, groups[1])
    if flush:
        return (HandRank.FLUSH, *sorted(flush, reverse=True)[:5])
    high = _best_straight_high(set(counts))
    if high is not None:
        return (HandRank.STRAIGHT, high)
    if top_count == 3:
        return (HandRank.THREE_OF_A_KIND, top, *sorted(groups[1:], reverse=True)[:2])
    if second_count == 2:
        return (HandRank.TWO_PAIR, top, groups[1], max(groups[2:]))
    if top_count == 2:
        return (HandRank.PAIR, top, *sorted(groups[1:], reverse=True)[:3])
    return (HandRank.HIGH_CARD, *sorted(groups, reverse=True)[:5])

def hand_name(score: tuple):
    return HandRank(score[0]).name.replace("_", " ").title()
