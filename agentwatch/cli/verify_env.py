"""
CLI command to check local setup, database connections, and dependencies.
"""

from __future__ import annotations

import os
import sys

from rich.console import Console
from rich.table import Table

console = Console()


def verify_environment() -> None:
    """Run diagnostics on environment variables, dependencies, and python version."""
    console.print("\n[bold cyan]AgentWatch Environment Diagnostics[/bold cyan]")
    console.print("=" * 50)

    # 1. Python version check
    py_ver = sys.version_info
    py_ver_str = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"
    if py_ver.major == 3 and py_ver.minor >= 12:
        console.print(f"[green][OK][/green] Python version: {py_ver_str} (compatible)")
    else:
        console.print(f"[red][FAIL][/red] Python version: {py_ver_str} (requires >= 3.12)")

    # 2. Dependency checks
    deps = {
        "fastapi": "FastAPI",
        "uvicorn": "Uvicorn",
        "pydantic": "Pydantic",
        "sqlalchemy": "SQLAlchemy",
        "redis": "Redis Client",
        "celery": "Celery",
        "httpx": "HTTPX",
        "rich": "Rich Text Engine",
    }
    table = Table(title="Required Dependencies Status", show_header=True, header_style="bold blue")
    table.add_column("Dependency", style="cyan")
    table.add_column("Status")

    for pkg, name in deps.items():
        try:
            __import__(pkg)
            table.add_row(name, "[green]Installed[/green]")
        except ImportError:
            table.add_row(name, "[red]Missing[/red]")
    console.print(table)

    # 3. Environment Variables
    env_vars = [
        ("DATABASE_URL", False),
        ("REDIS_URL", False),
        ("CELERY_BROKER_URL", False),
        ("AGENTWATCH_API_KEY", False),
        ("ANTHROPIC_API_KEY", False),
        ("ENVIRONMENT", False),
    ]

    var_table = Table(title="Environment Variables", show_header=True, header_style="bold blue")
    var_table.add_column("Variable", style="cyan")
    var_table.add_column("State")
    var_table.add_column("Value")

    for var, required in env_vars:
        val = os.environ.get(var)
        if val:
            # Mask sensitive values
            display_val = val if var in ("ENVIRONMENT",) else f"{val[:6]}... (masked)"
            var_table.add_row(var, "[green]Set[/green]", display_val)
        else:
            state = "[red]Required[/red]" if required else "[yellow]Optional[/yellow]"
            var_table.add_row(var, state, "[dim]Not Set[/dim]")

    console.print(var_table)
    console.print("\n[bold green]Diagnostics complete[/bold green]\n")
