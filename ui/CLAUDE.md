# UI

The browser UI for the poker engine. This folder and `.github/workflows/ui.yml` belong to the UI team. The rules in the root `CLAUDE.md` apply here too; these are the UI's own.

## Layout

- `play.py` starts the server: `python ui/play.py`.
- `server/` is the server, a FastAPI app.
  - `engine.py` is the only module that imports engine code. The rest of the UI gets engine classes from it.
  - `app.py` holds the endpoints.
- `tests/` has the server's tests.

## Rules

- **Reach the engine only through `server/engine.py`,** and only through its public API: nothing whose name starts with `_`. When you need something new from the engine, add it to the imports and `__all__` there.
- **Never add `ui/__init__.py`.** The engine's coverage check would then count every UI file and fail. Packages inside `ui/`, like `server/`, are fine.
- **Run the tests from inside `ui/`,** so pytest uses `ui/pyproject.toml`. It measures only `server/` and fails below 100% coverage. From the repo root, pytest would use the engine's settings instead.
- **Keep `play.py` thin.** Code outside `server/` isn't measured, so anything worth testing goes in `server/`.
- **Cards are strings,** rank then suit: `"10H"`, `"AS"`.
- **The server only listens on 127.0.0.1.**
- **Pin new packages** in `requirements.txt` if the app needs them, or `requirements-dev.txt` if only the tests do. pytest and pytest-cov match the engine's versions, so one virtual environment can run both test suites.

## Commands

From the repo root, after setting up `.venv` as in `README.md`:

- Run the server: `.venv/bin/python ui/play.py`
- Run the tests: `cd ui && ../.venv/bin/pytest`
