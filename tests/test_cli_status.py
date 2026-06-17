from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from typer.testing import CliRunner

from agentwatch.cli.main import app

runner = CliRunner()


def test_status_command_success():
    # Mock httpx.AsyncClient
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "total_sessions": 10,
        "active_sessions": 2,
        "failed_sessions": 1,
        "blocked_sessions": 1,
        "total_tokens": 5000,
        "estimated_cost_usd": 0.15,
        "safety_stats": {"checked": 100, "blocked": 1, "approved": 0},
        "event_bus_stats": {"total_published": 200, "active_subscribers": 5},
    }

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp

    with patch(
        "httpx.AsyncClient",
        return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_client), __aexit__=AsyncMock()
        ),
    ):
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "AgentWatch Runtime Status" in result.stdout
    assert "Active sessions:        2" in result.stdout
    assert "Failed sessions:        1" in result.stdout
    assert "Total tokens consumed:  5,000" in result.stdout
    assert "Estimated cost:         $0.1500" in result.stdout
    assert "Blocked operations:     1" in result.stdout
    assert "Event throughput:       200 processed" in result.stdout
    assert "Active subscribers:     5" in result.stdout


def test_status_command_connection_error():
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")

    with patch(
        "httpx.AsyncClient",
        return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_client), __aexit__=AsyncMock()
        ),
    ):
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "Failed to connect to API" in result.stdout


def test_status_command_auth_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.HTTPStatusError(
        "Unauthorized", request=MagicMock(), response=mock_resp
    )

    with patch(
        "httpx.AsyncClient",
        return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_client), __aexit__=AsyncMock()
        ),
    ):
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "Authentication failed" in result.stdout


def test_status_command_other_http_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=mock_resp
    )

    with patch(
        "httpx.AsyncClient",
        return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_client), __aexit__=AsyncMock()
        ),
    ):
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "API request failed with status 500: Internal Server Error" in result.stdout
