"""Find git repositories that already exist on disk."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Iterable, List, Optional

from repofleet.gitcmd import current_branch, is_git_repo, remote_url
from repofleet.models import RepoSpec


def matches(name: str, patterns: Iterable[str]) -> bool:
    patterns = list(patterns) or ["*"]
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def discover_repos(
    root: Path, patterns: Optional[Iterable[str]] = None, remote: str = "origin"
) -> List[RepoSpec]:
    """Return a spec for every git repo directly under ``root`` matching ``patterns``."""
    root = Path(root)
    if not root.is_dir():
        return []

    found: List[RepoSpec] = []
    for path in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_dir() or not is_git_repo(path):
            continue
        if not matches(path.name, patterns or ["*"]):
            continue
        url = remote_url(path, remote)
        if not url:
            continue
        found.append(RepoSpec(name=path.name, url=url, branch=None))
    return found


def local_branch(path: Path) -> str:
    return current_branch(path)
