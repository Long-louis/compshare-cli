# CLI Feature Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add image management, instance operations, disk management, and GPU inventory commands to compshare-cli.

**Architecture:** New Typer sub-apps (image_app, disk_app) in cli.py, expanded instance_app/resource_app commands, new request builders in requests.py. All commands follow existing --json/--agent output patterns and FakeCompShareClient testing.

**Tech Stack:** Python 3.11, typer, ucloud-sdk-python3, pytest

---

### Task 1: Extend FakeCompShareClient for new API actions

**Files:**
- Modify: `tests/test_cli_rental_loop.py:13-35` (FakeCompShareClient class)

- [ ] **Step 1: Add new API handlers to FakeCompShareClient.invoke()**

Add these action handlers inside the existing `invoke()` method, after the existing handlers:

```python
        if action == "CreateCompShareCustomImage":
            return {"RetCode": 0, "CompShareImageId": "compshareImage-custom-1"}
        if action == "DescribeCompShareCustomImages":
            return {"RetCode": 0, "ImageSet": [{"CompShareImageId": "compshareImage-custom-1", "Name": "my-env", "Status": "Available", "ImageType": "Custom", "Size": 5120}]}
        if action == "GetCompShareImageCreateProgress":
            return {"RetCode": 0, "Process": 100.0, "TotalDuration": "3600", "RemainingDuration": "0"}
        if action == "TerminateCompShareCustomImage":
            return {"RetCode": 0}
        if action == "ModifyCompShareInstanceName":
            return {"RetCode": 0}
        if action == "ReinstallCompShareInstance":
            return {"RetCode": 0}
        if action == "ResizeCompShareInstance":
            return {"RetCode": 0}
        if action == "UpdateCompShareStopScheduler":
            return {"RetCode": 0}
        if action == "AttachUS3":
            return {"RetCode": 0}
        if action == "AttachCompShareDisk":
            return {"RetCode": 0, "UDiskId": "udisk-1"}
        if action == "DetachCompShareDisk":
            return {"RetCode": 0}
        if action == "ResizeCompShareDisk":
            return {"RetCode": 0}
        if action == "DeleteCompShareDisk":
            return {"RetCode": 0}
        if action == "DescribeCompShareGpuInventory":
            return {"RetCode": 0, "InventorySet": [{"MachineType": "4090", "Zone": "cn-sh2-02", "Count": 3}]}
```

- [ ] **Step 2: Run tests to verify no regressions**

```bash
uv run pytest -v
```
Expected: All 69 tests pass (no new tests yet, existing tests unchanged)

- [ ] **Step 3: Commit**

```bash
git add tests/test_cli_rental_loop.py
git commit -m "test: extend FakeCompShareClient for new API actions"
```

### Task 2: Add resource images --type custom and gpu-inventory

**Files:**
- Modify: `src/compshare_cli/cli.py` (resource_images function, add resource_gpu_inventory)
- Test: `tests/test_cli_rental_loop.py` (add tests for new resource commands)

- [ ] **Step 1: Extend resource_images to support --type custom**

Change the `resource_images` function in `cli.py`:

```python
@resource_app.command("images")
def resource_images(
    image_type: Annotated[str, typer.Option("--type")] = "platform",
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
) -> None:
    action_map = {
        "platform": "DescribeCompShareImages",
        "community": "DescribeCommunityImages",
        "custom": "DescribeCompShareCustomImages",
    }
    if image_type not in action_map:
        typer.echo(f"Invalid type: {image_type}. Must be one of: {', '.join(action_map)}", err=True)
        raise typer.Exit(1)
    action = action_map[image_type]
    try:
        response = get_client().invoke(action, {})
    except CliError as e:
        handle_cli_error(e, json_output)
    else:
        print_response(response, json_output)
```

- [ ] **Step 2: Add resource_gpu_inventory command**

Add after `resource_capacity` in `cli.py`:

