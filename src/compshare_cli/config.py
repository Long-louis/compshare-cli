from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir

CONFIG_FILENAME = "config.json"


@dataclass(frozen=True)
class Credentials:
    public_key: str
    private_key: str


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = (
            path
            or Path(user_config_dir("compshare-cli", "compshare")) / CONFIG_FILENAME
        )

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def get_value(self, key: str) -> str | None:
        value = self.read().get(key)
        return value if isinstance(value, str) and value else None

    def set_value(self, key: str, value: str) -> None:
        data = self.read()
        data[key] = value
        self.write(data)

    def unset_value(self, key: str) -> None:
        data = self.read()
        data.pop(key, None)
        self.write(data)


def redact_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def credential_source(store: ConfigStore | None = None) -> str:
    store = store or ConfigStore()
    env_public = bool(os.getenv("COMPSHARE_PUBLIC_KEY"))
    env_private = bool(os.getenv("COMPSHARE_PRIVATE_KEY"))
    config_public = bool(store.get_value("public_key"))
    config_private = bool(store.get_value("private_key"))
    if env_public and env_private:
        return "env"
    if not env_public and not env_private and config_public and config_private:
        return "config"
    if (env_public or config_public) and (env_private or config_private):
        return "mixed"
    return "missing"


def load_credentials(store: ConfigStore | None = None) -> Credentials | None:
    store = store or ConfigStore()
    public_key = os.getenv("COMPSHARE_PUBLIC_KEY") or store.get_value("public_key")
    private_key = os.getenv("COMPSHARE_PRIVATE_KEY") or store.get_value("private_key")
    if not public_key or not private_key:
        return None
    return Credentials(public_key=public_key, private_key=private_key)
