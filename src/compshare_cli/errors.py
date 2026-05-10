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
