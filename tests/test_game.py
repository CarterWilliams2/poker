from game import Action, Game, Street
from player import Player
from conftest import stack_deck

FOLD = (Action.FOLD, 0)
CHECK = (Action.CHECK, 0)
CALL = (Action.CALL, 0)


def raise_to(amount):
    return (Action.RAISE, amount)


def make_game(chips, actions, scripted, deck=None):
    players = [Player(name, count) for name, count in zip("ABCDEF", chips)]
    get_action = scripted(actions)
    game = Game(players, 5, 10, get_action)
    if deck:
        stack_deck(game, deck)
    return game, players, get_action


# Three-handed with the button on A: B posts the small blind, C the big blind, and A acts
# first preflop. After the flop, B acts first. Cards are dealt A B C A B C, then
# burn + flop, burn + turn, burn + river.
THREE_HANDED_DECK = "AS KS 2C AH KH 7D 3D AD 9C 4S 5D JH 6D 8C"
CHECKS_TO_SHOWDOWN = [CALL, CALL, CHECK] + [CHECK] * 9


def test_new_game_state(scripted):
    game, _, _ = make_game([100, 100, 100], [], scripted)
    assert game.get_player_count() == 3
    assert game.community_cards == []
    assert game.pot == 0
    assert game.current_bet == 0
    assert game.min_raise == 10
    assert game.street == Street.PREFLOP
    assert not game.is_over()


def test_is_over_when_one_player_has_chips(scripted):
    game, _, _ = make_game([100, 0, 0], [], scripted)
    assert game.is_over()


def test_start_hand_posts_blinds_and_deals(scripted):
    game, (a, b, c), _ = make_game([100, 100, 100], [], scripted, THREE_HANDED_DECK)
    game.start_hand()
    assert game.pot == 15
    assert game.current_bet == 10
    assert (a.chips, b.chips, c.chips) == (100, 95, 90)
    assert [card.to_string() for card in a.hand] == ["A of S", "A of H"]
    assert all(len(p.hand) == 2 for p in (a, b, c))


def test_showdown_after_checking_down(scripted):
    game, (a, b, c), get_action = make_game([100, 100, 100], CHECKS_TO_SHOWDOWN, scripted,
                                            THREE_HANDED_DECK)
    results = game.play_hand()
    assert results == [(30, [a])]
    assert (a.chips, b.chips, c.chips) == (120, 90, 90)
    assert game.street == Street.SHOWDOWN
    assert [card.to_string() for card in game.community_cards] == \
        ["A of D", "9 of C", "4 of S", "J of H", "8 of C"]
    assert game.pot == 0
    assert get_action.remaining == []


def test_everyone_folds_preflop(scripted):
    game, (a, b, c), get_action = make_game([100, 100, 100], [FOLD, FOLD], scripted)
    assert game.play_hand() == [(15, [c])]
    assert (a.chips, b.chips, c.chips) == (100, 95, 105)
    assert game.community_cards == []
    assert get_action.remaining == []


def test_illegal_actions_are_asked_again(scripted):
    actions = [
        CHECK,            # can't check facing the big blind
        raise_to(15),     # below the minimum raise of 20
        raise_to(1000),   # more than A has
        raise_to(10),     # not above the current bet
        raise_to(20),
        FOLD,             # B
        CALL,             # C
        FOLD,             # C on the flop
    ]
    game, (a, b, c), get_action = make_game([100, 100, 100], actions, scripted)
    assert game.play_hand() == [(45, [a])]
    assert (a.chips, b.chips, c.chips) == (125, 95, 80)
    assert len(game.community_cards) == 3
    assert get_action.remaining == []


def test_raise_reopens_action_and_sets_min_raise(scripted):
    seen = []
    actions = [CALL, raise_to(30), CALL, CALL, FOLD, FOLD]

    def record(player, game):
        seen.append((player.name, game.current_bet, game.min_raise))
        return actions.pop(0)

    game = Game([Player(n, 100) for n in "ABC"], 5, 10, record)
    game.play_hand()
    assert seen == [("A", 10, 10), ("B", 10, 10), ("C", 30, 20), ("A", 30, 20),
                    ("B", 0, 10), ("C", 0, 10)]


def test_short_all_in_raise_is_legal(scripted):
    # A has 25: raising to 25 is less than a full raise but is allowed because it's all-in.
    actions = [raise_to(25), FOLD, FOLD]
    game, (a, b, c), _ = make_game([25, 100, 100], actions, scripted)
    assert game.play_hand() == [(40, [a])]
    assert a.chips == 40


