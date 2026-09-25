from card import Card
class Player:
    def __init__(self, name, chips):
        self.name = name
        self.chips = chips
        self._hand: list[Card] = []
        self.current_bet = 0
        self.folded = False
    
    @property
    def hand(self):
        return list(self._hand)
    
    def fold(self):
        self.folded = True
        self._hand = []
        
    def addCardToHand(self, card: Card):
        self._hand.append(card)
