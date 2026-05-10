# Agent-Friendly CLI Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `doctor`, clean JSON output, and an agent-oriented `--agent` envelope so future code agents can safely manage CompShare GPU instances.

**Architecture:** Keep API calls and request construction in existing modules, but move presentation decisions into focused output/model helpers. Every command will select one of three modes: human text, `--json` raw/structured data, or `--agent` decision envelope.

**Tech Stack:** Python 3.11, Typer, Rich, ucloud-sdk-python3, pytest, uv.

---

## File Structure

- Modify: `src/compshare_cli/output.py` - add stable JSON printing, agent envelope helpers, command suggestion helpers, and SDK log suppression.
- Modify: `src/compshare_cli/config.py` - add credential source detection and redaction helpers.
- Modify: `src/compshare_cli/errors.py` - add optional `hint` support for JSON errors.
- Modify: `src/compshare_cli/cli.py` - add `doctor`, `--agent`, `--debug`, normalized command output, and cleaner text renderers.
- Modify: `src/compshare_cli/requests.py` - add helpers for reconstructing command strings from create options.
- Modify: `tests/test_output.py` - cover envelope and command suggestion shapes.
- Modify: `tests/test_config.py` - cover credential source and redaction.
- Modify: `tests/test_cli_config.py` - cover config masking behavior.
- Modify: `tests/test_cli_rental_loop.py` - cover `--agent`, clean `--json`, and dry-run behavior.
- Create: `tests/test_cli_doctor.py` - cover doctor success and missing-credential flows.
- Modify: `README.md` - document `doctor`, `--json`, `--agent`, debug, and safety rules.
- Create: `.agents/skills/compshare-cli/SKILL.md` - companion skill for future agents using this CLI.

## Task 1: Output Helpers And SDK Log Suppression

**Files:**
- Modify: `src/compshare_cli/output.py`
- Test: `tests/test_output.py`

- [ ] **Step 1: Write failing tests for agent envelope and suggestions**

Append to `tests/test_output.py`:

```python
import json

from compshare_cli.output import agent_envelope, command_suggestion, print_json, quiet_sdk_logs


def test_agent_envelope_includes_required_fields():
    payload = agent_envelope(
        command="resource zones",
        summary="Found 2 supported zones.",
        data={"zones": []},
        cost_risk="read-only",
    )

    assert payload == {
        "ok": True,
        "command": "resource zones",
        "summary": "Found 2 supported zones.",
        "data": {"zones": []},
        "warnings": [],
        "next_actions": [],
        "commands": [],
        "cost_risk": "read-only",
        "debug": {},
    }


def test_command_suggestion_has_risk_and_confirmation():
    suggestion = command_suggestion(
        label="Create instance",
        command="compshare instance create --agent",
        risk="cost-incurring",
        requires_confirmation=True,
    )

    assert suggestion == {
        "label": "Create instance",
        "command": "compshare instance create --agent",
        "risk": "cost-incurring",
        "requires_confirmation": True,
    }


def test_print_json_is_parseable_stdout(capsys):
    print_json({"ok": True})

    assert json.loads(capsys.readouterr().out) == {"ok": True}


def test_quiet_sdk_logs_sets_ucloud_logger_above_info():
    logger = quiet_sdk_logs()

    assert logger.name == "ucloud"
    assert logger.level > 20
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_output.py -v`

Expected: FAIL because `agent_envelope`, `command_suggestion`, and `quiet_sdk_logs` are not defined.

- [ ] **Step 3: Implement output helpers**

Replace `src/compshare_cli/output.py` with:

