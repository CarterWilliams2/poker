# Poker UI

A browser UI for the poker engine at the repo root. So far it shows a random deal from the engine's deck as playing cards.

## Setup

From the repo root, with Python 3.11 and Node 22:

```sh
python3.11 -m venv .venv
.venv/bin/pip install -r ui/requirements-dev.txt
npm --prefix ui/web install
npm --prefix ui/web run build
```

`.venv`, `ui/web/node_modules` and the build in `ui/web/dist` are ignored by git. To run the engine's tests from the same environment, also install `requirements-dev.txt`; its test tools are pinned to the same versions.

## Run

```sh
.venv/bin/python ui/play.py
```

Then open http://127.0.0.1:8000 to see a deal: two hole cards and a five-card board. **Deal again** deals a new one.

After changing the web app, run `npm --prefix ui/web run build` and reload the page. If the server started before the first build, restart it.

The API is at http://127.0.0.1:8000/api/deal. Add `?seed=7` to get the same deal every time. http://127.0.0.1:8000/docs lists the endpoints.

Use `--port` to pick another port. The server only accepts connections from this computer.

## Test

```sh
cd ui && ../.venv/bin/pytest
cd ui/web && npm run typecheck && npm test
```

The server tests fail if coverage of `server/` drops below 100%.
