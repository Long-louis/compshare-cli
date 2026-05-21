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
                {
                    "UHostId": "uhost-1",
                    "Name": "stopped-gpu",
                    "State": "Stopped",
                    "Zone": "cn-sh2-02",
                }
            ],
        }


def test_doctor_agent_success(monkeypatch):
    monkeypatch.setattr(
        cli, "load_credentials", lambda: Credentials("public", "private")
    )
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
