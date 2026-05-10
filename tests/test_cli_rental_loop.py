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
            return {"RetCode": 0, "UHostSet": [{"UHostId": "uhost-1", "Name": "gpu"}]}
        if action == "GetCompShareInstancePrice":
            return {"RetCode": 0, "Price": 12.3}
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
    assert fake.calls[-1] == (action, {"UHostId": "uhost-1"})


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
