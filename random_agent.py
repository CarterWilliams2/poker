import random
from game import Game, Action
from player import Player

class RandomAgent:
    """Picks uniformly among its legal actions, and raises to a uniformly random legal total."""

    def __init__(self, rng: random.Random | None = None):
        self._rng = rng or random.Random()

    def __call__(self, player: Player, game: Game):
        all_in_total = player.committed_this_round + player.chips
        if game.current_bet > player.committed_this_round:
            choices = [Action.FOLD, Action.CALL]
        else:
            choices = [Action.CHECK]
        if game.is_legal(player, Action.RAISE, all_in_total):
            choices.append(Action.RAISE)

        action = self._rng.choice(choices)
        if action != Action.RAISE:
            return action, 0
        smallest = min(game.current_bet + game.min_raise, all_in_total)
        return action, self._rng.randint(smallest, all_in_total)
