"""Core data types shared across repofleet."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Result actions
CLONED = "cloned"
UPDATED = "updated"
UP_TO_DATE = "up to date"
ADOPTED = "adopted"
SKIPPED = "skipped"
MISSING = "missing"
FAILED = "failed"

_SCP_LIKE = re.compile(r"^(?P<user>[^@/]+)@(?P<host>[^:/]+):(?P<path>.+)$")
_CREDENTIALS = re.compile(r"(?P<scheme>[a-zA-Z0-9+.-]+://)(?P<userinfo>[^/@\s]+)@")


def sanitize_url(url: str) -> str:
    """Mask any userinfo/token embedded in a remote URL before printing it."""
    return _CREDENTIALS.sub(lambda m: f"{m.group('scheme')}***@", url)


def name_from_url(url: str) -> str:
    """Derive a directory name from a git remote URL."""
    candidate = url.strip().rstrip("/")
    match = _SCP_LIKE.match(candidate)
    if match:
        candidate = match.group("path")
    else:
        candidate = candidate.split("://", 1)[-1]
    candidate = candidate.split("?", 1)[0].split("#", 1)[0]
    tail = candidate.rstrip("/").rsplit("/", 1)[-1]
    if tail.endswith(".git"):
        tail = tail[: -len(".git")]
    if not tail:
        raise ValueError(
            f"Cannot derive a repository name from URL: {sanitize_url(url)}"
        )
    return tail


@dataclass
class RepoSpec:
    """A repository declared in the config (or discovered on disk)."""

    name: str
    url: str
    branch: Optional[str] = None

    @classmethod
    def from_url(
        cls, url: str, branch: Optional[str] = None, name: Optional[str] = None
    ) -> "RepoSpec":
        return cls(name=name or name_from_url(url), url=url.strip(), branch=branch)

    def path_in(self, root: Path) -> Path:
        return root / self.name


@dataclass
class RepoResult:
    """Outcome of an operation on a single repository."""

    name: str
    action: str
    ok: bool = True
    details: list = field(default_factory=list)

    @classmethod
    def failure(cls, name: str, *details: str) -> "RepoResult":
        return cls(
            name=name, action=FAILED, ok=False, details=[d for d in details if d]
        )
