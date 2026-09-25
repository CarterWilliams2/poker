class Card:
    def __init__(self, value: str, suit: str):
        self.value = value
        self.suit = suit
    
    def toString(self):
        return self.value + " of " + self.suit
