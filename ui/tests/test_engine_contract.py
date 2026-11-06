"""Pins down the parts of the engine the UI relies on.

The UI workflow runs these on engine pull requests too, as the engine-contract job. A failure there
means the engine change breaks something the UI uses, and the failing test's name starts with the
engine name it pins. It warns the engine team without blocking the PR (rule 6 in the root
CLAUDE.md). If the change merges anyway, the UI team updates the UI code that relies on it, then
the test.

Every name server/engine.py exports is pinned by at least one test here, marked with @pins. When
you export a new name, add tests for the parts of it the UI uses.
"""
import random
import pytest
from server import engine
from server.engine import (AGENTS, Card, Deck, MAX_PLAYERS, MIN_PLAYERS, Match, evaluate,
                           hand_name)

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["H", "D", "C", "S"]

# The engine names the tests below pin, filled in by @pins as this file loads.
PINNED = set()


def pins(name):
    """Marks a test as pinning part of an engine name that server/engine.py exports."""
    def mark(test):
        PINNED.add(name)
        return test
    return mark


def cards(text):
    """Engine cards from a string like "AS 10H"."""
    return [Card(card[:-1], card[-1]) for card in text.split()]


def deal_all(seed):
    """Every card of a deck shuffled with this seed, as (value, suit), in the order dealt."""
    deck = Deck(random.Random(seed))
    deck.shuffle_deck()
    return [(card.value, card.suit) for card in (deck.get_a_card() for _ in range(52))]


def seated(*bots, seed=1, looking_first=lambda agent: agent):
    """Seats for a Match, named and seeded the way server/watch.py does it."""
    rng = random.Random(seed)
    return [(f"{bot.capitalize()} {number}",
             looking_first(AGENTS[bot](random.Random(rng.random()))))
            for number, bot in enumerate(bots, start=1)]


def watched_match(*bots, chips=100, small_blind=1, big_blind=2, seed=1, look=lambda match: None):
    """A match that calls look just before each bot decides, the way server/watch.py does."""
    def looking_first(agent):
        def decide(view):
            look(match)
            return agent(view)
        return decide
    match = Match(seated(*bots, seed=seed, looking_first=looking_first), chips, small_blind,
                  big_blind, rng=random.Random(seed))
    return match


def test_every_engine_name_the_ui_imports_is_pinned():
    assert PINNED == set(engine.__all__), "Pin each name in server/engine.py's __all__ with @pins"


@pins("Card")
def test_card_takes_a_value_and_a_suit_and_gives_them_back():
    # server/app.py writes a card as its value then its suit, like "10H".
    card = Card("10", "H")
    assert (card.value, card.suit) == ("10", "H")


@pins("Deck")
def test_deck_deals_all_52_cards_once_after_a_shuffle():
    # web/src/cards.ts can only draw these values and suits.
    dealt = deal_all(1)
    assert len(dealt) == 52
    assert set(dealt) == {(value, suit) for value in RANKS for suit in SUITS}


@pins("Deck")
def test_deck_shuffles_the_same_way_for_the_same_seed():
    # /api/deal?seed= relies on this to repeat a deal.
    assert deal_all(7) == deal_all(7)
    assert deal_all(7) != deal_all(8)


@pins("evaluate")
def test_evaluate_scores_the_better_of_two_hands_higher():
    # server/app.py scores two cards plus the board, and the highest score wins.
    board = cards("2C 7D 9H JS KC")
    assert evaluate(cards("AS AD") + board) > evaluate(cards("3H 4S") + board)


@pins("evaluate")
def test_evaluate_scores_hands_that_play_the_same_five_cards_the_same():
    # server/app.py calls hands with equal scores a tie.
    board = cards("10S JS QS KS AS")
    assert evaluate(cards("2H 3D") + board) == evaluate(cards("4C 5H") + board)


@pins("hand_name")
@pytest.mark.parametrize("seven_cards, name", [
    ("2C 5D 7H 9S JC KD 3H", "High Card"),
    ("2C 2D 7H 9S JC KD 3H", "Pair"),
    ("2C 2D 7H 7S JC KD 3H", "Two Pair"),
    ("2C 2D 2H 7S JC KD 3H", "Three Of A Kind"),
    ("4C 5D 6H 7S 8C KD 2H", "Straight"),
    ("2H 5H 9H JH KH 3C 4D", "Flush"),
    ("2C 2D 2H 7S 7C KD 3H", "Full House"),
    ("2C 2D 2H 2S 7C KD 3H", "Four Of A Kind"),
    ("5S 6S 7S 8S 9S KD 3H", "Straight Flush"),
])
def test_hand_name_gives_the_names_the_ui_shows(seven_cards, name):
    # The deal page shows each hand's name just as the engine gives it.
    assert hand_name(evaluate(cards(seven_cards))) == name


