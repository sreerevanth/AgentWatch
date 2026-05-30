"""Tests for the AgentWatch API server."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

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


@pytest.mark.asyncio
async def test_api_server_safety_request_endpoint(client, monkeypatch):
    import asyncio

    from agentwatch.api.server import _safety_engine

    # We mock submit_pending_approval to create the future inside the running loop
    # of the active TestClient request, resolving it immediately.
    def mock_submit(event_id):
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        future.set_result(True)
        return future

    monkeypatch.setattr(_safety_engine, "submit_pending_approval", mock_submit)

    req_body = {
        "event_id": "test-mock-event",
        "session_id": "test-session",
        "agent_id": "test-agent",
        "safety": {
            "risk_level": "high",
            "risk_score": 0.8,
            "reasons": ["risky push"],
        },
        "approval_timeout_seconds": 5,
    }

    resp = client.post("/api/v1/safety/request", json=req_body)
    assert resp.status_code == 200
    assert resp.json()["approved"] is True
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_api_server_safety_pending_and_resolve_endpoints(client):
    from agentwatch.api.server import _safety_engine

    # 1. Verify initially no pending approvals
    resp = client.get("/api/v1/safety/pending")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    # 2. Add a pending approval directly to the engine
    event_id = "test-direct-event"
    _safety_engine.submit_pending_approval(event_id)

    # 3. Verify it is now listed
    resp = client.get("/api/v1/safety/pending")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert event_id in resp.json()["pending_event_ids"]

    # 4. Resolve it via the endpoint
    resp = client.post(
        f"/api/v1/safety/pending/{event_id}/resolve",
        json={"approved": True},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"
    assert resp.json()["approved"] is True

    # 5. Verify no pending approvals left
    resp = client.get("/api/v1/safety/pending")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
