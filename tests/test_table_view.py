import dataclasses
import pytest
from card import Card
from game import Action, Game, Street
from player import Player
from table_view import ActionRecord, LegalActions, SeatView, TableView
from conftest import stack_deck

FOLD = (Action.FOLD, 0)
CHECK = (Action.CHECK, 0)
CALL = (Action.CALL, 0)
LOOK = None

# Three-handed with the button on A: B posts the small blind, C the big blind, and A acts
# first preflop. Cards are dealt A B C A B C, then burn + flop, burn + turn, burn + river.
DECK = "AS KS 2C AH KH 7D 3D AD 9C 4S 5D JH 6D 8C"


class Stop(Exception):
    pass


def view_at(chips, actions):
    """Plays the actions up to the LOOK marker and returns the view of whoever acts there."""
    queue = list(actions)
    views = []

    def get_action(player, game):
        action = queue.pop(0)
        if action is LOOK:
            views.append(TableView.for_player(player, game))
            raise Stop
        return action

    players = [Player(name, count) for name, count in zip("ABC", chips)]
    game = Game(players, 5, 10, get_action)
    stack_deck(game, DECK)
    with pytest.raises(Stop):
        game.play_hand()
    return views[0]


def names(cards):
    return [card.value + card.suit for card in cards]


def test_view_shows_own_cards_and_the_public_table():
    # A raises to 30, B calls, C folds, and B is first to act on the flop.
    view = view_at([100, 100, 100], [(Action.RAISE, 30), CALL, FOLD, LOOK])
    assert view.name == "B"
    assert names(view.hand) == ["KS", "KH"]
    assert names(view.community_cards) == ["AD", "9C", "4S"]
    assert (view.chips, view.committed_this_round, view.committed_this_hand) == (70, 0, 30)
    assert view.street == Street.FLOP
    assert (view.pot, view.current_bet, view.min_raise) == (70, 0, 10)
    assert (view.small_blind, view.big_blind) == (5, 10)
    assert view.button == "A"
    assert view.seats == (SeatView("A", 70, 0, 30, False), SeatView("B", 70, 0, 30, False),
                          SeatView("C", 90, 0, 10, True))
    assert [seat.name for seat in view.opponents] == ["A", "C"]
    assert view.history == (ActionRecord("A", Street.PREFLOP, Action.RAISE, 30),
                            ActionRecord("B", Street.PREFLOP, Action.CALL, 30),
                            ActionRecord("C", Street.PREFLOP, Action.FOLD, 0))
    assert view.legal == LegalActions(can_check=True, to_call=0, min_raise_to=10, max_raise_to=70)
    assert not view.legal.can_call
    assert view.legal.can_raise


def test_view_never_shows_other_players_cards_or_the_game():
    view = view_at([100, 100, 100], [(Action.RAISE, 30), CALL, CALL, LOOK])
    seen = []

    def walk(value):
        if isinstance(value, (Player, Game)):
            pytest.fail(f"view exposes {value!r}")
        if isinstance(value, Card):
            seen.append(value)
        elif dataclasses.is_dataclass(value):
            for field in dataclasses.fields(value):
                walk(getattr(value, field.name))
        elif isinstance(value, tuple):
            for item in value:
                walk(item)

    walk(view)
    assert sorted(names(seen)) == sorted(names(view.hand) + names(view.community_cards))


def test_view_cannot_be_changed():
    view = view_at([100, 100, 100], [LOOK])
    with pytest.raises(dataclasses.FrozenInstanceError):
        view.pot = 1000


def test_facing_a_bet_shows_the_call_and_raise_range():
    view = view_at([100, 100, 100], [(Action.RAISE, 30), LOOK])
    # B posted 5 of the 30, so calling takes 25 and the smallest raise is to 50.
    assert view.legal == LegalActions(can_check=False, to_call=25, min_raise_to=50, max_raise_to=100)
    assert view.legal.can_call


def test_short_stack_can_only_call_all_in():
    # C has 5 behind after the big blind: calling 30 is all-in for 5, and it can't raise.
    view = view_at([100, 100, 15], [(Action.RAISE, 30), FOLD, LOOK])
    assert view.legal == LegalActions(can_check=False, to_call=5, min_raise_to=None, max_raise_to=None)
    assert not view.legal.can_raise


def test_short_all_in_raise_is_the_whole_raise_range():
    # A has 15, so its only raise is all-in, short of the full raise to 20.
    view = view_at([15, 100, 100], [LOOK])
    assert (view.legal.min_raise_to, view.legal.max_raise_to) == (15, 15)


def test_all_in_seats_are_marked():
    # A raises and B calls all-in for 15, so C sees B as all-in.
    view = view_at([100, 15, 100], [(Action.RAISE, 30), CALL, LOOK])
    b = view.seats[1]
    assert (b.chips, b.all_in) == (0, True)
    assert not view.seats[0].all_in
    assert view.history[-1] == ActionRecord("B", Street.PREFLOP, Action.CALL, 15)


def test_folded_players_are_not_all_in():
    # B folds to an all-in raise, so it shows as folded, not all-in.
    view = view_at([100, 100, 100], [(Action.RAISE, 100), FOLD, LOOK])
    assert view.seats[1].folded and not view.seats[1].all_in


def test_history_starts_over_each_hand(scripted):
    players = [Player(name, 100) for name in "AB"]
    game = Game(players, 5, 10, scripted([FOLD]))
    game.play_hand()
    assert len(game.history) == 1
    game.start_hand()
    assert game.history == []
