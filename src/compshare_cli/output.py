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


def command_suggestion(
    label: str,
    command: str,
    risk: Risk,
    requires_confirmation: bool,
) -> dict[str, Any]:
    return {
        "label": label,
        "command": command,
        "risk": risk,
        "requires_confirmation": requires_confirmation,
    }


def agent_envelope(
    command: str,
    summary: str,
    data: Any = None,
    cost_risk: CostRisk = "none",
    *,
    ok: bool = True,
    warnings: list[str] | None = None,
    next_actions: list[str] | None = None,
    commands: list[dict[str, Any]] | None = None,
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