```python
from __future__ import annotations

import json
import logging
from io import StringIO
from typing import Any, Iterable, Literal

import typer
from rich.console import Console
from rich.table import Table

Risk = Literal["safe", "read-only", "may-incur-cost", "cost-incurring", "destructive", "sensitive"]
CostRisk = Literal["none", "read-only", "may-incur-cost", "cost-incurring", "destructive", "sensitive"]


def quiet_sdk_logs() -> logging.Logger:
    logger = logging.getLogger("ucloud")
    logger.setLevel(logging.WARNING)
    return logger


def print_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def command_suggestion(label: str, command: str, risk: Risk, requires_confirmation: bool) -> dict[str, object]:
    return {
        "label": label,
        "command": command,
        "risk": risk,
        "requires_confirmation": requires_confirmation,
    }


def agent_envelope(
    *,
    command: str,
    summary: str,
    data: dict[str, Any] | None = None,
    ok: bool = True,
    warnings: list[str] | None = None,
    next_actions: list[str] | None = None,
    commands: list[dict[str, object]] | None = None,
    cost_risk: CostRisk = "none",
    debug: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "command": command,
        "summary": summary,
        "data": data or {},
        "warnings": warnings or [],
        "next_actions": next_actions or [],
        "commands": commands or [],
        "cost_risk": cost_risk,
        "debug": debug or {},
    }


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

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_output.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/compshare_cli/output.py tests/test_output.py
git commit -m "feat: add agent output helpers"
```

## Task 2: Credential Source And Redaction

**Files:**
- Modify: `src/compshare_cli/config.py`
- Modify: `src/compshare_cli/cli.py`
- Test: `tests/test_config.py`
- Test: `tests/test_cli_config.py`

- [ ] **Step 1: Write failing config tests**

Append to `tests/test_config.py`:

```python
from compshare_cli.config import credential_source, redact_secret


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
```

Modify `tests/test_cli_config.py` so config-get stores both keys and expects both values to be masked:

```python
set_public = runner.invoke(cli.app, ["config", "set", "public-key", "public-secret-1234"])
set_private = runner.invoke(cli.app, ["config", "set", "private-key", "private-secret-5678"])
get_result = runner.invoke(cli.app, ["config", "get", "--json"])

assert set_public.exit_code == 0
assert set_private.exit_code == 0
assert get_result.exit_code == 0
assert '"public_key": "publ...1234"' in get_result.stdout
assert '"private_key": "priv...5678"' in get_result.stdout
assert "public-secret-1234" not in get_result.stdout
assert "private-secret-5678" not in get_result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_config.py tests/test_cli_config.py -v`

Expected: FAIL because helper functions do not exist and `config get` still exposes public key.

- [ ] **Step 3: Implement config helpers and mask both keys**

Add to `src/compshare_cli/config.py`:

```python
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
```

Modify imports and `config_get` in `src/compshare_cli/cli.py`:

```python
from .config import ConfigStore, credential_source, load_credentials, redact_secret
```

```python
safe = {key: redact_secret(value) for key, value in data.items()}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py tests/test_cli_config.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/compshare_cli/config.py src/compshare_cli/cli.py tests/test_config.py tests/test_cli_config.py
git commit -m "fix: redact configured credentials"
```

## Task 3: Doctor Command

**Files:**
- Modify: `src/compshare_cli/cli.py`
- Test: `tests/test_cli_doctor.py`

- [ ] **Step 1: Write failing doctor tests**

Create `tests/test_cli_doctor.py`:

```python
import json

from typer.testing import CliRunner

from compshare_cli import cli
from compshare_cli.config import Credentials

runner = CliRunner()


class FakeDoctorClient:
    def support_zones(self):
        return [
            {"Region": "cn-wlcb", "Zone": "cn-wlcb-01", "Describe": "华北二A"},
            {"Region": "cn-sh2", "Zone": "cn-sh2-02", "Describe": "上海二B"},
        ]

    def invoke(self, action, payload):
        assert action == "DescribeCompShareInstance"
        assert payload == {}
        return {
            "RetCode": 0,
            "TotalCount": 1,
            "UHostSet": [
                {"UHostId": "uhost-1", "Name": "stopped-gpu", "State": "Stopped", "Zone": "cn-sh2-02"}
            ],
        }


def test_doctor_agent_success(monkeypatch):
    monkeypatch.setattr(cli, "load_credentials", lambda: Credentials("public", "private"))
    monkeypatch.setattr(cli, "credential_source", lambda: "config")
    monkeypatch.setattr(cli, "CompShareClient", lambda credentials: FakeDoctorClient())

    result = runner.invoke(cli.app, ["doctor", "--agent"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "doctor"
    assert payload["data"]["credentials"] == {"available": True, "source": "config"}
    assert payload["data"]["api"] == {"reachable": True}
    assert payload["data"]["instances"]["count"] == 1
    assert payload["commands"][0]["risk"] == "safe"


def test_doctor_agent_missing_credentials(monkeypatch):
    monkeypatch.setattr(cli, "load_credentials", lambda: None)
    monkeypatch.setattr(cli, "credential_source", lambda: "missing")

    result = runner.invoke(cli.app, ["doctor", "--agent"])

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["data"]["credentials"] == {"available": False, "source": "missing"}
    assert payload["commands"][0]["risk"] == "sensitive"


def test_doctor_json_missing_credentials_is_parseable(monkeypatch):
    monkeypatch.setattr(cli, "load_credentials", lambda: None)
    monkeypatch.setattr(cli, "credential_source", lambda: "missing")

    result = runner.invoke(cli.app, ["doctor", "--json"])

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["credentials"]["available"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli_doctor.py -v`

