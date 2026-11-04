import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.request import urlopen
from websockets.sync.client import connect
from server.fixtures import record

UI = Path(__file__).resolve().parents[1]
REPO = UI.parent

# Seconds to keep asking a server before giving up. Starting one imports a lot, and CI can be slow.
PATIENCE = 30

# A new route for the end of server/app.py.
NEW_ROUTE = """

@app.get("/api/edited")
def edited():
    return "edited"
"""


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def running(play, *args):
    """Runs a play.py from the repo root, the way the README does, and gives its address. Its
    output goes where pytest captures it, to be shown if the test fails. The engine is on
    PYTHONPATH so that a copy of play.py can find it too."""
    port = free_port()
    process = subprocess.Popen([sys.executable, str(play), "--port", str(port), *args], cwd=REPO,
                               env={**os.environ, "PYTHONPATH": str(REPO)})
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        process.terminate()
        try:
            process.wait(timeout=PATIENCE)
        except subprocess.TimeoutExpired:
            process.kill()
            raise


def answer(url):
    """The JSON a url answers with, asking until it gives one. Until then the server may still be
    starting, or the route may not exist yet."""
    deadline = time.monotonic() + PATIENCE
    while True:
        try:
            with urlopen(url, timeout=PATIENCE) as response:
                return json.load(response)
        except OSError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.1)


def test_play_starts_the_server():
    with running(UI / "play.py") as server:
        assert len(answer(f"{server}/api/deal")["board"]) == 5


def test_reload_picks_up_an_edit_to_a_server_file(tmp_path):
    ui = tmp_path / "ui"
    ui.mkdir()
    shutil.copy(UI / "play.py", ui)
    shutil.copytree(UI / "server", ui / "server")
    app_file = ui / "server" / "app.py"

    with running(ui / "play.py", "--reload") as server:
        assert len(answer(f"{server}/api/deal")["board"]) == 5
        # The reloader looks over the files a moment after each start, and only notices edits made
        # after that.
        time.sleep(0.5)
        app_file.write_text(app_file.read_text() + NEW_ROUTE)
        assert answer(f"{server}/api/edited") == "edited"


def test_a_match_streams_through_the_real_server():
    # The test client skips uvicorn, which can't speak WebSocket at all unless ui/requirements.txt
    # installs a library for it. The server also runs in its own process here, so this shows that
    # matches don't depend on anything that varies between processes.
    settings = {"bots": ["tuned", "strength", "random", "calling"], "chips": 30, "seed": 7}
    with running(UI / "play.py") as server:
        answer(f"{server}/api/deal")
        with connect(server.replace("http", "ws") + "/ws/watch", proxy=None) as browser:
            browser.send(json.dumps({"type": "start", **settings}))
            assert list(browser) == record(settings)


def test_quitting_doesnt_wait_for_a_browser_that_stopped_reading(capfd):
    # The match is far longer than the socket's small buffer can hold, and a WebSocket library would
    # go on reading, so this speaks the protocol by hand. The socket stays open until after the
    # server has been told to stop, and leaving the running block fails the test if it doesn't.
    start = json.dumps({"type": "start", "bots": ["calling", "calling"], "chips": 100000,
                        "max_hands": 100000}).encode()
    with socket.socket() as stalled:
        stalled.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        with running(UI / "play.py") as server:
            answer(f"{server}/api/deal")
            host, port = server.removeprefix("http://").split(":")
            stalled.connect((host, int(port)))
            key = base64.b64encode(os.urandom(16)).decode()
            stalled.sendall((f"GET /ws/watch HTTP/1.1\r\nHost: {host}:{port}\r\n"
                             "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                             f"Sec-WebSocket-Key: {key}\r\n"
                             "Sec-WebSocket-Version: 13\r\n\r\n").encode())
            # Reads the handshake's answer, a byte at a time so as to leave the match unread. The
            # server would ignore anything sent before answering.
            answered = b""
            while not answered.endswith(b"\r\n\r\n"):
                answered += stalled.recv(1)
            # A text frame with an all-zero mask, which leaves the text as it is.
            stalled.sendall(bytes([0x81, 0x80 | len(start)]) + bytes(4) + start)
            # Long enough for the match to fill the socket's buffers.
            time.sleep(1)
            told_to_stop = time.monotonic()
        # It only takes this long if the match really had stalled, which is what's being tested.
        assert time.monotonic() - told_to_stop > 1.5
    assert "Traceback" not in capfd.readouterr().err
