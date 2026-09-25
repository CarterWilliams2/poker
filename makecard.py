class Card:
    def __init__(self, value: str, suit: str):
        self._value = value
        self._suit = suit

    @property
    def value(self):
        return self._value

    @property
    def suit(self):
        return self._suit

    def toString(self):
        return self._value + " of " + self._suit
