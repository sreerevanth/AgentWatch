import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from agentwatch.cli.main import app

runner = CliRunner()

DUMMY_REPLAY = {
    "session": {
        "session_id": "abc-123",
        "status": "success",
        "framework": "claude_code",
        "started_at": "2026-06-14T10:00:00Z",
        "ended_at": "2026-06-14T10:01:00Z",
        "goal": "Test goal",
    },
    "steps": [
        {
            "index": 0,
            "event": {
                "event_type": "TOOL_CALL",
                "status": "success",
                "tool_call": {
                    "tool_name": "bash",
                    "raw_command": "echo 'hello'",
                },
                "tool_result": {
                    "output": "hello\n",
                },
            },
        }
    ],
    "failure_analysis": {
        "primary_cause": "unknown",
        "recommendations": ["Do better"],
    },
}

@pytest.fixture
def mock_httpx_client():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = DUMMY_REPLAY
        mock_instance.get.return_value = mock_response

        # AsyncClient as context manager
        mock_instance.__aenter__.return_value = mock_instance
        mock_client_cls.return_value = mock_instance
        yield mock_instance, mock_response


def test_export_json(mock_httpx_client, tmp_path):
    mock_instance, mock_response = mock_httpx_client
    out_file = tmp_path / "out.json"

    result = runner.invoke(
        app, ["session", "export", "abc-123", "--format", "json", "--output", str(out_file)]
    )
    assert result.exit_code == 0
    assert "out.json created successfully" in result.stdout

    mock_instance.get.assert_called_once()
    assert mock_instance.get.call_args[0][0].endswith("/api/v1/sessions/abc-123/replay")

    with open(out_file) as f:
        data = json.load(f)
    assert data["session"]["session_id"] == "abc-123"


def test_export_md(mock_httpx_client, tmp_path):
    mock_instance, mock_response = mock_httpx_client
    out_file = tmp_path / "out.md"

    result = runner.invoke(app, ["session", "export", "abc-123", "--format", "md", "--output", str(out_file)])
    assert result.exit_code == 0
    assert "out.md created successfully" in result.stdout

    with open(out_file, encoding="utf-8") as f:
        content = f.read()

    assert "# AgentWatch Session: abc-123" in content
    assert "**Status**: success" in content
    assert "### Goal" in content
    assert "Test goal" in content
    assert "## Failure Analysis" in content
    assert "Do better" in content
    assert "### Step 0" in content
    assert "**Tool**: bash" in content
    assert "echo 'hello'" in content
    assert "hello\n" in content


def test_export_invalid_format():
    result = runner.invoke(app, ["session", "export", "abc-123", "--format", "xml"])
    assert result.exit_code != 0
    assert "Invalid value" in result.output
    assert "not one of 'json', 'md'" in result.output


def test_export_404(mock_httpx_client):
    mock_instance, mock_response = mock_httpx_client
    mock_response.status_code = 404

    # We want it to raise httpx.HTTPError when raise_for_status is called,
    # OR we handle 404 manually before that. Our code handles 404 manually.

    result = runner.invoke(app, ["session", "export", "abc-123"])
    assert result.exit_code == 1
    assert "Session abc-123 not found" in result.stdout
