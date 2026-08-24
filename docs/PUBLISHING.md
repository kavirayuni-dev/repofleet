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

```bash
twine upload --repository testpypi dist/*      # rehearse first
pip install --index-url https://test.pypi.org/simple/ repofleet

twine upload dist/*                            # the real thing
```

Use an API token (`__token__` as username) or, better, a GitHub Actions trusted publisher.

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

## 5. Release pipeline (Azure Pipelines)

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
