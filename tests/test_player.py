from card import Card
from player import Player


def test_new_player():
    player = Player("Ann", 100)
    assert player.name == "Ann"
    assert player.chips == 100
    assert player.hand == []
    assert player.committed_this_round == 0
    assert player.committed_this_hand == 0
    assert player.folded is False


def test_hand_is_a_copy():
    player = Player("Ann", 100)
    player.add_card_to_hand(Card("A", "S"))
    player.hand.clear()
    assert len(player.hand) == 1


def test_post_blind_and_call_track_commitments():
    player = Player("Ann", 100)
    assert player.post_blind(5) == 5
    assert player.call(20) == 15
    assert player.chips == 80
    assert player.committed_this_round == 20
    assert player.committed_this_hand == 20


def test_call_is_capped_at_remaining_chips():
    player = Player("Ann", 30)
    assert player.call(100) == 30
    assert player.chips == 0


def test_raise_to_pays_only_the_difference():
    player = Player("Ann", 100)
    player.post_blind(10)
    assert player.raise_to(40) == 30
    assert player.committed_this_round == 40


def test_raise_to_below_commitment_pays_nothing():
    player = Player("Ann", 100)
    player.post_blind(10)
    assert player.raise_to(5) == 0
    assert player.chips == 90


def test_fold_clears_hand():
    player = Player("Ann", 100)
    player.add_card_to_hand(Card("A", "S"))
    player.fold()
    assert player.folded is True
    assert player.hand == []


def test_collect():
    player = Player("Ann", 100)
    player.collect(50)
    assert player.chips == 150


def test_start_new_round_keeps_hand_commitment():
    player = Player("Ann", 100)
    player.post_blind(10)
    player.start_new_round()
    assert player.committed_this_round == 0
    assert player.committed_this_hand == 10


def test_start_new_hand_resets_everything():
    player = Player("Ann", 100)
    player.post_blind(10)
    player.add_card_to_hand(Card("A", "S"))
    player.fold()
    player.add_card_to_hand(Card("K", "S"))
    player.start_new_hand()
    assert player.committed_this_round == 0
    assert player.committed_this_hand == 0
    assert player.folded is False
    assert player.hand == []
