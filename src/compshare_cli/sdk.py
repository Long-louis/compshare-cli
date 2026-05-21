from __future__ import annotations

from typing import Any

from ucloud.client import Client
from ucloud.core import exc

from .config import Credentials
from .errors import CliError

DEFAULT_BASE_URL = "https://api.compshare.cn"


class CompShareClient:
    def __init__(
        self,
        credentials: Credentials,
        *,
        base_url: str = DEFAULT_BASE_URL,
        sdk_client: Any | None = None,
    ) -> None:
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
            message = str(
                response.get("Message") or f"CompShare API returned RetCode {ret_code}"
            )
            raise CliError(
                message, type_name="CompShareApiError", ret_code=int(ret_code)
            )
