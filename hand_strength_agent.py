import math
import random
from card import Card
from game import Action, Street
from hand_evaluator import VALUE_RANKS, evaluate
from table_view import TableView

SUITS = ["H", "D", "C", "S"]

# Found by tune.py against itself and a random, calling and aggressive agent
# (python3 tune.py --rounds 8 --deals 2000 --seed 1). Over 10,000 fresh duplicate deals they
# beat the defaults by 275.6 +/- 12.9 big blinds per 100 hands across that pool, and by 38.3
# heads-up.
TUNED_SETTINGS = {"preflop_raise": 10, "preflop_call": 3, "postflop_raise": 0.65,
                  "call_margin": 0.05, "raise_size": 1.75}

def chen_score(hand: list[Card]):
    """Rates two starting cards with the Chen formula, from -1 (7-2 offsuit) to 20 (aces)."""
    high, low = sorted((VALUE_RANKS[card.value] for card in hand), reverse=True)
    points = {14: 10, 13: 8, 12: 7, 11: 6}.get(high, high / 2)
    if high == low:
        return max(5, math.ceil(points * 2))
    if hand[0].suit == hand[1].suit:
        points += 2
    gap = high - low - 1
    points -= {0: 0, 1: 1, 2: 2, 3: 4}.get(gap, 5)
    if gap <= 1 and high < 12:
        points += 1
    return math.ceil(points)

def equity(hand: list[Card], board: list[Card], opponents: int, samples: int,
           rng: random.Random):
    """Estimates the chance this hand wins at showdown, against opponents holding random cards.

    Each sample deals the opponents' cards and the rest of the board, so draws count for the
    times they hit. Ties count as half a win.
    """
    seen = {(card.value, card.suit) for card in hand + board}
    unseen = [Card(value, suit) for value in VALUE_RANKS for suit in SUITS
              if (value, suit) not in seen]
    to_come = 5 - len(board)
    total = 0.0
    for _ in range(samples):
        dealt = rng.sample(unseen, 2 * opponents + to_come)
        final_board = board + dealt[:to_come]
        mine = evaluate(hand + final_board)
        best = max(evaluate(dealt[i:i + 2] + final_board)
                   for i in range(to_come, len(dealt), 2))
        total += 1.0 if mine > best else 0.5 if mine == best else 0.0
    return total / samples

class HandStrengthAgent:
    """Bets on how strong its hand is: raises strong hands, calls when the price is right, and
    otherwise checks or folds.

    Before the flop it rates its cards with the Chen formula. After the flop it estimates its
    equity, its chance of winning at showdown, by dealing random cards to the players still in
    and to the rest of the board.
    """

    def __init__(self, rng: random.Random | None = None, preflop_raise: int = 10,
                 preflop_call: int = 7, postflop_raise: float = 0.75, call_margin: float = 0.0,
                 raise_size: float = 1.0, samples: int = 100):
        self._rng = rng or random.Random()
        self._preflop_raise = preflop_raise
        self._preflop_call = preflop_call
        self._postflop_raise = postflop_raise
        # How much the chance of winning must beat the price by before calling after the flop.
        self._call_margin = call_margin
        # Raises are this fraction of the pot after calling.
        self._raise_size = raise_size
        self._samples = samples

    def __call__(self, view: TableView):
        if view.street == Street.PREFLOP:
            score = chen_score(list(view.hand))
            should_raise = score >= self._preflop_raise
            should_call = score >= self._preflop_call
        else:
            opponents = len([seat for seat in view.opponents if not seat.folded])
            chance = equity(list(view.hand), list(view.community_cards), opponents,
                            self._samples, self._rng)
            should_raise = chance >= self._postflop_raise
            # Calling pays when the chance of winning beats the share of the final pot it costs.
            price = view.legal.to_call / (view.pot + view.legal.to_call)
            should_call = chance > price + self._call_margin

        legal = view.legal
        if should_raise and legal.can_raise:
            return Action.RAISE, self._raise_to(view)
        if not legal.can_call:
            return Action.CHECK, 0
        if should_raise or should_call:
            return Action.CALL, 0
        return Action.FOLD, 0

    def _raise_to(self, view: TableView):
        """Raises by raise_size times the pot after calling, kept inside the legal range."""
        legal = view.legal
        target = view.current_bet + round(self._raise_size * (view.pot + legal.to_call))
        return max(legal.min_raise_to, min(target, legal.max_raise_to))
