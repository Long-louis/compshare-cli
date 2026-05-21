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
            return {"RetCode": 0, "UHostSet": [{"UHostId": "uhost-1", "Name": "gpu", "State": "Stopped", "Zone": "cn-sh2-02"}]}
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
        return {"RetCode": 0}


def install_fake_client(monkeypatch):
    fake = FakeCompShareClient()
    monkeypatch.setattr(cli, "load_credentials", lambda: Credentials("public", "private"))
    monkeypatch.setattr(cli, "CompShareClient", lambda credentials: fake)
    return fake


def test_image_create_calls_api(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, [
        "image", "create",
        "--instance-id", "uhost-1",
        "--name", "my-image",
    ])
    assert result.exit_code == 0
    assert "compshareImage-custom-1" in result.stdout
    create_calls = [c for c in fake.calls if c[0] == "CreateCompShareCustomImage"]
    assert len(create_calls) == 1
    payload = create_calls[0][1]
    assert payload["UHostId"] == "uhost-1"
    assert payload["Name"] == "my-image"
    assert payload["Region"] == "cn-sh2"
    assert payload["Zone"] == "cn-sh2-02"


def test_image_create_with_description(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, [
        "image", "create",
        "--instance-id", "uhost-1",
        "--name", "my-image",
        "--description", "my description",
    ])
    assert result.exit_code == 0
    create_calls = [c for c in fake.calls if c[0] == "CreateCompShareCustomImage"]
    assert len(create_calls) == 1
    assert create_calls[0][1]["Description"] == "my description"


def test_image_list_prints_image_id(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["image", "list"])
    assert result.exit_code == 0
    assert "compshareImage-custom-1" in result.stdout
    assert fake.calls[-1][0] == "DescribeCompShareCustomImages"


def test_image_show_progress_prints_percent(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["image", "show-progress", "--image-id", "compshareImage-custom-1"])
    assert result.exit_code == 0
    assert "100.0%" in result.stdout
    assert fake.calls[-1][0] == "GetCompShareImageCreateProgress"
    assert fake.calls[-1][1]["CompShareImageId"] == "compshareImage-custom-1"


def test_image_delete_requires_yes(monkeypatch):
    install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["image", "delete", "--image-id", "compshareImage-custom-1"])
    assert result.exit_code != 0
    assert "requires --yes" in result.stderr
    assert "requires --yes" not in result.stdout


def test_image_delete_agent_risk_label(monkeypatch):
    install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["image", "delete", "--image-id", "compshareImage-custom-1", "--agent"])
    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["ok"] is False
    assert data["cost_risk"] == "destructive"


def test_image_create_handles_zone_value_error(monkeypatch):
    class FakeWithUnknownZone(FakeCompShareClient):
        def invoke(self, action, payload):
            if action == "DescribeCompShareInstance":
                return {"RetCode": 0, "UHostSet": [{"UHostId": "uhost-bad", "Name": "gpu", "State": "Stopped", "Zone": "unknown-zone"}]}
            return super().invoke(action, payload)

    fake = FakeWithUnknownZone()
    monkeypatch.setattr(cli, "load_credentials", lambda: Credentials("public", "private"))
    monkeypatch.setattr(cli, "CompShareClient", lambda credentials: fake)
    result = runner.invoke(cli.app, [
        "image", "create",
        "--instance-id", "uhost-bad",
        "--name", "my-image",
        "--json",
    ])
    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert "error" in data
    assert "unknown-zone" in result.stdout


def test_image_create_handles_zone_value_error_agent(monkeypatch):
    class FakeWithUnknownZone(FakeCompShareClient):
        def invoke(self, action, payload):
            if action == "DescribeCompShareInstance":
                return {"RetCode": 0, "UHostSet": [{"UHostId": "uhost-bad", "Name": "gpu", "State": "Stopped", "Zone": "unknown-zone"}]}
            return super().invoke(action, payload)

    fake = FakeWithUnknownZone()
    monkeypatch.setattr(cli, "load_credentials", lambda: Credentials("public", "private"))
    monkeypatch.setattr(cli, "CompShareClient", lambda credentials: fake)
    result = runner.invoke(cli.app, [
        "image", "create",
        "--instance-id", "uhost-bad",
        "--name", "my-image",
        "--agent",
    ])
    assert result.exit_code != 0
    data = json.loads(result.stdout)
    assert data["ok"] is False
    assert "unknown-zone" in data["data"]["error"]


def test_image_delete_yes_calls_api(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["image", "delete", "--image-id", "compshareImage-custom-1", "--yes"])
    assert result.exit_code == 0
    assert "OK" in result.stdout
    assert fake.calls[-1][0] == "TerminateCompShareCustomImage"
    assert fake.calls[-1][1]["CompShareImageId"] == "compshareImage-custom-1"


def test_image_create_agent_returns_json(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, [
        "image", "create",
        "--instance-id", "uhost-1",
        "--name", "my-image",
        "--agent",
    ])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["cost_risk"] == "may-incur-cost"
    assert data["data"]["image_id"] == "compshareImage-custom-1"
    assert any("compshare image show-progress" in cmd["command"] for cmd in data["commands"])


def test_image_list_json_returns_raw_response(monkeypatch):
    fake = install_fake_client(monkeypatch)
    result = runner.invoke(cli.app, ["image", "list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "ImageSet" in data
    assert data["ImageSet"][0]["CompShareImageId"] == "compshareImage-custom-1"
    assert fake.calls[-1][0] == "DescribeCompShareCustomImages"
