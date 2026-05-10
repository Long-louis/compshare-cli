from pathlib import Path

from compshare_cli.config import ConfigStore, Credentials, load_credentials, credential_source, redact_secret


def test_env_credentials_override_config(monkeypatch, tmp_path: Path):
    store = ConfigStore(tmp_path / "config.json")
    store.set_value("public_key", "file-public")
    store.set_value("private_key", "file-private")
    monkeypatch.setenv("COMPSHARE_PUBLIC_KEY", "env-public")
    monkeypatch.setenv("COMPSHARE_PRIVATE_KEY", "env-private")

    creds = load_credentials(store)

    assert creds == Credentials(public_key="env-public", private_key="env-private")


def test_config_credentials_used_when_env_missing(monkeypatch, tmp_path: Path):
    store = ConfigStore(tmp_path / "config.json")
    store.set_value("public_key", "file-public")
    store.set_value("private_key", "file-private")
    monkeypatch.delenv("COMPSHARE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("COMPSHARE_PRIVATE_KEY", raising=False)

    creds = load_credentials(store)

    assert creds == Credentials(public_key="file-public", private_key="file-private")


def test_missing_credentials_returns_none(monkeypatch, tmp_path: Path):
    store = ConfigStore(tmp_path / "config.json")
    monkeypatch.delenv("COMPSHARE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("COMPSHARE_PRIVATE_KEY", raising=False)

    assert load_credentials(store) is None


def test_unset_removes_value(tmp_path: Path):
    store = ConfigStore(tmp_path / "config.json")
    store.set_value("public_key", "value")

    store.unset_value("public_key")

    assert store.get_value("public_key") is None


def test_redact_secret_masks_values():
    assert redact_secret("abcdef123456") == "abcd...3456"
    assert redact_secret("") == ""


def test_credential_source_reports_env(monkeypatch, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.set_value("public_key", "config-public")
    store.set_value("private_key", "config-private")
    monkeypatch.setenv("COMPSHARE_PUBLIC_KEY", "env-public")
    monkeypatch.setenv("COMPSHARE_PRIVATE_KEY", "env-private")
    assert credential_source(store) == "env"


def test_credential_source_reports_mixed(monkeypatch, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.set_value("private_key", "config-private")
    monkeypatch.setenv("COMPSHARE_PUBLIC_KEY", "env-public")
    monkeypatch.delenv("COMPSHARE_PRIVATE_KEY", raising=False)
    assert credential_source(store) == "mixed"


def test_credential_source_reports_missing(monkeypatch, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    monkeypatch.delenv("COMPSHARE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("COMPSHARE_PRIVATE_KEY", raising=False)
    assert credential_source(store) == "missing"
