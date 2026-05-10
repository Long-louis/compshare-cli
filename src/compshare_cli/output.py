from __future__ import annotations

import json
from io import StringIO
from typing import Any, Iterable

import typer
from rich.console import Console
from rich.table import Table


def print_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


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
