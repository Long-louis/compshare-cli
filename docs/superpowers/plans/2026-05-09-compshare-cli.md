# CompShare CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first `compshare` Python CLI for the CompShare GPU rental loop.

**Architecture:** Implement a small Typer-based CLI over the official `ucloud-sdk-python3` client. Keep credentials, SDK access, request construction, output formatting, and command wiring in focused modules with tests that use fakes instead of real CompShare credentials.

**Tech Stack:** Python 3.11+, uv, Typer, Rich, platformdirs, pytest, ucloud-sdk-python3.

---

## File Structure

- Create: `src/compshare_cli/__init__.py` - package version marker and uv-generated script target.
- Create: `src/compshare_cli/__main__.py` - allows `python -m compshare_cli`.
- Create: `src/compshare_cli/cli.py` - Typer app and command groups.
- Create: `src/compshare_cli/config.py` - environment/config-file credential loading and mutation.
- Create: `src/compshare_cli/errors.py` - CLI exception types and rendering helpers.
- Create: `src/compshare_cli/output.py` - JSON and Rich table/text output helpers.
- Create: `src/compshare_cli/requests.py` - zone resolution and SDK request payload builders.
- Create: `src/compshare_cli/sdk.py` - official SDK client wrapper.
- Create: `tests/test_config.py` - config precedence and mutation tests.
- Create: `tests/test_requests.py` - memory conversion, zone resolution, and create payload tests.
- Create: `tests/test_output.py` - JSON and table rendering tests.
- Create: `tests/test_cli_config.py` - config subcommand tests.
- Create: `tests/test_cli_rental_loop.py` - resource, price, instance, dry-run, and confirmation tests.
- Modify through uv commands: `pyproject.toml` - package metadata, console script, and dependencies.
- Modify through uv commands: `uv.lock` - locked dependency versions.
- Modify: `.gitignore` - already ignores `.firecrawl/`; add `.venv/`, build, and Python cache entries.
- Create: `README.md` - minimal installation and usage documentation.

## Task 1: Scaffold Python Package

**Files:**
- Create by command: `pyproject.toml`
- Create by command: `uv.lock`
- Create: `src/compshare_cli/__init__.py`
- Create: `src/compshare_cli/__main__.py`
- Create: `src/compshare_cli/cli.py`
- Modify: `.gitignore`

- [ ] **Step 1: Initialize package metadata with uv**

Run:

```bash
uv init --package --name compshare --python 3.11
```

Expected: `pyproject.toml`, `README.md`, and a `src/compshare` package scaffold are created or updated by uv. The project name is `compshare` so uv generates the desired `compshare` command.

- [ ] **Step 2: Add runtime and test dependencies with uv**

Run:

```bash
uv add typer rich platformdirs ucloud-sdk-python3
uv add --dev pytest
```

Expected: `pyproject.toml` includes the dependencies and `uv.lock` is generated.

- [ ] **Step 3: Verify uv-generated console script target**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('pyproject.toml').read_text()
assert '[project.scripts]' in text
assert 'compshare =' in text
print('console script present')
PY
```

Expected: prints `console script present`. Do not manually edit `pyproject.toml`; the implementation will make the generated script target call the Typer app.

- [ ] **Step 4: Create the minimal CLI entry files**

Write `src/compshare_cli/__init__.py`:

```python
"""Command line tools for CompShare GPU rental workflows."""

__version__ = "0.1.0"


def main() -> None:
    from .cli import app

    app()
```

Write `src/compshare_cli/__main__.py`:

```python
from .cli import app


if __name__ == "__main__":
    app()
```

Write `src/compshare_cli/cli.py`:

```python
import typer

