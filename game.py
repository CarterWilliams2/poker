from player import Player
from deck import Deck

class Game:
    def __init__(self, players: list[Player]):
        self.players = players
        self.deck = Deck()
        
    def getPlayerCount(self):
        return self.players.len()
    
    def deal(self, player: Player):
        card = self.deck.getACard()
        player.addCardToHand(card)
    
    def dealToAllPlayers(self):
        for _ in range(2):
            for player in self.players:
                self.deal(self, player)
    