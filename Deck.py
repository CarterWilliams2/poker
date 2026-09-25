from card import Card
import random

class Deck:
    def __init__(self):
        self.makeDeck()
    
    def resetCards(self):
        self.makeDeck()
    
    def makeDeck(self):
        self._cards: list[Card] = []
        for value in ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]:
            for suit in ["H", "D", "C", "S"]:
                self._cards.append(Card(value, suit))

    def shuffleDeck(self):
        random.shuffle(self._cards)
    
    def getDeckSize(self):
        return len(self._cards)
    
    def discard(self):
        self._cards.pop()
    
    def getACard(self):
        return self._cards.pop()
