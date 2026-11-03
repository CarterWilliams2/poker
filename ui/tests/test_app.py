import random
from fastapi.testclient import TestClient
from server.app import app, showdown
from server.engine import Card, Deck

client = TestClient(app)

RANKS = {"2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"}
SUITS = {"H", "D", "C", "S"}


def deal(**params):
    response = client.get("/api/deal", params=params)
    assert response.status_code == 200
    return response.json()


def every_card(dealt):
    """The cards of a deal in the order they came off the deck: both hands, then the board."""
    return [card for hand in dealt["hands"] for card in hand["cards"]] + dealt["board"]


def cards(text):
    """Engine cards from a string like "AS 10H"."""
    return [Card(card[:-1], card[-1]) for card in text.split()]


def names_and_wins(hands):
    return [(hand["name"], hand["wins"]) for hand in hands]


def test_deal_gives_two_hands_and_a_five_card_board():
    dealt = deal()
    assert [len(hand["cards"]) for hand in dealt["hands"]] == [2, 2]
    assert len(dealt["board"]) == 5
    assert len(set(every_card(dealt))) == 9
    assert all(card[:-1] in RANKS and card[-1] in SUITS for card in every_card(dealt))
    assert any(hand["wins"] for hand in dealt["hands"])


def test_the_same_seed_gives_the_same_deal():
    assert deal(seed=7) == deal(seed=7)
    assert deal(seed=7) != deal(seed=8)


def test_cards_come_off_the_engine_deck_in_order():
    deck = Deck(random.Random(7))
    deck.shuffle_deck()
    expected = [deck.get_a_card() for _ in range(9)]
    assert every_card(deal(seed=7)) == [card.value + card.suit for card in expected]


def test_the_best_hand_wins():
    hands = showdown([cards("AS AD"), cards("3H 4S")], cards("2C 7D 9H JS KC"))
    assert [hand["cards"] for hand in hands] == [["AS", "AD"], ["3H", "4S"]]
    assert names_and_wins(hands) == [("Pair", True), ("High Card", False)]


def test_a_kicker_can_beat_a_hand_with_the_same_name():
    hands = showdown([cards("QS 9H"), cards("AS 9D")], cards("KC KD 7H 4S 2C"))
    assert names_and_wins(hands) == [("Pair", False), ("Pair", True)]


def test_hands_that_tie_both_win():
    hands = showdown([cards("2H 3D"), cards("4C 5H")], cards("10S JS QS KS AS"))
    assert names_and_wins(hands) == [("Straight Flush", True), ("Straight Flush", True)]
