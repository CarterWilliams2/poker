import random
from dataclasses import dataclass, field
from typing import Callable
from agent import Agent
from aggressive_agent import AggressiveAgent
from calling_station_agent import CallingStationAgent
from hand_strength_agent import TIGHT_SETTINGS, TUNED_SETTINGS, HandStrengthAgent
from random_agent import RandomAgent

@dataclass(frozen=True)
class Bot:
    """A bot that can be picked by name. build makes one from its own random source, and
    settings are what it passes to its agent's class beyond that class's defaults."""
    description: str
    build: Callable[[random.Random], Agent]
    settings: dict = field(default_factory=dict)

def _strength_bot(description: str, settings: dict):
    return Bot(description, lambda rng: HandStrengthAgent(rng, **settings), dict(settings))

# Every bot by name, in the order they're listed to people choosing one. New bots get added here.
BOTS = {
    "random": Bot("Picks any legal move at random.", lambda rng: RandomAgent(rng)),
    "calling": Bot("Calls every bet and never raises or folds.", lambda rng: CallingStationAgent()),
    "aggressive": Bot("Raises the size of the pot whenever it can, and never folds.",
                      lambda rng: AggressiveAgent()),
    "strength": _strength_bot("Bets on how strong its hand is, with the default settings.", {}),
    "tuned": _strength_bot("Bets on how strong its hand is, with settings tuned against the "
                           "other bots.", TUNED_SETTINGS),
    "tight": _strength_bot("Plays only the strongest 11% of starting hands, and raises each one "
                           "before the flop.", TIGHT_SETTINGS),
}

# Each bot's build function by name, for code that only needs to make one.
AGENTS = {name: bot.build for name, bot in BOTS.items()}