def test_short_all_in_raise_does_not_reopen_betting(scripted):
    # D raises to 30, A calls, and C goes all-in for 35, five short of a full raise. D has to
    # call the extra five or fold, but can't re-raise even though A still has chips.
    actions = [raise_to(30), CALL, FOLD, raise_to(35), raise_to(100), CALL, CALL] + [CHECK] * 6
    game, (a, b, c, d), get_action = make_game([200, 200, 35, 200], actions, scripted)
    game.play_hand()
    assert d.committed_this_hand == 35
    assert get_action.remaining == []


def test_short_all_in_raises_that_add_up_to_a_full_raise_reopen_betting(scripted):
    # D raises to 30 and A calls. B's all-in to 40 and C's all-in to 50 are each short, but
    # together they raise D by a full 20, so D may re-raise A, who still has chips.
    seen = []
    actions = [raise_to(30), CALL, raise_to(40), raise_to(50), raise_to(100), FOLD]

    def record(player, game):
        seen.append(player.name)
        return actions.pop(0)

    a, b, c, d = Player("A", 200), Player("B", 40), Player("C", 50), Player("D", 200)
    Game([a, b, c, d], 5, 10, record).play_hand()
    assert seen == ["D", "A", "B", "C", "D", "A"]
    assert d.committed_this_hand == 100


def test_cannot_raise_when_everyone_else_is_all_in(scripted):
    # C is all-in from the big blind, so A can call or fold but not raise.
    actions = [FOLD, raise_to(50), CALL]
    game, (a, b, c), get_action = make_game([200, 200, 10], actions, scripted)
    game.play_hand()
    assert a.committed_this_hand == 0
    assert b.committed_this_hand == 10
    assert get_action.remaining == []


def test_side_pots(scripted):
    # A covers everyone, B covers C. C has the best hand, B the second best.
    deck = "2C KS AS 3D KH AH 4D 9C 9D 9H 5D JS 6D QD"
    actions = [raise_to(100), CALL, CALL]
    game, (a, b, c), get_action = make_game([100, 50, 20], actions, scripted, deck)
    results = game.play_hand()
    assert results == [(60, [c]), (60, [b]), (50, [a])]
    assert (a.chips, b.chips, c.chips) == (50, 60, 60)
    assert len(game.community_cards) == 5
    assert get_action.remaining == []


def test_betting_stops_when_only_one_player_can_act(scripted):
    # Heads-up: A is the button and small blind and acts first preflop. B goes all-in,
    # A calls, and A isn't asked to act again on later streets.
    deck = "AS KS AH KH 2C 3D 7C 9D 4S JH 5S QC"
    actions = [CALL, raise_to(100), CALL]
    game, (a, b), get_action = make_game([200, 100], actions, scripted, deck)
    assert game.play_hand() == [(200, [a])]
    assert (a.chips, b.chips) == (300, 0)
    assert get_action.remaining == []
    assert game.is_over()


def test_split_pot_gives_odd_chip_to_first_winner_left_of_button(scripted):
    # The board is a royal flush, so A and C split; B folded their small blind.
    deck = "2C 3C 4C 2D 3D 4D 5H AS KS QS 6H JS 7H 10S"
    actions = [CALL, FOLD, CHECK] + [CHECK] * 6
    game, (a, b, c), get_action = make_game([100, 100, 100], actions, scripted, deck)
    assert game.play_hand() == [(25, [c, a])]
    assert (a.chips, b.chips, c.chips) == (102, 95, 103)
    assert get_action.remaining == []


def test_button_moves_and_skips_busted_players(scripted):
    game, (a, b, c), _ = make_game([100, 0, 100], [], scripted)
    game.start_hand()
    assert game._seated == [a, c]
    game.start_hand()
    assert game._seated == [c, a]
    # Heads-up, the button posts the small blind.
    assert c.committed_this_hand == 5
    assert a.committed_this_hand == 10


def test_move_button_with_no_one_left_keeps_it_in_place(scripted):
    game, _, _ = make_game([0, 0], [], scripted)
    game._move_button()
    assert game._dealer_index == -1


def test_build_pots_gives_folded_overbets_to_the_last_pot(scripted):
    game, (a, b, c), _ = make_game([100, 100, 100], [], scripted)
    a.raise_to(10)
    b.raise_to(10)
    c.raise_to(40)
    c.fold()
    game._seated = [a, b, c]
    game._pot = 60
    assert game._build_pots([a, b]) == [(60, [a, b])]


def test_build_pots_skips_empty_levels(scripted):
    game, (a, b), _ = make_game([100, 100], [], scripted)
    b.raise_to(10)
    game._seated = [a, b]
    game._pot = 10
    assert game._build_pots([a, b]) == [(10, [b])]


def test_shuffle_deck_shuffles_the_game_deck(scripted):
    game, _, _ = make_game([100, 100], [], scripted, "AS KS")
    game.shuffle_deck()
    assert game._deck.get_a_card().to_string() == "A of S"
