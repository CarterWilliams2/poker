import asyncio
import random
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from server.cards import card_text
from server.engine import Card, Deck, evaluate, hand_name
from server.watch import parse_start, play_match

# Where npm run build puts the web app.
WEB_DIST = Path(__file__).resolve().parents[1] / "web" / "dist"

# Shown at / until the web app has been built.
NOT_BUILT_PAGE = """<!doctype html>
<title>Poker</title>
<h1>The web app hasn't been built yet</h1>
<p>In <code>ui/web</code>, run <code>npm ci</code> and then <code>npm run build</code>.
Then restart <code>python ui/play.py</code> and reload this page.</p>
"""

def showdown(hands: list[list[Card]], board: list[Card]):
    """Names the best hand each player makes with the board, like "Full House", using the engine's
    scores, and marks the winners. Hands that tie for the best all win."""
    scores = [evaluate(hand + board) for hand in hands]
    best = max(scores)
    return [{"cards": [card_text(card) for card in hand],
             "name": hand_name(score),
             "wins": score == best}
            for hand, score in zip(hands, scores)]

async def read_start(socket: WebSocket):
    """Waits for a good start message, answering anything else with an error."""
    while True:
        try:
            return parse_start(await socket.receive_text())
        except ValueError as error:
            await socket.send_json({"type": "error", "message": str(error)})

def create_app(web_dist: Path = WEB_DIST):
    """Builds the server: the API, plus the web app from web_dist once it has been built."""
    app = FastAPI(title="Poker")

    @app.get("/api/deal")
    def deal(seed: int | None = None):
        """Deals two players two cards each and a five-card board from a freshly shuffled engine
        deck, then names each hand and says which one wins. The same seed always gives the same
        deal."""
        deck = Deck(random.Random(seed))
        deck.shuffle_deck()
        hands = [[deck.get_a_card(), deck.get_a_card()] for _ in range(2)]
        board = [deck.get_a_card() for _ in range(5)]
        return {"hands": showdown(hands, board), "board": [card_text(card) for card in board]}

    @app.websocket("/ws/watch")
    async def watch(socket: WebSocket):
        """Plays a match between bots and streams it. ui/PROTOCOL.md describes the messages."""
        await socket.accept()
        loop = asyncio.get_running_loop()

        def send(text: str):
            # The match plays on its own thread, because the engine plays a whole hand at once.
            # Waiting for each message to go out means a browser that falls behind holds the match
            # up, and one that has left raises WebSocketDisconnect here, which ends the match.
            asyncio.run_coroutine_threadsafe(socket.send_text(text), loop).result()

        try:
            settings = await read_start(socket)
            await asyncio.to_thread(play_match, settings, send)
            await socket.close()
        except (WebSocketDisconnect, asyncio.CancelledError):
            # The browser left, or the server is quitting while a browser has stopped reading.
            pass

    # The web app goes last: mounted at /, it would hide every route added after it.
    if (web_dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
    else:
        @app.get("/", response_class=HTMLResponse)
        def not_built():
            return NOT_BUILT_PAGE
    return app

app = create_app()
