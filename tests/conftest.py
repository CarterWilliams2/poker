import pytest
from card import Card


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
