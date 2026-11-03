import subprocess
from pathlib import Path
import pytest
from checks.team_boundary import is_ui_file, main


def git(*args):
    subprocess.run(["git", *args], check=True, capture_output=True)


def commit(changes):
    """Commits files given as {path: text}."""
    for path, text in changes.items():
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text)
    git("add", "--all")
    git("commit", "--quiet", "--message", "Change files")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A new git repo as the current folder. Its main branch has one engine file and one UI file,
    and a feature branch is checked out from it."""
    # Keeps the user's own git settings, like commit signing, out of the repo.
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "test@example.com")
    monkeypatch.chdir(tmp_path)
    git("init", "--quiet", "--initial-branch", "main")
    commit({"game.py": "engine", "ui/play.py": "ui"})
    git("switch", "--quiet", "--create", "feature")


@pytest.mark.parametrize("path, ui", [
    ("ui/server/app.py", True),
    (".github/workflows/ui.yml", True),
    ("game.py", False),
    ("tests/test_game.py", False),
    (".github/workflows/tests.yml", False),
    ("CLAUDE.md", False),
])
def test_ui_files_are_the_ones_in_ui_plus_the_ui_workflow(path, ui):
    assert is_ui_file(path) == ui


def test_passes_when_only_ui_files_change(repo, capsys):
    commit({"ui/README.md": "how to play", "ui/play.py": "changed"})
    assert main(["main"]) == 0
    assert capsys.readouterr().out == "Only UI files changed:\n  ui/README.md\n  ui/play.py\n"


def test_passes_when_only_engine_files_change(repo, capsys):
    commit({"game.py": "changed", ".github/workflows/tests.yml": "on: push"})
    assert main(["main"]) == 0
    assert capsys.readouterr().out == (
        "Only engine files changed:\n  .github/workflows/tests.yml\n  game.py\n")


def test_fails_when_files_from_both_teams_change(repo, capsys):
    commit({"ui/play.py": "changed", "game.py": "changed"})
    assert main(["main"]) == 1
    out = capsys.readouterr().out
    assert "Split them into an engine PR and a UI PR" in out
    assert out.endswith("UI files:\n  ui/play.py\nEngine files:\n  game.py\n")


def test_a_file_moved_to_the_other_side_counts_for_both(repo, capsys):
    git("mv", "game.py", "ui/game.py")
    git("commit", "--quiet", "--message", "Move the game into the UI")
    assert main(["main"]) == 1
    assert capsys.readouterr().out.endswith("UI files:\n  ui/game.py\nEngine files:\n  game.py\n")


def test_ignores_changes_made_on_base_after_the_branch_left_it(repo, capsys):
    commit({"ui/play.py": "changed"})
    git("switch", "--quiet", "main")
    commit({"game.py": "changed on main"})
    git("switch", "--quiet", "feature")
    assert main(["main"]) == 0
    assert capsys.readouterr().out == "Only UI files changed:\n  ui/play.py\n"


def test_checks_a_pull_requests_merge_commit_against_its_base(repo, capsys):
    # For a pull request, CI checks out the PR merged into its base and compares it with HEAD^1,
    # the base.
    commit({"ui/play.py": "changed"})
    git("switch", "--quiet", "main")
    commit({"game.py": "changed on main"})
    git("merge", "--quiet", "--no-edit", "feature")
    assert main(["HEAD^1"]) == 0
    assert capsys.readouterr().out == "Only UI files changed:\n  ui/play.py\n"


def test_can_check_a_branch_that_is_not_checked_out(repo):
    commit({"ui/play.py": "changed", "game.py": "changed"})
    git("switch", "--quiet", "main")
    assert main(["main", "feature"]) == 1


def test_says_when_nothing_changed(repo, capsys):
    assert main(["main"]) == 0
    assert capsys.readouterr().out == "No files changed.\n"


def test_a_branch_git_cannot_find_fails_with_gits_own_message(repo, capfd):
    assert main(["no-such-branch"]) != 0
    assert "no-such-branch" in capfd.readouterr().err
