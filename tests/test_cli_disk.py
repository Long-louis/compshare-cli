import json

from typer.testing import CliRunner

from compshare_cli import cli
from compshare_cli.config import Credentials

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
            from compshare_cli.errors import CliError

            raise CliError("boom")
        if action == "DescribeCompShareInstance":
            return {
                "RetCode": 0,
                "UHostSet": [
                    {
                        "UHostId": "uhost-1",
                        "Name": "gpu",
                        "State": "Stopped",
                        "Zone": "cn-sh2-02",
                    }
                ],
            }
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


def test_disk_attach_yes_calls_api(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(
        cli.app,
        [
            "disk",
            "attach",
            "--instance-id",
            "uhost-1",
            "--size",
            "20",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    assert "udisk-1" in result.stdout
    attach_calls = [c for c in fake.calls if c[0] == "AttachCompShareDisk"]
    assert len(attach_calls) == 1
    payload = attach_calls[0][1]
    assert payload["UHostId"] == "uhost-1"
    assert payload["Size"] == 20
    assert payload["Type"] == "CLOUD_SSD"
    assert payload["Region"] == "cn-sh2"
    assert payload["Zone"] == "cn-sh2-02"


def test_disk_attach_missing_yes(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(
        cli.app,
        [
            "disk",
            "attach",
            "--instance-id",
            "uhost-1",
            "--size",
            "20",
        ],
    )
    assert result.exit_code != 0
    assert "--yes" in result.stderr
    assert all(call[0] != "AttachCompShareDisk" for call in fake.calls)


def test_disk_detach_yes_calls_api(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(
        cli.app,
        [
            "disk",
            "detach",
            "--disk-id",
            "udisk-1",
            "--instance-id",
            "uhost-1",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    assert "OK" in result.stdout
    detach_calls = [c for c in fake.calls if c[0] == "DetachCompShareDisk"]
    assert len(detach_calls) == 1
    payload = detach_calls[0][1]
    assert payload["UDiskId"] == "udisk-1"
    assert payload["UHostId"] == "uhost-1"


def test_disk_detach_missing_yes(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(
        cli.app,
        [
            "disk",
            "detach",
            "--disk-id",
            "udisk-1",
            "--instance-id",
            "uhost-1",
        ],
    )
    assert result.exit_code != 0
    assert "--yes" in result.stderr
    assert all(call[0] != "DetachCompShareDisk" for call in fake.calls)


def test_disk_resize_yes_calls_api(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(
        cli.app,
        [
            "disk",
            "resize",
            "--disk-id",
            "udisk-1",
            "--size",
            "50",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    assert "OK" in result.stdout
    resize_calls = [c for c in fake.calls if c[0] == "ResizeCompShareDisk"]
    assert len(resize_calls) == 1
    payload = resize_calls[0][1]
    assert payload["UDiskId"] == "udisk-1"
    assert payload["Size"] == 50


def test_disk_resize_missing_yes(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(
        cli.app,
        [
            "disk",
            "resize",
            "--disk-id",
            "udisk-1",
            "--size",
            "50",
        ],
    )
    assert result.exit_code != 0
    assert "--yes" in result.stderr
    assert all(call[0] != "ResizeCompShareDisk" for call in fake.calls)


def test_disk_delete_requires_yes(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(
        cli.app,
        [
            "disk",
            "delete",
            "--disk-id",
            "udisk-1",
        ],
    )
    assert result.exit_code != 0
    assert "--yes" in result.stderr
    assert all(call[0] != "DeleteCompShareDisk" for call in fake.calls)


def test_disk_delete_yes_calls_api(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(
        cli.app,
        [
            "disk",
            "delete",
            "--disk-id",
            "udisk-1",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    assert "OK" in result.stdout
    assert fake.calls[-1][0] == "DeleteCompShareDisk"
    assert fake.calls[-1][1]["UDiskId"] == "udisk-1"


def test_disk_attach_agent_yes_returns_json(monkeypatch):
    install_fake_client(monkeypatch)
    result = runner.invoke(
        cli.app,
        [
            "disk",
            "attach",
            "--instance-id",
            "uhost-1",
            "--size",
            "20",
            "--agent",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["cost_risk"] == "may-incur-cost"
    assert data["data"]["instance_id"] == "uhost-1"
    assert data["data"]["size_gib"] == 20
    assert data["data"]["disk_id"] == "udisk-1"


def test_disk_delete_agent_without_yes(monkeypatch):
    install_fake_client(monkeypatch)
    result = runner.invoke(
        cli.app,
        [
            "disk",
            "delete",
            "--disk-id",
            "udisk-1",
            "--agent",
        ],
    )
    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["ok"] is False
    assert "--yes" in data["summary"]


def test_disk_detach_agent_without_yes(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(
        cli.app,
        [
            "disk",
            "detach",
            "--disk-id",
            "udisk-1",
            "--instance-id",
            "uhost-1",
            "--agent",
        ],
    )
    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["ok"] is False
    assert data["cost_risk"] == "destructive"
    assert all(call[0] != "DetachCompShareDisk" for call in fake.calls)


def test_disk_detach_agent_yes_returns_json(monkeypatch):
    install_fake_client(monkeypatch)
    result = runner.invoke(
        cli.app,
        [
            "disk",
            "detach",
            "--disk-id",
            "udisk-1",
            "--instance-id",
            "uhost-1",
            "--agent",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["cost_risk"] == "destructive"
    assert data["data"]["disk_id"] == "udisk-1"
    assert data["data"]["instance_id"] == "uhost-1"


def test_disk_resize_json(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(
        cli.app,
        [
            "disk",
            "resize",
            "--disk-id",
            "udisk-1",
            "--size",
            "50",
            "--yes",
            "--json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["RetCode"] == 0
    assert fake.calls[-1][0] == "ResizeCompShareDisk"
