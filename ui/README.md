# Poker UI

A browser UI for the poker engine at the repo root. So far it deals two hands and a board from the engine's deck, names each hand with the engine's hand evaluator and shows which one wins. It can also play a match between the engine's bots and redraw the poker table with everything that happens.

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

After changing the web app, run `npm --prefix ui/web run build` and reload the page. If the server started before the first build, restart it. To skip those steps while you work, see [Develop](#develop).

The API is at http://127.0.0.1:8000/api/deal. Add `?seed=7` to get the same deal every time. http://127.0.0.1:8000/docs lists the endpoints.

Use `--port` to pick another port. The server only accepts connections from this computer.

## Watch a match

http://127.0.0.1:8000/watch plays a match between one of each of the engine's bots, and redraws the poker table with everything that happens. Reload the page for a new match.

The match plays at a pace you can follow, about a second for each move. A bubble by each player says what they last did this betting round, like **Raises to 40**, with the newest one in gold. When a betting round ends, the bets slide into the pot. The line above the table says which hand it's on, and `Match over after 34 hands` at the end.

The panel beside the table logs the hand so far, by street: the blinds, every move, the cards each street deals, the cards shown at the showdown and who won. The number on the right of each line is the pot straight after it, counting the bets still in front of the players. The newest line is highlighted, and a new hand starts a new log.

The buttons at the top right control the pace:

- **Pause** stops it, and **Play** carries on.
- **Step** pauses and moves on by one thing at a time.
- **½×**, **1×**, **2×** and **4×** change the speed.

If the server can't be reached, the page says so. If it goes away during a match, the page plays what had already arrived, then says so and keeps the last table on screen.

The page gets the match from `ws://127.0.0.1:8000/ws/watch`. The server sends everything as soon as it happens, so a whole match arrives in under a second and the page plays it back from there. [`PROTOCOL.md`](PROTOCOL.md) describes the messages. With the server running, try it yourself from the repo root:

```sh
.venv/bin/python -m websockets ws://127.0.0.1:8000/ws/watch
```

Then type a start message and press Enter. Each line back is one thing that happened, ending with `match_over`:

```json
{"type": "start", "bots": ["tuned", "random"], "chips": 30, "seed": 7}
```

The same `seed` always gives exactly the same match. When the match is over the server closes the socket and the command ends by itself. To leave sooner, press Ctrl-D, which ends the match too.

## Review the table

http://127.0.0.1:8000/dev/fixtures draws the poker table at every moment of the matches recorded in `fixtures/`, with every table size from 2 to 8 seats. Above each table is the message it was drawn from. It's there to check how the table looks after changing it. With [`npm run dev`](#develop) running, http://127.0.0.1:5173/dev/fixtures updates as you save.

The pot in the middle only counts chips already collected. A bet stays in front of its player until the betting round ends, so every number on the table adds up to the chips the match started with.

## Develop

To see your edits as soon as you save them, run the server and the web app's dev server together, each in its own terminal, from the repo root:

```sh
.venv/bin/python ui/play.py --reload
npm --prefix ui/web run dev
```

Then open http://127.0.0.1:5173, the address the second command prints. If that port is busy, it uses the next free one. Nothing needs building first, and http://127.0.0.1:8000 keeps showing the last build.

- **The web app:** saving a file in `ui/web/src` updates the open page without reloading it. If your edit breaks the web app, the error shows over the page until you save a fix.
- **The server:** saving a Python file in `ui/server` restarts the server. A request made during the restart usually just waits for it. One caught at the instant the old server stops can fail, and then the page says it can't reach the server until you press **Deal again**. If your edit stops the server from starting, the first terminal shows the error and requests wait until you save a fix.
- **The engine:** the server doesn't watch the engine's files, so restart it yourself after changing them. Watching them would mean checking all of `.venv` and `ui/web/node_modules` several times a second, because they all sit under the repo root.

The dev server passes requests for `/api` and `/ws` to the Python server, so the web app calls the same addresses here as when the Python server serves it. If the Python server is on another port, tell the dev server where to find it:

```sh
.venv/bin/python ui/play.py --reload --port 9000
POKER_SERVER_PORT=9000 npm --prefix ui/web run dev
```

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
