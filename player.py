class Player:
    def __init__(self, name, chips):
        self.name = name
        self.chips = chips
    
    def getChips(self):
        return self.chips
    
    def setChips(self, amount):
        self.chips = amount
    
    def bet(self, amount):
        currentChips = self.getChips()
        
        if amount > currentChips:
            self.setChips(0)
            return currentChips
        
        self.setChips(currentChips - amount)
        return amount