import json

import pytest
from typer.testing import CliRunner
from compshare_cli import cli
from compshare_cli.config import Credentials
from compshare_cli.errors import CliError


runner = CliRunner()


class FakeCompShareClient:
    def __init__(self, fail_action=None):
        self.calls = []
        self.fail_action = fail_action

    def support_zones(self):
        self.calls.append(("DescribeCompShareSupportZone", {}))
        return [
            {"Region": "cn-wlcb", "Zone": "cn-wlcb-01", "Describe": "华北二A"},
            {"Region": "cn-sh2", "Zone": "cn-sh2-02", "Describe": "上海二"},
        ]

    def invoke(self, action, payload):
        self.calls.append((action, payload))
        if action == self.fail_action:
            raise CliError("boom")
        if action == "CreateCompShareInstance":
            return {"RetCode": 0, "UHostIds": ["uhost-1"]}
        if action == "DescribeCompShareInstance":
            return {"RetCode": 0, "UHostSet": [{"UHostId": "uhost-1", "Name": "gpu", "State": "Stopped", "Zone": "cn-sh2-02"}]}
        if action == "GetCompShareInstancePrice":
            return {"RetCode": 0, "Price": 12.3}
        if action == "CreateCompShareCustomImage":
            return {"RetCode": 0, "CompShareImageId": "compshareImage-custom-1"}
        if action == "DescribeCompShareCustomImages":
            return {
                "RetCode": 0,
                "ImageSet": [
                    {
                        "CompShareImageId": "compshareImage-custom-1",
                        "Name": "my-env",
                        "Status": "Available",
                        "ImageType": "Custom",
                        "Size": 5120,
                    }
                ],
            }
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
        return {"RetCode": 0}


def install_fake_client(monkeypatch):
    fake = FakeCompShareClient()
    monkeypatch.setattr(cli, "load_credentials", lambda: Credentials("public", "private"))
    monkeypatch.setattr(cli, "CompShareClient", lambda credentials: fake)
    return fake


def install_specific_fake_client(monkeypatch, fake):
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
            "--yes",
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


def test_price_create_calls_price_api(monkeypatch):
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
        ],
    )

    assert result.exit_code == 0
    assert "Price" in result.stdout
    assert fake.calls[-1][0] == "GetCompShareInstancePrice"


def test_fake_client_supports_planned_api_actions():
    fake = FakeCompShareClient()

    response = fake.invoke("CreateCompShareCustomImage", {})
    assert response["RetCode"] == 0
    assert response["CompShareImageId"] == "compshareImage-custom-1"

    response = fake.invoke("DescribeCompShareCustomImages", {})
    assert response["RetCode"] == 0
    assert "ImageSet" in response
    assert response["ImageSet"][0]["CompShareImageId"] == "compshareImage-custom-1"
    assert response["ImageSet"][0]["ImageType"] == "Custom"

    response = fake.invoke("GetCompShareImageCreateProgress", {})
    assert response["RetCode"] == 0
    assert response["Process"] == 100.0
    assert response["TotalDuration"] == "3600"
    assert response["RemainingDuration"] == "0"

    response = fake.invoke("AttachCompShareDisk", {})
    assert response["RetCode"] == 0
    assert response["UDiskId"] == "udisk-1"

    response = fake.invoke("DescribeCompShareGpuInventory", {})
    assert response["RetCode"] == 0
    assert "InventorySet" in response
    assert response["InventorySet"][0]["MachineType"] == "4090"
    assert response["InventorySet"][0]["Zone"] == "cn-sh2-02"
    assert response["InventorySet"][0]["Count"] == 3

    for action in [
        "TerminateCompShareCustomImage",
        "ModifyCompShareInstanceName",
        "ReinstallCompShareInstance",
        "ResizeCompShareInstance",
        "UpdateCompShareStopScheduler",
        "AttachUS3",
        "DetachCompShareDisk",
        "ResizeCompShareDisk",
        "DeleteCompShareDisk",
    ]:
        response = fake.invoke(action, {})
        assert response["RetCode"] == 0


def test_instance_list_renders_instance(monkeypatch):
    install_fake_client(monkeypatch)

    result = runner.invoke(cli.app, ["instance", "list"])

    assert result.exit_code == 0
    assert "uhost-1" in result.stdout


