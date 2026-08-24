# Changelog

All notable changes to this project are documented here.
This project follows [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-08-24

### Added

- `repofleet init` now also writes a companion `repo-urls.txt` with commented-out examples, links
  it from the generated config via `repos_file`, and prints step-by-step instructions for what to
  do next. Skip it with `--no-repos-file`.
- Repositories supplied through `repos_file` are kept in that file and are no longer inlined into
  `repofleet.toml` when the config is rewritten.

### Changed

- The "No repositories selected" error now lists the exact ways to fix it.
- The bundled profile is a generic `example-workspace.toml`; all documentation examples use
  placeholder organisation and repository names.

## [0.1.0] - 2026-08-24

Initial release.

### Added

- `repofleet init` — generate a config from the git repositories found on disk.
- `repofleet clone` — clone the repositories that are missing.
- `repofleet update` — fetch + pull every cloned repo, auto-stashing and restoring local work
  (`--clone-missing`, `--no-stash`, `--no-prune`).
- `repofleet sync` — clone missing, update existing and adopt newly discovered local repos into the
  config (`--no-adopt`).
- `repofleet list` / `repofleet status` — inspect the fleet.
- `repofleet add` / `repofleet remove` — manage tracked repositories; `add` appends so hand-written
  comments survive, `remove` never touches files on disk.
- TOML configuration (`repofleet.toml`) and plain-text repo lists (`*.txt`, `*.list`, `*.repos`),
  plus `--repo` / `--repos-file` for ad-hoc runs.
- `"auto"` workspace-root resolution: reuse the config's folder when it already holds repos,
  otherwise clone into a dedicated directory.
- Parallel execution (`-j`), glob filtering (`--only` / `--exclude`), `--dry-run` and `--quiet`.
- Bundled example profile `example-workspace.toml`.
- `bootstrap.py` for running from an unzipped folder without installing.
- Credential masking in output and `GIT_TERMINAL_PROMPT=0` to avoid hanging on prompts.
