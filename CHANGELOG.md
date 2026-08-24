# Changelog

All notable changes to this project are documented here.
This project follows [Semantic Versioning](https://semver.org/).

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
- Bundled profile `polaris-portfolios.toml`.
- `bootstrap.py` for running from an unzipped folder without installing.
- Credential masking in output and `GIT_TERMINAL_PROMPT=0` to avoid hanging on prompts.
