from player import Player
from deck import Deck

class Game:
    def __init__(self, players: list[Player]):
        self._players = players
        self._deck = Deck()
        self._community_cards = []

    @property
    def community_cards(self):
        return list(self._community_cards)

    def get_player_count(self):
        return len(self._players)

    def shuffle_deck(self):
        self._deck.shuffle_deck()

    def _deal(self, player: Player):
        card = self._deck.get_a_card()
        player.add_card_to_hand(card)

    def deal_to_all_players(self):
        for _ in range(2):
            for player in self._players:
                self._deal(player)

    def _burn_and_deal(self, count: int):
        self._deck.discard()
        for _ in range(count):
            card = self._deck.get_a_card()
            self._community_cards.append(card)

    def flop(self):
        self._burn_and_deal(3)

    def turn(self):
        self._burn_and_deal(1)

    def river(self):
        self._burn_and_deal(1)
