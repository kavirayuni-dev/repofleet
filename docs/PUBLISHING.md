# Publishing repofleet

How to cut a release and push it to PyPI or a private feed (Azure Artifacts, Nexus, Artifactory).

---

## 1. Pre-flight checklist

- [ ] `pytest -q` passes.
- [ ] `version` bumped in `pyproject.toml` **and** `src/repofleet/__init__.py`.
- [ ] `CHANGELOG.md` updated.
- [ ] `README.md` / `docs/USAGE.md` reflect any new flags.
- [ ] `[project.urls]` in `pyproject.toml` points at the real repository/docs.
- [ ] The bundled profiles under `src/repofleet/profiles/` contain **no credentials or tokens**.

The package name `repofleet` must be free on the target index. Check
<https://pypi.org/project/repofleet/> before the first public release; if taken, rename the
distribution (`[project] name`) — the import package and CLI can stay the same.

---

## 2. Build

```bash
pip install --upgrade build twine
python -m build           # writes dist/repofleet-X.Y.Z.tar.gz and .whl
twine check dist/*
```

Verify the bundled profiles made it into the wheel:

```bash
python -c "import zipfile,glob;print([n for n in zipfile.ZipFile(glob.glob('dist/*.whl')[0]).namelist() if 'profiles' in n])"
```

Smoke-test the artifact in a clean environment:

```bash
python -m venv /tmp/verify && /tmp/verify/bin/pip install dist/repofleet-*.whl
/tmp/verify/bin/repofleet --version
/tmp/verify/bin/repofleet --help
```

---

## 3. Publish to PyPI

### 3a. GitHub Actions with Trusted Publishing (recommended)

`.github/workflows/publish.yml` publishes automatically — no API token is stored anywhere. One-time
setup:

1. **Create the PyPI environments on GitHub**: Settings → Environments → New environment, named
   exactly `pypi` and `testpypi`. (Optionally add required reviewers to `pypi`.)
2. **Register the trusted publisher on PyPI**: <https://pypi.org/manage/account/publishing/> →
   *Add a new pending publisher*:
   - PyPI Project Name: `repofleet`
   - Owner: `kavirayuni-dev`
   - Repository name: `repofleet`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
3. **Repeat on TestPyPI**: <https://test.pypi.org/manage/account/publishing/> with environment
   name `testpypi`.

Then:

- **Rehearsal** — Actions → *Publish* → *Run workflow* → target `testpypi`.
- **Real release** — bump the version, tag it, and publish a GitHub Release:

  ```bash
  git tag v0.1.0 && git push origin v0.1.0
  gh release create v0.1.0 --generate-notes
  ```

  The workflow runs the tests, checks the tag matches `[project] version`, builds, and uploads to
  PyPI.

### 3b. Manual upload (fallback)

```bash
twine upload --repository testpypi dist/*      # rehearse first
pip install --index-url https://test.pypi.org/simple/ repofleet

twine upload dist/*                            # the real thing
```

Use an API token: username `__token__`, password the `pypi-...` token from
<https://pypi.org/manage/account/token/>. Store it in `~/.pypirc` (chmod 600) or the
`TWINE_PASSWORD` env var — never in the repo.

---

## 4. Publish to a private feed

### Azure Artifacts

```bash
pip install twine keyring artifacts-keyring
```

`~/.pypirc`:

```ini
[distutils]
index-servers = myfeed

[myfeed]
repository = https://pkgs.dev.azure.com/<org>/<project>/_packaging/<feed>/pypi/upload/
username = <anything>
password = <personal-access-token-with-Packaging-Read-Write>
```

```bash
twine upload --repository myfeed dist/*
```

Consumers install with:

```bash
pip install repofleet --index-url https://pkgs.dev.azure.com/<org>/<project>/_packaging/<feed>/pypi/simple/
```

### Nexus / Artifactory

Same flow — point `repository` at the feed's upload URL and use your feed credentials. Never commit
`~/.pypirc`.

---

## 5. Release pipelines

### GitHub Actions (this repo)

| Workflow | File | Trigger | What it does |
| --- | --- | --- | --- |
| CI | `.github/workflows/ci.yml` | push to `main`/`master`, PRs, manual | pytest on Linux + Windows across Python 3.9–3.13, plus a `python -m build` + `twine check` smoke build |
| Publish | `.github/workflows/publish.yml` | GitHub Release published, or manual | tests, builds, verifies tag matches the version, uploads via Trusted Publishing |

### Azure Pipelines (private feed alternative)

```yaml
trigger:
  tags:
    include: ['v*']

pool: { vmImage: ubuntu-latest }

steps:
  - task: UsePythonVersion@0
    inputs: { versionSpec: '3.11' }
  - script: pip install build twine pytest
    displayName: Tooling
  - script: pip install -e ".[dev]" && pytest -q
    displayName: Tests
  - script: python -m build && twine check dist/*
    displayName: Build
  - task: TwineAuthenticate@1
    inputs: { artifactFeed: '<project>/<feed>' }
  - script: twine upload -r '<feed>' --config-file $(PYPIRC_PATH) dist/*
    displayName: Publish
```

---

## 6. Versioning

Semantic versioning:

- **patch** — bug fixes, output tweaks;
- **minor** — new commands/flags, new config keys (backwards compatible);
- **major** — changes to config format, command names or exit-code meanings.

The CLI and config schema are the public contract; modules under `repofleet.*` may change in minor
releases.

Tag each release: `git tag v0.1.0 && git push --tags`.

---

## 7. After publishing

- Announce the install command and point people at `docs/USAGE.md`.
- Share the team `repofleet.toml` (or add it as a bundled profile in the next release).
- Remove stale copies of the old ad-hoc update scripts so everyone uses one tool.
