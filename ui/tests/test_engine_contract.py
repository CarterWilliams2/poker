"""Pins down the parts of the engine the UI relies on.

The UI workflow runs these on engine pull requests too, as the engine-contract job. A failure there
means the engine change breaks something the UI uses, and the failing test's name starts with the
engine name it pins. It warns the engine team without blocking the PR (rule 6 in the root
CLAUDE.md). If the change merges anyway, the UI team updates the UI code that relies on it, then
the test.

Every name server/engine.py exports is pinned by at least one test here, marked with @pins. When
you export a new name, add tests for the parts of it the UI uses.
"""
import random
import pytest
from server import engine
from server.engine import Card, Deck, evaluate, hand_name

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["H", "D", "C", "S"]

# The engine names the tests below pin, filled in by @pins as this file loads.
PINNED = set()


def pins(name):
    """Marks a test as pinning part of an engine name that server/engine.py exports."""
    def mark(test):
        PINNED.add(name)
        return test
    return mark


def cards(text):
    """Engine cards from a string like "AS 10H"."""
    return [Card(card[:-1], card[-1]) for card in text.split()]


def deal_all(seed):
    """Every card of a deck shuffled with this seed, as (value, suit), in the order dealt."""
    deck = Deck(random.Random(seed))
    deck.shuffle_deck()
    return [(card.value, card.suit) for card in (deck.get_a_card() for _ in range(52))]


def test_every_engine_name_the_ui_imports_is_pinned():
    assert PINNED == set(engine.__all__), "Pin each name in server/engine.py's __all__ with @pins"


@pins("Card")
def test_card_takes_a_value_and_a_suit_and_gives_them_back():
    # server/app.py writes a card as its value then its suit, like "10H".
    card = Card("10", "H")
    assert (card.value, card.suit) == ("10", "H")


@pins("Deck")
def test_deck_deals_all_52_cards_once_after_a_shuffle():
    # web/src/cards.ts can only draw these values and suits.
    dealt = deal_all(1)
    assert len(dealt) == 52
    assert set(dealt) == {(value, suit) for value in RANKS for suit in SUITS}


@pins("Deck")
def test_deck_shuffles_the_same_way_for_the_same_seed():
    # /api/deal?seed= relies on this to repeat a deal.
    assert deal_all(7) == deal_all(7)
    assert deal_all(7) != deal_all(8)


@pins("evaluate")
def test_evaluate_scores_the_better_of_two_hands_higher():
    # server/app.py scores two cards plus the board, and the highest score wins.
    board = cards("2C 7D 9H JS KC")
    assert evaluate(cards("AS AD") + board) > evaluate(cards("3H 4S") + board)


@pins("evaluate")
def test_evaluate_scores_hands_that_play_the_same_five_cards_the_same():
    # server/app.py calls hands with equal scores a tie.
    board = cards("10S JS QS KS AS")
    assert evaluate(cards("2H 3D") + board) == evaluate(cards("4C 5H") + board)


@pins("hand_name")
@pytest.mark.parametrize("seven_cards, name", [
    ("2C 5D 7H 9S JC KD 3H", "High Card"),
    ("2C 2D 7H 9S JC KD 3H", "Pair"),
    ("2C 2D 7H 7S JC KD 3H", "Two Pair"),
    ("2C 2D 2H 7S JC KD 3H", "Three Of A Kind"),
    ("4C 5D 6H 7S 8C KD 2H", "Straight"),
    ("2H 5H 9H JH KH 3C 4D", "Flush"),
    ("2C 2D 2H 7S 7C KD 3H", "Full House"),
    ("2C 2D 2H 2S 7C KD 3H", "Four Of A Kind"),
    ("5S 6S 7S 8S 9S KD 3H", "Straight Flush"),
])
def test_hand_name_gives_the_names_the_ui_shows(seven_cards, name):
    # The deal page shows each hand's name just as the engine gives it.
    assert hand_name(evaluate(cards(seven_cards))) == name
