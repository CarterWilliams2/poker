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
        process.wait(timeout=PATIENCE)


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
