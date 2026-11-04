from server.engine import Card

def card_text(card: Card):
    """Writes a card as rank then suit, like "10H" or "AS"."""
    return card.value + card.suit