```python
@resource_app.command("gpu-inventory")
def resource_gpu_inventory(
    zone: Annotated[str | None, typer.Option("--zone")] = None,
    gpu_type: Annotated[str | None, typer.Option("--gpu-type")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
) -> None:
    try:
        client = get_client()
        zones_info = client.support_zones()
        if zone:
            resolved_region, resolved_zone = resolve_zone_region(zone, None, zones_info)
        else:
            resolved_region, resolved_zone = resolve_zone_region(zones_info[0]["Zone"], None, zones_info)
        payload: dict = {"Region": resolved_region, "Zone": resolved_zone}
        if gpu_type:
            payload["MachineTypes"] = [gpu_type]
        response = client.invoke("DescribeCompShareGpuInventory", payload)
    except (CliError, ValueError) as error:
        handle_cli_error(error if isinstance(error, CliError) else CliError(str(error)), json_output)
    else:
        if json_output:
            print_json(response)
            return
        rows = [[item.get("MachineType", ""), item.get("Zone", ""), item.get("Count", 0)] for item in response.get("InventorySet", [])]
        print_table(["GPU TYPE", "ZONE", "COUNT"], rows)
```

- [ ] **Step 3: Add tests in test_cli_rental_loop.py**

Add after existing resource tests:

```python
def test_resource_images_custom_type(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["resource", "images", "--type", "custom"])
    assert result.exit_code == 0
    assert fake.calls[-1][0] == "DescribeCompShareCustomImages"


def test_resource_gpu_inventory(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["resource", "gpu-inventory"])
    assert result.exit_code == 0
    assert fake.calls[-1][0] == "DescribeCompShareGpuInventory"
    assert fake.calls[-1][1]["Region"] == "cn-wlcb"
    assert fake.calls[-1][1]["Zone"] == "cn-wlcb-01"
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_cli_rental_loop.py::test_resource_images_custom_type tests/test_cli_rental_loop.py::test_resource_gpu_inventory -v
```
Expected: 2 new tests pass, existing tests unchanged

- [ ] **Step 5: Commit**

```bash
git add src/compshare_cli/cli.py tests/test_cli_rental_loop.py
git commit -m "feat: add resource images --type custom and gpu-inventory"
```

### Task 3: Add image command group

**Files:**
- Modify: `src/compshare_cli/cli.py` (add image_app, register with app, add 4 commands)
- Modify: `src/compshare_cli/cli.py` (add _normalize_images helper)
- Test: `tests/test_cli_image.py` (new file)

- [ ] **Step 1: Add image_app and register with app**

At the top of `cli.py` after existing app definitions:

```python
image_app = typer.Typer(help="Manage CompShare custom images.", no_args_is_help=True)
app.add_typer(image_app, name="image")
```

- [ ] **Step 2: Add image create command**

```python
@image_app.command("create")
def image_create(
    instance_id: Annotated[str, typer.Option("--instance-id")],
    name: Annotated[str, typer.Option("--name")],
    description: Annotated[str | None, typer.Option("--description")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        client = get_client()
        region, resolved_zone = _resolve_instance_zone(instance_id, client)
        payload: dict = {"Region": region, "Zone": resolved_zone, "UHostId": instance_id, "Name": name}
        if description:
            payload["Description"] = description
        response = client.invoke("CreateCompShareCustomImage", payload)
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
        return
    if agent_output:
        envelope = agent_envelope(
            "image_create",
            f"Started creating image: {response.get('CompShareImageId', '')}",
            {"image_id": response.get("CompShareImageId", "")},
            "may-incur-cost",
            ok=True,
            commands=[command_suggestion("Check progress", f"compshare image show-progress --image-id {response.get('CompShareImageId', '')} --agent", "read-only", False)],
        )
        print_json(envelope)
        return
    print_json(response) if json_output else typer.echo(f"Image creation started: {response.get('CompShareImageId', '')}")
```

- [ ] **Step 3: Add image list command**

```python
@image_app.command("list")
def image_list(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        response = get_client().invoke("DescribeCompShareCustomImages", {})
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
        return
    images = response.get("ImageSet", [])
    if agent_output:
        envelope = agent_envelope(
            "image_list",
            f"Found {len(images)} custom images.",
            {"images": [{"id": img.get("CompShareImageId"), "name": img.get("Name"), "status": img.get("Status")} for img in images]},
            "read-only",
            ok=True,
        )
        print_json(envelope)
        return
    if json_output:
        print_json(response)
        return
    rows = [[img.get("CompShareImageId", ""), img.get("Name", ""), img.get("Status", ""), img.get("Size", 0)] for img in images]
    print_table(["ID", "NAME", "STATUS", "SIZE(MB)"], rows)
```

