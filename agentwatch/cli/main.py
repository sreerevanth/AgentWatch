"""AgentWatch CLI entry point."""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(
    name="agentwatch",
    help="AgentWatch — reliability, safety and observability for AI agents.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind host"),  # noqa: S104
    port: int = typer.Option(8000, help="Bind port"),
    reload: bool = typer.Option(False, help="Enable auto-reload (dev only)"),
) -> None:
    """Start the AgentWatch API server."""
    import uvicorn

    from agentwatch.api.server import app as fastapi_app  # noqa: F401

    console.print(f"[bold green]AgentWatch[/] starting on {host}:{port}")
    uvicorn.run("agentwatch.api.server:app", host=host, port=port, reload=reload)


@app.command()
def version() -> None:
    """Print the installed AgentWatch version."""
    from importlib.metadata import version as pkg_version

    console.print(f"agentwatch {pkg_version('agentwatch-ai')}")


def main() -> None:
    """CLI entry point (used by pyproject.toml scripts)."""
    app()
