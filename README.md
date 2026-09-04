# repofleet

**Clone, update and track a fleet of git repositories from a single declarative config.**

[![PyPI version](https://img.shields.io/pypi/v/repofleet.svg?logo=pypi&logoColor=white&label=PyPI)](https://pypi.org/project/repofleet/)
[![Python versions](https://img.shields.io/pypi/pyversions/repofleet.svg?logo=python&logoColor=white)](https://pypi.org/project/repofleet/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/kavirayuni-dev/repofleet/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/repofleet.svg?label=downloads&color=blue)](https://pypi.org/project/repofleet/)
[![CI](https://github.com/kavirayuni-dev/repofleet/actions/workflows/ci.yml/badge.svg)](https://github.com/kavirayuni-dev/repofleet/actions/workflows/ci.yml)
[![Wheel](https://img.shields.io/pypi/wheel/repofleet.svg)](https://pypi.org/project/repofleet/#files)

---

One command — `repofleet sync` — gets any machine into the same state as everyone else on the team:

- repositories in the list but **not on disk** are cloned,
- repositories already on disk are **fetched, switched to their default branch and pulled** (local
  work is auto-stashed and restored),
- repositories found on disk that are **not in the list yet** are updated and then **added to the
  config**, so the shared list grows organically.

`repofleet` is **host-agnostic and org-agnostic** — nothing is hard-coded to GitHub, Azure DevOps,
GitLab, Bitbucket or any team. Any group can ship its own `repofleet.toml` (or a plain
`repo-urls.txt`) and get an identical, reproducible workflow on Windows, macOS and Linux.

> **Full documentation (open these directly on GitHub — they resolve to the same source that
> generated this README):**
> [📖 Usage guide](https://github.com/kavirayuni-dev/repofleet/blob/main/docs/USAGE.md) ·
> [📘 Team wiki](https://github.com/kavirayuni-dev/repofleet/blob/main/docs/WIKI.md) ·
> [🚀 Publishing guide](https://github.com/kavirayuni-dev/repofleet/blob/main/docs/PUBLISHING.md) ·
> [🗒 Changelog](https://github.com/kavirayuni-dev/repofleet/blob/main/CHANGELOG.md)

---

## Table of contents

- [Why repofleet](#why-repofleet)
- [Feature highlights](#feature-highlights)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Command reference](#command-reference)
- [Global options](#global-options)
- [Configuration](#configuration)
- [How updates work (safety guarantees)](#how-updates-work-safety-guarantees)
- [Auto-adoption](#auto-adoption)
- [Output & exit codes](#output--exit-codes)
- [Authentication](#authentication)
- [Everyday recipes](#everyday-recipes)
- [CI/CD integration](#cicd-integration)
- [Python API](#python-api)
- [Troubleshooting](#troubleshooting)
- [For contributors (cloning this repo)](#for-contributors-cloning-this-repo)
- [Publishing a release](#publishing-a-release)
- [Versioning & changelog](#versioning--changelog)
- [License](#license)
- [Author & links](#author--links)

---

## Why repofleet

Teams that split a product across many git repositories keep repeating the same manual chores:

- new joiners spend their first morning `git clone`-ing 20+ URLs pasted from a wiki page,
- everyone starts the day running `git pull` in every folder — or forgets to, and debugs against
  stale code,
- someone adds a new service repo and announces it on chat; half the team misses it and is silently
  out of date for a week,
- each person's local layout is slightly different, so "it works on my machine" scripts don't
  travel.

`repofleet` replaces all of that with **one shared list and one command**. It is:

- **Declarative** — a single `repofleet.toml` (or a plain URL list) is the source of truth.
- **Self-maintaining** — new local repos are discovered and added to the shared list automatically.
- **Safe** — local work is stashed and restored, and never discarded if a conflict occurs.
- **Cross-platform** — identical behaviour on Windows, macOS and Linux; usable in CI.
- **Zero-lock-in** — everything it does you could have typed yourself; no daemon, cache or server.

---

## Feature highlights

| Feature | What it gives you |
| --- | --- |
| One-shot workspace bring-up | `repofleet sync` clones every missing repo and updates every existing one. |
| Auto-adoption | Local repos not yet in the list are automatically added, so the shared config grows itself. |
| Dirty-repo safety | Uncommitted work is `git stash`-ed before pull and restored after; kept (never dropped) on conflict. |
| Parallel execution | `-j N` processes N repos concurrently. |
| Glob filtering | `--only "svc.*"` / `--exclude "*.legacy"` for surgical runs. |
| Multiple config sources | Nearest `repofleet.toml`, `$REPOFLEET_CONFIG`, user-config dir, or explicit `-c FILE`. |
| Plain-text URL lists | `.txt` / `.list` / `.repos` files with per-line branch overrides. |
| Bundled profile | Ready-made `example-workspace.toml` ships inside the package. |
| Credential-safe output | Tokens embedded in remote URLs are masked; `GIT_TERMINAL_PROMPT=0` avoids hangs. |
| Zero-install launcher | `python bootstrap.py sync` runs the tool straight from an unzipped folder. |
| Rich exit codes | `0` success · `1` a repo failed · `2` config/env error · `130` interrupted. |
| Python API | Import `repofleet.config` / `.operations` / `.runner` and script your own flows. |
| Well-tested | `pytest` suite that spins up real local git repos — no network needed. |

---

## Requirements

- **Python 3.9+** (3.9, 3.10, 3.11, 3.12, 3.13 are all tested on Windows and Linux via CI).
- **git** available on `PATH` — check with `git --version`.
- Working git credentials for your remotes (see [Authentication](#authentication)).

On Windows use `py` in place of `python` if the launcher is what's on your `PATH`.

---

## Installation

`repofleet` is published on PyPI: <https://pypi.org/project/repofleet/>.

### 1. With `pipx` (recommended for a CLI tool)

`pipx` keeps `repofleet` isolated from your project virtualenvs but always on `PATH`.

```bash
python -m pip install --user pipx
python -m pipx ensurepath
pipx install repofleet
```

### 2. With plain `pip`

```bash
pip install repofleet
# or, user-local without a virtualenv:
pip install --user repofleet
```

### 3. Inside a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install repofleet
```

### 4. From a private Python index

For Azure Artifacts, Nexus, Artifactory, JFrog, GitLab package registry, etc.:

```bash
pip install repofleet \
  --index-url https://pkgs.dev.azure.com/<org>/_packaging/<feed>/pypi/simple/
```

### 5. From a source checkout (contributors)

```bash
git clone https://github.com/kavirayuni-dev/repofleet.git
cd repofleet
pip install -e ".[dev]"
pytest -q
```

### 6. Zero-install (unzip + run)

Download the source tarball from PyPI or GitHub, unzip it, and run the bundled launcher — it adds
`src/` to `sys.path` for you:

```bash
python bootstrap.py sync
python bootstrap.py --help
```

### Upgrade

```bash
pipx upgrade repofleet
# or
pip install --upgrade repofleet
```

### Verify the install

```bash
repofleet --version
repofleet --help
```

> If your shell says `repofleet: command not found`, the Python scripts folder is not on `PATH`.
> Either run `python -m repofleet ...`, or reinstall with `pipx` (which manages `PATH` for you).

---

## Quick start

Pick the scenario that matches your situation. All three converge to the same workflow.

### Scenario A — you already have all the repos cloned

Generate the shared list from what's on disk, then keep everything current:

```bash
cd "/path/to/your/workspace"
repofleet init --name "Backend Services" --match "svc.*"
repofleet sync
```

`init` scans the folder, records the `origin` URL of every git repo it finds, and writes
`repofleet.toml` plus an empty `repo-urls.txt` you can paste more URLs into. Commit both files so
your team can share them.

### Scenario B — you have nothing yet (typical new joiner)

Drop the shared `repofleet.toml` in an empty folder and run:

```bash
repofleet sync
```

Everything is cloned into the workspace directory declared in the config
(`directory = "…"`). An example profile ships with the package at
`src/repofleet/profiles/example-workspace.toml` — copy it, swap in your own URLs, and run:

```bash
repofleet sync -c example-workspace.toml
```

### Scenario C — you just want a list of URLs cloned somewhere

```bash
repofleet clone --repos-file repo-urls.txt --root ./workspace
```

No config file is created — this is a one-shot clone.

---

## Command reference

| Command | What it does |
| --- | --- |
| `repofleet init` | Create a config (`repofleet.toml` + `repo-urls.txt`) from the repositories found on disk. |
| `repofleet list` | Show every tracked repo, its URL, and whether it is present locally. |
| `repofleet status` | Per-repo branch + clean/dirty state and what is missing. |
| `repofleet clone` | Clone only the repositories that are missing. |
| `repofleet update` | Fetch + pull every cloned repo. Add `--clone-missing` to also clone new ones. |
| `repofleet sync` | Clone missing, update existing, adopt newly discovered local repos into the config. |
| `repofleet add <url…>` | Track new repositories. Use `--clone` to fetch them immediately. |
| `repofleet remove <name…>` | Stop tracking repositories (files on disk are left alone). |

Selected command-specific options (see `repofleet <command> --help` for the full list):

- `init` — `--name`, `--directory`, `--match GLOB…`, `--output FILE`, `--force`, `--no-repos-file`, `--root DIR`.
- `update` / `sync` — `--no-stash` (skip dirty repos instead of stashing), `--no-prune`.
- `update` — `--clone-missing`.
- `sync` — `--no-adopt` (do not write newly discovered repos to the config).
- `add` — `--name`, `--branch`, `--clone`.

Every command supports the [global options](#global-options).

Full flag-by-flag reference:
[docs/USAGE.md § Command reference](https://github.com/kavirayuni-dev/repofleet/blob/main/docs/USAGE.md#5-command-reference).

---

## Global options

Available on every command:

| Option | Default | Meaning |
| --- | --- | --- |
| `-c`, `--config FILE` | auto-discovered | Config file (`.toml`, or `.txt`/`.list`/`.repos`). |
| `--root DIR` | from config | Directory that holds the repositories. |
| `--repos-file FILE` | – | Extra repo list merged into the run (repeatable). |
| `--repo URL` | – | Extra repository given inline (repeatable). |
| `--only PATTERN…` | all | Keep only repos whose name matches a glob. |
| `--exclude PATTERN…` | none | Drop repos whose name matches a glob. |
| `--remote NAME` | `origin` | Remote name to fetch/pull from. |
| `-j`, `--jobs N` | `4` | Repositories processed in parallel. |
| `--dry-run` | off | Print the plan without touching anything. |
| `-q`, `--quiet` | off | Summary only. |
| `--version` | – | Print the version and exit. |

`--only` / `--exclude` use shell-style globs against the **repo name** (folder name), e.g.
`--only "svc.a*" "*.api"`.

---

## Configuration

### `repofleet.toml`

```toml
[workspace]
name       = "Backend Services"    # human-readable workspace name
root       = "auto"                # "auto", or a path relative to this file, or an absolute path
directory  = "Backend Services"    # folder used when root = "auto" and nothing is cloned yet
match      = ["svc.*"]             # which local folder names may be auto-adopted
remote     = "origin"              # remote name used for clone/fetch/pull
repos_file = "repo-urls.txt"       # optional: merge an external URL list into this config

[defaults]
stash     = true    # stash local changes before pulling, restore afterwards
prune     = true    # git fetch --prune
jobs      = 4       # parallel workers
autoadopt = true    # write newly discovered local repos back into this file

[[repos]]
name   = "svc.api"                                # optional — derived from the URL when omitted
url    = "https://github.com/org/svc.api.git"
# branch = "develop"                              # optional — defaults to the remote's default
```

A shorthand table is also accepted:

```toml
[repos]
"svc.api"  = "https://github.com/org/svc.api.git"
"svc.auth" = "https://github.com/org/svc.auth.git"
```

### Plain-text list (`repo-urls.txt`)

The easiest thing to paste into a wiki page, email or Teams/Slack message.
Extensions `.txt`, `.list`, `.repos` are all recognised.

```
# repo-urls.txt
https://github.com/org/svc.api.git
https://github.com/org/tooling.git
custom-folder-name = https://github.com/org/other.git   # alias the directory name
https://github.com/org/legacy.git   release/2024        # pin a branch
```

Rules:

- blank lines and lines starting with `#` are ignored;
- `name = url` sets the directory name;
- a second whitespace-separated token after the URL is the branch.

Use it three ways:

```bash
repofleet sync -c repo-urls.txt              # as the config itself
repofleet sync --repos-file repo-urls.txt    # merged into the current run
```

```toml
[workspace]
repos_file = "repo-urls.txt"                 # permanently referenced from the TOML
```

Repositories that come from `repos_file` are **kept in that file** — they are never inlined into
the TOML when it's rewritten, so the two files stay cleanly separated.

### Config lookup order

1. `--config` / `-c`
2. `$REPOFLEET_CONFIG` (error if the path does not exist)
3. Nearest `repofleet.toml` or `.repofleet.toml`, walking up from the current directory
4. `%APPDATA%\repofleet\repofleet.toml` (Windows) or
   `${XDG_CONFIG_HOME:-~/.config}/repofleet/repofleet.toml`

Auto-discovery only matches the names `repofleet.toml` / `.repofleet.toml`. If you copied a file
called `example-workspace.toml`, either rename it or pass `-c example-workspace.toml` every time.

### Where the repos end up (workspace root resolution)

1. `--root` if given — wins over everything.
2. `[workspace] root` if it is not `"auto"` — relative paths resolve against **the config file's
   folder**, so a shared config behaves identically on every machine.
3. `"auto"` (the default):
   - if the config's folder already contains at least one git repo → use that folder;
   - otherwise → use `<config folder>/<directory>` (falling back to `name`).

Print the resolved root anytime with `repofleet status`.

---

## How updates work (safety guarantees)

For each repository, `update` / `sync` runs:

1. `git fetch --prune <remote>`
2. work out the target branch — the repo's `branch` from the config, else `<remote>/HEAD`, else
   the first of `main`, `master`, `develop` that exists;
3. if the working tree is dirty → `git stash push -u -m "repofleet: auto-stash before update"`
   (with `--no-stash` the repo is reported `skipped` and left completely alone);
4. `git checkout <branch>`;
5. `git pull --ff-only`, falling back to a merge pull **only** if fast-forward is impossible;
6. `git stash pop` to restore your work.

### Guarantees

- **Your work is never discarded.** If `git stash pop` fails (e.g. a merge conflict), the stash is
  *kept* and the repo is reported as `failed` with the git message. Recover with
  `git stash list` / `git stash pop`.
- If `checkout` or `pull` fails **after** stashing, the stash is popped back before reporting.
- A failing repo never aborts the run — every repo is attempted and reported at the end.
- Git is always invoked with an argument list, never through a shell.
- `GIT_TERMINAL_PROMPT=0` prevents a batch run from hanging on a credential prompt.
- Any credentials embedded in a remote URL are masked (`https://***@host/...`) in all output.
- `repofleet remove` only edits the config — it never deletes directories.

---

## Auto-adoption

During `sync`, `repofleet` scans the workspace root for git repositories that match
`[workspace] match` but are not in the config. Those repos are updated like any other, and — only
if the update succeeded — appended to the config file:

```
Added 1 newly discovered repo(s) to C:\...\repofleet.toml:
  + svc.newservice  https://github.com/org/svc.newservice.git
```

When a colleague adds a repo, whoever runs `sync` next automatically pushes it into the shared
list. Disable per-run with `--no-adopt`, or permanently with `autoadopt = false` under
`[defaults]`. Adoption never runs for `clone` or `update`, only for `sync`.

---

## Output & exit codes

```
config : C:\code\Backend Services\repofleet.toml
root   : C:\code\Backend Services
  [+] svc.api: updated
  [x] svc.auth: failed

--------------------------------------------------
Sync summary
--------------------------------------------------
svc.api   updated
          - on main
          - Fast-forward
svc.auth  failed
          - git pull failed: ...
--------------------------------------------------
2 repo(s): 1 failed, 1 updated
```

Per-repo actions:

| Action | Meaning |
| --- | --- |
| `cloned` | Freshly cloned. |
| `updated` | Pulled new commits. |
| `up to date` | Already current. |
| `skipped` | Nothing to do (already cloned, dirty with `--no-stash`, or a dry run). |
| `missing` | Listed but not cloned yet — run `clone` or `sync`. |
| `failed` | Git reported an error; details follow on the next lines. |

`[+]` marks success, `[x]` marks failure. Use `-q` to hide progress lines and print only the
summary.

Exit codes:

| Code | Meaning |
| --- | --- |
| `0` | Everything succeeded. |
| `1` | At least one repo failed or was missing, or nothing was selected. |
| `2` | Configuration or environment error (bad TOML, git missing, bad arguments). |
| `130` | Interrupted with Ctrl+C. |

Safe to gate CI on: `repofleet sync -q || echo "fleet is out of date"`.

---

## Authentication

`repofleet` shells out to `git`, so it uses whatever credentials `git` already has. It sets
`GIT_TERMINAL_PROMPT=0`, so a batch run **fails fast instead of hanging** on a password prompt.

Set up credentials once, before your first run:

- **Windows** — Git Credential Manager ships with Git for Windows. Clone one repo manually, sign
  in via the browser popup; every later run is silent.
- **macOS / Linux** — `git config --global credential.helper osxkeychain` (or `store`), or use
  SSH keys with `ssh-agent`.
- **SSH** — put SSH URLs (`git@host:org/repo.git`) in the config and load your key with
  `ssh-agent`.
- **Azure DevOps** — a PAT with *Code (Read)* works with GCM, or use
  `git config --global credential.https://dev.azure.com.useHttpPath true`.

> **Never commit a token.** Don't paste `https://user:TOKEN@host/…` into a shared config file.
> `repofleet` masks credentials in the console, but the file itself would still contain the secret
> in plain text.

---

## Everyday recipes

```bash
# Morning refresh of everything, 8 repos at a time
repofleet sync -j 8

# See what sync would do, without touching anything
repofleet sync --dry-run

# Only the alerting services
repofleet update --only "svc.alerts*"

# Everything except the noisy ones
repofleet update --exclude "*.scripts" "*.wiki"

# What is missing on this machine?
repofleet status

# Clone the missing repos only, leave existing ones untouched
repofleet clone

# Update but never touch a dirty working tree
repofleet update --no-stash

# Track a brand-new service and clone it in one go
repofleet add https://github.com/org/svc.newservice.git --clone

# One-off list from a colleague, into a scratch folder
repofleet clone --repos-file colleague-repos.txt --root ./scratch

# Point at a config living somewhere else
repofleet sync -c "D:/configs/team.toml"
REPOFLEET_CONFIG=/etc/repofleet/team.toml repofleet sync
```

---

## CI/CD integration

### GitHub Actions

```yaml
- uses: actions/setup-python@v5
  with: { python-version: "3.12" }
- run: pip install repofleet
- run: repofleet clone --root workspace -c repofleet.toml -q -j 8 --no-stash
```

### Azure Pipelines

```yaml
steps:
  - task: UsePythonVersion@0
    inputs: { versionSpec: "3.11" }
  - script: pip install repofleet
    displayName: Install repofleet
  - script: |
      repofleet clone --root $(Build.SourcesDirectory)/workspace \
                      -c repofleet.toml -q -j 8 --no-stash
    displayName: Clone the fleet
```

### Tips for CI

- Prefer `clone` (or `update --clone-missing`) over `sync` so the config is never rewritten by a
  build.
- Add `--no-stash` — a CI checkout should never be dirty, and this makes surprises visible.
- `-q` keeps logs short; the summary and the exit code are all you need.

---

## Python API

The building blocks are importable if you want to script something custom:

```python
from pathlib import Path

from repofleet.config import load_config
from repofleet.operations import sync_repo
from repofleet.runner import run_all, summarize

config = load_config(Path("repofleet.toml"))
root = config.resolve_root()

results = run_all(
    config.repos,
    lambda spec: sync_repo(spec, root, config.remote),
    jobs=config.jobs,
)
exit_code = summarize(results, "My custom run")
```

Useful symbols:

| Symbol | Purpose |
| --- | --- |
| `repofleet.config.load_config` / `save_config` / `append_repos` / `remove_repos` | Read and write configs. |
| `repofleet.config.FleetConfig` | Resolved settings, `resolve_root()`, `repos`. |
| `repofleet.models.RepoSpec` / `RepoResult` | Repository declaration and per-repo outcome. |
| `repofleet.operations.clone_repo` / `update_repo` / `sync_repo` | Single-repo operations. |
| `repofleet.discovery.discover_repos` | Find git repos on disk. |
| `repofleet.runner.run_all` / `summarize` | Parallel execution and reporting. |
| `repofleet.cli.main(argv)` | Run the CLI programmatically; returns the exit code. |

The CLI surface and TOML schema are the **stable public contract**; internal modules under
`repofleet.*` may change between minor versions.

---

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `error: 'git' was not found on PATH` | Install git, or open a new shell so `PATH` refreshes. |
| `repofleet: command not found` | The scripts folder isn't on `PATH`. Use `python -m repofleet …`, or install with `pipx`. |
| `git clone failed: … could not read Username` | Credentials are missing; prompts are disabled on purpose. Clone one repo manually to store credentials, or switch to SSH. |
| `No repositories selected` | Config has no repositories yet. Paste URLs into `repo-urls.txt`, or run `repofleet add <url>`, or pass `--repo` / `--repos-file`. |
| `config : <none - using CLI arguments>` | No config found. Auto-discovery only matches `repofleet.toml` / `.repofleet.toml` — rename your file or pass `-c <file>`. |
| Repos cloned into an unexpected folder | See [workspace root resolution](#where-the-repos-end-up-workspace-root-resolution). Run `repofleet status` to print the resolved root, or pass `--root`. |
| `pull succeeded but 'git stash pop' failed - stash kept` | Your stashed changes conflict with the new commits. `cd` into the repo, resolve, then `git stash pop`. |
| `<path> exists and is not an empty git repo` | A non-git folder occupies the target name. Rename it, or alias the repo with `name = url`. |
| A repo is skipped every run | It has local changes and you passed `--no-stash`, or it is filtered by `--only` / `--exclude`. |
| New repos are not added to the config | Adoption is `sync`-only. Check that you didn't pass `--no-adopt`, that `autoadopt = true`, and that the folder name matches `[workspace] match`. |
| `Invalid TOML in …` | Syntax error in the config; the message includes the line. |
| Slow runs | Raise `-j`, or narrow the set with `--only`. |

More cases:
[docs/USAGE.md § Troubleshooting](https://github.com/kavirayuni-dev/repofleet/blob/main/docs/USAGE.md#17-troubleshooting).

---

## For contributors (cloning this repo)

If you cloned the source (rather than `pip install`-ed the package) and want to hack on it:

```bash
git clone https://github.com/kavirayuni-dev/repofleet.git
cd repofleet
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Unix: source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
repofleet --help
```

The test suite creates real local git repositories in a temp folder — **no network access is
needed**.

### Project layout

```
repofleet/
├── bootstrap.py                # zero-install launcher
├── pyproject.toml
├── README.md                   # this file
├── CHANGELOG.md
├── LICENSE
├── MANIFEST.in
├── docs/
│   ├── USAGE.md                # full developer usage guide
│   ├── WIKI.md                 # team wiki page (rollout, onboarding)
│   └── PUBLISHING.md           # how to cut a release
├── src/repofleet/
│   ├── __init__.py             # __version__
│   ├── __main__.py             # python -m repofleet
│   ├── cli.py                  # argparse commands
│   ├── config.py               # config load/save/merge, root resolution
│   ├── discovery.py            # find repos on disk
│   ├── gitcmd.py               # safe git wrapper
│   ├── models.py               # RepoSpec / RepoResult, URL helpers
│   ├── operations.py           # clone / update / sync one repo
│   ├── runner.py               # parallelism + console output
│   └── profiles/               # bundled ready-made repo lists
└── tests/                      # pytest suite (no network)
```

### Adding a command

1. Define it in `build_parser()` in `src/repofleet/cli.py`.
2. Implement `cmd_<name>(args)` in the same module.
3. Add coverage in `tests/test_cli.py`.
4. Document new flags in `README.md` and `docs/USAGE.md`.

### Reporting issues / requesting features

Please open an issue at
[github.com/kavirayuni-dev/repofleet/issues](https://github.com/kavirayuni-dev/repofleet/issues)
with:

- your OS and `python --version` / `git --version`,
- the exact command you ran,
- the full output (with `-q` disabled),
- your `repofleet.toml` (with any credentials scrubbed).

---

## Publishing a release

Maintainers only. Full checklist in
[docs/PUBLISHING.md](https://github.com/kavirayuni-dev/repofleet/blob/main/docs/PUBLISHING.md).

Short version:

```bash
# 1. Bump versions
#    - pyproject.toml           [project] version
#    - src/repofleet/__init__.py __version__
#    - CHANGELOG.md              add a new [X.Y.Z] section

# 2. Test + build
pytest -q
python -m build
twine check --strict dist/*

# 3. Tag + release (Trusted Publishing via GitHub Actions handles the upload)
git commit -am "release: vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
gh release create vX.Y.Z --generate-notes
```

The [`publish.yml`](https://github.com/kavirayuni-dev/repofleet/blob/main/.github/workflows/publish.yml)
workflow runs the tests, verifies the tag matches `[project] version`, builds, and uploads to
PyPI via [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) — no API tokens are
stored in the repo.

---

## Versioning & changelog

`repofleet` follows [Semantic Versioning](https://semver.org/):

- **patch** — bug fixes, output tweaks, doc updates;
- **minor** — new commands / flags / config keys (backwards compatible);
- **major** — changes to the config format, command names, or exit-code meanings.

The **CLI surface** and **TOML schema** are the public contract; modules under `repofleet.*` may
change in minor releases.

Release history:
[CHANGELOG.md](https://github.com/kavirayuni-dev/repofleet/blob/main/CHANGELOG.md).

---

## License

Released under the [MIT License](https://github.com/kavirayuni-dev/repofleet/blob/main/LICENSE).

Copyright © 2026 Srivathsa Kavirayuni.

---

## Author & links

- **Author:** Srivathsa Kavirayuni — <kavirayuni.dev@gmail.com>
- **PyPI:** <https://pypi.org/project/repofleet/>
- **Source:** <https://github.com/kavirayuni-dev/repofleet>
- **Issues:** <https://github.com/kavirayuni-dev/repofleet/issues>
- **Usage guide:** <https://github.com/kavirayuni-dev/repofleet/blob/main/docs/USAGE.md>
- **Team wiki:** <https://github.com/kavirayuni-dev/repofleet/blob/main/docs/WIKI.md>
- **Publishing guide:** <https://github.com/kavirayuni-dev/repofleet/blob/main/docs/PUBLISHING.md>
- **Changelog:** <https://github.com/kavirayuni-dev/repofleet/blob/main/CHANGELOG.md>

If `repofleet` saves your team time, please ⭐ the repo — it helps others find it.
