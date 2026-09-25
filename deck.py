from card import Card
import random

class Deck:
    def __init__(self):
        self._cards: list[Card] = []
        self._make_deck()

    def reset_cards(self):
        self._make_deck()

    def _make_deck(self):
        self._cards = []
        for value in ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]:
            for suit in ["H", "D", "C", "S"]:
                self._cards.append(Card(value, suit))

    def shuffle_deck(self):
        random.shuffle(self._cards)

    def get_deck_size(self):
        return len(self._cards)

    def discard(self):
        self._cards.pop()

    def get_a_card(self):
        return self._cards.pop()
