import math
import random
import statistics
from dataclasses import dataclass, field
from typing import Callable
from agent import Agent
from match import Match

@dataclass
class AgentRecord:
    """How one agent did across every game it played."""
    wins: int = 0
    places: list[int] = field(default_factory=list)

    @property
    def games(self):
        return len(self.places)

    @property
    def win_rate(self):
        return self.wins / self.games if self.games else 0.0

    @property
    def average_place(self):
        return sum(self.places) / self.games if self.games else 0.0

@dataclass
class SimulationResults:
    records: dict[str, AgentRecord]
    games: int = 0
    # Games stopped by max_hands with two or more players tied for the chip lead, so nobody won.
    draws: int = 0
    hands: int = 0

    def ranked(self):
        """(name, record) pairs from most wins to fewest, then by best average place."""
        return sorted(self.records.items(), key=lambda item: (-item[1].wins, item[1].average_place))

class Simulation:
    """Plays many matches between the same agents and counts how often each one wins.

    The seating order rotates every game so no agent always starts on the button. A game
    stopped by max_hands is won by the chip leader, or is a draw if the lead is tied. rng
    shuffles every deck; pass a seeded one for repeatable results.
    """

    def __init__(self, seats: list[tuple[str, Agent]], starting_chips: int,
                 small_blind: int, big_blind: int, max_hands: int | None = None,
                 rng: random.Random | None = None):
        # Building one match up front checks the seats the same way every game will.
        Match(seats, starting_chips, small_blind, big_blind)
        self._seats = seats
        self._starting_chips = starting_chips
        self._small_blind = small_blind
        self._big_blind = big_blind
        self._max_hands = max_hands
        self._rng = rng or random.Random()

    def run(self, games: int, on_game: Callable[[int, Match], None] | None = None):
        results = SimulationResults({name: AgentRecord() for name, _ in self._seats})
        for number in range(games):
            shift = number % len(self._seats)
            seats = self._seats[shift:] + self._seats[:shift]
            match = Match(seats, self._starting_chips, self._small_blind, self._big_blind,
                          rng=self._rng)
            standings = match.run(self._max_hands)
            results.games += 1
            results.hands += match.hands_played
            for place, player in enumerate(standings, start=1):
                results.records[player.name].places.append(place)
            if len(standings) > 1 and standings[0].chips == standings[1].chips:
                results.draws += 1
            else:
                results.records[standings[0].name].wins += 1
            if on_game:
                on_game(number + 1, match)
        return results

@dataclass
class ChipRecord:
    """How many big blinds one agent won, one entry per deal. With duplicate deals, an entry is
    the average over every seat the agent played that deal from."""
    deals: list[float] = field(default_factory=list)

    @property
    def bb_per_100(self):
        """Big blinds won per 100 hands."""
        return 100 * statistics.fmean(self.deals) if self.deals else 0.0

    @property
    def margin(self):
        """Half the width of a 95% confidence interval around bb_per_100. Infinite with fewer
        than two deals, since there's nothing to measure the spread with."""
        if len(self.deals) < 2:
            return math.inf
        return 100 * 1.96 * statistics.stdev(self.deals) / math.sqrt(len(self.deals))

@dataclass
class CashResults:
    records: dict[str, ChipRecord]
    hands: int = 0

    def ranked(self):
        """(name, record) pairs from the most big blinds won to the fewest."""
        return sorted(self.records.items(), key=lambda item: -item[1].bb_per_100)

class CashSimulation:
    """Measures agents by the chips they win, like a cash game: every hand starts with fresh
    stacks of starting_chips, so a lucky early hand can't carry the rest.

    With duplicate on, each deal is replayed once per seat, rotating the agents so every agent
    gets every seat's cards and position. Good and bad cards then cancel out, and what's left
    is mostly skill. Without it, each deal is played once and the seating rotates between deals.
    """

    def __init__(self, seats: list[tuple[str, Agent]], starting_chips: int,
                 small_blind: int, big_blind: int, duplicate: bool = True,
                 rng: random.Random | None = None):
        # Checks the seats the same way every hand will.
        Match(seats, starting_chips, small_blind, big_blind)
        self._seats = seats
        self._starting_chips = starting_chips
        self._small_blind = small_blind
        self._big_blind = big_blind
        self._duplicate = duplicate
        self._rng = rng or random.Random()

    def run(self, deals: int, on_deal: Callable[[int], None] | None = None):
        results = CashResults({name: ChipRecord() for name, _ in self._seats})
        count = len(self._seats)
        for number in range(deals):
            # Every replay of a deal shuffles with the same seed, so gets the same cards.
            seed = self._rng.getrandbits(64)
            shifts = range(count) if self._duplicate else [number % count]
            won = {name: 0 for name, _ in self._seats}
            for shift in shifts:
                seats = self._seats[shift:] + self._seats[:shift]
                match = Match(seats, self._starting_chips, self._small_blind, self._big_blind,
                              rng=random.Random(seed))
                match.play_hand()
                results.hands += 1
                for player in match.players:
                    won[player.name] += player.chips - self._starting_chips
            for name, chips in won.items():
                results.records[name].deals.append(chips / self._big_blind / len(shifts))
            if on_deal:
                on_deal(number + 1)
        return results
