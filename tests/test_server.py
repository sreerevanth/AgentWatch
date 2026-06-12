"""Tests for the AgentWatch API server."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import agentwatch.api.server as _server_module
from agentwatch.api.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == "0.2.0"


def test_get_sessions_empty(client):
    response = client.get("/api/v1/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert isinstance(data["sessions"], list)


def test_publish_event_malformed(client):
    response = client.post("/api/v1/events", json={"invalid": "data"})
    assert response.status_code == 422  # Validation error


def test_get_governance_report(client):
    response = client.get("/api/v1/governance/compliance-report")
    assert response.status_code == 200
    assert "generated_at" in response.json()


# ---------------------------------------------------------------------------
# WebSocket /ws/events authentication tests (issue #120)
# ---------------------------------------------------------------------------


class TestWebSocketAuth:
    """Verify that /ws/events enforces API key authentication consistently
    with the REST layer, covering both the header and query-param paths as
    well as the no-key-configured (development) and key-configured cases.
    """

    def test_anonymous_connection_rejected_when_key_configured(self, monkeypatch):
        """An anonymous WebSocket connection must be rejected when
        AGENTWATCH_API_KEY is set, regardless of whether a key is supplied.
        The server closes before accepting, so the client library raises
        WebSocketDisconnect at connection entry time.
        """
        monkeypatch.setattr(_server_module, "_API_KEY", "test-secret")
        monkeypatch.setattr(_server_module, "_IS_PROD", False)
        client = TestClient(app)
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/events"):
                pass

    def test_wrong_key_rejected_via_header(self, monkeypatch):
        """A connection supplying an incorrect key in X-Api-Key is rejected."""
        monkeypatch.setattr(_server_module, "_API_KEY", "correct-secret")
        monkeypatch.setattr(_server_module, "_IS_PROD", False)
        client = TestClient(app)
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/events", headers={"x-api-key": "wrong-secret"}):
                pass

    def test_wrong_key_rejected_via_query_param(self, monkeypatch):
        """A connection supplying an incorrect key as ?api_key=... is rejected."""
        monkeypatch.setattr(_server_module, "_API_KEY", "correct-secret")
        monkeypatch.setattr(_server_module, "_IS_PROD", False)
        client = TestClient(app)
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/events?api_key=wrong-secret"):
                pass

    def test_valid_key_accepted_via_header(self, monkeypatch):
        """A connection with the correct key in X-Api-Key is accepted."""
        monkeypatch.setattr(_server_module, "_API_KEY", "correct-secret")
        monkeypatch.setattr(_server_module, "_IS_PROD", False)
        client = TestClient(app)
        with client.websocket_connect("/ws/events", headers={"x-api-key": "correct-secret"}) as ws:
            # Connection accepted; send a keepalive ping and verify no error.
            ws.send_text("ping")

    def test_valid_key_accepted_via_query_param(self, monkeypatch):
        """A connection with the correct key as ?api_key=... is accepted."""
        monkeypatch.setattr(_server_module, "_API_KEY", "correct-secret")
        monkeypatch.setattr(_server_module, "_IS_PROD", False)
        client = TestClient(app)
        with client.websocket_connect("/ws/events?api_key=correct-secret") as ws:
            ws.send_text("ping")

    def test_no_key_configured_development_allows_connection(self, monkeypatch):
        """When AGENTWATCH_API_KEY is not set and the environment is
        development, WebSocket connections are accepted without a key,
        matching the existing REST endpoint behaviour.
        """
        monkeypatch.setattr(_server_module, "_API_KEY", None)
        monkeypatch.setattr(_server_module, "_IS_PROD", False)
        client = TestClient(app)
        with client.websocket_connect("/ws/events") as ws:
            ws.send_text("ping")

    def test_no_key_configured_production_rejects_connection(self, monkeypatch):
        """When AGENTWATCH_API_KEY is not set in production the server must
        fail-closed and reject the WebSocket connection (code 4500).
        """
        monkeypatch.setattr(_server_module, "_API_KEY", None)
        monkeypatch.setattr(_server_module, "_IS_PROD", True)
        client = TestClient(app)
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/events"):
                pass


def test_update_safety_policy_validation(client):
    # Valid payload
    resp = client.put(
        "/api/v1/safety/policy",
        json={
            "block_on_high": True,
            "block_on_critical": True,
            "require_approval_on_high": True,
            "require_approval_on_medium": False,
            "approval_timeout_seconds": 60,
        },
    )
    assert resp.status_code == 200

    # Invalid payload (timeout too low)
    resp = client.put(
        "/api/v1/safety/policy",
        json={
            "approval_timeout_seconds": 4,
        },
    )
    assert resp.status_code == 422

    # Invalid payload (timeout too high)
    resp = client.put(
        "/api/v1/safety/policy",
        json={
            "approval_timeout_seconds": 99999,
        },
    )
    assert resp.status_code == 422
