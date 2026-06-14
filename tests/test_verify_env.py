"""Unit tests for the verify-env CLI command."""

from __future__ import annotations

from typer.testing import CliRunner

from agentwatch.cli.main import app

runner = CliRunner()


def test_verify_env_cli():
    result = runner.invoke(app, ["verify-env"])
    assert result.exit_code == 0
    assert "AgentWatch Environment Diagnostics" in result.stdout
    assert "Python version" in result.stdout
    assert "Dependencies Status" in result.stdout
