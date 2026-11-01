# Poker

A Texas Hold'em engine in Python, with bots, simulations and a tuner, and a UI being built on top of it.

## Two teams

The repo is split between two teams that work in parallel, often in separate Claude sessions. Every change belongs to exactly one of them.

| Team | Owns |
|---|---|
| **UI** | `ui/` and everything in it, plus `.github/workflows/ui.yml` |
| **Engine** | Everything else: the root-level modules and scripts, `tests/`, `pyproject.toml`, `requirements-dev.txt`, `.gitignore`, the other workflows, `.claude/` and this file |

UI work follows the rules in `ui/CLAUDE.md` as well as these, once that file exists.

## Rules

1. **One team per branch and per PR.** Never change files from both sides in the same PR. If a task needs both, split it into an engine PR and a UI PR, and merge the engine one first.
2. **The UI doesn't change the engine.** UI code only reads the engine through its public API (nothing whose name starts with `_`), and only from one module in `ui/`, so an engine reorganization means fixing one file.
3. **The UI keeps its own copies of shared config** instead of editing the engine's: `ui/.gitignore`, `ui/pyproject.toml`, `ui/requirements*.txt` and `.github/workflows/ui.yml`. UI tests run from inside `ui/`.
4. **Two layouts break the engine's coverage check, so never add them:**
   - `ui/__init__.py`
   - any new `.py` file at the repo root, such as a launcher script. Put it in `ui/` instead.

   Coverage searches from the repo root (`source = ["."]` in `pyproject.toml`) and goes into any folder with an `__init__.py`. Either layout adds untested files to the engine's report and drops it below the required 100%.
5. **The UI asks for engine changes; it doesn't make them.** Open a GitHub issue labeled `engine-request` describing what the UI needs. The engine team adds it to the engine with defaults that keep today's behaviour (like `raiser_floor=-1` in #16), and the UI uses it once that merges.
6. **UI contract tests warn the engine team, they don't block it.** The UI workflow also runs when root `*.py` files change. If it fails on an engine PR, the engine change breaks something the UI relies on. The engine team decides whether to merge, and tells the UI team if it does.

## Working in parallel

- Give each session its own git worktree and branch, made from `main`, e.g. `git worktree add ../poker-<task> -b <task> origin/main`. Sessions sharing one folder switch branches under each other.
- Check `git status` and the current branch before committing; another session may have changed them.

## Engine conventions

- Run the tests with `pytest` from the repo root. It fails if any test fails or coverage drops below 100%.
- Scripts that are run by hand (`play_vs_random.py`, `play_bots.py`, `simulate.py`, `tune.py`) are left out of coverage in `pyproject.toml`.
