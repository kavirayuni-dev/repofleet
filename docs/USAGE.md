# repofleet — Developer Usage Guide

A complete, task-oriented guide to installing, configuring and running `repofleet`.
For a quick overview see the [README](../README.md).

---

## Table of contents

1. [What repofleet does](#1-what-repofleet-does)
2. [Requirements](#2-requirements)
3. [Installation](#3-installation)
4. [First run — three scenarios](#4-first-run--three-scenarios)
5. [Command reference](#5-command-reference)
6. [Global options](#6-global-options)
7. [Configuration files](#7-configuration-files)
8. [How the workspace root is resolved](#8-how-the-workspace-root-is-resolved)
9. [How updates work (and what happens to your local changes)](#9-how-updates-work-and-what-happens-to-your-local-changes)
10. [Auto-adoption: growing the shared list](#10-auto-adoption-growing-the-shared-list)
11. [Reading the output](#11-reading-the-output)
12. [Exit codes](#12-exit-codes)
13. [Authentication](#13-authentication)
14. [Everyday recipes](#14-everyday-recipes)
15. [Using repofleet in CI](#15-using-repofleet-in-ci)
16. [Sharing with your team](#16-sharing-with-your-team)
17. [Troubleshooting](#17-troubleshooting)
18. [Python API](#18-python-api)
19. [Contributing / local development](#19-contributing--local-development)

---

## 1. What repofleet does

Teams that split a product across many git repositories keep repeating the same chores: clone the
right set of repos on a new laptop, pull them all every morning, and remember which new repo a
colleague added last week.

`repofleet` turns that into one declarative list plus one command:

```bash
repofleet sync
```

| Situation on your machine | What `sync` does |
| --- | --- |
| Repo is in the list, not on disk | `git clone` it into the workspace root |
| Repo is in the list and on disk | fetch, switch to the default branch, pull (stashing/restoring local work) |
| Repo is on disk but not in the list | update it, then **add it to the config file** |
| Repo is in the list but you don't want it | filter it out with `--exclude`, or `repofleet remove` |

Nothing is hard-coded to a company, host or naming scheme — any team can ship its own list.

---

## 2. Requirements

- **Python 3.9 or newer** (`tomli` is installed automatically on 3.9/3.10; 3.11+ uses `tomllib`).
- **git** available on `PATH`. Verify with `git --version`.
- Working git credentials for your remotes (see [Authentication](#13-authentication)).

Windows, macOS and Linux are all supported. On Windows use `py` if `python` is not on `PATH`.

---

## 3. Installation

### From your package index (once published)

```bash
pip install repofleet
```

For a private Azure Artifacts / Nexus / Artifactory feed:

```bash
pip install repofleet --index-url https://pkgs.dev.azure.com/<org>/_packaging/<feed>/pypi/simple/
```

### With pipx (keeps it out of your project virtualenvs)

```bash
pipx install repofleet
```

### From a checkout

```bash
cd repofleet
pip install -e ".[dev]"
```

### Without installing anything

Unzip the project folder and use the bundled launcher — it adds `src/` to `sys.path` for you:

```bash
python bootstrap.py sync
python bootstrap.py --help
```

### Verify

```bash
repofleet --version
repofleet --help
```

---

## 4. First run — three scenarios

### A. You already have all the repos cloned

Generate the list from what is on disk, then keep everything current:

```bash
cd "/path/to/your/workspace"
repofleet init --name "Portfolios Backend" --match "portfolios.*"
repofleet sync
```

`init` writes `repofleet.toml` next to you, containing one entry per git repo it found
(the `origin` URL of each). Commit or share that file.

### B. You have nothing yet (new joiner)

Put the shared `repofleet.toml` (or `team-repos.txt`) in an empty folder and run:

```bash
repofleet sync
```

Every repo is cloned into the workspace directory declared by the config
(`directory = "..."`), e.g. `./Portfolios Backend/portfolios.api`.

### C. You just want to clone a list of URLs, no config file

```bash
repofleet clone --repos-file team-repos.txt --root ./workspace
repofleet clone --repo https://github.com/org/a.git --repo https://github.com/org/b.git --root ./workspace
```

---

## 5. Command reference

### `repofleet init`

Create a configuration file from the repositories found on disk.

| Option | Meaning |
| --- | --- |
| `--name NAME` | Workspace name written to the config. |
| `--directory DIR` | Folder name used when repos still need to be cloned. |
| `--match GLOB [GLOB...]` | Only track folders whose names match (default `*`). |
| `--output FILE` | Where to write (default `./repofleet.toml`). |
| `--force` | Overwrite an existing config. |
| `--root DIR` | Folder to scan (default: the config's own folder). |

```bash
repofleet init --name "Portfolios Backend" --directory "Portfolios Backend" --match "portfolios.*"
repofleet init --root ~/code --output ~/code/repofleet.toml --force
repofleet init --dry-run          # show what would be recorded
```

### `repofleet list`

Show every tracked repository, its URL, and whether it is present locally.

```bash
repofleet list
repofleet list --only "portfolios.a*"
```

### `repofleet status`

Per-repo local state: present/missing, current branch, clean/dirty.

```bash
repofleet status
repofleet status --exclude "*.scripts"
```

### `repofleet clone`

Clone only the repositories that are missing. Repos already present are reported as `skipped`.

```bash
repofleet clone
repofleet clone --only portfolios.api
repofleet clone --repos-file team-repos.txt --root ./workspace -j 8
```

### `repofleet update`

Fetch and pull every repository that is already cloned.

| Option | Meaning |
| --- | --- |
| `--clone-missing` | Also clone repos that are not present yet. |
| `--no-stash` | Skip repos with local changes instead of stashing them. |
| `--no-prune` | Do not pass `--prune` to `git fetch`. |

```bash
repofleet update
repofleet update --only "portfolios.a*" -j 8
repofleet update --no-stash          # leave dirty repos completely untouched
```

### `repofleet sync`

The everyday command: clone missing + update existing + adopt new local repos.

| Option | Meaning |
| --- | --- |
| `--no-adopt` | Do not write newly discovered local repos into the config. |
| `--no-stash`, `--no-prune` | Same as for `update`. |

```bash
repofleet sync
repofleet sync --dry-run
repofleet sync --no-adopt --exclude "*.experimental"
```

### `repofleet add <url...>`

Track one or more new repositories.

| Option | Meaning |
| --- | --- |
| `--name NAME` | Directory name (only with a single URL). |
| `--branch BRANCH` | Pin the repo to a branch. |
| `--clone` | Clone immediately after adding. |

```bash
repofleet add https://dev.azure.com/org/Proj/_git/portfolios.newservice --clone
repofleet add https://github.com/org/tooling.git --name tools --branch develop
```

New entries are **appended** to the config file, so comments and formatting you added by hand are
preserved. Duplicate URLs are ignored (comparison ignores case, `.git` and embedded credentials).

### `repofleet remove <name...>`

Stop tracking repositories. **Only the config file is edited — nothing on disk is deleted.**

```bash
repofleet remove portfolios.legacy portfolios.spike
```

---

## 6. Global options

Every command accepts these:

| Option | Default | Meaning |
| --- | --- | --- |
| `-c, --config FILE` | auto-discovered | Config file (`.toml`, or `.txt`/`.list`/`.repos` for a plain list). |
| `--root DIR` | from config | Directory that holds the repositories. |
| `--repos-file FILE` | – | Extra repo list merged into the run. Repeatable. |
| `--repo URL` | – | Extra repository given inline. Repeatable. |
| `--only PATTERN...` | all | Keep only repos whose name matches a glob. |
| `--exclude PATTERN...` | none | Drop repos whose name matches a glob. |
| `--remote NAME` | `origin` | Remote name to fetch/pull from. |
| `-j, --jobs N` | `4` (config) | Repositories processed in parallel. |
| `--dry-run` | off | Print the plan, change nothing. |
| `-q, --quiet` | off | Suppress per-repo progress; print only the summary. |
| `--version` | – | Print the version and exit. |

`--only` / `--exclude` use shell-style globs against the **repo name** (the folder name), e.g.
`--only "portfolios.a*" "*.api"`.

---

## 7. Configuration files

### 7.1 `repofleet.toml`

```toml
[workspace]
name      = "Portfolios Backend"   # human-readable workspace name
root      = "auto"                 # "auto", or a path relative to this file, or absolute
directory = "Portfolios Backend"   # folder created when root = "auto" and nothing is cloned yet
match     = ["portfolios.*"]       # which local folders may be auto-adopted
remote    = "origin"               # remote name used for clone/fetch/pull
# repos_file = "team-repos.txt"    # optional: merge an external list into this config

[defaults]
stash     = true    # stash local changes before pulling, restore afterwards
prune     = true    # git fetch --prune
jobs      = 4       # parallel workers
autoadopt = true    # write newly discovered local repos back into this file

[[repos]]
name   = "portfolios.api"                                   # optional, derived from the URL
url    = "https://dev.azure.com/org/Proj/_git/portfolios.api"
branch = "main"                                             # optional, defaults to remote HEAD
```

A shorthand table is also accepted:

```toml
[repos]
"portfolios.api"  = "https://dev.azure.com/org/Proj/_git/portfolios.api"
"portfolios.auth" = "https://dev.azure.com/org/Proj/_git/portfolios.auth"
```

### 7.2 Plain text list

The easiest thing to paste into a wiki or e-mail. Extensions `.txt`, `.list`, `.repos`.

```
# team-repos.txt
https://dev.azure.com/org/Proj/_git/portfolios.api        # comment after two spaces + #
https://github.com/org/tooling.git
custom-folder-name = https://github.com/org/other.git      # alias the directory name
https://github.com/org/legacy.git   release/2024           # pin a branch
```

Rules:

- blank lines and lines starting with `#` are ignored;
- `name = url` sets the directory name;
- a second whitespace-separated token after the URL is the branch.

Use it with `-c team-repos.txt`, `--repos-file team-repos.txt`, or `repos_file` in the TOML.

### 7.3 Where the config is found

In order:

1. `--config` / `-c`
2. `$REPOFLEET_CONFIG` (error if the path does not exist)
3. the nearest `repofleet.toml` or `.repofleet.toml`, walking up from the current directory
4. `%APPDATA%\repofleet\repofleet.toml` (Windows) or `${XDG_CONFIG_HOME:-~/.config}/repofleet/repofleet.toml`

If none is found, commands still work with `--repo` / `--repos-file`, but `add`, `remove` and
adoption have nowhere to write and will tell you to run `repofleet init`.

### 7.4 Bundled profiles

Ready-made lists ship inside the package under `repofleet/profiles/`, e.g.
`polaris-portfolios.toml`. Copy one next to your workspace and run:

```bash
repofleet sync -c polaris-portfolios.toml
```

---

## 8. How the workspace root is resolved

1. `--root` if given (wins over everything).
2. `[workspace] root` if it is not `"auto"` — relative paths are resolved against the **config
   file's folder**, so a shared config behaves the same on every machine.
3. `"auto"` (default):
   - if the config file's folder already contains at least one git repository → use that folder;
   - otherwise → use `<config folder>/<directory>` (falling back to `name`).

This is what lets the *same* config work for a veteran whose repos already sit next to the config
and for a new joiner who gets everything cloned into a fresh `Portfolios Backend/` folder.

Check what will be used with:

```bash
repofleet status        # prints "config :" and "root :" headers
```

---

## 9. How updates work (and what happens to your local changes)

For each repository, `update`/`sync` performs:

1. `git fetch --prune <remote>`
2. determine the target branch: the repo's `branch` from the config, else `<remote>/HEAD`, else the
   first of `main`, `master`, `develop` that exists;
3. if the working tree is dirty → `git stash push -u -m "repofleet: auto-stash before update"`
   (with `--no-stash` the repo is reported `skipped` and left alone);
4. `git checkout <branch>`;
5. `git pull --ff-only <remote> <branch>`, falling back to a normal merge pull only if
   fast-forward is impossible;
6. `git stash pop` to restore your work.

Guarantees:

- **Your work is never discarded.** If `stash pop` fails (e.g. a conflict), the stash is *kept* and
  the repo is reported as `failed` with the git message; recover with `git stash list` /
  `git stash pop`.
- A failing repo never aborts the run — every repo is reported at the end.
- If checkout or pull fails after stashing, repofleet pops the stash back before reporting.

---

## 10. Auto-adoption: growing the shared list

During `sync`, repofleet scans the workspace root for git repositories that match
`[workspace] match` but are not in the config. Those repos are updated like any other, and then —
only if the update succeeded — appended to the config file:

```
Added 1 newly discovered repo(s) to C:\...\repofleet.toml:
  + portfolios.newservice  https://dev.azure.com/org/Proj/_git/portfolios.newservice
```

So when a colleague adds a repo, whoever clones it first pushes it into the shared list simply by
running `sync`. Disable per-run with `--no-adopt`, or permanently with `autoadopt = false`.

Adoption never runs for `clone` or `update`, only for `sync`.

---

## 11. Reading the output

```
config : C:\code\Portfolios Backend\repofleet.toml
root   : C:\code\Portfolios Backend
  [+] portfolios.api: updated
  [x] portfolios.auth: failed
...
--------------------------------------------------
Sync summary
--------------------------------------------------
portfolios.api   updated
                 - on main
                 - Fast-forward
portfolios.auth  failed
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
| `skipped` | Nothing to do (already cloned / dirty with `--no-stash` / dry run). |
| `missing` | Listed but not cloned — run `clone` or `sync`. |
| `failed` | Git reported an error; details follow on the next lines. |

`[+]` = success, `[x]` = failure. Use `-q` to hide the progress lines.

---

## 12. Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Everything succeeded. |
| `1` | At least one repository failed or was missing / nothing selected. |
| `2` | Configuration or environment error (bad TOML, git not installed, bad arguments). |
| `130` | Interrupted with Ctrl+C. |

Safe to use in scripts: `repofleet sync -q || echo "fleet is out of date"`.

---

## 13. Authentication

repofleet shells out to `git`, so it uses whatever credentials git already has. It deliberately
sets `GIT_TERMINAL_PROMPT=0`, so a batch run **fails fast instead of hanging** on a password
prompt.

Set up credentials once, before your first run:

- **Windows**: Git Credential Manager (bundled with Git for Windows) — clone one repo manually and
  sign in; every later run is silent.
- **macOS/Linux**: `git config --global credential.helper store` / `osxkeychain`, or use SSH keys.
- **SSH**: put SSH URLs (`git@host:org/repo.git`) in the config and load your key with `ssh-agent`.
- **Azure DevOps**: a PAT with *Code (Read)* works with Git Credential Manager, or use
  `git config --global credential.https://dev.azure.com.useHttpPath true`.

Any credentials embedded in a URL are masked (`https://***@host/...`) in all console output, but
avoid committing tokens to a shared config file.

---

## 14. Everyday recipes

```bash
# Morning refresh of everything, 8 at a time
repofleet sync -j 8

# See what sync would do, without touching anything
repofleet sync --dry-run

# Only the alerting services
repofleet update --only "portfolios.alerts*"

# Everything except the noisy ones
repofleet update --exclude "*.scripts" "*.wiki"

# What is missing on this machine?
repofleet status

# Clone the missing repos only, leave existing ones untouched
repofleet clone

# Update but never touch a dirty working tree
repofleet update --no-stash

# Track a brand-new service and clone it in one go
repofleet add https://dev.azure.com/org/Proj/_git/portfolios.newservice --clone

# One-off list from a colleague, into a scratch folder
repofleet clone --repos-file colleague-repos.txt --root ./scratch

# Point at a config living somewhere else
repofleet sync -c "D:/configs/team.toml"
REPOFLEET_CONFIG=/etc/repofleet/team.toml repofleet sync
```

---

## 15. Using repofleet in CI

```yaml
# Azure Pipelines
steps:
  - task: UsePythonVersion@0
    inputs: { versionSpec: '3.11' }
  - script: pip install repofleet
    displayName: Install repofleet
  - script: repofleet clone --root $(Build.SourcesDirectory)/workspace -c repofleet.toml -q -j 8
    displayName: Clone the fleet
```

```yaml
# GitHub Actions
- run: pip install repofleet
- run: repofleet clone --root workspace -c repofleet.toml -q -j 8
```

Tips for CI:

- prefer `clone` (or `update --clone-missing`) over `sync` so the config is never rewritten;
- add `--no-stash` — CI checkouts should never be dirty, and this makes surprises visible;
- `-q` keeps logs short; the summary and exit code are all you need.

---

## 16. Sharing with your team

Three ways, pick what fits:

1. **Publish the package** (see [PUBLISHING.md](PUBLISHING.md)) and share just the config file.
   Teammates run `pip install repofleet` then `repofleet sync`.
2. **Zip the project folder.** Teammates unzip and run `python bootstrap.py sync` — no install, no
   virtualenv.
3. **Commit `repofleet.toml`** into an existing repo (or a wiki page as a `team-repos.txt`) and let
   people point at it with `-c`.

Keep the shared config authoritative by letting `sync` adopt new repos, and review the appended
entries in your normal code-review flow.

---

## 17. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `error: 'git' was not found on PATH` | Install git, or open a new shell so `PATH` is refreshed. |
| `repofleet: command not found` | The scripts folder is not on `PATH`. Use `python -m repofleet ...` or `pipx install repofleet`. |
| `git clone failed: ... could not read Username` | Credentials are missing; prompts are disabled on purpose. Clone one repo manually to store credentials, or switch to SSH. |
| `No repositories selected` | No config was found and no `--repo`/`--repos-file` was given. Run `repofleet init`. |
| Repos cloned into an unexpected folder | See [root resolution](#8-how-the-workspace-root-is-resolved); run `repofleet status` to print the resolved root, or pass `--root`. |
| `pull succeeded but 'git stash pop' failed - stash kept` | Your stashed changes conflict with the new commits. `cd` into the repo and resolve, then `git stash pop`. |
| `<path> exists and is not an empty git repo` | A non-git folder occupies the target name. Rename/remove it, or alias the repo with `name = url`. |
| A repo is skipped every run | It has local changes and you passed `--no-stash`, or it is filtered by `--only`/`--exclude`. |
| New repos are not added to the config | You used `clone`/`update` (adoption is `sync`-only), `--no-adopt` is set, `autoadopt = false`, or the folder name does not match `[workspace] match`. |
| `Invalid TOML in ...` | Syntax error in the config; the message includes the line. |
| Slow runs | Increase `-j`, or narrow the set with `--only`. |

---

## 18. Python API

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

Useful pieces:

| Symbol | Purpose |
| --- | --- |
| `repofleet.config.load_config / save_config / append_repos / remove_repos` | Read and write configs. |
| `repofleet.config.FleetConfig` | Resolved settings, `resolve_root()`, `repos`. |
| `repofleet.models.RepoSpec / RepoResult` | Repository declaration and per-repo outcome. |
| `repofleet.operations.clone_repo / update_repo / sync_repo` | Single-repo operations. |
| `repofleet.discovery.discover_repos` | Find git repos on disk. |
| `repofleet.runner.run_all / summarize` | Parallel execution and reporting. |
| `repofleet.cli.main(argv)` | Run the CLI programmatically; returns the exit code. |

The CLI surface is the stable contract; internal modules may change between minor versions.

---

## 19. Contributing / local development

```bash
cd repofleet
pip install -e ".[dev]"
pytest -q
```

The test suite creates real local git repositories in a temp folder, so no network access is
needed. Layout:

```
repofleet/
├── bootstrap.py              # run without installing
├── pyproject.toml
├── README.md
├── docs/
│   ├── USAGE.md              # this guide
│   └── PUBLISHING.md
├── src/repofleet/
│   ├── cli.py                # argparse commands
│   ├── config.py             # config load/save/merge, root resolution
│   ├── discovery.py          # find repos on disk
│   ├── gitcmd.py             # safe git wrapper
│   ├── models.py             # RepoSpec / RepoResult, URL helpers
│   ├── operations.py         # clone / update / sync one repo
│   ├── runner.py             # parallelism + console output
│   └── profiles/             # bundled ready-made repo lists
└── tests/
```

When adding a command: define it in `build_parser()`, implement `cmd_<name>(args)`, and cover it in
`tests/test_cli.py`.
