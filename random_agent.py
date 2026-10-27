import random
from game import Action
from table_view import TableView

class RandomAgent:
    """Picks uniformly among its legal actions, and raises to a uniformly random legal total."""

    def __init__(self, rng: random.Random | None = None):
        self._rng = rng or random.Random()

    def __call__(self, view: TableView):
        legal = view.legal
        choices = [Action.FOLD, Action.CALL] if legal.can_call else [Action.CHECK]
        if legal.can_raise:
            choices.append(Action.RAISE)

        action = self._rng.choice(choices)
        if action != Action.RAISE:
            return action, 0
        return action, self._rng.randint(legal.min_raise_to, legal.max_raise_to)
