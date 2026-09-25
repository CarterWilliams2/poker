from player import Player
from deck import Deck

class Game:
    def __init__(self, players: list[Player]):
        self.players = players
        self.deck = Deck()
        self.community_cards = []
        
    def getPlayerCount(self):
        return len(self.players)
    
    def deal(self, player: Player):
        card = self.deck.getACard()
        player.addCardToHand(card)
    
    def dealToAllPlayers(self):
        for _ in range(2):
            for player in self.players:
                self.deal(player)
    
    def flop(self):
        self.deck.discard()
        for _ in range(3):
            card = self.deck.getACard()
            self.community_cards.append(card)
    
    def turn(self):
        self.deck.discard()
        
        card = self.deck.getACard()
        self.community_cards.append(card)
    
    def river(self):
        self.deck.discard()
        
        card = self.deck.getACard()
        self.community_cards.append(card)