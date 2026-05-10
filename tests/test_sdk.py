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