- [ ] **Step 4: Add image show-progress command**

```python
@image_app.command("show-progress")
def image_show_progress(
    image_id: Annotated[str, typer.Option("--image-id")],
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        response = get_client().invoke("GetCompShareImageCreateProgress", {"CompShareImageId": image_id})
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
        return
    if agent_output:
        envelope = agent_envelope(
            "image_progress",
            f"Image {image_id} progress: {response.get('Process', 0):.1f}%",
            {"image_id": image_id, "process": response.get("Process", 0)},
            "read-only",
            ok=True,
        )
        print_json(envelope)
        return
    print_json(response) if json_output else typer.echo(f"Progress: {response.get('Process', 0):.1f}%")
```

- [ ] **Step 5: Add image delete command**

```python
@image_app.command("delete")
def image_delete(
    image_id: Annotated[str, typer.Option("--image-id")],
    yes: Annotated[bool, typer.Option("--yes", help="Confirm deletion.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    if not yes:
        typer.echo("image delete requires --yes")
        raise typer.Exit(1)
    try:
        response = get_client().invoke("TerminateCompShareCustomImage", {"CompShareImageId": image_id})
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
        return
    if agent_output:
        envelope = agent_envelope(
            "image_delete",
            f"Deleted image: {image_id}",
            {"image_id": image_id},
            "may-incur-cost",
            ok=True,
        )
        print_json(envelope)
        return
    print_json(response) if json_output else typer.echo("OK")
```

- [ ] **Step 6: Add test file tests/test_cli_image.py**

```python
import json
import pytest
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
        if action == "DescribeCompShareInstance":
            return {"RetCode": 0, "UHostSet": [{"UHostId": "uhost-1", "Name": "gpu", "State": "Stopped", "Zone": "cn-sh2-02"}]}
        if action == "CreateCompShareCustomImage":
            return {"RetCode": 0, "CompShareImageId": "compshareImage-custom-1"}
        if action == "DescribeCompShareCustomImages":
            return {"RetCode": 0, "ImageSet": [{"CompShareImageId": "compshareImage-custom-1", "Name": "my-env", "Status": "Available", "Size": 5120}]}
        if action == "GetCompShareImageCreateProgress":
            return {"RetCode": 0, "Process": 100.0, "TotalDuration": "3600", "RemainingDuration": "0"}
        if action == "TerminateCompShareCustomImage":
            return {"RetCode": 0}
        return {"RetCode": 0}


def install_fake_client(monkeypatch):
    fake = FakeCompShareClient()
    monkeypatch.setattr(cli, "load_credentials", lambda: Credentials("public", "private"))
    monkeypatch.setattr(cli, "CompShareClient", lambda credentials: fake)
    return fake


def test_image_create(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["image", "create", "--instance-id", "uhost-1", "--name", "my-env"])
    assert result.exit_code == 0
    assert fake.calls[-1][0] == "CreateCompShareCustomImage"
    assert fake.calls[-1][1]["Name"] == "my-env"


def test_image_list(monkeypatch):
    install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["image", "list"])
    assert result.exit_code == 0
    assert "compshareImage-custom-1" in result.stdout


def test_image_show_progress(monkeypatch):
    install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["image", "show-progress", "--image-id", "compshareImage-custom-1"])
    assert result.exit_code == 0
    assert "100.0%" in result.stdout


def test_image_delete_requires_yes(monkeypatch):
    install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["image", "delete", "--image-id", "compshareImage-custom-1"])
    assert result.exit_code != 0
    assert "--yes" in result.stdout


def test_image_delete_with_yes(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["image", "delete", "--image-id", "compshareImage-custom-1", "--yes"])
    assert result.exit_code == 0
    assert fake.calls[-1][0] == "TerminateCompShareCustomImage"


def test_image_create_agent(monkeypatch):
    install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["image", "create", "--instance-id", "uhost-1", "--name", "my-env", "--agent"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["cost_risk"] == "may-incur-cost"
```

- [ ] **Step 7: Run image tests**

```bash
uv run pytest tests/test_cli_image.py -v
```
Expected: 6 tests pass

- [ ] **Step 8: Run full suite**

```bash
uv run pytest -v
```
Expected: All tests pass (existing + 6 new)

