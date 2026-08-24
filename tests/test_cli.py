"""End-to-end tests using real local git repositories."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from repofleet.cli import main
from repofleet.config import REPOS_FILENAME, load_config

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")


def git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True
    )


@pytest.fixture()
def origin(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    git("init", "--initial-branch=main", cwd=work)
    git("config", "user.email", "dev@example.com", cwd=work)
    git("config", "user.name", "Dev", cwd=work)
    (work / "README.md").write_text("hello\n", encoding="utf-8")
    git("add", ".", cwd=work)
    git("commit", "-m", "init", cwd=work)

    bare = tmp_path / "origin" / "demo.git"
    bare.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--bare", str(work), str(bare)],
        check=True,
        capture_output=True,
    )
    return bare


def write_config(path: Path, root: str, url: Path) -> Path:
    path.write_text(
        "[workspace]\n"
        'name = "Fleet"\n'
        f'root = "{root}"\n'
        "\n[defaults]\njobs = 1\n"
        "\n[[repos]]\n"
        'name = "demo"\n'
        f'url = "{url.as_posix()}"\n',
        encoding="utf-8",
    )
    return path


def test_clone_then_update_and_adopt(tmp_path: Path, origin: Path, monkeypatch):
    config_path = write_config(tmp_path / "repofleet.toml", "checkout", origin)
    root = tmp_path / "checkout"

    assert main(["clone", "-c", str(config_path), "-q"]) == 0
    assert (root / "demo" / "README.md").exists()

    # local edit must survive an update
    (root / "demo" / "scratch.txt").write_text("wip\n", encoding="utf-8")
    assert main(["update", "-c", str(config_path), "-q"]) == 0
    assert (root / "demo" / "scratch.txt").read_text(encoding="utf-8") == "wip\n"

    # a repo cloned by hand gets adopted into the config on sync
    extra_origin = origin.parent / "extra.git"
    subprocess.run(
        ["git", "clone", "--bare", origin.as_posix(), extra_origin.as_posix()],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "clone", extra_origin.as_posix(), str(root / "extra")],
        check=True,
        capture_output=True,
    )
    assert main(["sync", "-c", str(config_path), "-q"]) == 0
    assert sorted(s.name for s in load_config(config_path).repos) == ["demo", "extra"]


def test_sync_ignores_a_second_checkout_of_a_known_repo(tmp_path: Path, origin: Path):
    config_path = write_config(tmp_path / "repofleet.toml", "checkout", origin)
    root = tmp_path / "checkout"

    assert main(["clone", "-c", str(config_path), "-q"]) == 0
    subprocess.run(
        ["git", "clone", origin.as_posix(), str(root / "demo-copy")],
        check=True,
        capture_output=True,
    )
    assert main(["sync", "-c", str(config_path), "-q"]) == 0
    assert [s.name for s in load_config(config_path).repos] == ["demo"]


def test_status_reports_missing(tmp_path: Path, origin: Path, capsys):
    config_path = write_config(tmp_path / "repofleet.toml", "checkout", origin)
    assert main(["status", "-c", str(config_path)]) == 0
    assert "missing" in capsys.readouterr().out


def test_add_and_remove(tmp_path: Path, origin: Path, capsys):
    config_path = write_config(tmp_path / "repofleet.toml", "checkout", origin)
    assert main(["add", "-c", str(config_path), "https://host/org/other.git"]) == 0
    assert sorted(s.name for s in load_config(config_path).repos) == ["demo", "other"]
    assert main(["remove", "-c", str(config_path), "other"]) == 0
    assert [s.name for s in load_config(config_path).repos] == ["demo"]


def test_init_creates_config_and_repo_list(tmp_path: Path, capsys):
    output = tmp_path / "repofleet.toml"
    assert main(["init", "--root", str(tmp_path), "--output", str(output)]) == 0

    repos_file = tmp_path / REPOS_FILENAME
    assert repos_file.is_file()
    assert load_config(output).repos == []
    assert load_config(repos_file).repos == []  # template is fully commented out

    out = capsys.readouterr().out
    assert "Next steps" in out
    assert REPOS_FILENAME in out


def test_init_repo_list_feeds_the_fleet(tmp_path: Path, origin: Path):
    output = tmp_path / "repofleet.toml"
    assert main(["init", "--root", str(tmp_path), "--output", str(output)]) == 0

    (tmp_path / REPOS_FILENAME).write_text(f"{origin.as_posix()}\n", encoding="utf-8")
    config = load_config(output)
    assert [s.name for s in config.repos] == ["demo"]

    # repos owned by the list file are not copied into the TOML on rewrite
    assert main(["add", "-c", str(output), "https://host/org/other.git"]) == 0
    assert main(["remove", "-c", str(output), "other"]) == 0
    assert "demo" not in output.read_text(encoding="utf-8")
    assert [s.name for s in load_config(output).repos] == ["demo"]
