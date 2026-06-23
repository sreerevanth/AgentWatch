"""Unit tests for Visual Workflow Builder endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agentwatch.api.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_workflows_lifecycle(client):
    # Test GET list
    resp = client.get("/api/workflows")
    assert resp.status_code == 200
    initial_workflows = resp.json()
    assert isinstance(initial_workflows, list)

    # Test POST
    new_workflow = {
        "id": "wf-test-1234",
        "name": "Integration Test Workflow",
        "description": "Created during testing",
        "nodes": [
            {
                "id": "node-1",
                "type": "agent",
                "position": {"x": 100.0, "y": 200.0},
                "data": {"name": "Test Agent"}
            }
        ],
        "edges": []
    }
    resp = client.post("/api/workflows", json=new_workflow)
    assert resp.status_code == 200
    saved = resp.json()
    assert saved["status"] == "saved"
    assert saved["workflow"]["id"] == "wf-test-1234"

    # Test GET by ID
    resp = client.get("/api/workflows/wf-test-1234")
    assert resp.status_code == 200
    retrieved = resp.json()
    assert retrieved["id"] == "wf-test-1234"
    assert retrieved["name"] == "Integration Test Workflow"

    # Test GET list again to verify it is present
    resp = client.get("/api/workflows")
    assert resp.status_code == 200
    workflows = resp.json()
    assert any(w["id"] == "wf-test-1234" for w in workflows)

    # Test DELETE
    resp = client.delete("/api/workflows/wf-test-1234")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    # Test GET by ID after delete (should be 404)
    resp = client.get("/api/workflows/wf-test-1234")
    assert resp.status_code == 404
