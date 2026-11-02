# Poker UI

A browser UI for the poker engine at the repo root. So far it's a server that deals a random hand from the engine's deck.

## Setup

From the repo root, with Python 3.11:

```sh
python3.11 -m venv .venv
.venv/bin/pip install -r ui/requirements-dev.txt
```

`.venv` is ignored by git. To run the engine's tests from the same environment, also install `requirements-dev.txt`; its test tools are pinned to the same versions.

## Run

```sh
.venv/bin/python ui/play.py
```

Then open http://127.0.0.1:8000/api/deal for two hole cards and a five-card board. Add `?seed=7` to get the same deal every time. http://127.0.0.1:8000/docs lists the endpoints.

Use `--port` to pick another port. The server only accepts connections from this computer.

## Test

```sh
cd ui && ../.venv/bin/pytest
```

The tests fail if coverage of `server/` drops below 100%.
