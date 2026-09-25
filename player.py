from card import Card
class Player:
    def __init__(self, name, chips):
        self.name = name
        self.chips = chips
        self.hand = None
        self.current_bet = None
    
    def getChips(self):
        return self.chips
    
    def getHand(self):
        return self.hand
    
    def getName(self):
        return self.name
    
    def getCurrentBet(self):
        return self.current_bet
    
    def setHand(self, hand: list[Card]):
        self.hand = hand
    
    def setChips(self, amount: int):
        self.chips = amount
    
    def setCurrentBet(self, amount: int):
        self.current_bet = amount
    
    def bet(self, amount: int):
        current_chips = self.getChips()
        
        if amount > current_chips:
            self.setChips(0)
            self.setCurrentBet(current_chips)
            return current_chips
        
        self.setChips(current_chips - amount)
        self.setCurrentBet(amount)
        return amount
    
    def goAllIn(self):
        all_chips = self.getChips()
        self.bet(all_chips)
        self.setCurrentBet(all_chips)
    
    def call(self, current_bet, call_amount):
        difference = call_amount - current_bet
        self.bet(difference)
    
    def raiseBet(self, current_bet, raised_amount):
        difference = raised_amount - current_bet
        self.bet(difference)