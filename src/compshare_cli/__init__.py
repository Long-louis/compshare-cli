"""Command line tools for CompShare GPU rental workflows."""

__version__ = "0.1.0"


def main() -> None:
    from .cli import app

    app()
