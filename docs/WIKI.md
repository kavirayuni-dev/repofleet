# repofleet — manage all your team's git repositories with one command

[[_TOC_]]

---

## 1. Why this exists

Most of our products are split across many git repositories. That means everyone repeats the same
manual chores:

- a new joiner spends their first morning copying repo URLs out of a wiki page and running
  `git clone` twenty times;
- everyone starts the day running `git pull` in twenty folders — or worse, forgets to, and debugs
  against stale code;
- someone adds a new service repo and tells the team on chat; half of them miss it and are silently
  out of date for a week;
- each person's folder layout is slightly different, so "it works on my machine" scripts don't
  travel.

`repofleet` replaces all of that with **one shared list file and one command**:

```bash
repofleet sync
```

| Situation on your machine | What `sync` does |
| --- | --- |
| Repo is in the list, not on disk | clones it into the workspace folder |
| Repo is in the list and on disk | fetches, switches to the default branch, pulls |
| You have uncommitted work in that repo | stashes it, pulls, restores the stash |
| Repo is on disk but **not** in the list | updates it, then **adds it to the shared list** |
| Repo is in the list but you don't want it | filter with `--exclude`, or `repofleet remove` |

### What the team gets out of it

- **Onboarding drops from hours to one command.** Share one file; the new joiner runs `sync`.
- **The list maintains itself.** Whoever clones a new repo first pushes it into the shared list
  automatically, just by running `sync` (this is the *auto-adoption* feature — see
  [section 9](#9-auto-adoption-the-list-maintains-itself)).
- **Your local work is never lost.** Dirty repos are stashed and restored, and if a stash can't be
  restored it is *kept* and reported instead of discarded.
- **One failure doesn't stop the run.** Every repo is attempted; you get a summary at the end.
- **It's just git.** No daemon, no server, no cache. Anything repofleet does you could have typed
  yourself.
- **Identical behaviour on Windows, macOS and Linux**, and usable in CI.

---

## 2. Requirements

- **Python 3.9 or newer**
- **git** on your `PATH` (check with `git --version`)
- Working git credentials for your remotes (see [section 12](#12-authentication))

---

## 3. Installation

`repofleet` is a public package on PyPI. Any of these work.

### Globally (recommended for a CLI tool) — with pipx

`pipx` keeps the tool isolated but on your `PATH`, so it never clashes with a project's
dependencies.

```bash
python -m pip install --user pipx
python -m pipx ensurepath
pipx install repofleet
```

### Globally — with plain pip

```bash
pip install --user repofleet
```

### Inside a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install repofleet
```

### Upgrading

```bash
pipx upgrade repofleet     # or: pip install --upgrade repofleet
```

### Verify

```bash
repofleet --version
repofleet --help
```

> If your shell says `repofleet: command not found`, the scripts folder isn't on `PATH`.
> Use `python -m repofleet ...` instead, or install with `pipx`.

---

## 4. The three ways to start

Pick the one that matches your situation. All three end up in the same place: a `repofleet.toml`
you can commit and share.

### 4.1 Use case A — "I already have all the repos cloned"

You have `C:\code\workspace\` full of checkouts. Turn what's on disk into a shared list.

```bash
cd C:\code\workspace
repofleet init --name "Backend Services" --match "svc.*"
```

What happened:

```
Wrote C:\code\workspace\repofleet.toml with 12 repository entrie(s).
Discovered 12 repo(s) under C:\code\workspace.
Wrote C:\code\workspace\repo-urls.txt - paste your repository URLs there, one per line.

Next steps
----------
1. Preview what will happen:  repofleet sync --dry-run
2. Clone everything:          repofleet sync
3. Every day after that:      repofleet sync   (clones new, pulls the rest)

Repositories will be cloned into: C:\code\workspace
```

`init` read the `origin` URL of every git folder it found and wrote them into `repofleet.toml`.
Commit that file somewhere the team can reach it — that's now the single source of truth.

`--match "svc.*"` restricts it to folders whose names start with `svc.` — useful when your
workspace also contains unrelated checkouts. Drop it to take everything.

### 4.2 Use case B — "I have nothing yet" (new joiner)

Someone hands you `repofleet.toml`. Put it in an empty folder and run one command.

```bash
mkdir C:\code\workspace
cd C:\code\workspace
# copy the shared repofleet.toml into this folder
repofleet sync
```

Every repo is cloned into the folder named by `directory` in the config, e.g.
`C:\code\workspace\Backend Services\svc.api`. Done — you're set up.

### 4.3 Use case C — "I just have a list of URLs in a text file"

The lowest-friction option: a plain text file, one URL per line. Perfect for pasting into a wiki
page or an email.

```
# repo-urls.txt
https://dev.azure.com/org/Project/_git/svc.api
https://dev.azure.com/org/Project/_git/svc.auth
https://github.com/org/shared-tooling.git
```

```bash
repofleet clone --repos-file repo-urls.txt --root ./workspace
```

No config file is created — this is a one-shot clone. To make it permanent, see
[section 6.2](#62-plain-text-list).

---

## 5. Command reference — one example each

Every command below accepts the [global options](#7-global-options) too.

### 5.1 `repofleet init` — create the config

Creates `repofleet.toml` from the repositories found on disk, **plus** a `repo-urls.txt` list file
pre-filled with commented-out examples.

| Option | Meaning |
| --- | --- |
| `--name NAME` | Workspace name written into the config. |
| `--directory DIR` | Folder repos are cloned into when they don't exist yet. |
| `--match GLOB...` | Only track folders whose names match (default `*`). |
| `--output FILE` | Where to write (default `./repofleet.toml`). |
| `--force` | Overwrite an existing config. |
| `--no-repos-file` | Don't create the companion `repo-urls.txt`. |
| `--root DIR` | Folder to scan (default: the config's own folder). |

**Example — starting from an empty folder:**

```bash
mkdir C:\code\myfleet
cd C:\code\myfleet
repofleet init --name "Backend Services"
```

```
Wrote C:\code\myfleet\repofleet.toml with 0 repository entrie(s).
Wrote C:\code\myfleet\repo-urls.txt - paste your repository URLs there, one per line.

Next steps
----------
1. List the repositories you want, one URL per line, in
   C:\code\myfleet\repo-urls.txt
   (the file already contains commented-out examples)
2. Preview what will happen:  repofleet sync --dry-run
3. Clone everything:          repofleet sync
4. Every day after that:      repofleet sync   (clones new, pulls the rest)

Repositories will be cloned into: C:\code\myfleet\Backend Services
Check anytime with 'repofleet list' or 'repofleet status'.
```

Now open `repo-urls.txt`, paste your URLs, and run `repofleet sync`. Zero TOML knowledge required.

**Example — preview without writing anything:**

```bash
repofleet init --dry-run
```

### 5.2 `repofleet list` — what is tracked

```bash
repofleet list
```

```
config : C:\code\myfleet\repofleet.toml
root   : C:\code\myfleet\Backend Services
svc.api      present   https://dev.azure.com/org/Project/_git/svc.api
svc.auth     present   https://dev.azure.com/org/Project/_git/svc.auth
svc.worker   missing   https://dev.azure.com/org/Project/_git/svc.worker  [develop]

3 repository(ies).
```

Filter it:

```bash
repofleet list --only "svc.a*"
```

### 5.3 `repofleet status` — local state of each repo

Shows branch and whether you have uncommitted changes. Great before a big pull.

```bash
repofleet status
```

```
svc.api      present   main                      clean
svc.auth     present   feature/new-login         dirty
svc.worker   missing   -                         -

3 repo(s), 1 missing. Run 'repofleet sync' to reconcile.
```

### 5.4 `repofleet clone` — only fetch what's missing

Leaves existing checkouts completely untouched (they're reported as `skipped`).

```bash
repofleet clone
repofleet clone --only svc.api
repofleet clone --repos-file repo-urls.txt --root ./workspace -j 8
```

### 5.5 `repofleet update` — fetch + pull everything already cloned

| Option | Meaning |
| --- | --- |
| `--clone-missing` | Also clone repos that aren't present yet. |
| `--no-stash` | Skip repos with local changes instead of stashing them. |
| `--no-prune` | Don't pass `--prune` to `git fetch`. |

```bash
repofleet update                      # the morning pull
repofleet update --only "svc.a*" -j 8 # just some of them, 8 in parallel
repofleet update --no-stash           # never touch a dirty working tree
```

### 5.6 `repofleet sync` — the everyday command

`clone` + `update` + adopt anything new it finds on disk.

| Option | Meaning |
| --- | --- |
| `--no-adopt` | Don't write newly discovered local repos into the config. |
| `--no-stash`, `--no-prune` | Same as `update`. |

```bash
repofleet sync
repofleet sync --dry-run              # show the plan, change nothing
repofleet sync --exclude "*.archive"
```

### 5.7 `repofleet add <url...>` — track a new repository

| Option | Meaning |
| --- | --- |
| `--name NAME` | Directory name (single URL only). |
| `--branch BRANCH` | Pin the repo to a branch. |
| `--clone` | Clone it immediately after adding. |

```bash
repofleet add https://dev.azure.com/org/Project/_git/svc.notifications --clone
repofleet add https://github.com/org/shared-tooling.git --name tools --branch develop
```

Entries are **appended**, so any comments or ordering you added by hand survive. Duplicate URLs are
ignored — the comparison ignores case, a trailing `.git`, and embedded credentials, so
`https://user@host/org/Repo.git` and `https://host/org/repo` count as the same repo.

### 5.8 `repofleet remove <name...>` — stop tracking

```bash
repofleet remove svc.legacy svc.spike
```

> **Only the config file is edited. Nothing on disk is deleted.** If you also want the folder gone,
> delete it yourself.

---

## 6. Configuration files

### 6.1 `repofleet.toml`

```toml
[workspace]
name       = "Backend Services"   # human-readable workspace name
root       = "auto"               # "auto", a path relative to this file, or an absolute path
directory  = "Backend Services"   # folder created when root = "auto" and nothing is cloned yet
match      = ["svc.*"]            # which local folder names may be auto-adopted
remote     = "origin"             # remote used for clone/fetch/pull
repos_file = "repo-urls.txt"      # optional: merge an external URL list into this config

[defaults]
stash     = true    # stash local changes before pulling, restore afterwards
prune     = true    # git fetch --prune
jobs      = 4       # how many repos to process in parallel
autoadopt = true    # write newly discovered local repos back into this file

[[repos]]
name   = "svc.api"                                    # optional — derived from the URL
url    = "https://dev.azure.com/org/Project/_git/svc.api"
branch = "main"                                       # optional — defaults to the remote's default
```

A shorthand form is also accepted:

```toml
[repos]
"svc.api"  = "https://dev.azure.com/org/Project/_git/svc.api"
"svc.auth" = "https://dev.azure.com/org/Project/_git/svc.auth"
```

### 6.2 Plain text list

Extensions `.txt`, `.list`, `.repos`. `repofleet init` creates `repo-urls.txt` for you.

```
# repo-urls.txt
https://dev.azure.com/org/Project/_git/svc.api            # comment after two spaces + #
https://github.com/org/shared-tooling.git
tools = git@github.com:org/internal-tooling.git            # alias the directory name
https://github.com/org/legacy.git   release/2024           # pin a branch
```

Rules:

- blank lines and `#` lines are ignored;
- `name = url` sets the folder name;
- a second token after the URL is the branch.

Use it three ways:

```bash
repofleet sync -c repo-urls.txt                # as the config itself
repofleet sync --repos-file repo-urls.txt      # merged into the current run
```

```toml
[workspace]
repos_file = "repo-urls.txt"                   # permanently referenced from the TOML
```

Repos that come from `repos_file` stay in that file — they're never copied into the TOML when it's
rewritten, so the two files stay cleanly separated.

### 6.3 Where the config is found

In order:

1. `--config` / `-c`
2. the `REPOFLEET_CONFIG` environment variable
3. the nearest `repofleet.toml` or `.repofleet.toml`, searching upwards from the current folder
4. `%APPDATA%\repofleet\repofleet.toml` (Windows) or `~/.config/repofleet/repofleet.toml`

> **Common gotcha:** auto-discovery only recognises the names `repofleet.toml` and
> `.repofleet.toml`. If you copied a file called `example-workspace.toml`, either rename it or pass
> `-c example-workspace.toml` every time. The symptom is
> `config : <none - using CLI arguments>` in the header.

### 6.4 Where the repos end up

1. `--root` if given — wins over everything.
2. `[workspace] root`, if it isn't `"auto"`. Relative paths resolve against **the config file's
   folder**, so a shared config behaves identically on every machine.
3. `"auto"` (the default):
   - if the config's folder already contains at least one git repo → use that folder;
   - otherwise → use `<config folder>/<directory>`.

That last rule is what lets the *same* config work for a veteran whose repos already sit next to it
and for a new joiner who gets everything cloned into a fresh subfolder.

Print the resolved root anytime with `repofleet status`.

---

## 7. Global options

| Option | Default | Meaning |
| --- | --- | --- |
| `-c, --config FILE` | auto-discovered | Config file (`.toml`, or `.txt`/`.list`/`.repos`). |
| `--root DIR` | from config | Folder that holds the repositories. |
| `--repos-file FILE` | – | Extra list merged into this run. Repeatable. |
| `--repo URL` | – | Extra repository given inline. Repeatable. |
| `--only PATTERN...` | all | Keep only repos matching a glob. |
| `--exclude PATTERN...` | none | Drop repos matching a glob. |
| `--remote NAME` | `origin` | Remote to fetch/pull from. |
| `-j, --jobs N` | `4` | Repositories processed in parallel. |
| `--dry-run` | off | Print the plan, change nothing. |
| `-q, --quiet` | off | Summary only. |
| `--version` | – | Print the version and exit. |

`--only` / `--exclude` match the **repo name** (its folder name) with shell-style globs:
`--only "svc.a*" "*.api"`.

---

## 8. What happens to your uncommitted work

For each repository, `update` / `sync` does:

1. `git fetch --prune <remote>`
2. work out the target branch — the `branch` from the config, else `<remote>/HEAD`, else the first
   of `main`, `master`, `develop` that exists
3. if the working tree is dirty → `git stash push -u` (with `--no-stash` the repo is reported
   `skipped` and left completely alone)
4. `git checkout <branch>`
5. `git pull --ff-only`, falling back to a merge pull only if fast-forward isn't possible
6. `git stash pop` to restore your work

Guarantees:

- **Your work is never discarded.** If `stash pop` hits a conflict, the stash is *kept* and the repo
  is reported as `failed` with git's message. Recover with `git stash list` / `git stash pop`.
- If checkout or pull fails after stashing, the stash is popped back before reporting.
- A failing repo never aborts the run.

---

## 9. Auto-adoption: the list maintains itself

This is the feature that keeps a team in sync without anyone policing the list.

During `sync`, repofleet scans the workspace folder for git repositories that match
`[workspace] match` but aren't in the config. It updates them like any other repo and then — **only
if the update succeeded** — appends them to the config file:

```
Added 1 newly discovered repo(s) to C:\code\myfleet\repofleet.toml:
  + svc.notifications  https://dev.azure.com/org/Project/_git/svc.notifications
```

### Worked example

1. A colleague creates a new repo `svc.notifications` and clones it into their workspace by hand.
2. They run `repofleet sync`. repofleet spots the unknown folder, updates it, and adds it to
   `repofleet.toml`.
3. They commit the one-line config change and push it.
4. Everyone else runs `repofleet sync` next morning and **automatically gets the new repo cloned**.

Nobody had to announce anything.

Notes:

- Adoption only happens on `sync` — never on `clone` or `update`.
- Turn it off for one run with `--no-adopt`, or permanently with `autoadopt = false`.
- A repo whose URL is already tracked under a different folder name is **not** adopted, so a second
  checkout of the same repo won't create a duplicate entry.
- Review adopted entries in your normal code review — it's just a diff on a text file.

---

## 10. Reading the output

```
config : C:\code\myfleet\repofleet.toml
root   : C:\code\myfleet\Backend Services
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

| Action | Meaning |
| --- | --- |
| `cloned` | Freshly cloned. |
| `updated` | Pulled new commits. |
| `up to date` | Already current. |
| `skipped` | Nothing to do — already cloned, dirty with `--no-stash`, or a dry run. |
| `missing` | Listed but not cloned — run `clone` or `sync`. |
| `failed` | Git reported an error; the details follow. |

`[+]` = success, `[x]` = failure. `-q` hides the per-repo lines and prints only the summary.

---

## 11. Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Everything succeeded. |
| `1` | At least one repo failed or was missing, or nothing was selected. |
| `2` | Configuration or environment error (bad TOML, git missing, bad arguments). |
| `130` | Interrupted with Ctrl+C. |

Safe to use in scripts:

```bash
repofleet sync -q || echo "the fleet is out of date"
```

---

## 12. Authentication

repofleet shells out to `git`, so it uses whatever credentials git already has. It deliberately
sets `GIT_TERMINAL_PROMPT=0`, so an unattended run **fails fast instead of hanging** on a password
prompt.

**Set credentials up once, before your first run.** The easiest way is to clone a single repo by
hand and sign in — every later run is then silent.

- **Azure DevOps on Windows:** Git Credential Manager ships with Git for Windows and handles the
  browser sign-in. If you use a Personal Access Token, it needs **Code (Read)** scope.
- **macOS / Linux:** `git config --global credential.helper osxkeychain` (or `store`), or use SSH
  keys with `ssh-agent`.
- **SSH:** put SSH URLs (`git@host:org/repo.git`) in the list instead of HTTPS.

> **Never commit a token.** Don't paste `https://user:TOKEN@host/...` into a shared config.
> repofleet masks credentials as `https://***@host/...` in all console output, but the file itself
> would still contain the secret in plain text.

---

## 13. Everyday recipes

```bash
# Morning refresh of everything, 8 repos at a time
repofleet sync -j 8

# What would sync do? (changes nothing)
repofleet sync --dry-run

# What's missing on this machine?
repofleet status

# Only the alerting services
repofleet update --only "svc.alerts*"

# Everything except the noisy ones
repofleet update --exclude "*.scripts" "*.wiki"

# Clone the missing repos only, leave existing checkouts alone
repofleet clone

# Update, but never touch a dirty working tree
repofleet update --no-stash

# Track a brand-new service and clone it in one go
repofleet add https://dev.azure.com/org/Project/_git/svc.notifications --clone

# A one-off list from a colleague, into a scratch folder
repofleet clone --repos-file colleague-repos.txt --root ./scratch

# Point at a config that lives somewhere else
repofleet sync -c "D:/configs/team.toml"
```

---

## 14. Using repofleet in CI

```yaml
# Azure Pipelines
steps:
  - task: UsePythonVersion@0
    inputs: { versionSpec: '3.11' }
  - script: pip install repofleet
    displayName: Install repofleet
  - script: repofleet clone --root $(Build.SourcesDirectory)/workspace -c repofleet.toml -q -j 8 --no-stash
    displayName: Clone the fleet
```

Tips:

- prefer `clone` (or `update --clone-missing`) over `sync`, so the config is never rewritten by a
  build;
- add `--no-stash` — a CI checkout should never be dirty, and this makes surprises visible;
- `-q` keeps the log short; the summary and the exit code are all you need.

---

## 15. Rolling this out to a team

1. One person runs `repofleet init` in their existing workspace and reviews the generated
   `repofleet.toml`.
2. Commit `repofleet.toml` (and `repo-urls.txt` if you use it) to a repo everyone can read — a
   `dev-setup` repo, or the main service repo.
3. Put this page in the wiki and link the config.
4. New joiners: `pipx install repofleet`, copy the config into an empty folder, `repofleet sync`.
5. Let `sync` adopt new repositories and review those one-line config changes in normal PRs.

---

## 16. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `config : <none - using CLI arguments>` | No config found. Auto-discovery only matches `repofleet.toml` / `.repofleet.toml` — rename your file or pass `-c <file>`. |
| `No repositories selected` | The config has no repositories yet. Paste URLs into `repo-urls.txt`, or use `repofleet add <url>`. |
| `error: 'git' was not found on PATH` | Install git, or open a new shell so `PATH` refreshes. |
| `repofleet: command not found` | The scripts folder isn't on `PATH`. Use `python -m repofleet ...`, or install with `pipx`. |
| `git clone failed: ... could not read Username` | Credentials are missing; prompts are disabled on purpose. Clone one repo by hand to store them, or switch to SSH. |
| Repos cloned into an unexpected folder | See [section 6.4](#64-where-the-repos-end-up). Run `repofleet status` to print the resolved root, or pass `--root`. |
| `pull succeeded but 'git stash pop' failed - stash kept` | Your stashed changes conflict with the new commits. `cd` into the repo, resolve, then `git stash pop`. |
| `<path> exists and is not an empty git repo` | A non-git folder occupies the target name. Rename it, or alias the repo with `name = url`. |
| A repo is skipped every run | It has local changes and you passed `--no-stash`, or it's filtered out by `--only` / `--exclude`. |
| New repos aren't added to the config | Adoption is `sync`-only. Check you didn't pass `--no-adopt`, that `autoadopt = true`, and that the folder name matches `[workspace] match`. |
| `Invalid TOML in ...` | Syntax error in the config; the message includes the line. |
| Runs feel slow | Raise `-j`, or narrow the set with `--only`. |

---

## 17. Getting help

```bash
repofleet --help
repofleet sync --help
```

Questions, bugs and feature requests: raise them with the team that owns this page.
