from pathlib import Path
import json

from typer.testing import CliRunner
from compshare_cli import cli
from compshare_cli.config import ConfigStore


runner = CliRunner()


def test_config_set_get_and_unset(monkeypatch, tmp_path: Path):
    store = ConfigStore(tmp_path / "config.json")
    monkeypatch.setattr(cli, "ConfigStore", lambda: store)

    # Set both keys
    set_public = runner.invoke(cli.app, ["config", "set", "public-key", "public-secret-1234"])
    set_private = runner.invoke(cli.app, ["config", "set", "private-key", "private-secret-5678"])
    get_result = runner.invoke(cli.app, ["config", "get", "--json"])
    unset_public = runner.invoke(cli.app, ["config", "unset", "public-key"])
    unset_private = runner.invoke(cli.app, ["config", "unset", "private-key"])

    assert set_public.exit_code == 0
    assert "Saved public-key" in set_public.stdout
    assert set_private.exit_code == 0
    assert "Saved private-key" in set_private.stdout

    assert get_result.exit_code == 0
    data = json.loads(get_result.stdout)
    assert data["public_key"] == "publ...1234"
    assert data["private_key"] == "priv...5678"
    assert "public-secret-1234" not in get_result.stdout
    assert "private-secret-5678" not in get_result.stdout

    assert unset_public.exit_code == 0
    assert store.get_value("public_key") is None
    assert unset_private.exit_code == 0
    assert store.get_value("private_key") is None


def test_config_path(monkeypatch, tmp_path: Path):
    store = ConfigStore(tmp_path / "config.json")
    monkeypatch.setattr(cli, "ConfigStore", lambda: store)

    result = runner.invoke(cli.app, ["config", "path"])

    assert result.exit_code == 0
    assert str(tmp_path / "config.json") in result.stdout
