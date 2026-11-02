import random
from fastapi import FastAPI
from server.engine import Card, Deck

app = FastAPI(title="Poker")

def card_text(card: Card):
    """Writes a card as rank then suit, like "10H" or "AS"."""
    return card.value + card.suit

@app.get("/api/deal")
def deal(seed: int | None = None):
    """Deals two hole cards and a five-card board from a freshly shuffled engine deck. The same
    seed always gives the same deal."""
    deck = Deck(random.Random(seed))
    deck.shuffle_deck()
    cards = [card_text(deck.get_a_card()) for _ in range(7)]
    return {"hand": cards[:2], "board": cards[2:]}