app = typer.Typer(help="CompShare GPU rental CLI.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """Manage CompShare GPU resources."""
```

If uv created `src/compshare/__init__.py`, replace its contents with a compatibility shim:

```python
from compshare_cli import main

__all__ = ["main"]
```

- [ ] **Step 5: Extend `.gitignore`**

Ensure `.gitignore` contains:

```gitignore
.firecrawl/
.venv/
__pycache__/
.pytest_cache/
dist/
*.egg-info/
```

- [ ] **Step 6: Run scaffold smoke check**

Run:

```bash
uv run compshare --help
```

Expected: command exits `0` and prints `CompShare GPU rental CLI.`.

- [ ] **Step 7: Checkpoint**

Run:

```bash
git status --short
```

Expected: new package files, `.gitignore`, `pyproject.toml`, and `uv.lock` are visible. Commit only if the user has explicitly requested commits.

## Task 2: Config And Credential Loading

**Files:**
- Create: `src/compshare_cli/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing config tests**

Create `tests/test_config.py`:

```python
from pathlib import Path

from compshare_cli.config import ConfigStore, Credentials, load_credentials


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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_config.py -v
```

Expected: FAIL with `ModuleNotFoundError` or missing `ConfigStore`.

- [ ] **Step 3: Implement config module**

Create `src/compshare_cli/config.py`:

```python
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
        self.path = path or Path(user_config_dir("compshare-cli", "compshare")) / CONFIG_FILENAME

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

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


def load_credentials(store: ConfigStore | None = None) -> Credentials | None:
    store = store or ConfigStore()
    public_key = os.getenv("COMPSHARE_PUBLIC_KEY") or store.get_value("public_key")
    private_key = os.getenv("COMPSHARE_PRIVATE_KEY") or store.get_value("private_key")
    if not public_key or not private_key:
        return None
    return Credentials(public_key=public_key, private_key=private_key)
```

- [ ] **Step 4: Run config tests**

Run:

```bash
uv run pytest tests/test_config.py -v
```

Expected: PASS.

- [ ] **Step 5: Checkpoint**

Run:

```bash
git status --short
```

Expected: config module and tests are visible. Commit only if the user has explicitly requested commits.

## Task 3: Request Builders And Zone Resolution

**Files:**
- Create: `src/compshare_cli/requests.py`
- Test: `tests/test_requests.py`

- [ ] **Step 1: Write failing request tests**

Create `tests/test_requests.py`:

```python
import pytest

from compshare_cli.requests import CreateInstanceOptions, build_create_instance_request, resolve_zone_region


ZONES = [
    {"Region": "cn-wlcb", "Zone": "cn-wlcb-01", "Describe": "华北二A"},
    {"Region": "cn-sh2", "Zone": "cn-sh2-02", "Describe": "上海二"},
]


def test_resolve_zone_region_from_zone():
    assert resolve_zone_region("cn-sh2-02", None, ZONES) == ("cn-sh2", "cn-sh2-02")


def test_resolve_zone_region_rejects_unknown_zone():
    with pytest.raises(ValueError, match="Unknown zone"):
        resolve_zone_region("cn-foo-01", None, ZONES)


def test_resolve_zone_region_rejects_mismatched_region():
    with pytest.raises(ValueError, match="does not belong"):
        resolve_zone_region("cn-sh2-02", "cn-wlcb", ZONES)


def test_build_create_instance_request_converts_memory_and_disk():
    options = CreateInstanceOptions(
        zone="cn-sh2-02",
        region="cn-sh2",
        image_id="compshareImage-xxx",
        gpu_type="4090",
        gpu=1,
        cpu=16,
        memory_gib=64,
        disk_size_gib=200,
        name="my-gpu",
    )

    request = build_create_instance_request(options)

    assert request["Region"] == "cn-sh2"
    assert request["Zone"] == "cn-sh2-02"
    assert request["Memory"] == 65536
    assert request["ChargeType"] == "Dynamic"
    assert request["Disks"] == [{"IsBoot": True, "Size": 200, "Type": "CLOUD_SSD"}]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_requests.py -v
```

Expected: FAIL with missing `compshare_cli.requests`.

- [ ] **Step 3: Implement request builders**

Create `src/compshare_cli/requests.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CreateInstanceOptions:
    zone: str
    region: str
    image_id: str
    gpu_type: str
    gpu: int
    cpu: int
    memory_gib: int
    disk_size_gib: int
    name: str | None = None
    machine_type: str = "G"
    disk_type: str = "CLOUD_SSD"
    charge_type: str = "Dynamic"
    quantity: int = 1


def resolve_zone_region(zone: str, region: str | None, zones: list[dict[str, Any]]) -> tuple[str, str]:
    matches = [item for item in zones if item.get("Zone") == zone]
    if not matches:
        raise ValueError(f"Unknown zone: {zone}")
    resolved_region = str(matches[0].get("Region"))
    if region and region != resolved_region:
        raise ValueError(f"Zone {zone} does not belong to region {region}; expected {resolved_region}")
    return resolved_region, zone


def _require_positive(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def build_create_instance_request(options: CreateInstanceOptions) -> dict[str, Any]:
    _require_positive("gpu", options.gpu)
    _require_positive("cpu", options.cpu)
    _require_positive("memory", options.memory_gib)
    _require_positive("disk_size", options.disk_size_gib)
    _require_positive("quantity", options.quantity)

    request: dict[str, Any] = {
        "Region": options.region,
        "Zone": options.zone,
        "MachineType": options.machine_type,
        "CompShareImageId": options.image_id,
        "GPU": options.gpu,
        "GpuType": options.gpu_type,
        "CPU": options.cpu,
        "Memory": options.memory_gib * 1024,
        "ChargeType": options.charge_type,
        "Quantity": options.quantity,
        "Disks": [{"IsBoot": True, "Size": options.disk_size_gib, "Type": options.disk_type}],
    }
    if options.name:
        request["Name"] = options.name
    return request
```

- [ ] **Step 4: Run request tests**

Run:

```bash
uv run pytest tests/test_requests.py -v
```

Expected: PASS.

- [ ] **Step 5: Checkpoint**

Run:

```bash
git status --short
```

Expected: request module and tests are visible. Commit only if the user has explicitly requested commits.

## Task 4: Output And Error Helpers

**Files:**
- Create: `src/compshare_cli/errors.py`
- Create: `src/compshare_cli/output.py`
- Test: `tests/test_output.py`

- [ ] **Step 1: Write failing output tests**

Create `tests/test_output.py`:

```python
from compshare_cli.output import print_json, table_text


def test_print_json_outputs_serialized_payload(capsys):
    print_json({"RetCode": 0, "UHostIds": ["uhost-1"]})

    assert '"RetCode": 0' in capsys.readouterr().out


def test_table_text_renders_headers_and_rows():
    rendered = table_text(["REGION", "ZONE"], [["cn-sh2", "cn-sh2-02"]])

    assert "REGION" in rendered
    assert "cn-sh2-02" in rendered
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_output.py -v
```

Expected: FAIL with missing `compshare_cli.output`.

- [ ] **Step 3: Implement error and output helpers**

Create `src/compshare_cli/errors.py`:

```python
from __future__ import annotations


class CliError(Exception):
    def __init__(self, message: str, *, type_name: str = "CliError", ret_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.type_name = type_name
        self.ret_code = ret_code

    def to_json(self) -> dict[str, object]:
        error: dict[str, object] = {"type": self.type_name, "message": self.message}
        if self.ret_code is not None:
            error["ret_code"] = self.ret_code
        return {"error": error}


MISSING_CREDENTIALS_MESSAGE = """Missing credentials. Set COMPSHARE_PUBLIC_KEY/COMPSHARE_PRIVATE_KEY or run:
  compshare config set public-key ...
  compshare config set private-key ..."""
```

Create `src/compshare_cli/output.py`:

```python
from __future__ import annotations

import json
from io import StringIO
from typing import Any, Iterable

import typer
from rich.console import Console
from rich.table import Table


def print_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def table_text(headers: list[str], rows: Iterable[Iterable[object]]) -> str:
    table = Table(*headers)
    for row in rows:
        table.add_row(*(str(value) for value in row))
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=False, width=120)
    console.print(table)
    return buffer.getvalue()


def print_table(headers: list[str], rows: Iterable[Iterable[object]]) -> None:
    typer.echo(table_text(headers, rows), nl=False)
```

- [ ] **Step 4: Run output tests**

Run:

```bash
uv run pytest tests/test_output.py -v
```

Expected: PASS.

- [ ] **Step 5: Checkpoint**

Run:

```bash
git status --short
```

Expected: output/error modules and tests are visible. Commit only if the user has explicitly requested commits.

## Task 5: SDK Wrapper With Fakeable Interface

**Files:**
- Create: `src/compshare_cli/sdk.py`
- Test: `tests/test_sdk.py`

- [ ] **Step 1: Write failing SDK wrapper tests**

Create `tests/test_sdk.py`:

```python
from compshare_cli.config import Credentials
from compshare_cli.sdk import CompShareClient


class FakeService:
    def __init__(self):
        self.calls = []

    def invoke(self, action, payload):
        self.calls.append((action, payload))
        return {"Action": f"{action}Response", "RetCode": 0}

    def describe_comp_share_support_zone(self, payload):
        self.calls.append(("DescribeCompShareSupportZone", payload))
        return {"RetCode": 0, "ZoneInfo": []}


class FakeSdkClient:
    def __init__(self):
        self.service = FakeService()

    def ucompshare(self):
        return self.service


def test_invoke_uses_ucompshare_service():
    sdk = FakeSdkClient()
    client = CompShareClient(Credentials("public", "private"), sdk_client=sdk)

    response = client.invoke("CreateCompShareInstance", {"Zone": "cn-sh2-02"})

    assert response["RetCode"] == 0
    assert sdk.service.calls == [("CreateCompShareInstance", {"Zone": "cn-sh2-02"})]


def test_support_zones_returns_zone_info():
    sdk = FakeSdkClient()
    client = CompShareClient(Credentials("public", "private"), sdk_client=sdk)

    zones = client.support_zones()

    assert zones == []
    assert sdk.service.calls == [("DescribeCompShareSupportZone", {})]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_sdk.py -v
```

Expected: FAIL with missing `compshare_cli.sdk`.

- [ ] **Step 3: Implement SDK wrapper**

Create `src/compshare_cli/sdk.py`:

```python
from __future__ import annotations

from typing import Any

from ucloud.client import Client

from ucloud.core import exc

from .config import Credentials
from .errors import CliError


DEFAULT_BASE_URL = "https://api.compshare.cn"


class CompShareClient:
    def __init__(self, credentials: Credentials, *, base_url: str = DEFAULT_BASE_URL, sdk_client: Any | None = None) -> None:
        self.credentials = credentials
        self.base_url = base_url
        self._sdk_client = sdk_client

    @property
    def sdk_client(self) -> Any:
        if self._sdk_client is None:
            self._sdk_client = Client(
                {
                    "region": "cn-wlcb",
                    "public_key": self.credentials.public_key,
                    "private_key": self.credentials.private_key,
                    "base_url": self.base_url,
                }
            )
        return self._sdk_client

    def service(self) -> Any:
        return self.sdk_client.ucompshare()

    def invoke(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self.service().invoke(action, payload)
        except exc.UCloudException as error:
            raise CliError(str(error), type_name="UCloudException") from error
        self._raise_for_ret_code(response)
        return response

    def support_zones(self) -> list[dict[str, Any]]:
        try:
            response = self.service().describe_comp_share_support_zone({})
        except exc.UCloudException as error:
            raise CliError(str(error), type_name="UCloudException") from error
        self._raise_for_ret_code(response)
        zones = response.get("ZoneInfo", [])
        return zones if isinstance(zones, list) else []

    @staticmethod
    def _raise_for_ret_code(response: dict[str, Any]) -> None:
        ret_code = response.get("RetCode", 0)
        if ret_code not in (0, None):
            message = str(response.get("Message") or f"CompShare API returned RetCode {ret_code}")
            raise CliError(message, type_name="CompShareApiError", ret_code=int(ret_code))
```

Note: the SDK client still needs an initial region value for construction. Use `cn-wlcb` only as SDK bootstrap configuration; per-request `Region` remains resolved from zone and sent in payload.

- [ ] **Step 4: Run SDK tests**

Run:

```bash
uv run pytest tests/test_sdk.py -v
```

Expected: PASS.

- [ ] **Step 5: Checkpoint**

Run:

```bash
git status --short
```

Expected: SDK wrapper and tests are visible. Commit only if the user has explicitly requested commits.

## Task 6: Config CLI Commands

**Files:**
- Modify: `src/compshare_cli/cli.py`
- Test: `tests/test_cli_config.py`

- [ ] **Step 1: Write failing config CLI tests**

Create `tests/test_cli_config.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_cli_config.py -v
```

Expected: FAIL because `config` commands do not exist.

- [ ] **Step 3: Implement config commands**

Replace `src/compshare_cli/cli.py` with:

```python
from __future__ import annotations

from typing import Annotated

import typer

from .config import ConfigStore
from .output import print_json

app = typer.Typer(help="CompShare GPU rental CLI.", no_args_is_help=True)
config_app = typer.Typer(help="Manage local credentials.", no_args_is_help=True)
app.add_typer(config_app, name="config")

CONFIG_KEYS = {"public-key": "public_key", "private-key": "private_key"}


@app.callback()
def main() -> None:
    """Manage CompShare GPU resources."""


@config_app.command("set")
def config_set(key: Annotated[str, typer.Argument()], value: Annotated[str, typer.Argument()]) -> None:
    if key not in CONFIG_KEYS:
        raise typer.BadParameter(f"key must be one of: {', '.join(CONFIG_KEYS)}")
    ConfigStore().set_value(CONFIG_KEYS[key], value)
    typer.echo(f"Saved {key}")


@config_app.command("get")
def config_get(json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    data = ConfigStore().read()
    safe = {key: ("***" if key == "private_key" and value else value) for key, value in data.items()}
    if json_output:
        print_json(safe)
        return
    for key in ("public_key", "private_key"):
        typer.echo(f"{key}: {safe.get(key, '')}")


@config_app.command("unset")
def config_unset(key: Annotated[str, typer.Argument()]) -> None:
    if key not in CONFIG_KEYS:
        raise typer.BadParameter(f"key must be one of: {', '.join(CONFIG_KEYS)}")
    ConfigStore().unset_value(CONFIG_KEYS[key])
    typer.echo(f"Removed {key}")


@config_app.command("path")
def config_path() -> None:
    typer.echo(str(ConfigStore().path))
```

- [ ] **Step 4: Run config CLI tests**

Run:

```bash
uv run pytest tests/test_cli_config.py -v
```

Expected: PASS.

- [ ] **Step 5: Run full tests so far**

Run:

```bash
uv run pytest tests/test_config.py tests/test_requests.py tests/test_output.py tests/test_sdk.py tests/test_cli_config.py -v
```

Expected: PASS.

- [ ] **Step 6: Checkpoint**

Run:

```bash
git status --short
```

Expected: config CLI is implemented. Commit only if the user has explicitly requested commits.

## Task 7: Rental Loop CLI Commands

**Files:**
- Modify: `src/compshare_cli/cli.py`
- Test: `tests/test_cli_rental_loop.py`

- [ ] **Step 1: Write failing rental-loop CLI tests**

Create `tests/test_cli_rental_loop.py`:

```python
import json

from typer.testing import CliRunner
from compshare_cli import cli
from compshare_cli.config import Credentials


runner = CliRunner()


class FakeCompShareClient:
    def __init__(self):
        self.calls = []

    def support_zones(self):
        self.calls.append(("DescribeCompShareSupportZone", {}))
        return [
            {"Region": "cn-wlcb", "Zone": "cn-wlcb-01", "Describe": "华北二A"},
            {"Region": "cn-sh2", "Zone": "cn-sh2-02", "Describe": "上海二"},
        ]

    def invoke(self, action, payload):
        self.calls.append((action, payload))
        if action == "CreateCompShareInstance":
            return {"RetCode": 0, "UHostIds": ["uhost-1"]}
        if action == "DescribeCompShareInstance":
            return {"RetCode": 0, "UHostSet": [{"UHostId": "uhost-1", "Name": "gpu"}]}
        if action == "GetCompShareInstancePrice":
            return {"RetCode": 0, "Price": 12.3}
        return {"RetCode": 0}


def install_fake_client(monkeypatch):
    fake = FakeCompShareClient()
    monkeypatch.setattr(cli, "load_credentials", lambda: Credentials("public", "private"))
    monkeypatch.setattr(cli, "CompShareClient", lambda credentials: fake)
    return fake


def test_resource_zones_table(monkeypatch):
    install_fake_client(monkeypatch)

    result = runner.invoke(cli.app, ["resource", "zones"])

    assert result.exit_code == 0
    assert "cn-sh2-02" in result.stdout
    assert "上海二" in result.stdout


def test_instance_create_dry_run_outputs_request(monkeypatch):
    fake = install_fake_client(monkeypatch)

    result = runner.invoke(
        cli.app,
        [
            "instance",
            "create",
            "--zone",
            "cn-sh2-02",
            "--image-id",
            "compshareImage-xxx",
            "--gpu-type",
            "4090",
            "--gpu",
            "1",
            "--cpu",
            "16",
            "--memory",
            "64",
            "--disk-size",
            "200",
            "--name",
            "my-gpu",
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["Region"] == "cn-sh2"
    assert payload["Memory"] == 65536
    assert all(call[0] != "CreateCompShareInstance" for call in fake.calls)


def test_instance_create_calls_api(monkeypatch):
    fake = install_fake_client(monkeypatch)

    result = runner.invoke(
        cli.app,
        [
            "instance",
            "create",
            "--zone",
            "cn-sh2-02",
            "--image-id",
            "compshareImage-xxx",
            "--gpu-type",
            "4090",
            "--gpu",
            "1",
            "--cpu",
            "16",
            "--memory",
            "64",
            "--disk-size",
            "200",
        ],
    )

    assert result.exit_code == 0
    assert "uhost-1" in result.stdout
    assert fake.calls[-1][0] == "CreateCompShareInstance"


def test_instance_delete_requires_yes(monkeypatch):
    install_fake_client(monkeypatch)

    result = runner.invoke(cli.app, ["instance", "delete", "uhost-1"])

    assert result.exit_code != 0
    assert "--yes" in result.stdout
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_cli_rental_loop.py -v
```

Expected: FAIL because `resource` and `instance` commands do not exist.

- [ ] **Step 3: Add client factory and shared option helpers to `cli.py`**

Append these imports near the top of `src/compshare_cli/cli.py`:

```python
from .config import ConfigStore, load_credentials
from .errors import CliError, MISSING_CREDENTIALS_MESSAGE
from .output import print_json, print_table
from .requests import CreateInstanceOptions, build_create_instance_request, resolve_zone_region
from .sdk import CompShareClient
```

Add these helpers below the config commands:

```python
def get_client() -> CompShareClient:
    credentials = load_credentials()
    if credentials is None:
        raise CliError(MISSING_CREDENTIALS_MESSAGE, type_name="MissingCredentials")
    return CompShareClient(credentials)


def handle_cli_error(error: CliError, json_output: bool) -> None:
    if json_output:
        print_json(error.to_json())
    else:
        typer.echo(error.message, err=True)
    raise typer.Exit(1)
```

- [ ] **Step 4: Add resource, price, and instance apps to `cli.py`**

Add after `config_app` definition:

```python
resource_app = typer.Typer(help="Discover rentable CompShare resources.", no_args_is_help=True)
price_app = typer.Typer(help="Check CompShare prices.", no_args_is_help=True)
instance_app = typer.Typer(help="Manage CompShare instances.", no_args_is_help=True)
app.add_typer(resource_app, name="resource")
app.add_typer(price_app, name="price")
app.add_typer(instance_app, name="instance")
```

- [ ] **Step 5: Implement zones and create commands in `cli.py`**

Add:

```python
@resource_app.command("zones")
def resource_zones(json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    try:
        zones = get_client().support_zones()
    except CliError as error:
        handle_cli_error(error, json_output)
    if json_output:
        print_json({"ZoneInfo": zones})
        return
    print_table(["REGION", "ZONE", "NAME"], [[z.get("Region", ""), z.get("Zone", ""), z.get("Describe", "")] for z in zones])


def make_create_options(
    zone: str,
    region: str | None,
    image_id: str,
    gpu_type: str,
    gpu: int,
    cpu: int,
    memory: int,
    disk_size: int,
    name: str | None,
) -> CreateInstanceOptions:
    client = get_client()
    resolved_region, resolved_zone = resolve_zone_region(zone, region, client.support_zones())
    return CreateInstanceOptions(
        zone=resolved_zone,
        region=resolved_region,
        image_id=image_id,
        gpu_type=gpu_type,
        gpu=gpu,
        cpu=cpu,
        memory_gib=memory,
        disk_size_gib=disk_size,
        name=name,
    )


@instance_app.command("create")
def instance_create(
    zone: Annotated[str, typer.Option("--zone")],
    image_id: Annotated[str, typer.Option("--image-id")],
    gpu_type: Annotated[str, typer.Option("--gpu-type")],
    gpu: Annotated[int, typer.Option("--gpu")],
    cpu: Annotated[int, typer.Option("--cpu")],
    memory: Annotated[int, typer.Option("--memory", help="Memory in GiB.")],
    disk_size: Annotated[int, typer.Option("--disk-size", help="Boot disk size in GiB.")],
    region: Annotated[str | None, typer.Option("--region")] = None,
    name: Annotated[str | None, typer.Option("--name")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
) -> None:
    try:
        options = make_create_options(zone, region, image_id, gpu_type, gpu, cpu, memory, disk_size, name)
        payload = build_create_instance_request(options)
        if dry_run:
            print_json(payload) if json_output else typer.echo(payload)
            return
        response = get_client().invoke("CreateCompShareInstance", payload)
    except (CliError, ValueError) as error:
        handle_cli_error(error if isinstance(error, CliError) else CliError(str(error)), json_output)
    if json_output:
        print_json(response)
        return
    typer.echo(f"Created instance: {', '.join(response.get('UHostIds', []))}")
```

- [ ] **Step 6: Implement remaining API command wrappers in `cli.py`**

Add:

```python
@price_app.command("create")
def price_create(
    zone: Annotated[str, typer.Option("--zone")],
    image_id: Annotated[str, typer.Option("--image-id")],
    gpu_type: Annotated[str, typer.Option("--gpu-type")],
    gpu: Annotated[int, typer.Option("--gpu")],
    cpu: Annotated[int, typer.Option("--cpu")],
    memory: Annotated[int, typer.Option("--memory")],
    disk_size: Annotated[int, typer.Option("--disk-size")],
    region: Annotated[str | None, typer.Option("--region")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
) -> None:
    try:
        options = make_create_options(zone, region, image_id, gpu_type, gpu, cpu, memory, disk_size, None)
        response = get_client().invoke("GetCompShareInstancePrice", build_create_instance_request(options))
    except (CliError, ValueError) as error:
        handle_cli_error(error if isinstance(error, CliError) else CliError(str(error)), json_output)
    print_json(response) if json_output else typer.echo(response)


@instance_app.command("list")
def instance_list(json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    try:
        response = get_client().invoke("DescribeCompShareInstance", {})
    except CliError as error:
        handle_cli_error(error, json_output)
    if json_output:
        print_json(response)
        return
    rows = [[item.get("UHostId", ""), item.get("Name", ""), item.get("State", "")] for item in response.get("UHostSet", [])]
    print_table(["ID", "NAME", "STATE"], rows)


@instance_app.command("show")
def instance_show(instance_id: str, json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    try:
        response = get_client().invoke("DescribeCompShareInstance", {"UHostIds": [instance_id]})
    except CliError as error:
        handle_cli_error(error, json_output)
    print_json(response) if json_output else typer.echo(response)


def invoke_instance_action(action: str, instance_id: str, json_output: bool) -> None:
    try:
        response = get_client().invoke(action, {"UHostId": instance_id})
    except CliError as error:
        handle_cli_error(error, json_output)
    print_json(response) if json_output else typer.echo("OK")


@instance_app.command("start")
def instance_start(instance_id: str, json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    invoke_instance_action("StartCompShareInstance", instance_id, json_output)


@instance_app.command("stop")
def instance_stop(instance_id: str, json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    invoke_instance_action("StopCompShareInstance", instance_id, json_output)


@instance_app.command("reboot")
def instance_reboot(instance_id: str, json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    invoke_instance_action("RebootCompShareInstance", instance_id, json_output)


@instance_app.command("delete")
def instance_delete(
    instance_id: str,
    yes: Annotated[bool, typer.Option("--yes", help="Confirm deletion.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
) -> None:
    if not yes:
        raise typer.BadParameter("instance delete requires --yes")
    invoke_instance_action("TerminateCompShareInstance", instance_id, json_output)
```

Add simple resource wrappers after `resource_zones`:

```python
@resource_app.command("machine-families")
def resource_machine_families(json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    response = get_client().invoke("DescribeCompShareMachineTypeFamilies", {})
    print_json(response) if json_output else typer.echo(response)


@resource_app.command("instance-types")
def resource_instance_types(
    zone: Annotated[str, typer.Option("--zone")],
    gpu_type: Annotated[str | None, typer.Option("--gpu-type")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
) -> None:
    payload = {"Zone": zone}
    if gpu_type:
        payload["GpuType"] = gpu_type
    response = get_client().invoke("DescribeAvailableCompShareInstanceTypes", payload)
    print_json(response) if json_output else typer.echo(response)


@resource_app.command("images")
def resource_images(
    image_type: Annotated[str, typer.Option("--type")] = "platform",
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
) -> None:
    action = "DescribeCommunityImages" if image_type == "community" else "DescribeCompShareImages"
    response = get_client().invoke(action, {})
    print_json(response) if json_output else typer.echo(response)


@resource_app.command("capacity")
def resource_capacity(
    zone: Annotated[str, typer.Option("--zone")],
    image_id: Annotated[str, typer.Option("--image-id")],
    gpu_type: Annotated[str, typer.Option("--gpu-type")],
    gpu: Annotated[int, typer.Option("--gpu")],
    cpu: Annotated[int, typer.Option("--cpu")],
    memory: Annotated[int, typer.Option("--memory")],
    disk_size: Annotated[int, typer.Option("--disk-size")],
    region: Annotated[str | None, typer.Option("--region")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
) -> None:
    try:
        options = make_create_options(zone, region, image_id, gpu_type, gpu, cpu, memory, disk_size, None)
        response = get_client().invoke("CheckCompShareResourceCapacity", build_create_instance_request(options))
    except (CliError, ValueError) as error:
        handle_cli_error(error if isinstance(error, CliError) else CliError(str(error)), json_output)
    print_json(response) if json_output else typer.echo(response)
```

- [ ] **Step 7: Run rental-loop tests**

Run:

```bash
uv run pytest tests/test_cli_rental_loop.py -v
```

Expected: PASS. If the `CompShareClient` monkeypatch lambda receives unexpected keyword arguments, change `get_client()` to call `CompShareClient(credentials)` exactly as shown.

- [ ] **Step 8: Run all tests**

Run:

```bash
uv run pytest -v
```

Expected: PASS.

- [ ] **Step 9: Check CLI smoke commands**

Run:

```bash
uv run compshare --help
uv run compshare config --help
uv run compshare resource --help
uv run compshare instance --help
```

Expected: all commands exit `0` and display help.

- [ ] **Step 10: Checkpoint**

Run:

```bash
git status --short
```

Expected: rental-loop CLI is implemented. Commit only if the user has explicitly requested commits.

## Task 8: README And Final Verification

**Files:**
- Create or Modify: `README.md`
- Verify: full test suite and CLI smoke commands

- [ ] **Step 1: Write README content**

Create or replace `README.md` with:

```markdown
# compshare-cli

Python CLI for common CompShare GPU rental workflows.

## Install

```bash
uv tool install .
```

## Credentials

Use environment variables:

```bash
export COMPSHARE_PUBLIC_KEY=...
export COMPSHARE_PRIVATE_KEY=...
```

Or store credentials locally:

```bash
compshare config set public-key ...
compshare config set private-key ...
```

Environment variables override the local config file.

## Discover Zones

```bash
compshare resource zones
```

## Check Price

```bash
compshare price create \
  --zone cn-sh2-02 \
  --image-id compshareImage-xxx \
  --gpu-type 4090 \
  --gpu 1 \
  --cpu 16 \
  --memory 64 \
  --disk-size 200
```

## Create Instance

```bash
compshare instance create \
  --zone cn-sh2-02 \
  --image-id compshareImage-xxx \
  --gpu-type 4090 \
  --gpu 1 \
  --cpu 16 \
  --memory 64 \
  --disk-size 200 \
  --name my-gpu
```

Use `--dry-run --json` to inspect the request body without creating resources.

## JSON Output

Most commands accept `--json` for automation.
```

- [ ] **Step 2: Run final tests**

Run:

```bash
uv run pytest -v
```

Expected: PASS.

- [ ] **Step 3: Run final CLI smoke checks**

Run:

```bash
uv run compshare --help
uv run compshare instance create --help
uv run compshare resource zones --help
```

Expected: all commands exit `0`.

- [ ] **Step 4: Inspect working tree**

Run:

```bash
git status --short
```

Expected: only intentional project files are changed. `.firecrawl/` does not appear because it is ignored.

- [ ] **Step 5: Final checkpoint**

Do not claim completion unless Step 2 and Step 3 passed. Commit only if the user has explicitly requested commits.