@pytest.mark.parametrize(
    ("command", "action"),
    [
        ("start", "StartCompShareInstance"),
        ("stop", "StopCompShareInstance"),
        ("reboot", "RebootCompShareInstance"),
    ],
)
def test_instance_lifecycle_actions(monkeypatch, command, action):
    fake = install_fake_client(monkeypatch)

    result = runner.invoke(cli.app, ["instance", command, "uhost-1"])

    assert result.exit_code == 0
    assert fake.calls[-1][0] == action
    assert fake.calls[-1][1]["UHostId"] == "uhost-1"
    assert "Region" in fake.calls[-1][1]
    assert "Zone" in fake.calls[-1][1]
    assert fake.calls[0][0] == "DescribeCompShareInstance"


@pytest.mark.parametrize(
    ("command", "action"),
    [
        ("start", "StartCompShareInstance"),
        ("stop", "StopCompShareInstance"),
        ("reboot", "RebootCompShareInstance"),
    ],
)
def test_instance_lifecycle_with_explicit_zone_skips_lookup(monkeypatch, command, action):
    fake = install_fake_client(monkeypatch)

    result = runner.invoke(cli.app, ["instance", command, "uhost-1", "--zone", "cn-sh2-02"])

    assert result.exit_code == 0
    assert fake.calls[-1][0] == action
    assert fake.calls[-1][1]["UHostId"] == "uhost-1"
    assert fake.calls[-1][1]["Zone"] == "cn-sh2-02"
    assert fake.calls[-1][1]["Region"] == "cn-sh2"
    assert all(call[0] != "DescribeCompShareInstance" for call in fake.calls)


