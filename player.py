from card import Card
class Player:
    def __init__(self, name, chips):
        self.name = name
        self._chips = chips
        self._hand: list[Card] = []
        self._current_bet = 0
        self.committed_this_round
        self.folded = False
    
    @property
    def hand(self):
        return list(self._hand)
    
    def _pay(self, amount):
        amount = min(amount, self.chips)
        self.chips -= amount
        self.committed_this_round += amount
    
    def fold(self):
        self.folded = True
        self._hand = []
        
    def addCardToHand(self, card: Card):
        self._hand.append(card)
