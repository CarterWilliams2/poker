import random
import pytest
from game import Action, Game
from player import Player
from random_agent import RandomAgent

FOLD = (Action.FOLD, 0)
CALL = (Action.CALL, 0)
CHECK = (Action.CHECK, 0)


class FakeRng:
    """Records what the agent chose between and returns a fixed pick."""

    def __init__(self, pick=None):
        self.pick = pick
        self.choices = None
        self.range = None

    def choice(self, options):
        self.choices = list(options)
        return self.pick if self.pick is not None else options[0]

    def randint(self, low, high):
        self.range = (low, high)
        return high


class Stop(Exception):
    pass


def agent_decision(chips, actions_before, rng):
    """Plays the scripted actions, then asks the agent for the next one and returns it."""
    queue = list(actions_before)
    decisions = []

    def get_action(player, game):
        if queue:
            return queue.pop(0)
        decisions.append(RandomAgent(rng)(player, game))
        raise Stop

    players = [Player(name, count) for name, count in zip("ABCD", chips)]
    with pytest.raises(Stop):
        Game(players, 5, 10, get_action).play_hand()
    return decisions[0]


def test_facing_a_bet_can_fold_call_or_raise():
    rng = FakeRng(Action.FOLD)
    assert agent_decision([100, 100, 100], [], rng) == FOLD
    assert rng.choices == [Action.FOLD, Action.CALL, Action.RAISE]


def test_with_nothing_to_call_can_check_or_raise():
    # A and B call, so the big blind C has the option to check.
    rng = FakeRng(Action.CHECK)
    assert agent_decision([100, 100, 100], [CALL, CALL], rng) == CHECK
    assert rng.choices == [Action.CHECK, Action.RAISE]


def test_raise_is_a_random_total_between_the_minimum_raise_and_all_in():
    rng = FakeRng(Action.RAISE)
    assert agent_decision([100, 100, 100], [], rng) == (Action.RAISE, 100)
    assert rng.range == (20, 100)


def test_short_stack_raise_can_only_be_all_in():
    # A has 15: the minimum raise is to 20, so the only raise is all-in for 15.
    rng = FakeRng(Action.RAISE)
    assert agent_decision([15, 100, 100], [], rng) == (Action.RAISE, 15)
    assert rng.range == (15, 15)


def test_cannot_raise_when_calling_puts_it_all_in():
    rng = FakeRng()
    agent_decision([10, 100, 100], [], rng)
    assert rng.choices == [Action.FOLD, Action.CALL]


def test_cannot_raise_after_a_short_all_in_raise():
    # D raises to 30, A calls, B folds, C goes all-in for 35. That doesn't reopen betting for D,
    # even though A still has chips.
    rng = FakeRng()
    agent_decision([200, 200, 35, 200], [(Action.RAISE, 30), CALL, FOLD, (Action.RAISE, 35)], rng)
    assert rng.choices == [Action.FOLD, Action.CALL]


def test_cannot_raise_when_everyone_else_is_all_in():
    # C is all-in from the big blind and A folds, so B can only call or fold.
    rng = FakeRng()
    agent_decision([200, 200, 10], [FOLD], rng)
    assert rng.choices == [Action.FOLD, Action.CALL]


def test_random_agents_only_make_legal_actions_until_the_game_ends():
    agent = RandomAgent(random.Random(7))

    def checked(player, game):
        action, amount = agent(player, game)
        assert game.is_legal(player, action, amount)
        return action, amount

    players = [Player(name, 100) for name in "ABC"]
    game = Game(players, 5, 10, checked)
    hands = 0
    while not game.is_over() and hands < 500:
        game.play_hand()
        hands += 1
    assert sum(p.chips for p in players) == 300


def test_uses_its_own_random_source_by_default():
    rng = RandomAgent()._rng
    assert isinstance(rng, random.Random)
