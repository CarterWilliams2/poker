from enum import Enum
from typing import Callable
from player import Player
from deck import Deck

class Street(Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"

class Action(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"

class Game:
    def __init__(self, players: list[Player], small_blind: int, big_blind: int,
                 get_action: Callable[[Player, "Game"], tuple[Action, int]]):
        self._players = players
        self._deck = Deck()
        self._community_cards = []
        self._small_blind = small_blind
        self._big_blind = big_blind
        self._get_action = get_action
        self._dealer_index = -1
        self._seated: list[Player] = []
        self._street = Street.PREFLOP
        self._pot = 0
        self._current_bet = 0
        self._min_raise = big_blind

    @property
    def community_cards(self):
        return list(self._community_cards)

    @property
    def pot(self):
        return self._pot

    @property
    def current_bet(self):
        return self._current_bet

    @property
    def min_raise(self):
        return self._min_raise

    @property
    def street(self):
        return self._street

    def get_player_count(self):
        return len(self._players)

    def start_hand(self):
        self._move_button()
        rotated = self._players[self._dealer_index:] + self._players[:self._dealer_index]
        self._seated = [p for p in rotated if p.chips > 0]
        self._deck.reset_cards()
        self._deck.shuffle_deck()
        self._community_cards = []
        self._pot = 0
        self._street = Street.PREFLOP
        for player in self._players:
            player.start_new_hand()
        self._post_blinds()
        self.deal_to_all_players()

    def _move_button(self):
        count = len(self._players)
        for step in range(1, count + 1):
            index = (self._dealer_index + step) % count
            if self._players[index].chips > 0:
                self._dealer_index = index
                return

    def _small_blind_index(self):
        return 0 if len(self._seated) == 2 else 1

    def _post_blinds(self):
        small_blind_index = self._small_blind_index()
        self._pot += self._seated[small_blind_index].post_blind(self._small_blind)
        self._pot += self._seated[small_blind_index + 1].post_blind(self._big_blind)
        self._current_bet = self._big_blind
        self._min_raise = self._big_blind

    def shuffle_deck(self):
        self._deck.shuffle_deck()

    def _deal(self, player: Player):
        card = self._deck.get_a_card()
        player.add_card_to_hand(card)

    def deal_to_all_players(self):
        for _ in range(2):
            for player in self._seated:
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