Expected: FAIL because `doctor` is not implemented.

- [ ] **Step 3: Implement doctor command**

In `src/compshare_cli/cli.py`, import `agent_envelope` and `command_suggestion`:

```python
from .output import agent_envelope, command_suggestion, print_json, print_table, quiet_sdk_logs
```

Call `quiet_sdk_logs()` near module load after app creation:

```python
quiet_sdk_logs()
```

Add the command before sub-app commands:

```python
@app.command("doctor")
def doctor(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Output agent decision envelope.")] = False,
    debug: Annotated[bool, typer.Option("--debug", help="Include diagnostic details.")] = False,
) -> None:
    source = credential_source()
    credentials = load_credentials()
    if credentials is None:
        data = {"credentials": {"available": False, "source": source}, "api": {"reachable": False}}
        if agent_output:
            print_json(agent_envelope(
                ok=False,
                command="doctor",
                summary="CompShare credentials are missing.",
                data=data,
                warnings=["No CompShare credentials configured."],
                next_actions=["Configure credentials before running live API commands."],
                commands=[
                    command_suggestion("Set public key", "compshare config set public-key <PUBLIC_KEY>", "sensitive", True),
                    command_suggestion("Set private key", "compshare config set private-key <PRIVATE_KEY>", "sensitive", True),
                ],
            ))
        elif json_output:
            print_json(data)
        else:
            typer.echo("CompShare credentials are missing.", err=True)
        raise typer.Exit(1)

    client = CompShareClient(credentials)
    try:
        zones = client.support_zones()
        instances = client.invoke("DescribeCompShareInstance", {})
    except CliError as error:
        handle_cli_error(error, json_output or agent_output)

    normalized_zones = normalize_zones(zones)
    normalized_instances = normalize_instances(instances.get("UHostSet", []))[:5]
    data = {
        "credentials": {"available": True, "source": source},
        "api": {"reachable": True},
        "zones": normalized_zones,
        "instances": {"count": int(instances.get("TotalCount", len(normalized_instances))), "items": normalized_instances},
    }
    if agent_output:
        print_json(agent_envelope(
            command="doctor",
            summary=f"CompShare CLI is configured and API is reachable. Found {len(normalized_zones)} zones and {data['instances']['count']} instances.",
            data=data,
            next_actions=[
                "Use an existing stopped instance if it matches the experiment requirements.",
                "Run price and capacity checks before creating a new instance.",
            ],
            commands=[
                command_suggestion("List current instances", "compshare instance list --agent", "safe", False),
                command_suggestion("Check zones", "compshare resource zones --agent", "safe", False),
            ],
            cost_risk="read-only",
            debug={"zone_count": len(normalized_zones)} if debug else {},
        ))
    elif json_output:
        print_json(data)
    else:
        typer.echo(f"CompShare CLI is configured. Found {len(normalized_zones)} zones and {data['instances']['count']} instances.")
```

If `normalize_zones` and `normalize_instances` do not exist yet, Task 4 will add them before this command passes. For this task, add minimal local implementations at module level:

```python
def normalize_zones(zones: list[dict]) -> list[dict[str, object]]:
    return [{"region": z.get("Region", ""), "zone": z.get("Zone", ""), "name": z.get("Describe", "")} for z in zones]


def normalize_instances(items: list[dict]) -> list[dict[str, object]]:
    return [{"id": item.get("UHostId", ""), "name": item.get("Name", ""), "state": item.get("State", ""), "zone": item.get("Zone", "")} for item in items]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli_doctor.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/compshare_cli/cli.py tests/test_cli_doctor.py
git commit -m "feat: add doctor command"
```

## Task 4: Agent Output For Resource And Price Commands

**Files:**
- Modify: `src/compshare_cli/cli.py`
- Test: `tests/test_cli_rental_loop.py`

- [ ] **Step 1: Write failing tests for resource and price agent output**

Append to `tests/test_cli_rental_loop.py`:

```python
def test_resource_zones_agent_output(monkeypatch):
    install_fake_client(monkeypatch)

    result = runner.invoke(cli.app, ["resource", "zones", "--agent"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "resource zones"
    assert payload["data"]["zones"][1] == {"region": "cn-sh2", "zone": "cn-sh2-02", "name": "上海二B"}
    assert payload["cost_risk"] == "read-only"


def test_price_create_agent_output_includes_cost_command(monkeypatch):
    fake = install_fake_client(monkeypatch)

    result = runner.invoke(
        cli.app,
        [
            "price",
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
            "--agent",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "price create"
    assert payload["cost_risk"] == "read-only"
    assert any(command["risk"] == "cost-incurring" for command in payload["commands"])
    assert fake.calls[-1][0] == "GetCompShareInstancePrice"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli_rental_loop.py::test_resource_zones_agent_output tests/test_cli_rental_loop.py::test_price_create_agent_output_includes_cost_command -v`

Expected: FAIL because `--agent` is not accepted by these commands.

- [ ] **Step 3: Implement `--agent` on resource zones and price create**

Add helper in `src/compshare_cli/cli.py`:

```python
def create_command_from_payload(payload: dict[str, object], *, agent: bool = False, dry_run: bool = False) -> str:
    parts = [
        "compshare instance create",
        f"--zone {payload['Zone']}",
        f"--image-id {payload['CompShareImageId']}",
        f"--gpu-type {payload['GpuType']}",
        f"--gpu {payload['GPU']}",
        f"--cpu {payload['CPU']}",
        f"--memory {int(payload['Memory']) // 1024}",
        f"--disk-size {payload['Disks'][0]['Size']}",
    ]
    if dry_run:
        parts.append("--dry-run")
    if agent:
        parts.append("--agent")
    return " ".join(parts)
```

Modify `resource_zones` signature and output branch:

```python
def resource_zones(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Output agent decision envelope.")] = False,
) -> None:
```

Before the `json_output` branch:

```python
if agent_output:
    normalized = normalize_zones(zones)
    print_json(agent_envelope(
        command="resource zones",
        summary=f"Found {len(normalized)} supported zones.",
        data={"zones": normalized},
        next_actions=["Choose a zone before checking images, capacity, or prices."],
        commands=[
            command_suggestion("List platform images", "compshare resource images --type platform --agent", "safe", False),
            command_suggestion("List instances", "compshare instance list --agent", "safe", False),
        ],
        cost_risk="read-only",
    ))
    return
```

Modify `price_create` signature to include `agent_output`, then after `response`:

```python
if agent_output:
    payload = build_create_instance_request(options)
    capacity_command = (
        f"compshare resource capacity --zone {zone} --image-id {image_id} "
        f"--gpu-type {gpu_type} --gpu {gpu} --cpu {cpu} --memory {memory} "
        f"--disk-size {disk_size} --agent"
    )
    print_json(agent_envelope(
        command="price create",
        summary="Fetched CompShare instance price for the requested spec.",
        data={"request": payload, "price": response},
        warnings=["Creating this instance will incur cost."],
        next_actions=["Check resource capacity before creating the instance.", "Use dry-run before live creation."],
        commands=[
            command_suggestion("Check capacity", capacity_command, "safe", False),
            command_suggestion("Preview instance creation", create_command_from_payload(payload, agent=True, dry_run=True), "safe", False),
            command_suggestion("Create instance", create_command_from_payload(payload, agent=True), "cost-incurring", True),
        ],
        cost_risk="read-only",
    ))
    return
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli_rental_loop.py::test_resource_zones_agent_output tests/test_cli_rental_loop.py::test_price_create_agent_output_includes_cost_command -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/compshare_cli/cli.py tests/test_cli_rental_loop.py
git commit -m "feat: add agent output for discovery"
```