- [ ] **Step 9: Commit**

```bash
git add src/compshare_cli/cli.py tests/test_cli_image.py
git commit -m "feat: add image command group (create/list/show-progress/delete)"
```

### Task 4: Add instance operations (rename, reinstall, resize, set-stop-scheduler, attach-us3)

**Files:**
- Modify: `src/compshare_cli/cli.py` (add 5 new instance commands)
- Test: `tests/test_cli_rental_loop.py` (add tests for new instance commands)

- [ ] **Step 1: Add instance rename command**

```python
@instance_app.command("rename")
def instance_rename(
    instance_id: str,
    name: Annotated[str, typer.Option("--name")],
    zone: Annotated[str | None, typer.Option("--zone")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        client = get_client()
        if zone:
            region, resolved_zone = resolve_zone_region(zone, None, client.support_zones())
        else:
            region, resolved_zone = _resolve_instance_zone(instance_id, client)
        response = client.invoke("ModifyCompShareInstanceName", {"Region": region, "Zone": resolved_zone, "UHostId": instance_id, "Name": name})
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
        return
    if agent_output:
        envelope = agent_envelope("instance_rename", f"Renamed instance {instance_id} to {name}", {"instance_id": instance_id, "name": name}, "read-only", ok=True)
        print_json(envelope)
        return
    print_json(response) if json_output else typer.echo("OK")
```

- [ ] **Step 2: Add instance reinstall command**

```python
@instance_app.command("reinstall")
def instance_reinstall(
    instance_id: str,
    image_id: Annotated[str, typer.Option("--image-id")],
    zone: Annotated[str | None, typer.Option("--zone")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        client = get_client()
        if zone:
            region, resolved_zone = resolve_zone_region(zone, None, client.support_zones())
        else:
            region, resolved_zone = _resolve_instance_zone(instance_id, client)
        response = client.invoke("ReinstallCompShareInstance", {"Region": region, "Zone": resolved_zone, "UHostId": instance_id, "CompShareImageId": image_id})
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
        return
    if agent_output:
        envelope = agent_envelope(
            "instance_reinstall",
            f"Reinstalling instance {instance_id} with image {image_id}",
            {"instance_id": instance_id, "image_id": image_id},
            "may-incur-cost",
            ok=True,
            commands=[command_suggestion("Show instance", f"compshare instance show {instance_id} --agent", "safe", False)],
        )
        print_json(envelope)
        return
    print_json(response) if json_output else typer.echo("OK")
```

- [ ] **Step 3: Add instance resize command**

```python
@instance_app.command("resize")
def instance_resize(
    instance_id: str,
    cpu: Annotated[int, typer.Option("--cpu")],
    memory: Annotated[int, typer.Option("--memory", help="Memory in GiB.")],
    gpu: Annotated[int | None, typer.Option("--gpu")] = None,
    gpu_type: Annotated[str | None, typer.Option("--gpu-type")] = None,
    zone: Annotated[str | None, typer.Option("--zone")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        client = get_client()
        if zone:
            region, resolved_zone = resolve_zone_region(zone, None, client.support_zones())
        else:
            region, resolved_zone = _resolve_instance_zone(instance_id, client)
        payload: dict = {"Region": region, "Zone": resolved_zone, "UHostId": instance_id, "CPU": cpu, "Memory": memory * 1024}
        if gpu is not None:
            payload["GPU"] = gpu
        if gpu_type:
            payload["GpuType"] = gpu_type
        response = client.invoke("ResizeCompShareInstance", payload)
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
        return
    if agent_output:
        envelope = agent_envelope(
            "instance_resize",
            f"Resizing instance {instance_id} to {cpu}CPU/{memory}GiB",
            {"instance_id": instance_id, "cpu": cpu, "memory_gib": memory},
            "may-incur-cost",
            ok=True,
        )
        print_json(envelope)
        return
    print_json(response) if json_output else typer.echo("OK")
```

- [ ] **Step 4: Add instance set-stop-scheduler command**