@pins("MIN_PLAYERS")
@pins("MAX_PLAYERS")
def test_a_table_seats_2_to_8():
    # server/watch.py limits the start message to these, and the web app draws this many seats.
    assert (MIN_PLAYERS, MAX_PLAYERS) == (2, 8)


@pins("AGENTS")
def test_agents_makes_a_bot_from_a_seeded_rng():
    # server/watch.py names each seat after the bot, so it needs a word it can capitalize.
    for name, make_bot in AGENTS.items():
        assert name.isalpha()
        assert callable(make_bot(random.Random(1)))


@pins("AGENTS")
def test_agents_has_the_simple_bots_the_samples_use():
    # server/fixtures.py records its sample matches with these.
    assert {"random", "calling"} <= set(AGENTS)


@pins("Match")
def test_match_plays_the_same_way_for_the_same_seeds():
    # /ws/watch relies on this to replay a match, and the recorded samples to stay the same.
    def chips_after_each_hand(seed):
        match = watched_match("random", "tuned", "calling", "aggressive", seed=seed)
        chips = []
        match.run(on_hand=lambda number, pots: chips.append([p.chips for p in match.players]))
        return chips

    assert chips_after_each_hand(7) == chips_after_each_hand(7)
    assert chips_after_each_hand(7) != chips_after_each_hand(8)


@pins("Match")
def test_match_run_reports_each_hand_and_stops_at_max_hands():
    # server/watch.py finishes each hand in on_hand, which gets the pots the hand paid out.
    match = watched_match("calling", "calling")
    hands = []
    standings = match.run(5, on_hand=lambda number, pots: hands.append((number, pots)))
    assert [number for number, _ in hands] == [1, 2, 3, 4, 5]
    assert match.hands_played == 5
    assert all(amount > 0 and winners for _, pots in hands for amount, winners in pots)
    assert {player.name for player in standings} == {"Calling 1", "Calling 2"}


@pins("Match")
def test_match_asks_for_at_most_one_action_between_looks():
    # server/watch.py reports chips as of each look, so each look must cover a single action.
    counts = []
    match = watched_match("random", "random", "calling",
                          look=lambda match: counts.append(len(match.game.history)))
    match.run(50, on_hand=lambda number, pots: counts.append(None))
    for before, after in zip(counts, counts[1:]):
        if before is not None and after is not None:
            assert after == before + 1


@pins("Match")
@pytest.mark.parametrize("bots, blinds_at", [(2, [0, 1]), (3, [1, 2]), (8, [1, 2])])
def test_match_has_only_the_blinds_in_at_the_first_look(bots, blinds_at):
    # server/watch.py works out who the blinds are from who has chips in at the first look, with
    # the small blind first, and that the button is the first seat.
    looks = []
    match = watched_match(*["calling"] * bots, look=lambda match: looks.append(
        [(player.name, player.committed_this_hand) for player in match.game.seated]))
    match.play_hand()
    posted = [(index, chips) for index, (_, chips) in enumerate(looks[0]) if chips > 0]
    assert posted == list(zip(blinds_at, [1, 2]))


@pins("Match")
def test_match_seats_start_from_the_button_which_moves_each_hand():
    # server/watch.py takes the first seat as the button.
    match = watched_match("calling", "calling", "calling", chips=1000)
    buttons = []
    match.run(3, on_hand=lambda number, pots: buttons.append(match.game.seated[0].name))
    assert buttons == ["Calling 1", "Calling 2", "Calling 3"]


@pins("Match")
def test_match_only_seats_players_with_chips():
    # server/watch.py treats a player who isn't seated as busted.
    match = watched_match("random", "random", "random", "calling", chips=20, seed=2)
    alive_before = [{player.name for player in match.players}]
    def after_hand(number, pots):
        assert {player.name for player in match.game.seated} == alive_before[-1]
        alive_before.append({player.name for player in match.players if player.chips > 0})
    match.run(on_hand=after_hand)
    assert len(alive_before[-1]) == 1


