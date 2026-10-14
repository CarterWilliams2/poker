from card import Card


def test_card_exposes_value_and_suit():
    card = Card("Q", "H")
    assert card.value == "Q"
    assert card.suit == "H"


def test_to_string():
    assert Card("10", "S").to_string() == "10 of S"
