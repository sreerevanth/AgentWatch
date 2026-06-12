"""
AgentWatch CLI
Rich terminal interface for session inspection, replay, safety review, and management.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="agentwatch",
    help="AgentWatch — Reliability, Safety, and Observability Layer for AI Agents",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def _status_color(status: str) -> str:
    return {
        "success": "green",
        "running": "blue",
        "failure": "red",
        "blocked": "yellow",
        "rolled_back": "magenta",
        "timeout": "orange1",
        "pending": "dim",
    }.get(status.lower(), "white")


def _risk_color(level: str) -> str:
    return {
        "safe": "green",
        "low": "cyan",
        "medium": "yellow",
        "high": "orange1",
        "critical": "red bold",
    }.get(level.lower(), "white")


def _load_session_file(path: Path):
    """Load a session JSON file from disk."""
    if not path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(1)
    with open(path) as f:
        return json.load(f)


# ─────────────────────────────────────────────
# NEW HELPER: Dry-run printer
# ─────────────────────────────────────────────


def _dry_run_print(action: str, detail: str = "") -> None:
    """Print a consistent dry-run preview line to the terminal."""
    detail_str = f"\n  [dim]{detail}[/dim]" if detail else ""
    console.print(f"[bold yellow][DRY-RUN][/bold yellow] Would {action}{detail_str}")


# ─────────────────────────────────────────────
# watch command — wrap an agent run
# ─────────────────────────────────────────────


@app.command()
def watch(
    prompt: str = typer.Argument(..., help="Prompt to run with Claude Code"),
    model: str = typer.Option("claude-opus-4-5", "--model", "-m"),
    max_turns: int = typer.Option(50, "--max-turns"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Save session to file"),
    no_safety: bool = typer.Option(False, "--no-safety", help="Disable safety checks (dangerous)"),
    policy: str = typer.Option(
        "default", "--policy", help="Safety policy: default|strict|permissive"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview what would happen without executing or writing to disk",
    ),
) -> None:
    """[bold]Watch[/bold] a Claude Code execution with full observability and safety."""

    if dry_run:
        console.print(
            Panel(
                "[bold yellow]DRY-RUN MODE[/bold yellow] — No agent will be run. "
                "No files will be written.\n"
                f"[dim]Prompt:[/dim]  "
                f"{prompt[:80]}{'...' if len(prompt) > 80 else ''}\n"
                f"[dim]Model:[/dim]   {model}\n"
                f"[dim]Turns:[/dim]   {max_turns}\n"
                f"[dim]Policy:[/dim]  {'DISABLED ⚠️' if no_safety else policy}\n"
                f"[dim]Safety:[/dim]  {'off' if no_safety else 'on'}",
                border_style="yellow",
                title="AgentWatch watch --dry-run",
            )
        )
        if output:
            _dry_run_print(
                "save session to file",
                f"Path: {output.resolve()}",
            )
        else:
            _dry_run_print("run agent (no --output specified, session would not be saved)")
        console.print("\n[yellow]Dry-run complete. Nothing was executed or written.[/yellow]")
        raise typer.Exit(0)

    async def _run() -> None:
        from agentwatch.adapters.claude_code import ClaudeCodeAdapter
        from agentwatch.core.safety import (
            DEFAULT_POLICY,
            SafetyEngine,
            SafetyPolicy,
            cli_approval_handler,
        )
        from agentwatch.replay.engine import ReplayEngine

        console.print(
            Panel(
                f"[bold cyan]AgentWatch[/bold cyan] — watching Claude Code\n"
                f"[dim]Prompt:[/dim] {prompt[:80]}{'...' if len(prompt) > 80 else ''}",
                border_style="cyan",
            )
        )

        if no_safety:
            console.print("[yellow]⚠️  Safety checks disabled![/yellow]")
            safety = SafetyEngine(
                policy=SafetyPolicy(
                    policy_id="disabled",
                    name="Disabled",
                    block_on_critical=False,
                    block_on_high=False,
                )
            )
        else:
            p = DEFAULT_POLICY
            if policy == "strict":
                p = SafetyPolicy(
                    policy_id="strict",
                    name="Strict",
                    block_on_high=True,
                    block_on_critical=True,
                    require_approval_on_medium=True,
                )
            safety = SafetyEngine(policy=p)
            safety.set_approval_callback(cli_approval_handler)

        adapter = ClaudeCodeAdapter(safety_engine=safety)

        from agentwatch.core.event_bus import get_event_bus

        bus = get_event_bus()

        async def on_event(event) -> None:
            _print_live_event(event)

        bus.subscribe_fn(on_event, handler_id="cli.watch.live")

        try:
            session = await adapter.run(prompt, model=model, max_turns=max_turns)
        finally:
            bus.unsubscribe("cli.watch.live")

        _print_session_summary(session, adapter.events)

        if output:
            from agentwatch.replay.engine import ReplayEngine

            re = ReplayEngine()
            rs = re.load_from_events(session, adapter.events)
            saved_path = re.save_to_file(rs, output)
            console.print(f"\n[green]Session saved to {saved_path}[/green]")

    asyncio.run(_run())


# ─────────────────────────────────────────────
# replay command
# ─────────────────────────────────────────────


@app.command()
def replay(
    session_file: Path = typer.Argument(..., help="Path to session JSON file"),
    speed: str = typer.Option("instant", "--speed", "-s", help="instant|fast|normal|slow"),
    from_step: int = typer.Option(0, "--from", help="Start from step N"),
    to_step: int | None = typer.Option(None, "--to", help="End at step N"),
    show_all: bool = typer.Option(False, "--all", help="Show all events including metadata"),
    failure_only: bool = typer.Option(False, "--failures", "-f", help="Show only failure points"),
) -> None:
    """[bold]Replay[/bold] a captured session step-by-step."""

    async def _run() -> None:
        from agentwatch.core.schema import AgentEvent, AgentSession
        from agentwatch.replay.engine import ReplayEngine, ReplaySpeed

        data = _load_session_file(session_file)
        session = AgentSession(**data["session"])
        events = [AgentEvent(**e) for e in data["events"]]

        engine = ReplayEngine()
        rs = engine.load_from_events(session, events)

        console.print(
            Panel(
                f"[bold]Replaying Session[/bold]\n"
                f"[dim]ID:[/dim]     {session.session_id}\n"
                f"[dim]Agent:[/dim]  {session.agent_name or session.agent_id}\n"
                f"[dim]Steps:[/dim]  {rs.total_steps}\n"
                f"[dim]Status:[/dim] "
                f"[{_status_color(session.status.value)}]{session.status.value}"
                f"[/{_status_color(session.status.value)}]",
                border_style="blue",
            )
        )

        if rs.failure_analysis:
            fa = rs.failure_analysis
            if (
                fa.primary_cause.value != "unknown" or fa.anomaly_flags
                if hasattr(fa, "anomaly_flags")
                else False
            ):
                console.print("\n[bold red]Failure Analysis:[/bold red]")
                console.print(f"  Cause: [yellow]{fa.primary_cause.value}[/yellow]")
                console.print(f"  {fa.summary}")
                if fa.recommendations:
                    console.print("\n[bold]Recommendations:[/bold]")
                    for rec in fa.recommendations:
                        console.print(f"  → {rec}")

        console.print()

        speed_map = {
            "instant": ReplaySpeed.INSTANT,
            "fast": ReplaySpeed.FAST,
            "normal": ReplaySpeed.NORMAL,
            "slow": ReplaySpeed.SLOW,
        }
        replay_speed = speed_map.get(speed, ReplaySpeed.INSTANT)

        async for step in engine.replay_async(
            rs, speed=replay_speed, start_step=from_step, end_step=to_step
        ):
            if failure_only and not step.is_failure_point:
                continue
            _print_replay_step(step, show_all=show_all)

        console.print("\n[green]✓ Replay complete[/green]")

    asyncio.run(_run())


# ─────────────────────────────────────────────
# sessions command
# ─────────────────────────────────────────────


@app.command()
def sessions(
    api_url: str = typer.Option("http://localhost:8000", "--api"),
    limit: int = typer.Option(20, "--limit", "-n"),
    framework: str | None = typer.Option(None, "--framework"),
) -> None:
    """[bold]List[/bold] recent agent sessions from the AgentWatch API."""

    async def _run() -> None:
        try:
            import httpx
        except ImportError:
            console.print("[red]httpx not installed. Run: pip install httpx[/red]")
            raise typer.Exit(1)

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{api_url}/api/v1/sessions",
                    params={"limit": limit, "framework": framework},
                    timeout=10.0,
                )
                resp.raise_for_status()
            except Exception as exc:
                console.print(f"[red]Failed to connect to API at {api_url}: {exc}[/red]")
                raise typer.Exit(1)

        data = resp.json()
        _print_sessions_table(data["sessions"])

    asyncio.run(_run())


# ─────────────────────────────────────────────
# confidence command
# ─────────────────────────────────────────────


@app.command()
def confidence(
    session_file: Path = typer.Argument(..., help="Path to session JSON file"),
) -> None:
    """[bold]Score[/bold] execution confidence and detect anomalies for a session."""

    from agentwatch.core.schema import AgentEvent, AgentSession
    from agentwatch.scoring.confidence import ConfidenceScorer

    data = _load_session_file(session_file)
    session = AgentSession(**data["session"])
    events = [AgentEvent(**e) for e in data["events"]]

    scorer = ConfidenceScorer()
    result = scorer.score(events, goal=session.goal)

    score_color = (
        "green"
        if result.overall_score >= 0.7
        else "yellow"
        if result.overall_score >= 0.4
        else "red"
    )

    console.print(
        Panel(
            f"[bold]Confidence Analysis[/bold]\nSession: {session.session_id[:16]}...",
            border_style="blue",
        )
    )

    table = Table(box=box.ROUNDED)
    table.add_column("Metric", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Rating")

    def _rate(s: float) -> str:
        if s >= 0.8:
            return "[green]● Good[/green]"
        elif s >= 0.5:
            return "[yellow]◐ Fair[/yellow]"
        return "[red]○ Poor[/red]"

    table.add_row(
        "Overall",
        f"[{score_color}]{result.overall_score:.3f}[/{score_color}]",
        _rate(result.overall_score),
    )
    table.add_row("Goal Alignment", f"{result.goal_alignment:.3f}", _rate(result.goal_alignment))
    table.add_row(
        "Consistency",
        f"{result.consistency_score:.3f}",
        _rate(result.consistency_score),
    )

    console.print(table)
    console.print()

    if result.anomaly_flags:
        console.print("[bold red]Anomalies Detected:[/bold red]")
        for flag in result.anomaly_flags:
            console.print(f"  [yellow]⚠[/yellow]  {flag}")
        console.print()

    console.print("[bold]Components:[/bold]")
    for k, v in result.component_scores.items():
        bar_len = int(v * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        color = "green" if v >= 0.7 else "yellow" if v >= 0.4 else "red"
        console.print(f"  {k:<25} [{color}]{bar}[/{color}] {v:.3f}")

    console.print(f"\n[dim]{result.explanation}[/dim]")


# ─────────────────────────────────────────────
# safety command
# ─────────────────────────────────────────────


@app.command()
def safety(
    command: str = typer.Argument(..., help="Command to risk-score"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """[bold]Score[/bold] the risk level of a shell command."""
    from agentwatch.core.safety import RiskScorer
    from agentwatch.core.schema import ToolCallData

    scorer = RiskScorer()
    tool = ToolCallData(tool_name="bash", raw_command=command, arguments={"command": command})
    level, score, reasons, policies = scorer.score(tool)

    color = _risk_color(level.value)
    console.print(f"\nCommand: [bold]{command}[/bold]")
    console.print(f"Risk:    [{color}]{level.value.upper()}[/{color}] (score: {score:.2f})")

    if reasons:
        console.print("\nMatched policies:")
        for i, (r, p) in enumerate(zip(reasons, policies)):
            console.print(f"  [{color}]{p}[/{color}]: {r}")
    else:
        console.print("[green]✓ No risk patterns matched[/green]")


# ─────────────────────────────────────────────
# serve command
# ─────────────────────────────────────────────


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8000, "--port"),
    reload: bool = typer.Option(False, "--reload"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview what would happen without starting the server",
    ),
) -> None:
    """[bold]Start[/bold] the AgentWatch API server."""

    if dry_run:
        console.print(
            Panel(
                "[bold yellow]DRY-RUN MODE[/bold yellow] — Server will NOT be started.\n"
                f"[dim]Would bind to:[/dim]  http://{host}:{port}\n"
                f"[dim]Dashboard:[/dim]     http://localhost:3000\n"
                f"[dim]Hot-reload:[/dim]    {'enabled' if reload else 'disabled'}\n"
                f"[dim]App module:[/dim]    agentwatch.api.server:app",
                border_style="yellow",
                title="AgentWatch serve --dry-run",
            )
        )
        _dry_run_print(
            "start uvicorn server",
            f"uvicorn agentwatch.api.server:app --host {host} --port {port}"
            + (" --reload" if reload else ""),
        )
        console.print("\n[yellow]Dry-run complete. Server was not started.[/yellow]")
        raise typer.Exit(0)

    try:
        import uvicorn
    except ImportError:
        console.print("[red]uvicorn not installed. Run: pip install uvicorn[/red]")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold cyan]AgentWatch API Server[/bold cyan]\n"
            f"[dim]Listening on[/dim] http://{host}:{port}\n"
            f"[dim]Dashboard[/dim]  http://localhost:3000",
            border_style="cyan",
        )
    )
    uvicorn.run(
        "agentwatch.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


# ─────────────────────────────────────────────
# verify-env command
# ─────────────────────────────────────────────


@app.command(name="verify-env")
def verify_env() -> None:
    """[bold]Verify[/bold] local developer environment variables and dependencies."""
    from agentwatch.cli.verify_env import verify_environment

    verify_environment()


# ─────────────────────────────────────────────
# Print helpers
# ─────────────────────────────────────────────


def _print_live_event(event) -> None:
    from agentwatch.core.schema import EventType

    icon_map = {
        EventType.TOOL_CALL: "🔧",
        EventType.TOOL_RESULT: "✅",
        EventType.TOOL_ERROR: "❌",
        EventType.SAFETY_BLOCK: "🚫",
        EventType.SAFETY_CHECK: "🛡",
        EventType.PLANNER_OUTPUT: "🧠",
        EventType.AGENT_START: "▶",
        EventType.AGENT_END: "⏹",
        EventType.SESSION_START: "🚀",
        EventType.SESSION_END: "🏁",
        EventType.CHECKPOINT_CREATE: "📍",
        EventType.ROLLBACK_TRIGGER: "↩",
        EventType.MEMORY_READ: "📖",
        EventType.MEMORY_WRITE: "✏️",
    }

    icon = icon_map.get(event.event_type, "•")
    ts = event.timestamp.strftime("%H:%M:%S")

    if event.event_type == EventType.TOOL_CALL and event.tool_call:
        name = event.tool_call.tool_name
        cmd = (event.tool_call.raw_command or "")[:60]
        risk_str = ""
        if event.safety:
            rc = _risk_color(event.safety.risk_level.value)
            risk_str = f" [{rc}][{event.safety.risk_level.value}][/{rc}]"
        status_str = " [red][BLOCKED][/red]" if event.is_blocked else ""
        console.print(f"[dim]{ts}[/dim] {icon} [bold]{name}[/bold]{risk_str}{status_str}")
        if cmd:
            console.print(f"         [dim]{cmd}[/dim]")

    elif event.event_type == EventType.SAFETY_BLOCK:
        console.print(f"[dim]{ts}[/dim] {icon} [bold red]SAFETY BLOCK[/bold red]")
        if event.safety and event.safety.reasons:
            for r in event.safety.reasons[:2]:
                console.print(f"         [red]→ {r}[/red]")

    elif event.event_type in (
        EventType.SESSION_START,
        EventType.SESSION_END,
        EventType.AGENT_START,
        EventType.AGENT_END,
    ):
        sc = _status_color(event.status.value)
        console.print(f"[dim]{ts}[/dim] {icon} [{sc}]{event.event_type.value}[/{sc}]")


def _print_replay_step(step, show_all: bool = False) -> None:
    event = step.event
    ts = event.timestamp.strftime("%H:%M:%S.%f")[:-3]

    annotations = " ".join(step.annotations)
    border = "red" if step.is_failure_point else "blue"

    info_lines = [
        f"[bold]Step {step.index:04d}[/bold]  "
        f"[{_status_color(event.status.value)}]{event.event_type.value}"
        f"[/{_status_color(event.status.value)}]  [dim]{ts}[/dim]"
    ]

    if event.tool_call:
        info_lines.append(f"Tool: [bold]{event.tool_call.tool_name}[/bold]")
        if event.tool_call.raw_command:
            info_lines.append(f"Cmd:  [dim]{event.tool_call.raw_command[:80]}[/dim]")
    if event.tool_result and event.tool_result.error:
        info_lines.append(f"[red]Error: {event.tool_result.error[:100]}[/red]")
    if event.safety and event.safety.risk_level.value not in ("safe", "low"):
        rc = _risk_color(event.safety.risk_level.value)
        info_lines.append(
            f"Risk: [{rc}]{event.safety.risk_level.value.upper()}[/{rc}]"
            f" ({event.safety.risk_score:.2f})"
        )
    if annotations:
        info_lines.append(f"[bold]{annotations}[/bold]")

    console.print(Panel("\n".join(info_lines), border_style=border, padding=(0, 1)))


def _print_session_summary(session, events) -> None:
    from agentwatch.scoring.confidence import ConfidenceScorer

    scorer = ConfidenceScorer()
    result = scorer.score(events, goal=session.goal)

    sc = _status_color(session.status.value)
    cc = (
        "green"
        if result.overall_score >= 0.7
        else "yellow"
        if result.overall_score >= 0.4
        else "red"
    )

    console.print(
        Panel(
            f"[bold]Session Complete[/bold]\n"
            f"Status:     [{sc}]{session.status.value}[/{sc}]\n"
            f"Events:     {session.total_events}\n"
            f"Tokens:     {session.total_tokens:,}\n"
            f"Cost (est): ${session.estimated_cost_usd:.4f}\n"
            f"Confidence: [{cc}]{result.overall_score:.3f}[/{cc}]\n"
            + (
                f"Anomalies:  {', '.join(result.anomaly_flags)}"
                if result.anomaly_flags
                else "Anomalies:  none"
            ),
            border_style=sc,
            title="AgentWatch Summary",
        )
    )


def _print_sessions_table(sessions: list) -> None:
    table = Table(title="Recent Sessions", box=box.ROUNDED)
    table.add_column("ID", style="dim", width=16)
    table.add_column("Agent")
    table.add_column("Framework")
    table.add_column("Status")
    table.add_column("Events", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Started")

    for s in sessions:
        sid = s["session_id"][:12] + "..."
        sc = _status_color(s.get("status", ""))
        started = s.get("started_at", "")[:16] if s.get("started_at") else "-"
        table.add_row(
            sid,
            s.get("agent_name") or s.get("agent_id", "?")[:16],
            s.get("framework", "-"),
            f"[{sc}]{s.get('status', '-')}[/{sc}]",
            str(s.get("total_events", 0)),
            f"{s.get('total_tokens', 0):,}",
            started,
        )

    console.print(table)


# ─────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────


def main() -> None:
    app()


if __name__ == "__main__":
    main()
