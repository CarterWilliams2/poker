from card import Card
class Player:
    def __init__(self, name, chips):
        self.name = name
        self._chips = chips
        self._hand: list[Card] = []
        self._committedThisRound = 0
        self.folded = False

    @property
    def hand(self):
        return list(self._hand)

    @property
    def chips(self):
        return self._chips


    def _pay(self, amount):
        amount = min(amount, self._chips)
        self._chips -= amount
        self._committedThisRound += amount

        return amount

    def fold(self):
        self.folded = True
        self._hand = []

    def call(self, tableBet):
        difference = tableBet - self._committedThisRound
        return self._pay(difference)

    def raiseTo(self, newTotal):
        difference = max(0, newTotal - self._committedThisRound)
        return self._pay(difference)

    def addCardToHand(self, card: Card):
        self._hand.append(card)

    def startNewRound(self):
        self._committedThisRound = 0

    def startNewHand(self):
        self.startNewRound()
        self.folded = False
        self._hand = []
