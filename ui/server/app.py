import random
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from server.engine import Card, Deck

# Where npm run build puts the web app.
WEB_DIST = Path(__file__).resolve().parents[1] / "web" / "dist"

# Shown at / until the web app has been built.
NOT_BUILT_PAGE = """<!doctype html>
<title>Poker</title>
<h1>The web app hasn't been built yet</h1>
<p>In <code>ui/web</code>, run <code>npm install</code> and then <code>npm run build</code>.
Then restart <code>python ui/play.py</code> and reload this page.</p>
"""

def card_text(card: Card):
    """Writes a card as rank then suit, like "10H" or "AS"."""
    return card.value + card.suit

def create_app(web_dist: Path = WEB_DIST):
    """Builds the server: the API, plus the web app from web_dist once it has been built."""
    app = FastAPI(title="Poker")

    @app.get("/api/deal")
    def deal(seed: int | None = None):
        """Deals two hole cards and a five-card board from a freshly shuffled engine deck. The
        same seed always gives the same deal."""
        deck = Deck(random.Random(seed))
        deck.shuffle_deck()
        cards = [card_text(deck.get_a_card()) for _ in range(7)]
        return {"hand": cards[:2], "board": cards[2:]}

    # The web app goes last: mounted at /, it would hide every route added after it.
    if (web_dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
    else:
        @app.get("/", response_class=HTMLResponse)
        def not_built():
            return NOT_BUILT_PAGE
    return app

app = create_app()
