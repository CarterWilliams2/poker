from player import Player
from deck import Deck

class Game:
    def __init__(self, players: list[Player]):
        self._players = players
        self._deck = Deck()
        self._communityCards = []

    @property
    def communityCards(self):
        return list(self._communityCards)

    def getPlayerCount(self):
        return len(self._players)

    def shuffleDeck(self):
        self._deck.shuffleDeck()

    def _deal(self, player: Player):
        card = self._deck.getACard()
        player.addCardToHand(card)

    def dealToAllPlayers(self):
        for _ in range(2):
            for player in self._players:
                self._deal(player)

    def _burnAndDeal(self, count: int):
        self._deck.discard()
        for _ in range(count):
            card = self._deck.getACard()
            self._communityCards.append(card)

    def flop(self):
        self._burnAndDeal(3)

    def turn(self):
        self._burnAndDeal(1)

    def river(self):
        self._burnAndDeal(1)
