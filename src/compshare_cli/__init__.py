"""Command line tools for CompShare GPU rental workflows."""

__version__ = "0.2.0"


def main() -> None:
    from .cli import app

    app()
