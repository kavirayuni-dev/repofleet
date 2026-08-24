"""Thin, safe wrapper around the git executable."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

DEFAULT_TIMEOUT = 900


class GitNotAvailable(RuntimeError):
    pass


def ensure_git() -> str:
    exe = shutil.which("git")
    if not exe:
        raise GitNotAvailable("'git' was not found on PATH. Install git and try again.")
    return exe


def run_git(
    args: Sequence[str],
    cwd: Path | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> subprocess.CompletedProcess:
    """Run a git command without a shell and capture its output."""
    exe = ensure_git()
    command = [exe]
    if cwd is not None:
        command += ["-C", str(cwd)]
    command += list(args)
    # Never prompt for credentials: a hung prompt in a batch run is worse than a failure.
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=_non_interactive_env(),
        check=False,
    )


def _non_interactive_env() -> dict:
    import os

    env = dict(os.environ)
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    env.setdefault("GIT_ASKPASS", env.get("GIT_ASKPASS", ""))
    return env


def output(proc: subprocess.CompletedProcess) -> str:
    return (
        (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    ).strip() or (proc.stderr or "").strip()


def last_line(proc: subprocess.CompletedProcess) -> str:
    text = output(proc)
    return text.splitlines()[-1].strip() if text else ""


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def remote_url(path: Path, remote: str = "origin") -> str | None:
    proc = run_git(["remote", "get-url", remote], cwd=path)
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None


def current_branch(path: Path) -> str:
    proc = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
    return proc.stdout.strip() or "HEAD"


def has_local_changes(path: Path) -> bool:
    proc = run_git(["status", "--porcelain"], cwd=path)
    return bool(proc.stdout.strip())


def default_branch(path: Path, remote: str = "origin") -> str | None:
    symbolic = run_git(["rev-parse", "--abbrev-ref", f"{remote}/HEAD"], cwd=path)
    if symbolic.returncode == 0:
        ref = symbolic.stdout.strip()
        if ref.startswith(f"{remote}/"):
            return ref.split("/", 1)[1]

    for candidate in ("main", "master", "develop"):
        local = run_git(
            ["show-ref", "--verify", "--quiet", f"refs/heads/{candidate}"], cwd=path
        )
        upstream = run_git(
            ["show-ref", "--verify", "--quiet", f"refs/remotes/{remote}/{candidate}"],
            cwd=path,
        )
        if local.returncode == 0 or upstream.returncode == 0:
            return candidate
    return None
