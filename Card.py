class Card:
    def __init__(self, value: str, suit: str):
        self.value = value
        self.suit = suit

    def getValue(self):
        return self.value
    
    def getSuit(self):
        return self.suit
    
    def toString(self):
        res = self.getValue() + " of " + self.getSuit()
        return res