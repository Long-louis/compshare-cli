from pathlib import Path

from typer.testing import CliRunner
from compshare_cli import cli
from compshare_cli.config import ConfigStore


runner = CliRunner()


def test_config_set_get_and_unset(monkeypatch, tmp_path: Path):
    store = ConfigStore(tmp_path / "config.json")
    monkeypatch.setattr(cli, "ConfigStore", lambda: store)

    set_result = runner.invoke(cli.app, ["config", "set", "public-key", "abc"])
    get_result = runner.invoke(cli.app, ["config", "get", "--json"])
    unset_result = runner.invoke(cli.app, ["config", "unset", "public-key"])

    assert set_result.exit_code == 0
    assert "Saved public-key" in set_result.stdout
    assert get_result.exit_code == 0
    assert '"public_key": "abc"' in get_result.stdout
    assert unset_result.exit_code == 0
    assert store.get_value("public_key") is None


def test_config_path(monkeypatch, tmp_path: Path):
    store = ConfigStore(tmp_path / "config.json")
    monkeypatch.setattr(cli, "ConfigStore", lambda: store)

    result = runner.invoke(cli.app, ["config", "path"])

    assert result.exit_code == 0
    assert str(tmp_path / "config.json") in result.stdout