## Task 5: Agent Output For Instance Commands

**Files:**
- Modify: `src/compshare_cli/cli.py`
- Test: `tests/test_cli_rental_loop.py`

- [ ] **Step 1: Write failing instance agent tests**

Append to `tests/test_cli_rental_loop.py`:

```python
def test_instance_list_agent_suggests_actions(monkeypatch):
    install_fake_client(monkeypatch)

    result = runner.invoke(cli.app, ["instance", "list", "--agent"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "instance list"
    assert payload["data"]["instances"][0]["id"] == "uhost-1"
    assert any(command["risk"] == "cost-incurring" for command in payload["commands"])


def test_instance_create_dry_run_agent_does_not_create(monkeypatch):
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
            "--dry-run",
            "--agent",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "instance create"
    assert payload["data"]["dry_run"] is True
    assert fake.calls[-1][0] == "DescribeCompShareSupportZone"
    assert all(call[0] != "CreateCompShareInstance" for call in fake.calls)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli_rental_loop.py::test_instance_list_agent_suggests_actions tests/test_cli_rental_loop.py::test_instance_create_dry_run_agent_does_not_create -v`

Expected: FAIL because `--agent` is not accepted by these commands.

- [ ] **Step 3: Implement instance agent output**

Add `agent_output` to `instance_create`, `instance_list`, `instance_show`, and lifecycle command signatures.

For `instance_create`, use this dry-run branch:

```python
if dry_run:
    if agent_output:
        print_json(agent_envelope(
            command="instance create",
            summary="Previewed CompShare instance creation. No instance was created.",
            data={"dry_run": True, "request": payload},
            warnings=["Live creation will incur cost."],
            next_actions=["Ask the user before running the live create command."],
            commands=[command_suggestion("Create instance", create_command_from_payload(payload, agent=True), "cost-incurring", True)],
            cost_risk="none",
        ))
    elif json_output:
        print_json(payload)
    else:
        print_response(payload, False)
    return
```

For `instance_list --agent`, normalize instances and suggest actions:

```python
if agent_output:
    instances = normalize_instances(response.get("UHostSet", []))
    suggestions = []
    for item in instances[:5]:
        instance_id = item.get("id", "")
        if item.get("state") == "Stopped":
            suggestions.append(command_suggestion(f"Start {instance_id}", f"compshare instance start {instance_id} --agent", "cost-incurring", True))
        elif item.get("state"):
            suggestions.append(command_suggestion(f"Show {instance_id}", f"compshare instance show {instance_id} --agent", "safe", False))
    print_json(agent_envelope(
        command="instance list",
        summary=f"Found {len(instances)} CompShare instances.",
        data={"instances": instances},
        commands=suggestions,
        cost_risk="read-only",
    ))
    return
```

For lifecycle commands, keep the first implementation minimal:

```python
print_json(agent_envelope(
    command=f"instance {command_name}",
    summary=f"Requested {command_name} for instance {instance_id}.",
    data={"instance_id": instance_id, "response": response},
    commands=[command_suggestion("Show instance", f"compshare instance show {instance_id} --agent", "safe", False)],
    cost_risk=cost_risk,
))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli_rental_loop.py::test_instance_list_agent_suggests_actions tests/test_cli_rental_loop.py::test_instance_create_dry_run_agent_does_not_create -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/compshare_cli/cli.py tests/test_cli_rental_loop.py
git commit -m "feat: add agent output for instances"
```

## Task 6: Agent Error Shapes And Clean JSON Stdout

