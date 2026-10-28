import random
from dataclasses import dataclass
from typing import Callable
from agent import Agent
from simulation import CashSimulation

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
    challenger's result, so a positive bb_per_100 means it won chips."""
    round: int
    settings: dict
    bb_per_100: float
    margin: float

    @property
    def accepted(self):
        """Whether the challenger won by more than the margin of error."""
        return self.bb_per_100 - self.margin > 0

class Tuner:
    """Improves an agent's settings by playing them against each other.

    Each round, every parameter is nudged up and then down by its step, and the nudged agent
    plays the current best heads-up over duplicate deals. A change is kept only when it wins
    by more than the 95% margin of error, so luck rarely moves the settings. Tuning stops when a
    round keeps nothing, or after the given number of rounds.

    make_agent builds an agent from a settings dict and its own random source.
    """

    def __init__(self, make_agent: Callable[[dict, random.Random], Agent],
                 parameters: list[Parameter], deals: int, starting_chips: int = 100,
                 small_blind: int = 1, big_blind: int = 2, rng: random.Random | None = None):
        self._make_agent = make_agent
        self._parameters = parameters
        self._deals = deals
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
        """Plays challenger against current heads-up and returns the challenger's result."""
        seats = [("Challenger", self._make_agent(challenger, random.Random(self._rng.random()))),
                 ("Current", self._make_agent(current, random.Random(self._rng.random())))]
        simulation = CashSimulation(seats, self._starting_chips, self._small_blind,
                                    self._big_blind, rng=random.Random(self._rng.random()))
        record = simulation.run(self._deals).records["Challenger"]
        return Trial(number, challenger, record.bb_per_100, record.margin)