```python
@instance_app.command("set-stop-scheduler")
def instance_set_stop_scheduler(
    instance_id: str,
    at: Annotated[str | None, typer.Option("--at", help="Stop at ISO timestamp, e.g. 2026-05-21T23:00:00")] = None,
    after_hours: Annotated[int | None, typer.Option("--after-hours", help="Stop after N hours")] = None,
    zone: Annotated[str | None, typer.Option("--zone")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    if not at and after_hours is None:
        typer.echo("set-stop-scheduler requires --at or --after-hours", err=True)
        raise typer.Exit(1)
    try:
        client = get_client()
        if zone:
            region, resolved_zone = resolve_zone_region(zone, None, client.support_zones())
        else:
            region, resolved_zone = _resolve_instance_zone(instance_id, client)
        stop_time = at if at else str(after_hours)
        response = client.invoke("UpdateCompShareStopScheduler", {"Region": region, "Zone": resolved_zone, "UHostId": instance_id, "StopTime": stop_time})
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
        return
    if agent_output:
        envelope = agent_envelope(
            "instance_set_stop_scheduler",
            f"Set stop scheduler for {instance_id} at {stop_time}",
            {"instance_id": instance_id, "stop_time": stop_time},
            "read-only",
            ok=True,
        )
        print_json(envelope)
        return
    print_json(response) if json_output else typer.echo(f"Stop scheduler set: {stop_time}")
```

- [ ] **Step 5: Add instance attach-us3 command**

```python
@instance_app.command("attach-us3")
def instance_attach_us3(
    instance_id: str,
    zone: Annotated[str | None, typer.Option("--zone")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        client = get_client()
        if zone:
            region, resolved_zone = resolve_zone_region(zone, None, client.support_zones())
        else:
            region, resolved_zone = _resolve_instance_zone(instance_id, client)
        response = client.invoke("AttachUS3", {"Region": region, "Zone": resolved_zone, "UHostId": instance_id})
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
        return
    if agent_output:
        envelope = agent_envelope(
            "instance_attach_us3",
            f"Attached US3 to instance {instance_id}",
            {"instance_id": instance_id},
            "may-incur-cost",
            ok=True,
        )
        print_json(envelope)
        return
    print_json(response) if json_output else typer.echo("OK")
```

- [ ] **Step 6: Add tests in test_cli_rental_loop.py**

Add after existing instance lifecycle tests:

```python
def test_instance_rename(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["instance", "rename", "uhost-1", "--name", "new-name"])
    assert result.exit_code == 0
    assert fake.calls[-1][0] == "ModifyCompShareInstanceName"
    assert fake.calls[-1][1]["Name"] == "new-name"


def test_instance_reinstall(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["instance", "reinstall", "uhost-1", "--image-id", "compshareImage-xxx"])
    assert result.exit_code == 0
    assert fake.calls[-1][0] == "ReinstallCompShareInstance"
    assert fake.calls[-1][1]["CompShareImageId"] == "compshareImage-xxx"


def test_instance_resize(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["instance", "resize", "uhost-1", "--cpu", "32", "--memory", "128"])
    assert result.exit_code == 0
    assert fake.calls[-1][0] == "ResizeCompShareInstance"
    assert fake.calls[-1][1]["CPU"] == 32
    assert fake.calls[-1][1]["Memory"] == 131072


def test_instance_set_stop_scheduler_requires_time(monkeypatch):
    install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["instance", "set-stop-scheduler", "uhost-1"])
    assert result.exit_code != 0
    assert "--at" in result.stdout or "--after-hours" in result.stdout


def test_instance_set_stop_scheduler(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["instance", "set-stop-scheduler", "uhost-1", "--after-hours", "2"])
    assert result.exit_code == 0
    assert fake.calls[-1][0] == "UpdateCompShareStopScheduler"


def test_instance_attach_us3(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["instance", "attach-us3", "uhost-1"])
    assert result.exit_code == 0
    assert fake.calls[-1][0] == "AttachUS3"
```

- [ ] **Step 7: Run tests**

```bash
uv run pytest -v
```
Expected: All tests pass (existing + 6 new instance tests + 6 image tests)

- [ ] **Step 8: Commit**

```bash
git add src/compshare_cli/cli.py tests/test_cli_rental_loop.py
git commit -m "feat: add instance operations (rename, reinstall, resize, set-stop-scheduler, attach-us3)"
```

### Task 5: Add disk command group

**Files:**
- Modify: `src/compshare_cli/cli.py` (add disk_app, register with app, add 4 commands)
- Test: `tests/test_cli_disk.py` (new file)