**Files:**
- Modify: `src/compshare_cli/errors.py`
- Modify: `src/compshare_cli/cli.py`
- Test: `tests/test_cli_rental_loop.py`
- Test: `tests/test_cli_doctor.py`

- [ ] **Step 1: Write failing error-output tests**

Append to `tests/test_cli_rental_loop.py`:

```python
def test_missing_credentials_agent_error_is_parseable(monkeypatch):
    monkeypatch.setattr(cli, "load_credentials", lambda: None)

    result = runner.invoke(cli.app, ["resource", "zones", "--agent"])

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["cost_risk"] == "none"
    assert result.stderr == ""


def test_json_error_has_hint(monkeypatch):
    monkeypatch.setattr(cli, "load_credentials", lambda: None)

    result = runner.invoke(cli.app, ["resource", "zones", "--json"])

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["error"]["type"] == "MissingCredentials"
    assert "hint" in payload["error"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli_rental_loop.py::test_missing_credentials_agent_error_is_parseable tests/test_cli_rental_loop.py::test_json_error_has_hint -v`

Expected: FAIL because errors do not yet support agent output or hints.

- [ ] **Step 3: Add hint support and agent error helper**

Modify `CliError` in `src/compshare_cli/errors.py`:

```python
class CliError(Exception):
    def __init__(self, message: str, *, type_name: str = "CliError", ret_code: int | None = None, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.type_name = type_name
        self.ret_code = ret_code
        self.hint = hint

    def to_json(self) -> dict[str, object]:
        error: dict[str, object] = {"type": self.type_name, "message": self.message}
        if self.ret_code is not None:
            error["ret_code"] = self.ret_code
        if self.hint:
            error["hint"] = self.hint
        return {"error": error}
```

In `get_client`, construct missing credentials with a hint:

```python
raise CliError(
    MISSING_CREDENTIALS_MESSAGE,
    type_name="MissingCredentials",
    hint="Set COMPSHARE_PUBLIC_KEY/COMPSHARE_PRIVATE_KEY or run compshare config set public-key/private-key.",
)
```

Add helper in `src/compshare_cli/cli.py`:

```python
def handle_cli_error(error: CliError, json_output: bool, agent_output: bool = False, command: str = "command") -> None:
    if agent_output:
        print_json(agent_envelope(
            ok=False,
            command=command,
            summary=error.message.splitlines()[0],
            warnings=[error.message.splitlines()[0]],
            next_actions=[error.hint] if error.hint else [],
            commands=[
                command_suggestion("Set public key", "compshare config set public-key <PUBLIC_KEY>", "sensitive", True),
                command_suggestion("Set private key", "compshare config set private-key <PRIVATE_KEY>", "sensitive", True),
            ] if error.type_name == "MissingCredentials" else [],
            cost_risk="none",
        ))
    elif json_output:
        print_json(error.to_json())
    else:
        typer.echo(error.message, err=True)
    raise typer.Exit(1)
```

Update command except blocks incrementally so `--agent` paths pass `agent_output=True` and a stable command name.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli_rental_loop.py::test_missing_credentials_agent_error_is_parseable tests/test_cli_rental_loop.py::test_json_error_has_hint -v`

Expected: PASS.

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/compshare_cli/errors.py src/compshare_cli/cli.py tests/test_cli_rental_loop.py tests/test_cli_doctor.py
git commit -m "feat: standardize structured errors"
```

## Task 7: README And Companion Skill

**Files:**
- Modify: `README.md`
- Create: `.agents/skills/compshare-cli/SKILL.md`

- [ ] **Step 1: Update README**

Append to `README.md`:

