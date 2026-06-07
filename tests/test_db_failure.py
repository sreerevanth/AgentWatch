from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agentwatch.api.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check_reports_db_status(client):
    # Depending on current state, it might be True or False
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "database_connected" in data
    assert isinstance(data["database_connected"], bool)


def test_system_status_endpoint(client):
    # Protect with API key if needed, but in local dev it's usually None
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert "database" in data
    assert "connected" in data["database"]
    assert "mode" in data["database"]
    assert data["database"]["mode"] in ["persistent", "in-memory"]