- [ ] **Step 1: Add disk_app and register with app**

At the top of `cli.py` after image_app:

```python
disk_app = typer.Typer(help="Manage CompShare data disks.", no_args_is_help=True)
app.add_typer(disk_app, name="disk")
```

- [ ] **Step 2: Add disk attach command**

```python
@disk_app.command("attach")
def disk_attach(
    instance_id: Annotated[str, typer.Option("--instance-id")],
    size: Annotated[int, typer.Option("--size", help="Disk size in GiB.")],
    zone: Annotated[str | None, typer.Option("--zone")] = None,
    disk_type: Annotated[str, typer.Option("--type")] = "CLOUD_SSD",
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        client = get_client()
        if zone:
            region, resolved_zone = resolve_zone_region(zone, None, client.support_zones())
        else:
            region, resolved_zone = _resolve_instance_zone(instance_id, client)
        payload: dict = {"Region": region, "Zone": resolved_zone, "UHostId": instance_id, "Size": size, "Type": disk_type}
        response = client.invoke("AttachCompShareDisk", payload)
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
        return
    if agent_output:
        envelope = agent_envelope(
            "disk_attach",
            f"Attached {size}GiB disk to instance {instance_id}",
            {"instance_id": instance_id, "size_gib": size, "disk_id": response.get("UDiskId", "")},
            "may-incur-cost",
            ok=True,
        )
        print_json(envelope)
        return
    print_json(response) if json_output else typer.echo(f"Disk attached: {response.get('UDiskId', '')}")
```

- [ ] **Step 3: Add disk detach command**

```python
@disk_app.command("detach")
def disk_detach(
    disk_id: Annotated[str, typer.Option("--disk-id")],
    instance_id: Annotated[str, typer.Option("--instance-id")],
    zone: Annotated[str | None, typer.Option("--zone")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        client = get_client()
        if zone:
            region, resolved_zone = resolve_zone_region(zone, None, client.support_zones())
        else:
            region, resolved_zone = _resolve_instance_zone(instance_id, client)
        response = client.invoke("DetachCompShareDisk", {"Region": region, "Zone": resolved_zone, "UHostId": instance_id, "UDiskId": disk_id})
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
        return
    if agent_output:
        envelope = agent_envelope(
            "disk_detach",
            f"Detached disk {disk_id} from instance {instance_id}",
            {"disk_id": disk_id, "instance_id": instance_id},
            "may-incur-cost",
            ok=True,
        )
        print_json(envelope)
        return
    print_json(response) if json_output else typer.echo("OK")
```

- [ ] **Step 4: Add disk resize command**

```python
@disk_app.command("resize")
def disk_resize(
    disk_id: Annotated[str, typer.Option("--disk-id")],
    size: Annotated[int, typer.Option("--size", help="New disk size in GiB.")],
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        response = get_client().invoke("ResizeCompShareDisk", {"UDiskId": disk_id, "Size": size})
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
        return
    if agent_output:
        envelope = agent_envelope(
            "disk_resize",
            f"Resized disk {disk_id} to {size}GiB",
            {"disk_id": disk_id, "size_gib": size},
            "may-incur-cost",
            ok=True,
        )
        print_json(envelope)
        return
    print_json(response) if json_output else typer.echo("OK")
```

- [ ] **Step 5: Add disk delete command**

```python
@disk_app.command("delete")
def disk_delete(
    disk_id: Annotated[str, typer.Option("--disk-id")],
    yes: Annotated[bool, typer.Option("--yes", help="Confirm deletion.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    if not yes:
        typer.echo("disk delete requires --yes")
        raise typer.Exit(1)
    try:
        response = get_client().invoke("DeleteCompShareDisk", {"UDiskId": disk_id})
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
        return
    if agent_output:
        envelope = agent_envelope(
            "disk_delete",
            f"Deleted disk: {disk_id}",
            {"disk_id": disk_id},
            "may-incur-cost",
            ok=True,
        )
        print_json(envelope)
        return
    print_json(response) if json_output else typer.echo("OK")
```

- [ ] **Step 6: Add test file tests/test_cli_disk.py**

