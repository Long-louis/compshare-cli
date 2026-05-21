from __future__ import annotations

import tomllib
from importlib import metadata
from pathlib import Path

from compshare_cli import __version__


def test_runtime_version_matches_project_metadata() -> None:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))["project"]

    assert project["version"] == __version__


def test_installed_package_version_matches_runtime_version() -> None:
    assert metadata.version("compshare") == __version__
