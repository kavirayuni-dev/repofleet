"""repofleet command line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from repofleet import __version__, gitcmd
from repofleet.config import (
    CONFIG_FILENAMES,
    ConfigError,
    FleetConfig,
    append_repos,
    find_config,
    load_config,
    merge_specs,
    normalize_url,
    remove_repos,
    save_config,
)
from repofleet.discovery import discover_repos, matches
from repofleet.models import ADOPTED, RepoResult, RepoSpec, sanitize_url
from repofleet.operations import clone_repo, sync_repo, update_repo
from repofleet.runner import error, info, run_all, summarize

EPILOG = """\
examples:
  repofleet init --directory "Portfolios Backend"   create a config from repos found on disk
  repofleet sync                                    clone missing, update existing, adopt new
  repofleet update --only portfolios.api            update a single repo
  repofleet add https://host/org/repo.git           track a new repository
  repofleet clone --repos-file team-repos.txt       clone everything listed in a text file
"""


# --------------------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repofleet",
        description="Clone, update and track a fleet of git repositories from one config.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"repofleet {__version__}"
    )

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-c", "--config", help="Path to repofleet.toml (or a .txt repo list)."
    )
    common.add_argument("--root", help="Directory that holds the repositories.")
    common.add_argument(
        "--repos-file",
        action="append",
        default=[],
        metavar="FILE",
        help="Extra repo list file (TOML or plain text). Repeatable.",
    )
    common.add_argument(
        "--repo",
        action="append",
        default=[],
        metavar="URL",
        help="Extra repository URL supplied on the command line. Repeatable.",
    )
    common.add_argument(
        "--only",
        nargs="+",
        default=[],
        metavar="PATTERN",
        help="Only these repos (glob).",
    )
    common.add_argument(
        "--exclude",
        nargs="+",
        default=[],
        metavar="PATTERN",
        help="Skip these repos (glob).",
    )
    common.add_argument("--remote", help="Remote name to use (default: origin).")
    common.add_argument(
        "-j", "--jobs", type=int, help="Parallel workers (default: from config)."
    )
    common.add_argument(
        "--dry-run", action="store_true", help="Show what would happen."
    )
    common.add_argument(
        "-q", "--quiet", action="store_true", help="Only print the summary."
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser(
        "init", parents=[common], help="Create a config from repos on disk."
    )
    p_init.add_argument("--name", help="Workspace name.")
    p_init.add_argument(
        "--directory",
        help="Folder name used when repositories still need to be cloned.",
    )
    p_init.add_argument(
        "--match",
        nargs="+",
        default=["*"],
        metavar="GLOB",
        help="Repo name patterns to track.",
    )
    p_init.add_argument(
        "--output", help=f"Config file to write (default: ./{CONFIG_FILENAMES[0]})."
    )
    p_init.add_argument(
        "--force", action="store_true", help="Overwrite an existing config."
    )
    p_init.set_defaults(func=cmd_init)

    p_list = sub.add_parser(
        "list", parents=[common], help="List the configured repositories."
    )
    p_list.set_defaults(func=cmd_list)

    p_status = sub.add_parser(
        "status", parents=[common], help="Show local state of each repo."
    )
    p_status.set_defaults(func=cmd_status)

    p_clone = sub.add_parser(
        "clone", parents=[common], help="Clone repositories that are missing."
    )
    p_clone.set_defaults(func=cmd_clone)

    p_update = sub.add_parser(
        "update", parents=[common], help="Fetch + pull every cloned repo."
    )
    _add_update_flags(p_update)
    p_update.add_argument(
        "--clone-missing",
        action="store_true",
        help="Also clone repos that are not present.",
    )
    p_update.set_defaults(func=cmd_update)

    p_sync = sub.add_parser(
        "sync",
        parents=[common],
        help="Clone missing repos, update existing ones and adopt new local repos.",
    )
    _add_update_flags(p_sync)
    p_sync.add_argument(
        "--no-adopt",
        action="store_true",
        help="Do not add locally-found repositories to the config.",
    )
    p_sync.set_defaults(func=cmd_sync)

    p_add = sub.add_parser(
        "add", parents=[common], help="Add repositories to the config."
    )
    p_add.add_argument("urls", nargs="+", help="Repository URLs to track.")
    p_add.add_argument("--name", help="Directory name (only valid with a single URL).")
    p_add.add_argument("--branch", help="Branch to track.")
    p_add.add_argument("--clone", action="store_true", help="Clone right after adding.")
    p_add.set_defaults(func=cmd_add)

    p_remove = sub.add_parser(
        "remove", parents=[common], help="Stop tracking repositories."
    )
    p_remove.add_argument(
        "names", nargs="+", help="Repository names to drop from the config."
    )
    p_remove.set_defaults(func=cmd_remove)

    return parser


def _add_update_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-stash",
        action="store_true",
        help="Skip repos with local changes instead of stashing them.",
    )
    parser.add_argument(
        "--no-prune", action="store_true", help="Do not prune remote refs on fetch."
    )


# --------------------------------------------------------------------------- helpers


def load(args) -> FleetConfig:
    if args.config:
        config = load_config(Path(args.config))
    else:
        found = find_config()
        config = load_config(found) if found else FleetConfig()

    for file in args.repos_file:
        config.repos = merge_specs(config.repos, load_config(Path(file)).repos)
    if args.repo:
        config.repos = merge_specs(
            config.repos, [RepoSpec.from_url(u) for u in args.repo]
        )

    if args.remote:
        config.remote = args.remote
    if args.jobs:
        config.jobs = max(1, args.jobs)
    return config


def select(specs: List[RepoSpec], args) -> List[RepoSpec]:
    if args.only:
        specs = [s for s in specs if matches(s.name, args.only)]
    if args.exclude:
        specs = [s for s in specs if not matches(s.name, args.exclude)]
    return specs


def resolve_root(config: FleetConfig, args) -> Path:
    return config.resolve_root(getattr(args, "root", None))


def header(config: FleetConfig, root: Path, args) -> None:
    if args.quiet:
        return
    source = config.source or "<none - using CLI arguments>"
    info(f"config : {source}")
    info(f"root   : {root}")


def require_repos(specs: List[RepoSpec]) -> bool:
    if specs:
        return True
    error(
        "No repositories selected. Add some with 'repofleet add <url>', point at a list with\n"
        "--repos-file, or generate a config from an existing folder with 'repofleet init'."
    )
    return False


# --------------------------------------------------------------------------- commands


def cmd_init(args) -> int:
    config = load(args)
    output = Path(args.output) if args.output else Path.cwd() / CONFIG_FILENAMES[0]
    if output.exists() and not args.force:
        error(f"{output} already exists. Use --force to overwrite.")
        return 1

    scan_root = (
        Path(args.root).expanduser().resolve() if args.root else output.parent.resolve()
    )
    discovered = discover_repos(scan_root, args.match, config.remote)

    config.name = args.name or config.name or scan_root.name
    config.directory = args.directory or config.directory or config.name
    config.match = list(args.match)
    config.source = output
    config.repos = merge_specs(config.repos, discovered)

    if args.dry_run:
        info(f"Would write {len(config.repos)} repo(s) to {output}")
        for spec in config.repos:
            info(f"  {spec.name}  {sanitize_url(spec.url)}")
        return 0

    path = save_config(config, output)
    info(f"Wrote {path} with {len(config.repos)} repository entrie(s).")
    if discovered:
        info(f"Discovered {len(discovered)} repo(s) under {scan_root}.")
    info("Next: run 'repofleet sync' to clone anything missing and update the rest.")
    return 0


def cmd_list(args) -> int:
    config = load(args)
    specs = select(config.repos, args)
    root = resolve_root(config, args)
    header(config, root, args)
    if not specs:
        info("No repositories configured.")
        return 0
    width = max(len(s.name) for s in specs)
    for spec in sorted(specs, key=lambda s: s.name.lower()):
        state = "present" if gitcmd.is_git_repo(spec.path_in(root)) else "missing"
        branch = f" [{spec.branch}]" if spec.branch else ""
        info(f"{spec.name.ljust(width)}  {state:<8}  {sanitize_url(spec.url)}{branch}")
    info(f"\n{len(specs)} repository(ies).")
    return 0


def cmd_status(args) -> int:
    config = load(args)
    specs = select(config.repos, args)
    root = resolve_root(config, args)
    header(config, root, args)
    if not require_repos(specs):
        return 1

    rows = []
    for spec in sorted(specs, key=lambda s: s.name.lower()):
        path = spec.path_in(root)
        if not gitcmd.is_git_repo(path):
            rows.append((spec.name, "missing", "-", "-"))
            continue
        dirty = "dirty" if gitcmd.has_local_changes(path) else "clean"
        rows.append((spec.name, "present", gitcmd.current_branch(path), dirty))

    width = max(len(r[0]) for r in rows)
    for name, state, branch, dirty in rows:
        info(f"{name.ljust(width)}  {state:<8}  {branch:<24}  {dirty}")
    missing = sum(1 for r in rows if r[1] == "missing")
    info(
        f"\n{len(rows)} repo(s), {missing} missing. Run 'repofleet sync' to reconcile."
    )
    return 0


def cmd_clone(args) -> int:
    config = load(args)
    specs = select(config.repos, args)
    if not require_repos(specs):
        return 1
    root = resolve_root(config, args)
    header(config, root, args)
    if not args.dry_run:
        root.mkdir(parents=True, exist_ok=True)

    results = run_all(
        specs,
        lambda spec: clone_repo(spec, root, remote=config.remote, dry_run=args.dry_run),
        jobs=config.jobs,
        quiet=args.quiet,
    )
    return summarize(results, "Clone summary")


def cmd_update(args) -> int:
    config = load(args)
    specs = select(config.repos, args)
    if not require_repos(specs):
        return 1
    root = resolve_root(config, args)
    header(config, root, args)

    stash = not args.no_stash and config.stash
    prune = not args.no_prune and config.prune

    def worker(spec: RepoSpec) -> RepoResult:
        if args.clone_missing:
            return sync_repo(spec, root, config.remote, stash, prune, args.dry_run)
        return update_repo(
            spec.path_in(root), spec.branch, config.remote, stash, prune, args.dry_run
        )

    results = run_all(specs, worker, jobs=config.jobs, quiet=args.quiet)
    return summarize(results, "Update summary")


def cmd_sync(args) -> int:
    config = load(args)
    root = resolve_root(config, args)
    header(config, root, args)

    adopted: List[RepoSpec] = []
    if not args.no_adopt and config.autoadopt:
        known = config.urls()
        known_names = {s.name for s in config.repos}
        for spec in discover_repos(root, config.match, config.remote):
            if normalize_url(spec.url) in known or spec.name in known_names:
                continue
            adopted.append(spec)

    specs = select(merge_specs(config.repos, adopted), args)
    if not require_repos(specs):
        return 1
    if not args.dry_run:
        root.mkdir(parents=True, exist_ok=True)

    stash = not args.no_stash and config.stash
    prune = not args.no_prune and config.prune

    results = run_all(
        specs,
        lambda spec: sync_repo(spec, root, config.remote, stash, prune, args.dry_run),
        jobs=config.jobs,
        quiet=args.quiet,
    )

    if adopted and not args.dry_run:
        adopted_names = {s.name for s in adopted}
        written = []
        if config.source:
            # Only persist repos that updated cleanly, so typos/broken clones are not adopted.
            healthy = [s for s in adopted if _ok(results, s.name)]
            written = append_repos(config, healthy)
        for result in results:
            if result.name in adopted_names:
                result.details.append(
                    "added to config"
                    if result.name in {w.name for w in written}
                    else ADOPTED
                )
        if written:
            info(f"\nAdded {len(written)} newly discovered repo(s) to {config.source}:")
            for spec in written:
                info(f"  + {spec.name}  {sanitize_url(spec.url)}")
        elif adopted and not config.source:
            info("\nDiscovered new local repos but there is no config file to update.")
            info("Run 'repofleet init' to create one.")

    return summarize(results, "Sync summary")


def _ok(results, name: str) -> bool:
    return any(r.name == name and r.ok for r in results)


def cmd_add(args) -> int:
    config = load(args)
    if args.name and len(args.urls) > 1:
        error("--name can only be used with a single URL.")
        return 1

    new = [
        RepoSpec.from_url(url, branch=args.branch, name=args.name) for url in args.urls
    ]
    if config.source is None:
        error(
            f"No config file found. Run 'repofleet init' first (creates ./{CONFIG_FILENAMES[0]})."
        )
        return 1

    added = append_repos(config, new)
    if not added:
        info("Nothing added - all URLs are already tracked.")
        return 0
    for spec in added:
        info(f"+ {spec.name}  {sanitize_url(spec.url)}")
    info(f"Updated {config.source}")

    if args.clone:
        root = resolve_root(config, args)
        results = run_all(
            added,
            lambda spec: clone_repo(
                spec, root, remote=config.remote, dry_run=args.dry_run
            ),
            jobs=config.jobs,
            quiet=args.quiet,
        )
        return summarize(results, "Clone summary")
    return 0


def cmd_remove(args) -> int:
    config = load(args)
    if config.source is None:
        error("No config file found; nothing to remove.")
        return 1
    removed = remove_repos(config, args.names)
    if not removed:
        info("No matching repositories in the config.")
        return 1
    for name in removed:
        info(f"- {name}")
    info(f"Updated {config.source}. Directories on disk were left untouched.")
    return 0


# --------------------------------------------------------------------------- entry


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        gitcmd.ensure_git()
        return args.func(args)
    except (ConfigError, gitcmd.GitNotAvailable, ValueError) as exc:
        error(f"error: {exc}")
        return 2
    except KeyboardInterrupt:  # pragma: no cover
        error("interrupted")
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
