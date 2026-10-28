import random
from deck import Deck


def _keys(deck):
    return [(c.value, c.suit) for c in deck._cards]


def test_new_deck_has_52_unique_cards():
    deck = Deck()
    assert deck.get_deck_size() == 52
    assert len(set(_keys(deck))) == 52


def test_get_a_card_and_discard_remove_from_the_top():
    deck = Deck()
    top = deck._cards[-1]
    assert deck.get_a_card() is top
    deck.discard()
    assert deck.get_deck_size() == 50


def test_reset_cards_restores_a_full_deck():
    deck = Deck()
    for _ in range(10):
        deck.get_a_card()
    deck.reset_cards()
    assert deck.get_deck_size() == 52


def test_shuffle_keeps_the_same_cards():
    deck = Deck()
    before = _keys(deck)
    deck.shuffle_deck()
    assert sorted(_keys(deck)) == sorted(before)


def test_the_same_seed_shuffles_the_same_way():
    first, second = Deck(random.Random(7)), Deck(random.Random(7))
    first.shuffle_deck()
    second.shuffle_deck()
    assert _keys(first) == _keys(second)
