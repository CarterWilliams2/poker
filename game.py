from enum import Enum
from typing import Callable
from player import Player
from deck import Deck
from hand_evaluator import evaluate

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

    def is_over(self):
        return len([p for p in self._players if p.chips > 0]) < 2

    def play_hand(self):
        self.start_hand()
        self._run_betting_round(self._preflop_first_index())
        for street, deal in [(Street.FLOP, self.flop), (Street.TURN, self.turn), (Street.RIVER, self.river)]:
            if self._count_in_hand() < 2:
                break
            self._street = street
            deal()
            self._start_betting_street()
            self._run_betting_round(1 % len(self._seated))
        self._street = Street.SHOWDOWN
        return self._award_pot()

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

    def _preflop_first_index(self):
        return (self._small_blind_index() + 2) % len(self._seated)

    def _post_blinds(self):
        small_blind_index = self._small_blind_index()
        self._pot += self._seated[small_blind_index].post_blind(self._small_blind)
        self._pot += self._seated[small_blind_index + 1].post_blind(self._big_blind)
        self._current_bet = self._big_blind
        self._min_raise = self._big_blind

    def _start_betting_street(self):
        self._current_bet = 0
        self._min_raise = self._big_blind
        for player in self._seated:
            player.start_new_round()

    def _can_act(self, player: Player):
        return not player.folded and player.chips > 0

    def _count_in_hand(self):
        return len([p for p in self._seated if not p.folded])

    def _run_betting_round(self, first_index: int):
        count = len(self._seated)
        order = [self._seated[(first_index + i) % count] for i in range(count)]
        to_act = [p for p in order if self._can_act(p)]
        while to_act and self._count_in_hand() > 1:
            player = to_act.pop(0)
            others_can_act = any(self._can_act(p) for p in self._seated if p is not player)
            if not others_can_act and player.committed_this_round >= self._current_bet:
                break
            if self._apply_action(player):
                position = order.index(player)
                after = order[position + 1:] + order[:position]
                to_act = [p for p in after if self._can_act(p)]

    def _is_legal(self, player: Player, action: Action, amount: int):
        if action == Action.CHECK:
            return player.committed_this_round == self._current_bet
        if action == Action.RAISE:
            all_in_total = player.committed_this_round + player.chips
            if amount > all_in_total or amount <= self._current_bet:
                return False
            return amount >= self._current_bet + self._min_raise or amount == all_in_total
        return True

    def _apply_action(self, player: Player):
        action, amount = self._get_action(player, self)
        while not self._is_legal(player, action, amount):
            action, amount = self._get_action(player, self)

        if action == Action.FOLD:
            player.fold()
        elif action == Action.CALL:
            self._pot += player.call(self._current_bet)
        elif action == Action.RAISE:
            self._min_raise = max(self._min_raise, amount - self._current_bet)
            self._current_bet = amount
            self._pot += player.raise_to(amount)
            return True
        return False

    def _award_pot(self):
        left_of_button = self._seated[1:] + self._seated[:1]
        winners = [p for p in left_of_button if not p.folded]
        if len(winners) > 1:
            scores = {p: evaluate(p.hand + self._community_cards) for p in winners}
            best = max(scores.values())
            winners = [p for p in winners if scores[p] == best]
        share, remainder = divmod(self._pot, len(winners))
        for player in winners:
            player.collect(share)
        winners[0].collect(remainder)
        self._pot = 0
        return winners

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
