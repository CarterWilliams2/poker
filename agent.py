from typing import Protocol
from game import Game, Action
from player import Player

class Agent(Protocol):
    """Anything that can decide a player's action: a random bot, a scripted bot, or a future AI.

    It's called with the player whose turn it is and the game, and returns the action plus the
    total to raise to (0 for anything other than a raise). It must only return legal actions.
    """

    def __call__(self, player: Player, game: Game) -> tuple[Action, int]: ...
