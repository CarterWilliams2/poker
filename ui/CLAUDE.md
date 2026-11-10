# UI

The browser UI for the poker engine. This folder and `.github/workflows/ui.yml` belong to the UI team. The rules in the root `CLAUDE.md` apply here too; these are the UI's own.

## Layout

- `PROTOCOL.md` describes the WebSocket messages between the server and the web app.
- `play.py` starts the server: `python ui/play.py`.
- `server/` is the server, a FastAPI app.
  - `engine.py` is the only module that imports engine code. The rest of the UI gets engine classes from it.
  - `app.py` holds the endpoints, and serves the built web app at `/`.
  - `watch.py` plays a match between bots and reports it as messages. `/ws/watch` runs that on its own thread and sends what it reports.
  - `fixtures.py` records the sample matches in `fixtures/`.
- `checks/` has checks CI runs on the repo itself. `team_boundary.py` fails a pull request that changes both UI and engine files.
- `tests/` has the tests for `server/` and `checks/`. `test_engine_contract.py` pins the parts of the engine the UI uses. `test_play.py` runs `play.py` for real, reloading and WebSockets included.
- `fixtures/` has real matches recorded from the server, one message per line, for the server and web tests to check against. The review page at `/dev/fixtures` draws them all.
- `web/` is the web app, React and TypeScript built with Vite. `npm run build` puts it in `web/dist`, which the server serves. Until it's built, its pages show how to build it.
  - `src/` has the components, with their tests next to them (`*.test.ts` and `*.test.tsx`, run by Vitest). `Pages.tsx` picks the page for the address, `Watch.tsx` is the page that shows a live match, `Table.tsx` draws the poker table and `Fixtures.tsx` is the review page. `Playback.tsx` plays messages back at a readable pace with pause, step and speed controls, and `events.ts` works out what to show for each message: the action bubbles, the bets sliding into the pot and how long it stays on screen. `api.ts` talks to the server, and `protocol.ts` has the types for the messages in `PROTOCOL.md`.
  - `vite.config.ts` sets up `npm run dev`, which serves the web app with hot reload and passes `/api` and `/ws` to the Python server. `vite.config.test.ts` checks that against real servers.

## Rules

- **Reach the engine only through `server/engine.py`,** and only through its public API: nothing whose name starts with `_`. When you need something new from the engine, add it to the imports and `__all__` there, then pin the parts you use with tests in `tests/test_engine_contract.py` marked `@pins`. A test there fails until every exported name is pinned.
- **A failing contract test means the engine changed under the UI.** Fix the UI code that relies on the changed part first, then update the test to match the engine.
- **Never add `ui/__init__.py`.** The engine's coverage check would then count every UI file and fail. Packages inside `ui/`, like `server/`, are fine.
- **Run the tests from inside `ui/`,** so pytest uses `ui/pyproject.toml`. It measures only `server/` and `checks/`, and fails below 100% coverage. From the repo root, pytest would use the engine's settings instead.
- **Keep `play.py` thin.** Code outside `server/` and `checks/` isn't measured, so anything worth testing goes in one of those.
- **Add API routes before the web app in `create_app`.** It's mounted at `/`, so it hides any route added after it.
- **Cards are strings,** rank then suit: `"10H"`, `"AS"`. `server/cards.py` writes them and `web/src/cards.ts` reads them.
- **`PROTOCOL.md` is the contract for WebSocket messages.** When you change a message, update it and re-record the samples with `python -m server.fixtures`. A test fails until the samples match what the server sends.
- **Test WebSocket routes on real uvicorn, not with `TestClient`,** which skips uvicorn, can't show a browser leaving, and waits forever if the server goes quiet. `serving` in `tests/test_watch.py` does that.
- **Keep every address the web app calls under `/api` or `/ws`.** `npm run dev` only passes those to the Python server, so anything else would work in the built app but fail while developing.
- **A new page goes in `web/src/Pages.tsx` and in `PAGES` in `server/app.py`.** The dev server answers any address, so a page missing from `PAGES` would work in `npm run dev` and get a 404 from `python ui/play.py`.
- **Size everything on the poker table in `em`.** An em there is a share of the table's width, so a table that fits together at one size does at all of them.
- **The server and the dev server only listen on 127.0.0.1.**
- **Pin new Python packages** in `requirements.txt` if the app needs them, or `requirements-dev.txt` if only the tests do. pytest and pytest-cov match the engine's versions, so one virtual environment can run both test suites.
- **Install the web app's packages with `npm ci`** in `web/`. It installs exactly what `package-lock.json` lists and never changes it, the same as CI. Use `npm install` only to add or update a package, then commit `package-lock.json` with `package.json`. Never ignore the lock file: `npm ci` can't run without it.

## Commands

From the repo root, after setting up as in `README.md`:

- Run the server: `.venv/bin/python ui/play.py`
- Rebuild the web app after changing it: `npm --prefix ui/web run build`, then reload the page
- See edits as you save them, with each command in its own terminal: `.venv/bin/python ui/play.py --reload` and `npm --prefix ui/web run dev`, then open the address the second one prints
- Watch a match in the terminal: `.venv/bin/python -m websockets ws://127.0.0.1:8000/ws/watch`, then type `{"type": "start", "seed": 7}`
- Re-record the samples after changing a message: `cd ui && ../.venv/bin/python -m server.fixtures`
- Run the server tests: `cd ui && ../.venv/bin/pytest`
- Check the web app: `cd ui/web && npm run typecheck && npm test`
- Check that your branch only changes UI files: `cd ui && ../.venv/bin/python -m checks.team_boundary origin/main`