```python
import json
import pytest
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
        if action == "DescribeCompShareInstance":
            return {"RetCode": 0, "UHostSet": [{"UHostId": "uhost-1", "Name": "gpu", "State": "Stopped", "Zone": "cn-sh2-02"}]}
        if action == "AttachCompShareDisk":
            return {"RetCode": 0, "UDiskId": "udisk-1"}
        if action == "DetachCompShareDisk":
            return {"RetCode": 0}
        if action == "ResizeCompShareDisk":
            return {"RetCode": 0}
        if action == "DeleteCompShareDisk":
            return {"RetCode": 0}
        return {"RetCode": 0}


def install_fake_client(monkeypatch):
    fake = FakeCompShareClient()
    monkeypatch.setattr(cli, "load_credentials", lambda: Credentials("public", "private"))
    monkeypatch.setattr(cli, "CompShareClient", lambda credentials: fake)
    return fake


def test_disk_attach(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["disk", "attach", "--instance-id", "uhost-1", "--size", "100"])
    assert result.exit_code == 0
    assert fake.calls[-1][0] == "AttachCompShareDisk"
    assert fake.calls[-1][1]["Size"] == 100


def test_disk_detach(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["disk", "detach", "--disk-id", "udisk-1", "--instance-id", "uhost-1"])
    assert result.exit_code == 0
    assert fake.calls[-1][0] == "DetachCompShareDisk"


def test_disk_resize(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["disk", "resize", "--disk-id", "udisk-1", "--size", "200"])
    assert result.exit_code == 0
    assert fake.calls[-1][0] == "ResizeCompShareDisk"


def test_disk_delete_requires_yes(monkeypatch):
    install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["disk", "delete", "--disk-id", "udisk-1"])
    assert result.exit_code != 0
    assert "--yes" in result.stdout


def test_disk_delete_with_yes(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["disk", "delete", "--disk-id", "udisk-1", "--yes"])
    assert result.exit_code == 0
    assert fake.calls[-1][0] == "DeleteCompShareDisk"


def test_disk_attach_agent(monkeypatch):
    install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["disk", "attach", "--instance-id", "uhost-1", "--size", "100", "--agent"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["cost_risk"] == "may-incur-cost"
```

- [ ] **Step 7: Run disk tests**

```bash
uv run pytest tests/test_cli_disk.py -v
```
Expected: 6 tests pass

- [ ] **Step 8: Run full suite**

```bash
uv run pytest -v
```
Expected: All tests pass (existing + 6 image + 6 instance + 6 disk = ~87 total)

- [ ] **Step 9: Commit**

```bash
git add src/compshare_cli/cli.py tests/test_cli_disk.py
git commit -m "feat: add disk command group (attach/detach/resize/delete)"
```

### Task 6: Update AGENTS.md and companion skill

**Files:**
- Modify: `AGENTS.md` (update command groups table, add new behaviors)
- Modify: `skills/compshare-cli/SKILL.md` (add new commands)

- [ ] **Step 1: Update AGENTS.md command table**

Replace the existing CLI Command Groups table with:

```markdown
| Group | Commands |
|---|---|
| `config` | `set`, `get`, `unset`, `path` |
| `resource` | `zones`, `instance-types --zone`, `images --type platform\|community\|custom`, `machine-families`, `capacity`, `gpu-inventory` |
| `price` | `create` (same spec as `instance create`) |
| `instance` | `create`, `list`, `show`, `start`, `stop`, `reboot`, `delete`, `rename`, `reinstall`, `resize`, `set-stop-scheduler`, `attach-us3` |
| `image` | `create`, `list`, `show-progress`, `delete` |
| `disk` | `attach`, `detach`, `resize`, `delete` |
| top-level | `doctor` |
```

- [ ] **Step 2: Update Key Behaviors**

Add to the Key Behaviors section:

```markdown
- **`image create/delete`**: `image delete` requires `--yes`. `image create` auto-resolves zone from `--instance-id`.
- **`disk attach/detach`**: `--zone` optional, auto-resolves from `--instance-id` when provided. `disk delete` requires `--yes`.
- **`instance reinstall/resize`**: require instance in Stopped state. `--zone` optional, auto-resolves.
```

- [ ] **Step 3: Run full suite to verify no regressions**

```bash
uv run pytest -v
```
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md skills/compshare-cli/SKILL.md
git commit -m "docs: update AGENTS.md and skill with new commands"
```
