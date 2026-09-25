from card import Card
class Player:
    def __init__(self, name, chips):
        self.name = name
        self.chips = chips
        self._hand: list[Card] = []
        self.current_bet = None
    
    @property
    def hand(self):
        return list(self._hand)
    
    def bet(self, amount: int):
        if amount > self.chips:
            amount = self.chips
        
        self.chips -= amount
        self.current_bet = amount
        return amount
    
    def goAllIn(self):
        self.bet(self.chips)
    
    def call(self, current_bet: int, call_amount: int):
        difference = call_amount - current_bet
        self.bet(difference)
    
    def raiseBet(self, current_bet: int, raised_amount: int):
        difference = raised_amount - current_bet
        self.bet(difference)
        
    def addCardToHand(self, card: Card):
        self._hand.append(card)
