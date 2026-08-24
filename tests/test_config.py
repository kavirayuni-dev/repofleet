from pathlib import Path

import pytest

from repofleet.config import (
    FleetConfig,
    append_repos,
    load_config,
    merge_specs,
    normalize_url,
    parse_list_line,
    remove_repos,
    save_config,
)
from repofleet.models import RepoSpec, name_from_url, sanitize_url


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://host/org/repo.git", "repo"),
        ("https://user@dev.azure.com/org/Proj/_git/portfolios.api", "portfolios.api"),
        ("git@github.com:org/some-repo.git", "some-repo"),
        ("ssh://git@host:22/org/repo/", "repo"),
    ],
)
def test_name_from_url(url, expected):
    assert name_from_url(url) == expected


def test_name_from_url_rejects_garbage():
    with pytest.raises(ValueError):
        name_from_url("   ")


def test_sanitize_url_masks_credentials():
    assert (
        sanitize_url("https://token:x@host/org/repo.git")
        == "https://***@host/org/repo.git"
    )


def test_normalize_url_ignores_userinfo_and_suffix():
    assert normalize_url("https://user@host/org/Repo.git") == normalize_url(
        "https://host/org/repo"
    )


@pytest.mark.parametrize(
    "line,name,url,branch",
    [
        ("https://host/org/repo.git", "repo", "https://host/org/repo.git", None),
        (
            "alias = https://host/org/repo.git",
            "alias",
            "https://host/org/repo.git",
            None,
        ),
        (
            "https://host/org/repo.git develop",
            "repo",
            "https://host/org/repo.git",
            "develop",
        ),
    ],
)
def test_parse_list_line(line, name, url, branch):
    spec = parse_list_line(line)
    assert (spec.name, spec.url, spec.branch) == (name, url, branch)


@pytest.mark.parametrize("line", ["", "   ", "# comment"])
def test_parse_list_line_skips(line):
    assert parse_list_line(line) is None


def test_merge_specs_dedupes_by_url():
    a = [RepoSpec.from_url("https://host/org/repo.git")]
    b = [
        RepoSpec.from_url("https://other@host/org/repo"),
        RepoSpec.from_url("https://host/org/two"),
    ]
    assert [s.name for s in merge_specs(a, b)] == ["repo", "two"]


def test_roundtrip_toml(tmp_path: Path):
    config = FleetConfig(
        name="demo",
        directory="demo-workspace",
        repos=[RepoSpec.from_url("https://host/org/one.git", branch="main")],
    )
    path = save_config(config, tmp_path / "repofleet.toml")
    loaded = load_config(path)
    assert loaded.name == "demo"
    assert loaded.directory == "demo-workspace"
    assert [(s.name, s.branch) for s in loaded.repos] == [("one", "main")]


def test_append_and_remove(tmp_path: Path):
    config = FleetConfig(
        name="demo", repos=[RepoSpec.from_url("https://host/org/one.git")]
    )
    save_config(config, tmp_path / "repofleet.toml")

    added = append_repos(config, [RepoSpec.from_url("https://host/org/two.git")])
    assert [s.name for s in added] == ["two"]
    assert [s.name for s in load_config(config.source).repos] == ["one", "two"]

    assert append_repos(config, [RepoSpec.from_url("https://host/org/two")]) == []

    assert remove_repos(config, ["one"]) == ["one"]
    assert [s.name for s in load_config(config.source).repos] == ["two"]


def test_list_format(tmp_path: Path):
    listing = tmp_path / "repos.txt"
    listing.write_text(
        "# team repos\nhttps://host/org/one.git\napi = https://host/org/two.git develop\n",
        encoding="utf-8",
    )
    config = load_config(listing)
    assert [(s.name, s.branch) for s in config.repos] == [
        ("one", None),
        ("api", "develop"),
    ]


def test_resolve_root_auto_uses_directory_when_empty(tmp_path: Path):
    config = FleetConfig(
        name="Fleet", directory="Portfolios Backend", source=tmp_path / "repofleet.toml"
    )
    assert config.resolve_root() == (tmp_path / "Portfolios Backend").resolve()


def test_resolve_root_auto_uses_base_when_repos_exist(tmp_path: Path):
    (tmp_path / "repo-a" / ".git").mkdir(parents=True)
    config = FleetConfig(
        name="Fleet", directory="X", source=tmp_path / "repofleet.toml"
    )
    assert config.resolve_root() == tmp_path.resolve()


def test_resolve_root_override(tmp_path: Path):
    config = FleetConfig(source=tmp_path / "repofleet.toml")
    assert (
        config.resolve_root(str(tmp_path / "custom")) == (tmp_path / "custom").resolve()
    )
