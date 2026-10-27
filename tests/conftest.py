import pytest
from card import Card
from game import Game
from player import Player
from table_view import TableView


def cards(text: str) -> list[Card]:
    """Builds cards from a string like "AH KS 10D"."""
    return [Card(token[:-1], token[-1]) for token in text.split()]


def stack_deck(game, text: str):
    """Makes the game's next shuffle leave the deck so cards come out in the order given."""
    order = cards(text)

    def shuffle():
        game._deck._cards = list(reversed(order))

    game._deck.shuffle_deck = shuffle


@pytest.fixture
def scripted():
    """Returns a get_action callback that replays a list of (Action, amount) pairs."""
    def make(actions):
        queue = list(actions)

        def get_action(player, game):
            return queue.pop(0)

        get_action.remaining = queue
        return get_action

    return make


# Three-handed with the button on A: B posts the small blind, C the big blind, and A acts
# first preflop. Cards are dealt A B C A B C, then burn + flop, burn + turn, burn + river.
THREE_HANDED_DECK = "AS KS 2C AH KH 7D 3D AD 9C 4S 5D JH 6D 8C"

# Marks the decision view_at stops at.
LOOK = None


class Stop(Exception):
    pass


def view_at(chips, actions, deck=THREE_HANDED_DECK):
    """Plays the actions up to the LOOK marker, with blinds of 5 and 10, and returns the view
    of whoever acts there."""
    queue = list(actions)
    views = []

    def get_action(player, game):
        action = queue.pop(0)
        if action is LOOK:
            views.append(TableView.for_player(player, game))
            raise Stop
        return action

    players = [Player(name, count) for name, count in zip("ABCDEF", chips)]
    game = Game(players, 5, 10, get_action)
    stack_deck(game, deck)
    with pytest.raises(Stop):
        game.play_hand()
    return views[0]
