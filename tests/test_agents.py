import random
import pytest
from agents import AGENTS, BOTS
from aggressive_agent import AggressiveAgent
from calling_station_agent import CallingStationAgent
from hand_strength_agent import TIGHT_SETTINGS, TUNED_SETTINGS, HandStrengthAgent
from match import Match
from random_agent import RandomAgent

# The UI lists bots in this order and seats the first ones by default, so the order matters.
NAMES = ["random", "calling", "aggressive", "strength", "tuned", "tight"]


def test_bots_are_listed_in_order():
    assert list(BOTS) == NAMES


def test_agents_builds_each_bot_by_the_same_name():
    assert list(AGENTS) == NAMES
    assert all(AGENTS[name] is BOTS[name].build for name in NAMES)


@pytest.mark.parametrize("name, kind", [
    ("random", RandomAgent),
    ("calling", CallingStationAgent),
    ("aggressive", AggressiveAgent),
    ("strength", HandStrengthAgent),
    ("tuned", HandStrengthAgent),
    ("tight", HandStrengthAgent),
])
def test_each_bot_builds_its_agent(name, kind):
    assert isinstance(BOTS[name].build(random.Random(1)), kind)


@pytest.mark.parametrize("name, settings", [
    ("random", {}),
    ("calling", {}),
    ("aggressive", {}),
    ("strength", {}),
    ("tuned", TUNED_SETTINGS),
    ("tight", TIGHT_SETTINGS),
])
def test_each_bot_lists_the_settings_it_builds_with(name, settings):
    assert BOTS[name].settings == settings


@pytest.mark.parametrize("name", ["tuned", "tight"])
def test_strength_bots_build_with_their_settings(name):
    agent = BOTS[name].build(random.Random(1))
    for setting, value in BOTS[name].settings.items():
        assert getattr(agent, f"_{setting}") == value


def test_changing_a_bots_settings_leaves_the_engines_alone():
    BOTS["tuned"].settings["preflop_raise"] = 99
    try:
        assert TUNED_SETTINGS["preflop_raise"] != 99
    finally:
        BOTS["tuned"].settings["preflop_raise"] = TUNED_SETTINGS["preflop_raise"]


@pytest.mark.parametrize("name", NAMES)
def test_each_bot_has_a_description(name):
    assert BOTS[name].description.endswith(".")


def play(names, seed):
    """Plays a short seeded match between the named bots and returns the final stacks."""
    rng = random.Random(seed)
    seats = [(f"{name} {i}", BOTS[name].build(random.Random(rng.random())))
             for i, name in enumerate(names)]
    match = Match(seats, 100, 1, 2, rng=random.Random(rng.random()))
    match.run(max_hands=30)
    return [(player.name, player.chips) for player in match.players]


def test_every_bot_plays_only_legal_moves_and_repeats_with_a_seed():
    # Match raises IllegalActionError on an illegal move.
    first = play(NAMES, seed=3)
    assert first == play(NAMES, seed=3)
    assert sum(chips for _, chips in first) == 100 * len(NAMES)
