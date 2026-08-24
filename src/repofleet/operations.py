"""Clone / update operations for a single repository."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from repofleet import gitcmd
from repofleet.models import (
    CLONED,
    FAILED,
    MISSING,
    SKIPPED,
    UPDATED,
    UP_TO_DATE,
    RepoResult,
    RepoSpec,
    sanitize_url,
)

STASH_MESSAGE = "repofleet: auto-stash before update"


def clone_repo(
    spec: RepoSpec,
    root: Path,
    remote: str = "origin",
    dry_run: bool = False,
) -> RepoResult:
    dest = spec.path_in(root)
    if gitcmd.is_git_repo(dest):
        return RepoResult(spec.name, SKIPPED, details=["already cloned"])
    if dest.exists() and any(dest.iterdir()):
        return RepoResult.failure(
            spec.name, f"{dest} exists and is not an empty git repo"
        )
    if dry_run:
        return RepoResult(
            spec.name, CLONED, details=[f"would clone {sanitize_url(spec.url)}"]
        )

    root.mkdir(parents=True, exist_ok=True)
    args = ["clone", "--origin", remote]
    if spec.branch:
        args += ["--branch", spec.branch]
    args += [spec.url, str(dest)]

    proc = gitcmd.run_git(args)
    if proc.returncode != 0:
        return RepoResult.failure(
            spec.name, f"git clone failed: {sanitize_url(gitcmd.output(proc))}"
        )
    return RepoResult(
        spec.name, CLONED, details=[f"branch {gitcmd.current_branch(dest)}"]
    )


def update_repo(
    path: Path,
    branch: Optional[str] = None,
    remote: str = "origin",
    stash: bool = True,
    prune: bool = True,
    dry_run: bool = False,
) -> RepoResult:
    """Fetch, switch to the target branch and pull, stashing local work if needed."""
    name = path.name
    details: list = []
    stashed = False

    if not gitcmd.is_git_repo(path):
        return RepoResult(name, MISSING, ok=False, details=["not cloned yet"])

    if dry_run:
        return RepoResult(name, SKIPPED, details=["would fetch + pull"])

    fetch_args = ["fetch", remote]
    if prune:
        fetch_args.insert(1, "--prune")
    fetch = gitcmd.run_git(fetch_args, cwd=path)
    if fetch.returncode != 0:
        return RepoResult.failure(
            name, f"git fetch failed: {sanitize_url(gitcmd.output(fetch))}"
        )

    target = branch or gitcmd.default_branch(path, remote)
    if not target:
        return RepoResult.failure(name, "Could not determine the default branch.")

    if gitcmd.has_local_changes(path):
        if not stash:
            return RepoResult(
                name,
                SKIPPED,
                ok=True,
                details=["local changes present, --no-stash set"],
            )
        push = gitcmd.run_git(["stash", "push", "-u", "-m", STASH_MESSAGE], cwd=path)
        if push.returncode != 0:
            return RepoResult.failure(name, f"git stash failed: {gitcmd.output(push)}")
        stashed = True
        details.append("stashed local changes")

    checkout = gitcmd.run_git(["checkout", target], cwd=path)
    if checkout.returncode != 0:
        if stashed:
            gitcmd.run_git(["stash", "pop"], cwd=path)
        return RepoResult.failure(
            name, *details, f"git checkout {target} failed: {gitcmd.output(checkout)}"
        )
    details.append(f"on {target}")

    pull = gitcmd.run_git(["pull", "--ff-only", remote, target], cwd=path)
    if pull.returncode != 0:
        pull = gitcmd.run_git(["pull", remote, target], cwd=path)
    if pull.returncode != 0:
        if stashed:
            pop = gitcmd.run_git(["stash", "pop"], cwd=path)
            if pop.returncode != 0:
                details.append(f"stash kept (pop failed): {gitcmd.output(pop)}")
        return RepoResult.failure(
            name, *details, f"git pull failed: {sanitize_url(gitcmd.output(pull))}"
        )

    pull_text = gitcmd.output(pull)
    action = UP_TO_DATE if "already up to date" in pull_text.lower() else UPDATED
    if action == UPDATED and pull_text:
        details.append(pull_text.splitlines()[-1].strip())

    if stashed:
        pop = gitcmd.run_git(["stash", "pop"], cwd=path)
        if pop.returncode != 0:
            return RepoResult(
                name,
                FAILED,
                ok=False,
                details=details
                + [
                    f"pull succeeded but 'git stash pop' failed - stash kept: {gitcmd.output(pop)}"
                ],
            )
        details.append("restored stash")

    return RepoResult(name, action, details=details)


def sync_repo(
    spec: RepoSpec,
    root: Path,
    remote: str = "origin",
    stash: bool = True,
    prune: bool = True,
    dry_run: bool = False,
) -> RepoResult:
    """Clone the repo when missing, otherwise update it."""
    dest = spec.path_in(root)
    if not gitcmd.is_git_repo(dest):
        return clone_repo(spec, root, remote=remote, dry_run=dry_run)
    return update_repo(
        dest,
        branch=spec.branch,
        remote=remote,
        stash=stash,
        prune=prune,
        dry_run=dry_run,
    )
