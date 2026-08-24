"""Parallel execution and console reporting."""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Callable, Iterable, List, Sequence

from repofleet.models import FAILED, MISSING, RepoResult, RepoSpec

_print_lock = Lock()


def info(message: str = "") -> None:
    with _print_lock:
        print(message, flush=True)


def error(message: str) -> None:
    with _print_lock:
        print(message, file=sys.stderr, flush=True)


def run_all(
    specs: Sequence[RepoSpec],
    worker: Callable[[RepoSpec], RepoResult],
    jobs: int = 4,
    quiet: bool = False,
) -> List[RepoResult]:
    if not specs:
        return []
    jobs = max(1, min(jobs, len(specs)))
    results: List[RepoResult] = []

    def wrapped(spec: RepoSpec) -> RepoResult:
        try:
            result = worker(spec)
        except Exception as exc:  # noqa: BLE001 - one repo must not kill the run
            result = RepoResult.failure(spec.name, f"{type(exc).__name__}: {exc}")
        if not quiet:
            marker = "x" if not result.ok else "+"
            info(f"  [{marker}] {result.name}: {result.action}")
        return result

    if jobs == 1:
        results = [wrapped(spec) for spec in specs]
    else:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            results = list(pool.map(wrapped, specs))
    return results


def summarize(results: Iterable[RepoResult], title: str = "Summary") -> int:
    results = list(results)
    if not results:
        info("Nothing to do.")
        return 0

    width = max(len(r.name) for r in results)
    line = "-" * min(88, width + 40)
    info("")
    info(line)
    info(f"{title}")
    info(line)
    for result in sorted(results, key=lambda r: (r.ok, r.name.lower())):
        info(f"{result.name.ljust(width)}  {result.action}")
        for detail in result.details:
            info(f"{' ' * width}  - {detail}")
    info(line)

    failed = [r for r in results if not r.ok]
    counts = {}
    for result in results:
        counts[result.action] = counts.get(result.action, 0) + 1
    breakdown = ", ".join(
        f"{count} {action}" for action, count in sorted(counts.items())
    )
    info(f"{len(results)} repo(s): {breakdown}")
    if failed:
        error(
            "Failed: "
            + ", ".join(r.name for r in failed if r.action in (FAILED, MISSING))
        )
    return 1 if failed else 0
