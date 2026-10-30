import itertools
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

# A tight opponent: raises the top 11% of starting hands (a Chen score of 8 or more) and folds
# everything else before the flop, so its raises really do mean a strong hand.
TIGHT_SETTINGS = {"preflop_raise": 8, "preflop_call": 8}

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

# Tries at dealing a raiser a hand from its range that doesn't clash with cards already dealt,
# before giving up and dealing it random cards.
RANGE_TRIES = 20

def equity(hand: list[Card], board: list[Card], opponents: int, samples: int,
           rng: random.Random, raisers: int = 0, raiser_floor: int = -1):
    """Estimates the chance this hand wins at showdown, against opponents holding random cards.

    Each sample deals the opponents' cards and the rest of the board, so draws count for the
    times they hit. Ties count as half a win. raisers of the opponents are dealt only
    starting hands with a Chen score of at least raiser_floor, since they raised before the
    flop. A floor of -1 lets them hold anything.
    """
    seen = {(card.value, card.suit) for card in hand + board}
    unseen = [Card(value, suit) for value in VALUE_RANKS for suit in SUITS
              if (value, suit) not in seen]
    to_come = 5 - len(board)
    in_range = []
    if raisers and raiser_floor > -1:
        in_range = [pair for pair in itertools.combinations(unseen, 2)
                    if chen_score(list(pair)) >= raiser_floor]
    total = 0.0
    for _ in range(samples):
        if in_range:
            dealt = _deal_with_ranges(unseen, in_range, raisers, 2 * opponents + to_come, rng)
        else:
            dealt = rng.sample(unseen, 2 * opponents + to_come)
        final_board = board + dealt[:to_come]
        mine = evaluate(hand + final_board)
        best = max(evaluate(dealt[i:i + 2] + final_board)
                   for i in range(to_come, len(dealt), 2))
        total += 1.0 if mine > best else 0.5 if mine == best else 0.0
    return total / samples

def _deal_with_ranges(unseen: list[Card], in_range: list[tuple[Card, Card]], raisers: int,
                      count: int, rng: random.Random):
    """Deals count cards like rng.sample would, laid out as the rest of the board followed by
    two cards per opponent, but with the last raisers pairs drawn from in_range."""
    taken: list[Card] = []
    for _ in range(raisers):
        for _ in range(RANGE_TRIES):
            pair = rng.choice(in_range)
            if pair[0] not in taken and pair[1] not in taken:
                taken.extend(pair)
                break
    rest = rng.sample([card for card in unseen if card not in taken], count - len(taken))
    return rest + taken

class HandStrengthAgent:
    """Bets on how strong its hand is: raises strong hands, calls when the price is right, and
    otherwise checks or folds.

    Before the flop it rates its cards with the Chen formula. After the flop it estimates its
    equity, its chance of winning at showdown, by dealing random cards to the players still in
    and to the rest of the board. Anyone still in who raised before the flop is only dealt
    starting hands with a Chen score of at least raiser_floor; the default of -1 lets them
    hold anything.
    """

    def __init__(self, rng: random.Random | None = None, preflop_raise: int = 10,
                 preflop_call: int = 7, postflop_raise: float = 0.75, call_margin: float = 0.0,
                 raise_size: float = 1.0, raiser_floor: int = -1, samples: int = 100):
        self._rng = rng or random.Random()
        self._preflop_raise = preflop_raise
        self._preflop_call = preflop_call
        self._postflop_raise = postflop_raise
        # How much the chance of winning must beat the price by before calling after the flop.
        self._call_margin = call_margin
        # Raises are this fraction of the pot after calling.
        self._raise_size = raise_size
        self._raiser_floor = raiser_floor
        self._samples = samples

    def __call__(self, view: TableView):
        if view.street == Street.PREFLOP:
            score = chen_score(list(view.hand))
            should_raise = score >= self._preflop_raise
            should_call = score >= self._preflop_call
        else:
            in_hand = {seat.name for seat in view.opponents if not seat.folded}
            raisers = {record.name for record in view.history if record.name in in_hand
                       and record.street == Street.PREFLOP and record.action == Action.RAISE}
            chance = equity(list(view.hand), list(view.community_cards), len(in_hand),
                            self._samples, self._rng, len(raisers), self._raiser_floor)
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
