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
