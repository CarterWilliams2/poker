# UI

The browser UI for the poker engine. This folder and `.github/workflows/ui.yml` belong to the UI team. The rules in the root `CLAUDE.md` apply here too; these are the UI's own.

## Layout

- `play.py` starts the server: `python ui/play.py`.
- `server/` is the server, a FastAPI app.
  - `engine.py` is the only module that imports engine code. The rest of the UI gets engine classes from it.
  - `app.py` holds the endpoints, and serves the built web app at `/`.
- `tests/` has the server's tests.
- `web/` is the web app, React and TypeScript built with Vite. `npm run build` puts it in `web/dist`, which the server serves. Until it's built, `/` shows how to build it.
  - `src/` has the components, with their tests next to them (`*.test.ts` and `*.test.tsx`, run by Vitest).

## Rules

- **Reach the engine only through `server/engine.py`,** and only through its public API: nothing whose name starts with `_`. When you need something new from the engine, add it to the imports and `__all__` there.
- **Never add `ui/__init__.py`.** The engine's coverage check would then count every UI file and fail. Packages inside `ui/`, like `server/`, are fine.
- **Run the tests from inside `ui/`,** so pytest uses `ui/pyproject.toml`. It measures only `server/` and fails below 100% coverage. From the repo root, pytest would use the engine's settings instead.
- **Keep `play.py` thin.** Code outside `server/` isn't measured, so anything worth testing goes in `server/`.
- **Add API routes before the web app in `create_app`.** It's mounted at `/`, so it hides any route added after it.
- **Cards are strings,** rank then suit: `"10H"`, `"AS"`. `web/src/cards.ts` reads them.
- **The server only listens on 127.0.0.1.**
- **Pin new Python packages** in `requirements.txt` if the app needs them, or `requirements-dev.txt` if only the tests do. pytest and pytest-cov match the engine's versions, so one virtual environment can run both test suites.
- **Install the web app's packages with `npm ci`** in `web/`. It installs exactly what `package-lock.json` lists and never changes it, the same as CI. Use `npm install` only to add or update a package, then commit `package-lock.json` with `package.json`. Never ignore the lock file: `npm ci` can't run without it.

## Commands

From the repo root, after setting up as in `README.md`:

- Run the server: `.venv/bin/python ui/play.py`
- Rebuild the web app after changing it: `npm --prefix ui/web run build`, then reload the page
- Run the server tests: `cd ui && ../.venv/bin/pytest`
- Check the web app: `cd ui/web && npm run typecheck && npm test`
