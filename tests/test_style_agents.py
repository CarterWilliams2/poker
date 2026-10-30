from aggressive_agent import AggressiveAgent
from calling_station_agent import CallingStationAgent
from conftest import LOOK, view_at
from game import Action

CALL = (Action.CALL, 0)
FOLD = (Action.FOLD, 0)


def test_calling_station_calls_a_bet():
    assert CallingStationAgent()(view_at([100, 100, 100], [LOOK])) == CALL


def test_calling_station_checks_when_there_is_nothing_to_call():
    # A and B call, so the big blind C can check.
    assert CallingStationAgent()(view_at([100, 100, 100], [CALL, CALL, LOOK])) == (Action.CHECK, 0)


def test_aggressive_agent_raises_the_pot():
    # A faces the big blind of 10 with 15 in the pot: calling makes it 25, so it raises to 35.
    assert AggressiveAgent()(view_at([100, 100, 100], [LOOK])) == (Action.RAISE, 35)


def test_aggressive_agent_raise_is_capped_at_all_in():
    assert AggressiveAgent()(view_at([30, 100, 100], [LOOK])) == (Action.RAISE, 30)


def test_aggressive_agent_bets_the_pot_after_the_flop():
    # A calls, B folds and C checks, so C opens the flop with 25 in the pot.
    view = view_at([100, 100, 100], [CALL, FOLD, (Action.CHECK, 0), LOOK])
    assert AggressiveAgent()(view) == (Action.RAISE, 25)


def test_aggressive_agent_calls_when_it_cannot_raise():
    # Calling the big blind puts A all-in, so there's no raise left.
    assert AggressiveAgent()(view_at([10, 100, 100], [LOOK])) == CALL