def test_invalid_zone_exits_cleanly(monkeypatch):
    install_fake_client(monkeypatch)

    result = runner.invoke(
        cli.app,
        [
            "instance",
            "create",
            "--zone",
            "cn-foo-01",
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

    assert result.exit_code != 0
    assert "Unknown zone" in result.stderr
    assert "Traceback" not in result.stderr


def test_missing_credentials_exits_cleanly(monkeypatch):
    monkeypatch.setattr(cli, "load_credentials", lambda: None)

    result = runner.invoke(cli.app, ["resource", "zones"])

    assert result.exit_code != 0
    assert "Missing credentials" in result.stderr
    assert "Traceback" not in result.stderr


def test_resource_wrapper_api_failure_exits_cleanly(monkeypatch):
    install_specific_fake_client(monkeypatch, FakeCompShareClient(fail_action="DescribeCompShareMachineTypeFamilies"))

    result = runner.invoke(cli.app, ["resource", "machine-families"])

    assert result.exit_code != 0
    assert "boom" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    ("args", "action"),
    [
        (["resource", "machine-families"], "DescribeCompShareMachineTypeFamilies"),
        (["resource", "instance-types", "--zone", "cn-sh2-02", "--gpu-type", "4090"], "DescribeAvailableCompShareInstanceTypes"),
        (["resource", "images", "--type", "platform"], "DescribeCompShareImages"),
        (["resource", "images", "--type", "community"], "DescribeCommunityImages"),
    ],
)
def test_resource_wrappers_call_expected_actions(monkeypatch, args, action):
    fake = install_fake_client(monkeypatch)

    result = runner.invoke(cli.app, args)

    assert result.exit_code == 0
    assert '"RetCode": 0' in result.stdout
    assert fake.calls[-1][0] == action


def test_instance_types_resolves_region_and_filters_machine_types(monkeypatch):
    fake = install_fake_client(monkeypatch)

    result = runner.invoke(cli.app, ["resource", "instance-types", "--zone", "cn-sh2-02", "--gpu-type", "4090"])

    assert result.exit_code == 0
    assert fake.calls[-1] == (
        "DescribeAvailableCompShareInstanceTypes",
        {"Region": "cn-sh2", "Zone": "cn-sh2-02", "MachineTypes": ["4090"]},
    )


def test_resource_capacity_calls_capacity_api(monkeypatch):
    fake = install_fake_client(monkeypatch)

    result = runner.invoke(
        cli.app,
        [
            "resource",
            "capacity",
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
    assert '"RetCode": 0' in result.stdout
    assert fake.calls[-1][0] == "CheckCompShareResourceCapacity"


def test_create_command_from_payload_quotes_spaced_values():
    from compshare_cli.cli import create_command_from_payload

    options = {
        "zone": "cn-sh2-02",
        "image-id": "my test image",
        "gpu-type": "4090",
        "gpu": 1,
        "cpu": 16,
        "memory": 64,
        "disk-size": 200,
    }
    cmd = create_command_from_payload("instance create", options)
    # Should quote the value with spaces
    assert "--image-id 'my test image'" in cmd or '--image-id "my test image"' in cmd
    assert "my test image" in cmd
    # Ensure no unquoted space in the middle
    assert "my test image" not in cmd or cmd.count("my test image") == 1  # simple presence check
    # Actually check that the command can be split safely
    import shlex
    parts = shlex.split(cmd)
    # Verify that --image-id is followed by the quoted value as a single token
    idx = parts.index("--image-id") if "--image-id" in parts else -1
    assert idx != -1
    assert parts[idx + 1] == "my test image"


def test_resource_zones_agent_output(monkeypatch):
    install_fake_client(monkeypatch)

    result = runner.invoke(cli.app, ["resource", "zones", "--agent"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["command"] == "resource_zones"
    assert "zones" in data["data"]
    assert len(data["data"]["zones"]) == 2
    assert data["data"]["zones"][0]["region"] == "cn-wlcb"
    assert "commands" in data
    assert any(c["label"] == "List available zones" for c in data["commands"])


def test_price_create_agent_output_includes_cost_command(monkeypatch):
    install_fake_client(monkeypatch)

    result = runner.invoke(
        cli.app,
        [
            "price",
            "create",
            "--agent",
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
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["command"] == "price_create"
    assert data["cost_risk"] == "may-incur-cost"
    commands = data["commands"]
    assert any(c["label"] == "Check capacity" for c in commands)
    assert any(c["label"] == "Dry-run instance creation" for c in commands)
    assert any(c["label"] == "Create instance" for c in commands)
    for cmd in commands:
        assert "{" not in cmd["command"]
        assert "}" not in cmd["command"]


def test_instance_list_agent_suggests_actions(monkeypatch):
    install_fake_client(monkeypatch)

    result = runner.invoke(cli.app, ["instance", "list", "--agent"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "instance_list"
    assert payload["data"]["instances"][0]["id"] == "uhost-1"
    assert any(cmd["label"] == "Start uhost-1" for cmd in payload["commands"])


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
    assert payload["command"] == "instance_create"
    assert payload["data"]["dry_run"] is True
    assert fake.calls[-1][0] == "DescribeCompShareSupportZone"
    assert all(call[0] != "CreateCompShareInstance" for call in fake.calls)


def test_instance_create_live_agent_outputs_created_ids(monkeypatch):
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
            "--agent",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "instance_create"
    assert payload["cost_risk"] == "cost-incurring"
    assert "instance_ids" in payload["data"]
    assert payload["data"]["instance_ids"] == ["uhost-1"]
    assert any(call[0] == "CreateCompShareInstance" for call in fake.calls)


def test_instance_create_live_agent_requires_yes(monkeypatch):
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
            "--agent",
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["cost_risk"] == "cost-incurring"
    assert "--yes" in payload["summary"]
    assert all(call[0] != "CreateCompShareInstance" for call in fake.calls)


def test_instance_show_agent_outputs_detail_and_command(monkeypatch):
    fake = install_fake_client(monkeypatch)

    result = runner.invoke(cli.app, ["instance", "show", "uhost-1", "--agent"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "instance_show"
    assert payload["data"]["instance"]["id"] == "uhost-1"
    assert payload["data"]["instance"]["state"] == "Stopped"
    # Should have at least one safe follow-up command
    assert len(payload.get("commands", [])) >= 1
    assert any(cmd["risk"] == "safe" for cmd in payload["commands"])


@pytest.mark.parametrize(
    ("cmd", "action", "expected_risk"),
    [
        ("start", "StartCompShareInstance", "cost-incurring"),
        ("stop", "StopCompShareInstance", "may-incur-cost"),
        ("reboot", "RebootCompShareInstance", "may-incur-cost"),
        ("delete", "TerminateCompShareInstance", "destructive"),
    ],
)
def test_instance_lifecycle_agent_outputs(monkeypatch, cmd, action, expected_risk):
    fake = install_fake_client(monkeypatch)

    args = ["instance", cmd, "uhost-1", "--agent"]
    if cmd == "delete":
        args.append("--yes")
    if cmd == "start":
        args.append("--without-gpu")

    result = runner.invoke(cli.app, args)

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == cmd
    assert payload["cost_risk"] == expected_risk
    assert payload["data"]["instance_id"] == "uhost-1"
    assert any(call[0] == action for call in fake.calls)
    matching_call = next(call for call in fake.calls if call[0] == action)
    assert matching_call[1]["UHostId"] == "uhost-1"
    assert "Region" in matching_call[1]
    assert "Zone" in matching_call[1]
    if cmd == "start":
        assert matching_call[1].get("WithoutGpu") is True
    # Should have a follow-up command (Show instance)
    assert len(payload.get("commands", [])) >= 1
    assert any(cmd_sug["label"] == f"Show instance" for cmd_sug in payload["commands"])


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
