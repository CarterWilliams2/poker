"""Records sample matches into ui/fixtures, for the server and web tests to check against. Run it
after changing a message, and update ui/PROTOCOL.md to match. From ui/:

    python -m server.fixtures
"""
from pathlib import Path
from server.watch import WatchSettings, play_match

FOLDER = Path(__file__).resolve().parents[1] / "fixtures"

# Short matches that between them send every message. Only simple bots play, so that the engine
# team retuning the strength agent doesn't change them. tests/test_fixtures.py checks that each one
# still shows what its comment says.
SAMPLES = {
    # Every kind of message, at the smallest table.
    "heads-up": {"bots": ["random", "calling"], "chips": 10, "seed": 576},
    # A pot split with an odd chip left over.
    "split-pot": {"bots": ["random", "random", "calling"], "chips": 10, "seed": 2826},
    # At the biggest table, a side pot won by a different player, and two players busting at once.
    "full-table": {"bots": ["random"] * 6 + ["calling"] * 2, "chips": 40, "seed": 327},
}

def record(settings: dict):
    """A match's messages, exactly as the server sends them."""
    messages = []
    play_match(WatchSettings(type="start", **settings), messages.append)
    return messages

def write(folder: Path = FOLDER):
    """Writes each sample as a JSON array with one message per line, for readable diffs."""
    for name, settings in SAMPLES.items():
        (folder / f"{name}.json").write_text("[\n" + ",\n".join(record(settings)) + "\n]\n")

if __name__ == "__main__":
    write()
