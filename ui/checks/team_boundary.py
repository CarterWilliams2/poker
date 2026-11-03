"""Checks that a branch only changes one team's files, as rule 1 in the root CLAUDE.md asks.

The UI team owns ui/ and the UI workflow, and the engine team owns everything else. From ui/,

    python -m checks.team_boundary origin/main

looks at the changes on this branch since it left origin/main, the same changes its pull request
would show, and fails if they include files from both teams. CI runs it on pull requests as the
team-boundary job.
"""
import argparse
import subprocess
import sys

UI_WORKFLOW = ".github/workflows/ui.yml"


def is_ui_file(path):
    """Whether the UI team owns a file, given its path from the repo root."""
    return path.startswith("ui/") or path == UI_WORKFLOW


def changed_files(base, head):
    """The files changed on head since it left base, with paths from the repo root. A file moved
    from one team's side to the other shows up on both sides, as a deletion and an addition."""
    diff = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", "--no-relative", "-z", f"{base}...{head}"],
        stdout=subprocess.PIPE, text=True, check=True)
    return [path for path in diff.stdout.split("\0") if path]


def print_files(heading, paths):
    print(heading)
    for path in paths:
        print("  " + path)


def main(args):
    parser = argparse.ArgumentParser(
        prog="python -m checks.team_boundary",
        description="Fails if the changes on head since it left base include both UI and engine "
                    "files.")
    parser.add_argument("base", help="the branch the changes started from, like origin/main")
    parser.add_argument("head", nargs="?", default="HEAD", help="where they end, HEAD by default")
    options = parser.parse_args(args)
    try:
        files = changed_files(options.base, options.head)
    except subprocess.CalledProcessError as error:
        # git has already said what went wrong.
        return error.returncode

    ui = [path for path in files if is_ui_file(path)]
    engine = [path for path in files if not is_ui_file(path)]
    if ui and engine:
        print("Both UI and engine files changed. Split them into an engine PR and a UI PR, and "
              "merge the engine one first (rule 1 in CLAUDE.md).")
        print_files("UI files:", ui)
        print_files("Engine files:", engine)
        return 1
    if files:
        print_files(f"Only {'UI' if ui else 'engine'} files changed:", files)
    else:
        print("No files changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