```markdown
## Agent Mode

Future code agents should start with:

```bash
compshare doctor --agent
```

Output modes:

- Default: human-readable summaries and tables.
- `--json`: pure machine-readable JSON for scripts and `jq`.
- `--agent`: stable decision envelope for code agents.
- `--agent --debug`: adds redacted diagnostics in the `debug` field.

Agent safety rules:

- Commands marked `safe` or `read-only` may be run to gather context.
- Commands marked `cost-incurring`, `destructive`, or `sensitive` require explicit user approval before execution.
- Prefer `instance create --dry-run --agent` before live creation.
- Never print full credentials.

Typical agent flow:

```bash
compshare doctor --agent
compshare instance list --agent
compshare resource zones --agent
compshare price create --zone cn-sh2-02 --image-id compshareImage-xxx --gpu-type 4090 --gpu 1 --cpu 16 --memory 64 --disk-size 200 --agent
compshare instance create --zone cn-sh2-02 --image-id compshareImage-xxx --gpu-type 4090 --gpu 1 --cpu 16 --memory 64 --disk-size 200 --dry-run --agent
```
```

- [ ] **Step 2: Create companion skill**

Create `.agents/skills/compshare-cli/SKILL.md`:

```markdown
# CompShare CLI

Use when the user asks an agent to inspect, start, stop, price, or create CompShare GPU instances.

## First Command

Run:

```bash
compshare doctor --agent
```

If the command is unavailable, ask the user to install this repo's CLI with `uv tool install .`.

## Safety Rules

- Prefer `--agent` for planning and `--json` for field extraction.
- Do not run commands marked `cost-incurring`, `destructive`, or `sensitive` unless the user explicitly approves that exact action.
- Always run price, capacity, and dry-run checks before live instance creation.
- Never print full credentials.

## Common Read Path

```bash
compshare doctor --agent
compshare instance list --agent
compshare resource zones --agent
compshare resource images --type platform --agent
```

## New Instance Path

```bash
compshare price create --zone cn-sh2-02 --image-id <IMAGE_ID> --gpu-type 4090 --gpu 1 --cpu 16 --memory 64 --disk-size 200 --agent
compshare resource capacity --zone cn-sh2-02 --image-id <IMAGE_ID> --gpu-type 4090 --gpu 1 --cpu 16 --memory 64 --disk-size 200 --agent
compshare instance create --zone cn-sh2-02 --image-id <IMAGE_ID> --gpu-type 4090 --gpu 1 --cpu 16 --memory 64 --disk-size 200 --dry-run --agent
```

Only after explicit approval, run live create without `--dry-run`.
```

- [ ] **Step 3: Commit docs**

```bash
git add README.md .agents/skills/compshare-cli/SKILL.md
git commit -m "docs: document agent CLI workflow"
```

## Task 8: Final Verification And Live Read Smoke Tests

**Files:**
- No code changes expected.

- [ ] **Step 1: Run full tests**

Run: `uv run pytest -v`

Expected: all tests pass.

- [ ] **Step 2: Verify structured output parsing locally**

Run:

```bash
uv run compshare doctor --agent > /tmp/compshare-doctor-agent.json || true
python -m json.tool /tmp/compshare-doctor-agent.json >/dev/null
uv run compshare resource zones --json > /tmp/compshare-zones.json
python -m json.tool /tmp/compshare-zones.json >/dev/null
```

Expected: both `python -m json.tool` commands exit 0. `doctor` may exit nonzero if credentials are missing, but its stdout must still parse.

- [ ] **Step 3: Verify help commands**

Run:

```bash
uv run compshare --help
uv run compshare doctor --help
uv run compshare instance create --help
```

Expected: each command exits 0 and shows `--json`, `--agent`, and where applicable `--debug`.

- [ ] **Step 4: Optional live read-only smoke tests**

Only run when credentials are configured:

```bash
uv run compshare doctor --agent
uv run compshare resource zones --agent
uv run compshare price create --zone cn-sh2-02 --image-id compshareImage-1minbz219ceq --gpu-type 4090 --gpu 1 --cpu 16 --memory 64 --disk-size 200 --agent
uv run compshare instance create --zone cn-sh2-02 --image-id compshareImage-1minbz219ceq --gpu-type 4090 --gpu 1 --cpu 16 --memory 64 --disk-size 200 --name cli-dry-run --dry-run --agent
```

Expected: all stdout payloads parse as JSON; no live instance is created.

- [ ] **Step 5: Final status**

Run: `git status --short`

Expected: no unstaged implementation changes. Existing unrelated tool config files may remain untracked if they were already outside this plan.