@pins("Match")
def test_match_keeps_what_each_player_put_in_after_the_hand():
    # server/watch.py works out chips and the pot from committed_this_hand, even after the engine
    # has paid the winners, and the pots paid out are everything that went in.
    match = watched_match("random", "random", "calling", chips=50, seed=3)
    stacks = {player: player.chips for player in match.players}
    def after_hand(number, pots):
        assert sum(amount for amount, _ in pots) == sum(
            player.committed_this_hand for player in match.players)
        won = {player: 0 for player in match.players}
        for amount, winners in pots:
            share, odd_chips = divmod(amount, len(winners))
            for winner in winners:
                won[winner] += share
            won[winners[0]] += odd_chips
        for player in match.players:
            assert player.chips == stacks[player] - player.committed_this_hand + won[player]
            stacks[player] = player.chips
    match.run(on_hand=after_hand)


@pins("Match")
def test_match_gives_the_odd_chips_of_a_split_pot_to_the_first_winner():
    # server/watch.py copies this rule, because the engine only reports each pot's total.
    splits_with_an_odd_chip = 0
    for seed in range(300):
        match = watched_match("random", "random", "calling", chips=10, seed=seed)
        stacks = {player: player.chips for player in match.players}
        def after_hand(number, pots):
            nonlocal splits_with_an_odd_chip
            if len(pots) == 1 and len(pots[0][1]) == 2 and pots[0][0] % 2 == 1:
                amount, (first, second) = pots[0]
                splits_with_an_odd_chip += 1
                assert first.chips - stacks[first] + first.committed_this_hand == amount // 2 + 1
                assert second.chips - stacks[second] + second.committed_this_hand == amount // 2
            stacks.update({player: player.chips for player in match.players})
        match.run(on_hand=after_hand)
    assert splits_with_an_odd_chip > 0


@pins("Match")
def test_match_deals_the_rest_of_the_board_without_asking_when_all_are_all_in():
    # server/watch.py reports those streets once the hand is over, since no bot gets to look.
    looks = []
    match = watched_match("aggressive", "calling", chips=4, look=lambda match: looks.append(
        len(match.game.community_cards)))
    match.play_hand()
    assert set(looks) == {0}
    assert len(match.game.community_cards) == 5


@pins("Match")
def test_match_can_play_a_hand_without_asking_anyone_anything():
    # server/watch.py starts a hand at its last look when there was never an earlier one: here the
    # blinds put both players all-in.
    looks = []
    match = watched_match("calling", "calling", chips=1, look=looks.append)
    match.play_hand()
    assert looks == []
    assert [player.committed_this_hand for player in match.game.seated] == [1, 1]
    assert len(match.game.community_cards) == 5


@pins("Match")
def test_match_records_each_action_as_player_street_action_and_amount():
    # server/watch.py reports these, and the amount is the player's total bet this round after a
    # call or raise, and 0 for a check or fold.
    actions = set()
    match = watched_match("random", "random", "calling", "aggressive", chips=50, seed=4)
    def after_hand(number, pots):
        for player, street, action, amount in match.game.history:
            assert player in match.players
            assert street.value in {"preflop", "flop", "turn", "river"}
            actions.add(action.value)
            assert (amount > 0) == (action.value in {"call", "raise"})
    match.run(on_hand=after_hand)
    assert actions == {"fold", "check", "call", "raise"}


@pins("Match")
def test_match_clears_a_folded_players_cards_and_keeps_the_rest_until_the_next_hand():
    # server/watch.py shows a seat's cards until it folds, and reads the showdown's after the hand.
    folds = 0
    match = watched_match("random", "random", "calling", chips=50, seed=5)
    def after_hand(number, pots):
        nonlocal folds
        for player in match.game.seated:
            assert len(player.hand) == (0 if player.folded else 2)
            folds += player.folded
    match.run(on_hand=after_hand)
    assert folds > 0


@pins("Match")
def test_match_lists_busted_players_in_order_and_ranks_the_standings():
    # server/watch.py gives each busted player a place from the order they went out.
    match = watched_match("random", "random", "random", "calling", chips=20, seed=2)
    standings = match.run()
    assert len(match.eliminated) == 3
    still_in = [player for player in match.players if player.chips > 0]
    assert standings == still_in + match.eliminated[::-1]
    assert standings[0].chips == 80
