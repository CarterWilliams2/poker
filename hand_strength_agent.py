import math
import random
from card import Card
from game import Action, Street
from hand_evaluator import VALUE_RANKS, evaluate
from table_view import TableView

SUITS = ["H", "D", "C", "S"]

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

def hand_strength(hand: list[Card], board: list[Card], opponents: int, samples: int,
                  rng: random.Random):
    """Estimates the chance this hand is best right now, against opponents holding random cards.

    It doesn't count cards still to come, so draws are worth nothing until they hit. Ties count
    as half a win.
    """
    seen = {(card.value, card.suit) for card in hand + board}
    unseen = [Card(value, suit) for value in VALUE_RANKS for suit in SUITS
              if (value, suit) not in seen]
    mine = evaluate(hand + board)
    total = 0.0
    for _ in range(samples):
        dealt = rng.sample(unseen, 2 * opponents)
        best = max(evaluate(dealt[i:i + 2] + board) for i in range(0, len(dealt), 2))
        total += 1.0 if mine > best else 0.5 if mine == best else 0.0
    return total / samples

class HandStrengthAgent:
    """Bets on how strong its hand is: raises strong hands, calls when the price is right, and
    otherwise checks or folds.

    Before the flop it rates its cards with the Chen formula. After the flop it estimates its
    chance of holding the best hand by dealing random cards to the players still in.
    """

    def __init__(self, rng: random.Random | None = None, preflop_raise: int = 10,
                 preflop_call: int = 7, postflop_raise: float = 0.75, samples: int = 100):
        self._rng = rng or random.Random()
        self._preflop_raise = preflop_raise
        self._preflop_call = preflop_call
        self._postflop_raise = postflop_raise
        self._samples = samples

    def __call__(self, view: TableView):
        if view.street == Street.PREFLOP:
            score = chen_score(list(view.hand))
            should_raise = score >= self._preflop_raise
            should_call = score >= self._preflop_call
        else:
            opponents = len([seat for seat in view.opponents if not seat.folded])
            strength = hand_strength(list(view.hand), list(view.community_cards), opponents,
                                     self._samples, self._rng)
            should_raise = strength >= self._postflop_raise
            # Calling pays when the chance of winning beats the share of the final pot it costs.
            should_call = strength > view.legal.to_call / (view.pot + view.legal.to_call)

        legal = view.legal
        if should_raise and legal.can_raise:
            return Action.RAISE, self._pot_sized_raise(view)
        if not legal.can_call:
            return Action.CHECK, 0
        if should_raise or should_call:
            return Action.CALL, 0
        return Action.FOLD, 0

    def _pot_sized_raise(self, view: TableView):
        """Raises by the size of the pot after calling, kept inside the legal range."""
        legal = view.legal
        target = view.current_bet + view.pot + legal.to_call
        return max(legal.min_raise_to, min(target, legal.max_raise_to))
