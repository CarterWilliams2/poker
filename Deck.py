from Card import Card
import random

class Deck:
    def __init__(self):
        self.cards = self.makeDeck()
            
    def getCards(self):
        return self.cards
    
    def setCards(self, cards: list[Card]):
        self.cards = cards
    
    def resetCards(self, cards: list[Card]):
        self.cards = cards
    
    def makeDeck(self):
        cards = []
        for value in ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]:
            for suit in ["H", "D", "C", "S"]:
                card = Card(value, suit)
                cards.append(card)
        
        self.setCards(cards)

    def shuffleDeck(self):
        shuffled_deck = random.shuffle(self.getCards())
        self.setCards(shuffled_deck)
    
    def getDeckSize(self):
        return self.cards.len()
    
    def discard(self):
        cards = self.getCards()
        cards.pop()
        self.setCards(cards)
    
    def getACard(self):
        cards = self.getCards()
        card = cards.pop()
        self.setCards(cards)
        
        return card
        