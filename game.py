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
        # The bet each player faced after their last action this round. A raise only reopens
        # betting for a player once the bet has gone up by at least a full raise since then.
        self._bet_after_acting: dict[Player, int] = {}
        # Every decision made this hand, in order, as (player, street, action, amount). The amount
        # is the player's total bet this round after a call or raise, and 0 for a check or fold.
        self._history: list[tuple[Player, Street, Action, int]] = []

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

    @property
    def small_blind(self):
        return self._small_blind

    @property
    def big_blind(self):
        return self._big_blind

    @property
    def seated(self):
        """Players dealt into this hand, starting from the button."""
        return list(self._seated)

    @property
    def history(self):
        return list(self._history)

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
        self._history = []
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
        self._bet_after_acting = {}
        while to_act and self._count_in_hand() > 1:
            player = to_act.pop(0)
            others_can_act = any(self._can_act(p) for p in self._seated if p is not player)
            if not others_can_act and player.committed_this_round >= self._current_bet:
                break
            if self._apply_action(player):
                position = order.index(player)
                after = order[position + 1:] + order[:position]
                to_act = [p for p in after if self._can_act(p)]

    def is_legal(self, player: Player, action: Action, amount: int):
        if action == Action.CHECK:
            return player.committed_this_round == self._current_bet
        if action == Action.RAISE:
            # Once everyone else is all-in or folded, nobody could call a raise.
            if not any(self._can_act(p) for p in self._seated if p is not player):
                return False
            bet_after_acting = self._bet_after_acting.get(player)
            if bet_after_acting is not None and self._current_bet - bet_after_acting < self._min_raise:
                return False
            all_in_total = player.committed_this_round + player.chips
            if amount > all_in_total or amount <= self._current_bet:
                return False
            return amount >= self._current_bet + self._min_raise or amount == all_in_total
        return True

    def _apply_action(self, player: Player):
        action, amount = self._get_action(player, self)
        while not self.is_legal(player, action, amount):
            action, amount = self._get_action(player, self)

        raised = False
        if action == Action.FOLD:
            player.fold()
        elif action == Action.CALL:
            self._pot += player.call(self._current_bet)
        elif action == Action.RAISE:
            self._min_raise = max(self._min_raise, amount - self._current_bet)
            self._current_bet = amount
            self._pot += player.raise_to(amount)
            raised = True
        self._bet_after_acting[player] = self._current_bet
        total = player.committed_this_round if action in (Action.CALL, Action.RAISE) else 0
        self._history.append((player, self._street, action, total))
        return raised

    def _build_pots(self, in_hand: list[Player]):
        pots = []
        previous = 0
        for level in sorted({p.committed_this_hand for p in in_hand}):
            amount = sum(min(p.committed_this_hand, level) - min(p.committed_this_hand, previous)
                         for p in self._seated)
            eligible = [p for p in in_hand if p.committed_this_hand >= level]
            if amount > 0:
                pots.append((amount, eligible))
            previous = level
        # Chips folded players put in above every remaining player's total go to the last pot.
        leftover = self._pot - sum(amount for amount, _ in pots)
        last_amount, last_eligible = pots[-1]
        pots[-1] = (last_amount + leftover, last_eligible)
        return pots

    def _award_pot(self):
        left_of_button = self._seated[1:] + self._seated[:1]
        in_hand = [p for p in left_of_button if not p.folded]
        scores = {}
        if len(in_hand) > 1:
            scores = {p: evaluate(p.hand + self._community_cards) for p in in_hand}

        results = []
        for amount, eligible in self._build_pots(in_hand):
            winners = eligible
            if len(eligible) > 1:
                best = max(scores[p] for p in eligible)
                winners = [p for p in eligible if scores[p] == best]
            share, remainder = divmod(amount, len(winners))
            for player in winners:
                player.collect(share)
            winners[0].collect(remainder)
            results.append((amount, winners))
        self._pot = 0
        return results

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
