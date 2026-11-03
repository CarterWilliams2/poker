# Poker UI

A browser UI for the poker engine at the repo root. So far it deals two hands and a board from the engine's deck, names each hand with the engine's hand evaluator and shows which one wins.

## Setup

From the repo root, with Python 3.11 and Node 22:

```sh
python3.11 -m venv .venv
.venv/bin/pip install -r ui/requirements-dev.txt
npm --prefix ui/web ci
npm --prefix ui/web run build
```

`npm ci` installs exactly the versions in `ui/web/package-lock.json` and never changes that file. `.venv`, `ui/web/node_modules` and the build in `ui/web/dist` are ignored by git. To run the engine's tests from the same environment, also install `requirements-dev.txt`; its test tools are pinned to the same versions.

## Run

```sh
.venv/bin/python ui/play.py
```

Then open http://127.0.0.1:8000 to see a deal: your two cards at the bottom, your opponent's at the top and a five-card board between them. Each hand is named, like "Two Pair", and the winning hand is marked **Wins**. When neither hand is better, both are marked **Tie**. **Deal again** deals a new one.

After changing the web app, run `npm --prefix ui/web run build` and reload the page. If the server started before the first build, restart it.

The API is at http://127.0.0.1:8000/api/deal. Add `?seed=7` to get the same deal every time. http://127.0.0.1:8000/docs lists the endpoints.

Use `--port` to pick another port. The server only accepts connections from this computer.

## Test

```sh
cd ui && ../.venv/bin/pytest
cd ui/web && npm run typecheck && npm test
```

The server tests fail if coverage of `server/` or `checks/` drops below 100%.

`tests/test_engine_contract.py` pins the parts of the engine the UI uses. CI also runs it on its own as the `engine-contract` job, including on engine changes, so a failure there tells the engine team what their change would break in the UI.

Before opening a pull request, check that your branch only changes UI files:

```sh
cd ui && ../.venv/bin/python -m checks.team_boundary origin/main
```

It lists the files the branch changes since it left `origin/main`, and fails if they include engine files too. CI runs the same check on pull requests as the `team-boundary` job.
