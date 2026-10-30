import random
import statistics
from dataclasses import dataclass, field
from typing import Callable
from agent import Agent
from simulation import CashSimulation, ChipRecord

# The name a trial gives to the head-to-head game between the challenger and the current best.
HEAD_TO_HEAD = "head-to-head"

@dataclass(frozen=True)
class Parameter:
    """One setting the tuner may change, by step at a time, staying between low and high."""
    name: str
    step: float
    low: float
    high: float

@dataclass(frozen=True)
class Trial:
    """One challenger tried against the current best settings. bb_per_100 and margin are the
    challenger's edge over the current best, averaged over every opponent, so a positive
    bb_per_100 means the challenger did better. by_opponent breaks the edge down by opponent."""
    round: int
    settings: dict
    bb_per_100: float
    margin: float
    by_opponent: dict[str, float] = field(default_factory=dict)

    @property
    def accepted(self):
        """Whether the challenger won by more than the margin of error."""
        return self.bb_per_100 - self.margin > 0

class Tuner:
    """Improves an agent's settings by playing them against each other and against a pool of
    other agents.

    Each round, every parameter is nudged up and then down by its step, and the nudged agent is
    measured against the current best over duplicate deals: once heads-up against it, and once
    against each opponent in the pool, where both play the same deals and the edge is how many
    more chips the challenger won. A change is kept only when its edge, averaged over all of
    these, beats the 95% margin of error, so luck rarely moves the settings and settings that
    only beat copies of themselves don't get kept. Tuning stops when a round keeps nothing, or
    after the given number of rounds.

    make_agent builds an agent from a settings dict and its own random source. opponents maps
    each pool opponent's name to a function building it from its own random source.
    """

    def __init__(self, make_agent: Callable[[dict, random.Random], Agent],
                 parameters: list[Parameter], deals: int,
                 opponents: dict[str, Callable[[random.Random], Agent]] | None = None,
                 starting_chips: int = 100, small_blind: int = 1, big_blind: int = 2,
                 rng: random.Random | None = None):
        self._make_agent = make_agent
        self._parameters = parameters
        self._deals = deals
        self._opponents = opponents or {}
        self._starting_chips = starting_chips
        self._small_blind = small_blind
        self._big_blind = big_blind
        self._rng = rng or random.Random()

    def tune(self, settings: dict, rounds: int, on_trial: Callable[[Trial], None] | None = None):
        """Returns the best settings found, starting from settings."""
        best = dict(settings)
        for number in range(1, rounds + 1):
            improved = False
            for parameter in self._parameters:
                for direction in (1, -1):
                    value = best[parameter.name] + direction * parameter.step
                    # Rounding keeps steps like 0.05 from drifting to 0.7999999.
                    value = round(min(parameter.high, max(parameter.low, value)), 6)
                    if value == best[parameter.name]:
                        continue
                    trial = self.compare(number, {**best, parameter.name: value}, best)
                    if on_trial:
                        on_trial(trial)
                    if trial.accepted:
                        best = trial.settings
                        improved = True
                        break
            if not improved:
                break
        return best

    def compare(self, number: int, challenger: dict, current: dict):
        """Measures challenger against current, heads-up and through the pool, and returns the
        challenger's result."""
        edges = {HEAD_TO_HEAD: self._play(challenger, current)}
        for name, make_opponent in self._opponents.items():
            # Both sides play the same deals against the same opponent, so the cards cancel out.
            seeds = [self._rng.random() for _ in range(3)]
            mine = self._play(challenger, make_opponent, seeds)
            theirs = self._play(current, make_opponent, seeds)
            edges[name] = [a - b for a, b in zip(mine, theirs)]
        # Each deal's edge is averaged over every opponent, so the margin counts them all.
        record = ChipRecord([statistics.fmean(deal) for deal in zip(*edges.values())])
        by_opponent = {name: ChipRecord(deals).bb_per_100 for name, deals in edges.items()}
        return Trial(number, challenger, record.bb_per_100, record.margin, by_opponent)

    def _play(self, settings: dict, opponent: dict | Callable[[random.Random], Agent],
              seeds: list[float] | None = None):
        """Plays settings heads-up against opponent, settings for another copy of the agent or a
        function building one, and returns what settings won on each deal, in big blinds."""
        seeds = seeds or [self._rng.random() for _ in range(3)]
        other = (self._make_agent(opponent, random.Random(seeds[1])) if isinstance(opponent, dict)
                 else opponent(random.Random(seeds[1])))
        seats = [("Challenger", self._make_agent(settings, random.Random(seeds[0]))),
                 ("Opponent", other)]
        simulation = CashSimulation(seats, self._starting_chips, self._small_blind,
                                    self._big_blind, rng=random.Random(seeds[2]))
        return simulation.run(self._deals).records["Challenger"].deals
