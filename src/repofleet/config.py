"""Configuration loading/saving for repofleet.

Two file formats are supported:

* TOML (``repofleet.toml``) - full configuration including workspace settings.
* Plain list (``*.txt`` / ``*.list``) - one repo per line, ideal for quick sharing::

      # comment
      https://host/org/repo.git
      custom-dir-name = https://host/org/other.git
      https://host/org/third.git   develop
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

from repofleet.gitcmd import is_git_repo
from repofleet.models import RepoSpec, name_from_url

try:  # Python >= 3.11
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on 3.9/3.10
    import tomli as tomllib  # type: ignore[no-redef]

CONFIG_FILENAMES = ("repofleet.toml", ".repofleet.toml")
ENV_CONFIG = "REPOFLEET_CONFIG"
LIST_SUFFIXES = {".txt", ".list", ".repos"}

FORMAT_TOML = "toml"
FORMAT_LIST = "list"


class ConfigError(Exception):
    pass


@dataclass
class FleetConfig:
    repos: List[RepoSpec] = field(default_factory=list)
    name: str = "workspace"
    source: Optional[Path] = None
    format: str = FORMAT_TOML
    root_setting: str = "auto"
    directory: Optional[str] = None
    match: List[str] = field(default_factory=lambda: ["*"])
    remote: str = "origin"
    stash: bool = True
    prune: bool = True
    jobs: int = 4
    autoadopt: bool = True

    @property
    def base_dir(self) -> Path:
        return self.source.parent if self.source else Path.cwd()

    def resolve_root(self, override: Optional[str] = None) -> Path:
        """Where the repositories live (or will be cloned into)."""
        if override:
            return Path(override).expanduser().resolve()

        base = self.base_dir
        setting = (self.root_setting or "auto").strip()
        if setting and setting != "auto":
            return (base / Path(setting).expanduser()).resolve()

        # auto: reuse the config's own folder when it already holds repositories,
        # otherwise nest them in a dedicated workspace directory.
        if any(is_git_repo(p) for p in _iter_dirs(base)):
            return base.resolve()
        return (base / (self.directory or self.name)).resolve()

    def by_name(self) -> dict:
        return {spec.name: spec for spec in self.repos}

    def urls(self) -> set:
        return {normalize_url(spec.url) for spec in self.repos}


def _iter_dirs(path: Path) -> Iterable[Path]:
    if not path.is_dir():
        return []
    try:
        return [p for p in path.iterdir() if p.is_dir()]
    except OSError:
        return []


def normalize_url(url: str) -> str:
    """Compare remotes ignoring case, trailing '.git' and embedded userinfo."""
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[: -len(".git")]
    if "://" in cleaned:
        scheme, rest = cleaned.split("://", 1)
        if "@" in rest.split("/", 1)[0]:
            rest = rest.split("@", 1)[1]
        cleaned = f"{scheme}://{rest}"
    return cleaned.lower()


# --------------------------------------------------------------------------- find


def find_config(start: Optional[Path] = None) -> Optional[Path]:
    env_path = os.environ.get(ENV_CONFIG)
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.is_file():
            return candidate.resolve()
        raise ConfigError(f"{ENV_CONFIG} points at a missing file: {candidate}")

    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        for filename in CONFIG_FILENAMES:
            candidate = directory / filename
            if candidate.is_file():
                return candidate

    user_config = _user_config_path()
    return user_config if user_config.is_file() else None


def _user_config_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "repofleet" / "repofleet.toml"


# --------------------------------------------------------------------------- load


def load_config(path: Path) -> FleetConfig:
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    if path.suffix.lower() in LIST_SUFFIXES:
        return _load_list(path)
    return _load_toml(path)


def _load_toml(path: Path) -> FleetConfig:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc

    workspace = data.get("workspace") or {}
    defaults = data.get("defaults") or {}
    config = FleetConfig(
        name=str(workspace.get("name") or path.parent.name or "workspace"),
        source=path,
        format=FORMAT_TOML,
        root_setting=str(workspace.get("root", "auto")),
        directory=workspace.get("directory"),
        match=list(workspace.get("match") or ["*"]),
        remote=str(workspace.get("remote", "origin")),
        stash=bool(defaults.get("stash", True)),
        prune=bool(defaults.get("prune", True)),
        jobs=max(1, int(defaults.get("jobs", 4))),
        autoadopt=bool(defaults.get("autoadopt", True)),
    )

    config.repos = _parse_repo_entries(data.get("repos") or [], path)

    repos_file = workspace.get("repos_file")
    if repos_file:
        extra = load_config(path.parent / repos_file)
        config.repos = merge_specs(config.repos, extra.repos)
    return config


def _parse_repo_entries(entries, path: Path) -> List[RepoSpec]:
    specs: List[RepoSpec] = []
    if isinstance(entries, dict):  # [repos] name = url
        entries = [{"name": key, "url": value} for key, value in entries.items()]
    for entry in entries:
        if isinstance(entry, str):
            specs.append(RepoSpec.from_url(entry))
            continue
        url = entry.get("url")
        if not url:
            raise ConfigError(f"A [[repos]] entry in {path} is missing 'url'.")
        specs.append(
            RepoSpec.from_url(url, branch=entry.get("branch"), name=entry.get("name"))
        )
    return specs


def _load_list(path: Path) -> FleetConfig:
    specs = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        spec = parse_list_line(raw)
        if spec:
            specs.append(spec)
    return FleetConfig(
        repos=specs,
        name=path.parent.name or "workspace",
        source=path,
        format=FORMAT_LIST,
    )


def parse_list_line(raw: str) -> Optional[RepoSpec]:
    line = raw.strip()
    if not line or line.startswith("#"):
        return None
    if " #" in line:
        line = line.split(" #", 1)[0].strip()
    name = None
    if (
        "=" in line
        and line.split("=", 1)[0].strip()
        and "://" not in line.split("=", 1)[0]
    ):
        name, line = (part.strip() for part in line.split("=", 1))
    parts = line.split()
    if not parts:
        return None
    url = parts[0]
    branch = parts[1] if len(parts) > 1 else None
    return RepoSpec.from_url(url, branch=branch, name=name)


def merge_specs(
    existing: Iterable[RepoSpec], extra: Iterable[RepoSpec]
) -> List[RepoSpec]:
    merged = list(existing)
    seen_urls = {normalize_url(s.url) for s in merged}
    seen_names = {s.name for s in merged}
    for spec in extra:
        if normalize_url(spec.url) in seen_urls or spec.name in seen_names:
            continue
        merged.append(spec)
        seen_urls.add(normalize_url(spec.url))
        seen_names.add(spec.name)
    return merged


# --------------------------------------------------------------------------- write


def _toml_str(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_config(config: FleetConfig) -> str:
    lines = [
        "# repofleet workspace configuration",
        "# Docs: repofleet --help  |  regenerate with: repofleet init --force",
        "",
        "[workspace]",
        f"name = {_toml_str(config.name)}",
        '# root: "auto" keeps repos next to this file when some already exist,',
        "# otherwise they are cloned into the 'directory' below.",
        f"root = {_toml_str(config.root_setting or 'auto')}",
        f"directory = {_toml_str(config.directory or config.name)}",
        "match = [" + ", ".join(_toml_str(m) for m in config.match) + "]",
        f"remote = {_toml_str(config.remote)}",
        "",
        "[defaults]",
        f"stash = {str(config.stash).lower()}",
        f"prune = {str(config.prune).lower()}",
        f"jobs = {config.jobs}",
        "# autoadopt: add locally-found repos that are missing here into this file",
        f"autoadopt = {str(config.autoadopt).lower()}",
        "",
    ]
    for spec in sorted(config.repos, key=lambda s: s.name.lower()):
        lines.extend(_render_repo(spec))
    return "\n".join(lines).rstrip() + "\n"


def _render_repo(spec: RepoSpec) -> List[str]:
    block = [
        "[[repos]]",
        f"name = {_toml_str(spec.name)}",
        f"url = {_toml_str(spec.url)}",
    ]
    if spec.branch:
        block.append(f"branch = {_toml_str(spec.branch)}")
    block.append("")
    return block


def save_config(config: FleetConfig, path: Optional[Path] = None) -> Path:
    target = Path(path or config.source or (Path.cwd() / CONFIG_FILENAMES[0]))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_config(config), encoding="utf-8")
    config.source = target.resolve()
    return config.source


def append_repos(config: FleetConfig, specs: Iterable[RepoSpec]) -> List[RepoSpec]:
    """Append new repos to the config file, preserving existing formatting/comments."""
    new = [s for s in merge_specs(config.repos, specs) if s not in config.repos]
    if not new:
        return []
    if config.source is None:
        config.repos = merge_specs(config.repos, new)
        return new

    if config.format == FORMAT_LIST:
        addition = "".join(
            f"{spec.name} = {spec.url}"
            + (f" {spec.branch}" if spec.branch else "")
            + "\n"
            for spec in new
        )
    else:
        chunk: List[str] = []
        for spec in new:
            chunk.extend(_render_repo(spec))
        addition = "\n".join(chunk)

    with config.source.open("a", encoding="utf-8") as handle:
        handle.write("\n" + addition.lstrip("\n"))
    config.repos = merge_specs(config.repos, new)
    return new


def remove_repos(config: FleetConfig, names: Iterable[str]) -> List[str]:
    wanted = set(names)
    removed = [s.name for s in config.repos if s.name in wanted]
    if not removed:
        return []
    config.repos = [s for s in config.repos if s.name not in wanted]
    if config.source and config.format == FORMAT_TOML:
        save_config(config)
    elif config.source and config.format == FORMAT_LIST:
        kept = [
            f"{s.name} = {s.url}" + (f" {s.branch}" if s.branch else "")
            for s in config.repos
        ]
        config.source.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return removed
