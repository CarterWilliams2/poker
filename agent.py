from typing import Protocol
from game import Action
from table_view import TableView

class Agent(Protocol):
    """Anything that can decide a player's action: a random bot, a scripted bot, or a future AI.

    It's called with a view of the table from the acting player's seat, and returns the action
    plus the total to raise to (0 for anything other than a raise). It must only return legal
    actions; view.legal says what those are.

    An agent may also have a hand_over(result) method. Match calls it after every hand the agent
    was dealt into, with a HandResult saying how the hand went and showing any cards turned
    over at the showdown, so the agent can learn how its opponents play.
    """

    def __call__(self, view: TableView) -> tuple[Action, int]: ...
