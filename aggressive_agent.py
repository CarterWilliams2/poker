from game import Action
from table_view import TableView

class AggressiveAgent:
    """Raises the size of the pot whenever it can, whatever its cards, and calls when it can't.
    It never folds."""

    def __call__(self, view: TableView):
        legal = view.legal
        if legal.can_raise:
            target = view.current_bet + view.pot + legal.to_call
            return Action.RAISE, max(legal.min_raise_to, min(target, legal.max_raise_to))
        return (Action.CALL, 0) if legal.can_call else (Action.CHECK, 0)
