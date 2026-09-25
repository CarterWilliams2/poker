from card import Card
class Player:
    def __init__(self, name, chips):
        self.name = name
        self._chips = chips
        self._hand: list[Card] = []
        self._committed_this_round = 0
        self.folded = False
    
    @property
    def hand(self):
        return list(self._hand)
    
    @property
    def chips(self):
        return self._chips

    
    def _pay(self, amount):
        amount = min(amount, self._chips)
        self.chips -= amount
        self._committed_this_round += amount
        
        return amount
    
    def fold(self):
        self.folded = True
        self._hand = []
    
    def call(self, table_bet):
        difference = table_bet - self._committed_this_round
        return self._pay(difference)
    
    def raise_to(self, new_total):
        difference = max(0, new_total - self._committed_this_round)
        return self._pay(difference)
        
    def add_card_to_hand(self, card: Card):
        self._hand.append(card)
