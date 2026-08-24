# repofleet

**Clone, update and track a fleet of git repositories from a single declarative config.**

One command (`repofleet sync`) gets any machine into the same state:

- repos in the list but **not on disk** are cloned,
- repos already on disk are **fetched, switched to their default branch and pulled** (local work is
  auto-stashed and restored),
- repos found on disk that are **not in the list yet** are updated and then **added to the config**,
  so the shared list grows organically.

It is generic: nothing is hard-coded to a team, org or git host. Any team can ship its own
`repofleet.toml` (or a plain `repos.txt`) and get the same workflow.

**Documentation:** [full usage guide](docs/USAGE.md) · [publishing guide](docs/PUBLISHING.md) ·
[changelog](CHANGELOG.md)

## Contents

[Install](#install) · [Quick start](#quick-start) · [Commands](#commands) ·
[Configuration](#configuration) · [Output & exit codes](#output--exit-codes) ·
[Authentication](#authentication) · [Troubleshooting](#troubleshooting) ·
[Development](#development)

---

## Install

```bash
pip install repofleet          # from your package index
pipx install repofleet         # isolated, always on PATH
pip install -e ".[dev]"        # from a checkout of this folder
```

Private feed:

```bash
pip install repofleet --index-url https://pkgs.dev.azure.com/<org>/_packaging/<feed>/pypi/simple/
```

No install? Unzip the folder and use the bundled launcher:

```bash
python bootstrap.py sync
```

Requires **Python 3.9+** and **git** on `PATH`. Verify with `repofleet --version`.

---

## Quick start

### You already have the repos checked out

```bash
cd "/path/to/your/workspace"
repofleet init --name "Portfolios Backend" --match "portfolios.*"
repofleet sync
```

`init` scans the folder, records every git repo it finds and writes `repofleet.toml`.

### You have nothing yet (typical for a new joiner)

Drop the shared `repofleet.toml` in an empty folder and run:

```bash
repofleet sync
```

Everything is cloned into the workspace directory declared in the config
(`directory = "Portfolios Backend"` by default for the bundled Polaris profile).

A ready-made profile for the Polaris portfolios services ships with the package at
`src/repofleet/profiles/polaris-portfolios.toml`:

```bash
repofleet sync -c polaris-portfolios.toml
```

### You just want a list of URLs cloned somewhere

```bash
repofleet clone --repos-file team-repos.txt --root ./workspace
```

---

## Commands

| Command | What it does |
| --- | --- |
| `repofleet init` | Create a config from the repositories found on disk. |
| `repofleet list` | Show every tracked repo and whether it is present locally. |
| `repofleet status` | Per-repo branch + clean/dirty state, and what is missing. |
| `repofleet clone` | Clone only the repositories that are missing. |
| `repofleet update` | Fetch + pull every cloned repo (add `--clone-missing` to do both). |
| `repofleet sync` | Clone missing, update existing, adopt new local repos into the config. |
| `repofleet add <url...>` | Track new repositories (`--clone` to fetch them immediately). |
| `repofleet remove <name...>` | Stop tracking repositories (files on disk are left alone). |

Common options (available on every command):

```
-c, --config FILE     config file to use (default: nearest repofleet.toml, then $REPOFLEET_CONFIG)
    --root DIR        where the repositories live / should be cloned
    --repos-file FILE extra repo list, TOML or plain text (repeatable)
    --repo URL        extra repository straight from the command line (repeatable)
    --only PATTERN    restrict to matching repo names (glob)
    --exclude PATTERN skip matching repo names (glob)
    --remote NAME     remote to use (default: origin)
-j, --jobs N          run N repos in parallel
    --dry-run         print the plan without touching anything
-q, --quiet           summary only
```

`update` / `sync` also accept `--no-stash` (skip dirty repos instead of stashing) and `--no-prune`.
`sync` accepts `--no-adopt` to disable writing newly discovered repos back to the config.

Examples:

```bash
repofleet update --only "portfolios.a*" -j 8
repofleet clone --repos-file team-repos.txt --root ./workspace
repofleet sync --dry-run
repofleet add https://dev.azure.com/org/Proj/_git/new.service --clone
```

Every flag is documented in the [usage guide](docs/USAGE.md#5-command-reference).

---

## Configuration

### `repofleet.toml`

```toml
[workspace]
name      = "Portfolios Backend"
# "auto": use this file's folder when it already holds repos, else use `directory`.
root      = "auto"
directory = "Portfolios Backend"
match     = ["portfolios.*"]   # which local folders may be auto-adopted
remote    = "origin"
# repos_file = "team-repos.txt"  # optional: pull the repo list from another file

[defaults]
stash     = true   # stash local changes before pulling, restore afterwards
prune     = true   # git fetch --prune
jobs      = 4      # parallel workers
autoadopt = true   # write newly discovered local repos back into this file

[[repos]]
name = "portfolios.api"
url  = "https://dev.azure.com/org/Proj/_git/portfolios.api"
# branch = "develop"   # optional, defaults to the remote's default branch
```

`name` is optional - it is derived from the URL when omitted.

### Plain text list (easiest to share)

```
# team-repos.txt
https://dev.azure.com/org/Proj/_git/portfolios.api
https://github.com/org/tooling.git
custom-folder-name = https://github.com/org/other.git
https://github.com/org/legacy.git   release/2024   # pin a branch
```

Use it with `--repos-file team-repos.txt`, or reference it from `repos_file` in the TOML.

### Config lookup order

1. `--config/-c`
2. `$REPOFLEET_CONFIG`
3. nearest `repofleet.toml` / `.repofleet.toml` walking up from the current directory
4. `%APPDATA%\repofleet\repofleet.toml` (Windows) or `~/.config/repofleet/repofleet.toml`

### Where repos end up

`--root` wins; otherwise `[workspace] root` (relative to the config file); with the default
`"auto"` the config's own folder is used when it already contains repos, and
`<config folder>/<directory>` when it does not. `repofleet status` prints the resolved root.

---

## Output & exit codes

```
config : C:\code\Portfolios Backend\repofleet.toml
root   : C:\code\Portfolios Backend
  [+] portfolios.api: updated
  [x] portfolios.auth: failed

--------------------------------------------------
Sync summary
--------------------------------------------------
portfolios.api   updated
                 - on main
portfolios.auth  failed
                 - git pull failed: ...
--------------------------------------------------
2 repo(s): 1 failed, 1 updated
```

| Action | Meaning |
| --- | --- |
| `cloned` | Freshly cloned. |
| `updated` | Pulled new commits. |
| `up to date` | Already current. |
| `skipped` | Nothing to do (already cloned, dirty with `--no-stash`, or dry run). |
| `missing` | Listed but not cloned yet. |
| `failed` | Git reported an error; details follow. |

Exit codes: `0` success · `1` a repo failed / nothing selected · `2` config or environment error ·
`130` interrupted.

---

## Authentication

repofleet uses your existing git credentials and sets `GIT_TERMINAL_PROMPT=0`, so a batch run fails
fast instead of hanging on a password prompt. Configure Git Credential Manager, a credential
helper, or SSH keys once before the first run.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `'git' was not found on PATH` | Install git or open a fresh shell. |
| `repofleet: command not found` | Use `python -m repofleet ...`, or install with `pipx`. |
| `could not read Username` | Credentials are missing and prompts are disabled; clone one repo manually or use SSH. |
| `No repositories selected` | No config found — run `repofleet init`, or pass `--repo` / `--repos-file`. |
| Repos cloned somewhere unexpected | Check the `root :` header from `repofleet status`, or pass `--root`. |
| `stash pop failed - stash kept` | Resolve the conflict in that repo, then `git stash pop`. |

More cases in the [usage guide](docs/USAGE.md#17-troubleshooting).

---

## Safety notes

- Git is always invoked with an argument list, never through a shell.
- `GIT_TERMINAL_PROMPT=0` prevents a batch run from hanging on a credential prompt.
- Any credentials embedded in a remote URL are masked in console output.
- `pull --ff-only` is tried first; a merge pull is only attempted if fast-forward is impossible.
- If `git stash pop` fails after a pull, the stash is **kept** and the repo is reported as failed -
  your work is never discarded.
- `remove` only edits the config; it never deletes directories.

---

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

Tests spin up real local git repositories in a temp folder — no network needed. See the
[usage guide](docs/USAGE.md#19-contributing--local-development) for the project layout and the
[publishing guide](docs/PUBLISHING.md) for cutting a release.

## License

MIT.
