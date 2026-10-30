from game import Action
from table_view import TableView

class CallingStationAgent:
    """Never raises and never folds: calls any bet, and checks when there's nothing to call."""

    def __call__(self, view: TableView):
        return (Action.CALL, 0) if view.legal.can_call else (Action.CHECK, 0)
