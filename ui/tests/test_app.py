import random
from fastapi.testclient import TestClient
from server.app import app
from server.engine import Deck

client = TestClient(app)

RANKS = {"2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"}
SUITS = {"H", "D", "C", "S"}


def deal(**params):
    response = client.get("/api/deal", params=params)
    assert response.status_code == 200
    return response.json()


def test_deal_gives_two_hole_cards_and_a_five_card_board():
    cards = deal()
    assert len(cards["hand"]) == 2
    assert len(cards["board"]) == 5
    every_card = cards["hand"] + cards["board"]
    assert len(set(every_card)) == 7
    assert all(card[:-1] in RANKS and card[-1] in SUITS for card in every_card)


def test_the_same_seed_gives_the_same_deal():
    assert deal(seed=7) == deal(seed=7)
    assert deal(seed=7) != deal(seed=8)


def test_cards_come_off_the_engine_deck_in_order():
    deck = Deck(random.Random(7))
    deck.shuffle_deck()
    expected = [deck.get_a_card() for _ in range(7)]
    cards = deal(seed=7)
    assert cards["hand"] + cards["board"] == [card.value + card.suit for card in expected]
