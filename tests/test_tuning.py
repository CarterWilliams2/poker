import random
import pytest
from game import Action
from tuning import Parameter, Trial, Tuner


def shover(view):
    if view.legal.can_raise:
        return Action.RAISE, view.legal.max_raise_to
    return Action.CALL, 0


def folder(view):
    return (Action.CHECK, 0) if view.legal.can_check else (Action.FOLD, 0)


def make_agent(settings, rng):
    """Folds at level 0 and shoves from level 1 up, so raising the level to 1 always wins."""
    return shover if settings["level"] >= 1 else folder


def run(start, rounds, parameter=Parameter("level", 1, 0, 1)):
    trials = []
    tuner = Tuner(make_agent, [parameter], deals=10, rng=random.Random(0))
    return tuner.tune(start, rounds, trials.append), trials


def test_keeps_a_change_that_wins_and_stops_when_nothing_helps():
    tuned, trials = run({"level": 0}, rounds=5)
    assert tuned == {"level": 1}
    # Round 1 keeps level 1. Round 2 can't go above the high of 1, tries 0, loses and stops.
    assert [(t.round, t.settings, t.accepted) for t in trials] == [
        (1, {"level": 1}, True),
        (2, {"level": 0}, False),
    ]
    assert trials[1].bb_per_100 < 0


def test_stops_after_the_last_round_even_while_improving():
    tuned, trials = run({"level": 0}, rounds=1, parameter=Parameter("level", 1, 0, 5))
    assert tuned == {"level": 1}
    assert len(trials) == 1


def test_a_tie_is_not_an_improvement():
    # Two folders just trade blinds, so neither direction ever wins.
    tuned, trials = run({"level": -3}, rounds=3, parameter=Parameter("level", 1, -5, -1))
    assert tuned == {"level": -3}
    assert [t.settings["level"] for t in trials] == [-2, -4]
    assert not any(t.accepted for t in trials)


def test_steps_do_not_drift():
    _, trials = run({"level": 0.7}, rounds=1, parameter=Parameter("level", 0.1, 0, 0.95))
    assert [t.settings["level"] for t in trials] == [0.8, 0.6]


def test_a_trial_is_accepted_only_beyond_the_margin():
    assert Trial(1, {}, 10.0, 5.0).accepted
    assert not Trial(1, {}, 10.0, 10.0).accepted
    assert not Trial(1, {}, -10.0, 5.0).accepted


def test_compare_works_without_a_seed():
    trial = Tuner(make_agent, [], deals=4).compare(3, {"level": 1}, {"level": 0})
    assert trial.round == 3
    assert trial.accepted


def test_tunes_without_reporting_trials():
    tuner = Tuner(make_agent, [Parameter("level", 1, 0, 1)], deals=4, rng=random.Random(1))
    assert tuner.tune({"level": 0}, rounds=2) == {"level": 1}


def calling(rng):
    return lambda view: (Action.CALL, 0) if view.legal.can_call else (Action.CHECK, 0)


def test_head_to_head_is_scored_even_without_a_pool():
    trial = Tuner(make_agent, [], deals=4, rng=random.Random(2)).compare(1, {"level": 1}, {"level": 0})
    assert list(trial.by_opponent) == ["head-to-head"]
    assert trial.by_opponent["head-to-head"] == trial.bb_per_100


def test_pool_edge_is_how_many_more_chips_the_challenger_wins_on_the_same_deals():
    # Against a folder, folding just trades blinds while shoving steals them, so the shover
    # gains in the pool too. The overall edge averages head-to-head and the pool.
    tuner = Tuner(make_agent, [], deals=10, opponents={"folder": lambda rng: folder},
                  rng=random.Random(3))
    trial = tuner.compare(1, {"level": 1}, {"level": 0})
    assert trial.by_opponent["folder"] > 0
    assert trial.bb_per_100 == pytest.approx(sum(trial.by_opponent.values()) / 2)
    assert trial.accepted


def test_a_change_that_only_beats_itself_can_be_outweighed_by_the_pool():
    # Shoving beats folding heads-up, but a calling station takes the shover's whole stack
    # whenever it has the better hand, so shoving can lose overall once the pool is counted.
    tuner = Tuner(make_agent, [], deals=200, opponents={"calling": calling},
                  rng=random.Random(4))
    trial = tuner.compare(1, {"level": 1}, {"level": 0})
    assert trial.by_opponent["head-to-head"] > 0
    assert set(trial.by_opponent) == {"head-to-head", "calling"}
    assert trial.bb_per_100 == pytest.approx(sum(trial.by_opponent.values()) / 2)
